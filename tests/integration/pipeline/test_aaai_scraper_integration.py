"""Integration tests for AAAI scraper."""

import os
import pytest
from compute_forecast.pipeline.metadata_collection.sources.scrapers.registry import (
    get_registry,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.base import (
    ScrapingConfig,
)


class TestAAAIScraperIntegration:
    """Integration tests for AAAI scraper."""

    @pytest.fixture
    def registry(self):
        """Get scraper registry."""
        return get_registry()

    @pytest.fixture
    def config(self):
        """Create scraping config with small batch size."""
        return ScrapingConfig(
            batch_size=5,  # Small batch for testing
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30,
        )

    def test_aaai_scraper_registration(self, registry):
        """Test that AAAI scraper is properly registered."""
        # Check venue mappings
        assert registry.get_scraper_for_venue_info("aaai")["scraper"] == "AAAIScraper"
        assert registry.get_scraper_for_venue_info("aies")["scraper"] == "AAAIScraper"
        assert registry.get_scraper_for_venue_info("hcomp")["scraper"] == "AAAIScraper"
        assert registry.get_scraper_for_venue_info("icwsm")["scraper"] == "AAAIScraper"

        # Check scraper can be instantiated
        scraper = registry.get_scraper_for_venue("aaai", config=ScrapingConfig())
        assert scraper is not None
        assert scraper.__class__.__name__ == "AAAIScraper"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("CI", "false").lower() == "true",
        reason="Skip live API tests in CI to avoid timeouts",
    )
    def test_aaai_scraper_live_collection(self, registry, config):
        """Test actual paper collection from AAAI (requires internet)."""
        # Get AAAI scraper
        scraper = registry.get_scraper_for_venue("aaai", config=config)

        # Try to scrape recent AAAI papers
        result = scraper.scrape_venue_year("aaai", 2024)

        assert result.success, f"Scraping failed with errors: {result.errors}"

        papers = result.metadata.get("papers", [])
        assert len(papers) > 0, "No papers collected"
        assert len(papers) <= config.batch_size, (
            f"Too many papers: {len(papers)} > {config.batch_size}"
        )

        # Validate first paper
        paper = papers[0]
        assert paper.title, "Paper missing title"
        assert paper.authors, "Paper missing authors"
        assert paper.venue == "AAAI", f"Wrong venue: {paper.venue}"
        assert paper.year == 2024, f"Wrong year: {paper.year}"
        assert paper.source_scraper == "aaai", f"Wrong scraper: {paper.source_scraper}"
        assert paper.source_url, "Paper missing source URL"

        # Check if DOI is present (most AAAI papers should have DOI)
        assert paper.doi or paper.paper_id, "Paper missing both DOI and paper_id"

    @pytest.mark.integration
    def test_aaai_scraper_error_handling(self, registry, config):
        """Test error handling for invalid venue/year."""
        scraper = registry.get_scraper_for_venue("aaai", config=config)

        # Test with invalid venue
        result = scraper.scrape_venue_year("invalid-venue", 2024)
        assert not result.success
        assert len(result.errors) > 0

        # Test with very old year (before AAAI started)
        result = scraper.scrape_venue_year("aaai", 1970)
        # Should either return no papers or handle gracefully
        assert result.success or len(result.errors) > 0

    @pytest.mark.integration
    def test_multiple_aaai_venues(self, registry, config):
        """Test that different AAAI venues work correctly."""
        venues_to_test = ["aaai", "aies"]  # Test main AAAI and AIES

        for venue in venues_to_test:
            scraper = registry.get_scraper_for_venue(venue, config=config)
            assert scraper is not None, f"No scraper for {venue}"

            # Get available years
            years = scraper.get_available_years(venue)
            assert len(years) > 0, f"No available years for {venue}"

            # Verify start years
            if venue == "aaai":
                assert min(years) == 1980
            elif venue == "aies":
                assert min(years) == 2018
