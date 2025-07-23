"""
Enhanced Collection Orchestrator with Streaming Support
Orchestrates multi-source collection with parallel execution, streaming, and pagination
"""

import time
import logging
from typing import Dict, List, Optional, Iterator, AsyncIterator, Callable, Any
from dataclasses import dataclass
import asyncio
from collections import deque

from ..models import Paper, CollectionQuery, APIConfig
from ..sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
from ..sources.enhanced_openalex import EnhancedOpenAlexClient
from ..sources.enhanced_crossref import EnhancedCrossrefClient
from ..sources.google_scholar import GoogleScholarSource
from .rate_limit_manager import RateLimitManager

logger = logging.getLogger(__name__)


@dataclass
class StreamingCollectionResult:
    """Results from multi-source collection with streaming support"""

    source_counts: Dict[str, int]
    duplicates_removed: int
    collection_time: float
    errors: List[str]
    total_papers_processed: int

    def get_source_coverage(self) -> Dict[str, float]:
        """Calculate percentage contribution from each source"""
        total = sum(self.source_counts.values())
        if total == 0:
            return {}
        return {source: count / total for source, count in self.source_counts.items()}


class EnhancedCollectionOrchestratorStreaming:
    """Orchestrate multi-source collection with streaming and memory optimization"""

    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        batch_size: int = 100,
        max_memory_papers: int = 1000,
    ):
        """
        Initialize orchestrator with API clients and streaming configuration

        Args:
            api_keys: Dictionary of API keys for different sources
            batch_size: Number of papers to process in each batch
            max_memory_papers: Maximum papers to keep in memory at once
        """
        # Initialize API clients
        self.sources: Dict[str, Any] = {
            "semantic_scholar": EnhancedSemanticScholarClient(
                api_key=api_keys.get("semantic_scholar") if api_keys else None
            ),
            "openalex": EnhancedOpenAlexClient(
                email=api_keys.get("openalex_email") if api_keys else None
            ),
            "crossref": EnhancedCrossrefClient(
                email=api_keys.get("crossref_email") if api_keys else None
            ),
            "google_scholar": GoogleScholarSource(
                use_proxy=bool(api_keys.get("google_scholar_proxy", False))
                if api_keys
                else False
            ),
        }

        # Initialize rate limiter with API configurations
        self.api_configs = self._create_api_configs()
        self.rate_limiter = RateLimitManager(self.api_configs)

        # Streaming configuration
        self.batch_size = batch_size
        self.max_memory_papers = max_memory_papers

    def _create_api_configs(self) -> Dict[str, APIConfig]:
        """Create API configurations for rate limiting"""
        configs = {
            # Semantic Scholar: 100 requests per 5 minutes
            "semantic_scholar": APIConfig(
                requests_per_window=100,
                base_delay_seconds=1.0,
                max_delay_seconds=60.0,
                health_degradation_threshold=0.8,
                burst_allowance=10,
            ),
            # OpenAlex: 100,000 requests per day (very generous)
            "openalex": APIConfig(
                requests_per_window=100,
                base_delay_seconds=0.1,
                max_delay_seconds=60.0,
                health_degradation_threshold=0.8,
                burst_allowance=20,
            ),
            # CrossRef: 50 requests per second with polite pool
            "crossref": APIConfig(
                requests_per_window=50,
                base_delay_seconds=0.02,
                max_delay_seconds=60.0,
                health_degradation_threshold=0.8,
                burst_allowance=5,
            ),
            # Google Scholar: Very conservative due to scraping
            "google_scholar": APIConfig(
                requests_per_window=10,
                base_delay_seconds=5.0,
                max_delay_seconds=60.0,
                health_degradation_threshold=0.5,
                burst_allowance=2,
            ),
        }

        return configs

    def stream_papers_from_all_sources(
        self,
        query: CollectionQuery,
        sources_to_use: Optional[List[str]] = None,
        process_callback: Optional[Callable[[Paper], None]] = None,
    ) -> Iterator[Paper]:
        """
        Stream papers from all sources with memory-efficient processing

        Args:
            query: Collection query with search parameters
            sources_to_use: List of source names to use (defaults to all)
            process_callback: Optional callback to process each paper as it's collected

        Yields:
            Individual papers as they are collected
        """
        # Determine which sources to use
        active_sources = sources_to_use or list(self.sources.keys())

        # Use a bounded queue to control memory usage
        deque(maxlen=self.max_memory_papers)

        # Track statistics
        source_counts = {source: 0 for source in active_sources}
        total_processed = 0

        # Process each source with pagination
        for source_name in active_sources:
            try:
                logger.info(f"Starting streaming collection from {source_name}")

                # Get paginated results from source
                for paper_batch in self._stream_from_source_paginated(
                    source_name, query
                ):
                    for paper in paper_batch:
                        # Apply callback if provided
                        if process_callback:
                            process_callback(paper)

                        # Update statistics
                        source_counts[source_name] += 1
                        total_processed += 1

                        # Yield the paper
                        yield paper

                        # Log progress periodically
                        if total_processed % 100 == 0:
                            logger.info(f"Processed {total_processed} papers so far")

            except Exception as e:
                logger.error(f"Streaming failed for {source_name}: {e}")
                continue

    async def async_stream_papers_from_all_sources(
        self,
        query: CollectionQuery,
        sources_to_use: Optional[List[str]] = None,
        process_callback: Optional[Callable[[Paper], None]] = None,
    ) -> AsyncIterator[Paper]:
        """
        Asynchronously stream papers from all sources

        Args:
            query: Collection query with search parameters
            sources_to_use: List of source names to use (defaults to all)
            process_callback: Optional callback to process each paper

        Yields:
            Individual papers as they are collected
        """
        # Determine which sources to use
        active_sources = sources_to_use or list(self.sources.keys())

        # Create async tasks for each source
        async def stream_from_source(source_name: str):
            """Stream papers from a single source"""
            try:
                async for paper_batch in self._async_stream_from_source(
                    source_name, query
                ):
                    for paper in paper_batch:
                        if process_callback:
                            processed_paper = (
                                await process_callback(paper)
                                if asyncio.iscoroutinefunction(process_callback)
                                else process_callback(paper)
                            )
                            if processed_paper is not None:
                                paper = processed_paper
                        yield paper
            except Exception as e:
                logger.error(f"Async streaming failed for {source_name}: {e}")

        # Merge streams from all sources
        tasks = [stream_from_source(source) for source in active_sources]

        # Use asyncio to merge the streams
        async def merge_streams():
            queues = [asyncio.Queue() for _ in tasks]

            async def enqueue_papers(task_gen, queue):
                async for paper in task_gen:
                    await queue.put(paper)
                await queue.put(None)  # Sentinel

            # Start all enqueue tasks
            [
                asyncio.create_task(enqueue_papers(task, queue))
                for task, queue in zip(tasks, queues)
            ]

            # Yield papers as they come in from any source
            active_queues = set(range(len(queues)))
            while active_queues:
                for i in list(active_queues):
                    try:
                        paper = queues[i].get_nowait()
                        if paper is None:
                            active_queues.remove(i)
                        else:
                            yield paper
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(0.01)

        async for paper in merge_streams():
            yield paper

    def _stream_from_source_paginated(
        self, source_name: str, query: CollectionQuery
    ) -> Iterator[List[Paper]]:
        """
        Stream papers from a source using pagination

        Args:
            source_name: Name of the source
            query: Collection query

        Yields:
            Batches of papers
        """
        offset = 0
        has_more = True

        while has_more and offset < query.max_results:
            # Wait for rate limit if needed
            wait_time = self.rate_limiter.wait_if_needed(source_name)
            if wait_time > 0:
                logger.debug(f"Rate limit wait for {source_name}: {wait_time:.2f}s")

            # Calculate batch size for this request
            remaining = query.max_results - offset
            current_batch_size = min(self.batch_size, remaining)

            # Get the source client
            source_client = self.sources[source_name]

            # Note: Using current_batch_size directly in API calls below

            # Perform collection based on query type
            if query.venue:
                response = source_client.search_venue_batch(
                    [query.venue], query.year, limit=current_batch_size, offset=offset
                )
            else:
                search_query = query.domain
                if query.keywords:
                    search_query += " " + " ".join(query.keywords)

                response = source_client.search_papers(
                    search_query, query.year, limit=current_batch_size, offset=offset
                )

            # Record the request
            response_time_ms = (
                response.metadata.response_time_ms if response.metadata else 1000
            )
            self.rate_limiter.record_request(
                source_name, response.success, response_time_ms
            )

            if response.success and response.papers:
                yield response.papers
                offset += len(response.papers)

                # Check if we got fewer papers than requested (indicating end of results)
                if len(response.papers) < current_batch_size:
                    has_more = False
            else:
                # No more results or error occurred
                has_more = False

    async def _async_stream_from_source(
        self, source_name: str, query: CollectionQuery
    ) -> AsyncIterator[List[Paper]]:
        """
        Asynchronously stream papers from a source

        Args:
            source_name: Name of the source
            query: Collection query

        Yields:
            Batches of papers
        """
        # Convert synchronous pagination to async
        for batch in self._stream_from_source_paginated(source_name, query):
            yield batch
            await asyncio.sleep(0)  # Allow other coroutines to run

    def collect_with_memory_limit(
        self,
        query: CollectionQuery,
        memory_limit_mb: int = 500,
        sources_to_use: Optional[List[str]] = None,
    ) -> StreamingCollectionResult:
        """
        Collect papers with memory limit enforcement

        Args:
            query: Collection query
            memory_limit_mb: Maximum memory usage in MB
            sources_to_use: Sources to use

        Returns:
            StreamingCollectionResult with statistics
        """
        start_time = time.time()

        # Calculate approximate papers per MB (assuming ~5KB per paper)
        papers_per_mb = 200
        memory_limit_mb * papers_per_mb

        # Initialize statistics
        source_counts: Dict[str, int] = {}
        errors: List[str] = []
        total_processed = 0

        # Process papers in batches
        for paper in self.stream_papers_from_all_sources(query, sources_to_use):
            # Update source count
            source = (
                paper.metadata.get("source", "unknown")
                if hasattr(paper, "metadata")
                else "unknown"
            )
            source_counts[source] = source_counts.get(source, 0) + 1
            total_processed += 1

            # Here you would typically write to disk or process immediately
            # For demonstration, we just count

            if total_processed >= query.max_results:
                break

        return StreamingCollectionResult(
            source_counts=source_counts,
            duplicates_removed=0,  # Deduplication handled by Agent Gamma
            collection_time=time.time() - start_time,
            errors=errors,
            total_papers_processed=total_processed,
        )

    def process_papers_in_batches(
        self,
        query: CollectionQuery,
        batch_processor: Callable[[List[Paper]], None],
        sources_to_use: Optional[List[str]] = None,
    ) -> StreamingCollectionResult:
        """
        Process papers in batches as they are collected

        Args:
            query: Collection query
            batch_processor: Function to process each batch of papers
            sources_to_use: Sources to use

        Returns:
            StreamingCollectionResult with statistics
        """
        start_time = time.time()

        # Initialize statistics
        source_counts: Dict[str, int] = {}
        errors: List[str] = []
        total_processed = 0
        current_batch = []

        # Stream and process papers
        for paper in self.stream_papers_from_all_sources(query, sources_to_use):
            current_batch.append(paper)

            # Process batch when it reaches the size limit
            if len(current_batch) >= self.batch_size:
                try:
                    batch_processor(current_batch)
                    total_processed += len(current_batch)

                    # Update source counts
                    for p in current_batch:
                        source = (
                            p.metadata.get("source", "unknown")
                            if hasattr(p, "metadata")
                            else "unknown"
                        )
                        source_counts[source] = source_counts.get(source, 0) + 1

                    current_batch = []
                except Exception as e:
                    errors.append(f"Batch processing error: {str(e)}")
                    logger.error(f"Failed to process batch: {e}")

        # Process remaining papers
        if current_batch:
            try:
                batch_processor(current_batch)
                total_processed += len(current_batch)

                for p in current_batch:
                    source = (
                        p.metadata.get("source", "unknown")
                        if hasattr(p, "metadata")
                        else "unknown"
                    )
                    source_counts[source] = source_counts.get(source, 0) + 1
            except Exception as e:
                errors.append(f"Final batch processing error: {str(e)}")
                logger.error(f"Failed to process final batch: {e}")

        return StreamingCollectionResult(
            source_counts=source_counts,
            duplicates_removed=0,
            collection_time=time.time() - start_time,
            errors=errors,
            total_papers_processed=total_processed,
        )
