"""Utility functions and error handling for the EPUB to Audiobook converter."""

import os
import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar, Optional, Union

from loguru import logger
from soundfile import SoundFile  # type: ignore
from tqdm import tqdm  # type: ignore

from .config import CACHE_DIR, ErrorCodes

StrPath = Union[str, Path]


@dataclass
class ConversionWarning:
    """Class for storing warning information during conversion."""

    type: str
    message: str
    chapter: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class ConversionError(Exception):
    """Custom exception for conversion errors."""

    def __init__(self, message: str, error_code: int):
        """Initialize the ConversionError.

        Args:
            message: Error message
            error_code: Error code
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class AudioHandlerError(Exception):
    """Custom exception for audio handler errors."""

    def __init__(self, message: str, error_code: int):
        """Initialize the AudioHandlerError.

        Args:
            message: Error message
            error_code: Error code
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class CacheDirManager:
    """Manager for cache directories based on EPUB file hashes."""

    _cache_dirs: ClassVar[dict[str, Path]] = {}

    def __init__(self, epub_path: StrPath):
        """Initialize the temp directory manager for an EPUB file.

        Args:
            epub_path: Path to the EPUB file
        """
        with open(epub_path, "rb") as f:
            f_bytes = f.read()
            self.epub_hash = sha256(f_bytes).hexdigest()
        self.epub_path = epub_path
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        if self.epub_hash not in self._cache_dirs:
            cache_dir = CACHE_DIR / self.epub_hash
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_dirs[self.epub_hash] = cache_dir

    @property
    def cache_dir(self) -> str:
        """Get the path to the temporary directory.

        Returns:
            str: Path to the temporary directory
        """
        return str(self._cache_dirs[self.epub_hash])

    def get_file(self, data: str, suffix: str = ".ogg") -> str:
        """Get a temporary file name.

        Args:
            data: Data to hash
            suffix: File suffix

        Returns:
            str: Temporary file name
        """
        hash = sha256(data.encode()).hexdigest()
        return f"{self.cache_dir}/{hash}{suffix}"

    def cleanup(self) -> None:
        """Clean up the temporary directory."""
        if self.epub_hash in self._cache_dirs:
            try:
                for file in self._cache_dirs[self.epub_hash].iterdir():
                    file.unlink()
                self._cache_dirs[self.epub_hash].rmdir()
                del self._cache_dirs[self.epub_hash]
            except Exception as e:
                logger.warning(
                    f"Failed to clean up cache directory for {self.epub_path}: {e}"
                )

    @classmethod
    def cleanup_all(cls) -> None:
        """Clean up all temporary directories."""
        for cache_dir in list(cls._cache_dirs.values()):
            try:
                cache_dir.rmdir()
            except Exception as e:
                logger.warning(f"Failed to clean up cache directory: {e}")
        cls._cache_dirs.clear()


def check_disk_space(path: StrPath, required_bytes: int) -> bool:
    """Check if there's enough disk space available.

    Args:
        path: Directory path to check
        required_bytes: Required space in bytes

    Returns:
        bool: True if enough space is available

    Raises:
        ConversionError: If there isn't enough disk space
    """
    try:
        _, _, free = shutil.disk_usage(path)
        if free < required_bytes:
            raise ConversionError(
                f"Insufficient disk space. Need {required_bytes / 1024 / 1024:.1f}MB, "
                f"but only {free / 1024 / 1024:.1f}MB available",
                ErrorCodes.DISK_SPACE_ERROR,
            )
        return True
    except OSError as e:
        raise ConversionError(
            f"Failed to check disk space: {str(e)}", ErrorCodes.FILESYSTEM_ERROR
        ) from e


def create_progress_bar(total: int, desc: str, disable: bool = False) -> tqdm:
    """Create a progress bar for tracking conversion progress.

    Args:
        total: Total number of items
        desc: Description for the progress bar
        disable: Whether to disable the progress bar

    Returns:
        tqdm: Progress bar instance
    """
    return tqdm(total=total, desc=desc, unit="B", unit_scale=True, disable=disable)


def ensure_dir_exists(path: StrPath) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Raises:
        ConversionError: If directory creation fails
    """
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise ConversionError(
            f"Failed to create directory {path}: {str(e)}", ErrorCodes.FILESYSTEM_ERROR
        ) from e


def clean_filename(filename: str) -> str:
    """Clean a filename to ensure it's valid.

    Args:
        filename: Original filename

    Returns:
        str: Cleaned filename
    """
    # Replace invalid characters
    invalid_chars = ' <>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Ensure filename isn't too long
    max_length = 255
    name, ext = os.path.splitext(filename)
    if len(filename) > max_length:
        return name[: max_length - len(ext)] + ext

    return filename


def format_time(seconds: float) -> str:
    """Format time in seconds to a human-readable string.

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def get_duration(audio: SoundFile) -> float:
    """Get the duration of an audio file.

    Args:
        audio: Audio file object
    """
    return float(audio.frames / (audio.samplerate * audio.channels * 1.0))


def format_duration(seconds: float) -> str:
    """Display duration as smallest unit.

    Args:
        seconds (float): duration in seconds

    Returns:
            str: Formatted duration string
    """
    if seconds < 60:
        # Format as seconds (00:15.1)
        return f"00:{seconds:02f}"

    elif seconds < 3600:
        # Format as minutes:seconds (1:30)
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes:02d}:{remaining_seconds:02f}"

    else:
        # Format as hours:minutes:seconds (2:30:00)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}:{minutes:02d}:{remaining_seconds:02f}"
