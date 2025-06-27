"""Enhanced API source clients for research data collection."""

from .enhanced_crossref import EnhancedCrossrefClient
from .enhanced_openalex import EnhancedOpenAlexClient
from .enhanced_semantic_scholar import EnhancedSemanticScholarClient

__all__ = [
    'EnhancedCrossrefClient',
    'EnhancedOpenAlexClient',
    'EnhancedSemanticScholarClient'
]