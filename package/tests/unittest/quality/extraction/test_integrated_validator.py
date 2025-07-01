"""
Tests for IntegratedExtractionValidator.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.quality.extraction.integrated_validator import (
    IntegratedExtractionValidator,
    IntegratedValidationResult
)
from src.quality.extraction.extraction_validator import ExtractionQuality
from src.data.models import Paper
from .test_helpers import MockComputationalAnalysis as ComputationalAnalysis


class TestIntegratedExtractionValidator:
    """Test integrated extraction validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IntegratedExtractionValidator()
        
        # Create test paper
        self.paper = Paper(paper_id="test_paper_1",
            title="Large Language Model Training",
            year=2023,
            authors=[],
            venue="",
            citations=0)
        
        # Create test extraction
        self.extraction = ComputationalAnalysis(
            gpu_hours=1000,
            gpu_type="A100",
            gpu_count=8,
            training_time=125,
            parameters=7e9,
            batch_size=256
        )
        
        # Create paper group for consistency checks
        self.paper_group = []
        for i in range(5):
            paper = Paper(paper_id=f"similar_{i}",
            title=f"Similar Language Model {i}",
            year=2023,
            authors=[],
            venue="",
            citations=0)
            paper.computational_analysis = ComputationalAnalysis(
                gpu_hours=800 + i * 100,  # 800-1200
                parameters=(6 + i * 0.5) * 1e9,  # 6-8e9
                training_time=100 + i * 10  # 100-140
            )
            self.paper_group.append(paper)
    
    def test_validate_single_extraction(self):
        """Test validation of single extraction."""
        result = self.validator.validate_extraction(
            self.paper,
            self.extraction,
            self.paper_group
        )
        
        assert isinstance(result, IntegratedValidationResult)
        assert result.paper_id == "test_paper_1"
        assert result.extraction_validation is not None
        assert len(result.consistency_checks) > 0
        assert isinstance(result.outlier_fields, list)
        assert result.overall_quality in ["high", "medium", "low", "unreliable"]
        assert isinstance(result.recommendations, list)
        assert 0 <= result.confidence <= 1
    
    def test_validate_extraction_batch(self):
        """Test batch validation."""
        extractions = [
            (self.paper, self.extraction)
        ] + [(p, p.computational_analysis) for p in self.paper_group]
        
        report = self.validator.validate_extraction_batch(extractions)
        
        assert "summary" in report
        assert "temporal_consistency" in report
        assert "recommendations" in report
        assert "details" in report
        
        # Check summary
        summary = report["summary"]
        assert summary["total_extractions"] == 6
        assert "average_confidence" in summary
        assert "quality_distribution" in summary
        
        # Check temporal consistency
        temporal = report["temporal_consistency"]
        assert "gpu_hours" in temporal
        assert "parameters" in temporal
    
    def test_quality_calculation(self):
        """Test overall quality calculation."""
        # High quality extraction
        high_quality_extraction = ComputationalAnalysis(
            gpu_hours=1000,
            gpu_type="A100",
            gpu_count=8,
            training_time=125,
            parameters=7e9,
            gpu_memory=80,
            batch_size=256,
            dataset_size=1e12,
            epochs=3,
            framework="pytorch"
        )
        
        result = self.validator.validate_extraction(
            self.paper,
            high_quality_extraction,
            self.paper_group
        )
        
        assert result.overall_quality in ["high", "medium"]
        assert result.confidence > 0.7
    
    def test_outlier_detection_integration(self):
        """Test outlier detection in integrated validation."""
        # Create outlier extraction
        outlier_extraction = ComputationalAnalysis(
            gpu_hours=1000000,  # Extreme outlier
            parameters=7e9,
            training_time=125000  # Extreme outlier
        )
        
        # Need more papers for outlier detection
        large_group = self.paper_group * 5  # 25 papers
        
        result = self.validator.validate_extraction(
            self.paper,
            outlier_extraction,
            large_group
        )
        
        # Should detect outliers
        assert len(result.outlier_fields) > 0
        assert "gpu_hours" in result.outlier_fields or "training_time" in result.outlier_fields
    
    def test_recommendations_generation(self):
        """Test recommendation generation."""
        # Incomplete extraction
        incomplete_extraction = ComputationalAnalysis(
            gpu_hours=100
        )
        
        result = self.validator.validate_extraction(
            self.paper,
            incomplete_extraction
        )
        
        assert len(result.recommendations) > 0
        assert any("completeness" in r.lower() for r in result.recommendations)
    
    def test_load_validation_rules(self):
        """Test validation rules loading."""
        # Test with default path
        rules = self.validator._load_validation_rules(None)
        assert "completeness_rules" in rules
        assert "quality_thresholds" in rules
        
        # Test with non-existent path
        rules = self.validator._load_validation_rules("/non/existent/path.yaml")
        assert "completeness_rules" in rules  # Should return defaults
    
    def test_domain_grouping(self):
        """Test paper grouping by domain."""
        papers = [
            (Paper(paper_id="1", title="Transformer NLP Model",
            year=2023,
            authors=[],
            venue="",
            citations=0), None),
            (Paper(paper_id="2", title="CNN Image Classification",
            year=2023,
            authors=[],
            venue="",
            citations=0), None),
            (Paper(paper_id="3", title="RL Agent Training",
            year=2023,
            authors=[],
            venue="",
            citations=0), None),
            (Paper(paper_id="4", title="BERT Language Understanding",
            year=2023,
            authors=[],
            venue="",
            citations=0), None)
        ]
        
        groups = self.validator._group_papers_by_domain(papers)
        
        assert "nlp" in groups
        assert "cv" in groups
        assert "rl" in groups
        assert len(groups["nlp"]) == 2  # Two NLP papers
    
    def test_consistency_checks(self):
        """Test consistency check integration."""
        result = self.validator.validate_extraction(
            self.paper,
            self.extraction,
            self.paper_group
        )
        
        # Should have multiple consistency checks
        assert len(result.consistency_checks) >= 2
        
        # Check types
        check_types = [c.check_type for c in result.consistency_checks]
        assert "domain_specific" in check_types
        assert "scaling_law" in check_types
    
    def test_batch_cache_usage(self):
        """Test batch cache for efficiency."""
        extractions = [(p, p.computational_analysis) for p in self.paper_group]
        
        # First call builds cache
        self.validator.validate_extraction_batch(extractions)
        
        # Cache should be populated
        assert len(self.validator._batch_cache) > 0
        assert "gpu_hours" in self.validator._batch_cache
        assert "parameters" in self.validator._batch_cache
    
    def test_calibration_integration(self):
        """Test cross-validation calibration integration."""
        # Mock manual data availability
        with patch.object(self.validator, '_has_manual_data', return_value=True):
            with patch.object(self.validator, '_separate_manual_auto', return_value=({}, {})):
                with patch.object(self.validator.cross_validator, 'validate_extraction_quality',
                                return_value={"overall_accuracy": 0.9}):
                    
                    extractions = [(self.paper, self.extraction)]
                    report = self.validator.validate_extraction_batch(extractions)
                    
                    assert report["cross_validation"] is not None
                    assert report["cross_validation"]["overall_accuracy"] == 0.9