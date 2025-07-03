"""Integration tests for PDF download functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

import pytest
import requests

from compute_forecast.pdf_download.downloader import SimplePDFDownloader
from compute_forecast.pdf_discovery.core.models import PDFRecord


class TestPDFDownloadIntegration:
    """Integration tests for PDF download with discovery models."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_pdf_records(self):
        """Create sample PDF records for testing."""
        base_time = datetime.now()
        
        return {
            "paper-1": PDFRecord(
                paper_id="paper-1",
                pdf_url="https://arxiv.org/pdf/2101.00001.pdf",
                source="arxiv",
                discovery_timestamp=base_time,
                confidence_score=0.95,
                version_info={"version": "v1"},
                validation_status="valid"
            ),
            "paper-2": PDFRecord(
                paper_id="paper-2",
                pdf_url="https://openaccess.thecvf.com/content/CVPR2021/papers/test.pdf",
                source="cvf",
                discovery_timestamp=base_time,
                confidence_score=0.90,
                version_info={"version": "final"},
                validation_status="valid"
            ),
            "paper-3": PDFRecord(
                paper_id="paper-3",
                pdf_url="https://proceedings.mlr.press/v139/test.pdf",
                source="pmlr",
                discovery_timestamp=base_time,
                confidence_score=0.85,
                version_info={"version": "v2"},
                validation_status="valid"
            ),
        }
    
    @patch("requests.Session.get")
    def test_full_download_workflow(self, mock_get, temp_dir, sample_pdf_records):
        """Test complete download workflow from discovery to cached files."""
        # Setup mock responses
        def mock_response_for_url(url, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/pdf"}
            
            # Different content for each source
            if "arxiv" in url:
                mock_resp.content = b"ArXiv PDF Content " + b"X" * 11000
            elif "cvf" in url:
                mock_resp.content = b"CVF PDF Content " + b"Y" * 12000
            else:
                mock_resp.content = b"PMLR PDF Content " + b"Z" * 13000
            
            mock_resp.raise_for_status = Mock()
            return mock_resp
        
        mock_get.side_effect = mock_response_for_url
        
        # Initialize downloader
        downloader = SimplePDFDownloader(cache_dir=str(temp_dir))
        
        # Download batch
        result = downloader.download_batch(sample_pdf_records, max_workers=3)
        
        # Verify results
        assert result["total"] == 3
        assert result["success_rate"] == 1.0
        assert len(result["successful"]) == 3
        assert len(result["failed"]) == 0
        
        # Verify cached files
        cached_files = list(temp_dir.glob("*.pdf"))
        assert len(cached_files) == 3
        
        # Verify file contents
        paper1_path = temp_dir / "paper-1.pdf"
        assert paper1_path.exists()
        assert b"ArXiv PDF Content" in paper1_path.read_bytes()
        
        # Test cache hit - no new download
        mock_get.reset_mock()
        second_result = downloader.download_batch(sample_pdf_records)
        
        # Should not make any HTTP requests
        mock_get.assert_not_called()
        assert second_result["success_rate"] == 1.0
        
        # Test cache statistics
        stats = downloader.get_cache_stats()
        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] > 30000  # At least 3 * 10KB
    
    @patch("requests.Session.get")
    def test_error_handling_and_recovery(self, mock_get, temp_dir):
        """Test error handling and partial success scenarios."""
        # Create records with mixed success/failure
        records = {
            "success-1": PDFRecord(
                paper_id="success-1",
                pdf_url="https://example.com/good1.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            ),
            "invalid-pdf": PDFRecord(
                paper_id="invalid-pdf",
                pdf_url="https://example.com/notpdf.html",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="valid"
            ),
            "network-error": PDFRecord(
                paper_id="network-error",
                pdf_url="https://example.com/timeout.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.7,
                version_info={},
                validation_status="valid"
            ),
            "success-2": PDFRecord(
                paper_id="success-2",
                pdf_url="https://example.com/good2.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid"
            ),
        }
        
        # Mock varied responses
        def mock_response_for_url(url, **kwargs):
            if "good" in url:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-type": "application/pdf"}
                mock_resp.content = b"Valid PDF " + b"X" * 11000
                mock_resp.raise_for_status = Mock()
                return mock_resp
            elif "notpdf" in url:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-type": "text/html"}
                mock_resp.content = b"<html>Not a PDF</html>"
                mock_resp.raise_for_status = Mock()
                return mock_resp
            else:  # timeout
                raise requests.Timeout("Connection timeout")
        
        mock_get.side_effect = mock_response_for_url
        
        # Initialize downloader
        downloader = SimplePDFDownloader(cache_dir=str(temp_dir))
        
        # Download with mixed results
        with patch("time.sleep"):  # Speed up retries
            result = downloader.download_batch(records, show_progress=False)
        
        # Verify partial success
        assert result["total"] == 4
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 2
        assert result["success_rate"] == 0.5
        
        # Check specific failures
        assert "invalid-pdf" in result["failed"]
        assert "Invalid content type" in result["failed"]["invalid-pdf"]
        assert "network-error" in result["failed"]
        
        # Verify only successful PDFs are cached
        cached_files = list(temp_dir.glob("*.pdf"))
        assert len(cached_files) == 2
        assert (temp_dir / "success-1.pdf").exists()
        assert (temp_dir / "success-2.pdf").exists()
        assert not (temp_dir / "invalid-pdf.pdf").exists()
        assert not (temp_dir / "network-error.pdf").exists()
    
    def test_cache_management(self, temp_dir):
        """Test cache management functionality."""
        downloader = SimplePDFDownloader(cache_dir=str(temp_dir))
        
        # Manually add some files to cache
        for i in range(5):
            pdf_path = temp_dir / f"test-{i}.pdf"
            pdf_path.write_bytes(b"Test PDF content " + b"X" * (1024 * (i + 1)))
        
        # Check cache stats
        stats = downloader.get_cache_stats()
        assert stats["total_files"] == 5
        assert stats["total_size_bytes"] > 5 * 1024
        
        # Clear cache
        cleared = downloader.clear_cache()
        assert cleared == 5
        
        # Verify cache is empty
        stats = downloader.get_cache_stats()
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0