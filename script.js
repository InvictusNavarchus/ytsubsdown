/**
 * YTSubsDown JavaScript functionality
 * Handles YouTube subtitle extraction and user interactions
 */

class YTSubsDown {
    constructor() {
        this.currentVideoData = null;
        this.currentSubtitleContent = null;
        this.selectedTrack = null;
        this.init();
    }

    /**
     * Initialize the application and bind event listeners
     */
    init() {
        this.bindEvents();
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        const fetchBtn = document.getElementById('fetchBtn');
        const copyBtn = document.getElementById('copyBtn');
        const downloadBtn = document.getElementById('downloadBtn');
        const videoUrlInput = document.getElementById('videoUrl');

        fetchBtn.addEventListener('click', () => this.handleFetchSubtitles());
        copyBtn.addEventListener('click', () => this.handleCopyToClipboard());
        downloadBtn.addEventListener('click', () => this.handleDownload());
        
        // Allow Enter key to trigger fetch
        videoUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleFetchSubtitles();
            }
        });

        // Auto-format YouTube URLs as user types
        videoUrlInput.addEventListener('input', (e) => {
            const url = e.target.value.trim();
            if (url && this.isValidYouTubeUrl(url)) {
                e.target.classList.remove('invalid');
                e.target.classList.add('valid');
            } else if (url.length > 10) {
                e.target.classList.add('invalid');
                e.target.classList.remove('valid');
            } else {
                e.target.classList.remove('invalid', 'valid');
            }
        });

        // Auto-hide error messages after a delay
        this.setupAutoHideError();
    }

    /**
     * Handle fetching subtitles from YouTube URL
     */
    async handleFetchSubtitles() {
        const videoUrl = document.getElementById('videoUrl').value.trim();
        
        if (!videoUrl) {
            this.showError('Please enter a YouTube URL');
            return;
        }

        if (!this.isValidYouTubeUrl(videoUrl)) {
            this.showError('Please enter a valid YouTube URL');
            return;
        }

        this.setLoading(true);
        this.hideError();
        this.hideResults();

        try {
            // First, get video info and available tracks
            const response = await fetch('/api/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ video_url: videoUrl })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch video information');
            }

            this.currentVideoData = data;
            this.displayVideoInfo(data.metadata);
            this.displaySubtitleTracks(data.tracks);

        } catch (error) {
            console.error('Error fetching video info:', error);
            this.showError(error.message || 'Failed to fetch video information');
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * Handle downloading subtitles for selected track
     */
    async handleDownloadSubtitles(trackInfo) {
        const includeMetadata = document.getElementById('includeMetadata').checked;

        try {
            const response = await fetch('/api/get_subtitles', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_url: this.currentVideoData.metadata.url,
                    track_info: trackInfo,
                    include_metadata: includeMetadata
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch subtitles');
            }

            this.currentSubtitleContent = data.subtitle_content;
            this.selectedTrack = trackInfo;
            this.displayResults(data.subtitle_content);
            this.showToast('Subtitles loaded successfully!');

        } catch (error) {
            console.error('Error fetching subtitles:', error);
            this.showError(error.message || 'Failed to fetch subtitles');
        }
    }

    /**
     * Handle copying subtitles to clipboard
     */
    async handleCopyToClipboard() {
        if (!this.currentSubtitleContent) {
            this.showError('No subtitle content to copy');
            return;
        }

        const copyBtn = document.getElementById('copyBtn');
        const textElement = copyBtn.querySelector('.btn-text') || copyBtn;
        const originalText = textElement.textContent;

        try {
            await navigator.clipboard.writeText(this.currentSubtitleContent);
            
            // Show success state
            copyBtn.classList.add('success');
            textElement.textContent = 'Copied!';
            
            this.showToast('Copied to clipboard!');
            
            // Reset button after 2 seconds
            setTimeout(() => {
                copyBtn.classList.remove('success');
                textElement.textContent = originalText;
            }, 2000);
            
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            this.showError('Failed to copy to clipboard');
        }
    }

    /**
     * Handle downloading subtitle file
     */
    handleDownload() {
        if (!this.currentSubtitleContent || !this.selectedTrack) {
            this.showError('No subtitle content to download');
            return;
        }

        const videoTitle = this.currentVideoData.metadata.title || 'video_subtitles';
        const langName = this.selectedTrack.name.replace(' (auto)', '_auto');
        const langCode = this.selectedTrack.lang_code;
        
        const filename = this.sanitizeFilename(`${videoTitle} - ${langName}.${langCode}.srt`);
        
        const blob = new Blob([this.currentSubtitleContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('File downloaded!');
    }

    /**
     * Display video information
     */
    displayVideoInfo(metadata) {
        document.getElementById('videoTitle').textContent = metadata.title;
        document.getElementById('videoChannel').textContent = `by ${metadata.channel}`;
        document.getElementById('videoInfo').classList.remove('hidden');
    }

    /**
     * Display available subtitle tracks
     */
    displaySubtitleTracks(tracks) {
        const tracksList = document.getElementById('tracksList');
        tracksList.innerHTML = '';

        tracks.forEach((track, index) => {
            const trackItem = document.createElement('div');
            trackItem.className = 'track-item';
            
            const trackId = `track-${index}`;
            const autoText = track.is_asr ? ' (auto-generated)' : '';
            
            trackItem.innerHTML = `
                <input type="radio" name="subtitle-track" id="${trackId}" value="${index}">
                <div class="track-info">
                    <div class="track-name">${track.name}${autoText}</div>
                    <div class="track-details">Language: ${track.lang_code}</div>
                </div>
            `;

            trackItem.addEventListener('click', () => {
                // Update radio button selection
                document.getElementById(trackId).checked = true;
                
                // Update visual selection
                document.querySelectorAll('.track-item').forEach(item => {
                    item.classList.remove('selected');
                });
                trackItem.classList.add('selected');
                
                // Download subtitles for selected track
                this.handleDownloadSubtitles(track);
            });

            tracksList.appendChild(trackItem);
        });

        document.getElementById('subtitleTracks').classList.remove('hidden');
    }

    /**
     * Display subtitle results
     */
    displayResults(content) {
        document.getElementById('subtitleContent').textContent = content;
        document.getElementById('resultSection').classList.remove('hidden');
    }

    /**
     * Hide all result sections
     */
    hideResults() {
        document.getElementById('videoInfo').classList.add('hidden');
        document.getElementById('subtitleTracks').classList.add('hidden');
        document.getElementById('resultSection').classList.add('hidden');
    }

    /**
     * Set loading state
     */
    setLoading(isLoading) {
        const fetchBtn = document.getElementById('fetchBtn');
        const btnText = fetchBtn.querySelector('.btn-text');
        const spinner = fetchBtn.querySelector('.spinner');

        if (isLoading) {
            fetchBtn.disabled = true;
            btnText.textContent = 'Fetching...';
            spinner.classList.remove('hidden');
        } else {
            fetchBtn.disabled = false;
            btnText.textContent = 'Get Subtitles';
            spinner.classList.add('hidden');
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        document.getElementById('errorText').textContent = message;
        document.getElementById('errorMessage').classList.remove('hidden');
    }

    /**
     * Hide error message
     */
    hideError() {
        document.getElementById('errorMessage').classList.add('hidden');
    }

    /**
     * Setup auto-hide for error messages
     */
    setupAutoHideError() {
        const errorMessage = document.getElementById('errorMessage');
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    if (!errorMessage.classList.contains('hidden')) {
                        setTimeout(() => {
                            errorMessage.classList.add('hidden');
                        }, 5000);
                    }
                }
            });
        });
        observer.observe(errorMessage, { attributes: true });
    }

    /**
     * Show toast notification
     */
    showToast(message) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');
        
        toastMessage.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    /**
     * Validate YouTube URL format
     */
    isValidYouTubeUrl(url) {
        const patterns = [
            /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)[a-zA-Z0-9_-]{11}/,
            /^https?:\/\/(www\.)?youtube\.com\/watch\?.*v=[a-zA-Z0-9_-]{11}/
        ];
        return patterns.some(pattern => pattern.test(url));
    }

    /**
     * Extract video ID from YouTube URL for validation
     */
    extractVideoId(url) {
        const patterns = [
            /(?:v=|\/)([0-9A-Za-z_-]{11}).*/,
            /(?:embed\/|youtu\.be\/)([0-9A-Za-z_-]{11})/
        ];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    /**
     * Sanitize filename for download
     */
    sanitizeFilename(name) {
        if (!name) return 'untitled.srt';
        
        // Remove invalid filename characters
        name = name.replace(/[<>:"/\\|?*]+/g, '_');
        // Replace multiple spaces with single space
        name = name.replace(/\s+/g, ' ').trim();
        // Limit length
        return name.substring(0, 200);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new YTSubsDown();
});
