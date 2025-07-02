"""Tests for the PDF downloader module."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future
import pytest
import requests

from src.pdf_download.downloader import SimplePDFDownloader
from src.pdf_discovery.core.models import PDFRecord
from datetime import datetime


class TestSimplePDFDownloader:
    """Test suite for SimplePDFDownloader."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def downloader(self, temp_cache_dir):
        """Create a downloader instance with temp cache."""
        return SimplePDFDownloader(cache_dir=str(temp_cache_dir))
    
    @pytest.fixture
    def sample_pdf_record(self):
        """Create a sample PDF record."""
        return PDFRecord(
            paper_id="test-paper-123",
            pdf_url="https://example.com/paper.pdf",
            source="test-source",
            discovery_timestamp=datetime.now(),
            confidence_score=0.95,
            version_info={"version": "1.0"},
            validation_status="valid"
        )
    
    def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that initialization creates the cache directory."""
        cache_path = temp_cache_dir / "pdf_cache"
        downloader = SimplePDFDownloader(cache_dir=str(cache_path))
        assert cache_path.exists()
        assert cache_path.is_dir()
    
    def test_init_sets_user_agent(self, downloader):
        """Test that the session has proper user agent."""
        assert downloader.session.headers["User-Agent"] == "Mozilla/5.0 (compatible; Academic PDF Collector)"
    
    def test_get_cache_path(self, downloader):
        """Test cache path generation through cache manager."""
        paper_id = "test-123"
        cache_path = downloader.cache_manager.get_cache_path(paper_id)
        assert cache_path.parent == downloader.cache_manager.cache_dir
        assert cache_path.name == "test-123.pdf"
    
    def test_is_cached_returns_true_for_existing_file(self, downloader, temp_cache_dir):
        """Test that cache manager's is_cached returns True for existing files."""
        paper_id = "cached-paper"
        cache_file = temp_cache_dir / f"{paper_id}.pdf"
        cache_file.write_bytes(b"PDF content")
        
        assert downloader.cache_manager.is_cached(paper_id) is True
    
    def test_is_cached_returns_false_for_missing_file(self, downloader):
        """Test that cache manager's is_cached returns False for missing files."""
        assert downloader.cache_manager.is_cached("non-existent") is False
    
    @patch("requests.Session.get")
    def test_download_pdf_uses_cache(self, mock_get, downloader, temp_cache_dir):
        """Test that cached files are not re-downloaded."""
        paper_id = "cached-paper"
        url = "https://example.com/paper.pdf"
        
        # Create cached file
        cache_file = temp_cache_dir / f"{paper_id}.pdf"
        cache_file.write_bytes(b"Cached PDF content")
        
        result = downloader.download_pdf(url, paper_id)
        
        # Should not make HTTP request
        mock_get.assert_not_called()
        assert result == cache_file
        assert result.read_bytes() == b"Cached PDF content"
    
    @patch("requests.Session.get")
    def test_download_pdf_success(self, mock_get, downloader):
        """Test successful PDF download."""
        paper_id = "new-paper"
        url = "https://example.com/paper.pdf"
        pdf_content = b"X" * 11000  # >10KB
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = pdf_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = downloader.download_pdf(url, paper_id)
        
        assert result.exists()
        assert result.read_bytes() == pdf_content
        mock_get.assert_called_once_with(url, timeout=30)
    
    @patch("requests.Session.get")
    def test_download_pdf_validates_content_type(self, mock_get, downloader):
        """Test that non-PDF content types are rejected."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"<html>Not a PDF</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="Invalid content type"):
            downloader.download_pdf("https://example.com/notpdf", "paper-123")
    
    @patch("requests.Session.get")
    def test_download_pdf_validates_file_size(self, mock_get, downloader):
        """Test that files smaller than 10KB are rejected."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = b"Too small"  # Less than 10KB
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="PDF file too small"):
            downloader.download_pdf("https://example.com/small.pdf", "paper-123")
    
    @patch("requests.Session.get")
    def test_download_pdf_retry_on_failure(self, mock_get, downloader):
        """Test exponential backoff retry logic."""
        url = "https://example.com/paper.pdf"
        paper_id = "retry-paper"
        
        # First two attempts fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = requests.RequestException("Server error")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.headers = {"content-type": "application/pdf"}
        mock_response_success.content = b"X" * 11000  # >10KB
        mock_response_success.raise_for_status = Mock()
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        with patch("time.sleep") as mock_sleep:
            result = downloader.download_pdf(url, paper_id)
        
        assert result.exists()
        assert mock_get.call_count == 3
        # Check exponential backoff delays
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry after 1 second
        mock_sleep.assert_any_call(2)  # Second retry after 2 seconds
    
    @patch("requests.Session.get")
    def test_download_pdf_max_retries_exceeded(self, mock_get, downloader):
        """Test that download fails after max retries."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.RequestException("Server error")
        mock_get.return_value = mock_response
        
        with patch("time.sleep"):  # Speed up test
            with pytest.raises(requests.RequestException):
                downloader.download_pdf("https://example.com/fail.pdf", "fail-paper")
        
        assert mock_get.call_count == 3
    
    def test_download_batch_empty_input(self, downloader):
        """Test batch download with empty input."""
        result = downloader.download_batch({})
        assert result["successful"] == {}
        assert result["failed"] == {}
        assert result["total"] == 0
        assert result["success_rate"] == 0.0
    
    @patch("requests.Session.get")
    def test_download_batch_parallel_execution(self, mock_get, downloader):
        """Test that batch downloads execute in parallel."""
        # Create multiple PDF records
        pdf_records = {
            f"paper-{i}": PDFRecord(
                paper_id=f"paper-{i}",
                pdf_url=f"https://example.com/paper{i}.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            )
            for i in range(5)
        }
        
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = b"X" * 11000
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        start_time = time.time()
        result = downloader.download_batch(pdf_records, max_workers=3)
        elapsed = time.time() - start_time
        
        # Should complete faster than sequential (5 * 0.1s delay in mock)
        assert elapsed < 0.5  # Generous margin for CI systems
        assert len(result["successful"]) == 5
        assert len(result["failed"]) == 0
        assert result["success_rate"] == 1.0
    
    @patch("requests.Session.get")
    def test_download_batch_mixed_results(self, mock_get, downloader):
        """Test batch download with some successes and failures."""
        pdf_records = {
            "success-1": PDFRecord(
                paper_id="success-1",
                pdf_url="https://example.com/success1.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            ),
            "fail-1": PDFRecord(
                paper_id="fail-1",
                pdf_url="https://example.com/fail1.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            ),
            "success-2": PDFRecord(
                paper_id="success-2",
                pdf_url="https://example.com/success2.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            ),
        }
        
        # Mock mixed responses
        def mock_response_for_url(url, **kwargs):
            if "fail" in url:
                mock_fail = Mock()
                mock_fail.raise_for_status.side_effect = requests.RequestException("Failed")
                return mock_fail
            else:
                mock_success = Mock()
                mock_success.status_code = 200
                mock_success.headers = {"content-type": "application/pdf"}
                mock_success.content = b"X" * 11000
                mock_success.raise_for_status = Mock()
                return mock_success
        
        mock_get.side_effect = mock_response_for_url
        
        with patch("time.sleep"):  # Speed up retries
            result = downloader.download_batch(pdf_records)
        
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 1
        assert "fail-1" in result["failed"]
        assert result["success_rate"] == pytest.approx(2/3)
    
    @patch("src.pdf_download.downloader.Progress")
    @patch("requests.Session.get")
    def test_download_batch_progress_tracking(self, mock_get, mock_progress_class, downloader):
        """Test that batch download shows progress bar."""
        pdf_records = {
            f"paper-{i}": PDFRecord(
                paper_id=f"paper-{i}",
                pdf_url=f"https://example.com/paper{i}.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            )
            for i in range(3)
        }
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = b"X" * 11000
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock rich Progress to track progress updates
        mock_progress = MagicMock()
        mock_progress_class.return_value.__enter__.return_value = mock_progress
        mock_task_id = 1
        mock_progress.add_task.return_value = mock_task_id
        
        downloader.download_batch(pdf_records, show_progress=True)
        
        # Verify progress bar was created and updated
        mock_progress_class.assert_called_once()
        mock_progress.add_task.assert_called_once_with("Downloading PDFs", total=3)
        assert mock_progress.update.call_count == 3  # One update per PDF
    
    def test_get_cache_stats(self, downloader, temp_cache_dir):
        """Test cache statistics reporting."""
        # Create some cached files
        for i in range(3):
            cache_file = temp_cache_dir / f"paper-{i}.pdf"
            cache_file.write_bytes(b"X" * (1024 * (i + 1)))  # Different sizes
        
        stats = downloader.get_cache_stats()
        
        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] == 1024 + 2048 + 3072
        assert stats["cache_dir"] == str(downloader.cache_manager.cache_dir)
    
    def test_clear_cache(self, downloader, temp_cache_dir):
        """Test cache clearing functionality."""
        # Create cached files
        for i in range(3):
            cache_file = temp_cache_dir / f"paper-{i}.pdf"
            cache_file.write_bytes(b"PDF content")
        
        assert len(list(temp_cache_dir.glob("*.pdf"))) == 3
        
        cleared = downloader.clear_cache()
        
        assert cleared == 3
        assert len(list(temp_cache_dir.glob("*.pdf"))) == 0