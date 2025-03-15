"""Unit tests for helper functions."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import ErrorCodes
from src.helpers import (
    ConversionError,
    ConversionWarning,
    check_disk_space,
    clean_filename,
    ensure_dir_exists,
    format_time,
    logger,
)


def test_conversion_error() -> None:
    """Test ConversionError class."""
    error = ConversionError("Test error", ErrorCodes.INVALID_EPUB)
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.error_code == ErrorCodes.INVALID_EPUB


def test_conversion_warning():
    """Test ConversionWarning class."""
    warning = ConversionWarning("test_type", "Test warning")
    assert warning.type == "test_type"
    assert warning.message == "Test warning"


def test_ensure_dir_exists(tmp_path):
    """Test directory creation."""
    test_dir = tmp_path / "test_dir"

    # Test creating new directory
    ensure_dir_exists(str(test_dir))
    assert test_dir.exists()
    assert test_dir.is_dir()

    # Test with existing directory
    ensure_dir_exists(str(test_dir))  # Should not raise error

    # Test with file path
    test_file = tmp_path / "test_file"
    test_file.touch()
    with pytest.raises(ConversionError) as exc_info:
        ensure_dir_exists(str(test_file))
    assert exc_info.value.error_code == ErrorCodes.FILESYSTEM_ERROR


def test_check_disk_space(tmp_path: Path) -> None:
    """Test disk space checking."""
    # Mock disk usage
    du = Mock(free=1024 * 1024 * 100)  # 100MB free
    with patch("shutil.disk_usage", return_value=du):
        # Test with sufficient space
        check_disk_space(str(tmp_path), 1024 * 1024 * 50)  # Need 50MB

        # Test with insufficient space
        with pytest.raises(ConversionError) as exc_info:
            check_disk_space(str(tmp_path), 1024 * 1024 * 200)  # Need 200MB
        assert exc_info.value.error_code == ErrorCodes.DISK_SPACE_ERROR

        # Test with invalid path
        with pytest.raises(ConversionError) as exc_info:
            check_disk_space("/nonexistent/path", 1024)
        assert exc_info.value.error_code == ErrorCodes.FILESYSTEM_ERROR


def test_clean_filename() -> None:
    """Test filename cleaning."""
    # Test basic cleaning
    assert clean_filename("Test File.txt") == "Test_File.txt"

    # Test special characters
    assert clean_filename("Test/File:*?.txt") == "Test_File.txt"

    # Test spaces
    assert clean_filename("  Test  File  .txt  ") == "Test_File.txt"

    # Test empty string
    assert clean_filename("") == ""

    # Test only special characters
    assert clean_filename("/:*?<>|") == ""


def test_format_time() -> None:
    """Test time formatting."""
    # Test zero
    assert format_time(0) == "00:00.000"

    # Test seconds
    assert format_time(12.345) == "00:12.345"

    # Test minutes
    assert format_time(65.432) == "01:05.432"

    # Test hours
    assert format_time(3661.789) == "01:01:01.789"

    # Test rounding
    assert format_time(12.3456789) == "00:12.346"


def test_logger(caplog):
    """Test logger functionality."""
    test_message = "Test log message"

    # Test info logging
    logger.info(test_message)
    assert test_message in caplog.text
    assert "INFO" in caplog.text

    # Test error logging
    error_message = "Test error message"
    logger.error(error_message)
    assert error_message in caplog.text
    assert "ERROR" in caplog.text

    # Test warning logging
    warning_message = "Test warning message"
    logger.warning(warning_message)
    assert warning_message in caplog.text
    assert "WARNING" in caplog.text
