"""Base collector interface for PDF discovery sources."""

from abc import ABC, abstractmethod
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging

from compute_forecast.data.models import Paper
from .models import PDFRecord

logger = logging.getLogger(__name__)


class BasePDFCollector(ABC):
    """Abstract base class for PDF discovery collectors."""

    def __init__(self, source_name: str):
        """Initialize collector with source name.

        Args:
            source_name: Name of the PDF source (e.g., 'arxiv', 'openreview')
        """
        self.source_name = source_name
        self.timeout = 60  # Default 60 second timeout per source
        self.supports_batch = False  # Override if collector supports batch operations

        # Statistics tracking
        self._stats = {"attempted": 0, "successful": 0, "failed": 0}

    @abstractmethod
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        pass

    def discover_pdfs(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
        """Discover PDFs for multiple papers.

        Args:
            papers: List of papers to discover PDFs for

        Returns:
            Dictionary mapping paper_id to PDFRecord for successful discoveries
        """
        if not papers:
            return {}

        logger.info(
            f"Starting PDF discovery for {len(papers)} papers using {self.source_name}"
        )

        results = {}
        self._stats["attempted"] += len(papers)

        # Use batch mode if supported
        if self.supports_batch and hasattr(self, "discover_pdfs_batch"):
            try:
                results = self.discover_pdfs_batch(papers)
                self._stats["successful"] += len(results)
                self._stats["failed"] += len(papers) - len(results)
            except Exception as e:
                logger.error(f"Batch discovery failed for {self.source_name}: {e}")
                self._stats["failed"] += len(papers)
            return results

        # Single paper discovery with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            for paper in papers:
                try:
                    # Submit task with timeout
                    future = executor.submit(self._discover_single, paper)
                    pdf_record = future.result(timeout=self.timeout)

                    results[paper.paper_id] = pdf_record
                    self._stats["successful"] += 1

                except FutureTimeoutError:
                    logger.warning(
                        f"Timeout discovering PDF for {paper.paper_id} from {self.source_name}"
                    )
                    self._stats["failed"] += 1

                except Exception as e:
                    logger.error(
                        f"Error discovering PDF for {paper.paper_id} from {self.source_name}: {e}"
                    )
                    self._stats["failed"] += 1

        logger.info(
            f"Discovered {len(results)}/{len(papers)} PDFs from {self.source_name}"
        )

        return results

    def get_statistics(self) -> Dict[str, int]:
        """Get collector statistics.

        Returns:
            Dictionary with attempted, successful, and failed counts
        """
        return self._stats.copy()

    def reset_statistics(self):
        """Reset collector statistics."""
        self._stats = {"attempted": 0, "successful": 0, "failed": 0}
