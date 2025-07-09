"""Base adapter for paperoni scrapers."""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..base import BaseScraper, ScrapingConfig, ScrapingResult
from ..models import SimplePaper, ScrapingBatch


class BasePaperoniAdapter(BaseScraper):
    """Base adapter for paperoni scrapers."""
    
    def __init__(self, scraper_name: str, config: Optional[ScrapingConfig] = None):
        super().__init__(f"paperoni_{scraper_name}", config)
        self.scraper_name = scraper_name
        self._paperoni_scraper = None
        
    def _get_paperoni_scraper(self):
        """Get or create paperoni scraper instance."""
        if self._paperoni_scraper is None:
            self._paperoni_scraper = self._create_paperoni_scraper()
        return self._paperoni_scraper
        
    def _create_paperoni_scraper(self):
        """Create paperoni scraper instance. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _create_paperoni_scraper")
        
    def _convert_papers(self, paperoni_papers: List[Any]) -> List[SimplePaper]:
        """Convert paperoni papers to SimplePaper format."""
        # For our simplified adapters, papers are already SimplePaper objects
        # or they are converted within each adapter's _call_paperoni_scraper method
        if not paperoni_papers:
            return []
            
        # If papers are already SimplePaper objects, return them
        if all(isinstance(p, SimplePaper) for p in paperoni_papers):
            return paperoni_papers
            
        # Otherwise, this is an error - adapters should handle conversion
        self.logger.error("Adapter returned non-SimplePaper objects")
        return []
        
    def get_available_years(self, venue: str) -> List[int]:
        """Get available years - paperoni scrapers typically support recent years."""
        current_year = datetime.now().year
        # Most paperoni scrapers support papers from ~2015 onwards
        return list(range(2015, current_year + 1))
        
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape papers using paperoni scraper."""
        try:
            scraper = self._get_paperoni_scraper()
            
            # Call paperoni scraper method
            paperoni_papers = self._call_paperoni_scraper(scraper, venue, year)
            
            # Convert to SimplePaper format
            simple_papers = self._convert_papers(paperoni_papers)
            
            # Create batch result
            batch = ScrapingBatch(
                papers=simple_papers,
                source=self.source_name,
                venue=venue,
                year=year,
                total_found=len(paperoni_papers),
                successfully_parsed=len(simple_papers)
            )
            
            return ScrapingResult.success_result(
                papers_count=len(simple_papers),
                metadata={
                    "venue": venue,
                    "year": year,
                    "batch": batch,
                    "papers": simple_papers
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping {venue} {year} with {self.scraper_name}: {e}")
            return ScrapingResult.failure_result(
                errors=[str(e)],
                metadata={"venue": venue, "year": year}
            )
            
    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Call the paperoni scraper. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _call_paperoni_scraper")