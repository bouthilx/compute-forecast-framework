"""
Specific contract implementations for analysis pipeline components.
"""

from typing import List, Any
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
)
from .base_contracts import (
    BaseContract,
    ContractViolation,
    ContractViolationType,
)


class ComputationalAnalysisContract(BaseContract):
    """Contract for computational analysis outputs."""

    def __init__(self):
        super().__init__("computational_analysis")
        self._required_fields = [
            "computational_richness",
            "confidence_score",
            "keyword_matches",
            "resource_metrics",
        ]
        self._performance_requirements = {
            "max_processing_time_ms": 1000.0,  # 1 second max
            "min_confidence_threshold": 0.3,
        }

    def validate(self, data: Any) -> List[ContractViolation]:
        """Validate computational analysis data."""
        violations = []

        # Handle both dict and ComputationalAnalysis object
        if isinstance(data, ComputationalAnalysis):
            analysis_data = {
                "computational_richness": data.computational_richness,
                "confidence_score": data.confidence_score,
                "keyword_matches": data.keyword_matches,
                "resource_metrics": data.resource_metrics,
                "experimental_indicators": data.experimental_indicators,
            }
        elif isinstance(data, dict):
            analysis_data = data
        else:
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.INVALID_TYPE,
                    field_name="data",
                    expected="ComputationalAnalysis or dict",
                    actual=type(data).__name__,
                    severity="error",
                    message="Data must be ComputationalAnalysis object or dict",
                )
            )
            return violations

        # Check required fields
        violations.extend(self._check_required_fields(analysis_data))

        # Validate computational richness
        if "computational_richness" in analysis_data:
            richness = analysis_data["computational_richness"]
            if isinstance(richness, (int, float)):
                range_violation = self._check_range(
                    float(richness), 0.0, 1.0, "computational_richness"
                )
                if range_violation:
                    violations.append(range_violation)
            else:
                violation = self._check_type(richness, float, "computational_richness")
                if violation:
                    violations.append(violation)

        # Validate confidence score
        if "confidence_score" in analysis_data:
            confidence = analysis_data["confidence_score"]
            if isinstance(confidence, (int, float)):
                range_violation = self._check_range(
                    float(confidence), 0.0, 1.0, "confidence_score"
                )
                if range_violation:
                    violations.append(range_violation)

                # Check minimum confidence threshold
                if (
                    float(confidence)
                    < self._performance_requirements["min_confidence_threshold"]
                ):
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                            field_name="confidence_score",
                            expected=f">= {self._performance_requirements['min_confidence_threshold']}",
                            actual=confidence,
                            severity="warning",
                            message=f"Confidence score {confidence} below recommended threshold",
                        )
                    )
            else:
                violation = self._check_type(confidence, float, "confidence_score")
                if violation:
                    violations.append(violation)

        # Validate keyword matches
        if "keyword_matches" in analysis_data:
            keyword_matches = analysis_data["keyword_matches"]
            if not isinstance(keyword_matches, dict):
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_TYPE,
                        field_name="keyword_matches",
                        expected="dict",
                        actual=type(keyword_matches).__name__,
                        severity="error",
                        message="keyword_matches must be a dictionary",
                    )
                )
            else:
                # Validate keyword match values are non-negative integers
                for keyword, count in keyword_matches.items():
                    if not isinstance(count, int) or count < 0:
                        violations.append(
                            ContractViolation(
                                violation_type=ContractViolationType.INVALID_TYPE,
                                field_name=f"keyword_matches.{keyword}",
                                expected="non-negative integer",
                                actual=count,
                                severity="error",
                                message=f"Keyword count for '{keyword}' must be non-negative integer",
                            )
                        )

        # Validate resource metrics consistency
        if "resource_metrics" in analysis_data:
            resource_metrics = analysis_data["resource_metrics"]
            if not isinstance(resource_metrics, dict):
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_TYPE,
                        field_name="resource_metrics",
                        expected="dict",
                        actual=type(resource_metrics).__name__,
                        severity="error",
                        message="resource_metrics must be a dictionary",
                    )
                )
            else:
                # Check GPU consistency
                if resource_metrics.get("gpu_count") and not resource_metrics.get(
                    "gpu_type"
                ):
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.INCONSISTENT_DATA,
                            field_name="resource_metrics.gpu_type",
                            expected="gpu_type when gpu_count present",
                            actual=None,
                            severity="warning",
                            message="GPU type should be specified when GPU count is present",
                        )
                    )

                # Check for negative values
                for metric, value in resource_metrics.items():
                    if isinstance(value, (int, float)) and value < 0:
                        violations.append(
                            ContractViolation(
                                violation_type=ContractViolationType.OUT_OF_RANGE,
                                field_name=f"resource_metrics.{metric}",
                                expected="non-negative value",
                                actual=value,
                                severity="error",
                                message=f"Resource metric '{metric}' cannot be negative",
                            )
                        )

        return violations


class PaperMetadataContract(BaseContract):
    """Contract for paper metadata requirements."""

    def __init__(self):
        super().__init__("paper_metadata")
        self._required_fields = ["title", "authors", "year", "venue"]
        self._optional_fields = [
            "abstract",
            "doi",
            "citations",
            "keywords",
            "paper_id",
            "openalex_id",
            "arxiv_id",
        ]
        self._performance_requirements = {
            "max_validation_time_ms": 100.0,
        }

    def validate(self, data: Any) -> List[ContractViolation]:
        """Validate paper metadata."""
        violations = []

        # Handle both dict and Paper object
        if isinstance(data, Paper):
            paper_data = {
                "title": data.title,
                "authors": data.authors,
                "year": data.year,
                "venue": data.venue,
                "citations": data.citations,
                "abstract": data.abstract,
                "paper_id": data.paper_id,
                "openalex_id": data.openalex_id,
                "arxiv_id": data.arxiv_id,
            }
        elif isinstance(data, dict):
            paper_data = data
        else:
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.INVALID_TYPE,
                    field_name="data",
                    expected="Paper or dict",
                    actual=type(data).__name__,
                    severity="error",
                    message="Data must be Paper object or dict",
                )
            )
            return violations

        # Check required fields
        violations.extend(self._check_required_fields(paper_data))

        # Validate title
        if "title" in paper_data:
            title = paper_data["title"]
            if isinstance(title, str):
                if not title.strip():
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                            field_name="title",
                            expected="non-empty string",
                            actual="empty/whitespace",
                            severity="error",
                            message="Title cannot be empty or only whitespace",
                        )
                    )
            else:
                violation = self._check_type(title, str, "title")
                if violation:
                    violations.append(violation)

        # Validate authors
        if "authors" in paper_data:
            authors = paper_data["authors"]
            if not isinstance(authors, list):
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_TYPE,
                        field_name="authors",
                        expected="list",
                        actual=type(authors).__name__,
                        severity="error",
                        message="Authors must be a list",
                    )
                )
            elif len(authors) == 0:
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                        field_name="authors",
                        expected="non-empty list",
                        actual="empty list",
                        severity="error",
                        message="Paper must have at least one author",
                    )
                )

        # Validate year
        if "year" in paper_data:
            year = paper_data["year"]
            if isinstance(year, int):
                current_year = datetime.now().year
                if year < 2019 or year > current_year:
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.OUT_OF_RANGE,
                            field_name="year",
                            expected=f"[2019, {current_year}]",
                            actual=year,
                            severity="error",
                            message=f"Year {year} is outside valid range [2019, {current_year}]",
                        )
                    )
            else:
                violation = self._check_type(year, int, "year")
                if violation:
                    violations.append(violation)

        # Validate venue
        if "venue" in paper_data:
            venue = paper_data["venue"]
            if isinstance(venue, str):
                if not venue.strip():
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                            field_name="venue",
                            expected="non-empty string",
                            actual="empty/whitespace",
                            severity="error",
                            message="Venue cannot be empty or only whitespace",
                        )
                    )
            else:
                violation = self._check_type(venue, str, "venue")
                if violation:
                    violations.append(violation)

        # Validate citations if present
        if "citations" in paper_data and paper_data["citations"] is not None:
            citations = paper_data["citations"]
            if isinstance(citations, int):
                if citations < 0:
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.OUT_OF_RANGE,
                            field_name="citations",
                            expected="non-negative integer",
                            actual=citations,
                            severity="error",
                            message="Citation count cannot be negative",
                        )
                    )
            else:
                violation = self._check_type(citations, int, "citations")
                if violation:
                    violations.append(violation)

        # Validate at least one identifier is present
        identifiers = ["paper_id", "openalex_id", "arxiv_id"]
        has_identifier = any(
            paper_data.get(id_field) is not None for id_field in identifiers
        )

        if not has_identifier:
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                    field_name="identifiers",
                    expected="at least one identifier",
                    actual="no identifiers",
                    severity="error",
                    message="Paper must have at least one identifier (paper_id, openalex_id, or arxiv_id)",
                )
            )

        return violations


class ResourceMetricsContract(BaseContract):
    """Contract specifically for resource metrics validation."""

    def __init__(self):
        super().__init__("resource_metrics")
        self._required_fields = []  # Resource metrics are flexible
        self._performance_requirements = {
            "max_metric_count": 50,  # Prevent excessive metrics
        }

    def validate(self, data: Any) -> List[ContractViolation]:
        """Validate resource metrics structure."""
        violations = []

        if not isinstance(data, dict):
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.INVALID_TYPE,
                    field_name="resource_metrics",
                    expected="dict",
                    actual=type(data).__name__,
                    severity="error",
                    message="Resource metrics must be a dictionary",
                )
            )
            return violations

        # Check metric count
        if len(data) > self._performance_requirements["max_metric_count"]:
            violations.append(
                ContractViolation(
                    violation_type=ContractViolationType.PERFORMANCE_VIOLATION,
                    field_name="resource_metrics",
                    expected=f"<= {self._performance_requirements['max_metric_count']} metrics",
                    actual=f"{len(data)} metrics",
                    severity="warning",
                    message=f"Too many resource metrics ({len(data)}), may impact performance",
                )
            )

        # Validate common resource patterns
        for key, value in data.items():
            # Check for valid metric names
            if not isinstance(key, str):
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_TYPE,
                        field_name=f"resource_metrics.{key}",
                        expected="string key",
                        actual=type(key).__name__,
                        severity="error",
                        message="Resource metric keys must be strings",
                    )
                )
                continue

            if not key.strip():
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INVALID_TYPE,
                        field_name=f"resource_metrics.{repr(key)}",
                        expected="non-empty string key",
                        actual=repr(key),
                        severity="error",
                        message="Resource metric keys must be non-empty strings",
                    )
                )
                continue

            # GPU-related validations
            if "gpu" in key.lower():
                if isinstance(value, (int, float)) and value < 0:
                    if "count" in key:
                        violations.append(
                            ContractViolation(
                                violation_type=ContractViolationType.OUT_OF_RANGE,
                                field_name=f"resource_metrics.{key}",
                                expected="non-negative value",
                                actual=value,
                                severity="error",
                                message="GPU count cannot be negative",
                            )
                        )
                    elif "memory" in key:
                        violations.append(
                            ContractViolation(
                                violation_type=ContractViolationType.OUT_OF_RANGE,
                                field_name=f"resource_metrics.{key}",
                                expected="non-negative value",
                                actual=value,
                                severity="error",
                                message="GPU memory cannot be negative",
                            )
                        )
                    else:
                        # Generic GPU-related negative value
                        violations.append(
                            ContractViolation(
                                violation_type=ContractViolationType.OUT_OF_RANGE,
                                field_name=f"resource_metrics.{key}",
                                expected="non-negative value",
                                actual=value,
                                severity="error",
                                message="GPU-related metric cannot be negative",
                            )
                        )

            # Memory validations (non-GPU)
            elif (
                "memory" in key.lower()
                and isinstance(value, (int, float))
                and value < 0
            ):
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.OUT_OF_RANGE,
                        field_name=f"resource_metrics.{key}",
                        expected="non-negative value",
                        actual=value,
                        severity="error",
                        message="Memory values cannot be negative",
                    )
                )

            # Training time validations
            elif "time" in key.lower() or "duration" in key.lower():
                if isinstance(value, (int, float)) and value < 0:
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.OUT_OF_RANGE,
                            field_name=f"resource_metrics.{key}",
                            expected="non-negative value",
                            actual=value,
                            severity="error",
                            message="Time/duration values cannot be negative",
                        )
                    )

            # Model size validations
            elif "size" in key.lower() or "parameters" in key.lower():
                if isinstance(value, (int, float)) and value < 0:
                    violations.append(
                        ContractViolation(
                            violation_type=ContractViolationType.OUT_OF_RANGE,
                            field_name=f"resource_metrics.{key}",
                            expected="non-negative value",
                            actual=value,
                            severity="error",
                            message="Size/parameter values cannot be negative",
                        )
                    )

        return violations
