"""Web scraper infrastructure for collecting papers from conference and journal websites"""

from .base import (
    BaseScaper,
    ConferenceProceedingsScaper,
    JournalPublisherScaper,
    APIEnhancedScaper,
    ScrapingConfig,
    ScrapingResult,
)
from .models import (
    SimplePaper,
    PaperoniAdapter,
    ScrapingBatch,
)

__all__ = [
    # Base classes
    "BaseScaper",
    "ConferenceProceedingsScaper",
    "JournalPublisherScaper",
    "APIEnhancedScaper",
    "ScrapingConfig",
    "ScrapingResult",
    # Models
    "SimplePaper",
    "PaperoniAdapter",
    "ScrapingBatch",
]