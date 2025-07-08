"""Unit tests for ACL Anthology PDF collector."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from compute_forecast.pdf_discovery.sources.acl_anthology_collector import (
    ACLAnthologyCollector,
)
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper, Author


class TestACLAnthologyCollector:
    """Test suite for ACL Anthology PDF collector."""

    @pytest.fixture
    def collector(self):
        """Create ACL Anthology collector instance."""
        return ACLAnthologyCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            title="Neural Machine Translation by Jointly Learning to Align and Translate",
            authors=[
                Author(name="Dzmitry Bahdanau", affiliation="University of Montreal"),
                Author(name="Kyunghyun Cho", affiliation="University of Montreal"),
                Author(name="Yoshua Bengio", affiliation="University of Montreal"),
            ],
            venue="EMNLP",
            year=2023,
            citations=1000,
            paper_id="test_paper_123",
            abstract="This paper presents a neural machine translation model...",
        )

    def test_venue_mapping(self, collector):
        """Test venue name to ACL code mapping."""
        # Test exact matches
        assert collector._map_venue_to_codes("EMNLP") == [
            "emnlp-main",
            "emnlp-findings",
        ]
        assert collector._map_venue_to_codes("EACL") == ["eacl-main", "eacl-short"]
        assert collector._map_venue_to_codes("ACL") == ["acl-long", "acl-short"]
        assert collector._map_venue_to_codes("NAACL") == ["naacl-main", "naacl-short"]

        # Test case insensitive matching
        assert collector._map_venue_to_codes("emnlp") == [
            "emnlp-main",
            "emnlp-findings",
        ]
        assert collector._map_venue_to_codes("Emnlp") == [
            "emnlp-main",
            "emnlp-findings",
        ]

        # Test with year in venue name
        assert collector._map_venue_to_codes("EMNLP 2023") == [
            "emnlp-main",
            "emnlp-findings",
        ]
        assert collector._map_venue_to_codes("ACL 2022") == ["acl-long", "acl-short"]

        # Test unknown venues
        assert collector._map_venue_to_codes("ICML") == []
        assert collector._map_venue_to_codes("Unknown Conference") == []

    def test_construct_pdf_url(self, collector):
        """Test PDF URL construction."""
        # Test basic URL construction
        url = collector._construct_pdf_url("emnlp-main", 2023, "456")
        assert url == "https://aclanthology.org/2023.emnlp-main.456.pdf"

        # Test different venues and years
        url = collector._construct_pdf_url("acl-long", 2022, "123")
        assert url == "https://aclanthology.org/2022.acl-long.123.pdf"

        url = collector._construct_pdf_url("naacl-short", 2021, "789")
        assert url == "https://aclanthology.org/2021.naacl-short.789.pdf"

    def test_search_proceedings_success(self, collector):
        """Test successful proceedings search."""
        # Mock proceedings page response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <div class="paper">
            <a href="/2023.emnlp-main.456/">Neural Machine Translation by Jointly Learning to Align and Translate</a>
        </div>
        <div class="paper">
            <a href="/2023.emnlp-main.789/">Another Paper Title</a>
        </div>
        </html>
        """

        with patch.object(
            collector.session, "get", return_value=mock_response
        ) as mock_get:
            paper_id = collector._search_proceedings(
                "emnlp-main",
                2023,
                "Neural Machine Translation by Jointly Learning to Align and Translate",
            )
            assert paper_id == "456"

            # Verify correct URL was called
            expected_url = "https://aclanthology.org/events/emnlp-2023/"
            mock_get.assert_called_with(expected_url, timeout=30)

    def test_search_proceedings_complex_html(self, collector):
        """Test proceedings search with complex HTML structure using BeautifulSoup."""
        # Mock proceedings page with more complex HTML structure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <div class="anthology-content">
                <div class="paper-entry">
                    <p class="d-flex justify-content-between">
                        <span class="title">
                            <a href="/2023.emnlp-main.456/" class="text-decoration-none">
                                Neural Machine Translation by Jointly Learning to Align and Translate
                            </a>
                        </span>
                        <span class="badge badge-secondary">Main</span>
                    </p>
                    <p class="authors">Author One, Author Two</p>
                </div>
                <div class="paper-entry">
                    <p class="d-flex justify-content-between">
                        <span class="title">
                            <a href="/2023.emnlp-main.789/" class="text-decoration-none">
                                Another Complex Paper Title with <em>Emphasis</em> and Other Tags
                            </a>
                        </span>
                        <span class="badge badge-secondary">Main</span>
                    </p>
                    <p class="authors">Author Three, Author Four</p>
                </div>
            </div>
        </body>
        </html>
        """

        with patch.object(collector.session, "get", return_value=mock_response):
            paper_id = collector._search_proceedings(
                "emnlp-main",
                2023,
                "Neural Machine Translation by Jointly Learning to Align and Translate",
            )
            assert paper_id == "456"

            # Test with the second paper that has HTML tags in title
            paper_id = collector._search_proceedings(
                "emnlp-main",
                2023,
                "Another Complex Paper Title with Emphasis and Other Tags",
            )
            assert paper_id == "789"

    def test_search_proceedings_not_found(self, collector):
        """Test proceedings search when paper not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <div class="paper">
            <a href="/2023.emnlp-main.789/">Different Paper Title</a>
        </div>
        </html>
        """

        with patch.object(collector.session, "get", return_value=mock_response):
            paper_id = collector._search_proceedings(
                "emnlp-main",
                2023,
                "Neural Machine Translation by Jointly Learning to Align and Translate",
            )
            assert paper_id is None

    def test_search_proceedings_http_error(self, collector):
        """Test proceedings search with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(collector.session, "get", return_value=mock_response):
            paper_id = collector._search_proceedings("emnlp-main", 2023, "Some Title")
            assert paper_id is None

    def test_validate_pdf_url_exists(self, collector):
        """Test PDF URL validation when file exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "1048576",
        }

        with patch.object(
            collector.session, "head", return_value=mock_response
        ) as mock_head:
            url = "https://aclanthology.org/2023.emnlp-main.456.pdf"
            is_valid, size = collector._validate_pdf_url(url)

            assert is_valid is True
            assert size == 1048576
            mock_head.assert_called_with(url, timeout=10)

    def test_validate_pdf_url_not_found(self, collector):
        """Test PDF URL validation when file doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(collector.session, "head", return_value=mock_response):
            url = "https://aclanthology.org/2023.emnlp-main.456.pdf"
            is_valid, size = collector._validate_pdf_url(url)

            assert is_valid is False
            assert size is None

    def test_validate_pdf_url_exception(self, collector):
        """Test PDF URL validation with network exception."""
        import requests

        with patch.object(
            collector.session,
            "head",
            side_effect=requests.exceptions.Timeout("Connection timeout"),
        ):
            url = "https://aclanthology.org/2023.emnlp-main.456.pdf"
            is_valid, size = collector._validate_pdf_url(url)

            assert is_valid is False
            assert size is None

    def test_search_proceedings_exception(self, collector):
        """Test proceedings search with network exception."""
        import requests

        with patch.object(
            collector.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        ):
            paper_id = collector._search_proceedings("emnlp-main", 2023, "Some Title")
            assert paper_id is None

    @patch.object(ACLAnthologyCollector, "_search_proceedings")
    @patch.object(ACLAnthologyCollector, "_validate_pdf_url")
    def test_discover_single_success(
        self, mock_validate, mock_search, collector, sample_paper
    ):
        """Test successful PDF discovery for single paper."""
        # Mock search returns paper ID
        mock_search.return_value = "456"

        # Mock validation returns success
        mock_validate.return_value = (True, 2097152)  # 2MB file

        # Discover PDF
        with patch(
            "compute_forecast.pdf_discovery.sources.acl_anthology_collector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 12, 1, 10, 0, 0)
            pdf_record = collector._discover_single(sample_paper)

        # Verify result
        assert pdf_record.paper_id == "test_paper_123"
        assert pdf_record.pdf_url == "https://aclanthology.org/2023.emnlp-main.456.pdf"
        assert pdf_record.source == "acl_anthology"
        assert pdf_record.confidence_score == 0.95
        assert pdf_record.validation_status == "validated"
        assert pdf_record.file_size_bytes == 2097152
        assert pdf_record.version_info == {
            "venue_code": "emnlp-main",
            "paper_id": "456",
            "year": 2023,
        }

        # Verify search was called for main venue
        mock_search.assert_called_with("emnlp-main", 2023, sample_paper.title)

    @patch.object(ACLAnthologyCollector, "_search_proceedings")
    @patch.object(ACLAnthologyCollector, "_validate_pdf_url")
    def test_discover_single_fallback_to_findings(
        self, mock_validate, mock_search, collector, sample_paper
    ):
        """Test PDF discovery falls back to findings when main fails."""
        # Mock search returns None for main, paper ID for findings
        mock_search.side_effect = [None, "789"]

        # Mock validation returns success
        mock_validate.return_value = (True, 1048576)

        pdf_record = collector._discover_single(sample_paper)

        # Verify findings URL was used
        assert (
            pdf_record.pdf_url == "https://aclanthology.org/2023.emnlp-findings.789.pdf"
        )
        assert pdf_record.version_info["venue_code"] == "emnlp-findings"

        # Verify both venue codes were tried
        assert mock_search.call_count == 2
        mock_search.assert_any_call("emnlp-main", 2023, sample_paper.title)
        mock_search.assert_any_call("emnlp-findings", 2023, sample_paper.title)

    @patch.object(ACLAnthologyCollector, "_search_proceedings")
    def test_discover_single_no_pdf_found(self, mock_search, collector, sample_paper):
        """Test discovery when no PDF found."""
        # Mock search returns None for all venue codes
        mock_search.return_value = None

        with pytest.raises(Exception) as exc_info:
            collector._discover_single(sample_paper)

        assert "Could not find PDF" in str(exc_info.value)
        assert "EMNLP" in str(exc_info.value)

    def test_discover_single_unknown_venue(self, collector):
        """Test discovery with unknown venue."""
        paper = Paper(
            title="Some Paper",
            authors=[Author(name="Author One")],
            venue="ICML",  # Not an ACL venue
            year=2023,
            citations=10,
            paper_id="test_123",
        )

        with pytest.raises(Exception) as exc_info:
            collector._discover_single(paper)

        assert "Unknown venue: ICML" in str(exc_info.value)

    def test_fuzzy_title_matching(self, collector):
        """Test fuzzy title matching for robustness."""
        # Test exact match
        assert (
            collector._fuzzy_match_title(
                "Neural Machine Translation", "Neural Machine Translation"
            )
            is True
        )

        # Test case differences
        assert (
            collector._fuzzy_match_title(
                "neural machine translation", "Neural Machine Translation"
            )
            is True
        )

        # Test minor differences
        assert (
            collector._fuzzy_match_title(
                "Neural Machine Translation by Jointly Learning",
                "Neural Machine Translation by Jointly Learning to Align",
            )
            is True
        )

        # Test significant differences
        assert (
            collector._fuzzy_match_title(
                "Completely Different Title", "Neural Machine Translation"
            )
            is False
        )

    def test_statistics_tracking(self, collector):
        """Test that statistics are properly tracked."""
        papers = [
            Paper(
                title="Paper 1",
                authors=[],
                venue="EMNLP",
                year=2023,
                citations=10,
                paper_id="p1",
            ),
            Paper(
                title="Paper 2",
                authors=[],
                venue="ACL",
                year=2023,
                citations=20,
                paper_id="p2",
            ),
        ]

        # Disable batch mode for this test to test single paper discovery
        collector.supports_batch = False

        with patch.object(collector, "_discover_single") as mock_discover:
            # First paper succeeds, second fails
            mock_discover.side_effect = [
                PDFRecord(
                    paper_id="p1",
                    pdf_url="https://example.com/p1.pdf",
                    source="acl_anthology",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={},
                    validation_status="validated",
                ),
                Exception("Failed to find PDF"),
            ]

            results = collector.discover_pdfs(papers)

            # Check results
            assert len(results) == 1
            assert "p1" in results

            # Check statistics
            stats = collector.get_statistics()
            assert stats["attempted"] == 2
            assert stats["successful"] == 1
            assert stats["failed"] == 1

    def test_batch_discovery(self, collector):
        """Test batch discovery of PDFs."""
        papers = [
            Paper(
                title="Neural Machine Translation with Attention",
                authors=[],
                venue="EMNLP",
                year=2023,
                citations=10,
                paper_id="p1",
            ),
            Paper(
                title="Transformer Networks for Language Understanding",
                authors=[],
                venue="EMNLP",
                year=2023,
                citations=20,
                paper_id="p2",
            ),
            Paper(
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors=[],
                venue="ACL",
                year=2022,
                citations=30,
                paper_id="p3",
            ),
        ]

        # Mock proceedings HTML with multiple papers
        mock_emnlp_proceedings = """
        <html>
        <div class="paper">
            <a href="/2023.emnlp-main.100/">Neural Machine Translation with Attention</a>
            <a href="/2023.emnlp-main.200/">Transformer Networks for Language Understanding</a>
        </div>
        </html>
        """

        mock_acl_proceedings = """
        <html>
        <div class="paper">
            <a href="/2022.acl-long.300/">BERT: Pre-training of Deep Bidirectional Transformers</a>
        </div>
        </html>
        """

        # Mock different responses for different URLs
        def mock_get(url, timeout=None):
            response = Mock()
            if "emnlp-2023" in url:
                response.status_code = 200
                response.text = mock_emnlp_proceedings
            elif "acl-2022" in url:
                response.status_code = 200
                response.text = mock_acl_proceedings
            else:
                response.status_code = 404
            return response

        # Mock PDF validation
        with patch.object(collector.session, "get", side_effect=mock_get):
            with patch.object(
                collector, "_validate_pdf_url", return_value=(True, 1048576)
            ):
                results = collector.discover_pdfs_batch(papers)

                # All papers should be found
                assert len(results) == 3
                assert all(f"p{i}" in results for i in range(1, 4))

                # Verify URLs are correct
                assert (
                    results["p1"].pdf_url
                    == "https://aclanthology.org/2023.emnlp-main.100.pdf"
                )
                assert (
                    results["p2"].pdf_url
                    == "https://aclanthology.org/2023.emnlp-main.200.pdf"
                )
                assert (
                    results["p3"].pdf_url
                    == "https://aclanthology.org/2022.acl-long.300.pdf"
                )
