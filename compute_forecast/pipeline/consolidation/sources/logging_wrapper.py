"""
Logging wrapper for consolidation sources to track API activity.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import functools
import logging

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper
from ..models import EnrichmentResult


class LoggingSourceWrapper(BaseConsolidationSource):
    """Wraps a consolidation source to add detailed logging of API activity"""
    
    def __init__(self, source: BaseConsolidationSource):
        """
        Initialize logging wrapper.
        
        Args:
            source: The actual consolidation source to wrap
        """
        # Initialize with source's config
        super().__init__(source.name, source.config)
        self.wrapped_source = source
        self.logger = logging.getLogger(f"consolidation.{source.name}")
        
        # Copy over important attributes
        self.api_calls = source.api_calls
        
        # Track request details
        self._last_api_start = None
        self._request_count = 0
        
        # Patch the wrapped source's rate limit method to log delays
        original_rate_limit = self.wrapped_source._rate_limit
        def logged_rate_limit():
            elapsed = time.time() - self.wrapped_source.last_request_time
            sleep_time = (1.0 / self.config.rate_limit) - elapsed
            if sleep_time > 0:
                self.logger.info(f"Rate limiting: waiting {sleep_time:.2f}s before next request")
            original_rate_limit()
        self.wrapped_source._rate_limit = logged_rate_limit
    
    def __getattr__(self, name):
        """Forward attribute access to wrapped source."""
        return getattr(self.wrapped_source, name)
        
        
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers with logging"""
        self.logger.info(f"Preparing paper ID lookup for {len(papers)} papers")
        
        start_time = time.time()
        self.logger.info(f"→ Sending paper ID lookup request...")
        
        try:
            result = self.wrapped_source.find_papers(papers)
            duration = time.time() - start_time
            self.logger.info(f"← Received response in {duration:.2f}s - found {len(result)} matches")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"← Request failed after {duration:.2f}s: {str(e)}")
            raise
            
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all fields with logging"""
        self.logger.info(f"Preparing to fetch enrichment data for {len(source_ids)} papers")
        
        start_time = time.time()
        self.logger.info(f"→ Sending enrichment data request...")
        
        try:
            result = self.wrapped_source.fetch_all_fields(source_ids)
            duration = time.time() - start_time
            
            # Count enrichments found
            citations = sum(1 for r in result.values() if r.get('citations') is not None)
            abstracts = sum(1 for r in result.values() if r.get('abstract'))
            urls = sum(1 for r in result.values() if r.get('urls'))
            identifiers = sum(1 for r in result.values() if r.get('identifiers'))
            
            self.logger.info(f"← Received response in {duration:.2f}s - "
                            f"citations: {citations}, abstracts: {abstracts}, "
                            f"urls: {urls}, identifiers: {identifiers}")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"← Request failed after {duration:.2f}s: {str(e)}")
            raise
            
    def enrich_papers(self, papers: List[Paper], progress_callback=None) -> List[EnrichmentResult]:
        """Main enrichment workflow with logging"""
        batch_size = self.config.find_batch_size or self.config.batch_size
        self.logger.info(f"Processing batch of {len(papers)} papers")
        
        # Track papers processed
        self._papers_processed = 0
        
        # Create a wrapped progress callback that logs
        def logging_progress_callback(result):
            self._papers_processed += 1
            
            # Log every 50 papers or if we found enrichments
            if self._papers_processed % 50 == 0:
                self.logger.debug(f"Progress: {self._papers_processed}/{len(papers)} papers processed")
            
            # Count enrichments in this result  
            if result.citations or result.abstracts or result.urls or result.identifiers:
                counts = []
                if result.citations:
                    counts.append(f"{len(result.citations)} citations")
                if result.abstracts:
                    counts.append(f"{len(result.abstracts)} abstracts")
                if result.urls:
                    counts.append(f"{len(result.urls)} URLs")
                if result.identifiers:
                    counts.append(f"{len(result.identifiers)} IDs")
                
                # Only log individual papers in debug mode
                if counts and self._papers_processed <= 5:  # First 5 papers only
                    self.logger.debug(f"Paper {result.paper_id}: found {', '.join(counts)}")
            
            # Call original callback if provided
            if progress_callback:
                progress_callback(result)
        
        # Call wrapped source's enrich_papers
        start_time = time.time()
        initial_api_calls = self.wrapped_source.api_calls
        
        result = self.wrapped_source.enrich_papers(papers, logging_progress_callback)
        duration = time.time() - start_time
        
        # Update our API call counter
        self.api_calls = self.wrapped_source.api_calls
        api_calls_made = self.api_calls - initial_api_calls
        
        if api_calls_made > 0:
            self.logger.info(f"Made {api_calls_made} API call(s) during this batch")
        
        # Log batch completion
        total_citations = sum(len(r.citations) for r in result)
        total_abstracts = sum(len(r.abstracts) for r in result)
        total_urls = sum(len(r.urls) for r in result)
        total_identifiers = sum(len(r.identifiers) for r in result)
        
        self.logger.info(f"Batch completed in {duration:.2f}s - Total enrichments: "
                        f"{total_citations} citations, {total_abstracts} abstracts, "
                        f"{total_urls} URLs, {total_identifiers} IDs")
        
        return result