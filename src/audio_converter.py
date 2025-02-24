"""Text-to-speech conversion using Kokoro."""

import os
from typing import List, Optional
import soundfile as sf
import numpy as np
from kokoro import KPipeline # Maybe I'll implement TextToSpeech, Voice
from dataclasses import dataclass

from .helpers import ConversionError, logger
from .config import (
    ErrorCodes,
    SAMPLE_RATE,
    TEMP_DIR
)
from .voices import Voice

@dataclass
class AudioSegment:
    """Class representing an audio segment."""
    data: np.ndarray
    sample_rate: int
    duration: float

class AudioConverter:
    """Class for converting text to speech using Kokoro."""
    
    def __init__(
        self,
        voice: str | Voice = Voice.AF_HEART,
        speech_rate: float = 1.0
    ):
        """Initialize the audio converter.
        
        Args:
            voice_name: Name of the voice to use
            speech_rate: Speech rate multiplier
        
        Raises:
            ConversionError: If the voice is invalid or TTS initialization fails
        """
        try:
            self.tts = KPipeline()
            if isinstance(voice, Voice):
                self.voice = voice
            else:
                self.voice = self._get_voice(voice)
            self.speech_rate = speech_rate
        except Exception as e:
            raise ConversionError(
                f"Failed to initialize TTS: {str(e)}",
                ErrorCodes.INVALID_VOICE
            )
    
    def _get_voice(self, voice_name: str) -> Voice:
        """Get a voice by name.
        
        Args:
            voice_name: Name of the voice to get
        
        Returns:
            Voice: The requested voice
        
        Raises:
            ConversionError: If the voice is invalid
        """
        try:
            return Voice.get_by_name(voice_name)
        except Exception as e:
            raise ConversionError(
                f"Invalid voice '{voice_name}'. Available voices: {', '.join(Voice.list_voices())}",
                ErrorCodes.INVALID_VOICE
            )
    
    def convert_text(self, text: str) -> AudioSegment:
        """Convert text to speech.
        
        Args:
            text: Text to convert
        
        Returns:
            AudioSegment: Converted audio
        """
        try:
            # Generate speech
            audio_data = self.tts.synthesize(
                text,
                voice=self.voice,
                rate=self.speech_rate
            )
            
            # Convert to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Calculate duration
            duration = len(audio_data) / SAMPLE_RATE
            
            return AudioSegment(
                data=audio_data,
                sample_rate=SAMPLE_RATE,
                duration=duration
            )
        
        except Exception as e:
            raise ConversionError(
                f"Failed to convert text to speech: {str(e)}",
                ErrorCodes.UNKNOWN_ERROR
            )
    
    def generate_chapter_announcement(self, chapter_title: str) -> AudioSegment:
        """Generate a chapter announcement.
        
        Args:
            chapter_title: Title of the chapter
        
        Returns:
            AudioSegment: Chapter announcement audio
        """
        announcement_text = f"Chapter: {chapter_title}"
        return self.convert_text(announcement_text)
    
    def save_audio_segment(
        self,
        segment: AudioSegment,
        output_path: str,
        temp: bool = False
    ) -> None:
        """Save an audio segment to a file.
        
        Args:
            segment: Audio segment to save
            output_path: Path to save to
            temp: Whether this is a temporary file
        """
        try:
            directory = TEMP_DIR if temp else os.path.dirname(output_path)
            os.makedirs(directory, exist_ok=True)
            
            sf.write(
                output_path,
                segment.data,
                segment.sample_rate,
                format='OGG',
                subtype='VORBIS'
            )
        except Exception as e:
            raise ConversionError(
                f"Failed to save audio file: {str(e)}",
                ErrorCodes.FILESYSTEM_ERROR
            )
    
    @staticmethod
    def concatenate_segments(segments: List[AudioSegment]) -> AudioSegment:
        """Concatenate multiple audio segments.
        
        Args:
            segments: List of audio segments to concatenate
        
        Returns:
            AudioSegment: Concatenated audio
        """
        if not segments:
            raise ValueError("No audio segments to concatenate")
        
        # Ensure all segments have the same sample rate
        sample_rate = segments[0].sample_rate
        if not all(s.sample_rate == sample_rate for s in segments):
            raise ValueError("All audio segments must have the same sample rate")
        
        # Concatenate the audio data
        concatenated_data = np.concatenate([s.data for s in segments])
        total_duration = sum(s.duration for s in segments)
        
        return AudioSegment(
            data=concatenated_data,
            sample_rate=sample_rate,
            duration=total_duration
        ) 