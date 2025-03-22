"""Audio file handling and metadata management."""

import base64
import io
from pathlib import Path
from dataclasses import asdict, dataclass
from shutil import move

from loguru import logger
from PIL import Image
from mutagen.flac import Picture, FLAC
from mutagen.id3 import PictureType
from mutagen.oggflac import OggFLAC
from mutagen.oggvorbis import OggVorbis
from soundfile import SoundFile
from tqdm import tqdm  # type: ignore

from .config import ErrorCodes
from .epub_processor import BookMetadata
from .helpers import AudioHandlerError, StrPath, format_time, CacheDirManager


@dataclass
class ChapterMarker:
    """Class for storing chapter marker information."""

    title: str
    start_time: float
    end_time: float

    @property
    def start_time_str(self) -> str:
        """Get the start time as a string."""
        return format_time(self.start_time)

    @property
    def end_time_str(self) -> str:
        """Get the end time as a string."""
        return format_time(self.end_time)

    @property
    def duration(self) -> float:
        """Get the duration of the chapter."""
        return self.end_time - self.start_time


class AudioHandler:
    """Class for handling audio file creation and metadata."""

    def __init__(self, epub_path: StrPath, output_path: StrPath, metadata: BookMetadata, quiet: bool = True):
        """Initialize the audio handler.

        Args:
            epub_path: Path to the EPUB file
            output_path: Path to the output audio file
            metadata: Book metadata
            quiet: Whether to suppress progress bars
        """
        self.epub_path = Path(epub_path)
        self.output_path = Path(output_path)
        self.extension = self.output_path.suffix
        self.metadata = metadata
        self.cache_dir_manager = CacheDirManager(epub_path, extension=self.extension)
        self.chapter_markers: list[ChapterMarker] = []
        self.quiet = quiet
    def add_chapter_marker(
        self, title: str, start_time: float, end_time: float
    ) -> None:
        """Add a chapter marker.

        Args:
            title: Chapter title
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        self.chapter_markers.append(ChapterMarker(title, start_time, end_time))

    def _make_flac_picture(self) -> Picture:
        """Make a FLAC picture.

        Returns:
            Picture: FLAC picture
        """
        if not self.metadata.cover_image:
            raise ValueError("No cover image found")
        cover_image_bytes = base64.b64decode(self.metadata.cover_image)
        cover_image = Image.open(io.BytesIO(cover_image_bytes))

        # cover_image.show()
        cover_picture = Picture()
        cover_picture.data = cover_image_bytes # cover_image.tobytes()
        if cover_image.format:
            cover_picture.mime = f"image/{cover_image.format.lower()}"
        else:
            cover_picture.mime = "image/jpeg"
        cover_picture.type = PictureType.COVER_FRONT
        cover_picture.height = cover_image.height
        cover_picture.width = cover_image.width
        cover_picture.depth = 8
        cover_picture.colors = 0
        cover_picture.desc = "Cover image" # TODO: Add description
        return cover_picture

    def _parse_cover_image(self) -> list[str]:
        """Parse the cover image.

        Args:
            cover_image_str: Cover image as a base64 encoded string
        """
        cover_picture = self._make_flac_picture()
        cover_b64_str = base64.b64encode(cover_picture.write()).decode("ascii")
        # cover_image.thumbnail((256, 256))
        # cover_picture.data = cover_image.tobytes()
        cover_picture.type = PictureType.FILE_ICON
        file_b64_str = base64.b64encode(cover_picture.write()).decode("ascii")
        return [
            cover_b64_str,
            file_b64_str,
        ]

    def _write_metadata(self, audio_file: OggVorbis | OggFLAC | FLAC) -> None:
        """Write metadata to the audio file.

        Args:
            audio_file: OggVorbis | OggFLAC | FLAC file object
        """
        # Add basic metadata
        audio_file["TITLE"] = self.metadata.title
        if self.metadata.creator:
            audio_file["ARTIST"] = self.metadata.creator
        if self.metadata.date:
            audio_file["DATE"] = self.metadata.date
        if self.metadata.publisher:
            audio_file["PUBLISHER"] = self.metadata.publisher
        if self.metadata.description:
            audio_file["DESCRIPTION"] = self.metadata.description
        if self.metadata.cover_image:
            if isinstance(audio_file, FLAC):
                flac_picture = self._make_flac_picture()
                audio_file.add_picture(flac_picture)
                flac_picture.type = PictureType.FILE_ICON
                audio_file.add_picture(flac_picture)
            else:
                audio_file["METADATA_BLOCK_PICTURE"] = self._parse_cover_image()

        audio_file["ORGANIZATION"] = "epub2audio"
        audio_file["PERFORMER"] = "Kokoro TextToSpeech"
        audio_file["COPYRIGHT"] = "https://creativecommons.org/licenses/by-sa/4.0/"

        # Add chapter markers
        for i, marker in enumerate(self.chapter_markers):
            audio_file[f"CHAPTER{i:03d}NAME"] = marker.title
            audio_file[f"CHAPTER{i:03d}"] = marker.start_time_str


    def _concatenate_segments(self, segments: list[SoundFile]) -> SoundFile:
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
        temp_file = self.cache_dir_manager.get_file("concatenated")
        concatenated_data = SoundFile(
            temp_file, mode="w", samplerate=sample_rate, channels=1
        )
        with tqdm(
            total=sum(segment.frames for segment in segments),
            desc="Concatenating audio segments",
            disable=self.quiet,
        ) as pbar:
            for segment in segments:
                with SoundFile(segment.name, mode="r") as sf:
                    data = sf.read()
                concatenated_data.write(data)
                pbar.update(len(data))
        concatenated_data.close()
        return concatenated_data


    def finalize_audio_file(self, segments: list[SoundFile]) -> None:
        """Write the final audio file with metadata.

        Args:
            segments: List of audio segments to concatenate and write to the final file

        Raises:
            AudioHandlerError: If writing the audio file fails
        """
        final_segment = self._concatenate_segments(segments)
        try:
            # Add metadata
            logger.trace(f"Adding metadata to final audio file, {final_segment.name}")
            # audio_file = OggVorbis(final_segment.name)
            audio_file = FLAC(final_segment.name)
            self._write_metadata(audio_file)
            logger.trace(f"Saving final audio file {audio_file.pprint()}")
            audio_file.save()
            move(final_segment.name, self.output_path)
            logger.debug(f"Final audio file saved to {self.output_path}")

        except Exception as e:
            raise AudioHandlerError(
                f"Failed to write final audio file: {str(e)}",
                ErrorCodes.FILESYSTEM_ERROR,
            ) from e

    @property
    def total_chapters(self) -> int:
        """Get the total number of chapters.

        Returns:
            int: Number of chapters
        """
        return len(self.chapter_markers)

    @property
    def total_duration(self) -> float:
        """Get the total duration in seconds.

        Returns:
            float: Total duration
        """
        if not self.chapter_markers:
            return 0.0
        return self.chapter_markers[-1].end_time
