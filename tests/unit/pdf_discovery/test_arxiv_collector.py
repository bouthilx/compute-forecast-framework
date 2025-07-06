"""Tests for ArXiv PDF collector."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.data.models import Paper, Author
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.pdf_discovery.sources.arxiv_collector import ArXivPDFCollector


class TestArXivPDFCollector:
    """Test cases for ArXiv PDF collector."""

    @pytest.fixture
    def collector(self):
        """Create ArXiv collector instance."""
        return ArXivPDFCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            paper_id="test_paper_1",
            title="Attention Is All You Need",
            authors=[Author(name="Vaswani, Ashish"), Author(name="Shazeer, Noam")],
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            year=2017,
            venue="NeurIPS",
            citations=1000,
            arxiv_id="1706.03762v5",
            doi="10.5555/3295222.3295349",
            urls=["https://arxiv.org/abs/1706.03762"],
        )

    @pytest.fixture
    def paper_without_arxiv_id(self):
        """Create paper without direct arXiv ID."""
        return Paper(
            paper_id="test_paper_2",
            title="Deep Residual Learning for Image Recognition",
            authors=[Author(name="He, Kaiming"), Author(name="Zhang, Xiangyu")],
            abstract="Deeper neural networks are more difficult to train...",
            year=2016,
            venue="CVPR",
            citations=500,
            arxiv_id=None,
            doi="10.1109/CVPR.2016.90",
            urls=["https://arxiv.org/pdf/1512.03385.pdf"],
        )

    def test_collector_initialization(self, collector):
        """Test collector is properly initialized."""
        assert collector.source_name == "arxiv"
        assert collector.base_url == "https://arxiv.org/pdf/"
        assert collector.api_url == "http://export.arxiv.org/api/query"
        assert hasattr(collector, "rate_limiter")

    def test_extract_arxiv_id_from_paper_field(self, collector, sample_paper):
        """Test extracting arXiv ID from paper.arxiv_id field."""
        arxiv_id = collector.extract_arxiv_id(sample_paper)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_from_urls(self, collector, paper_without_arxiv_id):
        """Test extracting arXiv ID from paper URLs."""
        arxiv_id = collector.extract_arxiv_id(paper_without_arxiv_id)
        assert arxiv_id == "1512.03385"

    def test_extract_arxiv_id_no_match(self, collector):
        """Test behavior when no arXiv ID found."""
        paper = Paper(
            paper_id="test_paper_3",
            title="Some Non-ArXiv Paper",
            authors=[Author(name="Author, Test")],
            abstract="Abstract...",
            year=2020,
            venue="Journal",
            citations=10,
            arxiv_id=None,
            doi="10.1000/test",
            urls=["https://example.com/paper.pdf"],
        )
        arxiv_id = collector.extract_arxiv_id(paper)
        assert arxiv_id is None

    def test_handle_versions_latest(self, collector):
        """Test handling different arXiv versions."""
        with patch("requests.head") as mock_head:
            mock_head.return_value.status_code = 200
            mock_head.return_value.headers = {"Content-Length": "1024000"}

            pdf_record = collector.handle_versions("1706.03762v3")

            assert pdf_record.pdf_url == "https://arxiv.org/pdf/1706.03762.pdf"
            assert pdf_record.version_info["original_version"] == "v3"
            assert pdf_record.version_info["fetched_version"] == "latest"

    @patch("requests.get")
    def test_search_by_title_author_success(self, mock_get, collector, sample_paper):
        """Test successful title+author search."""
        # Mock API response
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/1706.03762v5</id>
                <title>Attention Is All You Need</title>
                <author><name>Ashish Vaswani</name></author>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response

        arxiv_id = collector.search_by_title_author(sample_paper)
        assert arxiv_id == "1706.03762"

    @patch("requests.get")
    def test_search_by_title_author_no_results(self, mock_get, collector, sample_paper):
        """Test title+author search with no results."""
        # Mock empty API response
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""
        mock_get.return_value = mock_response

        arxiv_id = collector.search_by_title_author(sample_paper)
        assert arxiv_id is None

    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.handle_versions"
    )
    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.search_by_title_author"
    )
    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.extract_arxiv_id"
    )
    def test_discover_single_direct_id(
        self, mock_extract, mock_search, mock_handle, collector, sample_paper
    ):
        """Test _discover_single with direct arXiv ID."""
        # Setup mocks
        mock_extract.return_value = "1706.03762"
        expected_record = PDFRecord(
            paper_id="test_paper_1",
            pdf_url="http://arxiv.org/pdf/1706.03762.pdf",
            source="arxiv",
            discovery_timestamp=datetime.now(),
            confidence_score=0.95,
            version_info={"original_version": "v5", "fetched_version": "latest"},
            validation_status="pending",
        )
        mock_handle.return_value = expected_record

        result = collector._discover_single(sample_paper)

        mock_extract.assert_called_once_with(sample_paper)
        mock_handle.assert_called_once_with("1706.03762")
        mock_search.assert_not_called()
        assert result == expected_record

    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.handle_versions"
    )
    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.search_by_title_author"
    )
    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.extract_arxiv_id"
    )
    def test_discover_single_fallback_search(
        self, mock_extract, mock_search, mock_handle, collector, sample_paper
    ):
        """Test _discover_single falling back to title+author search."""
        # Setup mocks
        mock_extract.return_value = None  # No direct ID
        mock_search.return_value = "1706.03762"  # Found via search
        expected_record = PDFRecord(
            paper_id="test_paper_1",
            pdf_url="http://arxiv.org/pdf/1706.03762.pdf",
            source="arxiv",
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={"original_version": "unknown", "fetched_version": "latest"},
            validation_status="pending",
        )
        mock_handle.return_value = expected_record

        result = collector._discover_single(sample_paper)

        mock_extract.assert_called_once_with(sample_paper)
        mock_search.assert_called_once_with(sample_paper)
        mock_handle.assert_called_once_with("1706.03762")
        assert result == expected_record

    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.search_by_title_author"
    )
    @patch(
        "compute_forecast.pdf_discovery.sources.arxiv_collector.ArXivPDFCollector.extract_arxiv_id"
    )
    def test_discover_single_no_arxiv_found(
        self, mock_extract, mock_search, collector, sample_paper
    ):
        """Test _discover_single when no arXiv version exists."""
        # Setup mocks
        mock_extract.return_value = None
        mock_search.return_value = None

        with pytest.raises(Exception, match="No arXiv version found"):
            collector._discover_single(sample_paper)

    def test_rate_limiting(self, collector):
        """Test rate limiting functionality."""
        # Test that rate limiter is called
        with patch.object(collector.rate_limiter, "wait") as mock_wait:
            with patch("requests.head") as mock_head:
                mock_head.return_value.status_code = 200
                mock_head.return_value.headers = {"Content-Length": "1024000"}

                collector.handle_versions("1706.03762")
                mock_wait.assert_called_once()

    def test_error_handling_network_failure(self, collector):
        """Test error handling for network failures."""
        with patch("requests.head", side_effect=ConnectionError("Network error")):
            with pytest.raises(Exception, match="Network error"):
                collector.handle_versions("1706.03762")

    def test_discover_pdfs_multiple_papers(self, collector):
        """Test discover_pdfs with multiple papers."""
        papers = [
            Paper(
                paper_id="paper1",
                title="Paper 1",
                authors=[Author(name="Author 1")],
                abstract="Abstract 1",
                year=2020,
                venue="Venue 1",
                citations=100,
                arxiv_id="2001.00001",
                urls=[],
            ),
            Paper(
                paper_id="paper2",
                title="Paper 2",
                authors=[Author(name="Author 2")],
                abstract="Abstract 2",
                year=2021,
                venue="Venue 2",
                citations=200,
                arxiv_id="2101.00001",
                urls=[],
            ),
        ]

        with patch.object(collector, "_discover_single") as mock_discover:
            mock_discover.side_effect = [
                PDFRecord(
                    paper_id="paper1",
                    pdf_url="https://arxiv.org/pdf/2001.00001.pdf",
                    source="arxiv",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={},
                    validation_status="valid",
                ),
                Exception("Paper 2 not found"),
            ]

            results = collector.discover_pdfs(papers)

            assert len(results) == 1
            assert "paper1" in results
            assert "paper2" not in results
            assert collector.get_statistics()["attempted"] == 2
            assert collector.get_statistics()["successful"] == 1
            assert collector.get_statistics()["failed"] == 1


class TestArXivIDExtraction:
    """Test arXiv ID extraction patterns."""

    def test_extract_id_with_version(self):
        """Test extracting ID from versioned arXiv ID."""
        collector = ArXivPDFCollector()
        assert collector._extract_id_from_string("1706.03762v5") == "1706.03762"
        assert collector._extract_id_from_string("2001.12345v1") == "2001.12345"

    def test_extract_id_without_version(self):
        """Test extracting ID from unversioned arXiv ID."""
        collector = ArXivPDFCollector()
        assert collector._extract_id_from_string("1706.03762") == "1706.03762"
        assert collector._extract_id_from_string("2001.12345") == "2001.12345"

    def test_extract_id_from_url(self):
        """Test extracting ID from arXiv URLs."""
        collector = ArXivPDFCollector()
        assert (
            collector._extract_id_from_string("https://arxiv.org/abs/1706.03762")
            == "1706.03762"
        )
        assert (
            collector._extract_id_from_string("https://arxiv.org/pdf/1706.03762.pdf")
            == "1706.03762"
        )
        assert (
            collector._extract_id_from_string("http://arxiv.org/abs/1706.03762v3")
            == "1706.03762"
        )

    def test_extract_id_invalid(self):
        """Test behavior with invalid inputs."""
        collector = ArXivPDFCollector()
        assert collector._extract_id_from_string("not-an-arxiv-id") is None
        assert (
            collector._extract_id_from_string("https://example.com/paper.pdf") is None
        )
        assert collector._extract_id_from_string("") is None
        assert collector._extract_id_from_string(None) is None


class TestVersionHandling:
    """Test version handling functionality."""

    def test_version_extraction(self):
        """Test version extraction from arXiv IDs."""
        collector = ArXivPDFCollector()
        assert collector._extract_version("1706.03762v5") == "v5"
        assert collector._extract_version("2001.12345v1") == "v1"
        assert collector._extract_version("1706.03762") is None

    def test_build_pdf_url(self):
        """Test PDF URL construction."""
        collector = ArXivPDFCollector()
        assert (
            collector._build_pdf_url("1706.03762")
            == "https://arxiv.org/pdf/1706.03762.pdf"
        )
        assert (
            collector._build_pdf_url("2001.12345")
            == "https://arxiv.org/pdf/2001.12345.pdf"
        )
