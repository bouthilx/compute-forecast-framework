"""
Compute Forecast - A comprehensive tool for analyzing and forecasting computational requirements in ML research.

This package provides tools for:
- Collecting research papers from multiple sources
- Discovering and downloading PDFs
- Extracting computational requirements from papers
- Analyzing trends and making projections
"""

__version__ = "0.1.0"
__author__ = "Compute Forecast Team"

# Core modules
from . import pipeline
from . import core
from . import monitoring
from . import orchestration
from . import quality
from . import testing

# Module aliases for backward compatibility and test imports
from .pipeline.pdf_acquisition import discovery as pdf_discovery
from .pipeline import metadata_collection
from .pipeline import content_extraction as extraction
from .pipeline.metadata_collection import processors as data

__all__ = [
    "__version__",
    "pipeline",
    "core",
    "monitoring",
    "orchestration",
    "quality",
    "testing",
    "pdf_discovery",
    "metadata_collection",
    "extraction",
    "data",
]
