"""Paperoni adapters for scraping papers from various sources."""

from .neurips import NeurIPSAdapter
from .mlr import MLRAdapter
from .openreview import OpenReviewAdapter
from .semantic_scholar import SemanticScholarAdapter
from .nature_portfolio import NaturePortfolioAdapter

__all__ = [
    "NeurIPSAdapter",
    "MLRAdapter",
    "OpenReviewAdapter",
    "SemanticScholarAdapter",
    "NaturePortfolioAdapter",
]
