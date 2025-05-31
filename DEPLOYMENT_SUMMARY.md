
# TubeScribe Deployment Summary

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
