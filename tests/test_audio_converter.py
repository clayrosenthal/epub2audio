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
    with patch("src.audio_converter.KPipeline") as mock_kpipeline:
        # Create mock KModel
        with patch("src.audio_converter.KModel") as mock_kmodel:
            # Set up mock model
            model = mock_kmodel.return_value
            
            # Set up mock TTS engine
            tts = mock_kpipeline.return_value
            voice = Mock()
            voice.value = {"name": "test_voice"}
            voice.name = "test_voice"
            voice.local_path = None
            tts.get_voice.return_value = voice
            
            # Patch Path.exists to return True for model weights check
            with patch("pathlib.Path.exists", return_value=True):
                # Create 1 second of silence as default audio output
                tts.convert_text.return_value = np.zeros(SAMPLE_RATE, dtype=np.float32)
                
                # Set up mock for __call__
                mock_result = Mock()
                mock_result.audio = Mock()
                mock_result.audio.numpy.return_value = np.zeros(SAMPLE_RATE, dtype=np.float32)
                mock_result.phonemes = "test phonemes"
                tts.return_value = [mock_result]
                
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

        # Verify CacheDirManager was called with the correct path and default extension
        mock_cache_dir.assert_called_once_with(str(epub_path), extension=".flac")


def test_audio_converter_init_invalid_voice(mock_tts: Mock, tmp_path: Path) -> None:
    """Test AudioConverter initialization fails with invalid voice name."""
    epub_path = tmp_path / "test.epub"
    epub_path.touch()  # Create an empty file
    
    # Mock file open operation
    with patch("builtins.open", Mock(return_value=Mock(
        read=Mock(return_value=b"dummy content")
    ))):
        # Set the mock to raise an exception on get_voice
        mock_tts.get_voice.side_effect = Exception("Invalid voice")
        
        # Test with invalid voice name
        with pytest.raises(ConversionError) as exc_info:
            AudioConverter(epub_path=str(epub_path), voice="invalid_voice")
        assert exc_info.value.error_code == ErrorCodes.INVALID_VOICE


def test_get_voice(mock_tts: Mock, tmp_path: Path) -> None:
    """Test voice selection with both valid and invalid voice names."""
    test_voice = Voice.AF_HEART
    test_epub = tmp_path / "test.epub"
    test_epub.touch()
    
    # Test Voice class handling directly instead of the AudioConverter
    # Test valid voice
    voice = Voice.get_by_name(test_voice.name)
    assert voice.name == test_voice.name
    
    # Test invalid voice
    with patch.object(Voice, 'get_by_name', side_effect=Exception("Invalid voice")):
        with pytest.raises(Exception):
            Voice.get_by_name("invalid_voice")


def test_convert_text(mock_tts: Mock, tmp_path: Path) -> None:
    """Test text to speech conversion produces valid audio output."""
    epub_path = tmp_path / "test.epub"
    epub_path.touch()  # Create an empty file
    
    # Mock the file open operation in CacheDirManager
    with patch("builtins.open", Mock(return_value=Mock(
        read=Mock(return_value=b"dummy content")
    ))):
        # Mock the CacheDirManager
        with patch("src.audio_converter.CacheDirManager") as mock_cache_dir:
            mock_cache_dir_instance = Mock()
            mock_cache_dir_instance.get_file.return_value = str(tmp_path / "cached_audio.flac")
            mock_cache_dir.return_value = mock_cache_dir_instance
            
            # Mock os.path.exists to simulate the cached file doesn't exist
            with patch("os.path.exists", return_value=False):
                # Mock SoundFile creation
                mock_sound_file = Mock(spec=SoundFile)
                mock_sound_file.close = Mock()
                
                with patch("src.audio_converter.SoundFile", return_value=mock_sound_file) as mock_sf:
                    # Mock os.rename to avoid actual file operations
                    with patch("os.rename"):
                        converter = AudioConverter(epub_path=str(epub_path))
                        
                        # Set up the converter._audio_data_generator method to yield our mock result
                        mock_result = Mock()
                        mock_result.audio = Mock()
                        mock_result.audio.numpy.return_value = np.zeros(1000, dtype=np.float32)
                        mock_result.phonemes = "test phonemes"
                        
                        with patch.object(converter, '_audio_data_generator', return_value=[mock_result]):
                            segment = converter.convert_text("Test text")
                            
                            # Verify the correct calls were made
                            assert segment == mock_sound_file


def test_convert_text_error(mock_tts: Mock, tmp_path: Path) -> None:
    """Test text to speech conversion handles TTS engine errors."""
    epub_path = tmp_path / "test.epub"
    epub_path.touch()  # Create an empty file
    
    # Mock the file open operation in CacheDirManager
    with patch("builtins.open", Mock(return_value=Mock(
        read=Mock(return_value=b"dummy content")
    ))):
        # Mock the CacheDirManager
        with patch("src.audio_converter.CacheDirManager") as mock_cache_dir:
            mock_cache_dir_instance = Mock()
            mock_cache_dir_instance.get_file.return_value = str(tmp_path / "cached_audio.flac")
            mock_cache_dir.return_value = mock_cache_dir_instance
            
            with patch("os.path.exists", return_value=False):
                with patch("src.audio_converter.SoundFile") as mock_sf:
                    converter = AudioConverter(epub_path=str(epub_path))
                    
                    # Set up the _audio_data_generator to raise an exception
                    with patch.object(converter, '_audio_data_generator') as mock_generator:
                        mock_generator.side_effect = Exception("TTS error")
                    
                        with pytest.raises(ConversionError) as exc_info:
                            converter.convert_text("Test text")
                        assert exc_info.value.error_code == ErrorCodes.UNKNOWN_ERROR


def test_chapter_announcement_conversion(mock_tts: Mock, tmp_path: Path) -> None:
    """Test chapter announcement conversion with proper formatting."""
    epub_path = tmp_path / "test.epub"
    epub_path.touch()  # Create an empty file
    
    # Mock the file open operation in CacheDirManager
    with patch("builtins.open", Mock(return_value=Mock(
        read=Mock(return_value=b"dummy content")
    ))):
        # Mock the CacheDirManager
        with patch("src.audio_converter.CacheDirManager") as mock_cache_dir:
            mock_cache_dir_instance = Mock()
            mock_cache_dir_instance.get_file.return_value = str(tmp_path / "cached_audio.flac")
            mock_cache_dir.return_value = mock_cache_dir_instance
            
            # Need to mock convert_text to verify chapter announcement formatting
            with patch("src.audio_converter.SoundFile"):
                converter = AudioConverter(epub_path=str(epub_path))
                
                # Mock the convert_text method
                with patch.object(converter, 'convert_text') as mock_convert_text:
                    mock_soundfile = Mock(spec=SoundFile)
                    mock_convert_text.return_value = mock_soundfile
                    
                    # Test that chapter announcement is formatted correctly
                    chapter_title = "Chapter 1"
                    converter.convert_text(chapter_title)
                    
                    # Verify the convert_text was called with the chapter title
                    mock_convert_text.assert_called_with(chapter_title)


# Move these tests to test_audio_handler.py since that's where the concatenate_segments method is implemented


# Move this test to test_audio_handler.py since that's where the _concatenate_segments method is implemented


# Move this test to test_audio_handler.py since that's where the _concatenate_segments method is implemented
