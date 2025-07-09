"""Tests for PDFManager class."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import json
from datetime import datetime, timedelta

from compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager import PDFManager


class TestPDFManager(unittest.TestCase):
    """Test PDFManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_drive_store = Mock()
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_initialization(self, mock_home):
        """Test PDFManager initialization."""
        mock_home.return_value = self.temp_dir

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        self.assertEqual(manager.drive_store, self.mock_drive_store)
        self.assertTrue(manager.cache_dir.exists())
        # Metadata file is created on first save, not on initialization
        self.assertEqual(manager.metadata_file, manager.cache_dir / "pdf_metadata.json")

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_store_pdf_success(self, mock_home):
        """Test successful PDF storage."""
        mock_home.return_value = self.temp_dir
        self.mock_drive_store.upload_pdf.return_value = "drive_file_id"

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        # Create test PDF file
        test_pdf = self.temp_dir / "test.pdf"
        test_pdf.write_bytes(b"mock pdf content")

        metadata = {"venue": "Test Conference", "year": 2024}
        result = manager.store_pdf("test_paper_1", test_pdf, metadata)

        self.assertTrue(result)
        self.mock_drive_store.upload_pdf.assert_called_once()

        # Check metadata was saved
        with open(manager.metadata_file, "r") as f:
            saved_metadata = json.load(f)

        self.assertIn("test_paper_1", saved_metadata)
        self.assertEqual(
            saved_metadata["test_paper_1"]["metadata"]["venue"], "Test Conference"
        )

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_store_pdf_failure(self, mock_home):
        """Test PDF storage failure."""
        mock_home.return_value = self.temp_dir
        self.mock_drive_store.upload_pdf.return_value = None

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        # Create test PDF file
        test_pdf = self.temp_dir / "test.pdf"
        test_pdf.write_bytes(b"mock pdf content")

        metadata = {"venue": "Test Conference", "year": 2024}
        result = manager.store_pdf("test_paper_1", test_pdf, metadata)

        self.assertFalse(result)

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_get_pdf_for_analysis_cached(self, mock_home):
        """Test PDF retrieval from cache."""
        mock_home.return_value = self.temp_dir

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        # Create cached file
        cached_file = manager.cache_dir / "test_paper_1.pdf"
        cached_file.write_bytes(b"cached pdf content")

        # Add metadata
        manager.metadata["test_paper_1"] = {
            "drive_file_id": "drive_id",
            "cached_at": datetime.utcnow().isoformat(),
            "venue": "Test Conference",
        }
        manager._save_metadata()

        result = manager.get_pdf_for_analysis("test_paper_1")

        self.assertEqual(result, cached_file)
        self.mock_drive_store.download_pdf.assert_not_called()  # Should not download from Drive

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_get_pdf_for_analysis_download(self, mock_home):
        """Test PDF download from Drive."""
        mock_home.return_value = self.temp_dir

        # Mock successful download
        def mock_download(file_id, destination):
            destination.write_bytes(b"downloaded pdf content")

        self.mock_drive_store.download_pdf.side_effect = mock_download

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        # Ensure no cached file exists
        potential_cached_file = manager.cache_dir / "test_paper_1.pdf"
        if potential_cached_file.exists():
            potential_cached_file.unlink()

        # Add metadata without cached file
        manager.metadata["test_paper_1"] = {
            "drive_file_id": "drive_id",
            "venue": "Test Conference",
        }
        manager._save_metadata()

        result = manager.get_pdf_for_analysis("test_paper_1")

        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        self.assertEqual(result.read_bytes(), b"downloaded pdf content")

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_get_pdf_for_analysis_not_found(self, mock_home):
        """Test PDF retrieval for non-existent paper."""
        mock_home.return_value = self.temp_dir

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        result = manager.get_pdf_for_analysis("nonexistent_paper")

        self.assertIsNone(result)

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_cleanup_cache(self, mock_home):
        """Test cache cleanup functionality."""
        mock_home.return_value = self.temp_dir

        manager = PDFManager(self.mock_drive_store, cache_ttl_hours=1)

        # Create old cached file
        old_file = manager.cache_dir / "old_paper.pdf"
        old_file.write_bytes(b"old content")

        # Create recent cached file
        recent_file = manager.cache_dir / "recent_paper.pdf"
        recent_file.write_bytes(b"recent content")

        # Add metadata
        old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        recent_time = datetime.utcnow().isoformat()

        manager.metadata["old_paper"] = {
            "drive_file_id": "old_id",
            "cached_at": old_time,
        }
        manager.metadata["recent_paper"] = {
            "drive_file_id": "recent_id",
            "cached_at": recent_time,
        }
        manager._save_metadata()

        # Run cleanup
        cleaned_count = manager.cleanup_cache()

        self.assertEqual(cleaned_count, 1)
        self.assertFalse(old_file.exists())
        self.assertTrue(recent_file.exists())

    @patch("compute_forecast.pipeline.pdf_acquisition.storage.pdf_manager.Path.home")
    def test_get_statistics(self, mock_home):
        """Test statistics generation."""
        mock_home.return_value = self.temp_dir

        manager = PDFManager(self.mock_drive_store, cache_dir=str(self.temp_dir))

        # Create some test files and metadata
        test_file = manager.cache_dir / "test_paper.pdf"
        test_file.write_bytes(b"test content")

        # Update metadata directly on the manager instance
        manager.metadata["test_paper"] = {
            "drive_file_id": "test_id",
            "venue": "Test Conference",
            "cached_at": datetime.utcnow().isoformat(),
        }
        manager._save_metadata()

        stats = manager.get_statistics()

        self.assertEqual(stats["total_papers"], 1)
        self.assertEqual(stats["cache_stats"]["total_files"], 1)
        self.assertGreater(stats["cache_stats"]["total_size_bytes"], 0)
        self.assertTrue(stats["drive_connected"])


if __name__ == "__main__":
    unittest.main()
