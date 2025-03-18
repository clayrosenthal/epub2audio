"""Audio file handling and metadata management."""

from dataclasses import asdict, dataclass
from shutil import move

from loguru import logger
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
        self.epub_path = epub_path
        self.output_path = output_path
        self.metadata = metadata
        self.cache_dir_manager = CacheDirManager(epub_path)
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

    def _write_metadata(self, audio_file: OggVorbis) -> None:
        """Write metadata to the audio file.

        Args:
            audio_file: OggVorbis file object
        """
        # Convert metadata to dictionary, excluding None values
        metadata_dict = {
            k: v for k, v in asdict(self.metadata).items() if v is not None
        }

        # Add basic metadata
        audio_file["TITLE"] = metadata_dict.get("title", "")
        if "creator" in metadata_dict:
            audio_file["ARTIST"] = metadata_dict["creator"]
        if "date" in metadata_dict:
            audio_file["DATE"] = metadata_dict["date"]
        if "publisher" in metadata_dict:
            audio_file["PUBLISHER"] = metadata_dict["publisher"]
        if "description" in metadata_dict:
            audio_file["DESCRIPTION"] = metadata_dict["description"]
        if "cover_image" in metadata_dict:
            audio_file["METADATA_BLOCK_PICTURE"] = metadata_dict["cover_image"]

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
            audio_file = OggVorbis(final_segment.name)
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
