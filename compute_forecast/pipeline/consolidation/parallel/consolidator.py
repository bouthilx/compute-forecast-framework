"""Parallel consolidator that orchestrates multiple workers."""

import queue
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.parallel.openalex_worker import (
    OpenAlexWorker,
)
from compute_forecast.pipeline.consolidation.parallel.semantic_scholar_worker import (
    SemanticScholarWorker,
)
from compute_forecast.pipeline.consolidation.parallel.merge_worker import MergeWorker
from compute_forecast.pipeline.consolidation.checkpoint_manager import (
    ConsolidationCheckpointManager,
)
from compute_forecast.pipeline.consolidation.models_extended import (
    ConsolidationPhaseState,
)

logger = logging.getLogger(__name__)


class ParallelConsolidator:
    """Orchestrates parallel consolidation with multiple workers."""

    def __init__(
        self,
        openalex_email: Optional[str] = None,
        ss_api_key: Optional[str] = None,
        openalex_batch_size: int = 50,
        ss_batch_size: int = 500,
        checkpoint_manager: Optional[ConsolidationCheckpointManager] = None,
        checkpoint_interval: int = 300,  # 5 minutes
    ):
        self.openalex_email = openalex_email
        self.ss_api_key = ss_api_key
        self.openalex_batch_size = openalex_batch_size
        self.ss_batch_size = ss_batch_size
        self.checkpoint_manager = checkpoint_manager
        self.checkpoint_interval = checkpoint_interval

        # Queues - separate input queues for each worker
        self.openalex_input_queue = queue.Queue()
        self.ss_input_queue = queue.Queue()
        self.enrichment_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()

        # Workers
        self.openalex_worker = None
        self.semantic_scholar_worker = None
        self.merge_worker = None

        # Progress callbacks
        self.openalex_progress_callback = None
        self.ss_progress_callback = None

        # State
        self.openalex_processed_hashes = set()
        self.ss_processed_hashes = set()
        self.start_time = None

    def set_progress_callbacks(
        self,
        openalex_callback: Callable[[int], None],
        ss_callback: Callable[[int], None],
    ):
        """Set progress callbacks for workers."""
        self.openalex_progress_callback = openalex_callback
        self.ss_progress_callback = ss_callback

    def load_checkpoint(self, phase_state: ConsolidationPhaseState) -> List[Paper]:
        """Load state from checkpoint."""
        # Extract processed hashes for each source
        if hasattr(phase_state, "openalex_processed_hashes"):
            self.openalex_processed_hashes = phase_state.openalex_processed_hashes
        if hasattr(phase_state, "semantic_scholar_processed_hashes"):
            self.ss_processed_hashes = phase_state.semantic_scholar_processed_hashes

        # Return any merged papers from checkpoint
        return getattr(phase_state, "merged_papers", [])

    def process_papers(
        self,
        papers: List[Paper],
        progress_update_callback: Optional[Callable[[str, int], None]] = None,
        input_file: str = "",
        checkpoint_papers: Optional[List[Paper]] = None,
        checkpoint_stats: Optional[Dict[str, Any]] = None,
    ) -> List[Paper]:
        """
        Process papers through parallel consolidation.

        Args:
            papers: List of papers to process
            progress_update_callback: Optional callback(source, count) to update progress
        """
        self.start_time = time.time()
        logger.info(f"Starting parallel consolidation for {len(papers)} papers")

        # Store checkpoint info
        self.input_file = input_file
        self.checkpoint_papers = checkpoint_papers or papers
        self.total_papers = len(papers)

        # Initialize checkpoint manager's input file if present
        if self.checkpoint_manager:
            self.checkpoint_manager.input_file = input_file

        # Initialize workers with separate input queues
        self.openalex_worker = OpenAlexWorker(
            input_queue=self.openalex_input_queue,
            output_queue=self.enrichment_queue,
            error_queue=self.error_queue,
            openalex_email=self.openalex_email,
            progress_callback=None,  # No callback - main thread monitors
            batch_size=1,  # Process one at a time
            processed_hashes=self.openalex_processed_hashes,
        )

        self.semantic_scholar_worker = SemanticScholarWorker(
            input_queue=self.ss_input_queue,
            output_queue=self.enrichment_queue,
            error_queue=self.error_queue,
            ss_api_key=self.ss_api_key,
            progress_callback=None,  # No callback - main thread monitors
            batch_size=1,  # Process one at a time
            processed_hashes=self.ss_processed_hashes,
        )

        # If we have checkpoint stats, initialize worker counters
        if checkpoint_stats:
            oa_stats = checkpoint_stats.get("openalex", {})
            ss_stats = checkpoint_stats.get("semantic_scholar", {})

            self.openalex_worker.papers_processed = oa_stats.get("papers_processed", 0)
            self.openalex_worker.papers_enriched = oa_stats.get("papers_enriched", 0)
            self.openalex_worker.citations_found = oa_stats.get("citations_found", 0)
            self.openalex_worker.abstracts_found = oa_stats.get("abstracts_found", 0)
            self.openalex_worker.api_calls = oa_stats.get("api_calls", 0)

            self.semantic_scholar_worker.papers_processed = ss_stats.get(
                "papers_processed", 0
            )
            self.semantic_scholar_worker.papers_enriched = ss_stats.get(
                "papers_enriched", 0
            )
            self.semantic_scholar_worker.citations_found = ss_stats.get(
                "citations_found", 0
            )
            self.semantic_scholar_worker.abstracts_found = ss_stats.get(
                "abstracts_found", 0
            )
            self.semantic_scholar_worker.api_calls = ss_stats.get("api_calls", 0)

        self.merge_worker = MergeWorker(
            input_queue=self.enrichment_queue,
            output_queue=self.output_queue,
            error_queue=self.error_queue,
            checkpoint_callback=self._checkpoint if self.checkpoint_manager else None,
            checkpoint_interval=self.checkpoint_interval,
        )

        # Start workers
        self.openalex_worker.start()
        self.semantic_scholar_worker.start()
        self.merge_worker.start()

        # Feed papers to separate input queues
        logger.debug(f"Adding {len(papers)} papers to each worker's input queue")
        for i, paper in enumerate(papers):
            # Add paper to both queues
            logger.debug(f"Adding paper {i + 1}/{len(papers)}: {paper.title[:50]}...")
            self.openalex_input_queue.put(paper)
            self.ss_input_queue.put(paper)
        logger.debug(
            f"All papers added. OpenAlex queue size: {self.openalex_input_queue.qsize()}, SS queue size: {self.ss_input_queue.qsize()}"
        )

        # Monitor progress and wait for completion
        self._monitor_progress(len(papers), progress_update_callback)

        # Stop workers
        self.openalex_worker.stop()
        self.semantic_scholar_worker.stop()
        self.merge_worker.stop()

        # Wait for workers to finish
        self.openalex_worker.join(timeout=5)
        self.semantic_scholar_worker.join(timeout=5)
        self.merge_worker.join(timeout=5)

        # Get final results
        merged_papers = self.merge_worker.get_merged_papers()

        # Final checkpoint
        if self.checkpoint_manager:
            self._checkpoint(force=True)

        # Report statistics
        duration = time.time() - self.start_time
        logger.info(
            f"Parallel consolidation complete. "
            f"Papers: {len(merged_papers)}, Duration: {duration:.1f}s"
        )

        self._report_statistics()

        return merged_papers

    def _monitor_progress(
        self,
        total_papers: int,
        progress_callback: Optional[Callable[[str, int, int, int], None]],
    ):
        """Monitor progress by watching enrichment queue."""
        expected_enrichments = total_papers * 2  # Each paper processed by 2 workers

        # Track progress per source
        source_progress = {"openalex": 0, "semantic_scholar": 0}

        last_progress_update = time.time()

        while self.merge_worker.papers_merged < expected_enrichments:
            # Check enrichment queue for results
            try:
                # Non-blocking check of enrichment queue size
                # We can't peek, but we can track what merge worker has processed

                # Update progress based on what sources have completed
                # This is approximate since we can't peek into the queue
                if (
                    progress_callback and time.time() - last_progress_update > 0.1
                ):  # Update every 100ms
                    # Get actual counts from workers
                    oa_processed = self.openalex_worker.papers_processed
                    ss_processed = self.semantic_scholar_worker.papers_processed

                    # Update progress if changed
                    if oa_processed > source_progress["openalex"]:
                        progress_callback(
                            "openalex",
                            oa_processed - source_progress["openalex"],
                            self.openalex_worker.citations_found,
                            self.openalex_worker.abstracts_found,
                        )
                        source_progress["openalex"] = oa_processed

                    if ss_processed > source_progress["semantic_scholar"]:
                        progress_callback(
                            "semantic_scholar",
                            ss_processed - source_progress["semantic_scholar"],
                            self.semantic_scholar_worker.citations_found,
                            self.semantic_scholar_worker.abstracts_found,
                        )
                        source_progress["semantic_scholar"] = ss_processed

                    last_progress_update = time.time()

            except Exception as e:
                logger.error(f"Progress monitoring error: {e}")

            # Check for errors
            if not self.error_queue.empty():
                errors = []
                while not self.error_queue.empty():
                    errors.append(self.error_queue.get())
                logger.error(f"Worker errors: {errors}")

            # Brief sleep to avoid busy waiting
            time.sleep(0.05)  # 50ms

    def _checkpoint(self, force: bool = False):
        """Save checkpoint."""
        if not self.checkpoint_manager:
            return

        if not force and not self.checkpoint_manager.should_checkpoint():
            return

        # Get merged papers to count actual enriched papers
        merged_papers = self.merge_worker.get_merged_papers()

        # Count papers that actually have data from each source
        openalex_enriched = 0
        ss_enriched = 0

        for paper in merged_papers:
            # Check if paper has OpenAlex data
            if paper.openalex_id or any(
                r.source == "openalex" for r in getattr(paper, "citations", [])
            ):
                openalex_enriched += 1

            # Check if paper has Semantic Scholar data
            # Check external_ids for semantic_scholar ID
            if hasattr(paper, "external_ids") and paper.external_ids.get(
                "semantic_scholar"
            ):
                ss_enriched += 1
            elif any(
                r.source == "semanticscholar" for r in getattr(paper, "citations", [])
            ):
                ss_enriched += 1

        # Build phase state
        phase_state = ConsolidationPhaseState(
            phase="parallel_consolidation",
            phase_completed=False,
            phase_start_time=datetime.fromtimestamp(self.start_time),
            # Source-specific processed hashes
            openalex_processed_hashes=self.openalex_worker.processed_hashes,
            semantic_scholar_processed_hashes=self.semantic_scholar_worker.processed_hashes,
            # Merged papers
            merged_papers=merged_papers,
            # Statistics
            papers_processed=self.openalex_worker.papers_processed
            + self.semantic_scholar_worker.papers_processed,
            papers_enriched=self.merge_worker.papers_merged,
        )

        self.checkpoint_manager.save_checkpoint(
            input_file=self.input_file,
            total_papers=self.total_papers,
            sources_state={
                "openalex": {
                    "papers_processed": self.openalex_worker.papers_processed,
                    "papers_enriched": openalex_enriched,  # Use actual count
                    "api_calls": self.openalex_worker.api_calls,
                    "citations_found": self.openalex_worker.citations_found,
                    "abstracts_found": self.openalex_worker.abstracts_found,
                },
                "semantic_scholar": {
                    "papers_processed": self.semantic_scholar_worker.papers_processed,
                    "papers_enriched": ss_enriched,  # Use actual count
                    "api_calls": self.semantic_scholar_worker.api_calls,
                    "citations_found": self.semantic_scholar_worker.citations_found,
                    "abstracts_found": self.semantic_scholar_worker.abstracts_found,
                },
                "merge": self.merge_worker.get_state(),
            },
            papers=self.checkpoint_papers,
            phase_state=phase_state.to_dict(),
            force=force,
        )

    def _report_statistics(self):
        """Report consolidation statistics."""
        stats = {
            "OpenAlex": {
                "papers_processed": self.openalex_worker.papers_processed,
                "papers_enriched": self.openalex_worker.papers_enriched,
                "api_calls": self.openalex_worker.api_calls,
            },
            "Semantic Scholar": {
                "papers_processed": self.semantic_scholar_worker.papers_processed,
                "papers_enriched": self.semantic_scholar_worker.papers_enriched,
                "api_calls": self.semantic_scholar_worker.api_calls,
            },
            "Merge": {
                "papers_merged": self.merge_worker.papers_merged,
                "unique_papers": len(self.merge_worker.get_merged_papers()),
            },
        }

        logger.info("Consolidation statistics:")
        for source, source_stats in stats.items():
            logger.info(f"  {source}:")
            for key, value in source_stats.items():
                logger.info(f"    {key}: {value}")
