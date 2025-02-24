"""EPUB to Audiobook converter package."""

from .cli import main, process_epub
from .config import ErrorCodes, WarningTypes
from .epub_processor import EPUBProcessor, Chapter, BookMetadata
from .audio_converter import AudioConverter
from .audio_handler import AudioHandler
from .helpers import ConversionError, ConversionWarning

__version__ = '0.1.0'
__author__ = 'Clay Rosenthal'
__email__ = 'epub2audio@mail.clayrosenthal.me'

__all__ = [
    'main',
    'process_epub',
    'ErrorCodes',
    'WarningTypes',
    'EPUBProcessor',
    'Chapter',
    'BookMetadata',
    'AudioConverter',
    'AudioHandler',
    'ConversionError',
    'ConversionWarning',
] 