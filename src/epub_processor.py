"""EPUB processing and text extraction module."""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

from .helpers import ConversionError, ConversionWarning, logger
from .config import ErrorCodes, WarningTypes, METADATA_FIELDS

@dataclass
class Chapter:
    """Class representing a chapter in the EPUB book."""
    title: str
    content: str
    order: int
    id: str

@dataclass
class BookMetadata:
    """Class representing book metadata."""
    title: str
    creator: Optional[str] = None
    date: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    publisher: Optional[str] = None
    description: Optional[str] = None

class EPUBProcessor:
    """Class for processing EPUB files and extracting content."""
    
    def __init__(self, epub_path: str):
        """Initialize the EPUB processor.
        
        Args:
            epub_path: Path to the EPUB file
        
        Raises:
            ConversionError: If the EPUB file is invalid or cannot be read
        """
        self.epub_path = epub_path
        self.warnings: List[ConversionWarning] = []
        try:
            self.book = epub.read_epub(epub_path)
        except Exception as e:
            raise ConversionError(
                f"Failed to read EPUB file: {str(e)}",
                ErrorCodes.INVALID_EPUB
            )
    
    def extract_metadata(self) -> BookMetadata:
        """Extract metadata from the EPUB file.
        
        Returns:
            BookMetadata: Extracted metadata
        """
        metadata = {}
        
        # Extract Dublin Core metadata
        for field in METADATA_FIELDS:
            value = self.book.get_metadata('DC', field)
            if value:
                metadata[field] = value[0][0]
            else:
                if field == 'title':
                    raise ConversionError(
                        "EPUB file missing required title metadata",
                        ErrorCodes.INVALID_EPUB
                    )
                logger.warning(f"Missing metadata field: {field}")
                self.warnings.append(
                    ConversionWarning(
                        type=WarningTypes.UNSUPPORTED_METADATA,
                        message=f"Missing metadata field: {field}"
                    )
                )
        
        return BookMetadata(**metadata)
    
    def _clean_text(self, html_content: str) -> str:
        """Clean HTML content and extract plain text.
        
        Args:
            html_content: Raw HTML content
        
        Returns:
            str: Cleaned text content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Handle non-text elements
        for element in soup.find_all(['img', 'svg']):
            logger.warning(f"Skipping non-text element: {element.name}")
            self.warnings.append(
                ConversionWarning(
                    type=WarningTypes.NON_TEXT_ELEMENT,
                    message=f"Skipping non-text element: {element.name}"
                )
            )
            element.decompose()
        
        # Get text and clean it
        text = soup.get_text()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_chapters(self) -> List[Chapter]:
        """Extract chapters from the EPUB file.
        
        Returns:
            List[Chapter]: List of extracted chapters
        """
        chapters = []
        order = 0
        
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            # Skip non-chapter items (e.g., TOC, copyright pages)
            if not self._is_chapter(item):
                continue
            
            content = self._clean_text(item.get_content().decode('utf-8'))
            
            # Skip empty chapters
            if not content:
                continue
            
            # Extract title from content or use fallback
            title = self._extract_chapter_title(item) or f"Chapter {order + 1}"
            
            chapters.append(Chapter(
                title=title,
                content=content,
                order=order,
                id=item.id
            ))
            order += 1
        
        if not chapters:
            raise ConversionError(
                "No valid chapters found in EPUB file",
                ErrorCodes.INVALID_EPUB
            )
        
        return sorted(chapters, key=lambda x: x.order)
    
    def _is_chapter(self, item: epub.EpubItem) -> bool:
        """Determine if an EPUB item is a chapter.
        
        Args:
            item: EPUB item to check
        
        Returns:
            bool: True if the item is a chapter
        """
        # Skip common non-chapter files
        skip_patterns = [
            r'toc\.x?html$',
            r'copyright\.x?html$',
            r'cover\.x?html$'
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, item.file_name.lower()):
                return False
        
        return True
    
    def _extract_chapter_title(self, item: epub.EpubItem) -> Optional[str]:
        """Extract chapter title from an EPUB item.
        
        Args:
            item: EPUB item to extract title from
        
        Returns:
            Optional[str]: Extracted title or None
        """
        soup = BeautifulSoup(item.get_content().decode('utf-8'), 'html.parser')
        
        # Try to find title in common heading elements
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            title = heading.get_text().strip()
            if title:
                return title
        
        return None 