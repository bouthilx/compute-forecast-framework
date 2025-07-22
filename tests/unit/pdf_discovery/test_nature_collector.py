"""Unit tests for Nature PDF collector."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.nature_collector import (
    NaturePDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
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
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
        doi=doi,
    )


class TestNaturePDFCollector:
    """Test suite for Nature PDF collector."""

    @pytest.fixture
    def collector(self):
        """Create a Nature collector instance."""
        return NaturePDFCollector(email="test@example.com")

    @pytest.fixture
    def nature_comms_paper(self):
        """Create a mock Nature Communications paper."""
        return create_test_paper(
            paper_id="test123",
            title="Test Nature Communications Paper",
            authors=[Author(name="Test Author")],
            venue="Nature Communications",
            year=2023,
            citation_count=10,
        )

    @pytest.fixture
    def sci_reports_paper(self):
        """Create a mock Scientific Reports paper."""
        return create_test_paper(
            paper_id="test456",
            title="Test Scientific Reports Paper",
            authors=[Author(name="Test Author")],
            venue="Scientific Reports",
            year=2023,
            citation_count=5,
        )

    @pytest.fixture
    def non_nature_paper(self):
        """Create a mock non-Nature paper."""
        return create_test_paper(
            paper_id="paper_99",
            title="Test Non-Nature Paper",
            authors=[Author(name="Test Author")],
            venue="ICML",
            year=2023,
            citation_count=20,
        )

    def test_init(self):
        """Test collector initialization."""
        collector = NaturePDFCollector(email="test@example.com")
        assert collector.source_name == "nature"
        assert collector.email == "test@example.com"
        assert collector.request_delay == 2.0

    def test_init_without_email(self):
        """Test that initialization fails without email."""
        with pytest.raises(ValueError, match="Email is required"):
            NaturePDFCollector(email="")

    def test_is_nature_paper_by_venue(
        self, collector, nature_comms_paper, sci_reports_paper, non_nature_paper
    ):
        """Test Nature paper identification by venue."""
        assert collector.is_nature_paper(nature_comms_paper) is True
        assert collector.is_nature_paper(sci_reports_paper) is True
        assert collector.is_nature_paper(non_nature_paper) is False

    def test_is_nature_paper_by_doi(self, collector):
        """Test Nature paper identification by DOI pattern."""
        # Nature Communications DOIs
        paper1 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="1",
            doi="10.1038/s41467-023-12345-6",
        )
        assert collector.is_nature_paper(paper1) is True

        # Scientific Reports DOIs (old format)
        paper2 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="2",
            doi="10.1038/srep56789",
        )
        assert collector.is_nature_paper(paper2) is True

        # Old Nature Communications format
        paper3 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="3",
            doi="10.1038/ncomms12345",
        )
        assert collector.is_nature_paper(paper3) is True

        # Non-Nature DOI
        paper4 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="4",
            doi="10.1016/j.cell.2023.01.001",
        )
        assert collector.is_nature_paper(paper4) is False

    def test_is_nature_paper_by_url(self, collector):
        """Test Nature paper identification by URL."""
        # Note: The nature collector expects string URLs, not URLRecord objects

        paper = create_test_paper(
            title="Test Paper",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="test",
        )
        # Add Nature URL as string (the collector implementation expects strings)
        paper.urls = ["https://www.nature.com/articles/s41467-023-12345"]
        assert collector.is_nature_paper(paper) is True

        paper2 = create_test_paper(
            title="Test Paper",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="test2",
        )
        # Add non-Nature URL as string
        paper2.urls = [
            "https://www.sciencedirect.com/science/article/pii/S0092867423000011"
        ]
        assert collector.is_nature_paper(paper2) is False

    def test_extract_article_id_from_doi(self, collector):
        """Test article ID extraction from DOI."""
        # Nature Communications
        assert (
            collector._extract_article_id_from_doi("10.1038/s41467-023-36000-6")
            == "s41467-023-36000-6"
        )

        # Scientific Reports
        assert (
            collector._extract_article_id_from_doi("10.1038/srep12345") == "srep12345"
        )

        # Old format
        assert (
            collector._extract_article_id_from_doi("10.1038/ncomms1234") == "ncomms1234"
        )

        # Non-Nature DOI
        assert collector._extract_article_id_from_doi("10.1145/1234567.1234568") is None

    def test_identify_journal(self, collector, nature_comms_paper, sci_reports_paper):
        """Test journal identification."""
        assert (
            collector._identify_journal(nature_comms_paper) == "Nature Communications"
        )
        assert collector._identify_journal(sci_reports_paper) == "Scientific Reports"

        # Test by DOI when venue is missing
        paper = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="test",
            doi="10.1038/s41467-023-12345-6",
        )
        assert collector._identify_journal(paper) == "Nature Communications"

        paper2 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="test2",
            doi="10.1038/srep56789",
        )
        assert collector._identify_journal(paper2) == "Scientific Reports"

        # Unknown journal
        paper3 = create_test_paper(
            title="Test",
            authors=[],
            venue="",
            year=2023,
            citation_count=0,
            paper_id="test3",
        )
        assert collector._identify_journal(paper3) == "unknown"

    @patch("requests.head")
    def test_check_open_access_availability_success(self, mock_head, collector):
        """Test successful open access PDF discovery."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_head.return_value = mock_response

        pdf_url = collector._check_open_access_availability("s41467-023-36000-6")
        assert pdf_url == "https://www.nature.com/articles/s41467-023-36000-6.pdf"

    @patch("requests.head")
    def test_check_open_access_availability_auth_required(self, mock_head, collector):
        """Test when authentication is required (not open access)."""
        mock_response = Mock()
        mock_response.status_code = 303
        mock_response.headers = {"Location": "https://idp.nature.com/authorize?..."}
        mock_head.return_value = mock_response

        pdf_url = collector._check_open_access_availability("s41467-023-36000-6")
        assert pdf_url is None

    @patch("requests.head")
    def test_check_open_access_availability_not_pdf(self, mock_head, collector):
        """Test when URL exists but is not a PDF."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_response

        pdf_url = collector._check_open_access_availability("s41467-023-36000-6")
        assert pdf_url is None

    @patch("requests.head")
    def test_rate_limiting(self, mock_head, collector):
        """Test that rate limiting is enforced."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_head.return_value = mock_response

        # Make two requests and measure time
        import time

        start_time = time.time()

        collector._check_open_access_availability("article1")
        collector._check_open_access_availability("article2")

        elapsed = time.time() - start_time
        # Should take at least 2 seconds due to rate limiting
        assert elapsed >= 2.0

    @patch.object(NaturePDFCollector, "_check_open_access_availability")
    def test_discover_single_direct_success(
        self, mock_check, collector, nature_comms_paper
    ):
        """Test successful direct PDF discovery."""
        # Give the paper a DOI so it can extract article ID
        nature_comms_paper.doi = "10.1038/s41467-023-36000-6"

        mock_check.return_value = (
            "https://www.nature.com/articles/s41467-023-36000-6.pdf"
        )

        pdf_record = collector._discover_single(nature_comms_paper)

        assert pdf_record.paper_id == "test123"
        assert (
            pdf_record.pdf_url
            == "https://www.nature.com/articles/s41467-023-36000-6.pdf"
        )
        assert pdf_record.source == "nature"
        assert pdf_record.confidence_score == 0.95
        assert pdf_record.version_info["doi"] == "10.1038/s41467-023-36000-6"
        assert pdf_record.version_info["article_id"] == "s41467-023-36000-6"
        assert pdf_record.version_info["journal"] == "Nature Communications"
        assert pdf_record.license == "CC-BY"

    @patch.object(NaturePDFCollector, "_check_open_access_availability")
    def test_discover_single_fallback_to_doi_resolver(
        self, mock_check, collector, nature_comms_paper
    ):
        """Test fallback to DOI resolver when direct access fails."""
        # Give the paper a DOI so it can extract article ID and fall back to DOI resolver
        nature_comms_paper.doi = "10.1038/s41467-023-36000-6"

        mock_check.return_value = None  # Direct access fails

        # Mock DOI resolver response
        mock_pdf_record = PDFRecord(
            paper_id="test123",
            pdf_url="https://example.com/pdf",
            source="doi_resolver",
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={},
            validation_status="pending",
        )

        with patch.object(
            collector.doi_resolver, "_discover_single", return_value=mock_pdf_record
        ):
            pdf_record = collector._discover_single(nature_comms_paper)

            assert pdf_record.source == "nature_via_doi"
            assert pdf_record.version_info["nature_paper"] is True
            assert pdf_record.version_info["journal"] == "Nature Communications"

    def test_discover_single_non_nature_paper(self, collector, non_nature_paper):
        """Test that non-Nature papers are rejected."""
        from compute_forecast.core.exceptions import UnsupportedSourceError

        with pytest.raises(
            UnsupportedSourceError, match="not from a supported Nature journal"
        ):
            collector._discover_single(non_nature_paper)

    @patch.object(NaturePDFCollector, "_check_open_access_availability")
    def test_discover_single_no_pdf_found(
        self, mock_check, collector, nature_comms_paper
    ):
        """Test when no PDF can be found."""
        from compute_forecast.core.exceptions import PDFNotAvailableError

        mock_check.return_value = None  # Direct access fails

        # Mock DOI resolver to also fail
        with patch.object(
            collector.doi_resolver, "_discover_single", side_effect=Exception("No PDF")
        ):
            with pytest.raises(PDFNotAvailableError, match="No open access PDF found"):
                collector._discover_single(nature_comms_paper)

    def test_discover_pdfs_batch(
        self, collector, nature_comms_paper, sci_reports_paper
    ):
        """Test batch PDF discovery."""
        papers = [nature_comms_paper, sci_reports_paper]

        with patch.object(collector, "_discover_single") as mock_discover:
            # Mock successful discoveries
            mock_discover.side_effect = [
                PDFRecord(
                    paper_id="test123",
                    pdf_url="https://nature.com/pdf1",
                    source="nature",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={},
                    validation_status="validated",
                ),
                PDFRecord(
                    paper_id="test456",
                    pdf_url="https://nature.com/pdf2",
                    source="nature",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={},
                    validation_status="validated",
                ),
            ]

            results = collector.discover_pdfs(papers)

            assert len(results) == 2
            assert "test123" in results
            assert "test456" in results
            assert results["test123"].pdf_url == "https://nature.com/pdf1"
            assert results["test456"].pdf_url == "https://nature.com/pdf2"
