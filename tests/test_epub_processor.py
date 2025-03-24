"""Unit tests for EPUB processing module."""

from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from ebooklib import epub

from src.config import ErrorCodes
from src.epub_processor import BookMetadata, Chapter, EpubProcessor
from src.helpers import ConversionError


@pytest.fixture
def sample_epub(tmp_path: Path) -> str:
    """Create a sample EPUB file for testing."""
    book = epub.EpubBook()

    # Add metadata
    book.set_identifier("id123")
    book.set_title("Test Book")
    book.set_language("en")
    book.add_author("Test Author")

    # Add chapters
    c1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="chap_1.xhtml",
        lang="en",
        content="""
        <h1>Chapter 1</h1>
        <p>This is the first chapter.</p>
    """,
    )
    c2 = epub.EpubHtml(
        title="Chapter 2",
        file_name="chap_2.xhtml",
        lang="en",
        content="""
        <h1>Chapter 2</h1>
        <p>This is the second chapter.</p>
    """,
    )

    # Set unique IDs for the chapters
    c1.id = "chapter1"
    c2.id = "chapter2"
    
    # Add chapters to the book
    book.add_item(c1)
    book.add_item(c2)
    
    # Create table of contents
    book.toc = (
        epub.Link("chap_1.xhtml", "Chapter 1", "chapter1"),
        epub.Link("chap_2.xhtml", "Chapter 2", "chapter2")
    )
    
    # Add default NCX and Nav files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define spine
    book.spine = ["nav", c1, c2]
    
    # Save the book
    epub_path = tmp_path / "test.epub"
    epub.write_epub(str(epub_path), book)
    return str(epub_path)


def test_epub_processor_init(sample_epub: str) -> None:
    """Test EPUBProcessor initialization."""
    processor = EpubProcessor(sample_epub)
    assert processor is not None
    # Check that warnings contain expected missing metadata field warnings
    assert len(processor.warnings) == 3
    warning_messages = [w.message for w in processor.warnings]
    assert "Missing metadata field: date" in warning_messages
    assert "Missing metadata field: publisher" in warning_messages
    assert "Missing metadata field: description" in warning_messages


def test_epub_processor_init_invalid_file(tmp_path: Path) -> None:
    """Test EPUBProcessor initialization with invalid file."""
    invalid_path = tmp_path / "invalid.epub"
    invalid_path.write_text("not an epub file")

    with pytest.raises(ConversionError) as exc_info:
        EpubProcessor(str(invalid_path))
    assert exc_info.value.error_code == ErrorCodes.INVALID_EPUB


def test_extract_metadata(sample_epub: str) -> None:
    """Test metadata extraction."""
    metadata = EpubProcessor(sample_epub).metadata

    assert isinstance(metadata, BookMetadata)
    assert metadata.title == "Test Book"
    assert metadata.creator == "Test Author"
    assert metadata.language == "en"
    assert metadata.identifier == "id123"


def test_extract_chapters(sample_epub: str) -> None:
    """Test chapter extraction."""
    chapters = EpubProcessor(sample_epub).chapters

    assert len(chapters) == 3  # Book title + 2 chapters
    assert all(isinstance(c, Chapter) for c in chapters)
    
    # First chapter should be the book title
    assert chapters[0].title == "Test Book"
    assert chapters[0].id == "title"
    assert chapters[0].order == -1
    assert "book by Test Author" in chapters[0].content
    
    # Then the actual chapters
    assert chapters[1].title == "Chapter 1"
    assert "first chapter" in chapters[1].content.lower()
    assert chapters[2].title == "Chapter 2"
    assert "second chapter" in chapters[2].content.lower()


def test_clean_text() -> None:
    """Test HTML cleaning."""
    html = """
        <div>
            <script>alert('test');</script>
            <style>body { color: red; }</style>
            <h1>Title</h1>
            <p>Text with <b>formatting</b> and <img src="test.jpg" alt="test"/>.</p>
        </div>
    """
    
    # First, create a proper mock metadata object
    mock_metadata = BookMetadata(
        title="Test Book",
        creator="Test Author",
        language="en",
        identifier="id123"
    )
    
    # Use patching to avoid actual file operations
    with patch("ebooklib.epub.read_epub") as mock_read_epub:
        # Create and configure the mock EPUB object
        mock_epub = Mock()
        mock_read_epub.return_value = mock_epub
        
        # Setup EpubProcessor with method patches to avoid initialization errors
        with patch.object(EpubProcessor, '_extract_metadata', return_value=mock_metadata):
            with patch.object(EpubProcessor, '_extract_chapters', return_value=[
                Chapter(title="Test", content="Test content", order=0, id="test")
            ]):
                # Now we can initialize the processor safely
                processor = EpubProcessor("sample_path")
                processor.warnings = []
                
                # Test the clean_text method
                cleaned = processor._clean_text(html)
                assert "alert" not in cleaned
                assert "color: red" not in cleaned
                assert "Title" in cleaned
                assert "Text with formatting and ." in cleaned
                assert len(processor.warnings) == 1  # Warning for img tag


def test_is_chapter() -> None:
    """Test chapter identification."""
    # Create dummy EpubItem objects
    class DummyItem:
        def __init__(self, file_name: str, item_id: str = "dummy_id") -> None:
            self.file_name = file_name
            self.id = item_id
    
    # First, create a proper mock metadata object
    mock_metadata = BookMetadata(
        title="Test Book",
        creator="Test Author",
        language="en",
        identifier="id123"
    )
    
    # Use patching to avoid actual file operations
    with patch("ebooklib.epub.read_epub") as mock_read_epub:
        # Setup mock objects
        mock_epub = Mock()
        mock_read_epub.return_value = mock_epub
        
        # Setup EpubProcessor with method patches to avoid initialization errors
        with patch.object(EpubProcessor, '_extract_metadata', return_value=mock_metadata):
            with patch.object(EpubProcessor, '_extract_chapters', return_value=[
                Chapter(title="Test", content="Test content", order=0, id="test")
            ]):
                # Now we can initialize the processor safely
                processor = EpubProcessor("dummy_path")
                
                # Test the is_chapter method with different types of items
                assert processor._is_chapter(DummyItem("chapter1.xhtml"))
                assert not processor._is_chapter(DummyItem("toc.xhtml"))
                assert not processor._is_chapter(DummyItem("copyright.xhtml"))
                assert not processor._is_chapter(DummyItem("cover.xhtml"))
                assert not processor._is_chapter(DummyItem("chapter1.xhtml", "pg-toc"))
