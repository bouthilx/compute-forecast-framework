"""PDF Discovery Infrastructure for extracting PDF URLs from multiple sources."""

from .core.models import PDFRecord, DiscoveryResult

__all__ = [
    "PDFRecord",
    "DiscoveryResult",
]