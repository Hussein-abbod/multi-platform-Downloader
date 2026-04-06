"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from enum import Enum


class VideoQuality(str, Enum):
    BEST = "best"
    Q2160 = "2160p"
    Q1080 = "1080p"
    Q720 = "720p"
    Q480 = "480p"
    Q360 = "360p"
    Q240 = "240p"


class DownloadFormat(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class InfoRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class DownloadRequest(BaseModel):
    url: str
    quality: VideoQuality = VideoQuality.BEST
    format: DownloadFormat = DownloadFormat.VIDEO

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class FormatInfo(BaseModel):
    format_id: str
    quality: str
    ext: str
    filesize: Optional[int] = None


class VideoInfo(BaseModel):
    title: str
    uploader: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    platform: str
    formats: List[str] = []
    description: Optional[str] = None
    view_count: Optional[int] = None


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    filename: Optional[str] = None
    download_url: Optional[str] = None
    cached: bool = False
    error: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None


class QueueStatus(BaseModel):
    queue_length: int
    active_downloads: int
    max_concurrent: int
    tasks: List[TaskResult] = []
