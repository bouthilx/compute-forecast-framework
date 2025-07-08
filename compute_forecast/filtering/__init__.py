"""
Real-Time Filtering by Computational Research Criteria for Issue #8.
Provides intelligent filtering based on computational richness, author affiliations, and venue relevance.
"""

from .computational_analyzer import ComputationalAnalyzer
from .authorship_classifier import AuthorshipClassifier
from .venue_relevance_scorer import VenueRelevanceScorer
from .computational_filter import ComputationalResearchFilter

__all__ = [
    "ComputationalAnalyzer",
    "AuthorshipClassifier",
    "VenueRelevanceScorer",
    "ComputationalResearchFilter",
]
