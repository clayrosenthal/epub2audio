"""Configuration settings for the EPUB to Audiobook converter."""

import sys
from os import getenv
from pathlib import Path

from loguru import logger

# Set up logging
logger.remove(0)
DEFAULT_LOGGER_ID = logger.add(sys.stderr, level="INFO")

# Audio settings
SAMPLE_RATE = 24000  # Hz
DEFAULT_BITRATE = "192k"
DEFAULT_SPEECH_RATE = 1.0
AUDIO_FORMAT = "ogg"
AUDIO_CHANNELS = 1  # Mono

# File handling
DEFAULT_OUTPUT = "audiobook.ogg"
CACHE_DIR = Path(getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "epub2audio"

# Progress reporting
PROGRESS_UPDATE_INTERVAL = 0.5  # seconds

KOKORO_PATHS = {
    "config": getenv("KOKORO_CONFIG_PATH", "packages/kokoro-weights/config.json"),
    "model_weight": getenv(
        "KOKORO_MODEL_WEIGHT_PATH", "packages/kokoro-weights/kokoro-v1_0.pth"
    ),
    "voice_weights": getenv(
        "KOKORO_VOICE_WEIGHTS_PATH", "packages/kokoro-weights/voices"
    ),
}


# Error codes
class ErrorCodes:
    """Error codes for the EPUB to Audiobook converter."""

    SUCCESS = 0
    INVALID_EPUB = 1
    INVALID_VOICE = 2
    FILESYSTEM_ERROR = 3
    DISK_SPACE_ERROR = 4
    UNKNOWN_ERROR = 99


# Warning types
class WarningTypes:
    """Warning types for the EPUB to Audiobook converter."""

    NON_TEXT_ELEMENT = "non_text_element"
    UNSUPPORTED_METADATA = "unsupported_metadata"
    FORMATTING_ISSUE = "formatting_issue"


# Metadata fields to preserve
METADATA_FIELDS = [
    "title",
    "creator",
    "date",
    "identifier",
    "language",
    "publisher",
    "description",
]
