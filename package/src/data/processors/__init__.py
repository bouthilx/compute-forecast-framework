"""Data processors for venue normalization, deduplication, and analysis."""

from .venue_normalizer import VenueNormalizer, VenueNormalizationResult, BatchNormalizationResult, VenueMappingStats
from .venue_mapping_loader import VenueMappingLoader, VenueConfig
from .fuzzy_venue_matcher import FuzzyVenueMatcher, FuzzyMatchResult
from .deduplication_engine import (
    DeduplicationEngine, 
    DeduplicationResult, 
    DuplicateMatch, 
    DuplicateGroup, 
    SimilarityScore,
    DeduplicationQualityReport
)
from .title_normalizer import TitleNormalizer, TitleSimilarityCache
from .author_matcher import AuthorMatcher, AuthorMatchResult
from .similarity_index import SimilarityIndex, IndexStats, BatchSimilarityProcessor

__all__ = [
    # Venue normalization
    'VenueNormalizer',
    'VenueNormalizationResult', 
    'BatchNormalizationResult',
    'VenueMappingStats',
    'VenueMappingLoader',
    'VenueConfig',
    'FuzzyVenueMatcher',
    'FuzzyMatchResult',
    
    # Deduplication
    'DeduplicationEngine',
    'DeduplicationResult',
    'DuplicateMatch',
    'DuplicateGroup',
    'SimilarityScore',
    'DeduplicationQualityReport',
    'TitleNormalizer',
    'TitleSimilarityCache',
    'AuthorMatcher',
    'AuthorMatchResult',
    'SimilarityIndex',
    'IndexStats',
    'BatchSimilarityProcessor'
]