"""Text-to-speech conversion using Kokoro."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Union

import numpy as np
from kokoro import KModel, KPipeline  # Maybe I'll implement TextToSpeech, Voice
from loguru import logger
from soundfile import SoundFile

from .config import (
    KOKORO_PATHS,
    SAMPLE_RATE,
    ErrorCodes,
)
from .helpers import (
    CacheDirManager,
    ConversionError,
    StrPath,
)
from .voices import Voice


class AudioConverter:
    """Class for converting text to speech using Kokoro."""

    def __init__(
        self,
        epub_path: StrPath,
        voice: str | Voice = Voice.AF_HEART,
        speech_rate: float = 1.0,
        cache: bool = True,
    ):
        """Initialize the audio converter.

        Args:
            epub_path: Path to the EPUB file, used to generate a cache directory
            voice: Voice to use
            speech_rate: Speech rate multiplier
            cache: Whether to cache the generated audio
            quiet: Whether to suppress progress reporting

        Raises:
            ConversionError: If the voice is invalid or TTS initialization fails
        """
        try:
            self.voice = self._get_voice(voice)
            model = True
            if Path(KOKORO_PATHS["model_weight"]).exists():
                logger.debug(f"model weight found: {KOKORO_PATHS['model_weight']}")
                model = KModel(
                    config=KOKORO_PATHS["config"],
                    model=KOKORO_PATHS["model_weight"],
                    repo_id="hexgrad/Kokoro-82M",
                )
            self.tts = KPipeline(
                lang_code=self.voice.lang_code,
                repo_id="hexgrad/Kokoro-82M",
                model=model,
            )
            self.speech_rate = speech_rate
            self.cache_dir_manager = CacheDirManager(epub_path)
            self.cache = cache
        except Exception as e:
            raise ConversionError(
                f"Failed to initialize TextToSpeech: {str(e)}", ErrorCodes.INVALID_VOICE
            ) from e

    def _get_voice(self, voice: Union[str, Voice]) -> Voice:
        """Get a voice by name.

        Args:
            voice: Voice to get

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
            valid_voices = ", ".join([v.name for v in Voice.list_voices()])
            raise ConversionError(
                f"Invalid voice '{voice}'. Available voices: {valid_voices}",
                ErrorCodes.INVALID_VOICE,
            ) from e

    def _audio_data_generator(
        self, text: str
    ) -> Generator[KPipeline.Result, None, None]:
        """Generate audio data from text.

        Args:
            text: Text to convert

        Returns:
            Generator[KPipeline.Result, None, None]: Audio data generator
        """
        try:
            voice = self.voice.local_path if self.voice.local_path else self.voice.name
            yield from self.tts(
                text, voice=voice, speed=self.speech_rate, split_pattern=r"\n+"
            )
        except Exception as e:
            raise ConversionError(
                f"Failed to generate audio data: {str(e)}", ErrorCodes.UNKNOWN_ERROR
            ) from e

    def convert_text(self, text: str) -> SoundFile:
        """Convert text to speech.

        Args:
            text: Text to convert

        Returns:
            SoundFile: Converted audio
        """
        try:
            # Create a temporary file
            temp_file = self.cache_dir_manager.get_file(text)

            # If the file exists and caching is enabled, return the cached file
            if os.path.exists(temp_file) and self.cache:
                return SoundFile(temp_file)

            if os.path.exists(f"{temp_file}.generating"):
                os.remove(f"{temp_file}.generating")

            audio_data = SoundFile(
                f"{temp_file}.generating",
                mode="w",
                samplerate=SAMPLE_RATE,
                channels=1,
                format="OGG",
                subtype="VORBIS",
            )
            # Generate speech
            for result in self._audio_data_generator(text):
                phonemes = result.phonemes
                audio = result.audio
                logger.trace(f"Phonemes: {phonemes}")
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
                f"Failed to convert text to speech: {str(e)}", ErrorCodes.UNKNOWN_ERROR
            ) from e
