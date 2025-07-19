"""Base worker class for parallel consolidation."""

import threading
import queue
import logging
import time
from typing import List, Dict, Any, Optional, Set, Callable
from abc import ABC, abstractmethod
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.models import CitationData, CitationRecord, AbstractData, AbstractRecord, URLData, URLRecord, IdentifierData, IdentifierRecord
from compute_forecast.pipeline.consolidation.sources.base import BaseConsolidationSource

logger = logging.getLogger(__name__)


class ConsolidationWorker(ABC, threading.Thread):
    """Base class for consolidation workers."""
    
    def __init__(
        self,
        name: str,
        input_queue: queue.Queue,
        output_queue: queue.Queue,
        error_queue: queue.Queue,
        progress_callback: Optional[Callable[[int], None]] = None,
        batch_size: int = 50,
        processed_hashes: Optional[Set[str]] = None
    ):
        super().__init__(name=name)
        self.name = name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.progress_callback = progress_callback
        self.batch_size = batch_size
        self.processed_hashes = processed_hashes or set()
        
        # Control flags
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused
        
        # Statistics
        self.papers_processed = 0
        self.papers_enriched = 0
        self.api_calls = 0
        self.start_time = None
        
    def stop(self):
        """Signal the worker to stop."""
        self.stop_event.set()
        
    def pause(self):
        """Pause the worker."""
        self.pause_event.clear()
        
    def resume(self):
        """Resume the worker."""
        self.pause_event.set()
        
    def run(self):
        """Main worker loop."""
        self.start_time = time.time()
        logger.info(f"{self.name} started")
        
        try:
            while not self.stop_event.is_set():
                # Wait if paused
                self.pause_event.wait()
                
                try:
                    # Get paper from queue with timeout
                    paper = self.input_queue.get(timeout=0.1)
                    logger.debug(f"{self.name}: Got paper from queue: {paper.title[:50]}...")
                    
                    # Check if already processed
                    paper_hash = self._get_paper_hash(paper)
                    if paper_hash in self.processed_hashes:
                        logger.debug(f"{self.name}: Skipping already processed paper: {paper.title}")
                        self.papers_processed += 1
                        # Don't update progress - main thread will handle it
                        continue
                    
                    # Process single paper immediately
                    logger.debug(f"{self.name}: Processing paper: {paper.title[:50]}...")
                    self._process_single_paper(paper)
                        
                except queue.Empty:
                    continue
                    
        except Exception as e:
            logger.error(f"{self.name} encountered error: {str(e)}")
            self.error_queue.put({
                'worker': self.name,
                'error': str(e),
                'timestamp': datetime.now()
            })
            
        finally:
            duration = time.time() - self.start_time
            logger.info(
                f"{self.name} stopped. Processed: {self.papers_processed}, "
                f"Enriched: {self.papers_enriched}, API calls: {self.api_calls}, "
                f"Duration: {duration:.1f}s"
            )
    
    def _process_single_paper(self, paper: Paper):
        """Process a single paper."""
        try:
            # Get enrichment data from source
            enrichment_results = self.fetch_enrichment_data([paper])
            
            # Send result to output queue
            if enrichment_results:
                paper, enrichment_data = enrichment_results[0]
                if enrichment_data:
                    self.output_queue.put({
                        'paper': paper,
                        'enrichment': enrichment_data,
                        'source': self.name.lower().replace('worker', '').strip()
                    })
                    self.papers_enriched += 1
                else:
                    # Still send empty result so merge knows this paper was attempted
                    self.output_queue.put({
                        'paper': paper,
                        'enrichment': None,
                        'source': self.name.lower().replace('worker', '').strip()
                    })
            
            # Mark as processed
            paper_hash = self._get_paper_hash(paper)
            self.processed_hashes.add(paper_hash)
            self.papers_processed += 1
                    
        except Exception as e:
            logger.error(f"{self.name} processing error for paper '{paper.title}': {str(e)}")
            self.error_queue.put({
                'worker': self.name,
                'error': f"Processing error: {str(e)}",
                'timestamp': datetime.now(),
                'paper_title': paper.title
            })
            
            # Still mark as processed to avoid infinite retries
            paper_hash = self._get_paper_hash(paper)
            self.processed_hashes.add(paper_hash)
            self.papers_processed += 1
            
            # Send empty result so merge knows this paper was attempted
            self.output_queue.put({
                'paper': paper,
                'enrichment': None,
                'source': self.name.lower().replace('worker', '').strip()
            })
    
    @abstractmethod
    def fetch_enrichment_data(self, papers: List[Paper]) -> List[tuple[Paper, Dict[str, Any]]]:
        """
        Fetch enrichment data for a batch of papers.
        
        Returns list of (paper, enrichment_dict) tuples.
        Enrichment dict should contain fields like:
        - doi, arxiv_id, openalex_id (for ID fields)
        - citations (int)
        - abstract (str)
        - urls (list of str)
        - identifiers (list of {'type': str, 'value': str})
        """
        pass
    
    def _get_paper_hash(self, paper: Paper) -> str:
        """Generate hash for paper (same as in consolidate.py)."""
        title = paper.title.lower().strip() if paper.title else ""
        
        authors = []
        if hasattr(paper, 'authors') and paper.authors:
            for author in paper.authors:
                if isinstance(author, dict):
                    name = author.get('name', '').lower().strip()
                else:
                    name = str(author).lower().strip()
                if name:
                    authors.append(name)
        authors.sort()
        authors_str = ";".join(authors)
        
        venue = paper.venue.lower().strip() if paper.venue else ""
        year = str(paper.year) if paper.year else ""
        
        content = f"{title}|{authors_str}|{venue}|{year}"
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()