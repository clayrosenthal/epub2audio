"""Unit tests for audio file handling module."""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from mutagen.oggvorbis import OggVorbis
from soundfile import SoundFile

from src.audio_handler import AudioHandler
from src.config import ErrorCodes
from src.epub_processor import BookMetadata
from src.helpers import ConversionError


@pytest.fixture
def sample_metadata() -> BookMetadata:
    """Create sample book metadata."""
    return BookMetadata(
        title="Test Book",
        creator="Test Author",
        date="2025",
        identifier="id123",
        language="en",
        publisher="Test Publisher",
        description="Test Description",
    )


@pytest.fixture
def audio_handler(tmp_path: Path, sample_metadata: BookMetadata) -> AudioHandler:
    """Create an AudioHandler instance."""
    output_path = str(tmp_path / "test.ogg")
    return AudioHandler(output_path, sample_metadata)


def test_audio_handler_init(
    audio_handler: AudioHandler, sample_metadata: BookMetadata
) -> None:
    """Test AudioHandler initialization."""
    assert audio_handler is not None
    assert audio_handler.metadata == sample_metadata
    assert audio_handler.chapter_markers == []
    assert audio_handler.total_chapters == 0
    assert audio_handler.total_duration == 0.0


def test_add_chapter_marker(audio_handler: AudioHandler) -> None:
    """Test adding chapter markers."""
    audio_handler.add_chapter_marker("Chapter 1", 0.0, 10.0)
    audio_handler.add_chapter_marker("Chapter 2", 10.0, 20.0)

    assert len(audio_handler.chapter_markers) == 2

    # Check first chapter marker
    first_chapter = audio_handler.chapter_markers[0]
    assert first_chapter.title == "Chapter 1"
    assert first_chapter.start_time == 0.0
    assert first_chapter.end_time == 10.0
    assert first_chapter.start_time_str == "00:00:00.000"
    assert first_chapter.end_time_str == "00:00:10.000"

    # Check second chapter marker
    second_chapter = audio_handler.chapter_markers[1]
    assert second_chapter.title == "Chapter 2"
    assert second_chapter.start_time == 10.0
    assert second_chapter.end_time == 20.0
    assert second_chapter.start_time_str == "00:00:10.000"
    assert second_chapter.end_time_str == "00:00:20.000"


def test_write_metadata(
    audio_handler: AudioHandler, sample_metadata: BookMetadata
) -> None:
    """Test writing metadata to audio file."""
    mock_audio_file = Mock(spec=OggVorbis)
    mock_audio_file.__setitem__ = Mock()

    audio_handler.add_chapter_marker("Chapter 1", 0.0, 10.0)
    audio_handler._write_metadata(mock_audio_file)

    # Check basic metadata
    mock_audio_file.__setitem__.assert_any_call("TITLE", sample_metadata.title)
    mock_audio_file.__setitem__.assert_any_call("ARTIST", sample_metadata.creator)
    mock_audio_file.__setitem__.assert_any_call("DATE", sample_metadata.date)
    mock_audio_file.__setitem__.assert_any_call("PUBLISHER", sample_metadata.publisher)
    mock_audio_file.__setitem__.assert_any_call(
        "DESCRIPTION", sample_metadata.description
    )

    # Check chapter markers
    mock_audio_file.__setitem__.assert_any_call("CHAPTER000", "Chapter 1")
    mock_audio_file.__setitem__.assert_any_call("CHAPTER000START", "00:00:00.000")
    mock_audio_file.__setitem__.assert_any_call("CHAPTER000END", "00:00:10.000")


def test_finalize_audio_file(audio_handler: AudioHandler, tmp_path: Path) -> None:
    """Test finalizing audio file."""
    # Create a test audio segment
    data = np.zeros(1000, dtype=np.float32)
    segment = SoundFile(
        str(tmp_path / "test_segment.ogg"),
        mode="w",
        samplerate=1000,
        channels=1,
        format="OGG",
        subtype="VORBIS",
    )
    segment.write(data)
    segment.close()

    # Reopen for reading
    segment = SoundFile(str(tmp_path / "test_segment.ogg"))

    with patch("src.audio_handler.OggVorbis") as mock_ogg:
        mock_audio_file = Mock()
        mock_ogg.return_value = mock_audio_file

        audio_handler.finalize_audio_file(segment)

        # Check if metadata was written
        mock_ogg.assert_called_once_with(audio_handler.output_path)
        mock_audio_file.save.assert_called_once()


def test_finalize_audio_file_error(audio_handler: AudioHandler, tmp_path: Path) -> None:
    """Test error handling in finalize_audio_file."""
    # Create a test audio segment
    data = np.zeros(1000, dtype=np.float32)
    segment = SoundFile(
        str(tmp_path / "test_segment.ogg"),
        mode="w",
        samplerate=1000,
        channels=1,
        format="OGG",
        subtype="VORBIS",
    )
    segment.write(data)
    segment.close()

    # Reopen for reading
    segment = SoundFile(str(tmp_path / "test_segment.ogg"))

    with patch("src.audio_handler.OggVorbis", side_effect=Exception("Save error")):
        with pytest.raises(ConversionError) as exc_info:
            audio_handler.finalize_audio_file(segment)
        assert exc_info.value.error_code == ErrorCodes.FILESYSTEM_ERROR


def test_total_chapters(audio_handler: AudioHandler) -> None:
    """Test total chapters property."""
    assert audio_handler.total_chapters == 0

    audio_handler.add_chapter_marker("Chapter 1", 0.0, 10.0)
    assert audio_handler.total_chapters == 1

    audio_handler.add_chapter_marker("Chapter 2", 10.0, 20.0)
    assert audio_handler.total_chapters == 2


def test_total_duration(audio_handler: AudioHandler) -> None:
    """Test total duration property."""
    assert audio_handler.total_duration == 0.0

    audio_handler.add_chapter_marker("Chapter 1", 0.0, 10.0)
    assert audio_handler.total_duration == 10.0

    audio_handler.add_chapter_marker("Chapter 2", 10.0, 20.0)
    assert audio_handler.total_duration == 20.0
