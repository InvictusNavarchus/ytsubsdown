import unittest
import json
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from http.server import BaseHTTPRequestHandler
from io import BytesIO

# Ensure the api directory is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

# Import handlers
from get_video_info import handler as GetVideoInfoHandler
from get_subtitles import handler as GetSubtitlesHandler

class MockHTTPRequest:
    def __init__(self, method, path, headers, body=None):
        self.method = method
        self.path = path
        self.headers = headers
        if body:
            self.rfile = BytesIO(json.dumps(body).encode('utf-8'))
        else:
            self.rfile = BytesIO(b'')
        self.wfile = BytesIO() # To capture output

    def makefile(self, mode, *args, **kwargs):
        if mode == 'rb':
            return self.rfile
        elif mode == 'wb':
            return self.wfile
        return None # Should not happen in this context

class BaseTestHandler(unittest.TestCase):
    def _simulate_post_request(self, handler_class, body_dict):
        headers = {'Content-Length': str(len(json.dumps(body_dict)))}
        request = MockHTTPRequest('POST', '/', headers, body_dict)

        # Create a response_handler instance
        response_handler_instance = handler_class(request, ('localhost', 8000), None)

        # Capture response
        response_bytes = request.wfile.getvalue()

        # The first part of response_bytes might be headers, find where JSON begins
        try:
            json_start_index = response_bytes.find(b'{')
            if json_start_index == -1: # If no '{', maybe it's an array starting with '['
                 json_start_index = response_bytes.find(b'[')

            if json_start_index != -1:
                response_json_str = response_bytes[json_start_index:].decode('utf-8')
                response_data = json.loads(response_json_str)
            else: # No JSON found, maybe an error message not in JSON
                response_data = {"raw_response": response_bytes.decode('utf-8', errors='ignore')}
        except json.JSONDecodeError:
             response_data = {"error": "Failed to decode JSON response", "raw_response": response_bytes.decode('utf-8', errors='ignore')}

        # Extract status code (this is a bit hacky as send_response is not easily captured without deeper mocking)
        # For simplicity, we'll assume 200 if JSON is valid and no obvious error structure,
        # or rely on the error structure within the JSON.
        status_code = 200 # Placeholder
        if "error" in response_data and isinstance(response_data["error"], str) :
            if "400" in response_data["error"].lower() or "required" in response_data["error"].lower():
                 status_code = 400
            elif "404" in response_data["error"].lower() or "not found" in response_data["error"].lower():
                 status_code = 404
            elif "500" in response_data["error"].lower() or "internal server error" in response_data["error"].lower():
                 status_code = 500

        # A more robust way to get status_code would be to mock send_response on the handler instance
        # For now, this simplified approach will be used.

        return status_code, response_data

# ----- Tests for get_video_info.py -----
class TestGetVideoInfoHandler(BaseTestHandler):

    @patch('get_video_info.YoutubeDL')
    def test_video_with_manual_and_auto_subs(self, MockYoutubeDL):
        mock_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "id": "test_video_id", "title": "Test Video", "channel": "Test Channel",
            "description": "A test video.", "webpage_url": "http://example.com/test_video_id",
            "view_count": 1000, "upload_date": "20230101",
            "subtitles": {
                "en": [{"ext": "vtt", "name": "English", "url": "manual_en_url"}],
                "fr": [{"ext": "srv1", "name": "French", "url": "manual_fr_url"}]
            },
            "automatic_captions": {
                "en": [{"ext": "vtt", "name": "English", "url": "auto_en_url"}],
                "es": [{"ext": "srv2", "name": "Spanish", "url": "auto_es_url"}]
            }
        }

        status, response = self._simulate_post_request(GetVideoInfoHandler, {"video_url": "http://example.com/test_video_id"})

        self.assertEqual(status, 200)
        self.assertIn("metadata", response)
        self.assertIn("tracks", response)
        self.assertEqual(response["metadata"]["video_id"], "test_video_id")
        self.assertEqual(len(response["tracks"]), 4) # 2 manual, 2 auto

        # Check one manual and one auto track
        manual_en_track = next(t for t in response["tracks"] if t["lang_code"] == "en" and not t["is_asr"])
        auto_en_track = next(t for t in response["tracks"] if t["lang_code"] == "en" and t["is_asr"])

        self.assertEqual(manual_en_track["name"], "English")
        self.assertTrue("auto-generated" in auto_en_track["name"])


    @patch('get_video_info.YoutubeDL')
    def test_video_with_no_subs(self, MockYoutubeDL):
        mock_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "id": "no_sub_id", "title": "No Subs Video", "channel": "Test Channel",
            "description": "A video with no subtitles.", "webpage_url": "http://example.com/no_sub_id",
            "view_count": 50, "upload_date": "20230102",
            "subtitles": {},
            "automatic_captions": {}
        }

        status, response = self._simulate_post_request(GetVideoInfoHandler, {"video_url": "http://example.com/no_sub_id"})

        self.assertEqual(status, 200) # Should still return metadata
        self.assertIn("metadata", response)
        self.assertEqual(len(response["tracks"]), 0)


    @patch('get_video_info.YoutubeDL')
    def test_video_with_various_languages(self, MockYoutubeDL):
        mock_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "id": "multi_lang_id", "title": "Multi-Lang Video", "channel": "Lang Channel",
            "description": "Video with subs in DE, JA.", "webpage_url": "http://example.com/multi_lang_id",
            "view_count": 500, "upload_date": "20230103",
            "subtitles": {
                "de": [{"ext": "ttml", "name": "Deutsch", "url": "manual_de_url"}],
                "ja": [{"ext": "srv3", "name": "日本語", "url": "manual_ja_url"}]
            },
            "automatic_captions": {}
        }

        status, response = self._simulate_post_request(GetVideoInfoHandler, {"video_url": "http://example.com/multi_lang_id"})

        self.assertEqual(status, 200)
        self.assertEqual(len(response["tracks"]), 2)
        self.assertTrue(any(t["lang_code"] == "de" for t in response["tracks"]))
        self.assertTrue(any(t["lang_code"] == "ja" for t in response["tracks"]))

    @patch('get_video_info.YoutubeDL')
    def test_invalid_video_url_info(self, MockYoutubeDL):
        mock_instance = MockYoutubeDL.return_value.__enter__.return_value
        # Simulate yt-dlp failing to extract info
        mock_instance.extract_info.side_effect = Exception("yt-dlp download error")

        status, response = self._simulate_post_request(GetVideoInfoHandler, {"video_url": "http://invalid.url/error_video"})

        # The error message is generic now, so we check for 500
        self.assertEqual(status, 500)
        self.assertIn("error", response)
        self.assertTrue("Internal server error" in response["error"])

# ----- Tests for get_subtitles.py -----
class TestGetSubtitlesHandler(BaseTestHandler):

    @patch('get_subtitles.YoutubeDL')
    @patch('builtins.open', new_callable=mock_open, read_data="1\n00:00:01,000 --> 00:00:02,000\nTest subtitle\n")
    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: "/".join(args)) # Simple mock for os.path.join
    @patch('os.remove') # Mock os.remove to avoid FileNotFoundError
    def test_fetch_manual_subtitle(self, mock_remove, mock_join, mock_listdir, mock_file_open, MockYoutubeDL):
        # Mock for the pre-fetch of video_id
        mock_ydl_instance_pre = MagicMock()
        mock_ydl_instance_pre.extract_info.return_value = {"id": "test_id_manual"}

        # Mock for the subtitle download and metadata fetch
        mock_ydl_instance_main = MagicMock()
        mock_ydl_instance_main.extract_info.return_value = { # For metadata
            "id": "test_id_manual", "title": "Manual Sub Test", "channel": "Sub Channel",
            "upload_date": "20230201", "view_count": 100, "webpage_url": "http://example.com/manual_sub"
        }
        mock_ydl_instance_main.download.return_value = 0 # Simulate successful download call

        # Chain the mocks for multiple 'with YoutubeDL(...)' calls
        MockYoutubeDL.return_value.__enter__.side_effect = [mock_ydl_instance_pre, mock_ydl_instance_main, mock_ydl_instance_main]

        mock_listdir.return_value = ["test_id_manual.en.srt"] # File that will be "found"

        track_info = {"lang_code": "en", "is_asr": False, "name": "English"}
        body = {"video_url": "http://example.com/manual_sub", "track_info": track_info, "include_metadata": True}

        status, response = self._simulate_post_request(GetSubtitlesHandler, body)

        self.assertEqual(status, 200)
        self.assertIn("subtitle_content", response)
        self.assertTrue("Test subtitle" in response["subtitle_content"])
        self.assertTrue("Title: Manual Sub Test" in response["subtitle_content"]) # Metadata header
        self.assertIn("metadata", response)
        self.assertEqual(response["metadata"]["video_id"], "test_id_manual")
        mock_file_open.assert_called_with("/temp_dir_mock/test_id_manual.en.srt", 'r', encoding='utf-8')

        # Check that os.path.join was called to construct the path within the temp dir
        # The exact path depends on how tempfile.TemporaryDirectory and os.path.join are mocked.
        # For this test, a simple side_effect for os.path.join is used.
        # A more robust mock for tempfile.TemporaryDirectory would be needed for precise path checking.
        # For now, we assume the mock_open call path is sufficient.

    @patch('get_subtitles.YoutubeDL')
    @patch('builtins.open', new_callable=mock_open, read_data="1\n00:00:03,000 --> 00:00:04,000\nASR Subtitle\n")
    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: "/".join(args))
    @patch('os.remove')
    def test_fetch_auto_subtitle(self, mock_remove, mock_join, mock_listdir, mock_file_open, MockYoutubeDL):
        mock_ydl_instance_pre = MagicMock()
        mock_ydl_instance_pre.extract_info.return_value = {"id": "test_id_asr"}

        mock_ydl_instance_main = MagicMock()
        mock_ydl_instance_main.extract_info.return_value = { # For metadata
            "id": "test_id_asr", "title": "ASR Sub Test", "channel": "ASR Channel",
            "upload_date": "20230202", "view_count": 200, "webpage_url": "http://example.com/asr_sub"
        }
        mock_ydl_instance_main.download.return_value = 0

        MockYoutubeDL.return_value.__enter__.side_effect = [mock_ydl_instance_pre, mock_ydl_instance_main, mock_ydl_instance_main]
        mock_listdir.return_value = ["test_id_asr.en.asr.srt"]

        track_info = {"lang_code": "en", "is_asr": True, "name": "English (auto-generated)"}
        body = {"video_url": "http://example.com/asr_sub", "track_info": track_info, "include_metadata": True}

        status, response = self._simulate_post_request(GetSubtitlesHandler, body)

        self.assertEqual(status, 200)
        self.assertTrue("ASR Subtitle" in response["subtitle_content"])
        self.assertTrue("Title: ASR Sub Test" in response["subtitle_content"])

    @patch('get_subtitles.YoutubeDL')
    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: "/".join(args))
    @patch('os.remove')
    def test_fetch_no_subtitles_file_found(self, mock_remove, mock_join, mock_listdir, MockYoutubeDL):
        mock_ydl_instance_pre = MagicMock()
        mock_ydl_instance_pre.extract_info.return_value = {"id": "test_id_no_file"}

        mock_ydl_instance_main = MagicMock() # For the download call
        mock_ydl_instance_main.download.return_value = 0 # Simulate download call success (but no file "created")

        MockYoutubeDL.return_value.__enter__.side_effect = [mock_ydl_instance_pre, mock_ydl_instance_main]
        mock_listdir.return_value = [] # Simulate no subtitle file found in temp dir

        track_info = {"lang_code": "es", "is_asr": False, "name": "Spanish"}
        body = {"video_url": "http://example.com/no_sub_file", "track_info": track_info}

        status, response = self._simulate_post_request(GetSubtitlesHandler, body)

        self.assertEqual(status, 500)
        self.assertIn("error", response)
        self.assertTrue("Subtitle file for language 'es' not found" in response["error"])

    @patch('get_subtitles.YoutubeDL')
    def test_invalid_video_url_subs(self, MockYoutubeDL):
        mock_ydl_instance_pre = MagicMock()
        mock_ydl_instance_pre.extract_info.side_effect = Exception("yt-dlp id fetch error")
        MockYoutubeDL.return_value.__enter__.return_value = mock_ydl_instance_pre

        track_info = {"lang_code": "en", "is_asr": False, "name": "English"}
        body = {"video_url": "http://invalid.url/error_video_subs", "track_info": track_info}

        status, response = self._simulate_post_request(GetSubtitlesHandler, body)

        self.assertEqual(status, 500)
        self.assertIn("error", response)
        self.assertTrue("Error fetching video ID" in response["error"])


    @patch('get_subtitles.YoutubeDL')
    @patch('os.listdir') # To control file "creation"
    @patch('os.path.join', side_effect=lambda *args: "/".join(args))
    @patch('os.remove')
    def test_fetch_subtitle_invalid_lang(self, mock_remove, mock_join, mock_listdir, MockYoutubeDL):
        # This test checks if yt-dlp (mocked) "downloads" nothing for an unavailable language,
        # leading to a "file not found" error, which is the expected behavior.
        mock_ydl_instance_pre = MagicMock()
        mock_ydl_instance_pre.extract_info.return_value = {"id": "test_id_bad_lang"}

        mock_ydl_instance_main = MagicMock()
        mock_ydl_instance_main.download.return_value = 0 # yt-dlp might "succeed" but create no file for bad lang

        MockYoutubeDL.return_value.__enter__.side_effect = [mock_ydl_instance_pre, mock_ydl_instance_main]
        mock_listdir.return_value = [] # Simulate yt-dlp creating no file for 'xx'

        track_info = {"lang_code": "xx", "is_asr": False, "name": "NonExistent"} # Invalid language
        body = {"video_url": "http://example.com/bad_lang_video", "track_info": track_info}

        status, response = self._simulate_post_request(GetSubtitlesHandler, body)

        self.assertEqual(status, 500)
        self.assertIn("error", response)
        self.assertTrue("Subtitle file for language 'xx' not found" in response["error"])


if __name__ == '__main__':
    # Mock tempfile.TemporaryDirectory for tests
    # This is a simple mock. More sophisticated mocking might be needed if its behavior is complexly used.
    with patch('tempfile.TemporaryDirectory') as mock_temp_dir:
        mock_temp_dir.return_value.__enter__.return_value = "/temp_dir_mock" # Dummy path
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
