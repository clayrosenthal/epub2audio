"""Utility functions and error handling for the EPUB to Audiobook converter."""

import hashlib
import os
import shutil
import sys
from tempfile import TemporaryDirectory,NamedTemporaryFile
from typing import Optional, Dict, Any, ClassVar

from dataclasses import dataclass
from tqdm import tqdm
from soundfile import SoundFile

from .config import ErrorCodes, TEMP_DIR


from loguru import logger

# Set up logging
logger.add(sys.stdout, level="INFO")

@dataclass
class ConversionWarning:
    """Class for storing warning information during conversion."""
    type: str
    message: str
    chapter: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ConversionError(Exception):
    """Custom exception for conversion errors."""
    def __init__(self, message: str, error_code: int):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class AudioHandlerError(Exception):
    """Custom exception for audio handler errors."""
    def __init__(self, message: str, error_code: int):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class TempDirManager:
    """Manager for temporary directories based on EPUB file hashes."""
    
    _instances: ClassVar[Dict[str, str]] = {}
    _temp_dirs: ClassVar[Dict[str, TemporaryDirectory]] = {}
    
    def __init__(self, epub_path: str):
        """Initialize the temp directory manager for an EPUB file.
        
        Args:
            epub_path: Path to the EPUB file
        """
        with open(epub_path, 'rb') as f:
            self.epub_hash = hashlib.file_digest(f, 'sha256').hexdigest()
        self.epub_path = epub_path
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self) -> None:
        """Ensure the temporary directory exists."""
        if self.epub_hash not in self._instances:
            temp_dir = TemporaryDirectory(prefix=f"{TEMP_DIR}_{self.epub_hash}", delete=False)
            self._instances[self.epub_hash] = temp_dir.name
            self._temp_dirs[self.epub_hash] = temp_dir
    
    @property
    def tempdir(self) -> str:
        """Get the path to the temporary directory.
        
        Returns:
            str: Path to the temporary directory
        """
        return self._instances[self.epub_hash]
    
    def get_tempfile(self, suffix: str = '.ogg') -> str:
        """Get a temporary file name.
        
        Args:
            suffix: File suffix
            
        Returns:
            str: Temporary file name
        """
        return NamedTemporaryFile(delete=False, suffix=suffix, dir=self.tempdir).name
    
    def cleanup(self) -> None:
        """Clean up the temporary directory."""
        if self.epub_hash in self._temp_dirs:
            try:
                self._temp_dirs[self.epub_hash].cleanup()
                del self._temp_dirs[self.epub_hash]
                del self._instances[self.epub_hash]
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory for {self.epub_path}: {e}")
    
    @classmethod
    def cleanup_all(cls) -> None:
        """Clean up all temporary directories."""
        for temp_dir in list(cls._temp_dirs.values()):
            try:
                temp_dir.cleanup()
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")
        cls._temp_dirs.clear()
        cls._instances.clear()

def check_disk_space(path: str, required_bytes: int) -> bool:
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
        total, used, free = shutil.disk_usage(path)
        if free < required_bytes:
            raise ConversionError(
                f"Insufficient disk space. Need {required_bytes/1024/1024:.1f}MB, "
                f"but only {free/1024/1024:.1f}MB available",
                ErrorCodes.DISK_SPACE_ERROR
            )
        return True
    except OSError as e:
        raise ConversionError(
            f"Failed to check disk space: {str(e)}",
            ErrorCodes.FILESYSTEM_ERROR
        )

def create_progress_bar(total: int, desc: str, disable: bool = False) -> tqdm:
    """Create a progress bar for tracking conversion progress.
    
    Args:
        total: Total number of items
        desc: Description for the progress bar
        disable: Whether to disable the progress bar
    
    Returns:
        tqdm: Progress bar instance
    """
    return tqdm(
        total=total,
        desc=desc,
        unit='B',
        unit_scale=True,
        disable=disable
    )

def ensure_dir_exists(path: str) -> None:
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
            f"Failed to create directory {path}: {str(e)}",
            ErrorCodes.FILESYSTEM_ERROR
        )

def clean_filename(filename: str) -> str:
    """Clean a filename to ensure it's valid.
    
    Args:
        filename: Original filename
    
    Returns:
        str: Cleaned filename
    """
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename isn't too long
    max_length = 255
    name, ext = os.path.splitext(filename)
    if len(filename) > max_length:
        return name[:max_length-len(ext)] + ext
    
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
    return audio.frames / (audio.samplerate * audio.channels * 1.0)