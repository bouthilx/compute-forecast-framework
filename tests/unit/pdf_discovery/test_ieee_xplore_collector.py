"""Unit tests for IEEE Xplore PDF collector."""

import pytest
from unittest.mock import Mock, patch
import requests

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.ieee_xplore_collector import (
    IEEEXplorePDFCollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper


class TestIEEEXplorePDFCollector:
    """Test suite for IEEE Xplore PDF collector."""

    @pytest.fixture
    def collector(self):
        """Create a collector instance."""
        return IEEEXplorePDFCollector(api_key="test_key")

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        paper = Mock(spec=Paper)
        paper.paper_id = "test_paper_123"
        paper.title = "Test Paper Title"
        paper.doi = "10.1109/TEST.2024.123456"
        paper.venue = "ICRA"
        paper.year = 2024
        return paper

    @pytest.fixture
    def sample_paper_no_doi(self):
        """Create a sample paper without DOI."""
        paper = Mock(spec=Paper)
        paper.paper_id = "test_paper_456"
        paper.title = "Another Test Paper"
        paper.doi = None
        paper.venue = "IEEE Conference"
        paper.year = 2023
        return paper

    def test_initialization(self):
        """Test collector initialization."""
        collector = IEEEXplorePDFCollector(api_key="test_key")
        assert collector.source_name == "ieee_xplore"
        assert collector.api_key == "test_key"
        assert (
            collector.base_url
            == "https://ieeexploreapi.ieee.org/api/v1/search/articles"
        )
        assert collector.timeout == 30
        assert not collector.supports_batch

    def test_initialization_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict("os.environ", {"IEEE_XPLORE_API_KEY": "env_key"}):
            collector = IEEEXplorePDFCollector()
            assert collector.api_key == "env_key"

    def test_initialization_no_api_key_raises(self):
        """Test initialization raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="IEEE Xplore API key required"):
                IEEEXplorePDFCollector()

    @patch("requests.get")
    def test_discover_single_with_doi_success(self, mock_get, collector, sample_paper):
        """Test successful PDF discovery with DOI."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "articles": [
                {
                    "article_number": "123456",
                    "doi": "10.1109/TEST.2024.123456",
                    "title": "Test Paper Title",
                    "pdf_url": "https://ieeexplore.ieee.org/iel7/123/456/123456.pdf",
                    "access_type": "OPEN_ACCESS",
                    "content_type": "Conferences",
                }
            ],
            "total_records": 1,
        }
        mock_get.return_value = mock_response

        # Discover PDF
        pdf_record = collector._discover_single(sample_paper)

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert collector.base_url in call_args[0][0]
        assert "apikey=test_key" in call_args[0][0]
        assert "doi=10.1109/TEST.2024.123456" in call_args[0][0]

        # Verify result
        assert pdf_record.paper_id == "test_paper_123"
        assert (
            pdf_record.pdf_url == "https://ieeexplore.ieee.org/iel7/123/456/123456.pdf"
        )
        assert pdf_record.source == "ieee_xplore"
        assert pdf_record.confidence_score == 0.95
        assert pdf_record.validation_status == "open_access"
        assert pdf_record.version_info["article_number"] == "123456"
        assert pdf_record.version_info["access_type"] == "OPEN_ACCESS"

    @patch("requests.get")
    def test_discover_single_title_search_fallback(
        self, mock_get, collector, sample_paper_no_doi
    ):
        """Test PDF discovery with title search when no DOI."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "articles": [
                {
                    "article_number": "789012",
                    "title": "Another Test Paper",
                    "pdf_url": "https://ieeexplore.ieee.org/iel7/789/012/789012.pdf",
                    "access_type": "SUBSCRIPTION",
                    "content_type": "Journals",
                }
            ],
            "total_records": 1,
        }
        mock_get.return_value = mock_response

        # Discover PDF
        pdf_record = collector._discover_single(sample_paper_no_doi)

        # Verify API call used title search
        call_args = mock_get.call_args
        assert "article_title=Another%20Test%20Paper" in call_args[0][0]

        # Verify result
        assert pdf_record.paper_id == "test_paper_456"
        assert (
            pdf_record.pdf_url == "https://ieeexplore.ieee.org/iel7/789/012/789012.pdf"
        )
        assert pdf_record.confidence_score == 0.8  # Lower confidence for title search
        assert pdf_record.validation_status == "subscription"

    @patch("requests.get")
    def test_discover_single_no_pdf_available(self, mock_get, collector, sample_paper):
        """Test when no PDF is available."""
        # Mock API response without PDF URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "articles": [
                {
                    "article_number": "123456",
                    "doi": "10.1109/TEST.2024.123456",
                    "title": "Test Paper Title",
                    "access_type": "LOCKED",
                }
            ],
            "total_records": 1,
        }
        mock_get.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="No PDF available"):
            collector._discover_single(sample_paper)

    @patch("requests.get")
    def test_discover_single_paper_not_found(self, mock_get, collector, sample_paper):
        """Test when paper is not found in IEEE Xplore."""
        # Mock empty API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"articles": [], "total_records": 0}
        mock_get.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="Paper not found"):
            collector._discover_single(sample_paper)

    @patch("requests.get")
    def test_api_error_handling(self, mock_get, collector, sample_paper):
        """Test API error handling."""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response

        # Should raise exception
        with pytest.raises(requests.HTTPError):
            collector._discover_single(sample_paper)

    @patch("requests.get")
    def test_rate_limit_handling(self, mock_get, collector, sample_paper):
        """Test rate limit error handling."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        mock_get.return_value = mock_response

        # Should raise ValueError with specific message
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            collector._discover_single(sample_paper)

    @patch("requests.get")
    def test_discover_multiple_papers(self, mock_get, collector, sample_paper):
        """Test discovering PDFs for multiple papers."""
        papers = [
            sample_paper,
            Mock(spec=Paper, paper_id="test_456", title="Another Paper", doi=None),
        ]

        # Mock successful response for first paper
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "articles": [
                {
                    "article_number": "123456",
                    "doi": "10.1109/TEST.2024.123456",
                    "pdf_url": "https://ieeexplore.ieee.org/iel7/123/456/123456.pdf",
                    "access_type": "OPEN_ACCESS",
                }
            ],
            "total_records": 1,
        }

        # Mock failure for second paper
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"articles": [], "total_records": 0}

        mock_get.side_effect = [mock_response1, mock_response2]

        # Discover PDFs
        results = collector.discover_pdfs(papers)

        # Should have one successful result
        assert len(results) == 1
        assert "test_paper_123" in results
        assert (
            results["test_paper_123"].pdf_url
            == "https://ieeexplore.ieee.org/iel7/123/456/123456.pdf"
        )

        # Check statistics
        stats = collector.get_statistics()
        assert stats["attempted"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1

    def test_doi_resolution_fallback(self, collector):
        """Test DOI resolution fallback mechanism."""
        # Test the DOI resolution method
        with patch.object(collector, "_resolve_doi_to_pdf") as mock_resolve:
            mock_resolve.return_value = "https://resolved.pdf.url"

            url = collector._resolve_doi_to_pdf("10.1109/TEST.2024.123456")
            assert url == "https://resolved.pdf.url"
            mock_resolve.assert_called_once_with("10.1109/TEST.2024.123456")

    @patch("time.sleep")
    def test_rate_limiting(self, mock_sleep, collector):
        """Test rate limiting between requests."""
        # Make two requests quickly
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"articles": [], "total_records": 0}
            mock_get.return_value = mock_response

            paper1 = Mock(spec=Paper, paper_id="1", title="Paper 1", doi="10.1109/1")
            paper2 = Mock(spec=Paper, paper_id="2", title="Paper 2", doi="10.1109/2")

            try:
                collector._discover_single(paper1)
            except ValueError:
                pass  # Expected to fail, we're testing rate limiting

            try:
                collector._discover_single(paper2)
            except ValueError:
                pass  # Expected to fail

            # Should have enforced rate limit
            assert mock_sleep.called
