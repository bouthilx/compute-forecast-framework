"""
Statistical outlier detection for extracted computational values.

This module provides multiple methods for identifying outliers in extraction results.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum

from compute_forecast.pipeline.metadata_collection.models import Paper


class OutlierMethod(Enum):
    """Available outlier detection methods."""

    Z_SCORE = "z_score"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    COMBINED = "combined"


@dataclass
class OutlierResult:
    """Result of outlier detection."""

    index: int
    value: float
    method: OutlierMethod
    score: float  # Outlier score (z-score, distance from bounds, etc.)
    reason: str


class OutlierDetector:
    """Statistical outlier detection for extracted values."""

    def __init__(self):
        """Initialize with default settings."""
        self.methods = ["z_score", "iqr", "isolation_forest"]
        self.z_threshold = 3.0
        self.iqr_multiplier = 1.5

        # Field-specific thresholds
        self.field_thresholds = {
            "gpu_hours": {
                "z_score": 3.5,  # More tolerant for GPU hours
                "iqr_multiplier": 2.0,
            },
            "parameters": {
                "z_score": 4.0,  # Even more tolerant for parameters
                "iqr_multiplier": 2.5,
            },
            "batch_size": {
                "z_score": 2.5,  # Stricter for batch size
                "iqr_multiplier": 1.5,
            },
        }

        # Known extreme but valid cases
        self.known_extremes = {
            "parameters": {
                "gpt3": 175e9,
                "palm": 540e9,
                "gpt4": 1.76e12,  # Estimated
            },
            "gpu_hours": {"gpt3": 3.64e6, "palm": 6e6},
        }

    def detect_outliers(
        self, values: List[float], method: str = "z_score", field: Optional[str] = None
    ) -> List[int]:
        """
        Detect outlier indices.

        Args:
            values: List of numeric values
            method: Detection method to use
            field: Optional field name for field-specific thresholds

        Returns:
            List of outlier indices
        """
        if len(values) < 3:
            return []

        values_array = np.array(values)

        if method == "z_score":
            return self._detect_z_score_outliers(values_array, field)
        elif method == "iqr":
            return self._detect_iqr_outliers(values_array, field)
        elif method == "isolation_forest":
            return self._detect_isolation_forest_outliers(values_array)
        elif method == "combined":
            return self._detect_combined_outliers(values_array, field)
        else:
            raise ValueError(f"Unknown method: {method}")

    def contextualize_outlier(
        self, paper: Paper, field: str, value: float
    ) -> Dict[str, Any]:
        """
        Provide context for why value might be outlier.

        Args:
            paper: Paper containing the outlier
            field: Field name
            value: Outlier value

        Returns:
            Context dictionary explaining the outlier
        """
        context: Dict[str, Any] = {
            "paper_id": paper.paper_id or "unknown",
            "field": field,
            "value": value,
            "reasons": [],
            "severity": "unknown",
        }

        # Check if it's a known extreme case
        is_known_extreme = False
        if field in self.known_extremes:
            for model_name, known_value in self.known_extremes[field].items():
                if (
                    abs(value - known_value) / known_value < 0.3
                ):  # Within 30% of known extreme
                    context["reasons"].append(f"Similar to known extreme: {model_name}")
                    context["severity"] = "expected"
                    is_known_extreme = True
                    break

        # Check paper characteristics
        if hasattr(paper, "title") and paper.title:
            title_lower = paper.title.lower()

            # Only check other indicators if not already a known extreme
            if not is_known_extreme:
                # Novel architecture indicators
                if any(
                    term in title_lower
                    for term in ["novel", "new", "introducing", "proposing"]
                ):
                    context["reasons"].append("Paper describes novel architecture")
                    if context["severity"] == "unknown":
                        context["severity"] = "possible"

                # Scale indicators
                if any(
                    term in title_lower
                    for term in ["large", "giant", "massive", "billion"]
                ):
                    context["reasons"].append("Paper explicitly mentions large scale")
                    if context["severity"] in ["unknown", "possible"]:
                        context["severity"] = "expected"

            # Efficiency indicators
            if any(
                term in title_lower
                for term in ["efficient", "lightweight", "tiny", "small"]
            ):
                if value > self._get_field_median(field) * 2:
                    context["reasons"].append("High value despite efficiency claims")
                    context["severity"] = "suspicious"

        # Check temporal context
        if hasattr(paper, "year") and paper.year:
            if field == "parameters" and paper.year < 2018 and value > 1e10:
                context["reasons"].append(f"Unusually large for {paper.year}")
                context["severity"] = "suspicious"
            elif field == "gpu_hours" and paper.year < 2015 and value > 1e5:
                context["reasons"].append(f"Very high GPU hours for {paper.year}")
                context["severity"] = "suspicious"

        # Check if it's a breakthrough paper
        if hasattr(paper, "citations") and paper.citations:
            if paper.citations > 1000:
                context["reasons"].append("Highly cited paper - might be breakthrough")
                # Only update severity if not already determined to be expected
                if context["severity"] not in ["expected", "suspicious"]:
                    context["severity"] = "possible"

        # If no specific reasons found
        if not context["reasons"]:
            context["reasons"].append("No specific context identified")
            context["severity"] = "unknown"

        return context

    def verify_outlier(
        self, paper: Paper, extraction: Dict[str, Any], field: str, value: float
    ) -> bool:
        """
        Manual verification prompt for outliers.

        Args:
            paper: Paper being analyzed
            extraction: Full extraction results
            field: Field containing outlier
            value: Outlier value

        Returns:
            Boolean indicating if outlier should be kept
        """
        # Get context
        context = self.contextualize_outlier(paper, field, value)

        # Always check corroborating evidence for extreme values
        if field in ["parameters", "gpu_hours", "batch_size"]:
            has_evidence = self._check_corroborating_evidence(
                paper, extraction, field, value
            )
            if not has_evidence:
                return False  # Reject outlier without corroborating evidence

        # Auto-verify based on severity
        if context["severity"] == "expected":
            return True  # Keep the outlier
        elif context["severity"] == "suspicious":
            return False  # Already checked corroborating evidence above
        else:
            # For unknown cases, check against other fields
            return self._check_field_consistency(extraction, field, value)

    def _detect_z_score_outliers(
        self, values: np.ndarray, field: Optional[str] = None
    ) -> List[int]:
        """Detect outliers using z-score method."""
        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return []

        # Get threshold for this field
        threshold = self.z_threshold
        if field and field in self.field_thresholds:
            threshold = self.field_thresholds[field].get("z_score", self.z_threshold)

        z_scores = np.abs((values - mean) / std)
        outliers = np.where(z_scores > threshold)[0]

        return list(map(int, outliers.tolist()))

    def _detect_iqr_outliers(
        self, values: np.ndarray, field: Optional[str] = None
    ) -> List[int]:
        """Detect outliers using IQR method."""
        if len(values) < 4:
            return []

        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1

        if iqr == 0:
            return self._detect_z_score_outliers(values, field)

        # Get multiplier for this field
        multiplier = self.iqr_multiplier
        if field and field in self.field_thresholds:
            multiplier = self.field_thresholds[field].get(
                "iqr_multiplier", self.iqr_multiplier
            )

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        outliers = np.where((values < lower_bound) | (values > upper_bound))[0]

        return list(map(int, outliers.tolist()))

    def _detect_isolation_forest_outliers(self, values: np.ndarray) -> List[int]:
        """
        Detect outliers using Isolation Forest method.
        Note: Simplified implementation without sklearn dependency.
        """
        if len(values) < 10:
            # Fall back to IQR for small datasets
            return self._detect_iqr_outliers(values)

        # Simple approximation of isolation forest
        # Use distance from median as proxy
        median = np.median(values)
        mad = np.median(np.abs(values - median))  # Median absolute deviation

        if mad == 0:
            return []

        # Modified z-score using MAD
        modified_z_scores = 0.6745 * (values - median) / mad
        outliers = np.where(np.abs(modified_z_scores) > 3.5)[0]

        return list(map(int, outliers.tolist()))

    def _detect_combined_outliers(
        self, values: np.ndarray, field: Optional[str] = None
    ) -> List[int]:
        """Combine multiple methods for robust outlier detection."""
        z_outliers = set(self._detect_z_score_outliers(values, field))
        iqr_outliers = set(self._detect_iqr_outliers(values, field))
        iso_outliers = set(self._detect_isolation_forest_outliers(values))

        # An index is an outlier if detected by at least 2 methods
        all_candidates = z_outliers | iqr_outliers | iso_outliers
        outliers = []

        for idx in all_candidates:
            count = 0
            if idx in z_outliers:
                count += 1
            if idx in iqr_outliers:
                count += 1
            if idx in iso_outliers:
                count += 1

            if count >= 2:
                outliers.append(idx)

        return sorted(outliers)

    def _check_corroborating_evidence(
        self, paper: Paper, extraction: Dict[str, Any], field: str, value: float
    ) -> bool:
        """Check if other fields support the outlier value."""
        # High parameters should correlate with high GPU hours
        if field == "parameters" and value > 1e10:
            gpu_hours = extraction.get("gpu_hours", 0)
            if gpu_hours < 1000:  # Suspiciously low
                return False

        # High GPU hours should correlate with either high parameters or long training
        if field == "gpu_hours" and value > 1e5:
            parameters = extraction.get("parameters", 0)
            training_time = extraction.get("training_time", 0)
            if parameters < 1e8 and training_time < 100:
                return False

        # Large batch sizes should correlate with high GPU memory
        if field == "batch_size" and value > 1000:
            gpu_memory = extraction.get("gpu_memory", 0)
            if gpu_memory < 16:  # Less than 16GB
                return False

        return True

    def _check_field_consistency(
        self, extraction: Dict[str, Any], field: str, value: float
    ) -> bool:
        """Check if the outlier is consistent with other extracted fields."""
        # GPU hours consistency check
        if field == "gpu_hours":
            gpu_count = extraction.get("gpu_count", 1)
            training_time = extraction.get("training_time", 0)

            if gpu_count > 0 and training_time > 0:
                expected_gpu_hours = gpu_count * training_time
                if abs(value - expected_gpu_hours) / expected_gpu_hours > 0.5:
                    return False

        # Parameter count consistency
        if field == "parameters":
            model_size_gb = extraction.get("model_size_gb", 0)
            if model_size_gb > 0:
                # Rough estimate: 1B parameters ≈ 4GB (float32)
                expected_params = model_size_gb * 0.25e9
                if abs(value - expected_params) / expected_params > 1.0:
                    return False

        return True

    def _get_field_median(self, field: str) -> float:
        """Get typical median value for a field."""
        # These are rough estimates based on common values
        field_medians = {
            "gpu_hours": 1000,
            "parameters": 1e8,
            "training_time": 24,
            "batch_size": 32,
            "gpu_count": 8,
            "epochs": 100,
            "gpu_memory": 32,
        }
        return field_medians.get(field, 1.0)

    def analyze_outlier_pattern(
        self, outliers: List[OutlierResult], papers: List[Paper]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in detected outliers.

        Args:
            outliers: List of detected outliers
            papers: Corresponding papers

        Returns:
            Pattern analysis results
        """
        if not outliers:
            return {"no_outliers": True}

        # Group by field
        outliers_by_field: Dict[str, List[Any]] = {}
        for outlier in outliers:
            field = getattr(outlier, "field", "unknown")
            if field not in outliers_by_field:
                outliers_by_field[field] = []
            outliers_by_field[field].append(outlier)

        # Analyze temporal patterns
        temporal_patterns = {}
        for field, field_outliers in outliers_by_field.items():
            years = []
            for outlier in field_outliers:
                if outlier.index < len(papers):
                    paper = papers[outlier.index]
                    if hasattr(paper, "year") and paper.year:
                        years.append(paper.year)

            if years:
                temporal_patterns[field] = {
                    "min_year": min(years),
                    "max_year": max(years),
                    "concentration": "recent"
                    if np.mean(years) > 2020
                    else "historical",
                }

        return {
            "outliers_by_field": {k: len(v) for k, v in outliers_by_field.items()},
            "temporal_patterns": temporal_patterns,
            "total_outliers": len(outliers),
            "outlier_rate": len(outliers) / len(papers) if papers else 0,
        }
