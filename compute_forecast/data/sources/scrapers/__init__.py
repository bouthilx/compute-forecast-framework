"""Paperoni adapters for scraping papers from various sources."""

from .neurips import NeurIPSAdapter
from .mlr import MLRAdapter
from .openreview import OpenReviewAdapter
from .semantic_scholar import SemanticScholarAdapter

__all__ = [
    "NeurIPSAdapter",
    "MLRAdapter", 
    "OpenReviewAdapter",
    "SemanticScholarAdapter"
]