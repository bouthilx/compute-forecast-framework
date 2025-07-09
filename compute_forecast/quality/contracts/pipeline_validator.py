"""
Pipeline validation components for contract enforcement.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from compute_forecast.data.models import Paper, ComputationalAnalysis
from compute_forecast.quality.validators.base import BaseValidator
from compute_forecast.core.exceptions import ValidationError

from .base_contracts import (
    AnalysisContract,
    ContractViolation,
    ContractViolationType,
    ContractValidationResult,
    StageTransitionContract,
)
from .analysis_contracts import (
    ComputationalAnalysisContract,
    PaperMetadataContract,
    ResourceMetricsContract,
)


class AnalysisContractValidator(BaseValidator):
    """Validates analysis outputs meet pipeline requirements."""

    def __init__(self):
        super().__init__()
        self.contracts: Dict[str, AnalysisContract] = {}
        self.register_default_contracts()

    def register_default_contracts(self) -> None:
        """Register default validation contracts."""
        self.register_contract(
            "computational_analysis", ComputationalAnalysisContract()
        )
        self.register_contract("paper_metadata", PaperMetadataContract())
        self.register_contract("resource_metrics", ResourceMetricsContract())

    def register_contract(self, analysis_type: str, contract: AnalysisContract) -> None:
        """
        Register validation contract for analysis type.

        Args:
            analysis_type: Type of analysis (e.g., "computational_analysis")
            contract: Contract implementation
        """
        self.contracts[analysis_type] = contract

    def validate_computational_analysis(
        self, analysis: ComputationalAnalysis, paper: Optional[Paper] = None
    ) -> ContractValidationResult:
        """
        Validate computational analysis meets all contracts.

        Args:
            analysis: Computational analysis to validate
            paper: Optional paper for cross-validation

        Returns:
            ContractValidationResult with violations
        """
        start_time = time.time()

        # Get computational analysis contract
        contract = self.contracts.get("computational_analysis")
        if not contract:
            raise ValidationError("No contract registered for computational_analysis")

        # Validate analysis
        violations = contract.validate(analysis)

        # Additional cross-validation with paper if provided
        if paper:
            # Validate that analysis is consistent with paper metadata
            if hasattr(analysis, "paper_id") and analysis.paper_id != paper.paper_id:
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INCONSISTENT_DATA,
                        field_name="paper_id",
                        expected=paper.paper_id,
                        actual=analysis.paper_id,
                        severity="error",
                        message="Analysis paper_id does not match paper",
                    )
                )

        # Validate resource metrics separately
        if analysis.resource_metrics:
            metrics_contract = self.contracts.get("resource_metrics")
            if metrics_contract:
                metrics_violations = metrics_contract.validate(
                    analysis.resource_metrics
                )
                violations.extend(metrics_violations)

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Check performance requirements
        perf_requirements = contract.get_performance_requirements()
        if execution_time > perf_requirements.get(
            "max_processing_time_ms", float("inf")
        ):
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.PERFORMANCE_VIOLATION,
                    field_name="execution_time",
                    expected=f"<= {perf_requirements['max_processing_time_ms']}ms",
                    actual=f"{execution_time:.2f}ms",
                    severity="warning",
                    message="Validation took longer than expected",
                )
            )

        # Separate violations by severity
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        return ContractValidationResult(
            contract_name="computational_analysis",
            passed=len(errors) == 0,
            violations=errors,
            warnings=warnings,
            execution_time_ms=execution_time,
            metadata={
                "paper_id": paper.paper_id if paper else None,
                "has_resource_metrics": bool(analysis.resource_metrics),
                "confidence_score": analysis.confidence_score,
            },
        )

    def validate_pipeline_transition(
        self,
        from_stage: str,
        to_stage: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
    ) -> ContractValidationResult:
        """
        Validate data between pipeline stages.

        Args:
            from_stage: Source stage name
            to_stage: Target stage name
            input_data: Data from source stage
            output_data: Data from target stage

        Returns:
            ContractValidationResult
        """
        start_time = time.time()

        # Define stage transitions
        transition = self._get_stage_transition(from_stage, to_stage)

        if not transition:
            return ContractValidationResult(
                contract_name=f"{from_stage}_to_{to_stage}",
                passed=False,
                violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_REFERENCE,
                        field_name="transition",
                        expected="valid transition",
                        actual=f"{from_stage} -> {to_stage}",
                        severity="error",
                        message=f"Unknown transition from {from_stage} to {to_stage}",
                    )
                ],
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Validate transition
        violations = transition.validate_transition(input_data, output_data)

        execution_time = (time.time() - start_time) * 1000

        return ContractValidationResult(
            contract_name=f"{from_stage}_to_{to_stage}",
            passed=len(violations) == 0,
            violations=violations,
            execution_time_ms=execution_time,
            metadata={
                "from_stage": from_stage,
                "to_stage": to_stage,
                "input_fields": list(input_data.keys()),
                "output_fields": list(output_data.keys()),
            },
        )

    def _get_stage_transition(
        self, from_stage: str, to_stage: str
    ) -> Optional[StageTransitionContract]:
        """Get transition contract between stages."""
        transitions = {
            ("collection", "analysis"): StageTransitionContract(
                from_stage="collection",
                to_stage="analysis",
                required_fields=["papers", "metadata"],
                transformations={
                    "raw_papers": "papers",
                    "collection_metadata": "metadata",
                },
                validation_rules=["papers_valid", "metadata_complete"],
            ),
            ("analysis", "projection"): StageTransitionContract(
                from_stage="analysis",
                to_stage="projection",
                required_fields=["analyses", "quality_scores"],
                transformations={
                    "computational_analyses": "analyses",
                    "quality_metrics": "quality_scores",
                },
                validation_rules=["analyses_complete", "scores_valid"],
            ),
        }

        return transitions.get((from_stage, to_stage))

    def validate(self, papers: List[Paper]) -> Dict[str, Any]:
        """
        Validate papers according to BaseValidator interface.

        Args:
            papers: List of papers to validate

        Returns:
            Validation results dictionary
        """
        total_papers = len(papers)
        valid_papers = 0
        violations_by_type: Dict[str, int] = {}
        failed_papers: List[Dict[str, Any]] = []

        contract = self.contracts.get("paper_metadata")
        if not contract:
            raise ValidationError("No contract registered for paper_metadata")

        for paper in papers:
            violations = contract.validate(paper)

            if not violations:
                valid_papers += 1
            else:
                # Count violations by type
                for violation in violations:
                    violation_type = violation.violation_type.value
                    violations_by_type[violation_type] = (
                        violations_by_type.get(violation_type, 0) + 1
                    )

                failed_papers.append(
                    {
                        "paper_id": paper.paper_id,
                        "title": paper.title,
                        "violations": [
                            {
                                "type": v.violation_type.value,
                                "field": v.field_name,
                                "message": v.message,
                                "severity": v.severity,
                            }
                            for v in violations
                        ],
                    }
                )

        return {
            "total_papers": total_papers,
            "valid_papers": valid_papers,
            "invalid_papers": total_papers - valid_papers,
            "validation_rate": valid_papers / total_papers if total_papers > 0 else 0.0,
            "violations_by_type": violations_by_type,
            "failed_papers": failed_papers[:10],  # Limit to first 10 for readability
            "contract_type": "paper_metadata",
        }

    def get_validation_score(self, validation_result: Dict[str, Any]) -> float:
        """
        Get overall validation score from validation result.

        Args:
            validation_result: Result from validate()

        Returns:
            Score between 0.0 and 1.0
        """
        return float(validation_result.get("validation_rate", 0.0))


@dataclass
class PipelineValidationReport:
    """Comprehensive pipeline validation report."""

    stage: str
    total_items: int
    valid_items: int
    contract_results: List[ContractValidationResult] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    @property
    def validation_rate(self) -> float:
        """Overall validation success rate."""
        return self.valid_items / self.total_items if self.total_items > 0 else 0.0

    @property
    def total_violations(self) -> int:
        """Total number of violations across all contracts."""
        return sum(len(result.violations) for result in self.contract_results)

    @property
    def total_warnings(self) -> int:
        """Total number of warnings across all contracts."""
        return sum(len(result.warnings) for result in self.contract_results)


class PipelineIntegrationValidator:
    """Validates data flow between pipeline components."""

    def __init__(self):
        self.contract_validator = AnalysisContractValidator()
        self.stage_requirements = {
            "collection": ["paper_id", "title", "authors", "venue", "year"],
            "analysis": ["computational_analysis", "confidence_score"],
            "projection": ["growth_metrics", "trend_data"],
        }

    def validate_collection_to_analysis(
        self, papers: List[Paper]
    ) -> PipelineValidationReport:
        """
        Validate papers ready for analysis.

        Args:
            papers: Papers from collection stage

        Returns:
            PipelineValidationReport
        """
        report = PipelineValidationReport(
            stage="collection_to_analysis", total_items=len(papers), valid_items=0
        )

        # Validate each paper
        for paper in papers:
            result = self.contract_validator.contracts["paper_metadata"].validate(paper)

            if not result:  # No violations
                report.valid_items += 1

        # Add contract validation results
        validation_result = self.contract_validator.validate(papers)

        report.contract_results.append(
            ContractValidationResult(
                contract_name="paper_metadata_batch",
                passed=validation_result["validation_rate"] >= 0.9,
                execution_time_ms=0.0,  # Not tracked in batch
                metadata=validation_result,
            )
        )

        # Performance metrics
        report.performance_metrics = {
            "papers_per_second": len(papers)
            / max(report.contract_results[0].execution_time_ms / 1000, 0.001),
            "validation_rate": report.validation_rate,
            "avg_violations_per_paper": report.total_violations / len(papers)
            if papers
            else 0,
        }

        # Recommendations
        if report.validation_rate < 0.9:
            report.recommendations.append(
                f"Data quality below threshold: {report.validation_rate:.1%} valid papers"
            )

        if validation_result["violations_by_type"]:
            most_common = max(
                validation_result["violations_by_type"].items(), key=lambda x: x[1]
            )
            report.recommendations.append(
                f"Most common violation: {most_common[0]} ({most_common[1]} occurrences)"
            )

        return report

    def validate_analysis_outputs(
        self, analyses: List[ComputationalAnalysis]
    ) -> PipelineValidationReport:
        """
        Validate analysis outputs meet requirements.

        Args:
            analyses: Computational analyses to validate

        Returns:
            PipelineValidationReport
        """
        report = PipelineValidationReport(
            stage="analysis_outputs", total_items=len(analyses), valid_items=0
        )

        start_time = time.time()

        # Validate each analysis
        for analysis in analyses:
            result = self.contract_validator.validate_computational_analysis(analysis)

            if result.passed:
                report.valid_items += 1

            # Track first few failures for debugging
            if not result.passed and len(report.contract_results) < 5:
                report.contract_results.append(result)

        total_time = (time.time() - start_time) * 1000

        # Performance metrics
        report.performance_metrics = {
            "analyses_per_second": len(analyses) / (total_time / 1000),
            "validation_rate": report.validation_rate,
            "avg_execution_time_ms": total_time / len(analyses) if analyses else 0,
        }

        # Recommendations
        if report.validation_rate < 0.95:
            report.recommendations.append(
                f"Analysis quality below threshold: {report.validation_rate:.1%} valid"
            )

        # Check confidence scores
        low_confidence = sum(1 for a in analyses if a.confidence_score < 0.5)
        if low_confidence > len(analyses) * 0.1:
            report.recommendations.append(
                f"{low_confidence} analyses ({low_confidence / len(analyses):.1%}) have low confidence"
            )

        return report

    def validate_full_pipeline(
        self,
        collection_data: Dict[str, Any],
        analysis_data: Dict[str, Any],
        projection_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PipelineValidationReport]:
        """
        Validate complete pipeline from collection to projection.

        Args:
            collection_data: Data from collection stage
            analysis_data: Data from analysis stage
            projection_data: Optional data from projection stage

        Returns:
            Dictionary of validation reports by stage
        """
        reports = {}

        # Validate collection to analysis transition
        if "papers" in collection_data:
            reports["collection_to_analysis"] = self.validate_collection_to_analysis(
                collection_data["papers"]
            )

        # Validate analysis outputs
        if "analyses" in analysis_data:
            reports["analysis_outputs"] = self.validate_analysis_outputs(
                analysis_data["analyses"]
            )

        # Validate stage transitions
        transition_result = self.contract_validator.validate_pipeline_transition(
            "collection", "analysis", collection_data, analysis_data
        )

        reports["collection_analysis_transition"] = PipelineValidationReport(
            stage="collection_to_analysis_transition",
            total_items=1,
            valid_items=1 if transition_result.passed else 0,
            contract_results=[transition_result],
        )

        return reports
