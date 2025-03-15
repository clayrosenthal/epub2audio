"""Unit tests for audio conversion module."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from soundfile import SoundFile

from src.audio_converter import AudioConverter
from src.config import SAMPLE_RATE, ErrorCodes
from src.helpers import ConversionError
from src.voices import Voice


@pytest.fixture
def mock_tts() -> Generator[Mock, None, None]:
    """Create a mock TTS engine with default test voice and audio output."""
    with patch("src.audio_converter.KPipeline") as mock:
        tts = mock.return_value
        voice = Mock()
        voice.value = {"name": "test_voice"}
        voice.name = "test_voice"
        tts.get_voice.return_value = voice

        # Create 1 second of silence as default audio output
        tts.convert_text.return_value = np.zeros(SAMPLE_RATE, dtype=np.float32)
        yield tts


def test_audio_converter_init(mock_tts: Mock, tmp_path: Path) -> None:
    """Test AudioConverter initialization with default parameters."""
    # Create a dummy EPUB file
    epub_path = tmp_path / "test.epub"
    epub_path.touch()  # Create an empty file

    # Mock the CacheDirManager to prevent it from actually trying to open/read the file
    with patch("src.audio_converter.CacheDirManager") as mock_cache_dir:
        mock_cache_dir_instance = Mock()
        mock_cache_dir.return_value = mock_cache_dir_instance

        converter = AudioConverter(epub_path=str(epub_path))
        assert converter is not None
        assert converter.speech_rate == 1.0

        # Verify CacheDirManager was called with the correct path
        mock_cache_dir.assert_called_once_with(str(epub_path))


def test_audio_converter_init_invalid_voice(mock_tts: Mock, tmp_path: Path) -> None:
    """Test AudioConverter initialization fails with invalid voice name."""
    mock_tts.get_voice.side_effect = Exception("Invalid voice")

    with pytest.raises(ConversionError) as exc_info:
        AudioConverter(epub_path=str(tmp_path / "test.epub"), voice="invalid_voice")
    assert exc_info.value.error_code == ErrorCodes.INVALID_VOICE


def test_get_voice(mock_tts: Mock, tmp_path: Path) -> None:
    """Test voice selection with both valid and invalid voice names."""
    test_voice = Voice.AF_HEART
    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"), voice=test_voice)
    voice = converter._get_voice(test_voice.name)
    assert voice.name == test_voice.name

    mock_tts.get_voice.side_effect = Exception("Invalid voice")
    with pytest.raises(ConversionError) as exc_info:
        converter._get_voice("invalid_voice")
    assert exc_info.value.error_code == ErrorCodes.INVALID_VOICE


def test_convert_text(mock_tts: Mock, tmp_path: Path) -> None:
    """Test text to speech conversion produces valid audio output."""
    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"))
    segment = converter.convert_text("Test text")

    assert isinstance(segment, SoundFile)
    assert segment.samplerate == SAMPLE_RATE
    assert segment.data.dtype == np.float32


def test_convert_text_error(mock_tts: Mock, tmp_path: Path) -> None:
    """Test text to speech conversion handles TTS engine errors."""
    mock_tts.synthesize.side_effect = Exception("TTS error")
    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"))

    with pytest.raises(ConversionError) as exc_info:
        converter.convert_text("Test text")
    assert exc_info.value.error_code == ErrorCodes.UNKNOWN_ERROR


def test_generate_chapter_announcement(mock_tts: Mock, tmp_path: Path) -> None:
    """Test chapter announcement generation with proper formatting."""
    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"))
    segment = converter.generate_chapter_announcement("Chapter 1")

    assert isinstance(segment, SoundFile)
    mock_tts.synthesize.assert_called_with(
        "Chapter: Chapter 1", voice=mock_tts.get_voice.return_value, rate=1.0
    )


def test_concatenate_segments() -> None:
    """Test audio segment concatenation with proper sample rate and data alignment."""
    # Create two 1-second test segments with different amplitudes
    data1 = np.ones(SAMPLE_RATE, dtype=np.float32)
    data2 = np.ones(SAMPLE_RATE, dtype=np.float32) * 2

    seg1 = SoundFile(data1, mode="w", samplerate=SAMPLE_RATE, channels=1)
    seg2 = SoundFile(data2, mode="w", samplerate=SAMPLE_RATE, channels=1)

    converter = AudioConverter(epub_path="test.epub")
    result = converter.concatenate_segments([seg1, seg2])

    assert isinstance(result, SoundFile)
    assert result.samplerate == SAMPLE_RATE
    assert result.duration == 2.0
    assert len(result.data) == 2 * SAMPLE_RATE
    assert np.array_equal(result.data[:SAMPLE_RATE], data1)
    assert np.array_equal(result.data[SAMPLE_RATE:], data2)


def test_concatenate_segments_empty(tmp_path: Path) -> None:
    """Test concatenation fails with empty segment list."""
    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"))
    with pytest.raises(ValueError):
        converter.concatenate_segments([])


def test_concatenate_segments_different_rates(tmp_path: Path) -> None:
    """Test concatenation fails with segments of different sample rates."""
    seg1 = SoundFile(np.ones(1000), mode="w", samplerate=1000, channels=1)
    seg2 = SoundFile(np.ones(2000), mode="w", samplerate=2000, channels=1)

    converter = AudioConverter(epub_path=str(tmp_path / "test.epub"))
    with pytest.raises(ValueError):
        converter.concatenate_segments([seg1, seg2])
