"""Scraper registry for managing available scrapers."""

import logging
from typing import Dict, List, Optional, Type, Any

from .base import BaseScraper, ScrapingConfig

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """Registry for managing and accessing available scrapers."""

    def __init__(self):
        self._scrapers: Dict[str, Type[BaseScraper]] = {}
        self._venue_mapping: Dict[str, str] = {}
        self._initialize_scrapers()

    def _initialize_scrapers(self):
        """Initialize built-in scrapers and venue mappings."""
        # Register package scrapers
        self._register_package_scrapers()

        # Register paperoni adapters
        self._register_paperoni_adapters()

        # Set up venue to scraper mappings
        self._setup_venue_mappings()

    def _register_package_scrapers(self):
        """Register scrapers from this package."""
        try:
            # Import custom scrapers
            from .conference_scrapers.ijcai_scraper import IJCAIScraper
            from .conference_scrapers.acl_anthology_scraper import ACLAnthologyScraper
            from .conference_scrapers.cvf_scraper import CVFScraper
            from .conference_scrapers.pmlr_scraper import PMLRScraper

            self.register_scraper("IJCAIScraper", IJCAIScraper)
            self.register_scraper("ACLAnthologyScraper", ACLAnthologyScraper)
            self.register_scraper("CVFScraper", CVFScraper)
            self.register_scraper("PMLRScraper", PMLRScraper)

        except ImportError as e:
            logger.warning(f"Failed to import package scrapers: {e}")

    def _register_paperoni_adapters(self):
        """Register paperoni adapter scrapers."""
        try:
            from .paperoni_adapters import (
                NeurIPSAdapter,
                MLRAdapter,
                OpenReviewAdapter,
                SemanticScholarAdapter,
                NaturePortfolioAdapter,
            )
            from .aaai import AAAIScraper

            self.register_scraper("NeurIPSScraper", NeurIPSAdapter)
            self.register_scraper("MLRScraper", MLRAdapter)
            self.register_scraper("OpenReviewScraper", OpenReviewAdapter)
            self.register_scraper("SemanticScholarScraper", SemanticScholarAdapter)
            self.register_scraper("NaturePortfolioScraper", NaturePortfolioAdapter)
            self.register_scraper("AAAIScraper", AAAIScraper)

        except ImportError as e:
            logger.warning(f"Failed to import paperoni adapters: {e}")

    def _setup_venue_mappings(self):
        """Set up venue to scraper mappings."""
        self._venue_mapping = {
            # Direct scrapers with dedicated implementations
            "neurips": "NeurIPSScraper",
            "icml": "PMLRScraper",
            "iclr": "OpenReviewScraper",
            "ijcai": "IJCAIScraper",
            "acl": "ACLAnthologyScraper",
            "emnlp": "ACLAnthologyScraper",
            "naacl": "ACLAnthologyScraper",
            "coling": "ACLAnthologyScraper",
            "aistats": "PMLRScraper",
            "uai": "PMLRScraper",
            "collas": "PMLRScraper",
            # OpenReview venues
            "tmlr": "OpenReviewScraper",
            "colm": "OpenReviewScraper",
            "rlc": "OpenReviewScraper",
            # CVF venues with dedicated scraper
            "cvpr": "CVFScraper",
            "iccv": "CVFScraper",
            "eccv": "CVFScraper",
            "wacv": "CVFScraper",
            # Nature Portfolio journals
            "nature": "NaturePortfolioScraper",
            "scientific-reports": "NaturePortfolioScraper",
            "nature-communications": "NaturePortfolioScraper",
            "communications-biology": "NaturePortfolioScraper",
            "nature-machine-intelligence": "NaturePortfolioScraper",
            "nature-neuroscience": "NaturePortfolioScraper",
            "nature-methods": "NaturePortfolioScraper",
            "nature-biotechnology": "NaturePortfolioScraper",
            # AAAI venues
            "aaai": "AAAIScraper",
            "aies": "AAAIScraper",
            "hcomp": "AAAIScraper",
            "icwsm": "AAAIScraper",
            # Other venues with SemanticScholar fallback
            "miccai": "SemanticScholarScraper",
            "kdd": "SemanticScholarScraper",
            "www": "SemanticScholarScraper",
            # Default fallback
            "*": "SemanticScholarScraper",
        }

    def register_scraper(self, name: str, scraper_class: Type[BaseScraper]):
        """Register a scraper class."""
        self._scrapers[name] = scraper_class
        logger.info(f"Registered scraper: {name}")

    def get_scraper_for_venue(
        self, venue: str, config: Optional[ScrapingConfig] = None
    ) -> Optional[BaseScraper]:
        """Get appropriate scraper instance for a venue."""
        venue_lower = venue.lower()

        # Look up scraper name for venue
        scraper_name = self._venue_mapping.get(
            venue_lower, self._venue_mapping.get("*", "SemanticScholarScraper")
        )

        # Get scraper class
        scraper_class = self._scrapers.get(scraper_name)
        if not scraper_class:
            logger.error(
                f"No scraper found for venue {venue} (mapped to {scraper_name})"
            )
            return None

        # Instantiate scraper
        try:
            scraper = scraper_class(config or ScrapingConfig())
            return scraper
        except Exception as e:
            logger.error(f"Failed to instantiate scraper {scraper_name}: {e}")
            return None

    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names."""
        return list(self._scrapers.keys())

    def get_supported_venues(self) -> List[str]:
        """Get list of all supported venues."""
        venues = [v for v in self._venue_mapping.keys() if v != "*"]
        return sorted(venues)

    def get_scraper_for_venue_info(self, venue: str) -> Dict[str, str]:
        """Get information about which scraper will be used for a venue."""
        venue_lower = venue.lower()
        scraper_name = self._venue_mapping.get(
            venue_lower, self._venue_mapping.get("*", "SemanticScholarScraper")
        )

        result: Dict[str, Any] = {
            "venue": venue,
            "scraper": scraper_name,
            "is_fallback": venue_lower not in self._venue_mapping,
        }
        return result


# Global registry instance
_registry = None


def get_registry() -> ScraperRegistry:
    """Get global scraper registry instance."""
    global _registry
    if _registry is None:
        _registry = ScraperRegistry()
    return _registry
