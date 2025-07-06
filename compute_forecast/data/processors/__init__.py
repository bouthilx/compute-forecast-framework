"""Data processors for venue normalization, deduplication, citation analysis, and filtering."""

# Venue normalization imports
from .venue_normalizer import (
    VenueNormalizer,
    VenueNormalizationResult,
    BatchNormalizationResult,
    VenueMappingStats,
)
from .venue_mapping_loader import VenueMappingLoader, VenueConfig
from .fuzzy_venue_matcher import FuzzyVenueMatcher, FuzzyMatchResult

# Citation analysis imports
from .citation_analyzer import CitationAnalyzer
from .breakthrough_detector import BreakthroughDetector
from .adaptive_threshold_calculator import AdaptiveThresholdCalculator
from .citation_config import CitationConfig
from .citation_statistics import (
    CitationAnalysisReport,
    VenueCitationStats,
    YearCitationStats,
    CitationFilterResult,
    BreakthroughPaper,
    AdaptiveThreshold,
    FilteringQualityReport,
)

__all__ = [
    # Venue normalization exports
    "VenueNormalizer",
    "VenueNormalizationResult",
    "BatchNormalizationResult",
    "VenueMappingStats",
    "VenueMappingLoader",
    "VenueConfig",
    "FuzzyVenueMatcher",
    "FuzzyMatchResult",
    # Citation analysis exports
    "CitationAnalyzer",
    "BreakthroughDetector",
    "AdaptiveThresholdCalculator",
    "CitationConfig",
    "CitationAnalysisReport",
    "VenueCitationStats",
    "YearCitationStats",
    "CitationFilterResult",
    "BreakthroughPaper",
    "AdaptiveThreshold",
    "FilteringQualityReport",
]
