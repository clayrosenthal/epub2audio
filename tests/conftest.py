"""Shared test fixtures and configuration."""

import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def setup_temp_dir(tmp_path: str) -> Generator[None, None, None]:
    """Set up and clean up temporary directory for tests."""
    # Create temp directory if it doesn't exist
    os.makedirs(tmp_path, exist_ok=True)

    yield

    # Clean up after tests
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)


@pytest.fixture
def test_data_dir() -> Path:
    """Get the test data directory path."""
    return Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def setup_test_data(test_data_dir):
    """Set up test data directory."""
    os.makedirs(test_data_dir, exist_ok=True)
    yield
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Skip integration tests unless explicitly requested
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="need --run-integration option to run"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )
