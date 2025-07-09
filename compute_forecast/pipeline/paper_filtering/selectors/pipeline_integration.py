"""
Pipeline Integration for Computational Filtering (Issue #8).
Integrates the filtering system with the existing data collection pipeline.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
import time

from ...metadata_collection.models import Paper
from .computational_filter import (
    ComputationalResearchFilter,
    FilteringConfig,
    FilteringResult,
)

logger = logging.getLogger(__name__)


class FilteringPipelineIntegration:
    """
    Integrates computational filtering into the paper collection pipeline.
    Provides real-time filtering with minimal latency impact.
    """

    def __init__(
        self, filter_config: Optional[FilteringConfig] = None, num_workers: int = 4
    ):
        self.filter = ComputationalResearchFilter(filter_config)
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)

        # Performance tracking
        self.performance_lock = Lock()
        self.performance_stats = {
            "total_papers": 0,
            "filtered_papers": 0,
            "avg_filter_time_ms": 0.0,
            "total_filter_time_ms": 0.0,
            "papers_per_second": 0.0,
        }
        self.start_time = time.time()

        # Callbacks for pipeline integration
        self.on_paper_passed: Optional[Callable[[FilteringResult], None]] = None
        self.on_paper_filtered: Optional[Callable[[FilteringResult], None]] = None
        self.on_batch_complete: Optional[Callable[[List[FilteringResult]], None]] = None

        logger.info(
            f"FilteringPipelineIntegration initialized with {num_workers} workers"
        )

    def filter_papers_realtime(self, papers: List[Paper]) -> List[Paper]:
        """
        Filter papers in real-time for the collection pipeline.

        This is the main integration point for the collection system.
        Returns only papers that pass the computational research criteria.

        Args:
            papers: List of papers to filter

        Returns:
            List of papers that passed filtering
        """
        start_time = time.time()

        # Submit filtering tasks to thread pool
        futures: List[Future] = []
        for paper in papers:
            future = self.executor.submit(self._filter_single_paper, paper)
            futures.append(future)

        # Collect results
        passed_papers = []
        all_results = []

        for future in futures:
            try:
                result = future.result(timeout=5.0)  # 5 second timeout per paper
                all_results.append(result)

                if result.passed:
                    passed_papers.append(result.paper)
                    if self.on_paper_passed:
                        self.on_paper_passed(result)
                else:
                    if self.on_paper_filtered:
                        self.on_paper_filtered(result)

            except Exception as e:
                logger.error(f"Error filtering paper: {e}")

        # Update performance stats
        filter_time_ms = (time.time() - start_time) * 1000
        self._update_performance_stats(len(papers), len(passed_papers), filter_time_ms)

        # Trigger batch complete callback
        if self.on_batch_complete:
            self.on_batch_complete(all_results)

        logger.debug(
            f"Filtered {len(papers)} papers in {filter_time_ms:.1f}ms, "
            f"{len(passed_papers)} passed"
        )

        return passed_papers

    def _filter_single_paper(self, paper: Paper) -> FilteringResult:
        """Filter a single paper with error handling."""
        try:
            return self.filter.filter_paper(paper)
        except Exception as e:
            logger.error(f"Error filtering paper '{paper.title}': {e}")
            # Return a failed result
            return FilteringResult(
                paper=paper,
                passed=False,
                score=0.0,
                computational_analysis=None,
                authorship_analysis=None,
                venue_analysis=None,
                reasons=[f"Filtering error: {str(e)}"],
                confidence=0.0,
            )

    def _update_performance_stats(
        self, papers_processed: int, papers_passed: int, filter_time_ms: float
    ) -> None:
        """Update performance statistics thread-safely."""
        with self.performance_lock:
            self.performance_stats["total_papers"] += papers_processed
            self.performance_stats["filtered_papers"] += (
                papers_processed - papers_passed
            )
            self.performance_stats["total_filter_time_ms"] += filter_time_ms

            # Calculate averages
            if self.performance_stats["total_papers"] > 0:
                self.performance_stats["avg_filter_time_ms"] = (
                    self.performance_stats["total_filter_time_ms"]
                    / self.performance_stats["total_papers"]
                )

                elapsed_seconds = time.time() - self.start_time
                if elapsed_seconds > 0:
                    self.performance_stats["papers_per_second"] = (
                        self.performance_stats["total_papers"] / elapsed_seconds
                    )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        with self.performance_lock:
            stats = self.performance_stats.copy()

        # Add filter statistics
        stats.update(self.filter.get_statistics())

        return stats

    def update_filter_config(self, new_config: FilteringConfig) -> None:
        """Update filtering configuration on the fly."""
        self.filter.update_config(new_config)
        logger.info("Filter configuration updated in pipeline")

    def create_api_integration(self, api_layer):
        """
        Create integration with API integration layer.

        This method should be called by the API integration layer to set up
        the filtering pipeline.

        Args:
            api_layer: The API integration layer instance
        """
        # Import here to avoid circular dependency
        from ...metadata_collection.collectors.api_integration_layer import (
            APIIntegrationLayer,
        )

        if not isinstance(api_layer, APIIntegrationLayer):
            raise ValueError("Invalid API integration layer instance")

        # Create a wrapper for the API layer's paper processing
        original_process = api_layer._process_paper_batch

        def filtered_process(papers: List[Paper]) -> List[Paper]:
            """Wrapper that adds filtering to paper processing."""
            # Apply computational filtering
            filtered_papers = self.filter_papers_realtime(papers)

            # Continue with original processing on filtered papers
            result = original_process(filtered_papers)
            return list(result) if result else []

        # Replace the processing method
        api_layer._process_paper_batch = filtered_process

        logger.info("Computational filtering integrated with API layer")

    def create_monitoring_integration(self, monitoring_system):
        """
        Create integration with monitoring system.

        Sends filtering metrics to the monitoring dashboard.
        """

        def send_metrics():
            """Send current metrics to monitoring system."""
            stats = self.get_performance_stats()

            # Format metrics for monitoring
            metrics = {
                "filtering.total_papers": stats["total_papers"],
                "filtering.passed_papers": stats["total_passed"],
                "filtering.pass_rate": stats["pass_rate"],
                "filtering.avg_time_ms": stats["avg_filter_time_ms"],
                "filtering.papers_per_second": stats["papers_per_second"],
                "filtering.computational_filtered": stats["computational_filtered"],
                "filtering.authorship_filtered": stats["authorship_filtered"],
                "filtering.venue_filtered": stats["venue_filtered"],
            }

            # Send to monitoring system
            if hasattr(monitoring_system, "record_metrics"):
                monitoring_system.record_metrics(metrics)

        # Set up periodic metric reporting
        if hasattr(monitoring_system, "add_metric_collector"):
            monitoring_system.add_metric_collector(
                "computational_filtering", send_metrics, interval=30
            )

        logger.info("Computational filtering integrated with monitoring system")

    def shutdown(self) -> None:
        """Shutdown the filtering pipeline."""
        self.executor.shutdown(wait=True)
        logger.info("Filtering pipeline shut down")


# Convenience function for easy integration
def setup_computational_filtering(
    api_layer, monitoring_system=None, filter_config: Optional[FilteringConfig] = None
) -> FilteringPipelineIntegration:
    """
    Set up computational filtering for the paper collection pipeline.

    Args:
        api_layer: API integration layer instance
        monitoring_system: Optional monitoring system for metrics
        filter_config: Optional filtering configuration

    Returns:
        Configured FilteringPipelineIntegration instance
    """
    # Create pipeline integration
    pipeline = FilteringPipelineIntegration(filter_config)

    # Integrate with API layer
    pipeline.create_api_integration(api_layer)

    # Integrate with monitoring if provided
    if monitoring_system:
        pipeline.create_monitoring_integration(monitoring_system)

    logger.info("Computational filtering fully integrated with collection pipeline")

    return pipeline
