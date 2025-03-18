"""Unit tests for command-line interface."""

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.config import ErrorCodes
from src.epub2audio import main, process_epub
from src.helpers import ConversionError
from src.voice import Voice

@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_process_epub() -> Generator[Mock, None, None]:
    """Mock the process_epub function."""
    with patch("src.epub2audio.process_epub") as mock:
        yield mock


def test_cli_basic(
    cli_runner: CliRunner, mock_process_epub: Mock, tmp_path: Path
) -> None:
    """Test basic CLI usage with default parameters."""
    input_file = tmp_path / "test.epub"
    input_file.touch()

    result = cli_runner.invoke(main, [str(input_file)])

    assert result.exit_code == 0
    mock_process_epub.assert_called_once_with(
        input_file, 
        input_file.with_suffix(".ogg"),
        voice=Voice.AF_HEART,
        speech_rate=1.0,
        quiet=False,
        cache=True,
    )


def test_cli_with_options(
    cli_runner: CliRunner, mock_process_epub: Mock, tmp_path: Path
) -> None:
    """Test CLI with all options specified and verify they are passed correctly."""
    input_file = str(tmp_path / "test.epub")
    output = str(tmp_path / "output.ogg")
    open(input_file, "w").close()  # Create empty file

    result = cli_runner.invoke(
        main,
        [
            input_file,
            "--output",
            output,
            "--voice",
            "test_voice",
            "--rate",
            "1.5",
            "--bitrate",
            "256k",
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    mock_process_epub.assert_called_once_with(
        input_file, output, "test_voice", 1.5, "256k", True
    )


def test_cli_missing_input(cli_runner: CliRunner) -> None:
    """Test CLI fails gracefully when input file is not provided."""
    result = cli_runner.invoke(main, [])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_cli_invalid_input(cli_runner: CliRunner) -> None:
    """Test CLI fails gracefully when input file does not exist."""
    result = cli_runner.invoke(main, ["nonexistent.epub"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_cli_invalid_rate(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test CLI fails gracefully when an invalid speech rate is provided."""
    input_file = str(tmp_path / "test.epub")
    open(input_file, "w").close()  # Create empty file

    result = cli_runner.invoke(main, [input_file, "--rate", "invalid"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_process_epub_error_handling(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test error handling when process_epub raises a ConversionError."""
    input_file = str(tmp_path / "test.epub")
    open(input_file, "w").close()  # Create empty file

    with patch(
        "src.epub2audio.process_epub",
        side_effect=ConversionError("Test error", ErrorCodes.INVALID_EPUB),
    ):
        result = cli_runner.invoke(main, [input_file])
        assert result.exit_code == ErrorCodes.INVALID_EPUB
        assert "Error: Test error" in result.output


def test_process_epub_unexpected_error(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test error handling when process_epub raises an unexpected error."""
    input_file = str(tmp_path / "test.epub")
    open(input_file, "w").close()  # Create empty file

    with patch(
        "src.epub2audio.process_epub", side_effect=Exception("Unexpected error")
    ):
        result = cli_runner.invoke(main, [input_file])
        assert result.exit_code == ErrorCodes.UNKNOWN_ERROR
        assert "Unexpected error" in result.output


@pytest.mark.integration
def test_process_epub_integration(tmp_path: Path) -> None:
    """Integration test for EPUB processing with all components mocked."""
    # Create test files and directories
    input_file = str(tmp_path / "test.epub")
    output = tmp_path / "output.ogg"
    os.makedirs(output.parent, exist_ok=True)
    open(input_file, "w").close()  # Create empty file

    # Mock all the necessary components
    with (
        patch("src.epub2audio.EPUBProcessor") as mock_processor,
        patch("src.epub2audio.AudioConverter") as mock_converter,
        patch("src.epub2audio.AudioHandler") as mock_handler,
    ):
        # Set up mock returns
        mock_processor.return_value.extract_metadata.return_value = Mock()
        mock_processor.return_value.extract_chapters.return_value = [
            Mock(title="Chapter 1", content="Test content")
        ]
        mock_processor.return_value.warnings = []

        mock_converter.return_value.convert_text.return_value = Mock()
        mock_converter.return_value.generate_chapter_announcement.return_value = Mock()

        # Run the process
        process_epub(
            input_file, output, speech_rate=1.0, voice="test_voice", quiet=False
        )

        # Verify the process flow
        mock_processor.assert_called_once()
        mock_processor.return_value.extract_metadata.assert_called_once()
        mock_processor.return_value.extract_chapters.assert_called_once()

        mock_converter.assert_called_once()
        assert mock_converter.return_value.convert_text.called
        assert mock_converter.return_value.generate_chapter_announcement.called

        mock_handler.assert_called_once()
        assert mock_handler.return_value.add_chapter_marker.called
        assert mock_handler.return_value.finalize_audio_file.called
