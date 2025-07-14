"""Shared utilities for CLI operations"""

import asyncio
import os
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class ProgressTracker:
    """Track and display progress for long-running operations"""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description

    def update(self, count: int = 1):
        """Update progress by count"""
        self.current += count
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        print(
            f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%)",
            end="",
            flush=True,
        )

    def finish(self):
        """Finish progress tracking"""
        print()  # New line after progress


def ensure_directory(path: str) -> Path:
    """Ensure a directory exists, creating it if necessary"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def setup_gcs_environment(bucket_name: str | None = None) -> dict[str, str]:
    """Setup Google Cloud Storage environment variables"""
    env_updates: dict[str, str] = {}

    if bucket_name:
        env_updates["GCS_BUCKET_NAME"] = bucket_name
        os.environ["GCS_BUCKET_NAME"] = bucket_name

    # Check if GCS is enabled
    gcs_enabled = os.getenv("GCS_UPLOAD_ENABLED", "false").lower() == "true"
    if gcs_enabled and not os.getenv("GCS_BUCKET_NAME"):
        raise ValueError("GCS_BUCKET_NAME must be set when GCS_UPLOAD_ENABLED is true")

    return env_updates


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL"""
    import re

    url_pattern = re.compile(
        (
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$"
        ),
        re.IGNORECASE,
    )
    return url_pattern.match(url) is not None


class AsyncRunner:
    """Helper for running async operations in sync context"""

    @staticmethod
    def run(coro: Coroutine[Any, Any, T]) -> asyncio.Task[T] | T:
        """Run an async coroutine in a sync context"""
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            # If we're already in an async context, create a new task
            return asyncio.create_task(coro)
        else:
            # If we're in a sync context, run the coroutine
            return asyncio.run(coro)


def create_output_filename(
    base_name: str, extension: str, timestamp: bool = False
) -> str:
    """Create an output filename with optional timestamp"""
    from datetime import datetime

    if timestamp:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp_str}.{extension}"
    else:
        return f"{base_name}.{extension}"


def parse_id_range(range_str: str) -> tuple[int, int]:
    """Parse an ID range string like '1000-2000' into start and end integers"""
    if "-" in range_str:
        start, end = range_str.split("-", 1)
        return int(start), int(end)
    else:
        # Single ID
        id_val = int(range_str)
        return id_val, id_val
