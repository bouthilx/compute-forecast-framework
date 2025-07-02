"""Tests for PDFManager class."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
import os
from datetime import datetime, timedelta

from src.pdf_storage.pdf_manager import PDFManager


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

    @patch('src.pdf_storage.pdf_manager.Path.home')
    def test_initialization(self, mock_home):
        """Test PDFManager initialization."""
        mock_home.return_value = self.temp_dir
        
        manager = PDFManager(self.mock_drive_store)
        
        self.assertEqual(manager.drive_store, self.mock_drive_store)
        self.assertTrue(manager.cache_dir.exists())
        self.assertTrue(manager.metadata_file.exists())

    @patch('src.pdf_storage.pdf_manager.Path.home')
    def test_store_pdf_success(self, mock_home):
        """Test successful PDF storage."""
        mock_home.return_value = self.temp_dir
        self.mock_drive_store.upload_file.return_value = "drive_file_id"
        
        manager = PDFManager(self.mock_drive_store)
        
        # Create test PDF file
        test_pdf = self.temp_dir / "test.pdf"
        test_pdf.write_bytes(b"mock pdf content")
        
        metadata = {"venue": "Test Conference", "year": 2024}
        result = manager.store_pdf("test_paper_1", test_pdf, metadata)
        
        self.assertTrue(result)
        self.mock_drive_store.upload_file.assert_called_once()
        
        # Check metadata was saved
        with open(manager.metadata_file, 'r') as f:
            saved_metadata = json.load(f)
        
        self.assertIn("test_paper_1", saved_metadata)
        self.assertEqual(saved_metadata["test_paper_1"]["venue"], "Test Conference")

    @patch('src.pdf_storage.pdf_manager.Path.home')
    def test_store_pdf_failure(self, mock_home):
        """Test PDF storage failure."""
        mock_home.return_value = self.temp_dir
        self.mock_drive_store.upload_file.return_value = None
        
        manager = PDFManager(self.mock_drive_store)
        
        # Create test PDF file
        test_pdf = self.temp_dir / "test.pdf"
        test_pdf.write_bytes(b"mock pdf content")
        
        metadata = {"venue": "Test Conference", "year": 2024}
        result = manager.store_pdf("test_paper_1", test_pdf, metadata)
        
        self.assertFalse(result)

    @patch('src.pdf_storage.pdf_manager.Path.home')
    @patch('src.pdf_storage.pdf_manager.requests.get')
    def test_get_pdf_for_analysis_cached(self, mock_get, mock_home):
        """Test PDF retrieval from cache."""
        mock_home.return_value = self.temp_dir
        
        manager = PDFManager(self.mock_drive_store)
        
        # Create cached file
        cached_file = manager.cache_dir / "test_paper_1.pdf"
        cached_file.write_bytes(b"cached pdf content")
        
        # Add metadata
        metadata = {
            "test_paper_1": {
                "drive_file_id": "drive_id",
                "cached_at": datetime.utcnow().isoformat(),
                "venue": "Test Conference"
            }
        }
        with open(manager.metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        result = manager.get_pdf_for_analysis("test_paper_1")
        
        self.assertEqual(result, cached_file)
        mock_get.assert_not_called()  # Should not download from Drive

    @patch('src.pdf_storage.pdf_manager.Path.home')
    @patch('src.pdf_storage.pdf_manager.requests.get')
    def test_get_pdf_for_analysis_download(self, mock_get, mock_home):
        """Test PDF download from Drive."""
        mock_home.return_value = self.temp_dir
        
        # Mock successful download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"downloaded pdf content"
        mock_get.return_value = mock_response
        
        manager = PDFManager(self.mock_drive_store)
        
        # Add metadata without cached file
        metadata = {
            "test_paper_1": {
                "drive_file_id": "drive_id",
                "venue": "Test Conference"
            }
        }
        with open(manager.metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        result = manager.get_pdf_for_analysis("test_paper_1")
        
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        self.assertEqual(result.read_bytes(), b"downloaded pdf content")

    @patch('src.pdf_storage.pdf_manager.Path.home')
    def test_get_pdf_for_analysis_not_found(self, mock_home):
        """Test PDF retrieval for non-existent paper."""
        mock_home.return_value = self.temp_dir
        
        manager = PDFManager(self.mock_drive_store)
        
        result = manager.get_pdf_for_analysis("nonexistent_paper")
        
        self.assertIsNone(result)

    @patch('src.pdf_storage.pdf_manager.Path.home')
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
        
        metadata = {
            "old_paper": {
                "drive_file_id": "old_id",
                "cached_at": old_time
            },
            "recent_paper": {
                "drive_file_id": "recent_id",
                "cached_at": recent_time
            }
        }
        with open(manager.metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        # Run cleanup
        cleaned_count = manager.cleanup_cache()
        
        self.assertEqual(cleaned_count, 1)
        self.assertFalse(old_file.exists())
        self.assertTrue(recent_file.exists())

    @patch('src.pdf_storage.pdf_manager.Path.home')
    def test_get_statistics(self, mock_home):
        """Test statistics generation."""
        mock_home.return_value = self.temp_dir
        
        manager = PDFManager(self.mock_drive_store)
        
        # Create some test files and metadata
        test_file = manager.cache_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        metadata = {
            "test_paper": {
                "drive_file_id": "test_id",
                "venue": "Test Conference",
                "cached_at": datetime.utcnow().isoformat()
            }
        }
        with open(manager.metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        stats = manager.get_statistics()
        
        self.assertEqual(stats["total_papers"], 1)
        self.assertEqual(stats["cache_stats"]["total_files"], 1)
        self.assertGreater(stats["cache_stats"]["total_size_bytes"], 0)
        self.assertTrue(stats["drive_connected"])


if __name__ == '__main__':
    unittest.main()