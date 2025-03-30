"""Unit tests for EPUB processing module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from ebooklib import epub  # type: ignore

from epub2audio.config import ErrorCodes
from epub2audio.epub_processor import BookMetadata, Chapter, EpubProcessor
from epub2audio.helpers import ConversionError

test_image_content = """
<img src="image.jpg" alt="Alt text of the test image" title="The test image"/>
""".strip()

chapter_1_content = """
<p>This is the first chapter of the test book.</p>
<p>It contains multiple paragraphs to test text extraction.</p>
"""

chapter_2_content = f"""
<p>This is the second chapter of the test book.</p>
<p>It includes some formatting like <b>bold</b> and <i>italic</i> text.</p>
{test_image_content}
"""


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
        uid="chap1",
        content=f"""
        <h1>Chapter 1</h1>
        {chapter_1_content}
    """,
    )
    c2 = epub.EpubHtml(
        title="Chapter 2",
        file_name="chap_2.xhtml",
        lang="en",
        uid="chap2",
        content=f"""
        <h1>Chapter 2</h1>
        {chapter_2_content}
    """,
    )

    # Set unique IDs for the chapters
    # c1.id = "chap1"
    # c2.id = "chap2"

    # Add chapters to the book
    book.add_item(c1)
    book.add_item(c2)

    # Create table of contents
    book.toc = (
        # epub.Link("chap_1.xhtml", "Chapter 1", "chap1"),
        # epub.Link("chap_2.xhtml", "Chapter 2", "chap2"),
        c1,
        c2,
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


single_page_content = f"""
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head></head>
<body>
    <div class="Basic-Text-Frame">
        <p class="Title">Single Page Test Book</p>
    </div>
    <div class="Basic-Text-Frame">
        <p class="Author">By Test Author</p>
    </div>
    <div>
        <p class="Heading-2" id="chap1">Chapter 1</p>
        {chapter_1_content}

        <p class="Heading-2" id="chap2">Chapter 2</p>
        {chapter_2_content}
    </div>
</body>
</html>
"""


@pytest.fixture
def single_page_epub(tmp_path: Path) -> str:
    """Create a sample EPUB file with multiple chapters in a single page."""
    book = epub.EpubBook()

    # Add metadata
    book.set_identifier("id456")
    book.set_title("Single Page Test Book")
    book.set_language("en")
    book.add_author("Test Author")

    # Create a single page with all chapters
    single_page = epub.EpubHtml(
        title="Single Page Book",
        file_name="content.xhtml",
        lang="en",
        content=single_page_content,
    )

    # Add the single page to book
    book.add_item(single_page)

    # Create links for each chapter
    chap1 = epub.Link("content.xhtml#chap1", "Chapter 1", "chap1")
    chap2 = epub.Link("content.xhtml#chap2", "Chapter 2", "chap2")

    # Create proper table of contents with links to chapters
    book.toc = (chap1, chap2)

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Create spine
    book.spine = ["nav", single_page]

    # Save the book
    epub_path = tmp_path / "single_page_test.epub"
    epub.write_epub(str(epub_path), book)
    return str(epub_path)


def test_epub_processor_init(sample_epub: str) -> None:
    """Test EPUBProcessor initialization."""
    processor = EpubProcessor(sample_epub)
    assert processor is not None
    # Check that warnings contain expected missing metadata field warnings
    assert len(processor.warnings) == 4
    warning_messages = [w.message for w in processor.warnings]
    assert "Missing metadata field: date" in warning_messages
    assert "Missing metadata field: publisher" in warning_messages
    assert "Missing metadata field: description" in warning_messages
    assert "Skipping non-text element: img" in warning_messages


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


def _test_extract_chapters(chapters: list[Chapter], title: str) -> None:
    """Unified test suite for chapter extraction.

    Both single-page and multi-page EPUBs are supported.
    They should produce the same chapters.
    """
    # Find chapters by their IDs
    title_chapters = [c for c in chapters if c.id == "title"]
    chap1_chapters = [c for c in chapters if c.id == "chap1"]
    chap2_chapters = [c for c in chapters if c.id == "chap2"]

    # Verify we have all expected chapters
    assert len(title_chapters) >= 1
    assert len(chap1_chapters) >= 1
    assert len(chap2_chapters) >= 1

    # Verify chapter content
    title_chapter = title_chapters[0]
    assert title_chapter.title == title
    assert title_chapter.order == -1
    assert "Test Author" in title_chapter.content

    chap1 = chap1_chapters[0]
    assert chap1.title == "Chapter 1"
    assert "first chapter" in chap1.content.lower()
    assert "test book" in chap1.content.lower()

    chap2 = chap2_chapters[0]
    assert chap2.title == "Chapter 2"
    assert "second chapter" in chap2.content.lower()
    assert "test book" in chap2.content.lower()
    assert "formatting" in chap2.content.lower()
    assert "bold" in chap2.content.lower()
    assert "italic" in chap2.content.lower()


def test_extract_chapters(sample_epub: str) -> None:
    """Test chapter extraction."""
    processor = EpubProcessor(sample_epub)
    chapters = processor.chapters
    _test_extract_chapters(chapters, "Test Book")


def test_single_page_epub_extraction(single_page_epub: str) -> None:
    """Test extraction from a single-page EPUB with multiple chapters."""
    processor = EpubProcessor(single_page_epub)
    chapters = processor.chapters
    _test_extract_chapters(chapters, "Single Page Test Book")


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
        title="Test Book", creator="Test Author", language="en", identifier="id123"
    )

    # Use patching to avoid actual file operations
    with patch("ebooklib.epub.read_epub") as mock_read_epub:
        # Create and configure the mock EPUB object
        mock_epub = Mock()
        mock_read_epub.return_value = mock_epub

        # Setup EpubProcessor with method patches to avoid initialization errors
        with patch.object(
            EpubProcessor, "_extract_metadata", return_value=mock_metadata
        ):
            with patch.object(
                EpubProcessor,
                "_extract_chapters",
                return_value=[
                    Chapter(title="Test", content="Test content", order=0, id="test")
                ],
            ):
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

    # Create a more complete dummy EpubItem
    class DummyItem:
        def __init__(self, file_name: str, item_id: str = "dummy_id") -> None:
            self.file_name = file_name
            self.id = item_id

        def get_content(self) -> bytes:
            # Return a dummy content that's long enough to pass the size check
            return (
                b"<html><body><h1>Chapter Title</h1>"
                b"<p>This is some content for this chapter.</p>"
                b"<p>It needs to be long enough to pass the size check.</p>"
                b"</body></html>"
            )

    # First, create a proper mock metadata object
    mock_metadata = BookMetadata(
        title="Test Book", creator="Test Author", language="en", identifier="id123"
    )

    # Use patching to avoid actual file operations
    with patch("ebooklib.epub.read_epub") as mock_read_epub:
        # Setup mock objects
        mock_epub = Mock()
        mock_read_epub.return_value = mock_epub

        # Setup EpubProcessor with method patches to avoid initialization errors
        with patch.object(
            EpubProcessor, "_extract_metadata", return_value=mock_metadata
        ):
            with patch.object(
                EpubProcessor,
                "_extract_chapters",
                return_value=[
                    Chapter(title="Test", content="Test content", order=0, id="test")
                ],
            ):
                # Now we can initialize the processor safely
                processor = EpubProcessor("dummy_path")

                # Also patch isinstance check for EpubHtml
                with patch("epub2audio.epub_processor.isinstance", return_value=True):
                    # Test the is_chapter method with different types of items
                    assert processor._is_chapter(DummyItem("chapter1.xhtml"))
                    assert not processor._is_chapter(DummyItem("toc.xhtml"))
                    assert not processor._is_chapter(DummyItem("copyright.xhtml"))
                    assert not processor._is_chapter(DummyItem("cover.xhtml"))
                    assert not processor._is_chapter(
                        DummyItem("chapter1.xhtml", "pg-toc")
                    )
