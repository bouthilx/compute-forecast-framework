"""
Unit tests for extraction protocol implementation.

Tests the 5-phase extraction methodology including preparation,
automated extraction, manual extraction, validation, and documentation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
import yaml

from compute_forecast.analysis.computational.extraction_protocol import (
    ExtractionProtocol,
    ExtractionResult,
    ExtractionMetadata,
    HardwareSpecs,
    TrainingSpecs,
    ModelSpecs,
    ComputationSpecs,
    ValidationResults,
    ConfidenceLevel,
    ExtractionPhase,
    ExtractionDecisionTree,
)


@pytest.fixture
def sample_paper_content():
    """Sample paper content for testing."""
    return """
    Abstract
    We present a new model trained on 8 V100 GPUs for 5 days.
    The model has 340M parameters using transformer architecture.

    Experimental Setup
    Training was performed on a cluster with 8 NVIDIA V100 GPUs,
    each with 16GB memory. Total training time was 120 hours.
    We used the ImageNet dataset with 1.2M samples.

    Implementation Details
    The model uses BERT-like architecture with 24 layers.
    Training required approximately 960 GPU-hours total.
    Estimated cost was $2,880 using cloud pricing.
    """


@pytest.fixture
def extraction_protocol(sample_paper_content):
    """Create extraction protocol instance for testing."""
    return ExtractionProtocol(
        paper_content=sample_paper_content,
        paper_id="test_paper_001",
        analyst="test_analyst",
    )


@pytest.fixture
def mock_analyzer():
    """Mock analyzer for testing automated extraction."""
    analyzer = Mock()
    analyzer.analyze.return_value = Mock(
        confidence=0.75, gpu_type="V100", gpu_count=8, training_hours=120
    )
    return analyzer


class TestExtractionMetadata:
    """Test ExtractionMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating extraction metadata."""
        metadata = ExtractionMetadata(
            paper_id="test_001",
            title="Test Paper",
            extraction_date=datetime.now(),
            analyst="analyst_001",
        )

        assert metadata.paper_id == "test_001"
        assert metadata.title == "Test Paper"
        assert metadata.analyst == "analyst_001"
        assert metadata.time_spent_minutes == 0
        assert metadata.phase_completed is None


class TestHardwareSpecs:
    """Test HardwareSpecs dataclass."""

    def test_hardware_specs_defaults(self):
        """Test hardware specs with default values."""
        specs = HardwareSpecs()

        assert specs.gpu_type is None
        assert specs.gpu_count is None
        assert specs.gpu_memory_gb is None
        assert specs.tpu_version is None
        assert specs.tpu_cores is None
        assert specs.nodes_used is None
        assert specs.special_hardware is None

    def test_hardware_specs_with_values(self):
        """Test hardware specs with specific values."""
        specs = HardwareSpecs(
            gpu_type="V100", gpu_count=8, gpu_memory_gb=16.0, nodes_used=1
        )

        assert specs.gpu_type == "V100"
        assert specs.gpu_count == 8
        assert specs.gpu_memory_gb == 16.0
        assert specs.nodes_used == 1


class TestTrainingSpecs:
    """Test TrainingSpecs dataclass."""

    def test_training_specs_defaults(self):
        """Test training specs with default values."""
        specs = TrainingSpecs()

        assert specs.total_time_hours is None
        assert specs.time_unit_original is None
        assert specs.pre_training_hours is None
        assert specs.fine_tuning_hours is None
        assert specs.number_of_runs == 1
        assert specs.wall_clock_time is None


class TestModelSpecs:
    """Test ModelSpecs dataclass."""

    def test_model_specs_defaults(self):
        """Test model specs with default values."""
        specs = ModelSpecs()

        assert specs.parameters_count is None
        assert specs.parameters_unit == "millions"
        assert specs.architecture is None
        assert specs.layers is None
        assert specs.hidden_size is None
        assert specs.model_size_gb is None


class TestValidationResults:
    """Test ValidationResults dataclass."""

    def test_validation_results_defaults(self):
        """Test validation results with default values."""
        validation = ValidationResults()

        assert validation.confidence_hardware == ConfidenceLevel.LOW
        assert validation.confidence_training == ConfidenceLevel.LOW
        assert validation.confidence_model == ConfidenceLevel.LOW
        assert validation.confidence_overall == ConfidenceLevel.LOW
        assert validation.consistency_checks_passed is False
        assert validation.outliers_flagged == []


class TestExtractionDecisionTree:
    """Test ExtractionDecisionTree class."""

    def test_get_next_step_yes(self):
        """Test decision tree navigation with 'yes' answer."""
        next_step = ExtractionDecisionTree.get_next_step("start", "yes")
        assert next_step == "extract_abstract"

    def test_get_next_step_no(self):
        """Test decision tree navigation with 'no' answer."""
        next_step = ExtractionDecisionTree.get_next_step("start", "no")
        assert next_step == "check_experimental_section"

    def test_get_step_info(self):
        """Test getting step information."""
        step_info = ExtractionDecisionTree.get_step_info("start")

        assert "question" in step_info
        assert step_info["question"] == "Is computational info in abstract?"
        assert step_info["yes"] == "extract_abstract"
        assert step_info["no"] == "check_experimental_section"

    def test_invalid_step(self):
        """Test getting info for invalid step."""
        step_info = ExtractionDecisionTree.get_step_info("invalid_step")
        assert step_info == {}


class TestExtractionProtocol:
    """Test ExtractionProtocol main class."""

    def test_initialization(self, extraction_protocol):
        """Test protocol initialization."""
        assert extraction_protocol.paper_id == "test_paper_001"
        assert extraction_protocol.analyst == "test_analyst"
        assert (
            extraction_protocol.extraction_result.metadata.paper_id == "test_paper_001"
        )
        assert extraction_protocol.extraction_result.metadata.analyst == "test_analyst"

    def test_phase1_preparation(self, extraction_protocol):
        """Test Phase 1: Preparation."""
        results = extraction_protocol.phase1_preparation()

        # Check that computational experiments are detected
        assert results["has_computational_experiments"] is True
        assert "quick_scan_results" in results
        assert "structure_notes" in results

        # Check metadata updates
        assert (
            extraction_protocol.extraction_result.metadata.phase_completed
            == ExtractionPhase.PREPARATION
        )
        assert extraction_protocol.extraction_result.metadata.time_spent_minutes > 0

    def test_phase2_automated_extraction(self, extraction_protocol, mock_analyzer):
        """Test Phase 2: Automated Extraction."""
        results = extraction_protocol.phase2_automated_extraction(mock_analyzer)

        # Check that analyzer was called
        mock_analyzer.analyze.assert_called_once()

        # Check results structure
        assert "confidence_score" in results
        assert "fields_found" in results
        assert "fields_missing" in results
        assert "raw_results" in results

        # Check metadata updates
        assert (
            extraction_protocol.extraction_result.metadata.phase_completed
            == ExtractionPhase.AUTOMATED
        )

    def test_phase3_manual_extraction(self, extraction_protocol):
        """Test Phase 3: Manual Extraction."""
        results = extraction_protocol.phase3_manual_extraction()

        # Check that all categories are extracted
        assert "hardware" in results
        assert "training" in results
        assert "model" in results
        assert "dataset" in results
        assert "computation" in results

        # Check that extraction result is populated
        assert extraction_protocol.extraction_result.hardware is not None
        assert extraction_protocol.extraction_result.training is not None
        assert extraction_protocol.extraction_result.model is not None
        assert extraction_protocol.extraction_result.dataset is not None
        assert extraction_protocol.extraction_result.computation is not None

        # Check metadata updates
        assert (
            extraction_protocol.extraction_result.metadata.phase_completed
            == ExtractionPhase.MANUAL
        )

    def test_phase4_validation(self, extraction_protocol):
        """Test Phase 4: Validation."""
        # Set up some data for validation
        extraction_protocol.extraction_result.hardware = HardwareSpecs(
            gpu_type="V100", gpu_count=8
        )
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=120.0
        )
        extraction_protocol.extraction_result.model = ModelSpecs(
            parameters_count=340, architecture="Transformer"
        )

        validation = extraction_protocol.phase4_validation()

        # Check validation results
        assert isinstance(validation, ValidationResults)
        assert validation.confidence_hardware in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]
        assert validation.confidence_training in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]
        assert validation.confidence_model in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]
        assert validation.confidence_overall in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]

        # Check metadata updates
        assert (
            extraction_protocol.extraction_result.metadata.phase_completed
            == ExtractionPhase.VALIDATION
        )

    def test_phase5_documentation(self, extraction_protocol):
        """Test Phase 5: Documentation."""
        # Set up some data for documentation
        extraction_protocol.extraction_result.hardware = HardwareSpecs(
            gpu_type="V100", gpu_count=8
        )
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=120.0
        )

        documentation = extraction_protocol.phase5_documentation()

        # Check documentation results
        assert "extraction_summary" in documentation
        assert "yaml_export" in documentation
        assert "completeness_score" in documentation
        assert "quality_score" in documentation

        # Check that YAML export is valid
        yaml_data = yaml.safe_load(documentation["yaml_export"])
        assert yaml_data is not None
        assert "metadata" in yaml_data

        # Check metadata updates
        assert (
            extraction_protocol.extraction_result.metadata.phase_completed
            == ExtractionPhase.DOCUMENTATION
        )

    def test_run_full_protocol(self, extraction_protocol, mock_analyzer):
        """Test running the complete 5-phase protocol."""
        result = extraction_protocol.run_full_protocol(mock_analyzer)

        # Check that result is returned
        assert isinstance(result, ExtractionResult)
        assert result.metadata.phase_completed == ExtractionPhase.DOCUMENTATION

        # Check that all phases were completed
        assert result.metadata.time_spent_minutes > 0

        # Check that automated extraction was performed
        mock_analyzer.analyze.assert_called_once()

    def test_find_section_content(self, extraction_protocol):
        """Test finding content in paper sections."""
        # Test finding abstract section
        abstract_content = extraction_protocol._find_section_content("abstract")
        assert "Abstract" in abstract_content
        assert "V100" in abstract_content

        # Test finding experimental section
        experimental_content = extraction_protocol._find_section_content(
            "experimental_setup"
        )
        assert "Experimental Setup" in experimental_content

        # Test non-existent section
        nonexistent_content = extraction_protocol._find_section_content("nonexistent")
        assert nonexistent_content == ""

    def test_extract_hardware_specs(self, extraction_protocol):
        """Test hardware specification extraction."""
        hardware_info = extraction_protocol._extract_hardware_specs()

        # Should detect V100 GPU
        assert hardware_info.get("gpu_type") == "V100"

    def test_extract_training_specs(self, extraction_protocol):
        """Test training specification extraction."""
        training_info = extraction_protocol._extract_training_specs()

        # Should detect hours unit
        assert training_info.get("time_unit_original") == "hours"

    def test_extract_model_specs(self, extraction_protocol):
        """Test model specification extraction."""
        model_info = extraction_protocol._extract_model_specs()

        # Should detect transformer architecture
        assert model_info.get("architecture") == "Transformer"
        assert model_info.get("parameters_unit") == "millions"

    def test_extract_dataset_specs(self, extraction_protocol):
        """Test dataset specification extraction."""
        dataset_info = extraction_protocol._extract_dataset_specs()

        # Should detect ImageNet dataset
        assert dataset_info.get("name") == "IMAGENET"

    def test_extract_computation_specs(self, extraction_protocol):
        """Test computation specification extraction."""
        computation_info = extraction_protocol._extract_computation_specs()

        # Should detect explicit GPU-hours calculation method
        assert computation_info.get("calculation_method") == "explicit_gpu_hours"

    def test_run_consistency_checks(self, extraction_protocol):
        """Test consistency checks."""
        # Set up data with inconsistent GPU-hours
        extraction_protocol.extraction_result.hardware = HardwareSpecs(gpu_count=8)
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=120.0
        )
        extraction_protocol.extraction_result.computation = ComputationSpecs(
            total_gpu_hours=500.0
        )  # Should be 960

        issues = extraction_protocol._run_consistency_checks()

        # Should detect GPU-hours inconsistency
        assert len(issues) > 0
        assert any("GPU-hours calculation inconsistent" in issue for issue in issues)

    def test_assess_confidence(self, extraction_protocol):
        """Test confidence assessment."""
        # Test with well-populated hardware specs
        extraction_protocol.extraction_result.hardware = HardwareSpecs(
            gpu_type="V100", gpu_count=8, gpu_memory_gb=16.0, nodes_used=1
        )

        confidence = extraction_protocol._assess_confidence("hardware")
        assert confidence in [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]

        # Test with empty specs
        extraction_protocol.extraction_result.model = ModelSpecs()
        confidence = extraction_protocol._assess_confidence("model")
        assert confidence == ConfidenceLevel.LOW

    def test_detect_outliers(self, extraction_protocol):
        """Test outlier detection."""
        # Set up data with outlier values
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=10000.0
        )  # > 1 year
        extraction_protocol.extraction_result.computation = ComputationSpecs(
            total_gpu_hours=2000000.0
        )  # > 1M

        outliers = extraction_protocol._detect_outliers()

        assert len(outliers) >= 2
        assert any("Training time exceeds 1 year" in outlier for outlier in outliers)
        assert any("GPU-hours unusually high" in outlier for outlier in outliers)

    def test_calculate_completeness_score(self, extraction_protocol):
        """Test completeness score calculation."""
        # Empty extraction should have low completeness
        score = extraction_protocol._calculate_completeness_score()
        assert score == 0.0

        # Populate some fields
        extraction_protocol.extraction_result.hardware = HardwareSpecs(
            gpu_type="V100", gpu_count=8
        )
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=120.0
        )

        score = extraction_protocol._calculate_completeness_score()
        assert 0.0 < score < 1.0

    def test_calculate_quality_score(self, extraction_protocol):
        """Test quality score calculation."""
        # Set up validation results
        extraction_protocol.extraction_result.validation = ValidationResults(
            confidence_overall=ConfidenceLevel.HIGH, consistency_checks_passed=True
        )

        score = extraction_protocol._calculate_quality_score()
        assert score == 1.0  # High confidence + passed consistency = 1.0

        # Test with lower confidence and failed consistency
        extraction_protocol.extraction_result.validation = ValidationResults(
            confidence_overall=ConfidenceLevel.LOW, consistency_checks_passed=False
        )

        score = extraction_protocol._calculate_quality_score()
        assert score < 1.0

    def test_to_yaml(self, extraction_protocol):
        """Test YAML export functionality."""
        # Populate some data
        extraction_protocol.extraction_result.hardware = HardwareSpecs(
            gpu_type="V100", gpu_count=8
        )
        extraction_protocol.extraction_result.training = TrainingSpecs(
            total_time_hours=120.0
        )

        yaml_output = extraction_protocol.to_yaml()

        # Check that output is valid YAML
        data = yaml.safe_load(yaml_output)
        assert data is not None
        assert "metadata" in data
        assert "hardware" in data
        assert "training" in data

        # Check that specific values are preserved
        assert data["hardware"]["gpu_type"] == "V100"
        assert data["hardware"]["gpu_count"] == 8
        assert data["training"]["total_time_hours"] == 120.0


class TestExtractionProtocolEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_paper_content(self):
        """Test protocol with empty paper content."""
        protocol = ExtractionProtocol("", "empty_paper", "test_analyst")

        # Should not raise exception
        results = protocol.phase1_preparation()
        assert results["has_computational_experiments"] is False

    def test_protocol_with_exception(self, extraction_protocol, mock_analyzer):
        """Test protocol handling when analyzer raises exception."""
        # Make analyzer raise exception
        mock_analyzer.analyze.side_effect = Exception("Analyzer failed")

        with pytest.raises(Exception):
            extraction_protocol.run_full_protocol(mock_analyzer)

        # Check that error is recorded in notes
        assert len(extraction_protocol.extraction_result.notes.quality_issues) > 0

    def test_missing_analyzer_attributes(self, extraction_protocol):
        """Test with analyzer that has missing attributes."""
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = Mock()  # No attributes

        # Should not raise exception
        results = extraction_protocol.phase2_automated_extraction(mock_analyzer)
        assert "confidence_score" in results
        assert results["confidence_score"] == 0.0
