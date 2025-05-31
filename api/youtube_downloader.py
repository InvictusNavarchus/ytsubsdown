import requests
import json
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
import logging
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('YTSubDownloader')

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to be used as a valid filename.
    Removes or replaces characters that are problematic in filenames
    across common operating systems.
    """
    if not name:
        return "untitled"
    # Remove characters that are invalid in Windows/Linux/Mac filenames
    name = re.sub(r'[<>:"/\\|?*]+', '_', name)
    # Replace multiple spaces with a single space and strip leading/trailing spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Limit length to avoid issues with max path length
    return name[:200]

def seconds_to_srt_time(seconds_float: float) -> str:
    """
    Converts a time in seconds (float) to SRT timestamp format (HH:MM:SS,mmm).
    """
    if seconds_float < 0:
        seconds_float = 0
        
    hours = int(seconds_float // 3600)
    minutes = int((seconds_float % 3600) // 60)
    secs = int(seconds_float % 60)
    milliseconds = int((seconds_float % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def format_metadata_header(metadata: dict) -> str:
    """
    Formats video metadata into a readable header string.
    """
    header_parts = ["[video]"]
    if metadata.get("title"):
        header_parts.append(f'title = "{metadata["title"]}"')
    if metadata.get("channel"):
        header_parts.append(f'channel = "{metadata["channel"]}"')
    if metadata.get("url"):
        header_parts.append(f'url = "{metadata["url"]}"')
    if metadata.get("description"):
        header_parts.append(f'description = "{metadata["description"]}"') 
    
    header_parts.append("\n[transcript]\n\n```")
    return "\n".join(header_parts)

class YouTubeSubtitleDownloader:
    """
    Handles fetching, parsing, and providing YouTube subtitles.
    """
    def __init__(self, video_url: str):
        self.video_url = video_url
        self.video_id = self._extract_video_id(video_url)
        if not self.video_id:
            logger.error(f"Could not extract video ID from URL: {video_url}")
            raise ValueError("Invalid YouTube URL or could not extract video ID.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        
        self.player_response = None
        self.video_metadata = {}
        self.available_tracks = []

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extracts the YouTube video ID from a URL using regex.
        """
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', 
            r'(?:embed\/|youtu\.be\/)([0-9A-Za-z_-]{11})' 
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                logger.debug(f"Extracted video ID: {video_id}")
                return video_id
        return None

    def _fetch_page_html(self) -> Optional[str]:
        """
        Fetches the HTML content of the YouTube video page.
        """
        try:
            response = self.session.get(self.video_url, timeout=15)
            response.raise_for_status()
            logger.debug(f"Successfully fetched HTML for {self.video_url} (status: {response.status_code})")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {self.video_url}: {e}")
            return None

    def _extract_yt_initial_player_response(self, html_content: str) -> Optional[dict]:
        """
        Extracts the ytInitialPlayerResponse JSON object from the page HTML.
        """
        patterns = [
            r"var ytInitialPlayerResponse\s*=\s*({.+?});(?:var meta|</script)",
            r"ytInitialPlayerResponse\s*=\s*({.+?});(?:var meta|</script)"
        ]
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                try:
                    json_data_str = match.group(1)
                    data = json.loads(json_data_str)
                    logger.debug("Successfully parsed ytInitialPlayerResponse.")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode ytInitialPlayerResponse JSON: {e}")
                    return None
        logger.warn("Could not find ytInitialPlayerResponse in page HTML using known patterns.")
        return None
        
    def _populate_video_info(self) -> bool:
        """
        Fetches video page HTML, extracts player_response, 
        then populates video metadata and available subtitle tracks.
        """
        logger.info(f"Fetching video information for ID: {self.video_id}")
        html_content = self._fetch_page_html()
        if not html_content:
            logger.error("Failed to fetch video page HTML.")
            return False

        self.player_response = self._extract_yt_initial_player_response(html_content)
        if not self.player_response:
            logger.error("Failed to extract ytInitialPlayerResponse.")
            return False

        # Extract video metadata
        video_details = self.player_response.get("videoDetails", {})
        microformat_renderer = self.player_response.get("microformat", {}).get("playerMicroformatRenderer", {})

        self.video_metadata = {
            "title": video_details.get("title") or microformat_renderer.get("title", {}).get("simpleText", "Unknown Title"),
            "channel": video_details.get("author") or microformat_renderer.get("ownerChannelName", "Unknown Channel"),
            "description": (video_details.get("shortDescription") or microformat_renderer.get("description", {}).get("simpleText", "")).split('\n')[0],
            "url": self.video_url,
            "video_id": self.video_id
        }
        logger.debug(f"Extracted metadata: Title='{self.video_metadata['title']}', Channel='{self.video_metadata['channel']}'")

        # Extract subtitle tracks
        captions_data = self.player_response.get("captions")
        if captions_data and "playerCaptionsTracklistRenderer" in captions_data:
            tracklist_renderer = captions_data["playerCaptionsTracklistRenderer"]
            caption_tracks = tracklist_renderer.get("captionTracks", [])
            
            for track in caption_tracks:
                try:
                    track_name = track.get("name", {}).get("simpleText", "Unknown Language")
                    base_url = track.get("baseUrl")
                    lang_code = track.get("languageCode", "unk")
                    is_asr = track.get("kind") == "asr"
                    
                    if not base_url:
                        logger.warn(f"Skipping track '{track_name}' due to missing baseUrl.")
                        continue

                    self.available_tracks.append({
                        "name": track_name,
                        "url": base_url,
                        "lang_code": lang_code,
                        "is_asr": is_asr
                    })
                except Exception as e:
                    logger.warn(f"Error processing a caption track: {e}")
            
            logger.info(f"Found {len(self.available_tracks)} subtitle track(s).")
        else:
            logger.warn("No caption tracks found in player response.")
        
        return True

    def get_available_tracks(self) -> List[dict]:
        """
        Returns a list of available subtitle tracks.
        """
        if not self.available_tracks and not self.player_response: 
            if not self._populate_video_info():
                return []
        return self.available_tracks

    def _fetch_subtitle_xml(self, track_url: str) -> Optional[str]:
        """
        Fetches the subtitle data from the given track URL.
        """
        try:
            response = self.session.get(track_url, timeout=10)
            response.raise_for_status()
            logger.debug(f"Successfully fetched subtitle XML from {track_url}")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching subtitle XML from {track_url}: {e}")
            return None

    def _parse_subtitle_xml_to_srt(self, xml_text: str) -> Optional[str]:
        """
        Parses subtitle XML/TTML content and converts it to SRT format.
        """
        try:
            xml_text = re.sub(r'xmlns="[^"]+"', '', xml_text, count=1)
            root = ET.fromstring(xml_text)
            srt_lines = []
            
            text_elements = root.findall(".//text")
            if not text_elements:
                text_elements = root.findall(".//p")

            for i, element in enumerate(text_elements):
                start_str = element.get("start") or element.get("begin")
                dur_str = element.get("dur")
                end_str = element.get("end")
                
                if start_str is None:
                    logger.warn(f"Skipping element without start time")
                    continue

                try:
                    start_sec = float(start_str)
                    if dur_str is not None:
                        end_sec = start_sec + float(dur_str)
                    elif end_str is not None:
                        end_sec = float(end_str)
                    else:
                        logger.warn(f"Skipping element without duration or end time")
                        continue
                except ValueError:
                    logger.warn(f"Could not parse time attributes for element")
                    continue
                
                raw_content_parts = []
                for part in element.itertext():
                    raw_content_parts.append(part)
                for br_element in element.findall('.//br'):
                    if br_element.tail:
                         raw_content_parts.append('\n' + br_element.tail.strip())
                    else:
                         raw_content_parts.append('\n')

                content = "".join(raw_content_parts).strip()
                content = re.sub(r'\n\s*\n', '\n', content) 

                if content:
                    srt_lines.append(str(i + 1))
                    srt_lines.append(f"{seconds_to_srt_time(start_sec)} --> {seconds_to_srt_time(end_sec)}")
                    srt_lines.append(content)
                    srt_lines.append("")
            
            if not srt_lines:
                logger.warn("No subtitle text segments found after parsing XML.")
                return ""

            logger.debug("Successfully parsed XML to SRT format.")
            return "\n".join(srt_lines)
        except ET.ParseError as e:
            logger.error(f"Error parsing subtitle XML: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during XML parsing: {e}")
            return None

    def get_subtitle_srt(self, track_info: dict) -> Optional[str]:
        """
        Fetches the subtitle XML for the given track and converts it to SRT format.
        """
        logger.info(f"Fetching subtitle: {track_info['name']} ({track_info['lang_code']})")
        xml_content = self._fetch_subtitle_xml(track_info['url'])
        if xml_content is None:
            logger.error("Failed to fetch subtitle XML content.")
            return None
        if not xml_content.strip():
            logger.warn("Fetched subtitle XML content is empty.")
            return ""

        srt_content = self._parse_subtitle_xml_to_srt(xml_content)
        return srt_content
