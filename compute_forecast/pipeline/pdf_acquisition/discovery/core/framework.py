"""PDF Discovery Framework for orchestrating multiple sources."""

import logging
from typing import Dict, List, Optional, Callable, Set, TYPE_CHECKING, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from compute_forecast.pipeline.metadata_collection.models import Paper
from .models import PDFRecord, DiscoveryResult
from .collectors import BasePDFCollector
from ..deduplication.engine import PaperDeduplicator

if TYPE_CHECKING:
    from compute_forecast.pipeline.pdf_acquisition.storage.discovery_integration import (
        PDFDiscoveryStorage,
    )

logger = logging.getLogger(__name__)


class PDFDiscoveryFramework:
    """Orchestrates PDF discovery from multiple sources with parallel execution."""

    def __init__(self, storage_backend: Optional["PDFDiscoveryStorage"] = None):
        """Initialize the PDF discovery framework.

        Args:
            storage_backend: Optional storage backend for PDFs
        """
        self.discovered_papers: Dict[str, PDFRecord] = {}
        self.url_to_papers: Dict[str, List[str]] = {}
        self.collectors: List[BasePDFCollector] = []
        self.venue_priorities: Dict[str, List[str]] = {}
        self.deduplicator = PaperDeduplicator()
        self.storage_backend = storage_backend

    def add_collector(self, collector: BasePDFCollector):
        """Add a PDF collector to the framework.

        Args:
            collector: PDF collector instance
        """
        self.collectors.append(collector)
        logger.info(f"Added collector: {collector.source_name}")

    def set_venue_priorities(self, priorities: Dict[str, List[str]]):
        """Set source priorities by venue.

        Args:
            priorities: Dict mapping venue names to ordered list of preferred sources
        """
        self.venue_priorities = priorities

        # Convert venue priorities to source priority rankings for deduplication
        source_rankings = {}
        max_priority = 10  # Start with high base priority

        for venue, sources in priorities.items():
            for i, source in enumerate(sources):
                # Higher priority = higher score (reverse order)
                # First source gets highest score, subsequent sources get lower scores
                priority_score = max_priority - i
                if source not in source_rankings:
                    source_rankings[source] = priority_score
                else:
                    # Use highest priority seen across all venues
                    source_rankings[source] = max(
                        source_rankings[source], priority_score
                    )

        # Update deduplication engine with source priorities
        from ..deduplication.version_manager import SourcePriority

        if source_rankings:
            custom_priorities = SourcePriority(
                source_rankings=source_rankings, prefer_published=True
            )
            self.deduplicator.version_manager.set_priorities(custom_priorities)

    def discover_pdfs(
        self,
        papers: List[Paper],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> DiscoveryResult:
        """Discover PDFs for a list of papers using all collectors.

        Args:
            papers: List of papers to discover PDFs for
            progress_callback: Optional callback for progress updates

        Returns:
            DiscoveryResult with discovered PDFs and statistics
        """
        # Clear previous discoveries for this batch
        self.discovered_papers.clear()
        self.url_to_papers.clear()

        if not papers:
            return DiscoveryResult(
                total_papers=0,
                discovered_count=0,
                records=[],
                failed_papers=[],
                source_statistics={},
                execution_time_seconds=0.0,
            )

        start_time = time.time()
        logger.info(
            f"Starting PDF discovery for {len(papers)} papers with {len(self.collectors)} collectors"
        )

        # Handle case with no collectors
        if not self.collectors:
            return DiscoveryResult(
                total_papers=len(papers),
                discovered_count=0,
                records=[],
                failed_papers=[p.paper_id for p in papers if p.paper_id is not None],
                source_statistics={},
                execution_time_seconds=time.time() - start_time,
            )

        # Group papers by venue for prioritization
        papers_by_venue = self._group_papers_by_venue(papers)

        # Track failed papers
        failed_papers: Set[str] = set(
            p.paper_id for p in papers if p.paper_id is not None
        )

        # Collect statistics
        source_stats = {}

        # Collect all discovered records for deduplication
        all_discovered_records: Dict[str, List[PDFRecord]] = {}
        # Map PDFRecord to Paper for deduplication
        record_to_paper: Dict[str, Paper] = {}

        # Run collectors in parallel
        with ThreadPoolExecutor(max_workers=max(1, len(self.collectors))) as executor:
            # Submit all collector tasks
            future_to_collector = {}

            for collector in self.collectors:
                # Get papers for this collector based on venue priorities
                collector_papers = self._get_papers_for_collector(
                    collector, papers, papers_by_venue
                )

                if collector_papers:
                    future = executor.submit(collector.discover_pdfs, collector_papers)
                    future_to_collector[future] = collector

            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_collector):
                collector = future_to_collector[future]

                try:
                    results = future.result()

                    # Collect discovered PDFs for deduplication
                    for paper_id, pdf_record in results.items():
                        # Store paper data mapping for deduplication
                        paper = next(
                            (p for p in papers if p.paper_id == paper_id), None
                        )
                        if paper:
                            # Use pdf_record's paper_id as key for mapping
                            record_to_paper[pdf_record.paper_id] = paper

                        # Group by base paper ID for deduplication
                        base_id = paper_id
                        if base_id not in all_discovered_records:
                            all_discovered_records[base_id] = []
                        all_discovered_records[base_id].append(pdf_record)

                        failed_papers.discard(paper_id)

                    # Update progress
                    completed += 1
                    if progress_callback:
                        progress_callback(
                            completed, len(future_to_collector), collector.source_name
                        )

                except Exception as e:
                    logger.error(f"Collector {collector.source_name} failed: {e}")

                # Collect statistics
                stats = collector.get_statistics()
                source_stats[collector.source_name] = stats

        # Apply sophisticated deduplication
        if all_discovered_records:
            logger.info(
                f"Running deduplication on {sum(len(records) for records in all_discovered_records.values())} records"
            )

            try:
                deduplicated_records = self.deduplicator.deduplicate_records(
                    all_discovered_records, record_to_paper
                )

                # Update discovered_papers with deduplicated results
                self.discovered_papers.clear()
                self.url_to_papers.clear()

                for group_id, best_record in deduplicated_records.items():
                    # Use the paper_id from the best record
                    self.discovered_papers[best_record.paper_id] = best_record

                    # Track URL to paper mapping
                    url = best_record.pdf_url
                    if url not in self.url_to_papers:
                        self.url_to_papers[url] = []
                    if best_record.paper_id not in self.url_to_papers[url]:
                        self.url_to_papers[url].append(best_record.paper_id)

            except Exception as e:
                logger.error(f"Deduplication failed: {e}. Falling back to simple mode.")
                # Fall back to simple deduplication (first-come-first-served)
                self.discovered_papers.clear()
                self.url_to_papers.clear()

                for base_id, records in all_discovered_records.items():
                    if records:
                        # Just take the first record as fallback
                        best_record = records[0]
                        self.discovered_papers[best_record.paper_id] = best_record

                        url = best_record.pdf_url
                        if url not in self.url_to_papers:
                            self.url_to_papers[url] = []
                        if best_record.paper_id not in self.url_to_papers[url]:
                            self.url_to_papers[url].append(best_record.paper_id)

        # Build final result
        discovered_records = list(self.discovered_papers.values())

        execution_time = time.time() - start_time
        logger.info(
            f"PDF discovery completed in {execution_time:.2f}s. "
            f"Discovered {len(discovered_records)}/{len(papers)} PDFs"
        )

        return DiscoveryResult(
            total_papers=len(papers),
            discovered_count=len(discovered_records),
            records=discovered_records,
            failed_papers=list(failed_papers),
            source_statistics=source_stats,
            execution_time_seconds=execution_time,
        )

    def _group_papers_by_venue(self, papers: List[Paper]) -> Dict[str, List[Paper]]:
        """Group papers by venue for prioritization.

        Args:
            papers: List of papers to group

        Returns:
            Dictionary mapping venue to list of papers
        """
        grouped: Dict[str, List[Paper]] = {}
        for paper in papers:
            venue = paper.venue or "unknown"
            if venue not in grouped:
                grouped[venue] = []
            grouped[venue].append(paper)
        return grouped

    def _get_papers_for_collector(
        self,
        collector: BasePDFCollector,
        all_papers: List[Paper],
        papers_by_venue: Dict[str, List[Paper]],
    ) -> List[Paper]:
        """Get papers that should be processed by this collector.

        Args:
            collector: The collector to get papers for
            all_papers: All papers to process
            papers_by_venue: Papers grouped by venue

        Returns:
            List of papers for this collector
        """
        if not self.venue_priorities:
            # No priorities set, all collectors process all papers
            return all_papers

        papers_for_collector = []

        for venue, venue_papers in papers_by_venue.items():
            # Get priority sources for this venue
            priority_sources = self.venue_priorities.get(
                venue, self.venue_priorities.get("default", [])
            )

            # If this collector is the top priority for the venue, process all papers
            if priority_sources and collector.source_name == priority_sources[0]:
                papers_for_collector.extend(venue_papers)
            # Otherwise, only process papers not yet discovered
            else:
                for paper in venue_papers:
                    if paper.paper_id not in self.discovered_papers:
                        papers_for_collector.append(paper)

        return papers_for_collector

    def get_deduplication_stats(self) -> Dict:
        """Get statistics about the last deduplication run."""
        return self.deduplicator.get_deduplication_stats()

    def discover_and_store_pdfs(
        self,
        papers: List[Paper],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        download_pdfs: bool = True,
        upload_to_drive: bool = True,
    ) -> Dict[str, Any]:
        """Discover PDFs and store them using the storage backend.

        Args:
            papers: List of papers to discover PDFs for
            progress_callback: Optional callback for progress updates
            download_pdfs: Whether to download PDFs after discovery
            upload_to_drive: Whether to upload PDFs to Google Drive

        Returns:
            Combined discovery and storage statistics
        """
        if not self.storage_backend:
            raise ValueError(
                "Storage backend not configured. Initialize framework with storage_backend parameter."
            )

        # First, discover PDFs
        discovery_result = self.discover_pdfs(papers, progress_callback)

        # Then process with storage backend
        storage_stats = self.storage_backend.process_discovery_results(
            discovery_result,
            download_pdfs=download_pdfs,
            upload_to_drive=upload_to_drive,
            show_progress=True,
        )

        # Return combined statistics
        return {
            "discovery": {
                "total_papers": discovery_result.total_papers,
                "discovered_count": discovery_result.discovered_count,
                "failed_papers": len(discovery_result.failed_papers),
                "execution_time": discovery_result.execution_time_seconds,
            },
            "storage": storage_stats,
            "source_statistics": discovery_result.source_statistics,
        }
