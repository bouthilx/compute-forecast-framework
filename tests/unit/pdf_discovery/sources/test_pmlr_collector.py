"""Unit tests for PMLR PDF collector."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pdf_discovery.sources.pmlr_collector import PMLRCollector
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper, Author


class TestPMLRCollector:
    """Test PMLRCollector implementation."""

    @pytest.fixture
    def collector(self):
        """Create PMLRCollector instance."""
        return PMLRCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            title="Deep Learning for Computer Vision",
            authors=[Author(name="John Doe")],
            venue="ICML",
            year=2023,
            citations=10,
            paper_id="test_paper_123",
        )

    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector.source_name == "pmlr"
        assert collector.timeout == 60
        assert collector.venue_volumes is not None
        assert "ICML" in collector.venue_volumes
        assert collector.base_url == "https://proceedings.mlr.press/"

    def test_load_volume_mapping(self, collector):
        """Test loading volume mapping data."""
        assert "ICML" in collector.venue_volumes
        assert collector.venue_volumes["ICML"]["2023"] == "v202"
        assert "AISTATS" in collector.venue_volumes
        assert collector.venue_volumes["AISTATS"]["2024"] == "v238"

    def test_get_volume_for_venue_year(self, collector):
        """Test volume lookup for venue and year."""
        assert collector._get_volume("ICML", 2023) == "v202"
        assert collector._get_volume("AISTATS", 2022) == "v151"
        assert collector._get_volume("UNKNOWN", 2023) is None
        assert collector._get_volume("ICML", 1999) is None

    def test_normalize_venue_name(self, collector):
        """Test venue name normalization."""
        assert (
            collector._normalize_venue("International Conference on Machine Learning")
            == "ICML"
        )
        assert collector._normalize_venue("ICML") == "ICML"
        assert collector._normalize_venue("icml") == "ICML"
        assert collector._normalize_venue("Unknown Conference") == "Unknown Conference"

    @patch("requests.get")
    def test_search_proceedings_page_success(self, mock_get, collector):
        """Test successful paper ID extraction from proceedings page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
        <div class="paper">
            <a href="/v202/doe23a.html">Deep Learning for Computer Vision</a>
        </div>
        <div class="paper">
            <a href="/v202/smith23b.html">Another Paper Title</a>
        </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        paper_id = collector._search_proceedings_page(
            "v202", "Deep Learning for Computer Vision"
        )
        assert paper_id == "doe23a"

    @patch("requests.get")
    def test_search_proceedings_page_fuzzy_match(self, mock_get, collector):
        """Test fuzzy matching for paper titles."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
        <div class="paper">
            <a href="/v202/doe23a.html">Deep Learning for Computer Vision: A Survey</a>
        </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        paper_id = collector._search_proceedings_page(
            "v202", "Deep Learning for Computer Vision"
        )
        assert paper_id == "doe23a"

    @patch("requests.get")
    def test_search_proceedings_page_not_found(self, mock_get, collector):
        """Test when paper is not found in proceedings."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
        <div class="paper">
            <a href="/v202/other23a.html">Completely Different Paper</a>
        </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        paper_id = collector._search_proceedings_page(
            "v202", "Deep Learning for Computer Vision"
        )
        assert paper_id is None

    @patch("requests.get")
    def test_search_proceedings_page_network_error(self, mock_get, collector):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")

        paper_id = collector._search_proceedings_page(
            "v202", "Deep Learning for Computer Vision"
        )
        assert paper_id is None

    @patch("requests.get")
    def test_search_proceedings_page_complex_html(self, mock_get, collector):
        """Test BeautifulSoup parsing with complex HTML structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <!DOCTYPE html>
        <html>
        <head><title>ICML 2023 Proceedings</title></head>
        <body>
        <div class="proceedings">
            <h1>ICML 2023</h1>
            <div class="paper-list">
                <div class="paper-entry">
                    <span class="paper-number">1</span>
                    <a href="/v202/smith23a.html" class="paper-link">
                        Deep Learning for Computer Vision
                    </a>
                    <span class="authors">John Smith, Jane Doe</span>
                </div>
                <div class="paper-entry">
                    <span class="paper-number">2</span>
                    <a href="/v202/jones23b.html" class="paper-link">
                        Another Paper Title
                    </a>
                    <span class="authors">Bob Jones</span>
                </div>
            </div>
        </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        paper_id = collector._search_proceedings_page(
            "v202", "Deep Learning for Computer Vision"
        )
        assert paper_id == "smith23a"

    def test_construct_pdf_url(self, collector):
        """Test PDF URL construction."""
        url = collector._construct_pdf_url("v202", "doe23a")
        assert url == "https://proceedings.mlr.press/v202/doe23a.pdf"

    @patch.object(PMLRCollector, "_search_proceedings_page")
    def test_discover_single_success(self, mock_search, collector, sample_paper):
        """Test successful PDF discovery for single paper."""
        mock_search.return_value = "doe23a"

        record = collector._discover_single(sample_paper)

        assert record.paper_id == "test_paper_123"
        assert record.pdf_url == "https://proceedings.mlr.press/v202/doe23a.pdf"
        assert record.source == "pmlr"
        assert record.confidence_score == 0.95
        assert record.validation_status == "verified"
        assert record.version_info["volume"] == "v202"
        assert record.version_info["paper_id"] == "doe23a"

    def test_discover_single_missing_volume(self, collector):
        """Test discovery when volume mapping is missing."""
        paper = Paper(
            title="Test Paper",
            authors=[Author(name="Author")],
            venue="UNKNOWN_CONF",
            year=2023,
            citations=0,
            paper_id="test_123",
        )

        with pytest.raises(ValueError, match="No volume mapping"):
            collector._discover_single(paper)

    @patch.object(PMLRCollector, "_search_proceedings_page")
    def test_discover_single_paper_not_found(
        self, mock_search, collector, sample_paper
    ):
        """Test discovery when paper is not found in proceedings."""
        mock_search.return_value = None

        with pytest.raises(ValueError, match="Paper not found"):
            collector._discover_single(sample_paper)

    def test_discover_pdfs_batch(self, collector):
        """Test batch discovery of PDFs."""
        papers = [
            Paper(
                title=f"Paper {i}",
                authors=[Author(name=f"Author {i}")],
                venue="ICML",
                year=2023,
                citations=i,
                paper_id=f"paper_{i}",
            )
            for i in range(3)
        ]

        with patch.object(collector, "_discover_single") as mock_discover:
            mock_discover.side_effect = [
                PDFRecord(
                    paper_id=f"paper_{i}",
                    pdf_url=f"https://pmlr.test/paper_{i}.pdf",
                    source="pmlr",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.9,
                    version_info={},
                    validation_status="verified",
                )
                for i in range(3)
            ]

            results = collector.discover_pdfs(papers)

            assert len(results) == 3
            assert all(f"paper_{i}" in results for i in range(3))
            assert mock_discover.call_count == 3

    @patch("requests.get")
    def test_caching_proceedings_pages(self, mock_get, collector):
        """Test that proceedings pages are cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><div class="paper"><a href="/v202/test23a.html">Test Paper</a></div></body></html>'
        mock_get.return_value = mock_response

        # First call should fetch from network
        paper_id1 = collector._search_proceedings_page("v202", "Test Paper")
        assert paper_id1 == "test23a"
        assert mock_get.call_count == 1

        # Second call should use cache
        paper_id2 = collector._search_proceedings_page("v202", "Test Paper")
        assert paper_id2 == "test23a"
        assert mock_get.call_count == 1  # Should not increase

    def test_statistics_tracking(self, collector):
        """Test statistics are properly tracked."""
        papers = [
            Paper(
                title="Success Paper",
                authors=[Author(name="Author")],
                venue="ICML",
                year=2023,
                citations=10,
                paper_id="success_1",
            ),
            Paper(
                title="Fail Paper",
                authors=[Author(name="Author")],
                venue="UNKNOWN",
                year=2023,
                citations=0,
                paper_id="fail_1",
            ),
        ]

        with patch.object(collector, "_discover_single") as mock_discover:
            mock_discover.side_effect = [
                PDFRecord(
                    paper_id="success_1",
                    pdf_url="https://test.pdf",
                    source="pmlr",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.9,
                    version_info={},
                    validation_status="verified",
                ),
                ValueError("Failed"),
            ]

            collector.discover_pdfs(papers)

            stats = collector.get_statistics()
            assert stats["attempted"] == 2
            assert stats["successful"] == 1
            assert stats["failed"] == 1
