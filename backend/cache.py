"""
Cache manager: MD5-keyed, file-backed, in-memory dict with TTL.
"""
import json
import hashlib
import time
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = os.getenv("CACHE_DIR", "cache")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
CACHE_FILE = os.path.join(CACHE_DIR, "cache_index.json")


class CacheManager:
    def __init__(self):
        self._memory: Dict[str, Any] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load cache from JSON file on startup."""
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                # Filter out expired entries
                now = time.time()
                self._memory = {
                    k: v for k, v in data.items()
                    if now - v.get("created_at", 0) < CACHE_TTL
                }
                logger.info(f"Cache loaded: {len(self._memory)} valid entries")
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")
                self._memory = {}

    def _save_to_disk(self):
        """Persist cache to disk."""
        try:
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self._memory, f, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _make_key(self, url: str, quality: str, fmt: str) -> str:
        """Generate a unique cache key."""
        raw = f"{url}::{quality}::{fmt}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, url: str, quality: str, fmt: str) -> Optional[Dict]:
        """Return cached entry if it exists and is not expired."""
        key = self._make_key(url, quality, fmt)
        entry = self._memory.get(key)
        if not entry:
            return None

        age = time.time() - entry.get("created_at", 0)
        if age > CACHE_TTL:
            del self._memory[key]
            self._save_to_disk()
            return None

        # Verify the actual file still exists
        filepath = entry.get("filepath")
        if filepath and not os.path.exists(filepath):
            del self._memory[key]
            self._save_to_disk()
            return None

        logger.info(f"Cache HIT for key {key[:8]}...")
        return entry

    def set(self, url: str, quality: str, fmt: str, data: Dict):
        """Store entry in cache."""
        key = self._make_key(url, quality, fmt)
        self._memory[key] = {**data, "created_at": time.time()}
        self._save_to_disk()
        logger.info(f"Cache SET for key {key[:8]}...")

    def remove(self, url: str, quality: str, fmt: str):
        """Explicitly remove an entry from cache."""
        key = self._make_key(url, quality, fmt)
        if key in self._memory:
            del self._memory[key]
            self._save_to_disk()
            logger.info(f"Cache REMOVE for key {key[:8]}...")

    def cleanup_expired(self):
        """Remove expired entries."""
        now = time.time()
        before = len(self._memory)
        self._memory = {
            k: v for k, v in self._memory.items()
            if now - v.get("created_at", 0) < CACHE_TTL
        }
        removed = before - len(self._memory)
        if removed:
            self._save_to_disk()
            logger.info(f"Cache cleanup: removed {removed} expired entries")

    def stats(self) -> Dict:
        return {
            "total_entries": len(self._memory),
            "ttl_seconds": CACHE_TTL,
        }


# Singleton instance
cache_manager = CacheManager()
