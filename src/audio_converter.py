"""Text-to-speech conversion using Kokoro."""

import os
from loguru import logger
from typing import List, Generator, Union
from soundfile import SoundFile
import numpy as np
from kokoro import KPipeline # Maybe I'll implement TextToSpeech, Voice

from .helpers import ConversionError, logger, TempDirManager
from .config import (
    ErrorCodes,
    SAMPLE_RATE,
)
from .voices import Voice

class AudioConverter:
    """Class for converting text to speech using Kokoro."""
    
    def __init__(
        self,
        epub_path: str,
        voice: str | Voice = Voice.AF_HEART,
        speech_rate: float = 1.0,
        cache: bool = True,
    ):
        """Initialize the audio converter.
        
        Args:
            voice_name: Name of the voice to use
            speech_rate: Speech rate multiplier
        
        Raises:
            ConversionError: If the voice is invalid or TTS initialization fails
        """
        try:
            self.voice = self._get_voice(voice)
            self.tts = KPipeline(lang_code=self.voice.lang_code, repo_id='hexgrad/Kokoro-82M')
            self.speech_rate = speech_rate
            self.temp_dir_manager = TempDirManager(epub_path)
            self.cache = cache
        except Exception as e:
            raise ConversionError(
                f"Failed to initialize TextToSpeech: {str(e)}",
                ErrorCodes.INVALID_VOICE
            )
    
    def _get_voice(self, voice: Union[str, Voice]) -> Voice:
        """Get a voice by name.
        
        Args:
            voice_name: Name of the voice to get
        
        Returns:
            Voice: The requested voice
        
        Raises:
            ConversionError: If the voice is invalid
        """
        if isinstance(voice, Voice):
            return voice
        try:
            return Voice.get_by_name(voice)
        except Exception as e:
            raise ConversionError(
                f"Invalid voice '{voice}'. Available voices: {', '.join([v.name for v in Voice.list_voices()])}",
                ErrorCodes.INVALID_VOICE
            )
        
    def _audio_data_generator(self, text: str) -> Generator[KPipeline.Result, None, None]:
        """Generate audio data from text.
        
        Args:
            text: Text to convert
        
        Returns:
            Generator[KPipeline.Result, None, None]: Audio data generator
        """
        # if not self.voice.startswith(self.tts.lang_code):
        #     logger.warning(f"Voice {self.voice} is not made for language {self.tts.lang_code}")
        try:
            # audio_bytes = (result.audio.numpy() * 32767).astype(np.int16).tobytes()
            yield from self.tts(text, voice=self.voice.name, speed=self.speech_rate, split_pattern=r"\n+")
        except Exception as e:
            raise ConversionError(
                f"Failed to generate audio data: {str(e)}",
                ErrorCodes.UNKNOWN_ERROR
            )
    
    def convert_text(self, text: str) -> SoundFile:
        """Convert text to speech.
        
        Args:
            text: Text to convert
        
        Returns:
            SoundFile: Converted audio
        """
        try:
            # Create a temporary file
            temp_file = self.temp_dir_manager.get_tempfile()
            
            # If the file exists and caching is enabled, return the cached file
            if os.path.exists(temp_file) and self.cache:
                return SoundFile(temp_file)
            
            if os.path.exists(f"{temp_file}.generating"):
                os.remove(f"{temp_file}.generating")

            audio_data = SoundFile(f"{temp_file}.generating", mode='w', samplerate=SAMPLE_RATE, channels=1, format='OGG', subtype='VORBIS')
            # Generate speech
            for result in self._audio_data_generator(text):
                phonemes = result.phonemes
                audio = result.audio
                logger.debug(phonemes)
                if audio is None:
                    continue
                audio_bytes = (audio.numpy() * 32767).astype(np.int16)
                audio_data.write(audio_bytes)
            
            # Close the audio data, and rename the file to the final file
            audio_data.close()
            os.rename(f"{temp_file}.generating", temp_file)
            return SoundFile(temp_file)
        
        except Exception as e:
            raise ConversionError(
                f"Failed to convert text to speech: {str(e)}",
                ErrorCodes.UNKNOWN_ERROR
            )
    
    def generate_chapter_announcement(self, chapter_title: str) -> SoundFile:
        """Generate a chapter announcement.
        
        Args:
            chapter_title: Title of the chapter
        
        Returns:
            SoundFile: Chapter announcement audio
        """
        announcement_text = f"Chapter: {chapter_title}"
        return self.convert_text(announcement_text)
    
    def concatenate_segments(self, segments: List[SoundFile]) -> SoundFile:
        """Concatenate multiple audio segments.
        
        Args:
            segments: List of audio segments to concatenate
        
        Returns:
            SoundFile: Concatenated audio
        """
        if not segments:
            raise ValueError("No audio segments to concatenate")
        
        # Ensure all segments have the same sample rate
        sample_rate = segments[0].samplerate
        if not all(s.samplerate == sample_rate for s in segments):
            raise ValueError("All audio segments must have the same sample rate")
        
        # Concatenate the audio data
        temp_file = self.temp_dir_manager.get_tempfile()
        concatenated_data = SoundFile(temp_file, mode='w', samplerate=sample_rate, channels=1)
        for segment in segments:
            with SoundFile(segment.name, mode='r') as sf:
                data = sf.read(frames=sf.frames)
                concatenated_data.write(data)

        concatenated_data.close()
        return concatenated_data