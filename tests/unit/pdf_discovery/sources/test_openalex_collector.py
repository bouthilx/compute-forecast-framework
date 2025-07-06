"""Unit tests for OpenAlex PDF Collector."""

import pytest
from unittest.mock import Mock, patch
import time

from compute_forecast.pdf_discovery.sources.openalex_collector import (
    OpenAlexPDFCollector,
)
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper


class TestOpenAlexPDFCollector:
    """Test OpenAlex PDF collector functionality."""

    @pytest.fixture
    def collector(self):
        """Create collector instance."""
        return OpenAlexPDFCollector(email="test@example.com")

    @pytest.fixture
    def mock_paper(self):
        """Create a mock paper."""
        paper = Mock(spec=Paper)
        paper.paper_id = "test_123"
        paper.title = "Test Paper Title"
        paper.doi = "10.1234/test"
        paper.authors = ["Author One", "Author Two"]
        paper.year = 2023
        return paper

    @pytest.fixture
    def openalex_work_with_pdf(self):
        """Mock OpenAlex work response with PDF."""
        return {
            "id": "https://openalex.org/W1234567890",
            "title": "Test Paper Title",
            "doi": "https://doi.org/10.1234/test",
            "primary_location": {
                "is_oa": True,
                "pdf_url": "https://example.com/primary.pdf",
                "license": "cc-by",
            },
            "best_oa_location": {
                "is_oa": True,
                "pdf_url": "https://example.com/best_oa.pdf",
                "license": "cc-by",
            },
            "authorships": [
                {
                    "author": {"display_name": "Author One"},
                    "institutions": [
                        {
                            "id": "https://openalex.org/I162448124",
                            "display_name": "Mila",
                        }
                    ],
                }
            ],
        }

    @pytest.fixture
    def openalex_work_without_pdf(self):
        """Mock OpenAlex work response without PDF."""
        return {
            "id": "https://openalex.org/W9876543210",
            "title": "Test Paper Without PDF",
            "doi": "https://doi.org/10.1234/test2",
            "primary_location": {"is_oa": False, "pdf_url": None},
            "best_oa_location": None,
        }

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.source_name == "openalex"
        assert collector.email == "test@example.com"
        assert collector.supports_batch is True
        assert collector.batch_size == 200  # OpenAlex max
        assert "mailto:test@example.com" in collector.headers["User-Agent"]

    def test_initialization_without_email(self):
        """Test collector initialization without email."""
        collector = OpenAlexPDFCollector()
        assert collector.email is None
        assert "mailto:" not in collector.headers["User-Agent"]

    @patch("requests.get")
    def test_discover_single_with_pdf(
        self, mock_get, collector, mock_paper, openalex_work_with_pdf
    ):
        """Test discovering PDF for a single paper."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [openalex_work_with_pdf],
            "meta": {"count": 1},
        }
        mock_get.return_value = mock_response

        # Discover PDF
        pdf_record = collector._discover_single(mock_paper)

        # Verify result
        assert isinstance(pdf_record, PDFRecord)
        assert pdf_record.paper_id == "test_123"
        assert pdf_record.pdf_url == "https://example.com/best_oa.pdf"
        assert pdf_record.source == "openalex"
        assert pdf_record.confidence_score == 0.9  # Found by DOI
        assert pdf_record.license == "cc-by"
        assert (
            pdf_record.version_info["openalex_id"] == "https://openalex.org/W1234567890"
        )

    @patch("requests.get")
    def test_discover_single_without_pdf(
        self, mock_get, collector, mock_paper, openalex_work_without_pdf
    ):
        """Test handling paper without available PDF."""
        # Mock API response without PDF
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [openalex_work_without_pdf],
            "meta": {"count": 1},
        }
        mock_get.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="No PDF available"):
            collector._discover_single(mock_paper)

    @patch("requests.get")
    def test_discover_single_paper_not_found(self, mock_get, collector, mock_paper):
        """Test handling paper not found in OpenAlex."""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "meta": {"count": 0}}
        mock_get.return_value = mock_response

        # Should raise ValueError
        with pytest.raises(ValueError, match="Paper not found"):
            collector._discover_single(mock_paper)

    @patch("requests.get")
    def test_discover_single_by_title(
        self, mock_get, collector, openalex_work_with_pdf
    ):
        """Test discovering PDF by title search when no DOI."""
        # Create paper without DOI
        paper = Mock(spec=Paper)
        paper.paper_id = "test_456"
        paper.title = "Test Paper Title"
        paper.doi = None
        paper.authors = ["Author One"]

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [openalex_work_with_pdf],
            "meta": {"count": 1},
        }
        mock_get.return_value = mock_response

        # Discover PDF
        pdf_record = collector._discover_single(paper)

        # Verify result
        assert pdf_record.paper_id == "test_456"
        assert pdf_record.confidence_score == 0.8  # Found by title

        # Check that title search was used
        call_args = mock_get.call_args
        assert "filter" in call_args[1]["params"]
        assert "title.search" in call_args[1]["params"]["filter"]

    @patch("requests.get")
    def test_rate_limiting(
        self, mock_get, collector, mock_paper, openalex_work_with_pdf
    ):
        """Test rate limiting between requests."""
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [openalex_work_with_pdf],
            "meta": {"count": 1},
        }
        mock_get.return_value = mock_response

        # Make two rapid requests
        start_time = time.time()
        collector._discover_single(mock_paper)
        collector._discover_single(mock_paper)
        elapsed = time.time() - start_time

        # Should have delayed between requests
        assert elapsed >= collector.rate_limit_delay

    @patch("requests.get")
    def test_batch_discovery(self, mock_get, collector, openalex_work_with_pdf):
        """Test batch PDF discovery."""
        # Create multiple papers
        papers = []
        for i in range(3):
            paper = Mock(spec=Paper)
            paper.paper_id = f"test_{i}"
            paper.title = f"Test Paper {i}"
            paper.doi = f"10.1234/test{i}"
            papers.append(paper)

        # Create unique responses for each paper
        results_data = []
        for i in range(3):
            work = dict(openalex_work_with_pdf)
            work["doi"] = f"https://doi.org/10.1234/test{i}"
            results_data.append(work)

        # Mock batch API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": results_data,
            "meta": {"count": 3},
        }
        mock_get.return_value = mock_response

        # Discover PDFs in batch
        results = collector.discover_pdfs_batch(papers)

        # Verify results
        assert len(results) == 3
        for i, paper in enumerate(papers):
            assert paper.paper_id in results
            assert results[paper.paper_id].pdf_url == "https://example.com/best_oa.pdf"

    @patch("requests.get")
    def test_retry_on_server_error(
        self, mock_get, collector, mock_paper, openalex_work_with_pdf
    ):
        """Test retry logic on server errors."""
        # First two calls fail, third succeeds
        mock_responses = []

        # Server error response
        error_response = Mock()
        error_response.status_code = 500
        mock_responses.extend([error_response, error_response])

        # Success response
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "results": [openalex_work_with_pdf],
            "meta": {"count": 1},
        }
        mock_responses.append(success_response)

        mock_get.side_effect = mock_responses

        # Should succeed after retries
        pdf_record = collector._discover_single(mock_paper)
        assert pdf_record.pdf_url == "https://example.com/best_oa.pdf"
        assert mock_get.call_count == 3

    @patch("requests.get")
    def test_handle_rate_limit(self, mock_get, collector, mock_paper):
        """Test handling rate limit responses."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "2"}
        mock_get.return_value = mock_response

        # Should raise exception after handling
        with pytest.raises(Exception, match="rate limit"):
            collector._discover_single(mock_paper)

    def test_extract_best_pdf_url(self, collector, openalex_work_with_pdf):
        """Test PDF URL extraction logic."""
        # Should prefer best_oa_location
        url = collector._extract_pdf_url(openalex_work_with_pdf)
        assert url == "https://example.com/best_oa.pdf"

        # Test with only primary_location
        work = {
            "primary_location": {
                "is_oa": True,
                "pdf_url": "https://example.com/primary.pdf",
            },
            "best_oa_location": None,
        }
        url = collector._extract_pdf_url(work)
        assert url == "https://example.com/primary.pdf"

        # Test with no PDF
        work = {"primary_location": {"is_oa": False}, "best_oa_location": None}
        assert collector._extract_pdf_url(work) is None

    def test_institution_filtering(self, collector):
        """Test Mila institution filtering."""
        # Enable Mila filtering
        collector.mila_institution_id = "https://openalex.org/I162448124"

        # Paper with Mila author
        work_mila = {
            "authorships": [
                {
                    "institutions": [
                        {
                            "id": "https://openalex.org/I162448124",
                            "display_name": "Mila",
                        }
                    ]
                }
            ]
        }
        assert collector._has_mila_author(work_mila) is True

        # Paper without Mila author
        work_other = {
            "authorships": [
                {
                    "institutions": [
                        {
                            "id": "https://openalex.org/I999999999",
                            "display_name": "Other",
                        }
                    ]
                }
            ]
        }
        assert collector._has_mila_author(work_other) is False
