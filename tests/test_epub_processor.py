"""Unit tests for EPUB processing module."""

from pathlib import Path

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
        content="""
        <h1>Chapter 1</h1>
        <p>This is the first chapter.</p>
    """,
    )
    c2 = epub.EpubHtml(
        title="Chapter 2",
        file_name="chap_2.xhtml",
        content="""
        <h1>Chapter 2</h1>
        <p>This is the second chapter.</p>
    """,
    )

    book.add_item(c1)
    book.add_item(c2)

    # Save the book
    epub_path = tmp_path / "test.epub"
    epub.write_epub(str(epub_path), book)
    return str(epub_path)


def test_epub_processor_init(sample_epub: str) -> None:
    """Test EPUBProcessor initialization."""
    processor = EpubProcessor(sample_epub)
    assert processor is not None
    assert processor.warnings == []


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

    assert len(chapters) == 2
    assert all(isinstance(c, Chapter) for c in chapters)
    assert chapters[0].title == "Chapter 1"
    assert "first chapter" in chapters[0].content.lower()
    assert chapters[1].title == "Chapter 2"
    assert "second chapter" in chapters[1].content.lower()


def test_clean_text() -> None:
    """Test HTML cleaning."""
    processor = EpubProcessor("dummy_path")  # Path doesn't matter for this test
    html = """
        <div>
            <script>alert('test');</script>
            <style>body { color: red; }</style>
            <h1>Title</h1>
            <p>Text with <b>formatting</b> and <img src="test.jpg" alt="test"/>.</p>
        </div>
    """

    cleaned = processor._clean_text(html)
    assert "alert" not in cleaned
    assert "color: red" not in cleaned
    assert "Title" in cleaned
    assert "Text with formatting and ." in cleaned
    assert len(processor.warnings) == 1  # Warning for img tag


def test_is_chapter() -> None:
    """Test chapter identification."""
    processor = EpubProcessor("dummy_path")

    # Create dummy EpubItem objects
    class DummyItem:
        def __init__(self, file_name: str) -> None:
            self.file_name = file_name

    assert processor._is_chapter(DummyItem("chapter1.xhtml"))
    assert not processor._is_chapter(DummyItem("toc.xhtml"))
    assert not processor._is_chapter(DummyItem("copyright.xhtml"))
    assert not processor._is_chapter(DummyItem("cover.xhtml"))
