"""Web scraper infrastructure for collecting papers from conference and journal websites"""

from .base import (
    BaseScaper,
    ConferenceProceedingsScaper,
    JournalPublisherScaper,
    APIEnhancedScaper,
    ScrapingConfig,
    ScrapingResult,
)

__all__ = [
    "BaseScaper",
    "ConferenceProceedingsScaper",
    "JournalPublisherScaper",
    "APIEnhancedScaper",
    "ScrapingConfig",
    "ScrapingResult",
]