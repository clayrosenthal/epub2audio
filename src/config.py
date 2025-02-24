"""Configuration settings for the EPUB to Audiobook converter."""

# Audio settings
SAMPLE_RATE = 24000  # Hz
DEFAULT_BITRATE = "192k"
DEFAULT_SPEECH_RATE = 1.0
AUDIO_FORMAT = "ogg"
AUDIO_CHANNELS = 1  # Mono

# File handling
DEFAULT_OUTPUT_DIR = "./audiobooks"
TEMP_DIR = ".epub2audio_"

# Progress reporting
PROGRESS_UPDATE_INTERVAL = 0.5  # seconds

# Error codes
class ErrorCodes:
    SUCCESS = 0
    INVALID_EPUB = 1
    INVALID_VOICE = 2
    FILESYSTEM_ERROR = 3
    DISK_SPACE_ERROR = 4
    UNKNOWN_ERROR = 99

# Warning types
class WarningTypes:
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