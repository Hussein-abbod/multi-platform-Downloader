# 🎬 StreamGrab — Multi-Platform Video Downloader

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)
![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A full-stack web application to download videos from YouTube, Instagram, Twitter/X, TikTok and 1000+ platforms in any quality — with a queue system and smart caching.**

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🌐 **Multi-Platform** | YouTube, Instagram, Twitter/X, TikTok, Facebook, Vimeo, Twitch, Reddit, 1000+ more |
| 🎯 **Quality Selection** | Best, 4K (2160p), 1080p, 720p, 480p, 360p, 240p |
| 🎵 **Audio Extraction** | Download as MP3 audio-only |
| ⚡ **Smart Cache** | MD5-keyed, file-backed cache with 24-hour TTL — same URL returns instantly |
| 📋 **Download Queue** | Async queue with up to 3 concurrent downloads + real-time progress |
| 📊 **Live Progress** | Real-time progress bar with polling |
| 🎨 **Modern UI** | Glassmorphism dark UI with animated gradient background |
| 📱 **Responsive** | Works on mobile and desktop |

---

## 🖥️ Tech Stack

- **Backend:** FastAPI (Python) + yt-dlp
- **Concurrency:** `asyncio.Queue` + `ThreadPoolExecutor`
- **Caching:** MD5-keyed JSON file cache with TTL
- **Frontend:** Vanilla HTML + CSS + JavaScript (no frameworks)
- **Video Processing:** ffmpeg (required by yt-dlp for best quality)

---

## 📋 Prerequisites

Before setting up this project, you need:

1. **Python 3.10 or newer** — [Download here](https://www.python.org/downloads/)
2. **ffmpeg** — required for merging video+audio streams and MP3 extraction

---

## 🔧 Installing ffmpeg

ffmpeg is required by yt-dlp to merge video and audio (for best quality) and to convert audio to MP3.

### Windows

**Option A — Winget (Recommended, easiest):**
```powershell
winget install Gyan.FFmpeg
```
Then restart your terminal.

**Option B — Manual:**
1. Go to [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Click **Windows** → **Windows builds from gyan.dev**
3. Download `ffmpeg-release-essentials.zip`
4. Extract it to a folder, e.g. `C:\ffmpeg`
5. Add `C:\ffmpeg\bin` to your **System PATH**:
   - Search for **"Edit the system environment variables"** in Start
   - Click **"Environment Variables"**
   - Under **System variables**, select `Path` → **Edit**
   - Click **New** → paste `C:\ffmpeg\bin`
   - Click **OK** on all dialogs
6. Restart your terminal and verify: `ffmpeg -version`

### macOS
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install ffmpeg -y
```

### Verify Installation
```bash
ffmpeg -version
```
You should see version information printed.

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/multi-platform-downloader.git
cd multi-platform-downloader
```

### 2. Create a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
```bash
# Copy the example file
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux

# Edit .env to change settings (optional — defaults work fine)
```

Available settings in `.env`:
```env
MAX_CONCURRENT_DOWNLOADS=3   # Max parallel downloads
CACHE_TTL_SECONDS=86400      # Cache lifetime (24h)
DOWNLOAD_DIR=downloads       # Where files are saved
CACHE_DIR=cache              # Cache storage location
HOST=0.0.0.0
PORT=8000
```

### 5. Run the Application
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open in Browser
```
http://localhost:8000
```

---

## 📂 Project Structure

```
multi-platform-downloader/
├── backend/
│   ├── __init__.py          # Python package marker
│   ├── main.py              # FastAPI app + all API routes
│   ├── downloader.py        # yt-dlp download logic & quality mapping
│   ├── queue_manager.py     # Async queue with worker pool
│   ├── cache.py             # MD5-keyed cache with TTL
│   ├── models.py            # Pydantic request/response models
│   └── utils.py             # Platform detection & helpers
├── frontend/
│   └── index.html           # Full UI (HTML + CSS + JS)
├── downloads/               # Downloaded files (auto-created)
├── cache/                   # Cache storage (auto-created)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔌 API Reference

All endpoints are prefixed with `/api`.

### `POST /api/info`
Fetch video metadata without downloading.

**Request:**
```json
{ "url": "https://www.youtube.com/watch?v=..." }
```
**Response:**
```json
{
  "success": true,
  "data": {
    "title": "Video Title",
    "uploader": "Channel Name",
    "duration": 213,
    "thumbnail": "https://...",
    "platform": "YouTube",
    "formats": ["best", "1080p", "720p", "480p"],
    "view_count": 1500000
  }
}
```

### `POST /api/download`
Submit a download job. Returns immediately with a `task_id`.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "1080p",
  "format": "video"
}
```
**Quality options:** `best`, `2160p`, `1080p`, `720p`, `480p`, `360p`, `240p`
**Format options:** `video`, `audio`

**Response (new job):**
```json
{ "success": true, "cached": false, "task_id": "a1b2c3d4", "status": "queued" }
```
**Response (cached):**
```json
{ "success": true, "cached": true, "task_id": "cached", "status": "done", "download_url": "/api/file/..." }
```

### `GET /api/status/{task_id}`
Poll task progress (call every 1s while downloading).

**Response:**
```json
{
  "task_id": "a1b2c3d4",
  "status": "processing",
  "progress": 67.3,
  "filename": "a1b2c3d4_Video_Title.mp4",
  "download_url": "/api/file/a1b2c3d4"
}
```

### `GET /api/file/{task_id}`
Download the completed file (served as attachment).

### `GET /api/queue`
Get current queue status and recent tasks.

### `GET /api/health`
Health check with cache and queue stats.

---

## 💡 How It Works

```
User pastes URL
      │
      ▼
POST /api/download
      │
      ├─── Cache HIT? ──► Return instantly with file URL ✅
      │
      └─── Cache MISS
            │
            ▼
      asyncio.Queue (FIFO)
            │
            ▼
     Worker Pool (3 slots)
            │
            ▼
     yt-dlp downloads file
     (progress hooks → task status)
            │
            ▼
     Save to /downloads/
     Store in cache
            │
            ▼
     Frontend polls /api/status every 1s
            │
            ▼
     Status = "done" ──► Frontend shows download button ✅
```

---

## 🐛 Troubleshooting

**`ERROR: Postprocessing: ffprobe and ffmpeg not found`**
→ ffmpeg is not installed or not in PATH. Follow the [ffmpeg installation](#-installing-ffmpeg) section above.

**`yt_dlp.utils.DownloadError: ERROR: Sign in to confirm your age`**
→ The video requires age verification. yt-dlp cannot bypass this without cookies.

**`yt_dlp.utils.DownloadError: Private video`**
→ The video is private and cannot be downloaded.

**Downloads are slow**
→ This depends on your internet connection and the platform's server speed. The queue system ensures downloads don't interfere with each other.

**Instagram/TikTok returning errors**
→ These platforms frequently update their APIs. Run `pip install -U yt-dlp` to get the latest extractor updates.

---

## 🔄 Updating yt-dlp

yt-dlp releases frequent updates to keep up with platform changes. Update it with:
```bash
pip install -U yt-dlp
```

---

## 📄 License

MIT License — free for personal and commercial use.

---

<div align="center">

Made with ❤️ by **[Hussein Abbod](https://github.com/Hussein-abbod)**  
⭐ Star this repo if you found it useful!

</div>
