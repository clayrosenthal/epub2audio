"""Audio file handling and metadata management."""

import base64
import io
from pathlib import Path
from dataclasses import asdict, dataclass
from shutil import move

from loguru import logger
from PIL import Image
import mutagen
from mutagen.flac import Picture, FLAC
from mutagen.id3 import (
    PictureType, ID3, CTOC, TIT2, TPE1, TDRC, COMM, CHAP, CTOCFlags,
    TOR, TPUB, TPE2, TCOP
)
from mutagen.oggflac import OggFLAC
from mutagen.oggopus import OggOpus
from mutagen.mp3 import MP3
from soundfile import SoundFile
from tqdm import tqdm  # type: ignore

from .config import ErrorCodes, SUPPORTED_AUDIO_FORMATS
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

    def _write_mp3_metadata(self, audio_file: MP3) -> None:
        """Write metadata to the audio file.

        Args:
            audio_file: MP3 file object
        """
        # Create ID3 tag if it doesn't exist
        if audio_file.tags is None:
            audio_file.add_tags()
            assert audio_file.tags is not None

        # Add basic metadata
        audio_file.tags.add(TIT2(encoding=3, text=[self.metadata.title]))
        if self.metadata.creator:
            audio_file.tags.add(TPE1(encoding=3, text=[self.metadata.creator]))
        if self.metadata.date:
            audio_file.tags.add(TDRC(encoding=3, text=[self.metadata.date]))
        if self.metadata.publisher:
            audio_file.tags.add(TPUB(encoding=3, text=[self.metadata.publisher]))
        if self.metadata.description:
            audio_file.tags.add(COMM(encoding=3, text=[self.metadata.description]))

        # Add chapter markers
        if self.chapter_markers:
            logger.debug(f"Adding chapter markers to {self.output_path}")
            # Create chapter IDs
            chapter_ids = [f"chp{i:03d}" for i in range(len(self.chapter_markers))]

            # Create CTOC (Table of Contents)
            audio_file.tags.add(
                CTOC(
                    element_id="toc",
                    flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                    child_element_ids=chapter_ids,
                    sub_frames=[TIT2(encoding=3, text=["Table of Contents"])]
                )
            )

            # Add individual chapters
            for i, marker in enumerate(self.chapter_markers):
                # Convert times to milliseconds
                start_time = int(marker.start_time * 1000)
                end_time = int(marker.end_time * 1000)
                logger.trace(f"Adding chapter '{marker.title}' at {start_time}ms")
                audio_file.tags.add(
                    CHAP(
                        element_id=chapter_ids[i],
                        start_time=start_time,
                        end_time=end_time,
                        sub_frames=[TIT2(encoding=3, text=[marker.title])]
                    )
                )

        # Add organization info
        audio_file.tags.add(TOR(encoding=3, text=["epub2audio"]))
        audio_file.tags.add(TPE2(encoding=3, text=["Kokoro TextToSpeech"]))
        audio_file.tags.add(TCOP(encoding=3, text=["https://creativecommons.org/licenses/by-sa/4.0/"]))


    def _write_vorbis_metadata(self, audio_file: OggOpus | OggFLAC | FLAC) -> None:
        """Write metadata to the audio file.

        Args:
            audio_file: mutagen.FileType file object that uses Vorbis Comments
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

    def _write_metadata(self, audio_file: mutagen.FileType) -> None:
        """Write metadata to the audio file.

        Args:
            audio_file: mutagen.FileType file object to write metadata to
        """
        if isinstance(audio_file, OggOpus):
            self._write_vorbis_metadata(audio_file)
        elif isinstance(audio_file, OggFLAC):
            self._write_vorbis_metadata(audio_file)
        elif isinstance(audio_file, FLAC):
            self._write_vorbis_metadata(audio_file)
        elif isinstance(audio_file, MP3):
            self._write_mp3_metadata(audio_file)
        else:
            raise ValueError(f"Unsupported audio file type: {type(audio_file)}")


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
        format_info = SUPPORTED_AUDIO_FORMATS[self.extension]
        concatenated_data = SoundFile(
            temp_file, 
            mode="w", 
            samplerate=sample_rate, 
            channels=1,
            format=format_info.format,
            subtype=format_info.subtype
        )
        with tqdm(
            total=sum(segment.frames for segment in segments),
            desc="Concatenating audio segments",
            disable=self.quiet,
            unit="frames",
        ) as pbar:
            for segment in segments:
                with SoundFile(segment.name, mode="r") as sf:
                    data = sf.read()
                concatenated_data.write(data)
                pbar.update(len(data))
        concatenated_data.close()
        return SoundFile(concatenated_data.name)


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
            final_segment.close()
            audio_file_class = SUPPORTED_AUDIO_FORMATS[self.extension].file_class
            audio_file = audio_file_class(final_segment.name)
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
