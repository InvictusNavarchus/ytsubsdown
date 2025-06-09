from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import json
from http.server import BaseHTTPRequestHandler
from yt_dlp import YoutubeDL
from datetime import datetime
import tempfile

# Add the api directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Removed: from youtube_downloader import YouTubeSubtitleDownloader, format_metadata_header

class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler for getting subtitle content for a specific track.
    """
    
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            video_url = data.get('video_url')
            track_info = data.get('track_info') # Expected: {"lang_code": "en", "is_asr": False, "name": "English"}
            include_metadata = data.get('include_metadata', True)

            if not video_url:
                self._send_error(400, "video_url is required")
                return
            
            if not track_info or 'lang_code' not in track_info or 'is_asr' not in track_info:
                self._send_error(400, "track_info with lang_code and is_asr is required")
                return

            lang_code = track_info['lang_code']
            is_asr = track_info['is_asr']
            
            video_metadata = None
            srt_content = None
            video_id = None # To help predict filename

            # Fetch video ID first to predict subtitle filename
            try:
                with YoutubeDL({'quiet': True, 'skip_download': True, 'no_warnings': True}) as ydl:
                    pre_info = ydl.extract_info(video_url, download=False)
                    video_id = pre_info.get('id') if pre_info else None
                if not video_id:
                    self._send_error(500, "Failed to extract video ID.")
                    return
            except Exception as e:
                self._send_error(500, f"Error fetching video ID: {str(e)}")
                return

            # Use a temporary directory to store subtitle files
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts_subs = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'writesubtitles': not is_asr,
                    'writeautomaticsub': is_asr,
                    'subtitleslangs': [lang_code],
                    'subtitlesformat': 'srt',
                    'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'), # Save to temp dir
                }

                try:
                    with YoutubeDL(ydl_opts_subs) as ydl:
                        ydl.download([video_url])

                    # Expected filename: VIDEO_ID.LANG_CODE.srt (yt-dlp might put full lang name)
                    # We need to find the actual file name as yt-dlp might use the full language name.
                    # e.g. for 'en', it might be 'video_id.en.srt' or 'video_id.English.srt'
                    # For asr, it might be 'video_id.en.asr.srt'

                    # Let's list files and find the one that matches video_id and lang_code
                    found_sub_file = None
                    for f in os.listdir(tmpdir):
                        # yt-dlp filename pattern can be complex, e.g., title.lang.srt, id.lang.srt
                        # A simpler check for now, assuming it contains video_id and lang_code
                        # and ends with .srt
                        if video_id in f and f.endswith(f".{lang_code}.srt"):
                             found_sub_file = f
                             break

                    if not found_sub_file and is_asr: # try auto-caption naming convention
                         for f in os.listdir(tmpdir):
                            if video_id in f and f.endswith(f".{lang_code}.asr.srt"): # yt-dlp might add .asr
                                found_sub_file = f
                                break

                    if not found_sub_file: # Fallback: try to find first .srt file if specific name fails
                        for f in os.listdir(tmpdir):
                            if f.endswith(".srt"):
                                found_sub_file = f
                                break

                    if found_sub_file:
                        subtitle_file_path = os.path.join(tmpdir, found_sub_file)
                        with open(subtitle_file_path, 'r', encoding='utf-8') as f:
                            srt_content = f.read()
                    else:
                        self._send_error(500, f"Subtitle file for language '{lang_code}' not found in {tmpdir}. Files: {os.listdir(tmpdir)}")
                        return

                except Exception as e:
                    self._send_error(500, f"Failed to download or read subtitles: {str(e)}")
                    return
            
            if srt_content is None:
                 self._send_error(500, "Failed to fetch or parse subtitle content")
                 return

            if include_metadata:
                try:
                    with YoutubeDL({'quiet': True, 'skip_download': True, 'no_warnings': True}) as ydl:
                        info_dict = ydl.extract_info(video_url, download=False)

                    upload_date_str = info_dict.get('upload_date')
                    publish_date = None
                    if upload_date_str:
                        try:
                            publish_date = datetime.strptime(upload_date_str, '%Y%m%d').strftime('%Y-%m-%d')
                        except ValueError:
                            publish_date = None

                    video_metadata = {
                        "title": info_dict.get('title'),
                        "channel": info_dict.get('channel', info_dict.get('uploader')),
                        "description": info_dict.get('description'),
                        "url": info_dict.get('webpage_url'),
                        "video_id": info_dict.get('id'),
                        "view_count": info_dict.get('view_count'),
                        "publish_date": publish_date
                    }

                    # Construct metadata header
                    header_lines = [
                        f"```text",
                        f"Title: {video_metadata.get('title', 'N/A')}",
                        f"Channel: {video_metadata.get('channel', 'N/A')}",
                        f"Publish Date: {video_metadata.get('publish_date', 'N/A')}",
                        f"Views: {video_metadata.get('view_count', 'N/A')}",
                        f"Video URL: {video_metadata.get('url', 'N/A')}",
                        # Description can be long, consider if it should be here or just in metadata object
                        # f"Description: {video_metadata.get('description', 'N/A')[:200]}...",
                    ]
                    metadata_header = "\n".join(header_lines)
                    srt_content = f"{metadata_header}\n\n{srt_content.strip()}\n```"

                except Exception as e:
                    # If metadata fetch fails, proceed without it but log error
                    print(f"Error fetching metadata: {str(e)}")
                    # Fallback to just srt_content if metadata fails
                    srt_content = srt_content.strip()
            else:
                srt_content = srt_content.strip()

            response_data = {
                "subtitle_content": srt_content,
                "track_info": track_info, # Echo back the track_info used
                "metadata": video_metadata if include_metadata else None
            }
            
            self._send_json_response(200, response_data)

        except ValueError as e: # For json.loads errors or similar
            self._send_error(400, str(e))
        except Exception as e:
            # Log the full error for debugging on the server
            print(f"Internal server error in POST: {str(e)}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_headers()
        self.end_headers()
    
    def _send_json_response(self, status_code, data):
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error(self, status_code, message):
        """Send error response"""
        self._send_json_response(status_code, {"error": message})
    
    def _send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
