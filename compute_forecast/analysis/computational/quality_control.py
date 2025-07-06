"""
Quality control checklist implementation for extraction process validation.

This module provides comprehensive quality control mechanisms to ensure
accuracy, completeness, and consistency of extracted computational requirements.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime

from .extraction_protocol import ExtractionResult

logger = logging.getLogger(__name__)


class QualityCheckType(Enum):
    """Types of quality checks."""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    PLAUSIBILITY = "plausibility"


class QualityIssueLevel(Enum):
    """Severity levels for quality issues."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class QualityIssue:
    """Represents a quality issue found during validation."""

    check_type: QualityCheckType
    level: QualityIssueLevel
    field: str
    message: str
    suggested_action: str
    current_value: Any = None
    expected_range: Optional[Tuple[float, float]] = None


@dataclass
class QualityCheckResult:
    """Result of a quality check operation."""

    check_name: str
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0
    execution_time_ms: float = 0.0


@dataclass
class QualityReport:
    """Comprehensive quality report for an extraction."""

    extraction_id: str
    timestamp: datetime
    overall_score: float
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    plausibility_score: float
    check_results: List[QualityCheckResult] = field(default_factory=list)
    critical_issues: List[QualityIssue] = field(default_factory=list)
    warnings: List[QualityIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class CompletenessChecker:
    """Checks completeness of extracted data."""

    # Required fields by category
    REQUIRED_FIELDS = {
        "hardware": ["gpu_type", "gpu_count"],
        "training": ["total_time_hours"],
        "model": ["parameters_count", "architecture"],
        "dataset": ["name"],
        "computation": ["total_gpu_hours"],
    }

    # Optional but important fields
    IMPORTANT_FIELDS = {
        "hardware": ["gpu_memory_gb", "tpu_version"],
        "training": ["pre_training_hours", "fine_tuning_hours"],
        "model": ["layers", "hidden_size"],
        "dataset": ["size_gb", "samples_count"],
        "computation": ["estimated_cost_usd"],
    }

    def check_completeness(self, extraction: ExtractionResult) -> QualityCheckResult:
        """Check completeness of extraction against required fields."""
        start_time = datetime.now()
        issues = []

        total_required = 0
        filled_required = 0
        total_important = 0
        filled_important = 0

        # Check required fields
        for category, fields in self.REQUIRED_FIELDS.items():
            category_data = getattr(extraction, category)
            for field_name in fields:
                total_required += 1
                field_value = getattr(category_data, field_name, None)
                if field_value is not None:
                    filled_required += 1
                else:
                    issues.append(
                        QualityIssue(
                            check_type=QualityCheckType.COMPLETENESS,
                            level=QualityIssueLevel.CRITICAL,
                            field=f"{category}.{field_name}",
                            message=f"Required field {field_name} is missing",
                            suggested_action="Perform targeted extraction for this field",
                        )
                    )

        # Check important fields
        for category, fields in self.IMPORTANT_FIELDS.items():
            category_data = getattr(extraction, category)
            for field_name in fields:
                total_important += 1
                field_value = getattr(category_data, field_name, None)
                if field_value is not None:
                    filled_important += 1
                else:
                    issues.append(
                        QualityIssue(
                            check_type=QualityCheckType.COMPLETENESS,
                            level=QualityIssueLevel.WARNING,
                            field=f"{category}.{field_name}",
                            message=f"Important field {field_name} is missing",
                            suggested_action="Consider additional extraction effort",
                        )
                    )

        # Calculate completeness score
        required_score = filled_required / total_required if total_required > 0 else 1.0
        important_score = (
            filled_important / total_important if total_important > 0 else 1.0
        )
        overall_score = (required_score * 0.7) + (important_score * 0.3)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return QualityCheckResult(
            check_name="completeness_check",
            passed=required_score >= 0.8,  # 80% of required fields
            issues=issues,
            score=overall_score,
            execution_time_ms=execution_time,
        )


class AccuracyChecker:
    """Checks accuracy of extracted data against known patterns."""

    # Known GPU types with specifications
    GPU_SPECS = {
        "V100": {"memory_gb": 16, "release_year": 2017},
        "A100": {"memory_gb": 40, "release_year": 2020},
        "T4": {"memory_gb": 16, "release_year": 2018},
        "K80": {"memory_gb": 12, "release_year": 2014},
        "P100": {"memory_gb": 16, "release_year": 2016},
    }

    # Parameter count ranges for common architectures
    ARCHITECTURE_PARAMS = {
        "BERT-base": (110, 110),  # 110M parameters
        "BERT-large": (340, 340),  # 340M parameters
        "GPT-2": (117, 1500),  # 117M to 1.5B parameters
        "GPT-3": (125000, 175000),  # 125B to 175B parameters
        "T5": (60, 11000),  # 60M to 11B parameters
        "Transformer": (10, 1000),  # 10M to 1B parameters (general)
    }

    def check_accuracy(self, extraction: ExtractionResult) -> QualityCheckResult:
        """Check accuracy of extracted data against known specifications."""
        start_time = datetime.now()
        issues = []
        accuracy_score = 1.0

        # Check GPU specifications
        if extraction.hardware.gpu_type and extraction.hardware.gpu_memory_gb:
            gpu_issues = self._check_gpu_accuracy(extraction.hardware)
            issues.extend(gpu_issues)
            if gpu_issues:
                accuracy_score -= 0.2

        # Check parameter count vs architecture
        if extraction.model.architecture and extraction.model.parameters_count:
            model_issues = self._check_model_accuracy(extraction.model)
            issues.extend(model_issues)
            if model_issues:
                accuracy_score -= 0.3

        # Check temporal consistency (GPU release date vs paper year)
        temporal_issues = self._check_temporal_accuracy(extraction)
        issues.extend(temporal_issues)
        if temporal_issues:
            accuracy_score -= 0.1

        accuracy_score = max(0.0, accuracy_score)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return QualityCheckResult(
            check_name="accuracy_check",
            passed=accuracy_score >= 0.7,
            issues=issues,
            score=accuracy_score,
            execution_time_ms=execution_time,
        )

    def _check_gpu_accuracy(self, hardware) -> List[QualityIssue]:
        """Check GPU specifications against known values."""
        issues = []
        gpu_type = hardware.gpu_type.upper().replace(" ", "")

        if gpu_type in self.GPU_SPECS:
            expected_memory = self.GPU_SPECS[gpu_type]["memory_gb"]
            if (
                hardware.gpu_memory_gb
                and abs(hardware.gpu_memory_gb - expected_memory)
                > expected_memory * 0.1
            ):
                issues.append(
                    QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.WARNING,
                        field="hardware.gpu_memory_gb",
                        message=f"GPU memory {hardware.gpu_memory_gb}GB doesn't match expected {expected_memory}GB for {gpu_type}",
                        suggested_action="Verify GPU memory specification in paper",
                        current_value=hardware.gpu_memory_gb,
                        expected_range=(expected_memory * 0.9, expected_memory * 1.1),
                    )
                )

        return issues

    def _check_model_accuracy(self, model) -> List[QualityIssue]:
        """Check model parameter count against architecture expectations."""
        issues = []
        architecture = model.architecture.upper()

        # Find matching architecture pattern
        for arch_pattern, (min_params, max_params) in self.ARCHITECTURE_PARAMS.items():
            if arch_pattern.upper() in architecture:
                if (
                    model.parameters_count < min_params
                    or model.parameters_count > max_params
                ):
                    issues.append(
                        QualityIssue(
                            check_type=QualityCheckType.ACCURACY,
                            level=QualityIssueLevel.WARNING,
                            field="model.parameters_count",
                            message=f"Parameter count {model.parameters_count}M outside expected range for {arch_pattern}",
                            suggested_action="Verify parameter count or architecture specification",
                            current_value=model.parameters_count,
                            expected_range=(min_params, max_params),
                        )
                    )
                break

        return issues

    def _check_temporal_accuracy(
        self, extraction: ExtractionResult
    ) -> List[QualityIssue]:
        """Check temporal consistency of hardware vs publication date."""
        issues = []

        # This would need paper publication date - simplified implementation
        if extraction.hardware.gpu_type:
            gpu_type = extraction.hardware.gpu_type.upper().replace(" ", "")
            if gpu_type in self.GPU_SPECS:
                gpu_release_year = self.GPU_SPECS[gpu_type]["release_year"]
                # Would compare against paper year if available
                # For now, just check if GPU is from reasonable timeframe
                current_year = datetime.now().year
                if gpu_release_year > current_year:
                    issues.append(
                        QualityIssue(
                            check_type=QualityCheckType.ACCURACY,
                            level=QualityIssueLevel.CRITICAL,
                            field="hardware.gpu_type",
                            message=f"GPU {gpu_type} release year {gpu_release_year} is in the future",
                            suggested_action="Verify GPU type specification",
                        )
                    )

        return issues


class ConsistencyChecker:
    """Checks internal consistency of extracted data."""

    def check_consistency(self, extraction: ExtractionResult) -> QualityCheckResult:
        """Check internal consistency of extracted data."""
        start_time = datetime.now()
        issues = []
        consistency_score = 1.0

        # Check GPU-hours calculation consistency
        gpu_hour_issues = self._check_gpu_hours_consistency(extraction)
        issues.extend(gpu_hour_issues)
        if gpu_hour_issues:
            consistency_score -= 0.3

        # Check parameter count vs model size consistency
        size_issues = self._check_model_size_consistency(extraction)
        issues.extend(size_issues)
        if size_issues:
            consistency_score -= 0.2

        # Check training time vs computational cost consistency
        cost_issues = self._check_cost_consistency(extraction)
        issues.extend(cost_issues)
        if cost_issues:
            consistency_score -= 0.2

        # Check dataset size vs training time consistency
        dataset_issues = self._check_dataset_training_consistency(extraction)
        issues.extend(dataset_issues)
        if dataset_issues:
            consistency_score -= 0.1

        consistency_score = max(0.0, consistency_score)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return QualityCheckResult(
            check_name="consistency_check",
            passed=consistency_score >= 0.8,
            issues=issues,
            score=consistency_score,
            execution_time_ms=execution_time,
        )

    def _check_gpu_hours_consistency(
        self, extraction: ExtractionResult
    ) -> List[QualityIssue]:
        """Check consistency between GPU count, training time, and total GPU-hours."""
        issues = []

        if (
            extraction.hardware.gpu_count
            and extraction.training.total_time_hours
            and extraction.computation.total_gpu_hours
        ):
            calculated_gpu_hours = (
                extraction.hardware.gpu_count * extraction.training.total_time_hours
            )
            reported_gpu_hours = extraction.computation.total_gpu_hours

            # Allow 10% tolerance for rounding
            tolerance = calculated_gpu_hours * 0.1
            if abs(calculated_gpu_hours - reported_gpu_hours) > tolerance:
                issues.append(
                    QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.CRITICAL,
                        field="computation.total_gpu_hours",
                        message=f"GPU-hours inconsistent: calculated {calculated_gpu_hours:.1f}, reported {reported_gpu_hours:.1f}",
                        suggested_action="Recalculate GPU-hours or verify individual components",
                        current_value=reported_gpu_hours,
                        expected_range=(
                            calculated_gpu_hours - tolerance,
                            calculated_gpu_hours + tolerance,
                        ),
                    )
                )

        return issues

    def _check_model_size_consistency(
        self, extraction: ExtractionResult
    ) -> List[QualityIssue]:
        """Check consistency between parameter count and model size."""
        issues = []

        if extraction.model.parameters_count and extraction.model.model_size_gb:
            # Rough estimate: 4 bytes per parameter (float32)
            estimated_size_gb = (extraction.model.parameters_count * 1_000_000 * 4) / (
                1024**3
            )
            reported_size_gb = extraction.model.model_size_gb

            # Allow 50% tolerance (model size can vary significantly with precision, optimization)
            tolerance = estimated_size_gb * 0.5
            if abs(estimated_size_gb - reported_size_gb) > tolerance:
                issues.append(
                    QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.WARNING,
                        field="model.model_size_gb",
                        message=f"Model size inconsistent with parameter count: estimated {estimated_size_gb:.1f}GB, reported {reported_size_gb:.1f}GB",
                        suggested_action="Verify model size calculation or parameter count",
                        current_value=reported_size_gb,
                        expected_range=(
                            estimated_size_gb - tolerance,
                            estimated_size_gb + tolerance,
                        ),
                    )
                )

        return issues

    def _check_cost_consistency(
        self, extraction: ExtractionResult
    ) -> List[QualityIssue]:
        """Check consistency between computational resources and estimated cost."""
        issues = []

        if (
            extraction.computation.total_gpu_hours
            and extraction.computation.estimated_cost_usd
        ):
            # Rough estimate: $1-3 per GPU-hour for cloud computing
            min_cost = extraction.computation.total_gpu_hours * 1.0
            max_cost = extraction.computation.total_gpu_hours * 3.0
            reported_cost = extraction.computation.estimated_cost_usd

            if reported_cost < min_cost * 0.5 or reported_cost > max_cost * 2:
                issues.append(
                    QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.WARNING,
                        field="computation.estimated_cost_usd",
                        message=f"Cost estimate ${reported_cost:.0f} outside expected range ${min_cost:.0f}-${max_cost:.0f}",
                        suggested_action="Verify cost calculation methodology",
                        current_value=reported_cost,
                        expected_range=(min_cost, max_cost),
                    )
                )

        return issues

    def _check_dataset_training_consistency(
        self, extraction: ExtractionResult
    ) -> List[QualityIssue]:
        """Check consistency between dataset size and training time."""
        issues = []

        # This is highly dependent on specific circumstances, so only flag extreme cases
        if extraction.dataset.samples_count and extraction.training.total_time_hours:
            # Very rough heuristic: > 1M samples should take > 1 hour
            if (
                extraction.dataset.samples_count > 1_000_000
                and extraction.training.total_time_hours < 1
            ):
                issues.append(
                    QualityIssue(
                        check_type=QualityCheckType.CONSISTENCY,
                        level=QualityIssueLevel.INFO,
                        field="training.total_time_hours",
                        message=f"Training time {extraction.training.total_time_hours} hours seems short for {extraction.dataset.samples_count:,} samples",
                        suggested_action="Verify training time or check for pre-training/transfer learning",
                    )
                )

        return issues


class PlausibilityChecker:
    """Checks plausibility of extracted values against known limits."""

    # Plausibility ranges for different metrics
    PLAUSIBILITY_RANGES = {
        "gpu_count": (1, 10000),  # 1 GPU to 10K GPUs
        "gpu_memory_gb": (1, 80),  # 1GB to 80GB per GPU
        "training_hours": (0.1, 8760),  # 6 minutes to 1 year
        "parameters_millions": (0.1, 1_000_000),  # 100K to 1T parameters
        "dataset_size_gb": (0.001, 100_000),  # 1MB to 100TB
        "gpu_hours": (0.1, 10_000_000),  # 6 minutes to 10M GPU-hours
        "cost_usd": (1, 100_000_000),  # $1 to $100M
    }

    def check_plausibility(self, extraction: ExtractionResult) -> QualityCheckResult:
        """Check plausibility of extracted values."""
        start_time = datetime.now()
        issues = []
        plausibility_score = 1.0

        # Check all numeric values against plausibility ranges
        checks = [
            ("gpu_count", extraction.hardware.gpu_count, "hardware.gpu_count"),
            (
                "gpu_memory_gb",
                extraction.hardware.gpu_memory_gb,
                "hardware.gpu_memory_gb",
            ),
            (
                "training_hours",
                extraction.training.total_time_hours,
                "training.total_time_hours",
            ),
            (
                "parameters_millions",
                extraction.model.parameters_count,
                "model.parameters_count",
            ),
            ("dataset_size_gb", extraction.dataset.size_gb, "dataset.size_gb"),
            (
                "gpu_hours",
                extraction.computation.total_gpu_hours,
                "computation.total_gpu_hours",
            ),
            (
                "cost_usd",
                extraction.computation.estimated_cost_usd,
                "computation.estimated_cost_usd",
            ),
        ]

        for range_key, value, field_name in checks:
            if value is not None and range_key in self.PLAUSIBILITY_RANGES:
                min_val, max_val = self.PLAUSIBILITY_RANGES[range_key]
                if value < min_val or value > max_val:
                    level = (
                        QualityIssueLevel.CRITICAL
                        if (value < min_val * 0.1 or value > max_val * 10)
                        else QualityIssueLevel.WARNING
                    )
                    issues.append(
                        QualityIssue(
                            check_type=QualityCheckType.PLAUSIBILITY,
                            level=level,
                            field=field_name,
                            message=f"Value {value} outside plausible range [{min_val}, {max_val}]",
                            suggested_action="Verify value extraction and units",
                            current_value=value,
                            expected_range=(min_val, max_val),
                        )
                    )
                    if level == QualityIssueLevel.CRITICAL:
                        plausibility_score -= 0.3
                    else:
                        plausibility_score -= 0.1

        plausibility_score = max(0.0, plausibility_score)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return QualityCheckResult(
            check_name="plausibility_check",
            passed=plausibility_score >= 0.7,
            issues=issues,
            score=plausibility_score,
            execution_time_ms=execution_time,
        )


class QualityController:
    """Main quality control orchestrator."""

    def __init__(self):
        """Initialize quality controller with all checkers."""
        self.completeness_checker = CompletenessChecker()
        self.accuracy_checker = AccuracyChecker()
        self.consistency_checker = ConsistencyChecker()
        self.plausibility_checker = PlausibilityChecker()

    def run_quality_checks(self, extraction: ExtractionResult) -> QualityReport:
        """Run comprehensive quality checks on extraction result."""
        logger.info(
            f"Running quality checks for extraction {extraction.metadata.paper_id}"
        )

        start_time = datetime.now()
        check_results = []
        all_issues = []

        # Run all quality checks
        checks = [
            ("completeness", self.completeness_checker.check_completeness),
            ("accuracy", self.accuracy_checker.check_accuracy),
            ("consistency", self.consistency_checker.check_consistency),
            ("plausibility", self.plausibility_checker.check_plausibility),
        ]

        scores = {}
        for check_name, check_function in checks:
            try:
                result = check_function(extraction)
                check_results.append(result)
                all_issues.extend(result.issues)
                scores[check_name] = result.score
                logger.debug(
                    f"{check_name} check completed: score={result.score:.2f}, issues={len(result.issues)}"
                )
            except Exception as e:
                logger.error(f"Quality check {check_name} failed: {str(e)}")
                # Create a failed check result
                failed_result = QualityCheckResult(
                    check_name=check_name,
                    passed=False,
                    score=0.0,
                    issues=[
                        QualityIssue(
                            check_type=QualityCheckType.ACCURACY,
                            level=QualityIssueLevel.CRITICAL,
                            field="system",
                            message=f"Quality check {check_name} failed: {str(e)}",
                            suggested_action="Review extraction process",
                        )
                    ],
                )
                check_results.append(failed_result)
                all_issues.extend(failed_result.issues)
                scores[check_name] = 0.0

        # Categorize issues by severity
        critical_issues = [
            issue for issue in all_issues if issue.level == QualityIssueLevel.CRITICAL
        ]
        warnings = [
            issue for issue in all_issues if issue.level == QualityIssueLevel.WARNING
        ]

        # Calculate overall score (weighted average)
        weights = {
            "completeness": 0.3,
            "accuracy": 0.25,
            "consistency": 0.25,
            "plausibility": 0.2,
        }
        overall_score = sum(
            scores.get(check, 0) * weight for check, weight in weights.items()
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            critical_issues, warnings, scores
        )

        report = QualityReport(
            extraction_id=extraction.metadata.paper_id,
            timestamp=start_time,
            overall_score=overall_score,
            completeness_score=scores.get("completeness", 0),
            accuracy_score=scores.get("accuracy", 0),
            consistency_score=scores.get("consistency", 0),
            plausibility_score=scores.get("plausibility", 0),
            check_results=check_results,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
        )

        logger.info(
            f"Quality checks completed: overall_score={overall_score:.2f}, "
            f"critical_issues={len(critical_issues)}, warnings={len(warnings)}"
        )

        return report

    def _generate_recommendations(
        self,
        critical_issues: List[QualityIssue],
        warnings: List[QualityIssue],
        scores: Dict[str, float],
    ) -> List[str]:
        """Generate actionable recommendations based on quality check results."""
        recommendations = []

        # Critical issue recommendations
        if critical_issues:
            recommendations.append(
                f"Address {len(critical_issues)} critical issues before proceeding"
            )

            # Group by field for specific recommendations
            field_issues = {}
            for issue in critical_issues:
                field_issues.setdefault(issue.field, []).append(issue)

            for field, issues in field_issues.items():
                if len(issues) > 1:
                    recommendations.append(
                        f"Multiple critical issues in {field} - comprehensive review needed"
                    )

        # Score-based recommendations
        if scores.get("completeness", 0) < 0.6:
            recommendations.append(
                "Completeness score low - perform additional targeted extraction"
            )

        if scores.get("accuracy", 0) < 0.7:
            recommendations.append(
                "Accuracy issues detected - verify extracted values against paper"
            )

        if scores.get("consistency", 0) < 0.8:
            recommendations.append(
                "Consistency issues found - review calculations and cross-references"
            )

        if scores.get("plausibility", 0) < 0.7:
            recommendations.append(
                "Implausible values detected - verify units and extraction method"
            )

        # General recommendations
        if len(warnings) > 5:
            recommendations.append(
                "High number of warnings - consider additional quality review"
            )

        if not recommendations:
            recommendations.append("Extraction quality is good - ready for data entry")

        return recommendations

    def generate_quality_report_text(self, report: QualityReport) -> str:
        """Generate human-readable quality report."""
        lines = []
        lines.append(f"Quality Report for {report.extraction_id}")
        lines.append("=" * 50)
        lines.append(f"Overall Score: {report.overall_score:.2f}")
        lines.append(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Score breakdown
        lines.append("Score Breakdown:")
        lines.append(f"  Completeness: {report.completeness_score:.2f}")
        lines.append(f"  Accuracy:     {report.accuracy_score:.2f}")
        lines.append(f"  Consistency:  {report.consistency_score:.2f}")
        lines.append(f"  Plausibility: {report.plausibility_score:.2f}")
        lines.append("")

        # Critical issues
        if report.critical_issues:
            lines.append(f"Critical Issues ({len(report.critical_issues)}):")
            for issue in report.critical_issues:
                lines.append(f"  • {issue.field}: {issue.message}")
                lines.append(f"    Action: {issue.suggested_action}")
            lines.append("")

        # Warnings
        if report.warnings:
            lines.append(f"Warnings ({len(report.warnings)}):")
            for warning in report.warnings[:5]:  # Show first 5 warnings
                lines.append(f"  • {warning.field}: {warning.message}")
            if len(report.warnings) > 5:
                lines.append(f"  ... and {len(report.warnings) - 5} more warnings")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("Recommendations:")
            for rec in report.recommendations:
                lines.append(f"  • {rec}")

        return "\n".join(lines)
