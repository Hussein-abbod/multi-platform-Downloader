"""
Utility helpers: platform detection, filename sanitization, etc.
"""
import re
import os
from urllib.parse import urlparse


PLATFORM_PATTERNS = {
    "YouTube":    [r"youtube\.com", r"youtu\.be"],
    "Instagram":  [r"instagram\.com"],
    "Twitter":    [r"twitter\.com", r"x\.com"],
    "TikTok":     [r"tiktok\.com", r"vm\.tiktok\.com"],
    "Facebook":   [r"facebook\.com", r"fb\.watch"],
    "Reddit":     [r"reddit\.com", r"v\.redd\.it"],
    "Twitch":     [r"twitch\.tv"],
    "Vimeo":      [r"vimeo\.com"],
    "Dailymotion":[r"dailymotion\.com"],
}

PLATFORM_ICONS = {
    "YouTube":    "🎬",
    "Instagram":  "📷",
    "Twitter":    "🐦",
    "TikTok":     "🎵",
    "Facebook":   "👥",
    "Reddit":     "🤖",
    "Twitch":     "🟣",
    "Vimeo":      "🎥",
    "Dailymotion":"📹",
    "Unknown":    "🌐",
}


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to."""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform
    return "Unknown"


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Remove unsafe characters from filenames."""
    # Remove characters not safe for filenames
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple spaces/underscores
    name = re.sub(r"[\s_]+", "_", name).strip("_")
    # Truncate
    return name[:max_length] if len(name) > max_length else name


def format_duration(seconds: int) -> str:
    """Convert seconds to HH:MM:SS or MM:SS."""
    if not seconds:
        return "N/A"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_filesize(size_bytes: int) -> str:
    """Human-readable filesize."""
    if not size_bytes:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_view_count(count: int) -> str:
    """Human-readable view count."""
    if not count:
        return ""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M views"
    if count >= 1_000:
        return f"{count/1_000:.1f}K views"
    return f"{count} views"
