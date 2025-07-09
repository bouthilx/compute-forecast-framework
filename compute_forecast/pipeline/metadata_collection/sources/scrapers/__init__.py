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
from .error_handling import (
    ErrorType,
    ScrapingError,
    ScrapingMonitor,
    retry_on_error,
    RateLimiter,
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
    # Error handling
    "ErrorType",
    "ScrapingError",
    "ScrapingMonitor",
    "retry_on_error",
    "RateLimiter",
]
