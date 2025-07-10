"""Tests for Nature Portfolio adapter using Crossref API."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.sources.scrapers.paperoni_adapters.nature_portfolio import (
    NaturePortfolioAdapter,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.models import (
    SimplePaper,
)


class TestNaturePortfolioAdapter:
    """Test Nature Portfolio adapter functionality."""

    @pytest.fixture
    def adapter(self):
        """Create a Nature Portfolio adapter instance."""
        return NaturePortfolioAdapter()

    def test_get_supported_venues(self, adapter):
        """Test that adapter returns supported Nature venues."""
        venues = adapter.get_supported_venues()

        assert "nature" in venues
        assert "scientific-reports" in venues
        assert "nature-communications" in venues
        assert "communications-biology" in venues
        assert "nature-machine-intelligence" in venues
        assert len(venues) >= 5

    def test_get_available_years(self, adapter):
        """Test available years for different venues."""
        current_year = datetime.now().year

        # Nature - oldest journal
        nature_years = adapter.get_available_years("nature")
        assert 1869 in nature_years
        assert current_year in nature_years
        assert len(nature_years) > 150

        # Scientific Reports - started 2011
        sr_years = adapter.get_available_years("scientific-reports")
        assert min(sr_years) == 2011
        assert current_year in sr_years

        # Nature Machine Intelligence - started 2019
        nmi_years = adapter.get_available_years("nature-machine-intelligence")
        assert min(nmi_years) == 2019
        assert current_year in nmi_years

        # Unknown venue
        unknown_years = adapter.get_available_years("unknown-journal")
        assert unknown_years == []

    def test_venue_to_issn_mapping(self, adapter):
        """Test that venues map correctly to ISSNs."""
        assert adapter._get_issn("nature") == "1476-4687"
        assert adapter._get_issn("scientific-reports") == "2045-2322"
        assert adapter._get_issn("nature-communications") == "2041-1723"
        assert adapter._get_issn("communications-biology") == "2399-3642"
        assert adapter._get_issn("nature-machine-intelligence") == "2522-5839"
        assert adapter._get_issn("unknown") is None

    def test_create_paperoni_scraper(self, adapter):
        """Test creation of Crossref API client."""
        client = adapter._create_paperoni_scraper()

        assert client is not None
        # The session should be configured with correct headers
        assert "User-Agent" in adapter.session.headers
        assert "Accept" in adapter.session.headers
        assert adapter.session.headers["Accept"] == "application/json"

    def test_call_paperoni_scraper_success(self, adapter):
        """Test successful paper collection from Crossref."""
        # Mock response data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "total-results": 100,
                "items": [
                    {
                        "DOI": "10.1038/s41586-024-12345-6",
                        "title": ["Test Paper Title"],
                        "author": [
                            {"given": "John", "family": "Doe"},
                            {"given": "Jane", "family": "Smith"},
                        ],
                        "published-print": {"date-parts": [[2024, 3, 15]]},
                        "abstract": "<p>This is a test abstract.</p>",
                        "URL": "https://doi.org/10.1038/s41586-024-12345-6",
                        "type": "journal-article",
                    }
                ],
            }
        }

        # Mock the session's get method
        with patch.object(adapter.session, "get", return_value=mock_response):
            # Call scraper
            papers = adapter._call_paperoni_scraper(None, "nature", 2024)

        assert len(papers) == 1
        paper = papers[0]

        assert isinstance(paper, SimplePaper)
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["John Doe", "Jane Smith"]
        assert paper.venue == "NATURE"
        assert paper.year == 2024
        assert paper.abstract == "This is a test abstract."
        assert paper.paper_id == "10.1038/s41586-024-12345-6"
        assert paper.source_url == "https://doi.org/10.1038/s41586-024-12345-6"
        assert paper.pdf_urls == []  # Nature doesn't provide PDF URLs via Crossref

    def test_call_paperoni_scraper_with_pdf(self, adapter):
        """Test paper collection when PDF link is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "total-results": 1,
                "items": [
                    {
                        "DOI": "10.1038/s41598-024-12345-6",
                        "title": ["Open Access Paper"],
                        "author": [{"given": "Test", "family": "Author"}],
                        "published-online": {"date-parts": [[2024, 1, 10]]},
                        "link": [
                            {
                                "URL": "https://www.nature.com/articles/s41598-024-12345-6.pdf",
                                "content-type": "application/pdf",
                                "content-version": "vor",
                            }
                        ],
                        "URL": "https://doi.org/10.1038/s41598-024-12345-6",
                        "type": "journal-article",
                    }
                ],
            }
        }

        with patch.object(adapter.session, "get", return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "scientific-reports", 2024)

        assert len(papers) == 1
        assert papers[0].pdf_urls == [
            "https://www.nature.com/articles/s41598-024-12345-6.pdf"
        ]

    def test_call_paperoni_scraper_empty_results(self, adapter):
        """Test handling of empty results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"total-results": 0, "items": []}}

        with patch.object(adapter.session, "get", return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "nature", 2024)

        assert papers == []

    def test_call_paperoni_scraper_api_error(self, adapter):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(adapter.session, "get", return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                adapter._call_paperoni_scraper(None, "nature", 2024)

        assert "API error" in str(exc_info.value)

    def test_call_paperoni_scraper_invalid_venue(self, adapter):
        """Test handling of invalid venue."""

        papers = adapter._call_paperoni_scraper(None, "invalid-venue", 2024)

        assert papers == []

    def test_pagination(self, adapter):
        """Test that adapter respects batch_size configuration."""
        # Create many items
        items = []
        for i in range(150):
            items.append(
                {
                    "DOI": f"10.1038/test-{i}",
                    "title": [f"Paper {i}"],
                    "author": [],
                    "published-print": {"date-parts": [[2024, 1, 1]]},
                    "URL": f"https://doi.org/10.1038/test-{i}",
                    "type": "journal-article",
                }
            )

        # Set batch size
        adapter.config.batch_size = 100

        # Mock response should only return batch_size items
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "total-results": 150,
                "items": items[:100],  # Crossref would only return requested rows
            }
        }

        with patch.object(adapter.session, "get", return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "nature", 2024)

        # Should get exactly batch_size papers
        assert len(papers) == 100

    def test_clean_abstract(self, adapter):
        """Test abstract cleaning from HTML."""
        # Test with HTML tags
        html_abstract = "<p>This is <strong>important</strong> research.</p>"
        cleaned = adapter._clean_abstract(html_abstract)
        assert cleaned == "This is important research."

        # Test with multiple paragraphs
        multi_para = "<p>First paragraph.</p><p>Second paragraph.</p>"
        cleaned = adapter._clean_abstract(multi_para)
        assert cleaned == "First paragraph. Second paragraph."

        # Test with None
        assert adapter._clean_abstract(None) == ""

        # Test with plain text
        plain = "Just plain text"
        assert adapter._clean_abstract(plain) == plain

    def test_paper_keywords_empty(self, adapter):
        """Test that papers have empty keywords list (extraction done in consolidation)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "total-results": 1,
                "items": [
                    {
                        "DOI": "10.1038/s41586-024-12345-6",
                        "title": ["Machine Learning Applications in Climate Science"],
                        "author": [{"given": "John", "family": "Doe"}],
                        "abstract": "This study uses deep learning and neural networks to predict climate change impacts.",
                        "published-print": {"date-parts": [[2024, 1, 1]]},
                        "URL": "https://doi.org/10.1038/s41586-024-12345-6",
                        "type": "journal-article",
                    }
                ],
            }
        }

        with patch.object(adapter.session, "get", return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "nature", 2024)

        assert len(papers) == 1
        paper = papers[0]

        # Check that keywords list exists but is empty (will be populated in consolidation)
        assert hasattr(paper, "keywords")
        assert paper.keywords == []
