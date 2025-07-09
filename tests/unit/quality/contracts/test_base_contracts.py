"""Unit tests for base contract classes."""

from compute_forecast.core.contracts.base_contracts import (
    ContractViolationType,
    ContractViolation,
    ContractValidationResult,
    BaseContract,
    StageTransitionContract,
)


class TestContractViolationType:
    """Test ContractViolationType enum."""

    def test_violation_types_exist(self):
        """Test all violation types are defined."""
        assert ContractViolationType.MISSING_REQUIRED_FIELD
        assert ContractViolationType.INVALID_TYPE
        assert ContractViolationType.OUT_OF_RANGE
        assert ContractViolationType.INCONSISTENT_DATA
        assert ContractViolationType.INVALID_REFERENCE
        assert ContractViolationType.SCHEMA_MISMATCH
        assert ContractViolationType.BUSINESS_RULE_VIOLATION
        assert ContractViolationType.PERFORMANCE_VIOLATION

    def test_violation_type_values(self):
        """Test violation type string values."""
        assert ContractViolationType.MISSING_REQUIRED_FIELD.value == "missing_required"
        assert ContractViolationType.INVALID_TYPE.value == "invalid_type"
        assert ContractViolationType.OUT_OF_RANGE.value == "out_of_range"


class TestContractViolation:
    """Test ContractViolation dataclass."""

    def test_create_violation(self):
        """Test creating a contract violation."""
        violation = ContractViolation(
            violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
            field_name="test_field",
            expected="value",
            actual=None,
            severity="error",
            message="Test field is missing",
        )

        assert violation.violation_type == ContractViolationType.MISSING_REQUIRED_FIELD
        assert violation.field_name == "test_field"
        assert violation.expected == "value"
        assert violation.actual is None
        assert violation.severity == "error"
        assert violation.message == "Test field is missing"
        assert violation.context is None

    def test_violation_with_context(self):
        """Test violation with additional context."""
        context = {"stage": "analysis", "component": "validator"}
        violation = ContractViolation(
            violation_type=ContractViolationType.INVALID_TYPE,
            field_name="data",
            expected="dict",
            actual="list",
            severity="error",
            message="Invalid data type",
            context=context,
        )

        assert violation.context == context
        assert violation.context["stage"] == "analysis"


class TestContractValidationResult:
    """Test ContractValidationResult dataclass."""

    def test_create_result(self):
        """Test creating validation result."""
        result = ContractValidationResult(
            contract_name="test_contract", passed=True, execution_time_ms=10.5
        )

        assert result.contract_name == "test_contract"
        assert result.passed is True
        assert result.violations == []
        assert result.warnings == []
        assert result.execution_time_ms == 10.5
        assert result.metadata == {}

    def test_error_count(self):
        """Test error count property."""
        violations = [
            ContractViolation(
                violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
                field_name="field1",
                expected="value",
                actual=None,
                severity="error",
                message="Missing field",
            ),
            ContractViolation(
                violation_type=ContractViolationType.INVALID_TYPE,
                field_name="field2",
                expected="int",
                actual="str",
                severity="error",
                message="Wrong type",
            ),
            ContractViolation(
                violation_type=ContractViolationType.OUT_OF_RANGE,
                field_name="field3",
                expected="[0, 1]",
                actual=2,
                severity="warning",
                message="Out of range",
            ),
        ]

        result = ContractValidationResult(
            contract_name="test", passed=False, violations=violations
        )

        assert result.error_count == 2
        assert result.warning_count == 0  # Warnings are in separate list

    def test_warning_count(self):
        """Test warning count property."""
        warnings = [
            ContractViolation(
                violation_type=ContractViolationType.BUSINESS_RULE_VIOLATION,
                field_name="confidence",
                expected=">= 0.5",
                actual=0.3,
                severity="warning",
                message="Low confidence",
            ),
            ContractViolation(
                violation_type=ContractViolationType.PERFORMANCE_VIOLATION,
                field_name="execution_time",
                expected="< 100ms",
                actual="150ms",
                severity="warning",
                message="Slow execution",
            ),
        ]

        result = ContractValidationResult(
            contract_name="test", passed=True, warnings=warnings
        )

        assert result.warning_count == 2
        assert result.error_count == 0

    def test_has_errors(self):
        """Test has_errors property."""
        # No errors
        result1 = ContractValidationResult(contract_name="test", passed=True)
        assert result1.has_errors is False

        # With errors
        result2 = ContractValidationResult(
            contract_name="test",
            passed=False,
            violations=[
                ContractViolation(
                    violation_type=ContractViolationType.MISSING_REQUIRED_FIELD,
                    field_name="field",
                    expected="value",
                    actual=None,
                    severity="error",
                    message="Missing",
                )
            ],
        )
        assert result2.has_errors is True


class TestBaseContract:
    """Test BaseContract implementation."""

    def test_create_base_contract(self):
        """Test creating a base contract."""
        contract = BaseContract("test_contract")

        assert contract.contract_name == "test_contract"
        assert contract.get_required_fields() == []
        assert contract.get_performance_requirements() == {}

    def test_check_required_fields(self):
        """Test required field checking."""
        contract = BaseContract("test")
        contract._required_fields = ["field1", "field2", "field3"]

        # All fields present
        data1 = {"field1": "value1", "field2": "value2", "field3": "value3"}
        violations1 = contract._check_required_fields(data1)
        assert len(violations1) == 0

        # Missing field
        data2 = {"field1": "value1", "field3": "value3"}
        violations2 = contract._check_required_fields(data2)
        assert len(violations2) == 1
        assert violations2[0].field_name == "field2"
        assert (
            violations2[0].violation_type
            == ContractViolationType.MISSING_REQUIRED_FIELD
        )

        # Null field
        data3 = {"field1": "value1", "field2": None, "field3": "value3"}
        violations3 = contract._check_required_fields(data3)
        assert len(violations3) == 1
        assert violations3[0].field_name == "field2"

    def test_check_type(self):
        """Test type checking."""
        contract = BaseContract("test")

        # Correct type
        violation1 = contract._check_type("test", str, "field1")
        assert violation1 is None

        # Wrong type
        violation2 = contract._check_type(123, str, "field2")
        assert violation2 is not None
        assert violation2.violation_type == ContractViolationType.INVALID_TYPE
        assert violation2.field_name == "field2"
        assert violation2.expected == "str"
        assert violation2.actual == "int"

    def test_check_range(self):
        """Test range checking."""
        contract = BaseContract("test")

        # Within range
        violation1 = contract._check_range(0.5, 0.0, 1.0, "score")
        assert violation1 is None

        # Below range
        violation2 = contract._check_range(-0.1, 0.0, 1.0, "score")
        assert violation2 is not None
        assert violation2.violation_type == ContractViolationType.OUT_OF_RANGE
        assert violation2.expected == "[0.0, 1.0]"
        assert violation2.actual == -0.1

        # Above range
        violation3 = contract._check_range(1.5, 0.0, 1.0, "score")
        assert violation3 is not None
        assert violation3.violation_type == ContractViolationType.OUT_OF_RANGE


class TestStageTransitionContract:
    """Test StageTransitionContract."""

    def test_create_transition_contract(self):
        """Test creating a stage transition contract."""
        contract = StageTransitionContract(
            from_stage="collection",
            to_stage="analysis",
            required_fields=["papers", "metadata"],
            transformations={"raw_papers": "papers"},
            validation_rules=["papers_valid"],
        )

        assert contract.from_stage == "collection"
        assert contract.to_stage == "analysis"
        assert contract.required_fields == ["papers", "metadata"]
        assert contract.transformations == {"raw_papers": "papers"}
        assert contract.validation_rules == ["papers_valid"]

    def test_validate_transition(self):
        """Test transition validation."""
        contract = StageTransitionContract(
            from_stage="collection",
            to_stage="analysis",
            required_fields=["papers", "metadata"],
            transformations={"raw_papers": "papers"},
            validation_rules=[],
        )

        # Valid transition
        input_data = {"raw_papers": [1, 2, 3], "collection_info": "test"}
        output_data = {"papers": [1, 2, 3], "metadata": {"count": 3}}

        violations1 = contract.validate_transition(input_data, output_data)
        assert len(violations1) == 0

        # Missing required field
        output_data2 = {"papers": [1, 2, 3]}  # Missing metadata
        violations2 = contract.validate_transition(input_data, output_data2)
        assert len(violations2) == 1
        assert violations2[0].field_name == "metadata"
        assert (
            violations2[0].violation_type
            == ContractViolationType.MISSING_REQUIRED_FIELD
        )

        # Missing transformation
        input_data3 = {"raw_papers": [1, 2, 3]}
        output_data3 = {"metadata": {"count": 3}}  # Missing papers transformation
        violations3 = contract.validate_transition(input_data3, output_data3)
        assert len(violations3) == 2  # Missing required field and transformation

        # Check context in violations
        assert violations2[0].context["from_stage"] == "collection"
        assert violations2[0].context["to_stage"] == "analysis"
