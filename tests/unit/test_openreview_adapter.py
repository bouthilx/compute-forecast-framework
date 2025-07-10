"""Unit tests for OpenReview adapter"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.sources.scrapers.paperoni_adapters.openreview import (
    OpenReviewAdapter,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.models import SimplePaper
from compute_forecast.pipeline.metadata_collection.sources.scrapers.base import ScrapingConfig


class TestOpenReviewAdapter:
    """Test suite for OpenReview adapter"""

    @pytest.fixture
    def adapter(self):
        """Create OpenReview adapter instance"""
        config = ScrapingConfig(rate_limit_delay=0.1, max_retries=1, batch_size=5)
        return OpenReviewAdapter(config)

    def test_supported_venues(self, adapter):
        """Test that all expected venues are supported"""
        supported = adapter.get_supported_venues()

        # Check all venues (case variations)
        assert "ICLR" in supported
        assert "iclr" in supported
        assert "TMLR" in supported
        assert "tmlr" in supported
        assert "COLM" in supported
        assert "colm" in supported
        assert "RLC" in supported
        assert "rlc" in supported

    def test_get_available_years(self, adapter):
        """Test getting available years for venues"""
        current_year = datetime.now().year

        # ICLR has many years
        iclr_years = adapter.get_available_years("ICLR")
        assert 2013 in iclr_years
        assert current_year in iclr_years
        assert len(iclr_years) >= 10

        # TMLR started in 2022
        tmlr_years = adapter.get_available_years("TMLR")
        assert 2022 in tmlr_years
        assert current_year in tmlr_years
        assert 2021 not in tmlr_years

        # COLM started in 2024
        colm_years = adapter.get_available_years("COLM")
        assert 2024 in colm_years
        assert 2023 not in colm_years

        # RLC started in 2024
        rlc_years = adapter.get_available_years("RLC")
        assert 2024 in rlc_years
        assert 2025 in rlc_years  # Future conference

    def test_venue_id_mapping(self, adapter):
        """Test venue ID generation"""
        # Conference venues
        assert adapter._get_venue_id("iclr", 2023) == "ICLR.cc/2023/Conference"
        assert adapter._get_venue_id("colm", 2024) == "colmweb.org/COLM/2024/Conference"
        assert (
            adapter._get_venue_id("rlc", 2024) == "rl-conference.cc/RLC/2024/Conference"
        )

        # TMLR doesn't use year
        assert adapter._get_venue_id("tmlr", 2023) == "TMLR"
        assert adapter._get_venue_id("tmlr", 2024) == "TMLR"

        # Invalid venue
        assert adapter._get_venue_id("invalid", 2023) is None

    @patch("openreview.api.OpenReviewClient")
    def test_client_creation(self, mock_client_class, adapter):
        """Test OpenReview client creation"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = adapter._create_paperoni_scraper()

        assert client == mock_client
        mock_client_class.assert_called_once_with(baseurl="https://api2.openreview.net")

    @patch.object(OpenReviewAdapter, "_get_paperoni_scraper")
    @patch.object(OpenReviewAdapter, "_get_conference_submissions")
    @patch.object(OpenReviewAdapter, "_get_conference_submissions_v1")
    def test_conference_scraping(
        self, mock_get_submissions_v1, mock_get_submissions, mock_get_scraper, adapter
    ):
        """Test conference venue scraping (ICLR, COLM, RLC)"""
        # Mock client
        mock_client = Mock()
        mock_get_scraper.return_value = mock_client

        # Mock submissions
        mock_submission = Mock()
        mock_submission.id = "test123"
        mock_submission.content = {
            "title": "Test Paper Title",
            "authors": ["Author One", "Author Two"],
            "abstract": "Test abstract",
            "pdf": "/pdf/test123.pdf",
        }
        mock_get_submissions.return_value = [mock_submission]
        mock_get_submissions_v1.return_value = [mock_submission]

        # Test ICLR 2024 (uses v2 API)
        result = adapter.scrape_venue_year("ICLR", 2024)

        assert result.success
        assert result.papers_collected == 1
        assert len(result.metadata["papers"]) == 1

        paper = result.metadata["papers"][0]
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["Author One", "Author Two"]
        assert paper.venue == "ICLR"
        assert paper.year == 2024
        assert paper.paper_id == "test123"
        assert "test123.pdf" in paper.pdf_urls[0]

        # Test ICLR 2023 (uses v1 API)
        result = adapter.scrape_venue_year("ICLR", 2023)
        assert result.success

    @patch.object(OpenReviewAdapter, "_get_paperoni_scraper")
    @patch.object(OpenReviewAdapter, "_get_tmlr_papers")
    def test_tmlr_scraping(self, mock_get_tmlr, mock_get_scraper, adapter):
        """Test TMLR scraping with year filtering"""
        # Mock client
        mock_client = Mock()
        mock_get_scraper.return_value = mock_client

        # Mock TMLR papers
        mock_papers = [
            SimplePaper(
                title="TMLR Paper 1",
                authors=["Author A"],
                venue="TMLR",
                year=2023,
                paper_id="tmlr1",
                source_scraper="openreview",
                scraped_at=datetime.now(),
            ),
            SimplePaper(
                title="TMLR Paper 2",
                authors=["Author B"],
                venue="TMLR",
                year=2023,
                paper_id="tmlr2",
                source_scraper="openreview",
                scraped_at=datetime.now(),
            ),
        ]
        mock_get_tmlr.return_value = mock_papers

        result = adapter.scrape_venue_year("TMLR", 2023)

        assert result.success
        assert result.papers_collected == 2
        mock_get_tmlr.assert_called_once_with(2023)

    @patch.object(OpenReviewAdapter, "_get_paperoni_scraper")
    def test_tmlr_year_filtering(self, mock_get_scraper, adapter):
        """Test TMLR paper year filtering"""
        # Mock client
        mock_client = Mock()
        mock_get_scraper.return_value = mock_client
        adapter.client = mock_client

        # Mock submissions with different years
        mock_sub_2022 = Mock()
        mock_sub_2022.id = "tmlr2022"
        mock_sub_2022.pdate = 1640995200000  # 2022-01-01 in milliseconds
        mock_sub_2022.cdate = 1640995200000  # Fallback date
        mock_sub_2022.content = {
            "title": {"value": "Paper from 2022"},
            "authors": {"value": ["Author 2022"]},
            "abstract": {"value": "Abstract 2022"},
            "pdf": {"value": "/pdf/2022.pdf"},
        }

        mock_sub_2023 = Mock()
        mock_sub_2023.id = "tmlr2023"
        mock_sub_2023.pdate = 1672617600000  # 2023-01-02 in milliseconds
        mock_sub_2023.cdate = 1672617600000  # Fallback date
        mock_sub_2023.content = {
            "title": {"value": "Paper from 2023"},
            "authors": {"value": ["Author 2023"]},
            "abstract": {"value": "Abstract 2023"},
            "pdf": {"value": "/pdf/2023.pdf"},
        }

        mock_client.get_all_notes.return_value = [mock_sub_2022, mock_sub_2023]

        papers = adapter._get_tmlr_papers(2023)

        assert len(papers) == 1
        assert papers[0].title == "Paper from 2023"
        assert papers[0].year == 2023

    def test_conference_submission_formats(self, adapter):
        """Test different invitation formats for conferences"""
        mock_client = Mock()
        adapter.client = mock_client

        # Test with no submissions found initially
        mock_client.get_all_notes.side_effect = [
            Exception("Not found"),  # First format fails
            Exception("Not found"),  # Second format fails
            [Mock()],  # Third format succeeds
        ]

        submissions = adapter._get_conference_submissions(
            "test.venue/2024/Conference", "colm"
        )

        assert len(submissions) == 1
        assert mock_client.get_all_notes.call_count == 3

    def test_scrape_invalid_venue(self, adapter):
        """Test scraping with invalid venue"""
        result = adapter.scrape_venue_year("INVALID_VENUE", 2023)

        # The base adapter's scrape_venue_year will handle this
        # It should still try to call the scraper but fail
        assert not result.success or result.papers_collected == 0

    def test_scrape_venue_year_error_handling(self, adapter):
        """Test error handling in scrape_venue_year"""
        with patch.object(
            adapter, "_get_paperoni_scraper", side_effect=Exception("API Error")
        ):
            result = adapter.scrape_venue_year("ICLR", 2023)

            assert not result.success
            assert "API Error" in result.errors[0]

    @patch.object(OpenReviewAdapter, "_get_paperoni_scraper")
    def test_batch_size_limit(self, mock_get_scraper, adapter):
        """Test that batch size is respected"""
        # Set small batch size
        adapter.config.batch_size = 2

        mock_client = Mock()
        mock_get_scraper.return_value = mock_client
        adapter.client = mock_client

        # Create many mock submissions
        mock_submissions = []
        for i in range(10):
            mock_sub = Mock()
            mock_sub.id = f"paper{i}"
            mock_sub.pdate = 1672617600000  # 2023
            mock_sub.cdate = 1672617600000  # Fallback
            mock_sub.content = {
                "title": {"value": f"Paper {i}"},
                "authors": {"value": [f"Author {i}"]},
                "abstract": {"value": f"Abstract {i}"},
                "pdf": {"value": f"/pdf/{i}.pdf"},
            }
            mock_submissions.append(mock_sub)

        mock_client.get_all_notes.return_value = mock_submissions

        papers = adapter._get_tmlr_papers(2023)

        # Should only return batch_size papers
        assert len(papers) == 2
