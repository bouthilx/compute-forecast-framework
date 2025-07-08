"""Web scraper infrastructure for collecting papers from conference and journal websites"""

from .base import (
    BaseScraper,
    ConferenceProceedingsScraper,
    JournalPublisherScraper,
    APIEnhancedScraper,
    ScrapingConfig,
    ScrapingResult,
)
from .models import (
    SimplePaper,
    PaperoniAdapter,
    ScrapingBatch,
)
from .error_handling import (
    ErrorType,
    ScrapingError,
    ScrapingMonitor,
    retry_on_error,
    RateLimiter,
)
from .conference_scrapers import IJCAIScraper, ACLAnthologyScraper

__all__ = [
    # Base classes
    "BaseScraper",
    "ConferenceProceedingsScraper",
    "JournalPublisherScraper",
    "APIEnhancedScraper",
    "ScrapingConfig",
    "ScrapingResult",
    # Models
    "SimplePaper",
    "PaperoniAdapter",
    "ScrapingBatch",
    # Error handling
    "ErrorType",
    "ScrapingError",
    "ScrapingMonitor",
    "retry_on_error",
    "RateLimiter",
    # Scrapers
    "IJCAIScraper",
    "ACLAnthologyScraper",
]