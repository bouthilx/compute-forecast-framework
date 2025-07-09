"""Unit tests for analysis contract implementations."""

import pytest
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    Author,
)
from compute_forecast.core.contracts.base_contracts import ContractViolationType
from compute_forecast.core.contracts.analysis_contracts import (
    ComputationalAnalysisContract,
    PaperMetadataContract,
    ResourceMetricsContract,
)


class TestComputationalAnalysisContract:
    """Test ComputationalAnalysisContract."""

    @pytest.fixture
    def contract(self):
        """Provide contract instance."""
        return ComputationalAnalysisContract()

    def test_contract_properties(self, contract):
        """Test contract properties."""
        assert contract.contract_name == "computational_analysis"
        assert "computational_richness" in contract.get_required_fields()
        assert "confidence_score" in contract.get_required_fields()
        assert "keyword_matches" in contract.get_required_fields()
        assert "resource_metrics" in contract.get_required_fields()

        perf_reqs = contract.get_performance_requirements()
        assert perf_reqs["max_processing_time_ms"] == 1000.0
        assert perf_reqs["min_confidence_threshold"] == 0.3

    def test_validate_valid_analysis(self, contract):
        """Test validation of valid analysis."""
        analysis = ComputationalAnalysis(
            computational_richness=0.8,
            confidence_score=0.9,
            keyword_matches={"gpu": 5, "training": 3},
            resource_metrics={"gpu_count": 4, "gpu_type": "V100"},
            experimental_indicators={"ablation": True},
        )

        violations = contract.validate(analysis)
        assert len(violations) == 0

    def test_validate_dict_input(self, contract):
        """Test validation with dict input."""
        analysis_dict = {
            "computational_richness": 0.8,
            "confidence_score": 0.9,
            "keyword_matches": {"gpu": 5},
            "resource_metrics": {},
        }

        violations = contract.validate(analysis_dict)
        assert len(violations) == 0

    def test_validate_invalid_type(self, contract):
        """Test validation with invalid input type."""
        violations = contract.validate("not a valid input")

        assert len(violations) == 1
        assert violations[0].violation_type == ContractViolationType.INVALID_TYPE
        assert violations[0].field_name == "data"

    def test_validate_missing_fields(self, contract):
        """Test validation with missing required fields."""
        analysis_dict = {
            "computational_richness": 0.8,
            # Missing confidence_score, keyword_matches, resource_metrics
        }

        violations = contract.validate(analysis_dict)

        # Should have violations for missing fields
        missing_fields = {
            v.field_name
            for v in violations
            if v.violation_type == ContractViolationType.MISSING_REQUIRED_FIELD
        }
        assert "confidence_score" in missing_fields
        assert "keyword_matches" in missing_fields
        assert "resource_metrics" in missing_fields

    def test_validate_richness_out_of_range(self, contract):
        """Test validation of richness score out of range."""
        analysis_dict = {
            "computational_richness": 1.5,  # Out of [0, 1] range
            "confidence_score": 0.9,
            "keyword_matches": {},
            "resource_metrics": {},
        }

        violations = contract.validate(analysis_dict)

        range_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.OUT_OF_RANGE
        ]
        assert len(range_violations) == 1
        assert range_violations[0].field_name == "computational_richness"
        assert range_violations[0].expected == "[0.0, 1.0]"
        assert range_violations[0].actual == 1.5

    def test_validate_low_confidence_warning(self, contract):
        """Test validation with low confidence score."""
        analysis_dict = {
            "computational_richness": 0.5,
            "confidence_score": 0.2,  # Below 0.3 threshold
            "keyword_matches": {},
            "resource_metrics": {},
        }

        violations = contract.validate(analysis_dict)

        # Should have warning for low confidence
        warnings = [v for v in violations if v.severity == "warning"]
        assert len(warnings) == 1
        assert warnings[0].field_name == "confidence_score"
        assert (
            warnings[0].violation_type == ContractViolationType.BUSINESS_RULE_VIOLATION
        )

    def test_validate_invalid_keyword_matches(self, contract):
        """Test validation of invalid keyword matches."""
        analysis_dict = {
            "computational_richness": 0.8,
            "confidence_score": 0.9,
            "keyword_matches": "not a dict",  # Should be dict
            "resource_metrics": {},
        }

        violations = contract.validate(analysis_dict)

        type_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.INVALID_TYPE
        ]
        assert any(v.field_name == "keyword_matches" for v in type_violations)

    def test_validate_negative_keyword_count(self, contract):
        """Test validation of negative keyword counts."""
        analysis_dict = {
            "computational_richness": 0.8,
            "confidence_score": 0.9,
            "keyword_matches": {"gpu": 5, "cpu": -2},  # Negative count
            "resource_metrics": {},
        }

        violations = contract.validate(analysis_dict)

        keyword_violations = [
            v for v in violations if "keyword_matches" in v.field_name
        ]
        assert len(keyword_violations) == 1
        assert keyword_violations[0].field_name == "keyword_matches.cpu"

    def test_validate_gpu_inconsistency(self, contract):
        """Test validation of GPU data inconsistency."""
        analysis_dict = {
            "computational_richness": 0.8,
            "confidence_score": 0.9,
            "keyword_matches": {},
            "resource_metrics": {
                "gpu_count": 8,
                # Missing gpu_type
            },
        }

        violations = contract.validate(analysis_dict)

        # Should have warning about missing GPU type
        gpu_warnings = [
            v
            for v in violations
            if v.field_name == "resource_metrics.gpu_type" and v.severity == "warning"
        ]
        assert len(gpu_warnings) == 1
        assert gpu_warnings[0].violation_type == ContractViolationType.INCONSISTENT_DATA

    def test_validate_negative_resource_metrics(self, contract):
        """Test validation of negative resource metrics."""
        analysis_dict = {
            "computational_richness": 0.8,
            "confidence_score": 0.9,
            "keyword_matches": {},
            "resource_metrics": {
                "training_time": -10,  # Negative time
                "memory_gb": -32,  # Negative memory
            },
        }

        violations = contract.validate(analysis_dict)

        negative_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.OUT_OF_RANGE
            and "resource_metrics" in v.field_name
        ]
        assert len(negative_violations) == 2


class TestPaperMetadataContract:
    """Test PaperMetadataContract."""

    @pytest.fixture
    def contract(self):
        """Provide contract instance."""
        return PaperMetadataContract()

    @pytest.fixture
    def valid_paper(self):
        """Provide valid paper instance."""
        return Paper(
            paper_id="123",
            title="Test Paper",
            authors=[Author(name="Test Author", affiliation="Test University")],
            venue="ICML",
            year=2024,
            citations=10,
            abstract="Test abstract",
        )

    def test_contract_properties(self, contract):
        """Test contract properties."""
        assert contract.contract_name == "paper_metadata"
        assert "title" in contract.get_required_fields()
        assert "authors" in contract.get_required_fields()
        assert "year" in contract.get_required_fields()
        assert "venue" in contract.get_required_fields()

        perf_reqs = contract.get_performance_requirements()
        assert perf_reqs["max_validation_time_ms"] == 100.0

    def test_validate_valid_paper(self, contract, valid_paper):
        """Test validation of valid paper."""
        violations = contract.validate(valid_paper)
        assert len(violations) == 0

    def test_validate_dict_input(self, contract):
        """Test validation with dict input."""
        paper_dict = {
            "paper_id": "123",
            "title": "Test Paper",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2024,
            "citations": 10,
        }

        violations = contract.validate(paper_dict)
        assert len(violations) == 0

    def test_validate_missing_title(self, contract):
        """Test validation with missing title."""
        paper_dict = {
            "paper_id": "123",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2024,
        }

        violations = contract.validate(paper_dict)

        missing_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.MISSING_REQUIRED_FIELD
        ]
        assert any(v.field_name == "title" for v in missing_violations)

    def test_validate_empty_title(self, contract):
        """Test validation with empty title."""
        paper_dict = {
            "paper_id": "123",
            "title": "   ",  # Only whitespace
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2024,
        }

        violations = contract.validate(paper_dict)

        title_violations = [v for v in violations if v.field_name == "title"]
        assert len(title_violations) == 1
        assert (
            title_violations[0].violation_type
            == ContractViolationType.BUSINESS_RULE_VIOLATION
        )

    def test_validate_empty_authors(self, contract):
        """Test validation with empty authors list."""
        paper_dict = {
            "paper_id": "123",
            "title": "Test Paper",
            "authors": [],  # Empty list
            "venue": "ICML",
            "year": 2024,
        }

        violations = contract.validate(paper_dict)

        author_violations = [v for v in violations if v.field_name == "authors"]
        assert len(author_violations) == 1
        assert (
            author_violations[0].violation_type
            == ContractViolationType.BUSINESS_RULE_VIOLATION
        )

    def test_validate_invalid_year(self, contract):
        """Test validation with invalid year."""
        paper_dict = {
            "paper_id": "123",
            "title": "Test Paper",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2018,  # Before 2019
        }

        violations = contract.validate(paper_dict)

        year_violations = [v for v in violations if v.field_name == "year"]
        assert len(year_violations) == 1
        assert year_violations[0].violation_type == ContractViolationType.OUT_OF_RANGE
        assert "2018" in year_violations[0].message

    def test_validate_future_year(self, contract):
        """Test validation with future year."""
        future_year = datetime.now().year + 1
        paper_dict = {
            "paper_id": "123",
            "title": "Test Paper",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": future_year,
        }

        violations = contract.validate(paper_dict)

        year_violations = [v for v in violations if v.field_name == "year"]
        assert len(year_violations) == 1
        assert year_violations[0].violation_type == ContractViolationType.OUT_OF_RANGE

    def test_validate_negative_citations(self, contract):
        """Test validation with negative citations."""
        paper_dict = {
            "paper_id": "123",
            "title": "Test Paper",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2024,
            "citations": -5,  # Negative
        }

        violations = contract.validate(paper_dict)

        citation_violations = [v for v in violations if v.field_name == "citations"]
        assert len(citation_violations) == 1
        assert (
            citation_violations[0].violation_type == ContractViolationType.OUT_OF_RANGE
        )

    def test_validate_no_identifiers(self, contract):
        """Test validation with no identifiers."""
        paper_dict = {
            "title": "Test Paper",
            "authors": [{"name": "Test Author"}],
            "venue": "ICML",
            "year": 2024,
            # No paper_id, openalex_id, or arxiv_id
        }

        violations = contract.validate(paper_dict)

        id_violations = [v for v in violations if v.field_name == "identifiers"]
        assert len(id_violations) == 1
        assert (
            id_violations[0].violation_type
            == ContractViolationType.BUSINESS_RULE_VIOLATION
        )
        assert "at least one identifier" in id_violations[0].message


class TestResourceMetricsContract:
    """Test ResourceMetricsContract."""

    @pytest.fixture
    def contract(self):
        """Provide contract instance."""
        return ResourceMetricsContract()

    def test_contract_properties(self, contract):
        """Test contract properties."""
        assert contract.contract_name == "resource_metrics"
        assert contract.get_required_fields() == []  # No required fields

        perf_reqs = contract.get_performance_requirements()
        assert perf_reqs["max_metric_count"] == 50

    def test_validate_valid_metrics(self, contract):
        """Test validation of valid resource metrics."""
        metrics = {
            "gpu_count": 8,
            "gpu_type": "V100",
            "gpu_memory_gb": 32,
            "training_time_hours": 48.5,
            "model_parameters": 175_000_000_000,
        }

        violations = contract.validate(metrics)
        assert len(violations) == 0

    def test_validate_invalid_type(self, contract):
        """Test validation with non-dict input."""
        violations = contract.validate("not a dict")

        assert len(violations) == 1
        assert violations[0].violation_type == ContractViolationType.INVALID_TYPE
        assert violations[0].field_name == "resource_metrics"

    def test_validate_too_many_metrics(self, contract):
        """Test validation with excessive metrics."""
        metrics = {f"metric_{i}": i for i in range(60)}  # 60 metrics

        violations = contract.validate(metrics)

        perf_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.PERFORMANCE_VIOLATION
        ]
        assert len(perf_violations) == 1
        assert perf_violations[0].severity == "warning"
        assert "60" in perf_violations[0].message

    def test_validate_empty_metric_key(self, contract):
        """Test validation with empty metric key."""
        metrics = {
            "gpu_count": 4,
            "": 100,  # Empty key
            " ": 200,  # Whitespace key
        }

        violations = contract.validate(metrics)

        key_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.INVALID_TYPE
            and "non-empty string" in v.message
        ]
        assert len(key_violations) == 2

    def test_validate_negative_gpu_count(self, contract):
        """Test validation of negative GPU count."""
        metrics = {"gpu_count": -2, "total_gpus": -4}

        violations = contract.validate(metrics)

        gpu_violations = [
            v
            for v in violations
            if "gpu" in v.field_name.lower()
            and v.violation_type == ContractViolationType.OUT_OF_RANGE
        ]
        assert len(gpu_violations) == 2

    def test_validate_negative_memory(self, contract):
        """Test validation of negative memory values."""
        metrics = {"gpu_memory_gb": -32, "system_memory": -128}

        violations = contract.validate(metrics)

        memory_violations = [v for v in violations if "memory" in v.field_name.lower()]
        assert len(memory_violations) == 2

    def test_validate_negative_time_values(self, contract):
        """Test validation of negative time values."""
        metrics = {
            "training_time_hours": -10,
            "inference_duration_ms": -100,
            "total_time": -50,
        }

        violations = contract.validate(metrics)

        time_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.OUT_OF_RANGE
        ]
        assert len(time_violations) == 3

    def test_validate_negative_size_values(self, contract):
        """Test validation of negative size values."""
        metrics = {
            "model_size_gb": -10,
            "total_parameters": -1000000,
            "dataset_size": -50,
        }

        violations = contract.validate(metrics)

        size_violations = [
            v
            for v in violations
            if v.violation_type == ContractViolationType.OUT_OF_RANGE
        ]
        assert len(size_violations) == 3

    def test_validate_mixed_valid_invalid(self, contract):
        """Test validation with mix of valid and invalid metrics."""
        metrics = {
            "gpu_count": 4,  # Valid
            "gpu_memory_gb": 32,  # Valid
            "training_time_hours": -10,  # Invalid
            "model_parameters": 1000000,  # Valid
            "": 100,  # Invalid key
        }

        violations = contract.validate(metrics)

        # Should have violations for negative time and empty key
        assert len(violations) == 2
        assert any("training_time" in v.field_name for v in violations)
        assert any("non-empty string" in v.message for v in violations)
