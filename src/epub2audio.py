"""Command-line interface for EPUB to audiobook conversion."""

import re
import sys
import time
from pathlib import Path
from typing import Union

import click
import roman
from loguru import logger
from soundfile import SoundFile  # type: ignore
from tqdm import tqdm  # type: ignore

from .audio_converter import AudioConverter
from .audio_handler import AudioHandler
from .config import (
    DEFAULT_LOGGER_ID,
    DEFAULT_SPEECH_RATE,
    ErrorCodes,
)
from .epub_processor import Chapter, EpubProcessor, get_book_length
from .helpers import (
    AudioHandlerError,
    ConversionError,
    StrPath,
    check_disk_space,
    clean_filename,
    ensure_dir_exists,
    format_duration,
    get_duration,
    ROMAN_REGEX,
)
from .voices import Voice



class Epub2Audio:
    """An epub converted into an audio book with AI."""

    def __init__(
        self,
        epub_path: StrPath,
        output_path: StrPath = "",
        voice: Union[str, Voice] = Voice.AF_HEART,
        speech_rate: float = 1.0,
        quiet: bool = True,
        cache: bool = True,
        convert: bool = True,
        max_chapters: int = -1,
    ):
        """Creates an AudioBook from an Epub.

        Args:
            epub_path: Path to the EPUB file
            output_path: Path to the output OGG file
            voice: Name of the voice to use
            speech_rate: Speech rate multiplier
            quiet: Whether to suppress progress reporting
            cache: Whether to enable caching of audio segments
            convert: Whether to convert the epub immediately
            max_chapters: Maximum number of chapters to process, or -1 for no limit.
        """
        self.cache = cache
        self.quiet = quiet
        self.epub_path = epub_path
        self.voice = voice
        self.speech_rate = speech_rate
        self.max_chapters = max_chapters
        self._parse_epub()
        # Create output filename
        if not output_path and self.metadata.title:
            self.output_path = Path(clean_filename(f"{self.metadata.title}.ogg"))
        elif not output_path:
            self.output_path = Path(epub_path).with_suffix(".ogg")
        elif Path(output_path).suffix != ".ogg":
            self.output_path = Path(output_path).with_suffix(".ogg")
        else:
            self.output_path = Path(output_path)

        # Create output directory
        ensure_dir_exists(self.output_path.parent)

        self.current_audibook_time = 0.0

        self.converter = AudioConverter(
            self.epub_path,
            voice=self.voice,
            speech_rate=self.speech_rate,
            cache=self.cache,
        )
        self.audio_handler = AudioHandler(
            self.epub_path,
            self.output_path,
            self.metadata,
            self.quiet,
        )

        # Estimate required disk space (rough estimate: 1MB per minute of audio)
        estimated_space = get_book_length(self.chapters) * 100  # Very rough estimate
        check_disk_space(self.output_path.parent, estimated_space)

        if convert:
            self.convert()

    @property
    def title(self) -> str:
        """The title of the book."""
        if not self.metadata:
            return ""
        return self.metadata.title

    def _parse_epub(self) -> None:
        """Parses out info from epub."""
        if not self.quiet:
            logger.info(f"Processing EPUB file: {self.epub_path}")

        # Process EPUB
        self.epub = EpubProcessor(self.epub_path)
        self.metadata = self.epub.metadata
        self.chapters = self.epub.chapters
        self.warnings = self.epub.warnings
        uses_roman_numerals = True
        for chapter in self.chapters[1:]:
            if not re.search(r"^chapter\s+[ivxclm]+\s", chapter.title.lower()):
                uses_roman_numerals = False
                break

        if uses_roman_numerals:
            logger.debug("Using roman numerals for chapter markers")
            self._roman_to_arabic()

    def _roman_to_arabic(self) -> None:
        """Convert roman numerals to arabic numerals."""
        for chapter in self.chapters:
            chapter_number = ROMAN_REGEX.search(chapter.title)
            if chapter_number:
                chapter_number = roman.fromRoman(chapter_number.group("number"))
                chapter.title = re.sub(
                    ROMAN_REGEX, f"Chapter {chapter_number} ", chapter.title
                )


    def _process_epub_chapter(self, chapter: Chapter) -> None:
        if self.max_chapters > 0 and len(self.chapters) > self.max_chapters:
            logger.info(f"Skipping chapter {chapter.title} as max chapters reached")
            return

        # Generate chapter announcement
        announcement = self.converter.convert_text(chapter.title)
        self.audio_segments.append(announcement)
        logger.debug(
            f"Chapter: '{chapter.title}' "
            f"announcement duration: {get_duration(announcement)}"
        )

        # Convert chapter text
        chapter_audio = self.converter.convert_text(chapter.content)
        self.audio_segments.append(chapter_audio)
        logger.debug(
            f"Chapter: '{chapter.title}' audio duration: {get_duration(chapter_audio)}"
        )

        # Add chapter marker
        start_time = self.current_audibook_time
        self.current_audibook_time += get_duration(announcement) + get_duration(
            chapter_audio
        )
        self.audio_handler.add_chapter_marker(
            chapter.title, start_time, self.current_audibook_time
        )

    def convert(self) -> None:
        """Process an EPUB file and convert it to an audiobook.

        Args:
            epub_path: Path to the EPUB file
            output_path: Path to the output  OGG file
            voice: Name of the voice to use
            speech_rate: Speech rate multiplier
            bitrate: Output audio bitrate
            quiet: Whether to suppress progress reporting
            cache: Whether to enable caching of audio segments
        """
        self.generation_start_time = time.time()

        # Process chapters
        self.current_audibook_time = 0.0
        self.audio_segments: list[SoundFile] = []

        with tqdm(
            total=get_book_length(self.chapters),
            desc="Converting chapters",
            disable=self.quiet,
        ) as pbar:
            for chapter in self.chapters:
                self._process_epub_chapter(chapter)
                pbar.update(len(chapter.content))

        # Concatenate all audio segments
        if not self.quiet:
            logger.info("Finalizing audio file...")

        self.audio_handler.finalize_audio_file(self.audio_segments)

        # Clean up cache files
        if not self.cache:
            self.converter.cache_dir_manager.cleanup()

        if self.quiet:
            return

        self.generation_time = time.time() - self.generation_start_time

        # Display summary info
        display_generation = format_duration(self.generation_time)
        display_duration = format_duration(self.audio_handler.total_duration)
        logger.success(f"\nAudiobook created successfully: {self.output_path}")
        logger.info(f"Total time generating: {display_generation}")
        logger.info(f"Total audio duration: {display_duration}")
        logger.info(f"Total chapters: {self.audio_handler.total_chapters}")

        # Display any warnings
        if self.warnings:
            logger.info("\nWarnings during conversion:")
            for warning in self.warnings:
                logger.info(f"- {warning.message}")


def process_epub(
    input_epub: StrPath,
    output: StrPath,
    speech_rate: float,
    voice: Union[str, Voice],
    quiet: bool = True,
    cache: bool = True,
    convert: bool = True,
    max_chapters: int = -1,
) -> Epub2Audio:
    """Process an EPUB file and convert it to an audiobook.

    Args:
        input_epub: Path to the EPUB file
        output: Path to the output OGG file
        voice: Name of the voice to use
        speech_rate: Speech rate multiplier
        quiet: Whether to suppress progress reporting
        cache: Whether to enable caching of audio segments
        convert: Whether to convert the epub immediately
        max_chapters: Maximum number of chapters to process, or -1 for no limit.
    """
    return Epub2Audio(
        input_epub,
        output,
        voice=voice,
        speech_rate=speech_rate,
        quiet=quiet,
        cache=cache,
        convert=convert,
        max_chapters=max_chapters,
    )


@click.command()
@click.argument(
    "input_epub",
    type=click.Path(
        exists=True, readable=True, file_okay=True, dir_okay=False, path_type=Path
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=False, writable=True, path_type=Path),
    default=None,
    help="Output path for the audiobook OGG file, default to book title",
)
@click.option(
    "--voice",
    "-v",
    type=Voice,
    default=Voice.AF_HEART,
    help="Voice to use for text-to-speech.",
    show_choices=False,
)
@click.option(
    "--speech-rate",
    "-s",
    type=float,
    default=DEFAULT_SPEECH_RATE,
    help="Speech rate multiplier.",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress reporting.")
@click.option("--cache", "-c", is_flag=True, help="Enable caching of audio segments.")
@click.option("--verbose", "-v", help="Enable verbose mode.", count=True)
@click.option(
    "--max-chapters",
    "-m",
    type=int,
    help="Maximum number of chapters to process, or -1 for no limit.",
    default=-1,
    show_default=True,
)
@click.version_option()
def main(
    input_epub: Path,
    output: Path,
    voice: Union[str, Voice],
    speech_rate: float,
    quiet: bool,
    cache: bool,
    verbose: int,
    convert: bool = True,
    max_chapters: int = -1,
) -> None:
    """Convert an EPUB ebook to an OGG audiobook.

    INPUT_EPUB is the path to the EPUB file to convert.
    """
    if quiet:
        logger.remove(DEFAULT_LOGGER_ID)
    elif verbose:
        logger.remove(DEFAULT_LOGGER_ID)
        if verbose > 1:
            logger.add(sys.stderr, level="DEBUG")
        elif verbose > 2:
            logger.add(sys.stderr, level="TRACE")
        logger.trace(f"Input EPUB: {input_epub}")
        logger.trace(f"Output path: {output}")
        logger.trace(f"Voice: {voice}")
        logger.trace(f"Speech rate: {speech_rate}")
        logger.trace(f"Quiet: {quiet}")
        logger.trace(f"Cache: {cache}")
        logger.trace(f"Convert: {convert}")
        logger.trace(f"Max chapters: {max_chapters}")
    try:
        process_epub(
            input_epub,
            output,
            speech_rate,
            voice,
            quiet,
            cache,
            convert,
            max_chapters,
        )
    except ConversionError as e:
        logger.exception(e)
        logger.error(f"Conversion error: {e.message}", err=True)
        exit(e.error_code)
    except AudioHandlerError as e:
        logger.exception(e)
        logger.error(f"Audio handler error: {e.message}", err=True)
        exit(e.error_code)
    except Exception as e:
        logger.exception(e)
        logger.error(f"Unexpected error: {str(e)}", err=True)
        exit(ErrorCodes.UNKNOWN_ERROR)


if __name__ == "__main__":
    main()
