"""PDF Discovery Infrastructure for extracting PDF URLs from multiple sources."""

from .core.models import PDFRecord, DiscoveryResult
from .core.collectors import BasePDFCollector
from .core.framework import PDFDiscoveryFramework

__all__ = [
    "PDFRecord",
    "DiscoveryResult",
    "BasePDFCollector",
    "PDFDiscoveryFramework",
]
