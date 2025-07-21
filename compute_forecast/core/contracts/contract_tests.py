"""
Contract testing framework for validation testing.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    Author,
)
from .base_contracts import ContractViolation, ContractViolationType, AnalysisContract
from .analysis_contracts import (
    ComputationalAnalysisContract,
    PaperMetadataContract,
    ResourceMetricsContract,
)


@dataclass
class ContractTestCase:
    """Test case for contract validation."""

    name: str
    description: str
    input_data: Any
    expected_violations: List[ContractViolation]
    expected_passed: bool
    contract_type: str
    tags: List[str] = field(default_factory=list)


@dataclass
class ContractTestResult:
    """Result of a contract test case."""

    test_case: ContractTestCase
    actual_violations: List[ContractViolation]
    passed: bool
    execution_time_ms: float
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Test succeeded if results match expectations."""
        if self.error:
            return False

        # Check if pass/fail status matches
        if self.passed != self.test_case.expected_passed:
            return False

        # Check if violation counts match
        if len(self.actual_violations) != len(self.test_case.expected_violations):
            return False

        # Check if violation types match
        expected_types = {v.violation_type for v in self.test_case.expected_violations}
        actual_types = {v.violation_type for v in self.actual_violations}

        return expected_types == actual_types


class ContractTestSuite:
    """Suite of contract validation tests."""

    def __init__(self):
        self.test_cases: List[ContractTestCase] = []
        self.contracts: Dict[str, AnalysisContract] = {
            "computational_analysis": ComputationalAnalysisContract(),
            "paper_metadata": PaperMetadataContract(),
            "resource_metrics": ResourceMetricsContract(),
        }
        self.load_default_tests()

    def load_default_tests(self) -> None:
        """Load default test cases."""
        # Paper metadata tests
        self._add_paper_metadata_tests()

        # Computational analysis tests
        self._add_computational_analysis_tests()

        # Resource metrics tests
        self._add_resource_metrics_tests()

    def _add_paper_metadata_tests(self) -> None:
        """Add paper metadata contract tests."""
        # Valid paper
        self.add_test_case(
            ContractTestCase(
                name="valid_paper",
                description="Valid paper with all required fields",
                input_data=Paper(
                    paper_id="123",
                    title="Test Paper",
                    authors=[Author(name="Test Author", affiliations=["Test Uni"])],
                    venue="ICML",
                    year=2024,
                    abstracts=[],
                    citations=[],
                ),
                expected_violations=[],
                expected_passed=True,
                contract_type="paper_metadata",
                tags=["valid", "complete"],
            )
        )

        # Missing title
        self.add_test_case(
            ContractTestCase(
                name="missing_title",
                description="Paper missing required title field",
                input_data={
                    "authors": [{"name": "Test Author"}],
                    "venue": "ICML",
                    "year": 2024,
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
                        field_name="title",
                        expected="non-null value",
                        actual=None,
                        severity="error",
                        message="Required field 'title' is missing or null",
                    )
                ],
                expected_passed=False,
                contract_type="paper_metadata",
                tags=["invalid", "missing_field"],
            )
        )

        # Empty authors
        self.add_test_case(
            ContractTestCase(
                name="empty_authors",
                description="Paper with empty authors list",
                input_data={
                    "title": "Test Paper",
                    "authors": [],
                    "venue": "ICML",
                    "year": 2024,
                    "paper_id": "123",
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                        field_name="authors",
                        expected="non-empty list",
                        actual="empty list",
                        severity="error",
                        message="Paper must have at least one author",
                    )
                ],
                expected_passed=False,
                contract_type="paper_metadata",
                tags=["invalid", "business_rule"],
            )
        )

        # Invalid year
        self.add_test_case(
            ContractTestCase(
                name="invalid_year",
                description="Paper with year outside valid range",
                input_data={
                    "title": "Test Paper",
                    "authors": [{"name": "Test Author"}],
                    "venue": "ICML",
                    "year": 2018,
                    "paper_id": "123",
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.OUT_OF_RANGE,
                        field_name="year",
                        expected=f"[2019, {datetime.now().year}]",
                        actual=2018,
                        severity="error",
                        message=f"Year 2018 is outside valid range [2019, {datetime.now().year}]",
                    )
                ],
                expected_passed=False,
                contract_type="paper_metadata",
                tags=["invalid", "out_of_range"],
            )
        )

        # No identifiers
        self.add_test_case(
            ContractTestCase(
                name="no_identifiers",
                description="Paper without any identifiers",
                input_data={
                    "title": "Test Paper",
                    "authors": [{"name": "Test Author"}],
                    "venue": "ICML",
                    "year": 2024,
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                        field_name="identifiers",
                        expected="at least one identifier",
                        actual="no identifiers",
                        severity="error",
                        message="Paper must have at least one identifier (paper_id, openalex_id, or arxiv_id)",
                    )
                ],
                expected_passed=False,
                contract_type="paper_metadata",
                tags=["invalid", "missing_identifier"],
            )
        )

    def _add_computational_analysis_tests(self) -> None:
        """Add computational analysis contract tests."""
        # Valid analysis
        self.add_test_case(
            ContractTestCase(
                name="valid_analysis",
                description="Valid computational analysis",
                input_data=ComputationalAnalysis(
                    computational_richness=0.8,
                    confidence_score=0.9,
                    keyword_matches={"gpu": 5, "training": 3},
                    resource_metrics={"gpu_count": 4, "gpu_type": "V100"},
                    experimental_indicators={},
                ),
                expected_violations=[],
                expected_passed=True,
                contract_type="computational_analysis",
                tags=["valid"],
            )
        )

        # Out of range richness
        self.add_test_case(
            ContractTestCase(
                name="invalid_richness",
                description="Richness score out of range",
                input_data={
                    "computational_richness": 1.5,
                    "confidence_score": 0.9,
                    "keyword_matches": {},
                    "resource_metrics": {},
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.OUT_OF_RANGE,
                        field_name="computational_richness",
                        expected="[0.0, 1.0]",
                        actual=1.5,
                        severity="error",
                        message="Field 'computational_richness' value 1.5 is out of range [0.0, 1.0]",
                    )
                ],
                expected_passed=False,
                contract_type="computational_analysis",
                tags=["invalid", "out_of_range"],
            )
        )

        # Low confidence warning
        self.add_test_case(
            ContractTestCase(
                name="low_confidence",
                description="Low confidence score triggers warning",
                input_data={
                    "computational_richness": 0.5,
                    "confidence_score": 0.2,
                    "keyword_matches": {},
                    "resource_metrics": {},
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                        field_name="confidence_score",
                        expected=">= 0.3",
                        actual=0.2,
                        severity="warning",
                        message="Confidence score 0.2 below recommended threshold",
                    )
                ],
                expected_passed=True,  # Warnings don't fail validation
                contract_type="computational_analysis",
                tags=["warning", "low_confidence"],
            )
        )

        # Inconsistent GPU data
        self.add_test_case(
            ContractTestCase(
                name="gpu_inconsistency",
                description="GPU count without GPU type",
                input_data={
                    "computational_richness": 0.8,
                    "confidence_score": 0.9,
                    "keyword_matches": {},
                    "resource_metrics": {"gpu_count": 8},
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.INCONSISTENT_DATA,
                        field_name="resource_metrics.gpu_type",
                        expected="gpu_type when gpu_count present",
                        actual=None,
                        severity="warning",
                        message="GPU type should be specified when GPU count is present",
                    )
                ],
                expected_passed=True,  # Warnings don't fail validation
                contract_type="computational_analysis",
                tags=["warning", "inconsistent"],
            )
        )

    def _add_resource_metrics_tests(self) -> None:
        """Add resource metrics contract tests."""
        # Valid metrics
        self.add_test_case(
            ContractTestCase(
                name="valid_metrics",
                description="Valid resource metrics",
                input_data={
                    "gpu_count": 4,
                    "gpu_memory_gb": 32,
                    "training_time_hours": 48.5,
                    "model_parameters": 175000000000,
                },
                expected_violations=[],
                expected_passed=True,
                contract_type="resource_metrics",
                tags=["valid"],
            )
        )

        # Negative values
        self.add_test_case(
            ContractTestCase(
                name="negative_gpu_count",
                description="Negative GPU count",
                input_data={"gpu_count": -2, "training_time_hours": 10},
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.OUT_OF_RANGE,
                        field_name="resource_metrics.gpu_count",
                        expected="non-negative value",
                        actual=-2,
                        severity="error",
                        message="GPU count cannot be negative",
                    )
                ],
                expected_passed=False,
                contract_type="resource_metrics",
                tags=["invalid", "negative_value"],
            )
        )

        # Too many metrics warning
        self.add_test_case(
            ContractTestCase(
                name="excessive_metrics",
                description="Too many resource metrics",
                input_data={
                    **{f"metric_{i}": i for i in range(60)}  # 60 metrics
                },
                expected_violations=[
                    ContractViolation(
                        violation_type=ContractViolationType.PERFORMANCE_VIOLATION,
                        field_name="resource_metrics",
                        expected="<= 50 metrics",
                        actual="60 metrics",
                        severity="warning",
                        message="Too many resource metrics (60), may impact performance",
                    )
                ],
                expected_passed=True,  # Warning only
                contract_type="resource_metrics",
                tags=["warning", "performance"],
            )
        )

    def add_test_case(self, test_case: ContractTestCase) -> None:
        """Add test case to suite."""
        self.test_cases.append(test_case)

    def run_test(self, test_case: ContractTestCase) -> ContractTestResult:
        """Run single test case."""
        import time

        start_time = time.time()

        try:
            # Get appropriate contract
            contract = self.contracts.get(test_case.contract_type)
            if not contract:
                return ContractTestResult(
                    test_case=test_case,
                    actual_violations=[],
                    passed=False,
                    execution_time_ms=0.0,
                    error=f"Unknown contract type: {test_case.contract_type}",
                )

            # Run validation
            violations = contract.validate(test_case.input_data)

            # Separate errors from warnings
            errors = [v for v in violations if v.severity == "error"]
            passed = len(errors) == 0

            execution_time = (time.time() - start_time) * 1000

            return ContractTestResult(
                test_case=test_case,
                actual_violations=violations,
                passed=passed,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ContractTestResult(
                test_case=test_case,
                actual_violations=[],
                passed=False,
                execution_time_ms=execution_time,
                error=str(e),
            )

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all contract validation tests."""
        results: Dict[str, Any] = {
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "results": [],
            "failures": [],
            "execution_time_ms": 0.0,
        }

        for test_case in self.test_cases:
            result = self.run_test(test_case)
            results["results"].append(result)
            results["execution_time_ms"] += float(result.execution_time_ms)

            if result.error:
                results["errors"] += int(1)
                results["failures"].append(
                    {"test": test_case.name, "error": result.error}
                )
            elif result.success:
                results["passed"] += int(1)
            else:
                results["failed"] += int(1)
                results["failures"].append(
                    {
                        "test": test_case.name,
                        "expected_violations": len(test_case.expected_violations),
                        "actual_violations": len(result.actual_violations),
                        "expected_passed": test_case.expected_passed,
                        "actual_passed": result.passed,
                    }
                )

        results["success_rate"] = (
            results["passed"] / results["total_tests"]
            if results["total_tests"] > 0
            else 0.0
        )

        return results

    def run_tests_by_tag(self, tag: str) -> Dict[str, Any]:
        """Run tests matching a specific tag."""
        matching_tests = [tc for tc in self.test_cases if tag in tc.tags]

        if not matching_tests:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "results": [],
                "tag": tag,
            }

        # Temporarily swap test cases
        original_tests = self.test_cases
        self.test_cases = matching_tests

        results = self.run_all_tests()
        results["tag"] = tag

        # Restore original tests
        self.test_cases = original_tests

        return results
