"""Tests for PDF cache manager."""

import tempfile
from pathlib import Path
import pytest

from compute_forecast.pdf_download.cache_manager import PDFCacheManager


class TestPDFCacheManager:
    """Test suite for PDFCacheManager."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create a cache manager instance with temp cache."""
        return PDFCacheManager(cache_dir=str(temp_cache_dir))

    def test_remove_from_cache_existing_file(self, cache_manager):
        """Test removing an existing file from cache."""
        paper_id = "test-paper"
        # Create a cached file
        cache_path = cache_manager.get_cache_path(paper_id)
        cache_path.write_bytes(b"PDF content")

        # Remove it
        result = cache_manager.remove_from_cache(paper_id)

        assert result is True
        assert not cache_path.exists()

    def test_remove_from_cache_non_existing_file(self, cache_manager):
        """Test removing a non-existing file from cache."""
        paper_id = "non-existent"

        # Try to remove non-existing file
        result = cache_manager.remove_from_cache(paper_id)

        assert result is False
