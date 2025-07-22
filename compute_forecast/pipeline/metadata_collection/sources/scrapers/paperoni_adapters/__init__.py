"""Paperoni adapters for scraping papers from various sources."""

from .neurips import NeurIPSAdapter
from .mlr import MLRAdapter
from .openreview import OpenReviewAdapter
from .openreview_v2 import OpenReviewAdapterV2
from .semantic_scholar import SemanticScholarAdapter
from .nature_portfolio import NaturePortfolioAdapter

__all__ = [
    "NeurIPSAdapter",
    "MLRAdapter",
    "OpenReviewAdapter",
    "OpenReviewAdapterV2",
    "SemanticScholarAdapter",
    "NaturePortfolioAdapter",
]
