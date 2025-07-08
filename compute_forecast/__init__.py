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
from . import data
from . import pdf_parser
from . import pdf_discovery
from . import analysis
from . import core

__all__ = [
    "__version__",
    "data",
    "pdf_parser",
    "pdf_discovery",
    "analysis",
    "core",
]
