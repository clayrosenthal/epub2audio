"""Command-line interface for EPUB to audiobook conversion."""

import os
import click
import shutil
from typing import Optional
from tqdm import tqdm

from .epub_processor import EPUBProcessor
from .audio_converter import AudioConverter
from .audio_handler import AudioHandler
from .helpers import (
    ConversionError,
    AudioHandlerError,
    get_duration,
    ensure_dir_exists,
    check_disk_space,
    clean_filename,
    logger
)
from .voices import Voice
from .config import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SPEECH_RATE,
    DEFAULT_BITRATE,
    TEMP_DIR,
    ErrorCodes
)

def process_epub(
    epub_path: str,
    output_dir: str,
    voice_name: str,
    speech_rate: float,
    bitrate: str,
    quiet: bool,
    debug: bool,
) -> None:
    """Process an EPUB file and convert it to an audiobook.
    
    Args:
        epub_path: Path to the EPUB file
        output_dir: Output directory
        voice_name: Name of the voice to use
        speech_rate: Speech rate multiplier
        bitrate: Output audio bitrate
        quiet: Whether to suppress progress reporting
        debug: Whether to enable debug mode
    """
    # Create output directory
    ensure_dir_exists(output_dir)
    
    # Initialize progress bars
    if not quiet:
        click.echo(f"Processing EPUB file: {epub_path}")
    
    # Process EPUB
    epub = EPUBProcessor(epub_path)
    metadata = epub.extract_metadata()
    chapters = epub.extract_chapters()
    
    # Estimate required disk space (rough estimate: 1MB per minute of audio)
    estimated_space = sum(len(chapter.content) for chapter in chapters) * 100  # Very rough estimate
    check_disk_space(output_dir, estimated_space)
    
    # Initialize audio converter
    converter = AudioConverter(voice_name, speech_rate)
    
    # Create output filename
    output_filename = clean_filename(f"{metadata.title}.ogg")
    output_path = os.path.join(output_dir, output_filename)
    
    # Initialize audio handler
    audio_handler = AudioHandler(output_path, metadata)
    
    # Process chapters
    current_time = 0.0
    audio_segments = []
    
    with tqdm(
        total=len(chapters),
        desc="Converting chapters",
        disable=quiet
    ) as pbar:
        for chapter in chapters:
            # Generate chapter announcement
            announcement = converter.generate_chapter_announcement(chapter.title)
            audio_segments.append(announcement)
            
            # Convert chapter text
            chapter_audio = converter.convert_text(chapter.content)
            audio_segments.append(chapter_audio)
            
            # Add chapter marker
            start_time = current_time
            current_time += get_duration(announcement) + get_duration(chapter_audio)
            audio_handler.add_chapter_marker(
                chapter.title,
                start_time,
                current_time
            )
            
            pbar.update(1)
    
    # Concatenate all audio segments
    if not quiet:
        click.echo("Finalizing audio file...")
    
    final_audio = converter.concatenate_segments(audio_segments)
    audio_handler.finalize_audio_file(final_audio)
    
    # Clean up temporary files
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    
    if not quiet:
        click.echo(f"\nAudiobook created successfully: {output_path}")
        click.echo(f"Total duration: {audio_handler.total_duration:.1f} seconds")
        click.echo(f"Total chapters: {audio_handler.total_chapters}")
        
        # Display any warnings
        if epub.warnings:
            click.echo("\nWarnings during conversion:")
            for warning in epub.warnings:
                click.echo(f"- {warning.message}")

@click.command()
@click.argument('input_epub', type=click.Path(exists=True))
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(),
    default=DEFAULT_OUTPUT_DIR,
    help='Output directory for the audiobook.'
)
@click.option(
    '--voice',
    '-v',
    type=Voice,
    default=Voice.AF_HEART,
    help='Voice to use for text-to-speech.'
)
@click.option(
    '--rate',
    '-r',
    type=float,
    default=DEFAULT_SPEECH_RATE,
    help='Speech rate multiplier.'
)
@click.option(
    '--bitrate',
    '-b',
    type=str,
    default=DEFAULT_BITRATE,
    help='Output audio bitrate.'
)
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    help='Suppress progress reporting.'
)
@click.option(
    '--debug',
    '-d',
    is_flag=True,
    help='Enable debug mode.'
)
def main(
    input_epub: str,
    output_dir: str,
    voice: str,
    rate: float,
    bitrate: str,
    quiet: bool,
    debug: bool
) -> None:
    """Convert an EPUB ebook to an OGG audiobook.
    
    INPUT_EPUB is the path to the EPUB file to convert.
    """
    if debug:
        logger.level("DEBUG")
        logger.debug(f"Debug mode enabled")
        logger.debug(f"running in {os.getcwd()}")
    try:
        process_epub(
            input_epub,
            output_dir,
            voice,
            rate,
            bitrate,
            quiet,
            debug
        )
    except ConversionError as e:
        logger.exception(e)
        click.echo(f"Conversion error: {e.message}", err=True)
        exit(e.error_code)
    except AudioHandlerError as e:
        logger.exception(e)
        click.echo(f"Audio handler error: {e.message}", err=True)
        exit(e.error_code)
    except Exception as e:
        logger.exception(e)
        click.echo(f"Unexpected error: {str(e)}", err=True)
        exit(ErrorCodes.UNKNOWN_ERROR)

if __name__ == '__main__':
    main() 