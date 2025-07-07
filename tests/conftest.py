"""Shared pytest configuration and fixtures for all tests."""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir(tmp_path):
    """Return a temporary directory for test usage."""
    return tmp_path
