"""PDF Discovery Infrastructure for extracting PDF URLs from multiple sources."""

from .core.models import PDFRecord, DiscoveryResult
from .core.collectors import BasePDFCollector

__all__ = [
    "PDFRecord",
    "DiscoveryResult",
    "BasePDFCollector",
]