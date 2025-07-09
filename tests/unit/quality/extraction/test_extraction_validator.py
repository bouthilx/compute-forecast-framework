"""
Tests for ExtractionQualityValidator.
"""

from compute_forecast.pipeline.content_extraction.quality.extraction_validator import (
    ExtractionQualityValidator,
    ExtractionValidation,
    ExtractionQuality,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from .test_helpers import MockComputationalAnalysis as ComputationalAnalysis


class TestExtractionQualityValidator:
    """Test extraction quality validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ExtractionQualityValidator()

        # Create test paper
        self.paper = Paper(
            paper_id="test_paper_1",
            title="Large Language Model Training",
            year=2023,
            authors=[],
            venue="NeurIPS",
            citations=0,
        )

        # Create complete extraction
        self.complete_extraction = ComputationalAnalysis(
            gpu_hours=1000,
            gpu_type="A100",
            gpu_count=8,
            training_time=125,  # 1000/8 = 125 hours
            parameters=7e9,
            gpu_memory=80,
            batch_size=256,
            dataset_size=1e12,
            epochs=3,
            learning_rate=1e-4,
            optimizer="adam",
            framework="pytorch",
        )

        # Create partial extraction
        self.partial_extraction = ComputationalAnalysis(
            gpu_hours=100, gpu_type="V100", parameters=1e8
        )

        # Create minimal extraction
        self.minimal_extraction = ComputationalAnalysis(gpu_hours=10)

    def test_validate_complete_extraction(self):
        """Test validation of complete extraction."""
        result = self.validator.validate_extraction(
            self.paper, self.complete_extraction
        )

        assert isinstance(result, ExtractionValidation)
        assert result.paper_id == "test_paper_1"
        assert result.extraction_type == "computational_analysis"
        assert result.confidence > 0.8
        assert result.quality == ExtractionQuality.HIGH
        assert result.validation_method == "weighted_scoring"

        # Check cross validation details
        assert "completeness" in result.cross_validation_result
        assert "validity" in result.cross_validation_result
        assert "consistency" in result.cross_validation_result
        assert result.cross_validation_result["completeness"] > 0.8

    def test_validate_partial_extraction(self):
        """Test validation of partial extraction."""
        result = self.validator.validate_extraction(self.paper, self.partial_extraction)

        assert result.confidence < 0.8
        assert result.confidence > 0.5
        assert result.quality in [ExtractionQuality.MEDIUM, ExtractionQuality.LOW]
        assert result.cross_validation_result["completeness"] < 0.6

    def test_validate_minimal_extraction(self):
        """Test validation of minimal extraction."""
        result = self.validator.validate_extraction(self.paper, self.minimal_extraction)

        assert result.confidence < 0.6  # Minimal extraction should have low confidence
        assert result.quality in [ExtractionQuality.LOW, ExtractionQuality.UNRELIABLE]
        assert result.cross_validation_result["completeness"] < 0.3

    def test_calculate_completeness_score(self):
        """Test completeness score calculation."""
        # Complete extraction
        score = self.validator.calculate_completeness_score(self.complete_extraction)
        assert score > 0.8

        # Partial extraction
        score = self.validator.calculate_completeness_score(self.partial_extraction)
        assert 0.3 < score < 0.6

        # Minimal extraction
        score = self.validator.calculate_completeness_score(self.minimal_extraction)
        assert score < 0.3

    def test_validity_score_calculation(self):
        """Test validity score calculation."""
        # Valid values
        valid_extraction = ComputationalAnalysis(
            gpu_hours=1000,
            parameters=1e9,
            gpu_count=8,
            training_time=125,
            batch_size=256,
        )
        score = self.validator._calculate_validity_score(valid_extraction)
        assert score > 0.8

        # Invalid values
        invalid_extraction = ComputationalAnalysis(
            gpu_hours=1e10,  # Unrealistic
            parameters=1e20,  # Way too large
            gpu_count=1000000,  # Impossible
            training_time=100000,  # Over 10 years
            batch_size=1e10,  # Impossible
        )
        score = self.validator._calculate_validity_score(invalid_extraction)
        assert score < 0.2

    def test_paper_consistency_check(self):
        """Test consistency between paper and extraction."""
        # Language model paper with appropriate extraction
        lm_paper = Paper(
            paper_id="lm_paper",
            title="Scaling Transformer Language Models",
            year=2023,
            authors=[],
            venue="",
            citations=0,
        )
        lm_extraction = ComputationalAnalysis(parameters=10e9, gpu_hours=50000)
        score = self.validator._check_paper_consistency(lm_paper, lm_extraction)
        assert score > 0.8

        # Vision paper with batch size
        cv_paper = Paper(
            paper_id="cv_paper",
            title="Efficient Image Classification with CNNs",
            year=2022,
            authors=[],
            venue="",
            citations=0,
        )
        cv_extraction = ComputationalAnalysis(batch_size=128, parameters=50e6)
        score = self.validator._check_paper_consistency(cv_paper, cv_extraction)
        assert score > 0.7

    def test_quality_determination(self):
        """Test quality level determination."""
        assert self.validator._determine_quality(0.95) == ExtractionQuality.HIGH
        assert self.validator._determine_quality(0.85) == ExtractionQuality.MEDIUM
        assert self.validator._determine_quality(0.65) == ExtractionQuality.LOW
        assert self.validator._determine_quality(0.45) == ExtractionQuality.UNRELIABLE

    def test_cross_validate_extractions(self):
        """Test cross-validation between manual and automated."""
        manual = {"gpu_hours": 1000, "parameters": 7e9, "batch_size": 256}

        # Exact match
        automated = manual.copy()
        result = self.validator.cross_validate_extractions(manual, automated)
        assert result["agreement_score"] == 1.0
        assert len(result["discrepancies"]) == 0

        # Close match (within tolerance)
        automated = {
            "gpu_hours": 1050,  # 5% difference
            "parameters": 7.5e9,  # ~7% difference
            "batch_size": 256,
        }
        result = self.validator.cross_validate_extractions(manual, automated)
        assert result["agreement_score"] > 0.9
        assert len(result["discrepancies"]) < 2

        # Poor match
        automated = {
            "gpu_hours": 2000,  # 100% difference
            "parameters": 1e9,  # ~86% difference
            "batch_size": 512,  # 100% difference
        }
        result = self.validator.cross_validate_extractions(manual, automated)
        assert result["agreement_score"] < 0.5
        assert len(result["discrepancies"]) == 3
