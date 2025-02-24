"""Audio file handling and metadata management."""

import os
from shutil import move
from typing import List, Dict, Any
from mutagen.oggvorbis import OggVorbis
from soundfile import SoundFile
from dataclasses import asdict

from .epub_processor import Chapter, BookMetadata
from .helpers import AudioHandlerError, format_time, logger
from .config import ErrorCodes

class AudioHandler:
    """Class for handling audio file creation and metadata."""
    
    def __init__(self, output_path: str, metadata: BookMetadata):
        """Initialize the audio handler.
        
        Args:
            output_path: Path to the output audio file
            metadata: Book metadata
        """
        self.output_path = output_path
        self.metadata = metadata
        self.chapter_markers: List[Dict[str, Any]] = []
    
    def add_chapter_marker(
        self,
        title: str,
        start_time: float,
        end_time: float
    ) -> None:
        """Add a chapter marker.
        
        Args:
            title: Chapter title
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        self.chapter_markers.append({
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            'start_time_str': format_time(start_time),
            'end_time_str': format_time(end_time)
        })
    
    def _write_metadata(self, audio_file: OggVorbis) -> None:
        """Write metadata to the audio file.
        
        Args:
            audio_file: OggVorbis file object
        """
        # Convert metadata to dictionary, excluding None values
        metadata_dict = {
            k: v for k, v in asdict(self.metadata).items()
            if v is not None
        }
        
        # Add basic metadata
        audio_file['TITLE'] = metadata_dict.get('title', '')
        if 'creator' in metadata_dict:
            audio_file['ARTIST'] = metadata_dict['creator']
        if 'date' in metadata_dict:
            audio_file['DATE'] = metadata_dict['date']
        if 'publisher' in metadata_dict:
            audio_file['PUBLISHER'] = metadata_dict['publisher']
        if 'description' in metadata_dict:
            audio_file['DESCRIPTION'] = metadata_dict['description']
        
        # Add chapter markers
        for i, marker in enumerate(self.chapter_markers):
            audio_file[f'CHAPTER{i:03d}NAME'] = marker['title']
            audio_file[f'CHAPTER{i:03d}'] = marker['start_time_str']
    
    def finalize_audio_file(self, final_segment: SoundFile) -> None:
        """Write the final audio file with metadata.
        
        Args:
            final_segment: The final concatenated audio segment
        
        Raises:
            AudioHandlerError: If writing the audio file fails
        """
        try:
            # Add metadata
            logger.debug(f"Adding metadata to final audio file, {final_segment.name}")
            audio_file = OggVorbis(final_segment.name)
            self._write_metadata(audio_file)    
            logger.debug(f"Saving final audio file {audio_file.pprint()}")
            audio_file.save()
            move(final_segment.name, self.output_path)
            logger.debug(f"Final audio file saved to {self.output_path}")
            
        except Exception as e:
            raise AudioHandlerError(
                f"Failed to write final audio file: {str(e)}",
                ErrorCodes.FILESYSTEM_ERROR
            )
    
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
        return self.chapter_markers[-1]['end_time'] 