# YTSubsDown - YouTube Subtitle Downloader

A beautiful, modern web application for extracting and downloading subtitles from YouTube videos.

## Features

- 🎥 Extract subtitles from any YouTube video
- 🌍 Support for multiple languages and auto-generated subtitles
- 📋 Copy to clipboard functionality
- 💾 Download as SRT files
- 📝 Optional metadata inclusion
- 🎨 Beautiful, responsive design
- ⚡ Fast and lightweight

## Usage

1. Paste a YouTube video URL
2. Select your preferred subtitle track
3. Choose to copy to clipboard or download as SRT file
4. Optionally include video metadata in the output

## Deployment

This application is designed to be deployed on Vercel:

1. Connect your GitHub repository to Vercel
2. Deploy automatically - Vercel will handle both the frontend and Python API functions
3. The app will be available at your Vercel domain

## Local Development

### Prerequisites

- Python 3.9+ with `uv` package manager
- Modern web browser

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ytsubsdown

# Install Python dependencies using uv
uv sync

# Start development server with API endpoints
python dev_server.py
# OR use the npm script
npm run dev

# For simple static file serving only (no API functionality)
npm run dev:simple
```

Visit `http://localhost:3000` to use the application locally.

### Development Features

The `dev_server.py` provides:
- Static file serving for the frontend
- Local API endpoints that mirror the Vercel functions
- CORS support for development
- Real-time testing without deployment

## Deployment to Vercel

### Automatic Deployment

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Vercel will automatically detect the configuration and deploy

### Manual Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to production
npm run deploy
# OR
vercel --prod
```

### Environment Setup

The application requires no environment variables - it works out of the box!

## API Endpoints

- `POST /api/get_video_info` - Get video metadata and available subtitle tracks
- `POST /api/get_subtitles` - Get subtitle content for a specific track

## Technology Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Python with Vercel serverless functions
- **Deployment**: Vercel
- **Package Management**: uv (Python), pnpm (if needed for JS packages)

## License

GPL-3.0 License - see LICENSE file for details
