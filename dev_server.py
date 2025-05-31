#!/usr/bin/env python3
"""
Local development server for YTSubsDown
This script runs both the static file server and provides local API endpoints for testing
"""

import http.server
import socketserver
import json
import urllib.parse
import sys
import os
from pathlib import Path

# Add the api directory to Python path
api_dir = Path(__file__).parent / "api"
sys.path.insert(0, str(api_dir))

from youtube_downloader import YouTubeSubtitleDownloader, format_metadata_header

class YTSubsDownHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves static files and API endpoints"""
    
    def do_POST(self):
        """Handle POST requests to API endpoints"""
        if self.path == '/api/get_video_info':
            self.handle_get_video_info()
        elif self.path == '/api/get_subtitles':
            self.handle_get_subtitles()
        else:
            self.send_error(404, "Endpoint not found")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def handle_get_video_info(self):
        """Handle video info requests"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            video_url = data.get('video_url')
            if not video_url:
                self.send_json_error(400, "video_url is required")
                return
            
            downloader = YouTubeSubtitleDownloader(video_url)
            tracks = downloader.get_available_tracks()
            
            if not tracks:
                self.send_json_error(404, "No subtitles found for this video")
                return
            
            response_data = {
                "metadata": downloader.video_metadata,
                "tracks": tracks
            }
            
            self.send_json_response(200, response_data)
            
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            print(f"Error in get_video_info: {e}")
            self.send_json_error(500, f"Internal server error: {str(e)}")
    
    def handle_get_subtitles(self):
        """Handle subtitle content requests"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            video_url = data.get('video_url')
            track_info = data.get('track_info')
            include_metadata = data.get('include_metadata', True)
            
            if not video_url or not track_info:
                self.send_json_error(400, "video_url and track_info are required")
                return
            
            downloader = YouTubeSubtitleDownloader(video_url)
            
            # Ensure video info is populated
            if not downloader.video_metadata:
                tracks = downloader.get_available_tracks()
                if not tracks:
                    self.send_json_error(404, "Failed to fetch video information")
                    return
            
            srt_content = downloader.get_subtitle_srt(track_info)
            
            if srt_content is None:
                self.send_json_error(500, "Failed to fetch or parse subtitle content")
                return
            
            # Format final content
            if include_metadata and downloader.video_metadata:
                metadata_header = format_metadata_header(downloader.video_metadata)
                full_content = f"{metadata_header}\n{srt_content.strip()}\n```"
            else:
                full_content = srt_content.strip()
            
            response_data = {
                "subtitle_content": full_content,
                "track_info": track_info,
                "metadata": downloader.video_metadata if include_metadata else None
            }
            
            self.send_json_response(200, response_data)
            
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            print(f"Error in get_subtitles: {e}")
            self.send_json_error(500, f"Internal server error: {str(e)}")
    
    def send_json_response(self, status_code, data):
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_json_error(self, status_code, message):
        """Send error response"""
        self.send_json_response(status_code, {"error": message})
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

def main():
    port = 3000
    print(f"🚀 Starting YTSubsDown development server on http://localhost:{port}")
    print("📹 Features:")
    print("   • Static file serving for frontend")
    print("   • Local API endpoints for testing")
    print("   • CORS enabled for development")
    print("\n🛑 Press Ctrl+C to stop the server")
    
    try:
        with socketserver.TCPServer(("", port), YTSubsDownHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
