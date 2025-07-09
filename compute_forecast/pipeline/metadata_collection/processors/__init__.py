"""Data processors for venue normalization, deduplication, citation analysis, and filtering."""

# Venue normalization imports
from compute_forecast.pipeline.metadata_collection.processors.venue_normalizer import (
    VenueNormalizer,
    VenueNormalizationResult,
    BatchNormalizationResult,
    VenueMappingStats,
)
from compute_forecast.pipeline.metadata_collection.processors.venue_mapping_loader import (
    VenueMappingLoader,
    VenueConfig,
)
from compute_forecast.pipeline.metadata_collection.processors.fuzzy_venue_matcher import (
    FuzzyVenueMatcher,
    FuzzyMatchResult,
)

# Citation analysis imports
from compute_forecast.pipeline.metadata_collection.processors.citation_analyzer import (
    CitationAnalyzer,
)
from compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector import (
    BreakthroughDetector,
)
from compute_forecast.pipeline.metadata_collection.processors.adaptive_threshold_calculator import (
    AdaptiveThresholdCalculator,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_config import (
    CitationConfig,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_statistics import (
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
