"""
Consistency checker for extracted computational metrics.

This module validates consistency across similar papers and identifies anomalies.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np

from compute_forecast.pipeline.metadata_collection.models import Paper


@dataclass
class ConsistencyCheck:
    """Result of a consistency check."""

    check_type: str  # temporal, cross_paper, domain_specific
    passed: bool
    confidence: float
    details: Dict[str, Any]


class ExtractionConsistencyChecker:
    """Check consistency across similar papers."""

    def __init__(self):
        """Initialize with thresholds."""
        self.similarity_threshold = 0.8
        self.outlier_z_score = 2.0

        # Expected scaling laws
        self.scaling_laws = {
            "gpu_hours_vs_parameters": {
                "relationship": "power",
                "exponent": 0.7,  # GPU hours ~ parameters^0.7
                "tolerance": 0.3,
            },
            "parameters_vs_year": {
                "relationship": "exponential",
                "growth_rate": 1.5,  # 50% annual growth
                "tolerance": 0.5,
            },
        }

        # Domain-specific ranges
        self.domain_ranges = {
            "nlp": {
                "parameters": (1e6, 1e12),
                "gpu_hours": (10, 1e6),
                "batch_size": (8, 512),
            },
            "cv": {
                "parameters": (1e6, 1e10),
                "gpu_hours": (10, 1e5),
                "batch_size": (16, 1024),
            },
            "rl": {
                "parameters": (1e5, 1e9),
                "gpu_hours": (100, 1e6),
                "episodes": (1000, 1e8),
            },
        }

    def check_temporal_consistency(
        self, papers: List[Paper], metric: str
    ) -> ConsistencyCheck:
        """
        Verify metrics follow temporal trends.

        Args:
            papers: List of papers sorted by year
            metric: Metric to check (e.g., "gpu_hours", "parameters")

        Returns:
            ConsistencyCheck result
        """
        # Extract year and metric values
        data_points = []
        for paper in papers:
            if hasattr(paper, "year") and paper.year:
                if (
                    hasattr(paper, "computational_analysis")
                    and paper.computational_analysis
                ):
                    analysis = paper.computational_analysis
                    if hasattr(analysis, metric):
                        value = getattr(analysis, metric)
                        if value is not None and value > 0:
                            data_points.append((paper.year, value))

        if len(data_points) < 3:
            return ConsistencyCheck(
                check_type="temporal",
                passed=True,
                confidence=0.5,
                details={
                    "reason": "insufficient_data",
                    "data_points": len(data_points),
                },
            )

        # Sort by year
        data_points.sort(key=lambda x: x[0])
        years = np.array([p[0] for p in data_points])
        values = np.array([p[1] for p in data_points])

        # Check for general increasing trend
        if metric in ["parameters", "gpu_hours"]:
            # Fit exponential trend
            try:
                # Check if we have enough unique years for fitting
                if len(np.unique(years)) < 2:
                    # All years are the same, can't compute trend
                    growth_rate = 0
                # Check if values are suitable for polynomial fitting
                elif len(np.unique(values)) < 2 or np.std(values) < 1e-10:
                    # Data is constant or nearly constant
                    growth_rate = 0
                elif np.any(values <= 0):
                    # Can't take log of non-positive values, use linear fit
                    # But first check if data has enough variation
                    if np.std(values) / np.mean(np.abs(values)) < 1e-10:
                        growth_rate = 0
                    else:
                        coeffs = np.polyfit(years - years[0], values, 1)
                        growth_rate = (
                            coeffs[0] / np.mean(values) if np.mean(values) > 0 else 0
                        )
                else:
                    log_values = np.log(values)
                    # Check for invalid values (NaN or inf)
                    if not np.all(np.isfinite(log_values)):
                        # Fall back to linear trend if log doesn't work
                        coeffs = np.polyfit(years - years[0], values, 1)
                        # Use linear growth rate approximation
                        growth_rate = (
                            coeffs[0] / np.mean(values) if np.mean(values) > 0 else 0
                        )
                    else:
                        coeffs = np.polyfit(years - years[0], log_values, 1)
                        growth_rate = np.exp(coeffs[0]) - 1
            except (np.linalg.LinAlgError, ValueError, RuntimeWarning):
                # If polynomial fitting fails, use simple linear trend
                try:
                    # Simple linear growth rate
                    if len(values) >= 2:
                        growth_rate = (
                            (values[-1] - values[0])
                            / (values[0] * (years[-1] - years[0]))
                            if values[0] > 0
                            else 0
                        )
                    else:
                        growth_rate = 0
                except (ZeroDivisionError, ValueError):
                    growth_rate = 0

            # Check if growth rate is reasonable
            expected_growth = self.scaling_laws.get(f"{metric}_vs_year", {}).get(
                "growth_rate", 0.5
            )
            tolerance = self.scaling_laws.get(f"{metric}_vs_year", {}).get(
                "tolerance", 0.5
            )

            if growth_rate < -0.2:  # Significant decrease
                passed = False
                confidence = 0.3
                details = {
                    "issue": "decreasing_trend",
                    "growth_rate": growth_rate,
                    "expected_positive": True,
                }
            elif (
                expected_growth != 0
                and abs(growth_rate - expected_growth) / expected_growth > tolerance
            ):
                passed = True  # Pass but note deviation
                confidence = 0.7
                details = {
                    "issue": "unusual_growth_rate",
                    "growth_rate": growth_rate,
                    "expected": expected_growth,
                }
            else:
                passed = True
                confidence = 0.9
                details = {
                    "growth_rate": growth_rate,
                    "expected": expected_growth,
                    "within_tolerance": True,
                }
        else:
            # For other metrics, just check for outliers
            try:
                std_val = np.std(values)
                if std_val == 0 or not np.isfinite(std_val):
                    # All values are the same, no outliers
                    outliers: List[int] = []
                    z_scores = np.zeros_like(values)
                else:
                    z_scores = np.abs((values - np.mean(values)) / std_val)
                    outliers = list(np.where(z_scores > self.outlier_z_score)[0])
            except (ValueError, RuntimeWarning):
                # If calculation fails, assume no outliers
                outliers = []
                z_scores = np.zeros_like(values)

            passed = len(outliers) == 0
            confidence = 1.0 - (len(outliers) / len(values)) if len(values) > 0 else 1.0
            details = {
                "outliers": len(outliers),
                "total": len(values),
                "outlier_years": [years[i] for i in outliers],
            }

        return ConsistencyCheck(
            check_type="temporal", passed=passed, confidence=confidence, details=details
        )

    def check_cross_paper_consistency(
        self, paper_group: List[Paper], extraction_field: str
    ) -> ConsistencyCheck:
        """
        Check if similar papers have similar metrics.

        Args:
            paper_group: List of similar papers
            extraction_field: Field to check consistency for

        Returns:
            ConsistencyCheck result
        """
        # Extract values for the field
        values = []
        papers_with_data = []

        for paper in paper_group:
            if (
                hasattr(paper, "computational_analysis")
                and paper.computational_analysis
            ):
                analysis = paper.computational_analysis
                if hasattr(analysis, extraction_field):
                    value = getattr(analysis, extraction_field)
                    if value is not None and value > 0:
                        values.append(value)
                        papers_with_data.append(paper)

        if len(values) < 2:
            return ConsistencyCheck(
                check_type="cross_paper",
                passed=True,
                confidence=0.5,
                details={
                    "reason": "insufficient_data",
                    "papers_with_data": len(values),
                },
            )

        values = list(values)

        # Calculate statistics
        mean_val = np.mean(values)
        std_val = np.std(values)
        cv = (
            std_val / mean_val if mean_val > 0 else float("inf")
        )  # Coefficient of variation

        # Identify outliers
        z_scores = (
            np.abs((values - mean_val) / std_val)
            if std_val > 0
            else np.zeros_like(values)
        )
        outliers = list(np.where(z_scores > self.outlier_z_score)[0])

        # Determine if consistency is acceptable
        if cv > 1.0:  # High variation
            passed = False
            confidence = 0.4
            details = {
                "issue": "high_variation",
                "coefficient_of_variation": cv,
                "mean": mean_val,
                "std": std_val,
            }
        elif len(outliers) > len(values) * 0.2:  # More than 20% outliers
            passed = False
            confidence = 0.6
            details = {
                "issue": "too_many_outliers",
                "outliers": len(outliers),
                "total": len(values),
                "outlier_papers": [
                    papers_with_data[i].paper_id or f"paper_{i}" for i in outliers
                ],
            }
        else:
            passed = True
            confidence = 0.9 - (cv / 10)  # Decrease confidence with variation
            confidence = max(0.7, min(1.0, confidence))
            details = {
                "coefficient_of_variation": cv,
                "outliers": len(outliers),
                "total": len(values),
                "consistent": True,
            }

        return ConsistencyCheck(
            check_type="cross_paper",
            passed=passed,
            confidence=confidence,
            details=details,
        )

    def check_domain_consistency(
        self, paper: Paper, extraction: Dict[str, Any]
    ) -> ConsistencyCheck:
        """
        Check if extraction values are consistent with domain expectations.

        Args:
            paper: Paper being analyzed
            extraction: Extracted values

        Returns:
            ConsistencyCheck result
        """
        # Determine domain from paper
        domain = self._determine_domain(paper)

        if domain not in self.domain_ranges:
            return ConsistencyCheck(
                check_type="domain_specific",
                passed=True,
                confidence=0.7,
                details={"reason": "unknown_domain", "domain": domain},
            )

        expected_ranges = self.domain_ranges[domain]
        violations = []
        checks = []

        # Check each field against domain ranges
        for field, (min_val, max_val) in expected_ranges.items():
            if field in extraction and extraction[field] is not None:
                value = extraction[field]
                checks.append(field)

                if value < min_val or value > max_val:
                    violations.append(
                        {
                            "field": field,
                            "value": value,
                            "expected_range": (min_val, max_val),
                            "severity": "high"
                            if value < min_val / 10 or value > max_val * 10
                            else "medium",
                        }
                    )

        if not checks:
            return ConsistencyCheck(
                check_type="domain_specific",
                passed=True,
                confidence=0.5,
                details={"reason": "no_domain_fields_to_check"},
            )

        # Calculate pass/fail
        violation_rate = len(violations) / len(checks)
        passed = violation_rate < 0.3  # Allow up to 30% violations
        confidence = 1.0 - violation_rate

        return ConsistencyCheck(
            check_type="domain_specific",
            passed=passed,
            confidence=confidence,
            details={
                "domain": domain,
                "violations": violations,
                "checks_performed": len(checks),
                "violation_rate": violation_rate,
            },
        )

    def identify_outliers(
        self, values: List[float], context: Dict[str, Any]
    ) -> List[int]:
        """
        Statistical outlier detection.

        Args:
            values: List of numeric values
            context: Additional context (field name, domain, etc.)

        Returns:
            List of outlier indices
        """
        if len(values) < 3:
            return []

        values_array = np.array(values)

        # Method 1: Z-score
        z_scores = np.abs((values_array - np.mean(values_array)) / np.std(values_array))
        z_outliers = np.where(z_scores > self.outlier_z_score)[0]

        # Method 2: IQR
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        iqr_outliers = np.where(
            (values_array < lower_bound) | (values_array > upper_bound)
        )[0]

        # Combine both methods
        outliers = list(set(z_outliers) | set(iqr_outliers))

        # Context-specific adjustments
        field = context.get("field", "")
        if field in ["gpu_hours", "parameters"]:
            # These can have legitimate extreme values
            # Only flag if both methods agree
            outliers = list(set(z_outliers) & set(iqr_outliers))

        return outliers

    def _determine_domain(self, paper: Paper) -> str:
        """
        Determine paper domain from title and other metadata.

        Args:
            paper: Paper to analyze

        Returns:
            Domain string (nlp, cv, rl, or general)
        """
        if not hasattr(paper, "title") or not paper.title:
            return "general"

        title_lower = paper.title.lower()

        # Computer Vision indicators (check first for specificity)
        cv_terms = [
            "image",
            "vision",
            "visual",
            "video",
            "detection",
            "segmentation",
            "recognition",
            "cnn",
            "convolution",
            "resnet",
            "yolo",
        ]
        if any(term in title_lower for term in cv_terms):
            return "cv"

        # Reinforcement Learning indicators
        rl_terms = [
            "reinforcement",
            "rl",
            "agent",
            "environment",
            "reward",
            "policy",
            "q-learning",
            "actor-critic",
            "dqn",
            "ppo",
            "sac",
        ]
        if any(term in title_lower for term in rl_terms):
            return "rl"

        # NLP indicators
        nlp_terms = [
            "language",
            "text",
            "nlp",
            "transformer",
            "bert",
            "gpt",
            "translation",
            "summarization",
            "question answering",
            "dialogue",
            "chatbot",
        ]
        if any(term in title_lower for term in nlp_terms):
            return "nlp"

        return "general"

    def check_scaling_consistency(
        self, gpu_hours: Optional[float], parameters: Optional[float]
    ) -> ConsistencyCheck:
        """
        Check if GPU hours and parameters follow expected scaling laws.

        Args:
            gpu_hours: Total GPU hours used
            parameters: Model parameter count

        Returns:
            ConsistencyCheck result
        """
        if gpu_hours is None or parameters is None or gpu_hours <= 0 or parameters <= 0:
            return ConsistencyCheck(
                check_type="scaling_law",
                passed=True,
                confidence=0.5,
                details={"reason": "missing_data"},
            )

        # Expected: GPU hours ~ parameters^0.7
        scaling_info = self.scaling_laws["gpu_hours_vs_parameters"]
        expected_gpu_hours = parameters ** scaling_info["exponent"] / 1e6  # Normalize

        # Calculate ratio
        ratio = gpu_hours / expected_gpu_hours
        log_ratio = np.log10(ratio) if ratio > 0 else 0

        # Check if within reasonable bounds (less than 0.7 order of magnitude)
        if abs(log_ratio) > 0.7:
            passed = False
            confidence = 0.4
            details = {
                "issue": "scaling_law_violation",
                "expected_gpu_hours": expected_gpu_hours,
                "actual_gpu_hours": gpu_hours,
                "ratio": ratio,
                "log_ratio": log_ratio,
            }
        elif abs(log_ratio) > 1:
            passed = True
            confidence = 0.7
            details = {
                "issue": "minor_scaling_deviation",
                "expected_gpu_hours": expected_gpu_hours,
                "actual_gpu_hours": gpu_hours,
                "ratio": ratio,
            }
        else:
            passed = True
            confidence = 0.9
            details = {"follows_scaling_law": True, "ratio": ratio}

        return ConsistencyCheck(
            check_type="scaling_law",
            passed=passed,
            confidence=confidence,
            details=details,
        )
