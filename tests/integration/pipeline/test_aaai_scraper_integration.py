"""Integration tests for AAAI scraper."""

import os
import pytest
from unittest.mock import Mock, patch
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
    @patch('requests.Session.get')
    def test_aaai_scraper_live_collection(self, mock_get, registry, config):
        """Test paper collection from AAAI with mocked responses."""
        # Mock OAI-PMH response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/
         http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
  <responseDate>2024-01-01T00:00:00Z</responseDate>
  <request verb="ListRecords" metadataPrefix="oai_dc">https://ojs.aaai.org/index.php/AAAI/oai</request>
  <ListRecords>
    <record>
      <header>
        <identifier>oai:ojs.aaai.org:article/28301</identifier>
        <datestamp>2024-01-15</datestamp>
      </header>
      <metadata>
        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:title>Test Paper: Advances in AI Research</dc:title>
          <dc:creator>Smith, John</dc:creator>
          <dc:creator>Doe, Jane</dc:creator>
          <dc:description>This is a test abstract for the paper.</dc:description>
          <dc:date>2024-01-15</dc:date>
          <dc:type>info:eu-repo/semantics/article</dc:type>
          <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/28301</dc:identifier>
          <dc:identifier>10.1609/aaai.v38i1.28301</dc:identifier>
          <dc:source>Proceedings of the AAAI Conference on Artificial Intelligence; Vol. 38</dc:source>
        </oai_dc:dc>
      </metadata>
    </record>
    <record>
      <header>
        <identifier>oai:ojs.aaai.org:article/28302</identifier>
        <datestamp>2024-01-16</datestamp>
      </header>
      <metadata>
        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:title>Another Test Paper: Machine Learning Applications</dc:title>
          <dc:creator>Johnson, Alice</dc:creator>
          <dc:creator>Williams, Bob</dc:creator>
          <dc:description>Another test abstract.</dc:description>
          <dc:date>2024-01-16</dc:date>
          <dc:type>info:eu-repo/semantics/article</dc:type>
          <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/28302</dc:identifier>
          <dc:identifier>10.1609/aaai.v38i1.28302</dc:identifier>
          <dc:source>Proceedings of the AAAI Conference on Artificial Intelligence; Vol. 38</dc:source>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>'''
        mock_get.return_value = mock_response
        
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
    @patch('requests.Session.get')
    def test_aaai_scraper_error_handling(self, mock_get, registry, config):
        """Test error handling for invalid venue/year."""
        scraper = registry.get_scraper_for_venue("aaai", config=config)

        # Test with invalid venue
        result = scraper.scrape_venue_year("invalid-venue", 2024)
        assert not result.success
        assert len(result.errors) > 0

        # Test with very old year (before AAAI started) - mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2024-01-01T00:00:00Z</responseDate>
  <request verb="ListRecords" metadataPrefix="oai_dc">https://ojs.aaai.org/index.php/AAAI/oai</request>
  <ListRecords>
  </ListRecords>
</OAI-PMH>'''
        mock_get.return_value = mock_response
        
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
