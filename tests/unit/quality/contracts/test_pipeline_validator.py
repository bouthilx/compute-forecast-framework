"""Unit tests for pipeline validation components."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    Author,
)
from compute_forecast.core.contracts.base_contracts import (
    ContractViolationType,
    ContractValidationResult,
)
from compute_forecast.core.contracts.pipeline_validator import (
    AnalysisContractValidator,
    PipelineIntegrationValidator,
    PipelineValidationReport,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestAnalysisContractValidator:
    """Test AnalysisContractValidator."""

    @pytest.fixture
    def validator(self):
        """Provide validator instance."""
        return AnalysisContractValidator()

    @pytest.fixture
    def valid_analysis(self):
        """Provide valid computational analysis."""
        return ComputationalAnalysis(
            computational_richness=0.8,
            confidence_score=0.9,
            keyword_matches={"gpu": 5, "training": 3},
            resource_metrics={"gpu_count": 4, "gpu_type": "V100"},
            experimental_indicators={},
        )

    @pytest.fixture
    def valid_paper(self):
        """Provide valid paper."""
        return create_test_paper(
            paper_id="123",
            title="Test Paper",
            authors=[Author(name="Test Author", affiliations=["Test Uni"])],
            venue="ICML",
            year=2024,
            citation_count=10,
            abstract_text="Test abstract",
        )

    def test_register_default_contracts(self, validator):
        """Test default contracts are registered."""
        assert "computational_analysis" in validator.contracts
        assert "paper_metadata" in validator.contracts
        assert "resource_metrics" in validator.contracts

    def test_register_custom_contract(self, validator):
        """Test registering custom contract."""
        mock_contract = Mock()
        validator.register_contract("custom", mock_contract)

        assert validator.contracts["custom"] == mock_contract

    def test_validate_computational_analysis_valid(self, validator, valid_analysis):
        """Test validation of valid computational analysis."""
        result = validator.validate_computational_analysis(valid_analysis)

        assert isinstance(result, ContractValidationResult)
        assert result.contract_name == "computational_analysis"
        assert result.passed is True
        assert len(result.violations) == 0
        assert result.execution_time_ms > 0

    def test_validate_computational_analysis_invalid(self, validator):
        """Test validation of invalid computational analysis."""
        invalid_analysis = ComputationalAnalysis(
            computational_richness=1.5,  # Out of range
            confidence_score=0.1,  # Below threshold
            keyword_matches={},
            resource_metrics={},
            experimental_indicators={},
        )

        result = validator.validate_computational_analysis(invalid_analysis)

        assert result.passed is False
        assert len(result.violations) > 0
        assert len(result.warnings) > 0  # Low confidence warning

    def test_validate_with_paper_cross_validation(
        self, validator, valid_analysis, valid_paper
    ):
        """Test validation with paper cross-validation."""
        # Add paper_id to analysis for testing
        valid_analysis.paper_id = "456"  # Different from paper

        result = validator.validate_computational_analysis(valid_analysis, valid_paper)

        # Should have inconsistency violation
        inconsistent = [
            v
            for v in result.violations
            if v.violation_type == ContractViolationType.INCONSISTENT_DATA
        ]
        assert len(inconsistent) == 1
        assert inconsistent[0].field_name == "paper_id"

    def test_validate_resource_metrics(self, validator):
        """Test resource metrics validation."""
        analysis = ComputationalAnalysis(
            computational_richness=0.8,
            confidence_score=0.9,
            keyword_matches={},
            resource_metrics={
                "gpu_count": -2,  # Invalid negative value
                "training_time": 100,
            },
            experimental_indicators={},
        )

        result = validator.validate_computational_analysis(analysis)

        # Should have resource metrics violations
        resource_violations = [
            v for v in result.violations if "resource_metrics" in v.field_name
        ]
        assert len(resource_violations) > 0

    def test_performance_violation(self, validator, valid_analysis):
        """Test performance requirement violation."""
        # Mock slow validation
        with patch("time.time") as mock_time:
            # Simulate validation taking 2 seconds (2000ms)
            mock_time.side_effect = [0, 2.0]

            result = validator.validate_computational_analysis(valid_analysis)

            # Should have performance warning
            perf_warnings = [
                v
                for v in result.warnings
                if v.violation_type == ContractViolationType.PERFORMANCE_VIOLATION
            ]
            assert len(perf_warnings) == 1

    def test_validate_pipeline_transition_valid(self, validator):
        """Test valid pipeline transition validation."""
        input_data = {
            "raw_papers": [1, 2, 3],
            "collection_metadata": {"source": "test"},
        }
        output_data = {"papers": [1, 2, 3], "metadata": {"source": "test", "count": 3}}

        result = validator.validate_pipeline_transition(
            "collection", "analysis", input_data, output_data
        )

        assert result.passed is True
        assert len(result.violations) == 0
        assert result.metadata["from_stage"] == "collection"
        assert result.metadata["to_stage"] == "analysis"

    def test_validate_pipeline_transition_unknown(self, validator):
        """Test unknown pipeline transition."""
        result = validator.validate_pipeline_transition("unknown", "stage", {}, {})

        assert result.passed is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type
            == ContractViolationType.INVALID_REFERENCE
        )

    def test_validate_papers_interface(self, validator):
        """Test BaseValidator interface implementation."""
        papers = [
            create_test_paper(
                paper_id="1",
                title="Paper 1",
                authors=[Author(name="Author 1", affiliations=["Uni 1"])],
                venue="ICML",
                year=2024,
                citation_count=10,
                abstract_text="Abstract 1",
            ),
            create_test_paper(
                paper_id="2",
                title="",  # Invalid empty title
                authors=[],  # Invalid empty authors
                venue="NeurIPS",
                year=2024,
                citation_count=5,
                abstract_text="Abstract 2",
            ),
        ]

        result = validator.validate(papers)

        assert isinstance(result, dict)
        assert result["total_papers"] == 2
        assert result["valid_papers"] == 1
        assert result["invalid_papers"] == 1
        assert result["validation_rate"] == 0.5
        assert len(result["violations_by_type"]) > 0
        assert len(result["failed_papers"]) == 1

    def test_get_validation_score(self, validator):
        """Test validation score calculation."""
        validation_result = {
            "total_papers": 10,
            "valid_papers": 8,
            "validation_rate": 0.8,
        }

        score = validator.get_validation_score(validation_result)
        assert score == 0.8


class TestPipelineValidationReport:
    """Test PipelineValidationReport."""

    def test_create_report(self):
        """Test creating validation report."""
        report = PipelineValidationReport(
            stage="test_stage", total_items=100, valid_items=95
        )

        assert report.stage == "test_stage"
        assert report.total_items == 100
        assert report.valid_items == 95
        assert report.validation_rate == 0.95
        assert report.total_violations == 0
        assert report.total_warnings == 0

    def test_report_with_results(self):
        """Test report with contract results."""
        result1 = ContractValidationResult(
            contract_name="test1",
            passed=False,
            violations=[Mock(), Mock()],  # 2 violations
            warnings=[Mock()],  # 1 warning
        )
        result2 = ContractValidationResult(
            contract_name="test2",
            passed=True,
            violations=[],
            warnings=[Mock(), Mock()],  # 2 warnings
        )

        report = PipelineValidationReport(
            stage="test",
            total_items=10,
            valid_items=8,
            contract_results=[result1, result2],
        )

        assert report.total_violations == 2
        assert report.total_warnings == 3


class TestPipelineIntegrationValidator:
    """Test PipelineIntegrationValidator."""

    @pytest.fixture
    def validator(self):
        """Provide validator instance."""
        return PipelineIntegrationValidator()

    @pytest.fixture
    def valid_papers(self):
        """Provide list of valid papers."""
        return [
            create_test_paper(
                paper_id=f"{i}",
                title=f"Paper {i}",
                authors=[Author(name=f"Author {i}", affiliations=[f"Uni {i}"])],
                venue="ICML",
                year=2024,
                citation_count=i * 10,
                abstract_text=f"Abstract {i}",
            )
            for i in range(1, 6)
        ]

    @pytest.fixture
    def valid_analyses(self):
        """Provide list of valid analyses."""
        return [
            ComputationalAnalysis(
                computational_richness=0.8,
                confidence_score=0.9,
                keyword_matches={"gpu": i},
                resource_metrics={"gpu_count": i},
                experimental_indicators={},
            )
            for i in range(1, 6)
        ]

    def test_validate_collection_to_analysis(self, validator, valid_papers):
        """Test collection to analysis validation."""
        report = validator.validate_collection_to_analysis(valid_papers)

        assert isinstance(report, PipelineValidationReport)
        assert report.stage == "collection_to_analysis"
        assert report.total_items == 5
        assert report.valid_items == 5
        assert report.validation_rate == 1.0
        assert len(report.contract_results) > 0
        assert "papers_per_second" in report.performance_metrics

    def test_validate_collection_with_invalid_papers(self, validator):
        """Test validation with invalid papers."""
        papers = [
            create_test_paper(
                paper_id="1",
                title="Valid Paper",
                authors=[Author(name="Author", affiliations=["Uni"])],
                venue="ICML",
                year=2024,
                citation_count=10,
                abstract_text="Abstract",
            ),
            create_test_paper(
                paper_id="2",
                title="",  # Invalid
                authors=[],  # Invalid
                venue="NeurIPS",
                year=2018,  # Invalid year
                citation_count=-5,  # Invalid
                abstract_text="",
            ),
        ]

        report = validator.validate_collection_to_analysis(papers)

        assert report.total_items == 2
        assert report.valid_items == 1
        assert report.validation_rate == 0.5
        assert len(report.recommendations) > 0
        assert any("Data quality below threshold" in r for r in report.recommendations)

    def test_validate_analysis_outputs(self, validator, valid_analyses):
        """Test analysis outputs validation."""
        report = validator.validate_analysis_outputs(valid_analyses)

        assert isinstance(report, PipelineValidationReport)
        assert report.stage == "analysis_outputs"
        assert report.total_items == 5
        assert report.valid_items == 5
        assert report.validation_rate == 1.0
        assert "analyses_per_second" in report.performance_metrics

    def test_validate_analysis_with_low_confidence(self, validator):
        """Test validation with low confidence analyses."""
        analyses = [
            ComputationalAnalysis(
                computational_richness=0.5,
                confidence_score=0.3,  # Low confidence
                keyword_matches={},
                resource_metrics={},
                experimental_indicators={},
            )
            for _ in range(5)
        ]

        report = validator.validate_analysis_outputs(analyses)

        assert len(report.recommendations) > 0
        assert any("low confidence" in r for r in report.recommendations)

    def test_validate_full_pipeline(self, validator, valid_papers, valid_analyses):
        """Test full pipeline validation."""
        collection_data = {"papers": valid_papers}
        analysis_data = {"analyses": valid_analyses}

        reports = validator.validate_full_pipeline(collection_data, analysis_data)

        assert isinstance(reports, dict)
        assert "collection_to_analysis" in reports
        assert "analysis_outputs" in reports
        assert "collection_analysis_transition" in reports

        # Check all reports are valid
        for report_name, report in reports.items():
            assert isinstance(report, PipelineValidationReport)
            assert report.total_items > 0

    def test_validate_full_pipeline_partial_data(self, validator):
        """Test full pipeline validation with partial data."""
        collection_data = {}  # Missing papers
        analysis_data = {"analyses": []}  # Empty analyses

        reports = validator.validate_full_pipeline(collection_data, analysis_data)

        # Should still return transition validation
        assert "collection_analysis_transition" in reports

        # Should not have other reports due to missing data
        assert "collection_to_analysis" not in reports
        assert (
            len(reports["analysis_outputs"].contract_results) == 0
            if "analysis_outputs" in reports
            else True
        )
