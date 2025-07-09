"""Enhanced API source clients for research data collection."""

from compute_forecast.pipeline.metadata_collection.sources.enhanced_crossref import (
    EnhancedCrossrefClient,
)
from compute_forecast.pipeline.metadata_collection.sources.enhanced_openalex import (
    EnhancedOpenAlexClient,
)
from compute_forecast.pipeline.metadata_collection.sources.enhanced_semantic_scholar import (
    EnhancedSemanticScholarClient,
)

__all__ = [
    "EnhancedCrossrefClient",
    "EnhancedOpenAlexClient",
    "EnhancedSemanticScholarClient",
]
