from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import traceback

# Add the api directory to the Python path
sys.path.append(os.path.dirname(__file__))

from youtube_downloader import YouTubeSubtitleDownloader, format_metadata_header
from error_handler import handle_error, ErrorCategory, ErrorSeverity

class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler for getting subtitle content for a specific track.
    """
    
    def do_POST(self):
        detailed_error = None
        try:
            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            video_url = data.get('video_url')
            track_info = data.get('track_info')
            include_metadata = data.get('include_metadata', True)
            
            if not video_url:
                self._send_error(400, "video_url is required")
                return
            
            if not track_info:
                self._send_error(400, "track_info is required")
                return
            
            # Initialize downloader
            downloader = YouTubeSubtitleDownloader(video_url)
            
            # Ensure video info is populated (for metadata)
            if not downloader.video_metadata:
                tracks = downloader.get_available_tracks()
                if not tracks:
                    last_error = downloader.get_last_error()
                    error_msg = "Failed to fetch video information"
                    
                    if last_error:
                        self._send_detailed_error(404, error_msg, last_error)
                    else:
                        self._send_error(404, error_msg)
                    return
            
            # Get subtitle content
            srt_content = downloader.get_subtitle_srt(track_info)
            
            if srt_content is None:
                last_error = downloader.get_last_error()
                error_msg = "Failed to fetch or parse subtitle content"
                
                if last_error:
                    self._send_detailed_error(500, error_msg, last_error)
                else:
                    self._send_error(500, error_msg)
                return
            
            # Format final content
            if include_metadata and downloader.video_metadata:
                metadata_header = format_metadata_header(downloader.video_metadata)
                full_content = f"{metadata_header}\n{srt_content.strip()}\n```"
            else:
                full_content = srt_content.strip()
            
            # Prepare response
            response_data = {
                "subtitle_content": full_content,
                "track_info": track_info,
                "metadata": downloader.video_metadata if include_metadata else None
            }
            
            self._send_json_response(200, response_data)
            
        except ValueError as e:
            detailed_error = handle_error(e, {
                "video_url": data.get('video_url') if 'data' in locals() else None,
                "track_info": data.get('track_info') if 'data' in locals() else None
            })
            self._send_detailed_error(400, str(e), detailed_error.to_dict())
        except Exception as e:
            detailed_error = handle_error(e, {
                "video_url": data.get('video_url') if 'data' in locals() else None,
                "track_info": data.get('track_info') if 'data' in locals() else None,
                "endpoint": "get_subtitles"
            })
            self._send_detailed_error(500, f"Internal server error: {str(e)}", detailed_error.to_dict())
    
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
    
    def _send_detailed_error(self, status_code, message, detailed_error_info=None):
        """Send detailed error response with traceback information"""
        error_response = {
            "error": message,
            "detailed_error": detailed_error_info
        }
        self._send_json_response(status_code, error_response)
    
    def _send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
