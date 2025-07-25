"""Unit tests for CORE API collector."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.core_collector import (
    COREPDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from datetime import datetime
from compute_forecast.pipeline.pdf_acquisition.discovery.utils import (
    APIError,
    NoResultsError,
    NoPDFFoundError,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
    doi: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
        doi=doi,
    )


class TestCOREPDFCollector:
    """Tests for CORE PDF collector."""

    @pytest.fixture
    def collector(self):
        """Create a CORE collector instance."""
        return COREPDFCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return create_test_paper(
            paper_id="test_paper_1",
            title="Test Paper on Deep Learning",
            authors=[Author(name="Author A"), Author(name="Author B")],
            year=2023,
            venue="Test Conference",
            citation_count=50,
        )

    @pytest.fixture
    def core_api_response(self):
        """Mock CORE API response with PDF URL."""
        return {
            "totalHits": 1,
            "limit": 10,
            "offset": 0,
            "scrollId": None,
            "results": [
                {
                    "id": "core:123456",
                    "doi": "10.1234/test.2023.001",
                    "title": "Test Paper on Deep Learning",
                    "downloadUrl": "https://core.ac.uk/download/pdf/123456.pdf",
                    "repositoryDocument": {
                        "pdfStatus": 1,
                        "pdfSize": 2048576,
                        "pdfUrl": "https://core.ac.uk/download/pdf/123456.pdf",
                    },
                    "language": {"name": "English"},
                    "publishedDate": "2023-01-01",
                }
            ],
        }

    def test_discover_single_success(self, collector, sample_paper, core_api_response):
        """Test successful PDF discovery from CORE."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = core_api_response
            mock_get.return_value = mock_response

            result = collector._discover_single(sample_paper)

            assert isinstance(result, PDFRecord)
            assert result.paper_id == sample_paper.paper_id
            assert result.pdf_url == "https://core.ac.uk/download/pdf/123456.pdf"
            assert result.source == "core"
            assert result.confidence_score == 0.9
            assert result.validation_status == "verified"
            assert result.file_size_bytes == 2048576

    def test_discover_single_no_pdf(self, collector, sample_paper):
        """Test when CORE has no PDF available."""
        response = {
            "totalHits": 1,
            "results": [
                {
                    "id": "core:123456",
                    "doi": "10.1234/test.2023.001",
                    "title": "Test Paper on Deep Learning",
                    "downloadUrl": None,
                    "repositoryDocument": {"pdfStatus": 0, "pdfUrl": None},
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response
            mock_get.return_value = mock_response

            with pytest.raises(NoPDFFoundError, match="No PDF found"):
                collector._discover_single(sample_paper)

    def test_discover_single_no_results(self, collector, sample_paper):
        """Test when CORE returns no results."""
        response = {"totalHits": 0, "results": []}

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response
            mock_get.return_value = mock_response

            with pytest.raises(NoResultsError, match="No results found"):
                collector._discover_single(sample_paper)

    def test_discover_single_api_error(self, collector, sample_paper):
        """Test handling of API errors."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            with pytest.raises(APIError, match="CORE API error"):
                collector._discover_single(sample_paper)

    def test_search_by_title(self, collector, sample_paper, core_api_response):
        """Test searching by title when DOI is not available."""
        paper_without_doi = create_test_paper(
            paper_id="test_paper_2",
            title="Test Paper on Deep Learning",
            authors=[Author(name="Author A")],
            year=2023,
            venue="Test Conference",
            citation_count=10,
        )

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = core_api_response
            mock_get.return_value = mock_response

            result = collector._discover_single(paper_without_doi)

            assert result.paper_id == paper_without_doi.paper_id
            assert result.pdf_url == "https://core.ac.uk/download/pdf/123456.pdf"

            # Verify title search was used
            call_args = mock_get.call_args
            assert "title:" in call_args[1]["params"]["q"]

    def test_rate_limiting(self, collector, sample_paper, core_api_response):
        """Test that rate limiting is applied."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = core_api_response
            mock_get.return_value = mock_response

            # Make multiple requests
            with patch("time.sleep") as mock_sleep:
                collector._discover_single(sample_paper)
                collector._discover_single(sample_paper)

                # Verify rate limiter was called
                assert mock_sleep.called

    def test_extract_best_pdf_url(self, collector, core_api_response):
        """Test PDF URL extraction logic."""
        result = core_api_response["results"][0]

        # Test with downloadUrl
        pdf_url = collector._extract_pdf_url(result)
        assert pdf_url == "https://core.ac.uk/download/pdf/123456.pdf"

        # Test with only repositoryDocument.pdfUrl
        result["downloadUrl"] = None
        pdf_url = collector._extract_pdf_url(result)
        assert pdf_url == "https://core.ac.uk/download/pdf/123456.pdf"

        # Test with no PDF URLs
        result["repositoryDocument"]["pdfUrl"] = None
        pdf_url = collector._extract_pdf_url(result)
        assert pdf_url is None

    def test_build_search_query(self, collector):
        """Test search query building."""
        # With DOI
        paper_with_doi = create_test_paper(
            paper_id="test1",
            title="Test Paper",
            year=2023,
            authors=[Author(name="Test Author")],
            venue="Test Venue",
            citation_count=0,
            doi="10.1234/test",
        )
        query = collector._build_search_query(paper_with_doi)
        assert query == 'doi:"10.1234/test"'

        # Without DOI
        paper_without_doi = create_test_paper(
            paper_id="test2",
            title="Test Paper on Machine Learning",
            year=2023,
            authors=[Author(name="Test Author")],
            venue="Test Venue",
            citation_count=0,
        )
        query = collector._build_search_query(paper_without_doi)
        assert query == 'title:"Test Paper on Machine Learning"'
