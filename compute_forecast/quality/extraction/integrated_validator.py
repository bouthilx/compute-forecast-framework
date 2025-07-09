"""
Integrated extraction validator combining all validation components.

This module provides a unified interface for comprehensive extraction validation.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import yaml
from pathlib import Path

from compute_forecast.quality.adaptive_thresholds import AdaptiveThresholdEngine
from compute_forecast.quality.quality_structures import QualityMetrics
from compute_forecast.data.models import Paper, ComputationalAnalysis

from .extraction_validator import ExtractionQualityValidator, ExtractionValidation
from .consistency_checker import ExtractionConsistencyChecker, ConsistencyCheck
from .cross_validation import CrossValidationFramework
from .outlier_detection import OutlierDetector


@dataclass
class IntegratedValidationResult:
    """Complete validation result from all components."""

    paper_id: str
    extraction_validation: ExtractionValidation
    consistency_checks: List[ConsistencyCheck]
    outlier_fields: List[str]
    overall_quality: str
    recommendations: List[str]
    confidence: float


class IntegratedExtractionValidator:
    """Unified validator using all extraction validation systems."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize with all validation components.

        Args:
            config_path: Path to validation rules YAML file
        """
        # Use existing components
        from compute_forecast.quality.quality_structures import AdaptationConfig

        self.threshold_engine = AdaptiveThresholdEngine(AdaptationConfig())
        self.quality_metrics = QualityMetrics()

        # Add extraction-specific validators
        self.extraction_validator = ExtractionQualityValidator()
        self.consistency_checker = ExtractionConsistencyChecker()
        self.cross_validator = CrossValidationFramework()
        self.outlier_detector = OutlierDetector()

        # Load validation rules
        self.rules = self._load_validation_rules(config_path)

        # Cache for batch validations
        self._batch_cache: Dict[str, Any] = {}

    def validate_extraction(
        self,
        paper: Paper,
        extraction: ComputationalAnalysis,
        paper_group: Optional[List[Paper]] = None,
    ) -> IntegratedValidationResult:
        """
        Perform comprehensive validation on a single extraction.

        Args:
            paper: Paper being analyzed
            extraction: Extracted computational analysis
            paper_group: Optional group of similar papers for consistency checks

        Returns:
            Integrated validation result
        """
        # 1. Basic extraction validation
        extraction_validation = self.extraction_validator.validate_extraction(
            paper, extraction
        )

        # 2. Consistency checks
        consistency_checks = []

        # Domain consistency
        if hasattr(extraction, "__dict__"):
            extraction_dict = extraction.__dict__
        else:
            extraction_dict = extraction if isinstance(extraction, dict) else {}
        domain_check = self.consistency_checker.check_domain_consistency(
            paper, extraction_dict
        )
        consistency_checks.append(domain_check)

        # Scaling law consistency
        gpu_hours = extraction_dict.get("gpu_hours")
        parameters = extraction_dict.get("parameters")
        if gpu_hours and parameters:
            scaling_check = self.consistency_checker.check_scaling_consistency(
                gpu_hours, parameters
            )
            consistency_checks.append(scaling_check)

        # Cross-paper consistency if group provided
        if paper_group and len(paper_group) > 1:
            for field in ["gpu_hours", "parameters", "training_time"]:
                if field in extraction_dict and extraction_dict[field]:
                    cross_check = (
                        self.consistency_checker.check_cross_paper_consistency(
                            paper_group, field
                        )
                    )
                    consistency_checks.append(cross_check)

        # 3. Outlier detection
        outlier_fields = []
        for field, value in extraction_dict.items():
            if isinstance(value, (int, float)) and value > 0:
                # Get values from cache or paper group
                field_values = self._get_field_values(field, paper_group)
                if field_values and len(field_values) > 3:
                    # Add current value to the list for outlier detection
                    all_values = field_values + [value]
                    outliers = self.outlier_detector.detect_outliers(
                        all_values, method="combined", field=field
                    )
                    # Check if current value index (last in list) is an outlier
                    current_value_index = len(all_values) - 1
                    if current_value_index in outliers:
                        outlier_fields.append(field)

        # 4. Calculate overall quality
        overall_quality, confidence = self._calculate_overall_quality(
            extraction_validation, consistency_checks, outlier_fields
        )

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(
            extraction_validation, consistency_checks, outlier_fields
        )

        return IntegratedValidationResult(
            paper_id=paper.paper_id or "unknown",
            extraction_validation=extraction_validation,
            consistency_checks=consistency_checks,
            outlier_fields=outlier_fields,
            overall_quality=overall_quality,
            recommendations=recommendations,
            confidence=confidence,
        )

    def validate_extraction_batch(
        self, extractions: List[Tuple[Paper, ComputationalAnalysis]]
    ) -> Dict[str, Any]:
        """
        Comprehensive validation using all systems.

        Args:
            extractions: List of (paper, extraction) tuples

        Returns:
            Batch validation report
        """
        # Build cache of field values
        self._build_batch_cache(extractions)

        # Group papers by domain for consistency checks
        domain_groups = self._group_papers_by_domain(extractions)

        # Validate each extraction
        results = []
        for paper, extraction in extractions:
            # Find relevant paper group
            paper_domain = self._determine_paper_domain(paper)
            paper_group = domain_groups.get(paper_domain, [])

            result = self.validate_extraction(paper, extraction, paper_group)
            results.append(result)

        # Temporal consistency checks
        temporal_checks = {}
        for field in ["gpu_hours", "parameters", "training_time"]:
            papers = [p for p, _ in extractions]
            check = self.consistency_checker.check_temporal_consistency(papers, field)
            temporal_checks[field] = check

        # Cross-validation if manual data available
        cross_validation_results = None
        if self._has_manual_data(extractions):
            manual_data, auto_data = self._separate_manual_auto(extractions)
            cross_validation_results = self.cross_validator.validate_extraction_quality(
                manual_data, auto_data
            )

        # Generate batch report
        return self._generate_batch_report(
            results, temporal_checks, cross_validation_results
        )

    def _load_validation_rules(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load validation rules from YAML file."""
        if config_path is None:
            # Use default path
            config_file_path = Path(__file__).parent / "validation_rules.yaml"
        else:
            config_file_path = Path(config_path)

        try:
            with open(config_file_path, "r") as f:
                return dict(yaml.safe_load(f))
        except Exception:
            # Return default rules if file not found
            return {
                "completeness_rules": {
                    "gpu_required": ["gpu_hours", "gpu_type"],
                    "training_required": ["training_time", "parameters"],
                },
                "quality_thresholds": {
                    "high": {"confidence": 0.9},
                    "medium": {"confidence": 0.7},
                    "low": {"confidence": 0.5},
                },
            }

    def _calculate_overall_quality(
        self,
        extraction_validation: ExtractionValidation,
        consistency_checks: List[ConsistencyCheck],
        outlier_fields: List[str],
    ) -> Tuple[str, float]:
        """Calculate overall quality level and confidence."""
        # Start with extraction confidence
        confidence = extraction_validation.confidence

        # Adjust for consistency
        if consistency_checks:
            consistency_scores = [c.confidence for c in consistency_checks if c.passed]
            avg_consistency = (
                sum(consistency_scores) / len(consistency_checks)
                if consistency_checks
                else 0.5
            )
            confidence = confidence * 0.7 + avg_consistency * 0.3

        # Penalize for outliers
        outlier_penalty = len(outlier_fields) * 0.1
        confidence = max(0.0, confidence - outlier_penalty)

        # Determine quality level
        thresholds = self.rules.get("quality_thresholds", {})
        if confidence >= thresholds.get("high", {}).get("confidence", 0.9):
            quality = "high"
        elif confidence >= thresholds.get("medium", {}).get("confidence", 0.7):
            quality = "medium"
        elif confidence >= thresholds.get("low", {}).get("confidence", 0.5):
            quality = "low"
        else:
            quality = "unreliable"

        return quality, confidence

    def _generate_recommendations(
        self,
        extraction_validation: ExtractionValidation,
        consistency_checks: List[ConsistencyCheck],
        outlier_fields: List[str],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Completeness recommendations
        if extraction_validation.confidence < 0.8:
            details = extraction_validation.cross_validation_result or {}
            completeness = details.get("completeness", 0)
            if completeness < 0.7:
                recommendations.append(
                    "Improve extraction completeness - missing critical fields"
                )

        # Consistency recommendations
        failed_checks = [c for c in consistency_checks if not c.passed]
        for check in failed_checks:
            if check.check_type == "domain_specific":
                recommendations.append(
                    f"Review domain-specific values: {check.details}"
                )
            elif check.check_type == "scaling_law":
                recommendations.append(
                    "GPU hours and parameters don't follow expected scaling"
                )
            elif check.check_type == "temporal":
                recommendations.append(
                    f"Temporal trend anomaly detected: {check.details}"
                )

        # Outlier recommendations
        if outlier_fields:
            recommendations.append(
                f"Manual review recommended for outlier fields: {', '.join(outlier_fields)}"
            )

        # Quality-based recommendations
        if extraction_validation.quality.value == "unreliable":
            recommendations.append("Consider manual extraction for this paper")
        elif extraction_validation.quality.value == "low":
            recommendations.append("Verify extraction accuracy with additional sources")

        return recommendations

    def _build_batch_cache(
        self, extractions: List[Tuple[Paper, ComputationalAnalysis]]
    ):
        """Build cache of field values for batch processing."""
        self._batch_cache.clear()

        for paper, extraction in extractions:
            if hasattr(extraction, "__dict__"):
                extraction_dict = extraction.__dict__
            else:
                extraction_dict = extraction if isinstance(extraction, dict) else {}
            for field, value in extraction_dict.items():
                if isinstance(value, (int, float)) and value > 0:
                    if field not in self._batch_cache:
                        self._batch_cache[field] = []
                    self._batch_cache[field].append(value)

    def _get_field_values(
        self, field: str, paper_group: Optional[List[Paper]] = None
    ) -> List[float]:
        """Get field values from cache or paper group."""
        # First check cache
        if field in self._batch_cache:
            return list(self._batch_cache[field])

        # Otherwise extract from paper group
        if paper_group:
            values = []
            for paper in paper_group:
                if (
                    hasattr(paper, "computational_analysis")
                    and paper.computational_analysis
                ):
                    analysis = paper.computational_analysis
                    if hasattr(analysis, field):
                        value = getattr(analysis, field)
                        if isinstance(value, (int, float)) and value > 0:
                            values.append(value)
            return values

        return []

    def _group_papers_by_domain(
        self, extractions: List[Tuple[Paper, ComputationalAnalysis]]
    ) -> Dict[str, List[Paper]]:
        """Group papers by domain for consistency checks."""
        domain_groups: Dict[str, List[Paper]] = {}

        for paper, _ in extractions:
            domain = self._determine_paper_domain(paper)
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(paper)

        return domain_groups

    def _determine_paper_domain(self, paper: Paper) -> str:
        """Determine paper domain from title."""
        if not hasattr(paper, "title") or not paper.title:
            return "general"

        title_lower = paper.title.lower()

        if any(
            term in title_lower
            for term in ["language", "nlp", "transformer", "bert", "gpt"]
        ):
            return "nlp"
        elif any(
            term in title_lower for term in ["image", "vision", "cnn", "detection"]
        ):
            return "cv"
        elif any(
            term in title_lower for term in ["reinforcement", "rl", "agent", "reward"]
        ):
            return "rl"

        return "general"

    def _has_manual_data(
        self, extractions: List[Tuple[Paper, ComputationalAnalysis]]
    ) -> bool:
        """Check if any extractions have manual validation data."""
        # This is a placeholder - in practice, you'd check for manual validation flags
        return False

    def _separate_manual_auto(
        self, extractions: List[Tuple[Paper, ComputationalAnalysis]]
    ) -> Tuple[Dict, Dict]:
        """Separate manual and automated extraction data."""
        # This is a placeholder - in practice, you'd separate based on extraction method
        manual_data: Dict[str, Any] = {}
        auto_data: Dict[str, Any] = {}
        return manual_data, auto_data

    def _generate_batch_report(
        self,
        results: List[IntegratedValidationResult],
        temporal_checks: Dict[str, ConsistencyCheck],
        cross_validation_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate comprehensive batch validation report."""
        # Calculate summary statistics
        quality_distribution = {"high": 0, "medium": 0, "low": 0, "unreliable": 0}
        total_outliers = 0
        all_recommendations = []

        for result in results:
            quality_distribution[result.overall_quality] += 1
            total_outliers += len(result.outlier_fields)
            all_recommendations.extend(result.recommendations)

        # Unique recommendations
        unique_recommendations = list(set(all_recommendations))

        # Average confidence
        avg_confidence = (
            sum(r.confidence for r in results) / len(results) if results else 0
        )

        return {
            "summary": {
                "total_extractions": len(results),
                "average_confidence": avg_confidence,
                "quality_distribution": quality_distribution,
                "total_outliers": total_outliers,
            },
            "temporal_consistency": temporal_checks,
            "cross_validation": cross_validation_results,
            "recommendations": unique_recommendations,
            "details": [
                {
                    "paper_id": r.paper_id,
                    "quality": r.overall_quality,
                    "confidence": r.confidence,
                    "outlier_fields": r.outlier_fields,
                }
                for r in results
            ],
        }
