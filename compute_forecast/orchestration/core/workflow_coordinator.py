"""
Workflow Coordinator for managing the end-to-end collection workflow.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ...pipeline.metadata_collection.models import Paper

logger = logging.getLogger(__name__)


@dataclass
class VenueProcessingResult:
    venue: str
    year: int
    success: bool
    papers_collected: int
    papers_after_dedup: int
    processing_time_seconds: float
    errors: List[str]


class WorkflowCoordinator:
    """Coordinates the complete venue collection workflow across all agents"""

    def __init__(self):
        self.current_workflow_id = None
        self.workflow_state = {}

    def execute_venue_collection_workflow(
        self,
        session_id: str,
        venues: List[str],
        years: List[int],
        api_engine,
        state_manager,
        venue_normalizer,
        deduplicator,
        citation_analyzer,
        metrics_collector,
    ) -> Dict[str, Any]:
        """
        Execute complete venue collection workflow

        Workflow Steps:
        1. Create initial checkpoint
        2. For each venue/year combination:
           a. Create venue checkpoint
           b. Collect papers via API
           c. Normalize venue names
           d. Deduplicate papers
           e. Update metrics
           f. Save completion checkpoint
        3. Final analysis and quality validation
        """

        workflow_id = f"workflow_{session_id}_{int(time.time())}"
        self.current_workflow_id = workflow_id

        logger.info(
            f"Starting workflow {workflow_id}: {len(venues)} venues x {len(years)} years"
        )

        workflow_result: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "success": False,
            "venues_attempted": [],
            "venues_completed": [],
            "venues_failed": [],
            "raw_papers_collected": 0,
            "deduplicated_papers": 0,
            "filtered_papers": 0,
            "final_dataset_size": 0,
            "data_quality_score": 0.0,
            "api_efficiency": 0.0,
            "errors": [],
            "venue_results": [],
        }

        workflow_start = time.time()
        all_papers = []

        try:
            # Step 1: Create initial workflow checkpoint
            logger.info("Step 1: Creating initial workflow checkpoint")

            from ..state.state_manager import CheckpointData

            initial_checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="workflow_start",
                timestamp=datetime.now(),
                venues_completed=[],
                venues_in_progress=[],
                venues_not_started=[(v, y) for v in venues for y in years],
                papers_collected=0,
                papers_by_venue={},
                last_successful_operation="workflow_initialization",
                api_health_status={},
                rate_limit_status={},
                checksum="",
            )

            state_manager.save_checkpoint(session_id, initial_checkpoint)

            # Step 2: Process each venue/year combination
            logger.info(
                f"Step 2: Processing {len(venues)} venues across {len(years)} years"
            )

            for venue in venues:
                for year in years:
                    venue_year = (venue, year)
                    workflow_result["venues_attempted"].append(venue_year)

                    logger.info(f"Processing {venue} {year}")

                    # Process venue/year
                    venue_result = self._process_venue_year(
                        venue,
                        year,
                        session_id,
                        api_engine,
                        state_manager,
                        venue_normalizer,
                        deduplicator,
                        metrics_collector,
                    )

                    workflow_result["venue_results"].append(venue_result)

                    if venue_result.success:
                        workflow_result["venues_completed"].append(venue_year)
                        workflow_result["raw_papers_collected"] += (
                            venue_result.papers_collected
                        )
                        workflow_result["deduplicated_papers"] += (
                            venue_result.papers_after_dedup
                        )

                        # Collect papers for final analysis
                        # Note: In real implementation, this would come from the actual collection
                        all_papers.extend(
                            self._create_mock_papers(
                                venue, year, venue_result.papers_collected
                            )
                        )

                    else:
                        workflow_result["venues_failed"].append(venue_year)
                        workflow_result["errors"].extend(venue_result.errors)

            # Step 3: Final analysis and quality validation
            logger.info("Step 3: Final analysis and quality validation")

            if all_papers:
                # Citation analysis
                citation_report = citation_analyzer.analyze_citation_distributions(
                    all_papers
                )

                # Final deduplication across all papers
                final_dedup_result = deduplicator.deduplicate_papers(all_papers)
                workflow_result["final_dataset_size"] = (
                    final_dedup_result.deduplicated_count
                )

                # Data quality score calculation
                workflow_result["data_quality_score"] = (
                    self._calculate_data_quality_score(
                        workflow_result, citation_report, final_dedup_result
                    )
                )

                # API efficiency calculation (simplified)
                total_venue_years = len(venues) * len(years)
                theoretical_api_calls = (
                    total_venue_years * 10
                )  # Assume 10 calls per venue/year normally
                actual_api_calls = (
                    total_venue_years * 3
                )  # Assume batching reduces to 3 calls
                workflow_result["api_efficiency"] = 1.0 - (
                    actual_api_calls / theoretical_api_calls
                )

            # Final checkpoint
            final_checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="workflow_complete",
                timestamp=datetime.now(),
                venues_completed=list(workflow_result["venues_completed"]),
                venues_in_progress=[],
                venues_not_started=[],
                papers_collected=int(workflow_result["raw_papers_collected"]),
                papers_by_venue={
                    v: {y: 100 for y in years} for v in venues
                },  # Simplified
                last_successful_operation="workflow_completion",
                api_health_status={},
                rate_limit_status={},
                checksum="",
            )

            state_manager.save_checkpoint(session_id, final_checkpoint)

            # Determine overall success
            workflow_result["success"] = (
                len(workflow_result["venues_completed"]) > 0
                and len(workflow_result["venues_failed"]) == 0
                and workflow_result["raw_papers_collected"] > 0
            )

            workflow_duration = time.time() - workflow_start
            logger.info(
                f"Workflow {workflow_id} completed in {workflow_duration:.1f}s: "
                f"{workflow_result['raw_papers_collected']} papers collected"
            )

        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            workflow_result["errors"].append(error_msg)
            logger.error(error_msg)

        return workflow_result

    def _process_venue_year(
        self,
        venue: str,
        year: int,
        session_id: str,
        api_engine,
        state_manager,
        venue_normalizer,
        deduplicator,
        metrics_collector,
    ) -> VenueProcessingResult:
        """Process a single venue/year combination through the complete pipeline"""

        process_start = time.time()

        result = VenueProcessingResult(
            venue=venue,
            year=year,
            success=False,
            papers_collected=0,
            papers_after_dedup=0,
            processing_time_seconds=0.0,
            errors=[],
        )

        try:
            # Step 1: Create venue checkpoint
            from ..state.state_manager import CheckpointData

            venue_checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="venue_start",
                timestamp=datetime.now(),
                venues_completed=[],
                venues_in_progress=[(venue, year)],
                venues_not_started=[],
                papers_collected=0,
                papers_by_venue={venue: {year: 0}},
                last_successful_operation=f"venue_{venue}_{year}_start",
                api_health_status={},
                rate_limit_status={},
                checksum="",
            )

            state_manager.save_checkpoint(session_id, venue_checkpoint)

            # Step 2: Collect papers (simplified - using mock data)
            papers_collected = self._mock_paper_collection(venue, year)
            result.papers_collected = len(papers_collected)

            if result.papers_collected == 0:
                result.errors.append(f"No papers collected for {venue} {year}")
                return result

            # Step 3: Normalize venue names
            normalized_papers = []
            for paper in papers_collected:
                try:
                    normalized_venue = venue_normalizer.normalize_venue(paper.venue)
                    if normalized_venue:
                        paper.normalized_venue = normalized_venue.get(
                            "normalized_name", paper.venue
                        )
                    normalized_papers.append(paper)
                except Exception as e:
                    result.errors.append(
                        f"Venue normalization failed for paper {paper.title}: {str(e)}"
                    )
                    normalized_papers.append(paper)  # Keep original

            # Step 4: Deduplicate papers
            dedup_result = deduplicator.deduplicate_papers(normalized_papers)
            result.papers_after_dedup = dedup_result.deduplicated_count

            # Step 5: Update metrics
            venue_metrics = {
                "session_id": session_id,
                "venue": venue,
                "year": year,
                "papers_collected": result.papers_collected,
                "papers_after_dedup": result.papers_after_dedup,
                "processing_time": time.time() - process_start,
            }

            metrics_collector.record_venue_completion(venue_metrics)

            # Step 6: Save completion checkpoint
            completion_checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="venue_complete",
                timestamp=datetime.now(),
                venues_completed=[(venue, year)],
                venues_in_progress=[],
                venues_not_started=[],
                papers_collected=result.papers_collected,
                papers_by_venue={venue: {year: result.papers_collected}},
                last_successful_operation=f"venue_{venue}_{year}_complete",
                api_health_status={},
                rate_limit_status={},
                checksum="",
            )

            state_manager.save_checkpoint(session_id, completion_checkpoint)

            result.success = True

        except Exception as e:
            result.errors.append(f"Venue processing failed: {str(e)}")

        finally:
            result.processing_time_seconds = time.time() - process_start

        return result

    def _mock_paper_collection(self, venue: str, year: int) -> List[Paper]:
        """Mock paper collection for testing (replace with real API calls)"""

        # Return mock papers based on venue characteristics
        mock_count = {
            "NeurIPS": 200,
            "ICML": 180,
            "ICLR": 150,
            "AAAI": 120,
            "CVPR": 220,
            "ICCV": 200,
            "EMNLP": 140,
            "ACL": 130,
        }.get(venue, 50)

        return self._create_mock_papers(venue, year, mock_count)

    def _create_mock_papers(self, venue: str, year: int, count: int) -> List[Paper]:
        """Create mock papers for testing"""
        from ...pipeline.metadata_collection.models import Author

        papers = []
        for i in range(count):
            paper = Paper(
                title=f"{venue} Paper {i + 1} {year}",
                authors=[Author(name=f"Author {i + 1}", affiliations=["Test University"])],
                venue=venue,
                year=year,
                citations=max(0, 50 - i),  # Decreasing citations
                abstract=f"Abstract for {venue} paper {i + 1} from {year}",
                collection_source="mock_api",
            )
            papers.append(paper)

        return papers

    def _calculate_data_quality_score(
        self, workflow_result: Dict[str, Any], citation_report, dedup_result
    ) -> float:
        """Calculate overall data quality score for the workflow"""

        # Component scores
        collection_completeness = (
            len(workflow_result["venues_completed"])
            / len(workflow_result["venues_attempted"])
            if workflow_result["venues_attempted"]
            else 0
        )

        deduplication_quality = min(
            1.0, dedup_result.deduplicated_count / dedup_result.original_count
        )

        citation_quality = 1.0  # Simplified - assume citations are valid

        venue_normalization_quality = 0.95  # Simplified assumption

        # Weighted average
        quality_score = (
            collection_completeness * 0.3
            + deduplication_quality * 0.25
            + citation_quality * 0.25
            + venue_normalization_quality * 0.2
        )

        return float(quality_score)

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of workflow"""
        if workflow_id == self.current_workflow_id:
            return dict(self.workflow_state.get(workflow_id, {}))

        return None

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel running workflow"""
        if workflow_id == self.current_workflow_id:
            logger.info(f"Cancelling workflow {workflow_id}")
            # In real implementation, this would stop all running operations
            return True

        return False
