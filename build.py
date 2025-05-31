#!/usr/bin/env python3
"""
Production build script for YTSubsDown
This script prepares the application for deployment
"""

import os
import json
import shutil
from pathlib import Path

def optimize_for_production():
    """Optimize the application for production deployment"""
    
    print("🔧 Preparing YTSubsDown for production deployment...")
    
    # Ensure all required files exist
    required_files = [
        'public/index.html',
        'public/styles.css', 
        'public/script.js',
        'vercel.json',
        'requirements.txt',
        'api/get_video_info.py',
        'api/get_subtitles.py',
        'api/youtube_downloader.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    
    # Validate vercel.json
    try:
        with open('vercel.json', 'r') as f:
            vercel_config = json.load(f)
        print("✅ vercel.json is valid JSON")
    except json.JSONDecodeError:
        print("❌ vercel.json contains invalid JSON")
        return False
    
    # Check Python dependencies
    try:
        import requests
        print(f"✅ requests library available (v{requests.__version__})")
    except ImportError:
        print("❌ requests library not available")
        return False
    
    # Validate API functions
    try:
        import sys
        sys.path.insert(0, 'api')
        from youtube_downloader import YouTubeSubtitleDownloader
        print("✅ YouTube downloader module imports successfully")
    except ImportError as e:
        print(f"❌ Error importing YouTube downloader: {e}")
        return False
    
    # Check for common issues
    print("\n🔍 Checking for common deployment issues...")
    
    # Check CORS headers in API functions
    api_files = ['api/get_video_info.py', 'api/get_subtitles.py']
    for api_file in api_files:
        with open(api_file, 'r') as f:
            content = f.read()
            if 'Access-Control-Allow-Origin' not in content:
                print(f"⚠️  CORS headers might be missing in {api_file}")
            else:
                print(f"✅ CORS headers found in {api_file}")
    
    print("\n🚀 Production readiness check complete!")
    print("\nNext steps:")
    print("1. Push code to GitHub repository")
    print("2. Connect repository to Vercel")
    print("3. Deploy automatically or run: vercel --prod")
    
    return True

def create_deployment_summary():
    """Create a deployment summary"""
    
    summary = """
# YTSubsDown Deployment Summary

## 📁 Project Structure
- Frontend: HTML, CSS, JavaScript (static files)
- Backend: Python serverless functions in /api directory
- Package management: uv for Python, pnpm for Node.js (if needed)

## 🚀 Deployment Platform
- **Primary**: Vercel (recommended)
- **Alternative**: Netlify with serverless functions

## 🔧 Configuration Files
- `vercel.json`: Vercel deployment configuration
- `requirements.txt`: Python dependencies
- `pyproject.toml`: Python project configuration
- `package.json`: Node.js project metadata

## 🌐 API Endpoints
- `POST /api/get_video_info`: Get video metadata and subtitle tracks
- `POST /api/get_subtitles`: Get subtitle content for specific track

## 📋 Features
- ✅ YouTube video subtitle extraction
- ✅ Multiple language support
- ✅ Auto-generated subtitle detection
- ✅ Copy to clipboard functionality
- ✅ Download as SRT files
- ✅ Optional metadata inclusion
- ✅ Responsive design
- ✅ Error handling
- ✅ CORS support

## 🛠️ Local Development
```bash
# Start development server with API
python3 dev_server.py

# Or use npm scripts
npm run dev
```

## 📦 Dependencies
- **Python**: requests
- **Frontend**: Vanilla JavaScript (no external dependencies)
"""
    
    with open('DEPLOYMENT_SUMMARY.md', 'w') as f:
        f.write(summary)
    
    print("📄 Created DEPLOYMENT_SUMMARY.md")

if __name__ == "__main__":
    success = optimize_for_production()
    if success:
        create_deployment_summary()
        print("\n🎉 Ready for deployment!")
    else:
        print("\n❌ Please fix the issues above before deploying.")
        exit(1)
