"""PDF Discovery Framework for orchestrating multiple sources."""

import logging
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.data.models import Paper
from .models import PDFRecord, DiscoveryResult
from .collectors import BasePDFCollector

logger = logging.getLogger(__name__)


class PDFDiscoveryFramework:
    """Orchestrates PDF discovery from multiple sources with parallel execution."""
    
    def __init__(self):
        """Initialize the PDF discovery framework."""
        self.discovered_papers: Dict[str, PDFRecord] = {}
        self.url_to_papers: Dict[str, List[str]] = {}
        self.collectors: List[BasePDFCollector] = []
        self.venue_priorities: Dict[str, List[str]] = {}
    
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
    
    def discover_pdfs(
        self, 
        papers: List[Paper],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
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
                execution_time_seconds=0.0
            )
        
        start_time = time.time()
        logger.info(f"Starting PDF discovery for {len(papers)} papers with {len(self.collectors)} collectors")
        
        # Handle case with no collectors
        if not self.collectors:
            return DiscoveryResult(
                total_papers=len(papers),
                discovered_count=0,
                records=[],
                failed_papers=[p.paper_id for p in papers],
                source_statistics={},
                execution_time_seconds=time.time() - start_time
            )
        
        # Group papers by venue for prioritization
        papers_by_venue = self._group_papers_by_venue(papers)
        
        # Track failed papers
        failed_papers: Set[str] = set(p.paper_id for p in papers)
        
        # Collect statistics
        source_stats = {}
        
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
                    
                    # Process discovered PDFs
                    for paper_id, pdf_record in results.items():
                        self._add_discovery(pdf_record)
                        failed_papers.discard(paper_id)
                    
                    # Update progress
                    completed += 1
                    if progress_callback:
                        progress_callback(
                            completed, 
                            len(future_to_collector), 
                            collector.source_name
                        )
                    
                except Exception as e:
                    logger.error(f"Collector {collector.source_name} failed: {e}")
                
                # Collect statistics
                stats = collector.get_statistics()
                source_stats[collector.source_name] = stats
        
        # Build final result
        discovered_records = list(self.discovered_papers.values())
        
        execution_time = time.time() - start_time
        logger.info(f"PDF discovery completed in {execution_time:.2f}s. "
                   f"Discovered {len(discovered_records)}/{len(papers)} PDFs")
        
        return DiscoveryResult(
            total_papers=len(papers),
            discovered_count=len(discovered_records),
            records=discovered_records,
            failed_papers=list(failed_papers),
            source_statistics=source_stats,
            execution_time_seconds=execution_time
        )
    
    def _group_papers_by_venue(self, papers: List[Paper]) -> Dict[str, List[Paper]]:
        """Group papers by venue for prioritization.
        
        Args:
            papers: List of papers to group
            
        Returns:
            Dictionary mapping venue to list of papers
        """
        grouped = {}
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
        papers_by_venue: Dict[str, List[Paper]]
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
                venue, 
                self.venue_priorities.get("default", [])
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
    
    def _add_discovery(self, pdf_record: PDFRecord):
        """Add a discovered PDF to the framework.
        
        Args:
            pdf_record: The discovered PDF record
        """
        paper_id = pdf_record.paper_id
        
        # Check if we already have a record for this paper
        if paper_id in self.discovered_papers:
            existing = self.discovered_papers[paper_id]
            # Keep the one with higher confidence
            if pdf_record.confidence_score > existing.confidence_score:
                logger.debug(f"Replacing PDF for {paper_id}: "
                           f"{existing.source} ({existing.confidence_score:.2f}) -> "
                           f"{pdf_record.source} ({pdf_record.confidence_score:.2f})")
                self.discovered_papers[paper_id] = pdf_record
        else:
            self.discovered_papers[paper_id] = pdf_record
        
        # Track URL to paper mapping
        url = pdf_record.pdf_url
        if url not in self.url_to_papers:
            self.url_to_papers[url] = []
        if paper_id not in self.url_to_papers[url]:
            self.url_to_papers[url].append(paper_id)