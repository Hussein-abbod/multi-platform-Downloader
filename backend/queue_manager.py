"""
Async download queue with worker pool and task status tracking.
"""
import asyncio
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from datetime import datetime

from backend.models import TaskStatus

logger = logging.getLogger(__name__)

MAX_CONCURRENT = int(__import__("os").getenv("MAX_CONCURRENT_DOWNLOADS", "3"))


class DownloadTask:
    def __init__(self, task_id: str, url: str, quality: str, fmt: str):
        self.task_id = task_id
        self.url = url
        self.quality = quality
        self.fmt = fmt
        self.status: TaskStatus = TaskStatus.QUEUED
        self.progress: float = 0.0
        self.filename: Optional[str] = None
        self.filepath: Optional[str] = None
        self.download_url: Optional[str] = None
        self.error: Optional[str] = None
        self.cached: bool = False
        self.title: Optional[str] = None
        self.thumbnail: Optional[str] = None
        self.created_at: str = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "filename": self.filename,
            "download_url": self.download_url,
            "cached": self.cached,
            "error": self.error,
            "title": self.title,
            "thumbnail": self.thumbnail,
        }


class DownloadQueue:
    """
    Manages a queue of download tasks with a bounded thread pool executor.
    Workers pick tasks off the asyncio.Queue and run downloads in threads.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: Dict[str, DownloadTask] = {}
        self._executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._progress_store: Dict[str, float] = {}
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        """Start background worker. Must be called after the event loop is running."""
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"Download queue started (max_concurrent={MAX_CONCURRENT})")

    async def stop(self):
        """Graceful shutdown."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)
        logger.info("Download queue stopped")

    async def _worker_loop(self):
        """Continuously pick tasks from the queue and dispatch them."""
        while True:
            task: DownloadTask = await self._queue.get()
            # Fire-and-forget with semaphore limiting concurrency
            asyncio.create_task(self._run_task(task))
            self._queue.task_done()

    async def _run_task(self, task: DownloadTask):
        """Execute a single download task inside the semaphore."""
        async with self._semaphore:
            task.status = TaskStatus.PROCESSING
            loop = asyncio.get_running_loop()
            try:
                # Import here to avoid circular imports
                from backend.downloader import download_media
                from backend.cache import cache_manager

                result = await loop.run_in_executor(
                    self._executor,
                    download_media,
                    task.url,
                    task.quality,
                    task.fmt,
                    task.task_id,
                    self._progress_store,
                )

                task.filename = result["filename"]
                task.filepath = result["filepath"]
                task.download_url = f"/api/file/{task.task_id}"
                task.title = result.get("title")
                task.thumbnail = result.get("thumbnail")
                task.progress = 100.0
                task.status = TaskStatus.DONE

                # Store in cache
                cache_manager.set(task.url, task.quality, task.fmt, {
                    "filepath": task.filepath,
                    "filename": task.filename,
                    "title": task.title,
                    "thumbnail": task.thumbnail,
                    "download_url": task.download_url,
                })
                logger.info(f"Task {task.task_id} completed: {task.filename}")

            except Exception as e:
                task.status = TaskStatus.ERROR
                task.error = str(e)
                task.progress = 0.0
                logger.error(f"Task {task.task_id} failed: {e}")

    def create_task(self, url: str, quality: str, fmt: str) -> DownloadTask:
        """Create a new task and add it to the queue."""
        task_id = str(uuid.uuid4())[:8]
        task = DownloadTask(task_id, url, quality, fmt)
        self._tasks[task_id] = task
        self._queue.put_nowait(task)
        logger.info(f"Task {task_id} queued (queue size: {self._queue.qsize()})")
        return task

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        task = self._tasks.get(task_id)
        if task:
            # Sync progress from live progress store
            live = self._progress_store.get(task_id)
            if live is not None:
                task.progress = live
        return task

    def get_queue_status(self) -> dict:
        active = sum(
            1 for t in self._tasks.values()
            if t.status == TaskStatus.PROCESSING
        )
        recent_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )[:10]
        return {
            "queue_length": self._queue.qsize(),
            "active_downloads": active,
            "max_concurrent": MAX_CONCURRENT,
            "tasks": [t.to_dict() for t in recent_tasks],
        }

    @property
    def all_tasks(self) -> Dict[str, DownloadTask]:
        return self._tasks


# Singleton instance
download_queue = DownloadQueue()
