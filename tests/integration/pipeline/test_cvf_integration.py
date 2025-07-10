"""Integration tests for CVF scraper with CLI and registry."""

from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.sources.scrapers.registry import (
    ScraperRegistry,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.conference_scrapers.cvf_scraper import (
    CVFScraper,
)


class TestCVFIntegration:
    """Integration tests for CVF scraper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ScraperRegistry()

    def test_cvf_scraper_registered(self):
        """Test that CVF scraper is properly registered."""
        # CVF scraper should be in registry
        assert "CVFScraper" in self.registry._scrapers

        # Should be able to get CVF scraper class
        scraper_class = self.registry._scrapers["CVFScraper"]
        assert scraper_class == CVFScraper

    def test_cvf_venues_mapped_correctly(self):
        """Test that all CVF venues are mapped to CVF scraper."""
        cvf_venues = ["cvpr", "iccv", "eccv", "wacv"]

        for venue in cvf_venues:
            # Venue should be mapped to CVFScraper
            assert venue in self.registry._venue_mapping
            assert self.registry._venue_mapping[venue] == "CVFScraper"

    def test_get_scraper_for_cvf_venues(self):
        """Test getting scraper instances for CVF venues."""
        cvf_venues = ["cvpr", "iccv", "eccv", "wacv"]

        for venue in cvf_venues:
            scraper = self.registry.get_scraper_for_venue(venue)
            assert scraper is not None
            assert isinstance(scraper, CVFScraper)
            assert venue.upper() in scraper.get_supported_venues()

    def test_case_insensitive_venue_lookup(self):
        """Test that venue lookup is case insensitive."""
        # Test both uppercase and lowercase
        scraper_lower = self.registry.get_scraper_for_venue("cvpr")
        scraper_upper = self.registry.get_scraper_for_venue("CVPR")

        assert scraper_lower is not None
        assert scraper_upper is not None
        assert type(scraper_lower) is type(scraper_upper)
        assert isinstance(scraper_lower, CVFScraper)
        assert isinstance(scraper_upper, CVFScraper)

    def test_cvf_venues_in_supported_venues(self):
        """Test that CVF venues appear in registry's supported venues."""
        supported_venues = self.registry.get_supported_venues()

        # Should include CVF venues
        cvf_venues = ["cvpr", "iccv", "eccv", "wacv"]
        for venue in cvf_venues:
            assert venue in supported_venues

    def test_cvf_scraper_supports_expected_venues(self):
        """Test that CVF scraper instance supports expected venues."""
        scraper = CVFScraper()
        supported_venues = scraper.get_supported_venues()

        # Should support both upper and lower case
        expected_venues = [
            "CVPR",
            "ICCV",
            "ECCV",
            "WACV",
            "cvpr",
            "iccv",
            "eccv",
            "wacv",
        ]
        for venue in expected_venues:
            assert venue in supported_venues

    def test_venue_year_validation(self):
        """Test venue/year validation for conference schedules."""
        scraper = CVFScraper()

        # Test ICCV (odd years only)
        iccv_years = scraper.get_available_years("ICCV")
        for year in iccv_years:
            assert year % 2 == 1, f"ICCV year {year} should be odd"

        # Test ECCV (even years only)
        eccv_years = scraper.get_available_years("ECCV")
        for year in eccv_years:
            assert year % 2 == 0, f"ECCV year {year} should be even"

        # Test CVPR/WACV (annual)
        cvpr_years = scraper.get_available_years("CVPR")
        wacv_years = scraper.get_available_years("WACV")

        # Should have both odd and even years
        assert any(year % 2 == 0 for year in cvpr_years)
        assert any(year % 2 == 1 for year in cvpr_years)
        assert any(year % 2 == 0 for year in wacv_years)
        assert any(year % 2 == 1 for year in wacv_years)

    @patch(
        "compute_forecast.data.sources.scrapers.conference_scrapers.cvf_scraper.CVFScraper._make_request"
    )
    def test_end_to_end_scraping_flow(self, mock_make_request):
        """Test complete scraping flow from registry to results."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = """
        <dt class="ptitle"><br><a href="/content/CVPR2024/html/Test_Paper_CVPR_2024_paper.html">Test Paper Title</a></dt>
        <dd><form class="authsearch"><input type="hidden" name="query_author" value="Test Author"></form></dd>
        <dd>[<a href="/content/CVPR2024/papers/Test_Paper_CVPR_2024_paper.pdf">pdf</a>]</dd>
        """
        mock_make_request.return_value = mock_response

        # Get scraper through registry
        scraper = self.registry.get_scraper_for_venue("cvpr")
        assert isinstance(scraper, CVFScraper)

        # Test scraping
        result = scraper.scrape_venue_year("cvpr", 2024)

        assert result.success is True
        assert result.papers_collected > 0
        assert "papers" in result.metadata

        # Check paper structure
        papers = result.metadata["papers"]
        assert len(papers) > 0

        paper = papers[0]
        assert paper.title == "Test Paper Title"
        assert paper.venue == "cvpr"
        assert paper.year == 2024
        assert paper.source_scraper == "cvf"
        assert len(paper.authors) > 0
        assert paper.authors[0] == "Test Author"
