"""Unit tests for CVF Open Access PDF collector."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from requests.exceptions import RequestException

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.cvf_collector import (
    CVFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.metadata_collection.models import Paper


class TestCVFCollector:
    """Test suite for CVF collector."""

    @pytest.fixture
    def collector(self):
        """Create CVF collector instance."""
        return CVFCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            paper_id="test_paper_1",
            title="Deep Learning for Computer Vision",
            authors=["Author One", "Author Two"],
            year=2023,
            citations=10,
            venue="CVPR",
        )

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.source_name == "cvf"
        assert collector.timeout == 60
        assert collector.base_url == "https://openaccess.thecvf.com/"
        assert collector.supported_venues == ["CVPR", "ICCV", "ECCV", "WACV"]

    def test_venue_not_supported(self, collector):
        """Test handling of unsupported venues."""
        paper = Paper(
            paper_id="test_1",
            title="Test Paper",
            authors=[],
            year=2023,
            citations=0,
            venue="ICML",  # Not a CVF venue
        )

        with pytest.raises(ValueError, match="not a CVF venue"):
            collector._discover_single(paper)

    def test_construct_proceedings_url(self, collector):
        """Test proceedings URL construction."""
        # Test CVPR
        url = collector._construct_proceedings_url("CVPR", 2023)
        assert url == "https://openaccess.thecvf.com/CVPR2023"

        # Test ICCV
        url = collector._construct_proceedings_url("ICCV", 2021)
        assert url == "https://openaccess.thecvf.com/ICCV2021"

        # Test ECCV
        url = collector._construct_proceedings_url("ECCV", 2022)
        assert url == "https://openaccess.thecvf.com/ECCV2022"

    def test_construct_pdf_url(self, collector):
        """Test PDF URL construction."""
        url = collector._construct_pdf_url("CVPR", 2023, "Smith23_Deep_Learning")
        expected = (
            "https://openaccess.thecvf.com/CVPR2023/papers/Smith23_Deep_Learning.pdf"
        )
        assert url == expected

    @patch("requests.get")
    def test_search_proceedings_success(self, mock_get, collector):
        """Test successful proceedings page search."""
        # Mock proceedings HTML with paper links
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <div class="paper">
                <a href="/content/CVPR2023/papers/Smith23_Deep_Learning_for_Computer_Vision_CVPR_2023_paper.pdf">
                    Deep Learning for Computer Vision
                </a>
            </div>
            <div class="paper">
                <a href="/content/CVPR2023/papers/Jones23_Other_Paper_CVPR_2023_paper.pdf">
                    Other Paper Title
                </a>
            </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        paper_id = collector._search_proceedings_page(
            "CVPR", 2023, "Deep Learning for Computer Vision"
        )
        assert paper_id == "Smith23_Deep_Learning_for_Computer_Vision_CVPR_2023_paper"

    @patch("requests.get")
    def test_search_proceedings_fuzzy_match(self, mock_get, collector):
        """Test fuzzy title matching in proceedings."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <div class="paper">
                <a href="/content/CVPR2023/papers/Smith23_Deep_Learning_Computer_Vision_CVPR_2023_paper.pdf">
                    Deep Learning for Computer Vision: A Survey
                </a>
            </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        # Should match despite slight title difference
        paper_id = collector._search_proceedings_page(
            "CVPR", 2023, "Deep Learning for Computer Vision"
        )
        assert paper_id == "Smith23_Deep_Learning_Computer_Vision_CVPR_2023_paper"

    @patch("requests.get")
    def test_search_proceedings_not_found(self, mock_get, collector):
        """Test when paper is not found in proceedings."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <div class="paper">
                <a href="/content/CVPR2023/papers/Other_Paper.pdf">
                    Completely Different Paper
                </a>
            </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = collector._search_proceedings_page(
            "CVPR", 2023, "Deep Learning for Computer Vision"
        )
        assert result is None

    @patch("requests.get")
    def test_search_proceedings_network_error(self, mock_get, collector):
        """Test handling of network errors."""
        mock_get.side_effect = RequestException("Network error")

        result = collector._search_proceedings_page("CVPR", 2023, "Test Paper")
        assert result is None

    @patch.object(CVFCollector, "_search_proceedings_page")
    def test_discover_single_success(self, mock_search, collector, sample_paper):
        """Test successful PDF discovery."""
        mock_search.return_value = "Smith23_Deep_Learning_CVPR_2023_paper"

        result = collector._discover_single(sample_paper)

        assert isinstance(result, PDFRecord)
        assert result.paper_id == "test_paper_1"
        assert (
            result.pdf_url
            == "https://openaccess.thecvf.com/CVPR2023/papers/Smith23_Deep_Learning_CVPR_2023_paper.pdf"
        )
        assert result.source == "cvf"
        assert result.confidence_score == 0.95
        assert result.validation_status == "validated"
        assert result.license == "CVF Open Access"

        mock_search.assert_called_once_with(
            "CVPR", 2023, "Deep Learning for Computer Vision"
        )

    @patch.object(CVFCollector, "_search_proceedings_page")
    def test_discover_single_paper_not_found(
        self, mock_search, collector, sample_paper
    ):
        """Test when paper cannot be found in proceedings."""
        mock_search.return_value = None

        with pytest.raises(ValueError, match="Could not find paper"):
            collector._discover_single(sample_paper)

    def test_discover_multiple_papers(self, collector):
        """Test batch discovery of papers."""
        papers = [
            Paper(
                paper_id="p1",
                title="Paper One",
                authors=[],
                year=2023,
                citations=0,
                venue="CVPR",
            ),
            Paper(
                paper_id="p2",
                title="Paper Two",
                authors=[],
                year=2023,
                citations=0,
                venue="ICML",  # Not CVF
            ),
            Paper(
                paper_id="p3",
                title="Paper Three",
                authors=[],
                year=2022,
                citations=0,
                venue="ECCV",
            ),
        ]

        with patch.object(collector, "_discover_single") as mock_discover:
            # Configure mock to succeed for CVF papers, fail for others
            def side_effect(paper):
                if paper.venue in ["CVPR", "ECCV"]:
                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=f"https://cvf.com/{paper.paper_id}.pdf",
                        source="cvf",
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.95,
                        version_info={},
                        validation_status="validated",
                    )
                raise ValueError("Not CVF")

            mock_discover.side_effect = side_effect

            results = collector.discover_pdfs(papers)

            assert len(results) == 2
            assert "p1" in results
            assert "p3" in results
            assert "p2" not in results

    def test_venue_year_validation(self, collector):
        """Test validation of venue and year combinations."""
        # ICCV is biannual (odd years)
        paper_odd = Paper(
            paper_id="test1",
            title="Test",
            authors=[],
            year=2023,
            citations=0,
            venue="ICCV",
        )

        paper_even = Paper(
            paper_id="test2",
            title="Test",
            authors=[],
            year=2022,
            citations=0,
            venue="ICCV",
        )

        # Should work for odd year
        with patch.object(
            collector, "_search_proceedings_page", return_value="paper_id"
        ):
            result = collector._discover_single(paper_odd)
            assert result is not None

        # Should fail for even year
        with pytest.raises(ValueError, match="does not occur in"):
            collector._discover_single(paper_even)

    def test_proceedings_cache(self, collector):
        """Test that proceedings pages are cached."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_get.return_value = mock_response

            # First call
            collector._search_proceedings_page("CVPR", 2023, "Paper 1")
            # Second call with same venue/year
            collector._search_proceedings_page("CVPR", 2023, "Paper 2")

            # Should only fetch once due to caching
            assert mock_get.call_count == 1
