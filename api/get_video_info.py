from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add the api directory to the Python path
sys.path.append(os.path.dirname(__file__))

from youtube_downloader import YouTubeSubtitleDownloader, format_metadata_header

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
            
            # Initialize downloader and get video info
            downloader = YouTubeSubtitleDownloader(video_url)
            tracks = downloader.get_available_tracks()
            
            if not tracks:
                self._send_error(404, "No subtitles found for this video or failed to fetch video information")
                return
            
            # Prepare response
            response_data = {
                "metadata": downloader.video_metadata,
                "tracks": tracks
            }
            
            self._send_json_response(200, response_data)
            
        except ValueError as e:
            self._send_error(400, str(e))
        except Exception as e:
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
