"""MLR adapter - simplified stub implementation."""

from typing import List, Any
from datetime import datetime

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class MLRAdapter(BasePaperoniAdapter):
    """Simplified adapter for PMLR venues (ICML, AISTATS, UAI)."""
    
    def __init__(self, config=None):
        super().__init__("mlr", config)
        
    def get_supported_venues(self) -> List[str]:
        return ["icml", "ICML", "aistats", "AISTATS", "uai", "UAI"]
        
    def _create_paperoni_scraper(self):
        """No scraper needed for stub implementation."""
        return None
            
    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Stub implementation - returns empty list for now."""
        # TODO: Implement actual PMLR scraping
        # For now, we'll use Semantic Scholar as fallback
        self.logger.warning(f"MLR scraper not yet implemented for {venue} {year}. Using empty result.")
        return []