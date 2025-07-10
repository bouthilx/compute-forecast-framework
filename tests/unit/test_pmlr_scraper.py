"""Unit tests for PMLR scraper"""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.sources.scrapers.conference_scrapers.pmlr_scraper import (
    PMLRScraper,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.base import (
    ScrapingConfig,
)


class TestPMLRScraper:
    """Test suite for PMLR scraper"""

    @pytest.fixture
    def scraper(self):
        """Create PMLR scraper instance"""
        config = ScrapingConfig(rate_limit_delay=0.1, max_retries=1)
        return PMLRScraper(config)

    def test_supported_venues(self, scraper):
        """Test that all expected venues are supported"""
        supported = scraper.get_supported_venues()

        # Check main venues (case variations)
        assert "ICML" in supported
        assert "icml" in supported
        assert "AISTATS" in supported
        assert "aistats" in supported
        assert "UAI" in supported
        assert "uai" in supported
        assert "COLLAS" in supported
        assert "collas" in supported
        assert "CoLLAs" in supported

    def test_normalize_venue(self, scraper):
        """Test venue normalization"""
        assert scraper._normalize_venue("icml") == "ICML"
        assert scraper._normalize_venue("ICML") == "ICML"
        assert scraper._normalize_venue("aistats") == "AISTATS"
        assert scraper._normalize_venue("collas") == "COLLAS"
        assert scraper._normalize_venue("CoLLAs") == "COLLAS"

    def test_get_available_years(self, scraper):
        """Test getting available years for venues"""
        # ICML should have multiple years
        icml_years = scraper.get_available_years("ICML")
        assert len(icml_years) > 0
        assert 2023 in icml_years
        assert 2022 in icml_years

        # Case insensitive
        icml_years_lower = scraper.get_available_years("icml")
        assert icml_years == icml_years_lower

        # COLLAS has fewer years
        collas_years = scraper.get_available_years("COLLAS")
        assert 2023 in collas_years
        assert 2022 in collas_years

    def test_get_proceedings_url(self, scraper):
        """Test URL construction"""
        # ICML 2023 -> volume 202
        url = scraper.get_proceedings_url("ICML", 2023)
        assert url == "https://proceedings.mlr.press/v202/"

        # AISTATS 2022 -> volume 151
        url = scraper.get_proceedings_url("AISTATS", 2022)
        assert url == "https://proceedings.mlr.press/v151/"

        # Invalid venue
        with pytest.raises(ValueError, match="not supported"):
            scraper.get_proceedings_url("INVALID", 2023)

        # Invalid year
        with pytest.raises(ValueError, match="not available"):
            scraper.get_proceedings_url("ICML", 1999)

    def test_parse_div_paper_structure(self, scraper):
        """Test parsing div.paper HTML structure"""
        html = """
        <html>
        <body>
        <div class="paper">
            <p class="title">Test Paper Title</p>
            <p class="authors">John Doe, Jane Smith</p>
            <p class="links">
                <a href="/v202/doe23a.html">abs</a>
                <a href="/v202/doe23a/doe23a.pdf">Download PDF</a>
            </p>
        </div>
        </body>
        </html>
        """

        papers = scraper.parse_proceedings_page(html, "ICML", 2023)
        assert len(papers) == 1

        paper = papers[0]
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["John Doe", "Jane Smith"]
        assert paper.venue == "ICML"
        assert paper.year == 2023
        assert len(paper.pdf_urls) == 1
        assert "doe23a.pdf" in paper.pdf_urls[0]

    def test_parse_p_title_structure(self, scraper):
        """Test parsing p.title HTML structure (older format)"""
        html = """
        <html>
        <body>
        <p class="title">Another Test Paper</p>
        <p class="authors">Alice Johnson; Bob Wilson</p>
        <p class="links">
            <a href="paper123.pdf">PDF</a>
            <a href="paper123.html">abs</a>
        </p>
        </body>
        </html>
        """

        papers = scraper.parse_proceedings_page(html, "UAI", 2021)
        assert len(papers) == 1

        paper = papers[0]
        assert paper.title == "Another Test Paper"
        assert paper.authors == ["Alice Johnson", "Bob Wilson"]
        assert paper.venue == "UAI"
        assert paper.year == 2021

    def test_extract_authors_various_formats(self, scraper):
        """Test author extraction with various formats"""
        from bs4 import BeautifulSoup

        # Comma separated
        elem = BeautifulSoup("<p>John Doe, Jane Smith, Bob Wilson</p>", "html.parser").p
        authors = scraper._extract_authors(elem)
        assert authors == ["John Doe", "Jane Smith", "Bob Wilson"]

        # Semicolon separated
        elem = BeautifulSoup("<p>John Doe; Jane Smith; Bob Wilson</p>", "html.parser").p
        authors = scraper._extract_authors(elem)
        assert authors == ["John Doe", "Jane Smith", "Bob Wilson"]

        # With affiliations in parentheses
        elem = BeautifulSoup(
            "<p>John Doe (MIT), Jane Smith (Stanford)</p>", "html.parser"
        ).p
        authors = scraper._extract_authors(elem)
        assert authors == ["John Doe", "Jane Smith"]

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.scrapers.conference_scrapers.pmlr_scraper.PMLRScraper._make_request"
    )
    def test_scrape_venue_year_success(self, mock_request, scraper):
        """Test successful scraping"""
        mock_response = Mock()
        mock_response.text = """
        <div class="paper">
            <p class="title">ML Paper 1</p>
            <p class="authors">Author A, Author B</p>
            <p class="links"><a href="paper1.pdf">Download PDF</a></p>
        </div>
        <div class="paper">
            <p class="title">ML Paper 2</p>
            <p class="authors">Author C, Author D</p>
            <p class="links"><a href="paper2.pdf">Download PDF</a></p>
        </div>
        """
        mock_request.return_value = mock_response

        result = scraper.scrape_venue_year("ICML", 2023)

        assert result.success
        assert result.papers_collected == 2
        assert len(result.metadata["papers"]) == 2
        assert result.metadata["venue"] == "ICML"
        assert result.metadata["year"] == 2023
        assert result.metadata["volume"] == 202

    def test_scrape_invalid_venue(self, scraper):
        """Test scraping with invalid venue"""
        result = scraper.scrape_venue_year("INVALID_VENUE", 2023)

        assert not result.success
        assert result.papers_collected == 0
        assert "not supported" in result.errors[0]

    def test_scrape_invalid_year(self, scraper):
        """Test scraping with invalid year"""
        result = scraper.scrape_venue_year("ICML", 1999)

        assert not result.success
        assert result.papers_collected == 0
        assert "not available" in result.errors[0]

    def test_estimate_paper_count(self, scraper):
        """Test paper count estimation"""
        # Known estimates
        assert scraper.estimate_paper_count("ICML", 2023) == 350
        assert scraper.estimate_paper_count("AISTATS", 2023) == 65
        assert scraper.estimate_paper_count("UAI", 2023) == 38
        assert scraper.estimate_paper_count("COLLAS", 2023) == 15

        # Unknown year
        assert scraper.estimate_paper_count("ICML", 2030) is None

        # Unknown venue
        assert scraper.estimate_paper_count("UNKNOWN", 2023) is None

    def test_metadata_completeness(self, scraper):
        """Test metadata completeness calculation"""
        # Full metadata
        score = scraper._calculate_completeness(
            "This is a sufficiently long title",
            ["Author 1", "Author 2"],
            "http://example.com/paper.pdf",
        )
        assert score == 1.0

        # Missing PDF
        score = scraper._calculate_completeness(
            "This is a sufficiently long title", ["Author 1", "Author 2"], None
        )
        assert score == 0.7

        # Missing authors
        score = scraper._calculate_completeness(
            "This is a sufficiently long title", [], "http://example.com/paper.pdf"
        )
        assert score == 0.7

        # Short title
        score = scraper._calculate_completeness(
            "Short", ["Author 1"], "http://example.com/paper.pdf"
        )
        assert score == 0.6
