"""
Real-Time Filtering by Computational Research Criteria for Issue #8.
Provides intelligent filtering based on computational richness, author affiliations, and venue relevance.
"""

from compute_forecast.pipeline.paper_filtering.selectors.computational_analyzer import (
    ComputationalAnalyzer,
)
from compute_forecast.pipeline.paper_filtering.selectors.authorship_classifier import (
    AuthorshipClassifier,
)
from compute_forecast.pipeline.paper_filtering.selectors.venue_relevance_scorer import (
    VenueRelevanceScorer,
)
from compute_forecast.pipeline.paper_filtering.selectors.computational_filter import (
    ComputationalResearchFilter,
)

__all__ = [
    "ComputationalAnalyzer",
    "AuthorshipClassifier",
    "VenueRelevanceScorer",
    "ComputationalResearchFilter",
]
