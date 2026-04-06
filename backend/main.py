"""
FastAPI application entry point.
Serves the API and static frontend files.
"""
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.models import (
    InfoRequest, DownloadRequest, TaskResult, QueueStatus, TaskStatus
)
from backend.downloader import get_video_info
from backend.cache import cache_manager
from backend.queue_manager import download_queue
from backend.utils import detect_platform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# Lifespan: start/stop background queue worker
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    download_queue.start()
    logger.info("✅ Download queue worker started")
    yield
    await download_queue.stop()
    logger.info("🛑 Download queue worker stopped")


# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title="Multi-Platform Video Downloader",
    description="Download videos from YouTube, Instagram, Twitter, TikTok and more.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve downloaded files
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "Multi-Platform Video Downloader API is running."})


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.post("/api/info")
async def fetch_info(req: InfoRequest):
    """
    Fetch video metadata (title, thumbnail, formats) without downloading.
    """
    try:
        info = get_video_info(req.url)
        return {"success": True, "data": info}
    except Exception as e:
        logger.error(f"Info fetch failed for {req.url}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
async def start_download(req: DownloadRequest):
    """
    Submit a download job. Returns immediately with a task_id.
    Checks cache first — if found, returns instantly with cached file info.
    """
    url = req.url
    quality = req.quality.value
    fmt = req.format.value

    # ── Cache check ──
    cached = cache_manager.get(url, quality, fmt)
    if cached:
        logger.info(f"Returning cached result for {url}")
        return {
            "success": True,
            "cached": True,
            "task_id": "cached",
            "status": TaskStatus.DONE,
            "download_url": cached.get("download_url"),
            "filename": cached.get("filename"),
            "title": cached.get("title"),
            "thumbnail": cached.get("thumbnail"),
        }

    # ── Enqueue ──
    task = download_queue.create_task(url, quality, fmt)
    return {
        "success": True,
        "cached": False,
        "task_id": task.task_id,
        "status": task.status,
    }


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """
    Poll the status and progress of a download task.
    """
    task = download_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "filename": task.filename,
        "download_url": task.download_url,
        "cached": task.cached,
        "error": task.error,
        "title": task.title,
        "thumbnail": task.thumbnail,
    }


@app.get("/api/file/{task_id}")
async def download_file(task_id: str):
    """
    Serve the downloaded file as an attachment.
    """
    task = download_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.DONE:
        raise HTTPException(status_code=400, detail="Download not yet complete")
    if not task.filepath or not os.path.exists(task.filepath):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=task.filepath,
        filename=task.filename,
        media_type="application/octet-stream",
    )


@app.get("/api/queue")
async def queue_status():
    """
    Return current queue length, active downloads, and recent task list.
    """
    return download_queue.get_queue_status()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "env": "production" if os.getenv("RENDER") else "development",
        "cache": cache_manager.stats(),
        "queue": {
            "size": download_queue._queue.qsize(),
            "max_concurrent": int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3")),
        },
    }
