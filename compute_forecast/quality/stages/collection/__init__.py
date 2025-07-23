"""Collection stage quality checking."""

from .checker import CollectionQualityChecker
from .models import CollectionQualityMetrics, CollectionContext
from .formatters import (
    TextReportFormatter,
    JSONReportFormatter,
    MarkdownReportFormatter,
)

# Import formatter adapters to register them
from . import formatter_adapters  # noqa: F401

__all__ = [
    "CollectionQualityChecker",
    "CollectionQualityMetrics",
    "CollectionContext",
    "TextReportFormatter",
    "JSONReportFormatter",
    "MarkdownReportFormatter",
]
