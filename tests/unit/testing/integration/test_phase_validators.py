"""
Unit tests for Pipeline Phase Validators
"""

import pytest
from unittest.mock import Mock

from compute_forecast.testing.integration.phase_validators import (
    PhaseValidator,
    CollectionPhaseValidator,
    ExtractionPhaseValidator,
    AnalysisPhaseValidator,
    ProjectionPhaseValidator,
    ReportingPhaseValidator,
    TransitionValidator,
    ValidationResult,
    DataIntegrityChecker,
)
from compute_forecast.testing.integration.pipeline_test_framework import PipelinePhase
from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
)


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test creating validation result"""
        result = ValidationResult(
            phase=PipelinePhase.COLLECTION,
            is_valid=True,
            errors=[],
            warnings=["Low paper count"],
            metrics={"paper_count": 50},
        )

        assert result.phase == PipelinePhase.COLLECTION
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.metrics["paper_count"] == 50


class TestPhaseValidator:
    """Test base PhaseValidator class"""

    def test_base_validator_interface(self):
        """Test base validator interface"""
        # Cannot instantiate abstract class directly
        with pytest.raises(TypeError):
            PhaseValidator()


class TestCollectionPhaseValidator:
    """Test CollectionPhaseValidator"""

    @pytest.fixture
    def validator(self):
        return CollectionPhaseValidator()

    def test_validate_valid_papers(self, validator):
        """Test validating valid paper collection"""
        papers = [
            Mock(spec=Paper, paper_id="1", title="Paper 1", authors=["Author 1"]),
            Mock(spec=Paper, paper_id="2", title="Paper 2", authors=["Author 2"]),
            Mock(spec=Paper, paper_id="3", title="Paper 3", authors=["Author 3"]),
        ]

        result = validator.validate(papers)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.metrics["paper_count"] == 3
        assert result.metrics["valid_papers"] == 3

    def test_validate_invalid_papers(self, validator):
        """Test validating papers with missing data"""
        papers = [
            Mock(spec=Paper, paper_id="1", title=None, authors=[]),  # Missing title
            Mock(
                spec=Paper, paper_id=None, title="Paper 2", authors=["Author"]
            ),  # Missing ID
            Mock(spec=Paper, paper_id="3", title="Paper 3", authors=[]),  # No authors
        ]

        result = validator.validate(papers)

        assert result.is_valid is False
        assert len(result.errors) >= 2  # At least title and paper_id errors
        assert "missing title" in str(result.errors).lower()
        assert "missing paper_id" in str(result.errors).lower()

    def test_validate_empty_collection(self, validator):
        """Test validating empty collection"""
        result = validator.validate([])

        assert result.is_valid is False
        assert "no papers collected" in str(result.errors).lower()

    def test_validate_duplicate_papers(self, validator):
        """Test detecting duplicate papers"""
        papers = [
            Mock(spec=Paper, paper_id="1", title="Paper 1", authors=["Author"]),
            Mock(
                spec=Paper, paper_id="1", title="Paper 1", authors=["Author"]
            ),  # Duplicate
            Mock(spec=Paper, paper_id="2", title="Paper 2", authors=["Author"]),
        ]

        result = validator.validate(papers)

        assert len(result.warnings) > 0
        assert "duplicate" in str(result.warnings).lower()
        assert result.metrics["duplicate_count"] == 1


class TestExtractionPhaseValidator:
    """Test ExtractionPhaseValidator"""

    @pytest.fixture
    def validator(self):
        return ExtractionPhaseValidator()

    def test_validate_extracted_papers(self, validator):
        """Test validating extracted paper data"""
        papers = [
            Mock(
                spec=Paper,
                paper_id="1",
                title="Paper 1",
                abstract="This is an abstract",
                computational_content={"gpu": True},
            ),
            Mock(
                spec=Paper,
                paper_id="2",
                title="Paper 2",
                abstract="Another abstract",
                computational_content={"cpu": True},
            ),
        ]

        result = validator.validate(papers)

        assert result.is_valid is True
        assert result.metrics["extraction_rate"] == 1.0  # 100%

    def test_validate_missing_abstracts(self, validator):
        """Test papers missing abstracts"""
        papers = [
            Mock(spec=Paper, paper_id="1", title="Paper 1", abstract=None),
            Mock(spec=Paper, paper_id="2", title="Paper 2", abstract="Has abstract"),
        ]

        result = validator.validate(papers)

        assert len(result.warnings) > 0
        assert "missing abstract" in str(result.warnings).lower()
        assert result.metrics["papers_without_abstract"] == 1


class TestAnalysisPhaseValidator:
    """Test AnalysisPhaseValidator"""

    @pytest.fixture
    def validator(self):
        return AnalysisPhaseValidator()

    def test_validate_valid_analyses(self, validator):
        """Test validating valid computational analyses"""
        analyses = [
            Mock(
                spec=ComputationalAnalysis,
                paper_id="1",
                has_computational_content=True,
                resource_metrics={"gpu_hours": 100},
            ),
            Mock(
                spec=ComputationalAnalysis,
                paper_id="2",
                has_computational_content=True,
                resource_metrics={"cpu_hours": 200},
            ),
        ]

        result = validator.validate(analyses)

        assert result.is_valid is True
        assert result.metrics["analysis_count"] == 2
        assert result.metrics["computational_papers"] == 2

    def test_validate_missing_metrics(self, validator):
        """Test analyses missing resource metrics"""
        analyses = [
            Mock(
                spec=ComputationalAnalysis,
                paper_id="1",
                has_computational_content=True,
                resource_metrics=None,
            )
        ]

        result = validator.validate(analyses)

        assert len(result.errors) > 0
        assert "missing resource metrics" in str(result.errors).lower()


class TestProjectionPhaseValidator:
    """Test ProjectionPhaseValidator"""

    @pytest.fixture
    def validator(self):
        return ProjectionPhaseValidator()

    def test_validate_valid_projections(self, validator):
        """Test validating valid projection data"""
        projections = {
            "total_papers": 1000,
            "computational_papers": 800,
            "projection_years": [2025, 2026],
            "resource_projections": {
                "2025": {"gpu_hours": 10000},
                "2026": {"gpu_hours": 15000},
            },
            "confidence_intervals": {
                "2025": {"lower": 8000, "upper": 12000},
                "2026": {"lower": 12000, "upper": 18000},
            },
        }

        result = validator.validate(projections)

        assert result.is_valid is True
        assert result.metrics["projection_years_count"] == 2

    def test_validate_missing_projections(self, validator):
        """Test projections missing required data"""
        projections = {
            "total_papers": 1000,
            # Missing resource_projections
        }

        result = validator.validate(projections)

        assert result.is_valid is False
        assert "missing resource_projections" in str(result.errors).lower()


class TestReportingPhaseValidator:
    """Test ReportingPhaseValidator"""

    @pytest.fixture
    def validator(self):
        return ReportingPhaseValidator()

    def test_validate_valid_report(self, validator):
        """Test validating valid report"""
        report = {
            "summary": {"total_analyzed": 1000},
            "methodology": "Analysis methodology",
            "results": {"key_findings": ["Finding 1", "Finding 2"]},
            "visualizations": ["chart1.png", "chart2.png"],
            "generated_at": "2025-01-01T00:00:00",
        }

        result = validator.validate(report)

        assert result.is_valid is True
        assert result.metrics["sections_count"] == 5

    def test_validate_incomplete_report(self, validator):
        """Test report missing sections"""
        report = {
            "summary": {"total_analyzed": 1000},
            # Missing other sections
        }

        result = validator.validate(report)

        assert len(result.warnings) > 0
        assert "missing recommended section" in str(result.warnings).lower()


class TestTransitionValidator:
    """Test TransitionValidator"""

    @pytest.fixture
    def validator(self):
        return TransitionValidator()

    def test_validate_valid_transition(self, validator):
        """Test valid phase transition"""
        # Collection -> Extraction with papers
        from_data = [Mock(spec=Paper) for _ in range(10)]
        to_data = [Mock(spec=Paper) for _ in range(10)]

        result = validator.validate_transition(
            PipelinePhase.COLLECTION, PipelinePhase.EXTRACTION, from_data, to_data
        )

        assert result.is_valid is True

    def test_validate_data_loss(self, validator):
        """Test detecting data loss in transition"""
        # 10 papers -> 5 papers (data loss)
        from_data = [Mock(spec=Paper) for _ in range(10)]
        to_data = [Mock(spec=Paper) for _ in range(5)]

        result = validator.validate_transition(
            PipelinePhase.COLLECTION, PipelinePhase.EXTRACTION, from_data, to_data
        )

        assert len(result.warnings) > 0
        assert "data loss" in str(result.warnings).lower()
        assert result.metrics["data_loss_percent"] == 50.0

    def test_validate_type_mismatch(self, validator):
        """Test type mismatch between phases"""
        # Papers -> Dict (type change)
        from_data = [Mock(spec=Paper) for _ in range(5)]
        to_data = {"analyses": [1, 2, 3]}

        result = validator.validate_transition(
            PipelinePhase.EXTRACTION, PipelinePhase.ANALYSIS, from_data, to_data
        )

        # Should still be valid if it's an expected transition
        assert result.is_valid is True


class TestDataIntegrityChecker:
    """Test DataIntegrityChecker"""

    @pytest.fixture
    def checker(self):
        return DataIntegrityChecker()

    def test_check_paper_integrity(self, checker):
        """Test checking paper data integrity"""
        papers = [
            Mock(
                spec=Paper,
                paper_id="1",
                title="Valid Paper",
                authors=["Author"],
                year=2024,
                venue="ICML",
            ),
            Mock(
                spec=Paper,
                paper_id="2",
                title="",  # Empty title
                authors=[],  # No authors
                year=None,  # Missing year
                venue="",
            ),
        ]

        issues = checker.check_papers(papers)

        assert len(issues) > 0
        assert any("empty title" in issue.lower() for issue in issues)
        assert any("no authors" in issue.lower() for issue in issues)
        assert any("missing year" in issue.lower() for issue in issues)

    def test_check_unique_ids(self, checker):
        """Test checking for unique IDs"""
        items = [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
            {"id": "1", "name": "Item 3"},  # Duplicate ID
        ]

        has_duplicates, duplicates = checker.check_unique_ids(items, "id")

        assert has_duplicates is True
        assert "1" in duplicates
        assert len(duplicates) == 1
