"""Unit tests for PubMed Central PDF collector."""

import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector import (
    PubMedCentralCollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
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
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
        doi=doi,
    )


class TestPubMedCentralCollector:
    """Test PubMed Central PDF collector implementation."""

    @pytest.fixture
    def collector(self):
        """Create a PubMed Central collector instance."""
        return PubMedCentralCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return create_test_paper(
            paper_id="test_paper_123",
            title="Deep Learning for Medical Image Analysis",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            citation_count=50,
            venue="Journal of Medical Imaging",
        )

    @pytest.fixture
    def esearch_response_with_pmc(self):
        """Mock E-utilities search response with PMC ID."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <eSearchResult>
            <Count>1</Count>
            <RetMax>1</RetMax>
            <RetStart>0</RetStart>
            <IdList>
                <Id>12345678</Id>
            </IdList>
        </eSearchResult>"""

    @pytest.fixture
    def esummary_response_with_pmc(self):
        """Mock E-utilities summary response with PMC ID."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <eSummaryResult>
            <DocSum>
                <Id>12345678</Id>
                <Item Name="pmc" Type="String">PMC9876543</Item>
                <Item Name="Title" Type="String">Deep Learning for Medical Image Analysis</Item>
                <Item Name="DOI" Type="String">10.1234/jmi.2023.123456</Item>
            </DocSum>
        </eSummaryResult>"""

    def test_collector_initialization(self, collector):
        """Test collector is properly initialized."""
        assert collector.source_name == "pubmed_central"
        assert collector.base_url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        assert collector.pdf_base_url == "https://www.ncbi.nlm.nih.gov/pmc/articles"
        assert collector.timeout == 30
        assert collector.delay_between_requests == 0.34  # ~3 requests per second

    def test_discover_single_paper_with_doi(
        self,
        collector,
        esearch_response_with_pmc,
        esummary_response_with_pmc,
    ):
        """Test discovering PDF for a paper with DOI."""
        # Create paper with DOI
        paper_with_doi = create_test_paper(
            paper_id="test_paper_123",
            title="Deep Learning for Medical Image Analysis",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            citation_count=50,
            venue="Journal of Medical Imaging",
            doi="10.1234/jmi.2023.123456",
        )

        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # Mock search response
            search_response = Mock()
            search_response.text = esearch_response_with_pmc
            search_response.status_code = 200

            # Mock summary response
            summary_response = Mock()
            summary_response.text = esummary_response_with_pmc
            summary_response.status_code = 200

            mock_get.side_effect = [search_response, summary_response]

            # Test discovery
            pdf_record = collector._discover_single(paper_with_doi)

            assert pdf_record.paper_id == "test_paper_123"
            assert (
                pdf_record.pdf_url
                == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9876543/pdf/"
            )
            assert pdf_record.source == "pubmed_central"
            assert pdf_record.confidence_score == 0.95
            assert pdf_record.validation_status == "valid"
            assert pdf_record.version_info["pmc_id"] == "PMC9876543"
            assert pdf_record.version_info["search_method"] == "doi"

    def test_discover_single_paper_by_title(
        self,
        collector,
        sample_paper,
        esearch_response_with_pmc,
        esummary_response_with_pmc,
    ):
        """Test discovering PDF by title when DOI search fails."""
        sample_paper.doi = None  # Remove DOI to force title search

        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # First search (by title) returns results
            search_response = Mock()
            search_response.text = esearch_response_with_pmc
            search_response.status_code = 200

            summary_response = Mock()
            summary_response.text = esummary_response_with_pmc
            summary_response.status_code = 200

            mock_get.side_effect = [search_response, summary_response]

            pdf_record = collector._discover_single(sample_paper)

            assert pdf_record.paper_id == "test_paper_123"
            assert (
                pdf_record.pdf_url
                == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9876543/pdf/"
            )
            assert pdf_record.version_info["search_method"] == "title"

    def test_discover_single_paper_by_author_year(
        self,
        collector,
        sample_paper,
        esearch_response_with_pmc,
        esummary_response_with_pmc,
    ):
        """Test discovering PDF by author+year when other searches fail."""
        sample_paper.doi = None

        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # First search (title) returns no results
            no_results_response = Mock()
            no_results_response.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult><Count>0</Count><IdList></IdList></eSearchResult>"""
            no_results_response.status_code = 200

            # Second search (author+year) returns results
            search_response = Mock()
            search_response.text = esearch_response_with_pmc
            search_response.status_code = 200

            summary_response = Mock()
            summary_response.text = esummary_response_with_pmc
            summary_response.status_code = 200

            mock_get.side_effect = [
                no_results_response,
                search_response,
                summary_response,
            ]

            pdf_record = collector._discover_single(sample_paper)

            assert pdf_record.paper_id == "test_paper_123"
            assert pdf_record.version_info["search_method"] == "author_year"

    def test_discover_single_paper_no_pmc_id(
        self, collector, sample_paper, esearch_response_with_pmc
    ):
        """Test handling papers without PMC ID."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            search_response = Mock()
            search_response.text = esearch_response_with_pmc
            search_response.status_code = 200

            # Summary without PMC ID
            summary_response = Mock()
            summary_response.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSummaryResult>
                <DocSum>
                    <Id>12345678</Id>
                    <Item Name="Title" Type="String">Some Title</Item>
                </DocSum>
            </eSummaryResult>"""
            summary_response.status_code = 200

            mock_get.side_effect = [search_response, summary_response]

            with pytest.raises(Exception, match="No PMC ID found"):
                collector._discover_single(sample_paper)

    def test_discover_single_paper_api_error(self, collector, sample_paper):
        """Test handling API errors."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            mock_get.side_effect = Exception("API connection error")

            with pytest.raises(Exception, match="No PMC ID found"):
                collector._discover_single(sample_paper)

    def test_rate_limiting(
        self, collector, esearch_response_with_pmc, esummary_response_with_pmc
    ):
        """Test rate limiting between requests."""
        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Test {i}",
                authors=["Author"],
                year=2023,
                citation_count=10,
                venue="Test",
                doi=f"10.1234/test.{i}",
            )
            for i in range(3)
        ]

        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # Mock all responses
            responses = []
            for i in range(3):
                search_resp = Mock()
                search_resp.text = esearch_response_with_pmc
                search_resp.status_code = 200

                summary_resp = Mock()
                summary_resp.text = esummary_response_with_pmc
                summary_resp.status_code = 200

                responses.extend([search_resp, summary_resp])

            mock_get.side_effect = responses

            # Track timing
            start_time = time.time()
            results = collector.discover_pdfs(papers)
            elapsed_time = time.time() - start_time

            # Should take at least 2 * delay for 3 papers (6 requests)
            expected_min_time = 5 * collector.delay_between_requests
            assert elapsed_time >= expected_min_time * 0.9  # Allow 10% margin
            assert len(results) == 3

    def test_extract_pmc_id_from_xml(self, collector):
        """Test PMC ID extraction from various XML formats."""
        # Test with PMC prefix
        xml1 = """<DocSum><Item Name="pmc" Type="String">PMC1234567</Item></DocSum>"""
        assert collector._extract_pmc_id_from_xml(xml1) == "PMC1234567"

        # Test without PMC prefix
        xml2 = """<DocSum><Item Name="pmc" Type="String">7654321</Item></DocSum>"""
        assert collector._extract_pmc_id_from_xml(xml2) == "PMC7654321"

        # Test no PMC ID
        xml3 = """<DocSum><Item Name="title" Type="String">Some Title</Item></DocSum>"""
        assert collector._extract_pmc_id_from_xml(xml3) is None

    def test_build_pdf_url(self, collector):
        """Test PDF URL construction."""
        assert (
            collector._build_pdf_url("PMC1234567")
            == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/pdf/"
        )

        # Test without PMC prefix
        assert (
            collector._build_pdf_url("7654321")
            == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7654321/pdf/"
        )

    def test_search_query_formatting(self, collector, sample_paper):
        """Test search query formatting for different methods."""
        # DOI search - create paper with DOI
        paper_with_doi = create_test_paper(
            paper_id="test",
            title="Deep Learning for Medical Image Analysis",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            citation_count=0,
            venue="Journal",
            doi="10.1234/jmi.2023.123456",
        )
        query = collector._format_search_query(paper_with_doi, "doi")
        assert query == "10.1234/jmi.2023.123456[DOI]"

        # Title search
        query = collector._format_search_query(sample_paper, "title")
        assert query == '"Deep Learning for Medical Image Analysis"[Title]'

        # Author+year search
        query = collector._format_search_query(sample_paper, "author_year")
        assert "Doe[Author]" in query
        assert "2023[PDAT]" in query

    def test_empty_search_results(self, collector, sample_paper):
        """Test handling empty search results."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # All searches return no results
            no_results = Mock()
            no_results.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult><Count>0</Count><IdList></IdList></eSearchResult>"""
            no_results.status_code = 200

            mock_get.return_value = no_results

            with pytest.raises(Exception, match="No PMC ID found"):
                collector._discover_single(sample_paper)

    def test_http_error_handling(self, collector, sample_paper):
        """Test handling HTTP errors."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            error_response = Mock()
            error_response.status_code = 429  # Rate limit exceeded
            error_response.raise_for_status.side_effect = Exception(
                "429 Too Many Requests"
            )

            mock_get.return_value = error_response

            with pytest.raises(Exception, match="No PMC ID found"):
                collector._discover_single(sample_paper)

    def test_malformed_xml_handling(
        self, collector, sample_paper, esearch_response_with_pmc
    ):
        """Test handling malformed XML responses."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            search_response = Mock()
            search_response.text = esearch_response_with_pmc
            search_response.status_code = 200

            malformed_response = Mock()
            malformed_response.text = "Not valid XML <broken>"
            malformed_response.status_code = 200

            mock_get.side_effect = [search_response, malformed_response]

            with pytest.raises(Exception):
                collector._discover_single(sample_paper)

    def test_confidence_scoring(
        self, collector, esearch_response_with_pmc, esummary_response_with_pmc
    ):
        """Test confidence scoring based on search method."""
        with patch(
            "compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # Setup responses
            search_resp = Mock()
            search_resp.text = esearch_response_with_pmc
            search_resp.status_code = 200

            summary_resp = Mock()
            summary_resp.text = esummary_response_with_pmc
            summary_resp.status_code = 200

            mock_get.side_effect = [search_resp, summary_resp]

            # Test DOI search (highest confidence)
            paper = create_test_paper(
                paper_id="p1",
                title="Test",
                authors=["A"],
                year=2023,
                citation_count=0,
                venue="V",
                doi="10.1234/test",
            )
            result = collector._discover_single(paper)
            assert result.confidence_score == 0.95

            # Test title search (medium confidence)
            mock_get.side_effect = [search_resp, summary_resp]
            paper.doi = None
            result = collector._discover_single(paper)
            assert result.confidence_score == 0.85
