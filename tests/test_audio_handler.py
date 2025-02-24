"""Unit tests for audio file handling module."""

import pytest
from unittest.mock import Mock, patch
import numpy as np
from mutagen.oggvorbis import OggVorbis
from src.audio_handler import AudioHandler
from src.epub_processor import BookMetadata
from src.helpers import ConversionError
from src.config import ErrorCodes
from soundfile import SoundFile

@pytest.fixture
def sample_metadata():
    """Create sample book metadata."""
    return BookMetadata(
        title='Test Book',
        creator='Test Author',
        date='2025',
        identifier='id123',
        language='en',
        publisher='Test Publisher',
        description='Test Description'
    )

@pytest.fixture
def audio_handler(tmp_path, sample_metadata):
    """Create an AudioHandler instance."""
    output_path = str(tmp_path / 'test.ogg')
    return AudioHandler(output_path, sample_metadata)

def test_audio_handler_init(audio_handler, sample_metadata):
    """Test AudioHandler initialization."""
    assert audio_handler is not None
    assert audio_handler.metadata == sample_metadata
    assert audio_handler.chapter_markers == []

def test_add_chapter_marker(audio_handler):
    """Test adding chapter markers."""
    audio_handler.add_chapter_marker('Chapter 1', 0.0, 10.0)
    audio_handler.add_chapter_marker('Chapter 2', 10.0, 20.0)
    
    assert len(audio_handler.chapter_markers) == 2
    assert audio_handler.chapter_markers[0]['title'] == 'Chapter 1'
    assert audio_handler.chapter_markers[0]['start_time'] == 0.0
    assert audio_handler.chapter_markers[0]['end_time'] == 10.0
    assert audio_handler.chapter_markers[0]['start_time_str'] == '00:00:00.000'
    assert audio_handler.chapter_markers[0]['end_time_str'] == '00:00:10.000'

def test_write_metadata(audio_handler, sample_metadata):
    """Test writing metadata to audio file."""
    mock_audio_file = Mock(spec=OggVorbis)
    mock_audio_file.__setitem__ = Mock()
    
    audio_handler.add_chapter_marker('Chapter 1', 0.0, 10.0)
    audio_handler._write_metadata(mock_audio_file)
    
    # Check basic metadata
    mock_audio_file.__setitem__.assert_any_call('TITLE', sample_metadata.title)
    mock_audio_file.__setitem__.assert_any_call('ARTIST', sample_metadata.creator)
    mock_audio_file.__setitem__.assert_any_call('DATE', sample_metadata.date)
    mock_audio_file.__setitem__.assert_any_call('PUBLISHER', sample_metadata.publisher)
    mock_audio_file.__setitem__.assert_any_call('DESCRIPTION', sample_metadata.description)
    
    # Check chapter markers
    mock_audio_file.__setitem__.assert_any_call('CHAPTER000', 'Chapter 1')
    mock_audio_file.__setitem__.assert_any_call('CHAPTER000START', '00:00:00.000')
    mock_audio_file.__setitem__.assert_any_call('CHAPTER000END', '00:00:10.000')

def test_finalize_audio_file(audio_handler):
    """Test finalizing audio file."""
    # Create a mock audio segment
    data = np.zeros(1000, dtype=np.float32)
    segment = SoundFile(data=data, sample_rate=1000, duration=1.0)
    
    with patch('src.audio_handler.OggVorbis') as mock_ogg:
        mock_audio_file = Mock()
        mock_ogg.return_value = mock_audio_file
        
        with patch.object(segment, 'save_audio_segment') as mock_save:
            audio_handler.finalize_audio_file(segment)
            
            # Check if audio was saved
            mock_save.assert_called_once()
            
            # Check if metadata was written
            mock_audio_file.save.assert_called_once()

def test_finalize_audio_file_error(audio_handler):
    """Test error handling in finalize_audio_file."""
    data = np.zeros(1000, dtype=np.float32)
    segment = SoundFile(data=data, sample_rate=1000, duration=1.0)
    
    with patch.object(segment, 'save_audio_segment', side_effect=Exception('Save error')):
        with pytest.raises(ConversionError) as exc_info:
            audio_handler.finalize_audio_file(segment)
        assert exc_info.value.error_code == ErrorCodes.FILESYSTEM_ERROR

def test_total_chapters(audio_handler):
    """Test total chapters property."""
    assert audio_handler.total_chapters == 0
    
    audio_handler.add_chapter_marker('Chapter 1', 0.0, 10.0)
    audio_handler.add_chapter_marker('Chapter 2', 10.0, 20.0)
    
    assert audio_handler.total_chapters == 2

def test_total_duration(audio_handler):
    """Test total duration property."""
    assert audio_handler.total_duration == 0.0
    
    audio_handler.add_chapter_marker('Chapter 1', 0.0, 10.0)
    audio_handler.add_chapter_marker('Chapter 2', 10.0, 20.0)
    
    assert audio_handler.total_duration == 20.0 