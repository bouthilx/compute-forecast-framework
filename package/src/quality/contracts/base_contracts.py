"""
Base classes and protocols for contract validation.
Defines the core structures for interface contract validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
from enum import Enum


class ContractViolationType(Enum):
    """Types of contract violations that can occur."""

    MISSING_REQUIRED_FIELD = "missing_required"
    INVALID_TYPE = "invalid_type"
    OUT_OF_RANGE = "out_of_range"
    INCONSISTENT_DATA = "inconsistent_data"
    INVALID_REFERENCE = "invalid_reference"
    SCHEMA_MISMATCH = "schema_mismatch"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    PERFORMANCE_VIOLATION = "performance_violation"


@dataclass
class ContractViolation:
    """Represents a single contract violation."""

    violation_type: ContractViolationType
    field_name: str
    expected: Any
    actual: Any
    severity: str  # "error", "warning", "info"
    message: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class ContractValidationResult:
    """Result of contract validation."""

    contract_name: str
    passed: bool
    violations: List[ContractViolation] = field(default_factory=list)
    warnings: List[ContractViolation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        """Count of error-level violations."""
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-level violations."""
        return len(self.warnings)

    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level violations."""
        return self.error_count > 0


@runtime_checkable
class AnalysisContract(Protocol):
    """Protocol defining analysis output requirements."""

    @property
    def contract_name(self) -> str:
        """Name of this contract."""
        ...

    def validate(self, data: Any) -> List[ContractViolation]:
        """
        Validate data against this contract.

        Args:
            data: Data to validate

        Returns:
            List of violations found (empty if valid)
        """
        ...

    def get_required_fields(self) -> List[str]:
        """Get list of required fields for this contract."""
        ...

    def get_performance_requirements(self) -> Dict[str, float]:
        """Get performance requirements (e.g., max processing time)."""
        ...


class BaseContract:
    """Base implementation for contracts with common functionality."""

    def __init__(self, contract_name: str):
        self._contract_name = contract_name
        self._required_fields: List[str] = []
        self._optional_fields: List[str] = []
        self._performance_requirements: Dict[str, float] = {}

    @property
    def contract_name(self) -> str:
        return self._contract_name

    def get_required_fields(self) -> List[str]:
        return self._required_fields.copy()

    def get_performance_requirements(self) -> Dict[str, float]:
        return self._performance_requirements.copy()

    def _check_required_fields(self, data: Dict[str, Any]) -> List[ContractViolation]:
        """Check that all required fields are present."""
        violations = []

        for field_name in self._required_fields:
            if field_name not in data or data[field_name] is None:
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
                        field_name=field_name,
                        expected="non-null value",
                        actual=data.get(field_name),
                        severity="error",
                        message=f"Required field '{field_name}' is missing or null",
                    )
                )

        return violations

    def _check_type(
        self, value: Any, expected_type: type, field_name: str
    ) -> Optional[ContractViolation]:
        """Check if a value matches the expected type."""
        if not isinstance(value, expected_type):
            return ContractViolation(
                violation_type=ContractViolationType.INVALID_TYPE,
                field_name=field_name,
                expected=expected_type.__name__,
                actual=type(value).__name__,
                severity="error",
                message=f"Field '{field_name}' has invalid type",
            )
        return None

    def _check_range(
        self, value: float, min_val: float, max_val: float, field_name: str
    ) -> Optional[ContractViolation]:
        """Check if a numeric value is within the expected range."""
        if not (min_val <= value <= max_val):
            return ContractViolation(
                violation_type=ContractViolationType.OUT_OF_RANGE,
                field_name=field_name,
                expected=f"[{min_val}, {max_val}]",
                actual=value,
                severity="error",
                message=f"Field '{field_name}' value {value} is out of range [{min_val}, {max_val}]",
            )
        return None


@dataclass
class StageTransitionContract:
    """Contract for data transitions between pipeline stages."""

    from_stage: str
    to_stage: str
    required_fields: List[str]
    transformations: Dict[str, str]  # field mappings
    validation_rules: List[str]

    def validate_transition(
        self, input_data: Dict[str, Any], output_data: Dict[str, Any]
    ) -> List[ContractViolation]:
        """Validate data transition between stages."""
        violations = []

        # Check required fields in output
        for field_name in self.required_fields:
            if field_name not in output_data:
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
                        field_name=field_name,
                        expected="field present in output",
                        actual="missing",
                        severity="error",
                        message=f"Required field '{field_name}' missing in {self.to_stage} output",
                        context={
                            "from_stage": self.from_stage,
                            "to_stage": self.to_stage,
                        },
                    )
                )

        # Validate transformations
        for input_field, output_field in self.transformations.items():
            if input_field in input_data and output_field not in output_data:
                violations.append(
                    ContractViolation(
                        violation_type=ContractViolationType.INCONSISTENT_DATA,
                        field_name=output_field,
                        expected=f"transformed from {input_field}",
                        actual="missing",
                        severity="error",
                        message=f"Expected transformation from '{input_field}' to '{output_field}' not found",
                        context={
                            "from_stage": self.from_stage,
                            "to_stage": self.to_stage,
                        },
                    )
                )

        return violations
