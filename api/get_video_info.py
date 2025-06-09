from http.server import BaseHTTPRequestHandler
import json
import sys
import os
from yt_dlp import YoutubeDL
from datetime import datetime

# Add the api directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Removed: from youtube_downloader import YouTubeSubtitleDownloader, format_metadata_header

class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler for getting video information and available subtitle tracks.
    """
    
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            video_url = data.get('video_url')
            if not video_url:
                self._send_error(400, "video_url is required")
                return

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': False, # We don't want yt-dlp to write subs to disk
                'writeautomaticsub': False, # We don't want yt-dlp to write auto subs to disk
                'listsubtitles': True, # Needed to get subtitle info
            }
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)

            if not info_dict:
                self._send_error(404, "Failed to fetch video information")
                return

            # Format metadata
            upload_date_str = info_dict.get('upload_date')
            publish_date = None
            if upload_date_str:
                try:
                    # Format YYYYMMDD to YYYY-MM-DD
                    publish_date = datetime.strptime(upload_date_str, '%Y%m%d').strftime('%Y-%m-%d')
                except ValueError:
                    publish_date = None # Or handle error as appropriate

            metadata = {
                "title": info_dict.get('title'),
                "channel": info_dict.get('channel'),
                "description": info_dict.get('description'),
                "url": info_dict.get('webpage_url'),
                "video_id": info_dict.get('id'),
                "view_count": info_dict.get('view_count'),
                "publish_date": publish_date
            }

            tracks = []
            # Process manual subtitles
            if info_dict.get('subtitles'):
                for lang_code, subs_list in info_dict['subtitles'].items():
                    for sub_info in subs_list:
                        if sub_info.get('ext') in ['srv1', 'srv2', 'srv3', 'ttml', 'vtt']: # Common subtitle formats
                            tracks.append({
                                "name": sub_info.get('name', lang_code), # Use name if available, else lang_code
                                "lang_code": lang_code,
                                "is_asr": False,
                                "url": f"fake_url_{lang_code}" # Fake URL as it's not used by frontend
                            })

            # Process automatic captions
            if info_dict.get('automatic_captions'):
                for lang_code, subs_list in info_dict['automatic_captions'].items():
                    for sub_info in subs_list:
                         if sub_info.get('ext') in ['srv1', 'srv2', 'srv3', 'ttml', 'vtt']:
                            tracks.append({
                                "name": f"{sub_info.get('name', lang_code)} (auto-generated)",
                                "lang_code": lang_code,
                                "is_asr": True,
                                "url": f"fake_url_{lang_code}_asr" # Fake URL
                            })
            
            if not tracks and not metadata.get("title"): # Check if any info was actually extracted
                 self._send_error(404, "No subtitles or video information found")
                 return

            # Prepare response
            response_data = {
                "metadata": metadata,
                "tracks": tracks
            }
            
            self._send_json_response(200, response_data)
            
        except ValueError as e:
            self._send_error(400, str(e))
        except Exception as e:
            # Log the full error for debugging on the server
            print(f"Internal server error: {str(e)}")
            import traceback
            traceback.print_exc()
            self._send_error(500, f"Internal server error: Failed to process video.")

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
