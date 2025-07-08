"""
Enhanced Collection Orchestrator
Orchestrates multi-source collection with parallel execution and integration with deduplication
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ..models import Paper, CollectionQuery, APIConfig
from ..sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
from ..sources.enhanced_openalex import EnhancedOpenAlexClient
from ..sources.enhanced_crossref import EnhancedCrossrefClient
from ..sources.google_scholar import GoogleScholarSource as GoogleScholarClient
from .rate_limit_manager import RateLimitManager

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Results from multi-source collection"""

    papers: List[Paper]
    source_counts: Dict[str, int]
    duplicates_removed: int
    collection_time: float
    errors: List[str]

    def get_total_papers(self) -> int:
        """Get total unique papers collected"""
        return len(self.papers)

    def get_source_coverage(self) -> Dict[str, float]:
        """Calculate percentage contribution from each source"""
        total = sum(self.source_counts.values())
        if total == 0:
            return {}
        return {source: count / total for source, count in self.source_counts.items()}


class EnhancedCollectionOrchestrator:
    """Orchestrate multi-source collection with deduplication"""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize orchestrator with API clients

        Args:
            api_keys: Dictionary of API keys for different sources
        """
        # Merge provided API keys with environment variables
        merged_keys = self._load_from_env()
        if api_keys:
            merged_keys.update(api_keys)

        # Initialize API clients
        self.sources = {
            "semantic_scholar": EnhancedSemanticScholarClient(
                api_key=merged_keys.get("semantic_scholar")
            ),
            "openalex": EnhancedOpenAlexClient(email=merged_keys.get("openalex_email")),
            "crossref": EnhancedCrossrefClient(email=merged_keys.get("crossref_email")),
            "google_scholar": GoogleScholarClient(),
        }

        # Initialize rate limiter with API configurations
        self.api_configs = self._create_api_configs()
        self.rate_limiter = RateLimitManager(self.api_configs)

    def _load_from_env(self) -> Dict[str, Any]:
        """Load API configuration from environment variables"""
        env_config = {}

        # Semantic Scholar API key
        if os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
            env_config["semantic_scholar"] = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

        # OpenAlex email for polite pool
        if os.getenv("OPENALEX_EMAIL"):
            env_config["openalex_email"] = os.getenv("OPENALEX_EMAIL")

        # CrossRef email for polite pool
        if os.getenv("CROSSREF_EMAIL"):
            env_config["crossref_email"] = os.getenv("CROSSREF_EMAIL")

        # Google Scholar proxy setting
        if os.getenv("GOOGLE_SCHOLAR_USE_PROXY"):
            env_config["google_scholar_proxy"] = os.getenv(
                "GOOGLE_SCHOLAR_USE_PROXY"
            ).lower() in ("true", "1", "yes")

        logger.info(
            f"Loaded {len(env_config)} API configurations from environment variables"
        )
        return env_config

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

    def collect_from_all_sources(
        self,
        query: CollectionQuery,
        parallel: bool = True,
        sources_to_use: Optional[List[str]] = None,
    ) -> CollectionResult:
        """
        Collect from all sources with optional parallel execution

        Args:
            query: Collection query with search parameters
            parallel: Whether to collect from sources in parallel
            sources_to_use: List of source names to use (defaults to all)

        Returns:
            CollectionResult with all papers and statistics
        """
        start_time = time.time()

        # Determine which sources to use
        active_sources = sources_to_use or list(self.sources.keys())

        # Initialize result tracking
        all_papers = []
        source_counts = {}
        errors = []

        if parallel:
            # Parallel collection using ThreadPoolExecutor
            logger.info(
                f"Starting parallel collection from {len(active_sources)} sources"
            )

            with ThreadPoolExecutor(max_workers=len(active_sources)) as executor:
                # Submit collection tasks
                future_to_source = {
                    executor.submit(
                        self._collect_from_source_with_rate_limit, source_name, query
                    ): source_name
                    for source_name in active_sources
                }

                # Collect results as they complete
                for future in as_completed(future_to_source):
                    source_name = future_to_source[future]
                    try:
                        source_papers = future.result()
                        source_counts[source_name] = len(source_papers)
                        all_papers.extend(source_papers)
                        logger.info(
                            f"Collected {len(source_papers)} papers from {source_name}"
                        )
                    except Exception as e:
                        error_msg = f"{source_name}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"Collection failed for {source_name}: {e}")
                        source_counts[source_name] = 0
        else:
            # Sequential collection
            logger.info(
                f"Starting sequential collection from {len(active_sources)} sources"
            )

            for source_name in active_sources:
                try:
                    source_papers = self._collect_from_source_with_rate_limit(
                        source_name, query
                    )
                    source_counts[source_name] = len(source_papers)
                    all_papers.extend(source_papers)
                    logger.info(
                        f"Collected {len(source_papers)} papers from {source_name}"
                    )
                except Exception as e:
                    error_msg = f"{source_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Collection failed for {source_name}: {e}")
                    source_counts[source_name] = 0

        # Calculate collection time
        collection_time = time.time() - start_time

        # Note: Deduplication will be handled by Agent Gamma's DeduplicationEngine
        # For now, we'll just count papers by source and note that deduplication is pending
        duplicates_removed = 0  # Will be updated after deduplication

        logger.info(
            f"Collection completed in {collection_time:.2f}s. "
            f"Total papers: {len(all_papers)} from {len(active_sources)} sources"
        )

        return CollectionResult(
            papers=all_papers,
            source_counts=source_counts,
            duplicates_removed=duplicates_removed,
            collection_time=collection_time,
            errors=errors,
        )

    def _collect_from_source_with_rate_limit(
        self, source_name: str, query: CollectionQuery
    ) -> List[Paper]:
        """
        Collect from a single source with rate limiting

        Args:
            source_name: Name of the source to collect from
            query: Collection query

        Returns:
            List of papers from the source
        """
        # Wait for rate limit if needed
        wait_time = self.rate_limiter.wait_if_needed(source_name)
        if wait_time > 0:
            logger.debug(f"Rate limit wait for {source_name}: {wait_time:.2f}s")

        # Get the source client
        source_client = self.sources[source_name]

        # Perform collection based on query type
        if query.venue:
            # Single venue search
            response = source_client.search_venue_batch(
                [query.venue], query.year, limit=query.max_results
            )
        else:
            # Domain/keyword based search
            search_query = query.domain
            if query.keywords:
                search_query += " " + " ".join(query.keywords)

            response = source_client.search_papers(
                search_query, query.year, limit=query.max_results
            )

        # Record the request with response time
        response_time_ms = (
            response.metadata.response_time_ms if response.metadata else 1000
        )
        self.rate_limiter.record_request(
            source_name, response.success, response_time_ms
        )

        if response.success:
            return response.papers
        else:
            # Log errors and return empty list
            for error in response.errors:
                logger.error(f"{source_name} error: {error.message}")
            return []

    def collect_with_fallback(
        self, query: CollectionQuery, preferred_sources: List[str]
    ) -> CollectionResult:
        """
        Collect with fallback strategy - try preferred sources first

        Args:
            query: Collection query
            preferred_sources: Ordered list of preferred sources

        Returns:
            CollectionResult from first successful source
        """
        start_time = time.time()
        errors = []

        for source_name in preferred_sources:
            if source_name not in self.sources:
                continue

            try:
                papers = self._collect_from_source_with_rate_limit(source_name, query)

                if papers:
                    # Success! Return results from this source
                    return CollectionResult(
                        papers=papers,
                        source_counts={source_name: len(papers)},
                        duplicates_removed=0,
                        collection_time=time.time() - start_time,
                        errors=errors,
                    )

            except Exception as e:
                error_msg = f"{source_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Fallback failed for {source_name}: {e}")

        # All sources failed
        return CollectionResult(
            papers=[],
            source_counts={},
            duplicates_removed=0,
            collection_time=time.time() - start_time,
            errors=errors,
        )

    def get_source_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each source"""
        stats = {}

        for source_name in self.sources:
            rate_limit_info = self.rate_limiter.get_current_usage(source_name)

            stats[source_name] = {
                "available": source_name in self.sources,
                "rate_limit": {
                    "requests_in_window": rate_limit_info.requests_in_window
                    if rate_limit_info
                    else 0,
                    "window_capacity": rate_limit_info.window_capacity
                    if rate_limit_info
                    else "unknown",
                    "current_delay": rate_limit_info.current_delay_seconds
                    if rate_limit_info
                    else 0.0,
                    "health_multiplier": rate_limit_info.health_multiplier
                    if rate_limit_info
                    else 1.0,
                },
            }

        return stats
