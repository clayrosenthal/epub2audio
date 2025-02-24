"""Unit tests for audio conversion module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from soundfile import SoundFile
from src.audio_converter import AudioConverter
from src.helpers import ConversionError
from src.config import ErrorCodes, SAMPLE_RATE
from src.voices import Voice
@pytest.fixture
def mock_tts():
    """Create a mock TTS engine."""
    with patch('src.audio_converter.KPipeline') as mock:
        tts = mock.return_value
        voice = Mock()
        voice.value = {'name': 'test_voice'}
        voice.name = 'test_voice'
        tts.get_voice.return_value = voice
        tts.convert_text.return_value = np.zeros(SAMPLE_RATE, dtype=np.float32)  # 1 second of silence
        yield tts

def test_audio_converter_init(mock_tts):
    """Test AudioConverter initialization."""
    converter = AudioConverter()
    assert converter is not None
    assert converter.speech_rate == 1.0

def test_audio_converter_init_invalid_voice(mock_tts):
    """Test AudioConverter initialization with invalid voice."""
    mock_tts.get_voice.side_effect = Exception('Invalid voice')
    
    with pytest.raises(ConversionError) as exc_info:
        AudioConverter(voice='invalid_voice')
    assert exc_info.value.error_code == ErrorCodes.INVALID_VOICE

def test_get_voice(mock_tts):
    """Test voice selection."""
    test_voice = Voice.AF_HEART
    converter = AudioConverter(voice=test_voice)
    voice = converter._get_voice(test_voice.name)
    assert voice.name == test_voice.name
    
    mock_tts.get_voice.side_effect = Exception('Invalid voice')
    with pytest.raises(ConversionError) as exc_info:
        converter._get_voice('invalid_voice')
    assert exc_info.value.error_code == ErrorCodes.INVALID_VOICE

def test_convert_text(mock_tts):
    """Test text to speech conversion."""
    converter = AudioConverter()
    segment = converter.convert_text('Test text')
    
    assert isinstance(segment, SoundFile)
    assert segment.samplerate == SAMPLE_RATE
    # assert segment.duration == 1.0  # Our mock returns 1 second of audio
    assert segment.data.dtype == np.float32

def test_convert_text_error(mock_tts):
    """Test text to speech conversion error."""
    mock_tts.synthesize.side_effect = Exception('TTS error')
    converter = AudioConverter()
    
    with pytest.raises(ConversionError) as exc_info:
        converter.convert_text('Test text')
    assert exc_info.value.error_code == ErrorCodes.UNKNOWN_ERROR

def test_generate_chapter_announcement(mock_tts):
    """Test chapter announcement generation."""
    converter = AudioConverter()
    segment = converter.generate_chapter_announcement('Chapter 1')
    
    assert isinstance(segment, SoundFile)
    mock_tts.synthesize.assert_called_with(
        'Chapter: Chapter 1',
        voice=mock_tts.get_voice.return_value,
        rate=1.0
    )

def test_concatenate_segments():
    """Test audio segment concatenation."""
    # Create two 1-second segments
    data1 = np.ones(SAMPLE_RATE, dtype=np.float32)
    data2 = np.ones(SAMPLE_RATE, dtype=np.float32) * 2
    
    seg1 = SoundFile(data1, mode='w', samplerate=SAMPLE_RATE, channels=1)
    seg2 = SoundFile(data2, mode='w', samplerate=SAMPLE_RATE, channels=1)
    
    result = AudioConverter.concatenate_segments([seg1, seg2])
    
    assert isinstance(result, SoundFile)
    assert result.samplerate == SAMPLE_RATE
    assert result.duration == 2.0
    assert len(result.data) == 2 * SAMPLE_RATE
    assert np.array_equal(result.data[:SAMPLE_RATE], data1)
    assert np.array_equal(result.data[SAMPLE_RATE:], data2)

def test_concatenate_segments_empty():
    """Test concatenation with empty list."""
    with pytest.raises(ValueError):
        AudioConverter.concatenate_segments([])

def test_concatenate_segments_different_rates():
    """Test concatenation with different sample rates."""
    seg1 = SoundFile(np.ones(1000), mode='w', samplerate=1000, channels=1)
    seg2 = SoundFile(np.ones(2000), mode='w', samplerate=2000, channels=1)
    
    with pytest.raises(ValueError):
        AudioConverter.concatenate_segments([seg1, seg2]) 