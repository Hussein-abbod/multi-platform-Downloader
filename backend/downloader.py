"""
Core download logic using yt-dlp.
Handles format selection, progress hooks, and audio extraction.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Callable, Optional
import yt_dlp

from backend.utils import detect_platform, sanitize_filename

logger = logging.getLogger(__name__)

# App-wide settings from environment
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
FFMPEG_PATH = os.getenv("FFMPEG_LOCATION")

AUDIO_FORMAT = "bestaudio/best"


def get_video_info(url: str) -> Dict[str, Any]:
    """
    Fetch video metadata without downloading.
    Returns title, uploader, duration, thumbnail, available qualities.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "ffmpeg_location": FFMPEG_PATH,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    platform = detect_platform(url)

    # Extract available heights/widths from formats
    available_res = set()
    formats = info.get("formats", [])
    for fmt in formats:
        h = fmt.get("height")
        w = fmt.get("width")
        res = min(h, w) if h and w else (h or w)
        if res:
            available_res.add(res)

    # Map resolutions to quality labels
    quality_labels = []
    for label, min_res in [("2160p", 2160), ("1080p", 1080), ("720p", 720),
                          ("480p", 480), ("360p", 360), ("240p", 240)]:
        if any(r >= min_res * 0.8 for r in available_res):
            quality_labels.append(label)
    if not quality_labels:
        quality_labels = ["best"]
    else:
        quality_labels.insert(0, "best")

    return {
        "title": info.get("title", "Unknown"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "platform": platform,
        "formats": quality_labels,
        "description": (info.get("description") or "")[:200],
        "view_count": info.get("view_count"),
    }


def make_progress_hook(task_id: str, progress_store: Dict[str, float]) -> Callable:
    """Return a yt-dlp progress hook that updates the shared progress store."""
    def hook(d: Dict):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total and total > 0:
                pct = (downloaded / total) * 90  
                progress_store[task_id] = round(pct, 1)
        elif d["status"] == "finished":
            progress_store[task_id] = 95.0
    return hook


def download_media(
    url: str,
    quality: str,
    fmt: str,
    task_id: str,
    progress_store: Dict[str, float],
) -> Dict[str, Any]:
    """
    Download a video or audio file and return metadata about the result.
    This runs synchronously (call from a thread pool).
    """
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Build output template
    output_template = os.path.join(DOWNLOAD_DIR, f"{task_id}_%(title).80s.%(ext)s")

    # Build yt-dlp options
    ydl_opts: Dict[str, Any] = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [make_progress_hook(task_id, progress_store)],
        "merge_output_format": "mp4",
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [],
    }

    if fmt == "audio":
        ydl_opts["format"] = AUDIO_FORMAT
        ydl_opts["postprocessors"].append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        })
        # Override extension after post-processing
        expected_ext = "mp3"
    else:
        # Force H.264 (mp4) and AAC (m4a) for universal compatibility
        # YouTube often provides Opus audio by default which fails in standard players.
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ydl_opts["format_sort"] = ["vcodec:h264", "acodec:m4a"]
        expected_ext = "mp4"

    # Also embed thumbnail for video
    if fmt == "video":
        ydl_opts["postprocessors"].append({"key": "FFmpegMetadata"})

    actual_filepath: Optional[str] = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "download")

    # Locate the output file (yt-dlp may rename it)
    safe_title = sanitize_filename(title, max_length=80)
    for file in os.listdir(DOWNLOAD_DIR):
        if file.startswith(task_id):
            actual_filepath = os.path.join(DOWNLOAD_DIR, file)
            break

    if not actual_filepath or not os.path.exists(actual_filepath):
        raise FileNotFoundError(f"Download completed but file not found for task {task_id}")

    filename = os.path.basename(actual_filepath)
    progress_store[task_id] = 100.0

    return {
        "filepath": actual_filepath,
        "filename": filename,
        "title": title,
        "thumbnail": info.get("thumbnail"),
        "platform": detect_platform(url),
    }
