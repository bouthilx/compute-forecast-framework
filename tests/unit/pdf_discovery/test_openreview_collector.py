"""Tests for OpenReview PDF collector."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.openreview_collector import (
    OpenReviewPDFCollector,
)


class TestOpenReviewPDFCollector:
    """Test OpenReview PDF collector implementation."""

    @pytest.fixture
    def collector(self):
        """Create OpenReview collector instance."""
        return OpenReviewPDFCollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            paper_id="test_123",
            title="Deep Learning for Natural Language Processing",
            authors=[
                Author(name="John Doe", affiliation="Test University"),
                Author(name="Jane Smith", affiliation="Research Lab"),
            ],
            venue="ICLR",
            year=2024,
            citations=10,
            abstract="This paper presents a new approach...",
        )

    @pytest.fixture
    def neurips_paper(self):
        """Create NeurIPS paper for testing."""
        return Paper(
            paper_id="neurips_123",
            title="Reinforcement Learning at Scale",
            authors=[Author(name="Alice Johnson", affiliation="AI Lab")],
            venue="NeurIPS",
            year=2023,
            citations=5,
        )

    def test_collector_initialization(self, collector):
        """Test collector is properly initialized."""
        assert collector.source_name == "openreview"
        assert collector.client is not None
        assert hasattr(collector, "venue_mapping")
        assert "ICLR" in collector.venue_mapping
        assert "NeurIPS" in collector.venue_mapping

    def test_venue_mapping_completeness(self, collector):
        """Test that all required venues are mapped."""
        required_venues = ["ICLR", "NeurIPS", "COLM"]
        for venue in required_venues:
            assert venue in collector.venue_mapping
            assert collector.venue_mapping[venue] is not None

    @patch("openreview.api.OpenReviewClient")
    def test_discover_single_paper_success(
        self, mock_client_class, collector, sample_paper
    ):
        """Test successful PDF discovery for single paper."""
        # Mock OpenReview client and API response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create mock submission
        mock_submission = Mock()
        mock_submission.id = "test_forum_id"
        mock_submission.forum = "test_forum_id"
        mock_submission.content = {
            "title": {"value": "Deep Learning for Natural Language Processing"},
            "pdf": {"value": "/pdf/test_forum_id.pdf"},
        }

        # Mock search result
        mock_client.get_all_notes.return_value = [mock_submission]

        # Re-initialize collector to use mocked client
        collector.__init__()

        # Test discovery
        pdf_record = collector._discover_single(sample_paper)

        assert pdf_record.paper_id == "test_123"
        assert pdf_record.pdf_url == "https://openreview.net/pdf?id=test_forum_id"
        assert pdf_record.source == "openreview"
        assert pdf_record.confidence_score >= 0.9
        assert pdf_record.validation_status == "valid"

    @patch("openreview.api.OpenReviewClient")
    def test_discover_with_title_variation(
        self, mock_client_class, collector, sample_paper
    ):
        """Test PDF discovery with slight title variations."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock submission with slightly different title
        mock_submission = Mock()
        mock_submission.id = "variation_forum_id"
        mock_submission.forum = "variation_forum_id"
        mock_submission.content = {
            "title": {"value": "Deep Learning for Natural Language Processing:"},
            "pdf": {"value": "/pdf/variation_forum_id.pdf"},
        }

        mock_client.get_all_notes.return_value = [mock_submission]
        collector.__init__()

        pdf_record = collector._discover_single(sample_paper)

        assert pdf_record is not None
        assert pdf_record.pdf_url == "https://openreview.net/pdf?id=variation_forum_id"
        assert pdf_record.confidence_score >= 0.85  # Lower confidence for fuzzy match

    @patch("openreview.api.OpenReviewClient")
    def test_author_fallback_search(self, mock_client_class, collector, sample_paper):
        """Test fallback to author search when title search fails."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First call returns empty (title search fails)
        # Second call returns result (author search succeeds)
        mock_submission = Mock()
        mock_submission.id = "author_search_id"
        mock_submission.forum = "author_search_id"
        mock_submission.content = {
            "title": {"value": "Different Title Completely"},
            "authors": {"value": ["John Doe", "Jane Smith"]},
            "pdf": {"value": "/pdf/author_search_id.pdf"},
        }

        mock_client.get_all_notes.side_effect = [[], [mock_submission]]
        collector.__init__()

        pdf_record = collector._discover_single(sample_paper)

        assert pdf_record is not None
        assert pdf_record.pdf_url == "https://openreview.net/pdf?id=author_search_id"
        assert pdf_record.confidence_score >= 0.7  # Lower confidence for author match
        assert mock_client.get_all_notes.call_count == 2

    @patch("openreview.api.OpenReviewClient")
    def test_neurips_2023_handling(self, mock_client_class, collector, neurips_paper):
        """Test handling of NeurIPS 2023+ papers."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_submission = Mock()
        mock_submission.id = "neurips_forum_id"
        mock_submission.forum = "neurips_forum_id"
        mock_submission.content = {
            "title": {"value": "Reinforcement Learning at Scale"},
            "pdf": {"value": "/pdf/neurips_forum_id.pdf"},
        }

        mock_client.get_all_notes.return_value = [mock_submission]
        collector.__init__()

        pdf_record = collector._discover_single(neurips_paper)

        assert pdf_record is not None
        assert "neurips_forum_id" in pdf_record.pdf_url
        # Verify correct venue mapping was used
        assert (
            mock_client.get_all_notes.call_args[1]["invitation"]
            == "NeurIPS.cc/2023/Conference/-/Submission"
        )

    @patch("openreview.api.OpenReviewClient")
    def test_pdf_not_found(self, mock_client_class, collector, sample_paper):
        """Test behavior when PDF is not found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_all_notes.return_value = []

        collector.__init__()

        with pytest.raises(Exception) as exc_info:
            collector._discover_single(sample_paper)

        assert "not found" in str(exc_info.value).lower()

    @patch("openreview.api.OpenReviewClient")
    def test_rate_limiting_retry(self, mock_client_class, collector, sample_paper):
        """Test rate limiting and retry logic."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First call raises rate limit error, second succeeds
        mock_submission = Mock()
        mock_submission.id = "retry_forum_id"
        mock_submission.forum = "retry_forum_id"
        mock_submission.content = {
            "title": {"value": "Deep Learning for Natural Language Processing"},
            "pdf": {"value": "/pdf/retry_forum_id.pdf"},
        }

        mock_client.get_all_notes.side_effect = [
            Exception("Rate limit exceeded"),
            [mock_submission],
        ]

        collector.__init__()

        pdf_record = collector._discover_single(sample_paper)

        assert pdf_record is not None
        assert mock_client.get_all_notes.call_count == 2

    def test_build_pdf_url(self, collector):
        """Test PDF URL construction."""
        forum_id = "test_forum_123"
        expected_url = "https://openreview.net/pdf?id=test_forum_123"

        url = collector._build_pdf_url(forum_id)

        assert url == expected_url

    @patch("openreview.api.OpenReviewClient")
    def test_discover_multiple_papers(self, mock_client_class, collector):
        """Test discovering PDFs for multiple papers."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        papers = [
            Paper(
                paper_id="p1",
                title="Paper One",
                authors=[Author(name="Author One", affiliation="Uni")],
                venue="ICLR",
                year=2024,
                citations=1,
            ),
            Paper(
                paper_id="p2",
                title="Paper Two",
                authors=[Author(name="Author Two", affiliation="Lab")],
                venue="NeurIPS",
                year=2023,
                citations=2,
            ),
        ]

        # Mock responses for both papers
        mock_sub1 = Mock()
        mock_sub1.id = "forum1"
        mock_sub1.forum = "forum1"
        mock_sub1.content = {
            "title": {"value": "Paper One"},
            "pdf": {"value": "/pdf/forum1.pdf"},
        }

        mock_sub2 = Mock()
        mock_sub2.id = "forum2"
        mock_sub2.forum = "forum2"
        mock_sub2.content = {
            "title": {"value": "Paper Two"},
            "pdf": {"value": "/pdf/forum2.pdf"},
        }

        mock_client.get_all_notes.side_effect = [[mock_sub1], [mock_sub2]]
        collector.__init__()

        results = collector.discover_pdfs(papers)

        assert len(results) == 2
        assert "p1" in results
        assert "p2" in results
        assert results["p1"].pdf_url == "https://openreview.net/pdf?id=forum1"
        assert results["p2"].pdf_url == "https://openreview.net/pdf?id=forum2"

    def test_statistics_tracking(self, collector):
        """Test that statistics are properly tracked."""
        initial_stats = collector.get_statistics()
        assert initial_stats["attempted"] == 0
        assert initial_stats["successful"] == 0
        assert initial_stats["failed"] == 0
