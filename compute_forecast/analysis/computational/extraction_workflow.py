"""
Integration workflow between automated and manual extraction processes.

This module orchestrates the complete extraction process, combining automated
analysis with manual validation and quality control for optimal results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from pathlib import Path

from .analyzer import ComputationalAnalyzer
from .extraction_protocol import ExtractionProtocol, ExtractionResult
from .quality_control import QualityController, QualityReport
from .extraction_forms import FormManager
from .extraction_patterns import PatternMatcher, PatternType

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Stages in the extraction workflow."""

    INITIALIZATION = "initialization"
    AUTOMATED_ANALYSIS = "automated_analysis"
    PATTERN_MATCHING = "pattern_matching"
    MANUAL_EXTRACTION = "manual_extraction"
    QUALITY_VALIDATION = "quality_validation"
    FORM_GENERATION = "form_generation"
    REVIEW_PREPARATION = "review_preparation"
    COMPLETED = "completed"


class WorkflowStatus(Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class WorkflowConfig:
    """Configuration for extraction workflow."""

    # Automated analysis settings
    automated_confidence_threshold: float = 0.7
    skip_manual_if_high_confidence: bool = False

    # Quality control settings
    quality_threshold: float = 0.8
    require_quality_validation: bool = True

    # Pattern matching settings
    enable_pattern_matching: bool = True
    pattern_confidence_boost: float = 0.1

    # Manual extraction settings
    manual_extraction_timeout_minutes: int = 60
    require_manual_validation: bool = True

    # Output settings
    generate_forms: bool = True
    save_intermediate_results: bool = True
    output_directory: Optional[Path] = None


@dataclass
class WorkflowStep:
    """Represents a single step in the workflow."""

    stage: WorkflowStage
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    result: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Complete result of the extraction workflow."""

    workflow_id: str
    paper_id: str
    analyst: str
    config: WorkflowConfig
    steps: List[WorkflowStep] = field(default_factory=list)
    extraction_result: Optional[ExtractionResult] = None
    quality_report: Optional[QualityReport] = None
    form_data: Optional[Dict[str, Any]] = None
    overall_status: WorkflowStatus = WorkflowStatus.PENDING
    total_duration_seconds: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class ExtractionWorkflowOrchestrator:
    """Orchestrates the complete extraction workflow."""

    def __init__(self, config: Optional[WorkflowConfig] = None):
        """Initialize workflow orchestrator."""
        self.config = config or WorkflowConfig()

        # Initialize components
        self.analyzer = ComputationalAnalyzer()
        self.quality_controller = QualityController()
        self.form_manager = FormManager()
        self.pattern_matcher = PatternMatcher()

        # Workflow tracking
        self.active_workflows: Dict[str, WorkflowResult] = {}

        logger.info("Extraction workflow orchestrator initialized")

    def run_extraction_workflow(
        self,
        paper_content: str,
        paper_id: str,
        analyst: str,
        paper_metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Run the complete extraction workflow."""
        workflow_id = f"{paper_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting extraction workflow {workflow_id} for paper {paper_id}")

        # Initialize workflow result
        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            paper_id=paper_id,
            analyst=analyst,
            config=self.config,
        )

        self.active_workflows[workflow_id] = workflow_result
        start_time = datetime.now()

        try:
            # Stage 1: Initialization
            self._run_stage_initialization(
                workflow_result, paper_content, paper_metadata
            )

            # Stage 2: Automated Analysis
            self._run_stage_automated_analysis(workflow_result, paper_content)

            # Stage 3: Pattern Matching
            if self.config.enable_pattern_matching:
                self._run_stage_pattern_matching(workflow_result, paper_content)

            # Stage 4: Manual Extraction (conditional)
            if self._should_run_manual_extraction(workflow_result):
                self._run_stage_manual_extraction(workflow_result, paper_content)

            # Stage 5: Quality Validation
            if self.config.require_quality_validation:
                self._run_stage_quality_validation(workflow_result)

            # Stage 6: Form Generation
            if self.config.generate_forms:
                self._run_stage_form_generation(workflow_result)

            # Stage 7: Review Preparation
            self._run_stage_review_preparation(workflow_result)

            # Finalize workflow
            workflow_result.overall_status = WorkflowStatus.COMPLETED
            workflow_result.total_duration_seconds = (
                datetime.now() - start_time
            ).total_seconds()

            logger.info(
                f"Workflow {workflow_id} completed successfully in {workflow_result.total_duration_seconds:.1f}s"
            )

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {str(e)}")
            workflow_result.overall_status = WorkflowStatus.FAILED
            workflow_result.total_duration_seconds = (
                datetime.now() - start_time
            ).total_seconds()

            # Add error to final step
            if workflow_result.steps:
                workflow_result.steps[-1].errors.append(str(e))

        return workflow_result

    def _run_stage_initialization(
        self,
        workflow_result: WorkflowResult,
        paper_content: str,
        paper_metadata: Optional[Dict[str, Any]],
    ):
        """Run initialization stage."""
        step = WorkflowStep(
            stage=WorkflowStage.INITIALIZATION,
            name="workflow_initialization",
            description="Initialize extraction workflow and validate inputs",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            # Validate inputs
            if not paper_content.strip():
                raise ValueError("Paper content is empty")

            if len(paper_content) < 100:
                step.warnings.append("Paper content seems very short")

            # Extract basic metadata
            initialization_data = {
                "content_length": len(paper_content),
                "word_count": len(paper_content.split()),
                "metadata": paper_metadata or {},
            }

            step.result = initialization_data
            step.status = WorkflowStatus.COMPLETED

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            raise

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_automated_analysis(
        self, workflow_result: WorkflowResult, paper_content: str
    ):
        """Run automated analysis stage."""
        step = WorkflowStep(
            stage=WorkflowStage.AUTOMATED_ANALYSIS,
            name="automated_computational_analysis",
            description="Run automated computational content analysis",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            # Run automated analysis
            analysis_result = self.analyzer.analyze(paper_content)

            # Create extraction protocol and run automated phase
            protocol = ExtractionProtocol(
                paper_content, workflow_result.paper_id, workflow_result.analyst
            )
            automated_results = protocol.phase2_automated_extraction(self.analyzer)

            step.result = {
                "analysis_result": analysis_result,
                "automated_extraction": automated_results,
                "confidence_score": automated_results.get("confidence_score", 0.0),
            }

            # Store extraction result
            workflow_result.extraction_result = protocol.extraction_result

            step.status = WorkflowStatus.COMPLETED

            # Add warnings for low confidence
            confidence = automated_results.get("confidence_score", 0.0)
            if confidence < self.config.automated_confidence_threshold:
                step.warnings.append(f"Low automated confidence: {confidence:.2f}")

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            raise

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_pattern_matching(
        self, workflow_result: WorkflowResult, paper_content: str
    ):
        """Run pattern matching stage."""
        step = WorkflowStep(
            stage=WorkflowStage.PATTERN_MATCHING,
            name="pattern_matching_analysis",
            description="Identify and extract using common patterns",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            # Identify patterns
            pattern_types = self.pattern_matcher.identify_pattern_type(paper_content)

            # Extract using patterns
            pattern_results = self.pattern_matcher.extract_all_patterns(paper_content)

            # Merge pattern results with existing extraction
            if workflow_result.extraction_result:
                self._merge_pattern_results(
                    workflow_result.extraction_result, pattern_results
                )

            step.result = {
                "identified_patterns": [p.value for p in pattern_types],
                "pattern_extractions": pattern_results,
            }

            step.status = WorkflowStatus.COMPLETED

            # Add info about patterns found
            if pattern_types:
                step.warnings.append(f"Found {len(pattern_types)} extraction patterns")

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            # Don't raise - pattern matching is optional
            logger.warning(f"Pattern matching failed: {str(e)}")

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_manual_extraction(
        self, workflow_result: WorkflowResult, paper_content: str
    ):
        """Run manual extraction stage."""
        step = WorkflowStep(
            stage=WorkflowStage.MANUAL_EXTRACTION,
            name="manual_computational_extraction",
            description="Perform manual extraction to fill gaps and validate automated results",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            # Get extraction protocol
            if not workflow_result.extraction_result:
                protocol = ExtractionProtocol(
                    paper_content, workflow_result.paper_id, workflow_result.analyst
                )
                workflow_result.extraction_result = protocol.extraction_result
            else:
                # Create protocol from existing result
                protocol = ExtractionProtocol(
                    paper_content, workflow_result.paper_id, workflow_result.analyst
                )
                protocol.extraction_result = workflow_result.extraction_result

            # Run manual extraction phases
            prep_results = protocol.phase1_preparation()
            manual_results = protocol.phase3_manual_extraction()
            validation_results = protocol.phase4_validation()
            doc_results = protocol.phase5_documentation()

            step.result = {
                "preparation": prep_results,
                "manual_extraction": manual_results,
                "validation": validation_results,
                "documentation": doc_results,
            }

            # Update workflow extraction result
            workflow_result.extraction_result = protocol.extraction_result

            step.status = WorkflowStatus.COMPLETED

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            raise

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_quality_validation(self, workflow_result: WorkflowResult):
        """Run quality validation stage."""
        step = WorkflowStep(
            stage=WorkflowStage.QUALITY_VALIDATION,
            name="quality_control_validation",
            description="Run comprehensive quality checks on extraction results",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            if not workflow_result.extraction_result:
                raise ValueError(
                    "No extraction result available for quality validation"
                )

            # Run quality checks
            quality_report = self.quality_controller.run_quality_checks(
                workflow_result.extraction_result
            )

            workflow_result.quality_report = quality_report

            step.result = {
                "overall_score": quality_report.overall_score,
                "critical_issues": len(quality_report.critical_issues),
                "warnings": len(quality_report.warnings),
                "recommendations": quality_report.recommendations,
            }

            # Check if quality meets threshold
            if quality_report.overall_score < self.config.quality_threshold:
                workflow_result.overall_status = WorkflowStatus.REQUIRES_REVIEW
                step.warnings.append(
                    f"Quality score {quality_report.overall_score:.2f} below threshold {self.config.quality_threshold}"
                )

            # Add critical issues as errors
            for issue in quality_report.critical_issues:
                step.errors.append(f"{issue.field}: {issue.message}")

            step.status = WorkflowStatus.COMPLETED

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            raise

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_form_generation(self, workflow_result: WorkflowResult):
        """Run form generation stage."""
        step = WorkflowStep(
            stage=WorkflowStage.FORM_GENERATION,
            name="extraction_form_generation",
            description="Generate standardized extraction forms",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            if not workflow_result.extraction_result:
                raise ValueError("No extraction result available for form generation")

            # Convert extraction result to form
            form_data = self.form_manager.convert_extraction_result_to_form(
                workflow_result.extraction_result
            )

            # Validate form
            validation_result = self.form_manager.validate_form(form_data)

            workflow_result.form_data = form_data

            step.result = {
                "form_generated": True,
                "validation_passed": validation_result.is_valid,
                "completeness_score": validation_result.completeness_score,
                "validation_errors": validation_result.errors,
                "validation_warnings": validation_result.warnings,
            }

            # Add validation issues
            step.errors.extend(validation_result.errors)
            step.warnings.extend(validation_result.warnings)

            step.status = WorkflowStatus.COMPLETED

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            raise

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _run_stage_review_preparation(self, workflow_result: WorkflowResult):
        """Run review preparation stage."""
        step = WorkflowStep(
            stage=WorkflowStage.REVIEW_PREPARATION,
            name="review_preparation",
            description="Prepare extraction results for human review",
        )

        step.start_time = datetime.now()
        step.status = WorkflowStatus.IN_PROGRESS

        try:
            # Generate recommendations
            recommendations = self._generate_workflow_recommendations(workflow_result)
            workflow_result.recommendations = recommendations

            # Prepare review summary
            review_summary = self._generate_review_summary(workflow_result)

            step.result = {
                "recommendations": recommendations,
                "review_summary": review_summary,
                "requires_review": workflow_result.overall_status
                == WorkflowStatus.REQUIRES_REVIEW,
            }

            step.status = WorkflowStatus.COMPLETED

        except Exception as e:
            step.status = WorkflowStatus.FAILED
            step.errors.append(str(e))
            # Don't raise - this is final cleanup
            logger.warning(f"Review preparation failed: {str(e)}")

        finally:
            step.end_time = datetime.now()
            step.duration_seconds = (step.end_time - step.start_time).total_seconds()
            workflow_result.steps.append(step)

    def _should_run_manual_extraction(self, workflow_result: WorkflowResult) -> bool:
        """Determine if manual extraction should be run."""
        if self.config.require_manual_validation:
            return True

        # Check automated confidence
        automated_step = None
        for step in workflow_result.steps:
            if step.stage == WorkflowStage.AUTOMATED_ANALYSIS:
                automated_step = step
                break

        if automated_step and automated_step.result:
            confidence = automated_step.result.get("confidence_score", 0.0)
            if (
                confidence >= self.config.automated_confidence_threshold
                and self.config.skip_manual_if_high_confidence
            ):
                logger.info(
                    f"Skipping manual extraction due to high automated confidence: {confidence:.2f}"
                )
                return False

        return True

    def _merge_pattern_results(
        self,
        extraction_result: ExtractionResult,
        pattern_results: Dict[PatternType, Dict[str, Any]],
    ):
        """Merge pattern matching results with extraction result."""
        for pattern_type, results in pattern_results.items():
            if pattern_type == PatternType.EXPLICIT_RESOURCE:
                # Merge hardware and training info
                if "gpu_count" in results and not extraction_result.hardware.gpu_count:
                    extraction_result.hardware.gpu_count = results["gpu_count"]
                if "gpu_type" in results and not extraction_result.hardware.gpu_type:
                    extraction_result.hardware.gpu_type = results["gpu_type"]
                if (
                    "training_time_hours" in results
                    and not extraction_result.training.total_time_hours
                ):
                    extraction_result.training.total_time_hours = results[
                        "training_time_hours"
                    ]

            elif pattern_type == PatternType.DISTRIBUTED_TRAINING:
                # Merge distributed training info
                if "total_gpus" in results and not extraction_result.hardware.gpu_count:
                    extraction_result.hardware.gpu_count = results["total_gpus"]
                if "nodes" in results and not extraction_result.hardware.nodes_used:
                    extraction_result.hardware.nodes_used = results["nodes"]

            # Add pattern notes
            extraction_result.notes.assumptions.append(
                f"Used {pattern_type.value} pattern for extraction"
            )

    def _generate_workflow_recommendations(
        self, workflow_result: WorkflowResult
    ) -> List[str]:
        """Generate recommendations based on workflow results."""
        recommendations = []

        # Check for failed steps
        failed_steps = [
            step
            for step in workflow_result.steps
            if step.status == WorkflowStatus.FAILED
        ]
        if failed_steps:
            recommendations.append(f"Review {len(failed_steps)} failed workflow steps")

        # Check quality score
        if workflow_result.quality_report:
            if workflow_result.quality_report.overall_score < 0.6:
                recommendations.append("Quality score is low - consider re-extraction")
            elif workflow_result.quality_report.overall_score < 0.8:
                recommendations.append(
                    "Quality score is moderate - manual review recommended"
                )

        # Check extraction completeness
        if workflow_result.extraction_result:
            completeness = self._calculate_extraction_completeness(
                workflow_result.extraction_result
            )
            if completeness < 0.5:
                recommendations.append(
                    "Extraction completeness is low - additional sources may be needed"
                )

        # Check timing
        if workflow_result.total_duration_seconds > 3600:  # > 1 hour
            recommendations.append(
                "Extraction took longer than expected - review process efficiency"
            )

        # Add quality recommendations
        if (
            workflow_result.quality_report
            and workflow_result.quality_report.recommendations
        ):
            recommendations.extend(workflow_result.quality_report.recommendations)

        return recommendations

    def _generate_review_summary(self, workflow_result: WorkflowResult) -> str:
        """Generate human-readable review summary."""
        lines = []
        lines.append(f"Extraction Workflow Summary: {workflow_result.workflow_id}")
        lines.append("=" * 60)
        lines.append(f"Paper ID: {workflow_result.paper_id}")
        lines.append(f"Analyst: {workflow_result.analyst}")
        lines.append(f"Status: {workflow_result.overall_status.value}")
        lines.append(f"Duration: {workflow_result.total_duration_seconds:.1f} seconds")
        lines.append("")

        # Step summary
        lines.append("Workflow Steps:")
        for step in workflow_result.steps:
            status_icon = "✓" if step.status == WorkflowStatus.COMPLETED else "✗"
            lines.append(f"  {status_icon} {step.name} ({step.duration_seconds:.1f}s)")
            if step.errors:
                for error in step.errors:
                    lines.append(f"    ERROR: {error}")
        lines.append("")

        # Quality summary
        if workflow_result.quality_report:
            lines.append("Quality Report:")
            lines.append(
                f"  Overall Score: {workflow_result.quality_report.overall_score:.2f}"
            )
            lines.append(
                f"  Critical Issues: {len(workflow_result.quality_report.critical_issues)}"
            )
            lines.append(f"  Warnings: {len(workflow_result.quality_report.warnings)}")
            lines.append("")

        # Recommendations
        if workflow_result.recommendations:
            lines.append("Recommendations:")
            for rec in workflow_result.recommendations:
                lines.append(f"  • {rec}")

        return "\n".join(lines)

    def _calculate_extraction_completeness(
        self, extraction_result: ExtractionResult
    ) -> float:
        """Calculate overall completeness of extraction."""
        total_fields = 0
        filled_fields = 0

        # Check main data fields
        for category in [
            extraction_result.hardware,
            extraction_result.training,
            extraction_result.model,
            extraction_result.dataset,
            extraction_result.computation,
        ]:
            for value in category.__dict__.values():
                total_fields += 1
                if value is not None:
                    filled_fields += 1

        return filled_fields / total_fields if total_fields > 0 else 0.0

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get status of a specific workflow."""
        return self.active_workflows.get(workflow_id)

    def list_active_workflows(self) -> List[str]:
        """List all active workflow IDs."""
        return list(self.active_workflows.keys())

    def save_workflow_result(
        self, workflow_result: WorkflowResult, output_path: Optional[Path] = None
    ) -> Path:
        """Save workflow result to file."""
        if output_path is None:
            output_path = Path("workflow_results")

        output_path.mkdir(parents=True, exist_ok=True)

        # Save extraction form if available
        if workflow_result.form_data:
            form_path = self.form_manager.save_form(
                workflow_result.form_data,
                workflow_result.paper_id,
                output_path / "forms",
            )
            logger.info(f"Saved extraction form to {form_path}")

        # Save quality report if available
        if workflow_result.quality_report:
            quality_path = (
                output_path
                / "quality_reports"
                / f"{workflow_result.paper_id}_quality.txt"
            )
            quality_path.parent.mkdir(parents=True, exist_ok=True)

            quality_text = self.quality_controller.generate_quality_report_text(
                workflow_result.quality_report
            )
            quality_path.write_text(quality_text)
            logger.info(f"Saved quality report to {quality_path}")

        # Save workflow summary
        summary_path = (
            output_path / "summaries" / f"{workflow_result.workflow_id}_summary.txt"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        summary_text = self._generate_review_summary(workflow_result)
        summary_path.write_text(summary_text)
        logger.info(f"Saved workflow summary to {summary_path}")

        return output_path
