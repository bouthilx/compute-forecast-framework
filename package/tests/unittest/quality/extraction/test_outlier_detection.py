"""
Tests for OutlierDetector.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from src.quality.extraction.outlier_detection import (
    OutlierDetector,
    OutlierMethod,
    OutlierResult
)
from src.data.models import Paper


class TestOutlierDetector:
    """Test outlier detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = OutlierDetector()
        
        # Create test data
        np.random.seed(42)
        self.normal_values = list(np.random.normal(100, 10, 100))
        self.values_with_outliers = self.normal_values[:95] + [500, 600, 10, 5, 1000]
    
    def test_detect_z_score_outliers(self):
        """Test z-score outlier detection."""
        outliers = self.detector.detect_outliers(
            self.values_with_outliers, 
            method="z_score"
        )
        
        assert len(outliers) > 0
        # Should detect the extreme values
        assert 95 in outliers or 96 in outliers  # 500, 600
        assert 99 in outliers  # 1000
    
    def test_detect_iqr_outliers(self):
        """Test IQR outlier detection."""
        outliers = self.detector.detect_outliers(
            self.values_with_outliers,
            method="iqr"
        )
        
        assert len(outliers) > 0
        # Should detect extreme values
        assert any(i >= 95 for i in outliers)
    
    def test_detect_isolation_forest_outliers(self):
        """Test isolation forest outlier detection."""
        outliers = self.detector.detect_outliers(
            self.values_with_outliers,
            method="isolation_forest"
        )
        
        assert len(outliers) > 0
    
    def test_detect_combined_outliers(self):
        """Test combined outlier detection."""
        outliers = self.detector.detect_outliers(
            self.values_with_outliers,
            method="combined"
        )
        
        # Combined method should be more conservative
        assert len(outliers) > 0
        assert len(outliers) <= 10  # Not too many false positives
    
    def test_field_specific_thresholds(self):
        """Test field-specific threshold application."""
        # GPU hours should be more tolerant
        gpu_hours_outliers = self.detector.detect_outliers(
            self.values_with_outliers,
            method="z_score",
            field="gpu_hours"
        )
        
        # Batch size should be stricter
        batch_size_outliers = self.detector.detect_outliers(
            self.values_with_outliers,
            method="z_score",
            field="batch_size"
        )
        
        # Different thresholds should give different results
        assert len(gpu_hours_outliers) <= len(batch_size_outliers)
    
    def test_insufficient_data(self):
        """Test with insufficient data."""
        outliers = self.detector.detect_outliers([10, 20], method="z_score")
        assert len(outliers) == 0
    
    def test_contextualize_outlier_known_extreme(self):
        """Test contextualizing known extreme values."""
        paper = Paper(
            paper_id="gpt3_paper",
            title=f"GPT-3: Language Models are Few-Shot Learners",
            year=2020,
            authors=[],
            venue="",
            citations=5000
        )
        
        # GPT-3 parameter count
        context = self.detector.contextualize_outlier(paper, "parameters", 175e9)
        
        assert context["severity"] == "expected"
        assert any("known extreme" in reason for reason in context["reasons"])
    
    def test_contextualize_outlier_novel_architecture(self):
        """Test contextualizing novel architecture."""
        paper = Paper(paper_id="novel_paper",
            title="Introducing a Novel Transformer Architecture",
            year=2023,
            authors=[],
            venue="",
            citations=0)
        
        context = self.detector.contextualize_outlier(paper, "parameters", 50e9)
        
        assert any("novel architecture" in reason for reason in context["reasons"])
        assert context["severity"] == "possible"
    
    def test_contextualize_outlier_scale_indicator(self):
        """Test contextualizing with scale indicators."""
        paper = Paper(paper_id="large_paper",
            title="Training Massive Language Models at Scale",
            year=2023,
            authors=[],
            venue="",
            citations=0)
        
        context = self.detector.contextualize_outlier(paper, "gpu_hours", 1e6)
        
        assert any("large scale" in reason for reason in context["reasons"])
        assert context["severity"] == "expected"
    
    def test_contextualize_outlier_efficiency_contradiction(self):
        """Test contextualizing efficiency contradiction."""
        paper = Paper(paper_id="efficient_paper",
            title="Efficient Lightweight Model Training",
            year=2023,
            authors=[],
            venue="",
            citations=0)
        
        # High GPU hours despite efficiency claims
        self.detector._get_field_median = lambda x: 1000  # Mock median
        context = self.detector.contextualize_outlier(paper, "gpu_hours", 50000)
        
        assert any("efficiency claims" in reason for reason in context["reasons"])
        assert context["severity"] == "suspicious"
    
    def test_contextualize_outlier_temporal(self):
        """Test temporal context for outliers."""
        # Old paper with modern-scale parameters
        old_paper = Paper(paper_id="old_paper",
            title="Deep Learning Model",
            year=2015,
            authors=[],
            venue="",
            citations=0)
        
        context = self.detector.contextualize_outlier(old_paper, "parameters", 100e9)
        
        assert any("2015" in reason for reason in context["reasons"])
        assert context["severity"] == "suspicious"
    
    def test_verify_outlier_expected(self):
        """Test automatic verification of expected outliers."""
        paper = Paper(paper_id="gpt3",
            title="GPT-3: Language Models are Few-Shot Learners",
            year=2020,
            authors=[],
            venue="",
            citations=0)
        
        extraction = {
            "parameters": 175e9,
            "gpu_hours": 3.64e6
        }
        
        # Should verify as valid
        is_valid = self.detector.verify_outlier(paper, extraction, "parameters", 175e9)
        assert is_valid is True
    
    def test_verify_outlier_corroborating_evidence(self):
        """Test verification with corroborating evidence."""
        paper = Paper(paper_id="test", title="Large Model",
            year=2023,
            authors=[],
            venue="",
            citations=0)
        
        # High parameters with high GPU hours (corroborating)
        extraction = {
            "parameters": 50e9,
            "gpu_hours": 100000
        }
        is_valid = self.detector.verify_outlier(paper, extraction, "parameters", 50e9)
        assert is_valid is True
        
        # High parameters with low GPU hours (suspicious)
        extraction = {
            "parameters": 50e9,
            "gpu_hours": 100
        }
        is_valid = self.detector.verify_outlier(paper, extraction, "parameters", 50e9)
        assert is_valid is False
    
    def test_check_field_consistency(self):
        """Test field consistency checking."""
        # Consistent GPU hours
        extraction = {
            "gpu_count": 8,
            "training_time": 100,
            "gpu_hours": 800  # 8 * 100
        }
        is_consistent = self.detector._check_field_consistency(
            extraction, "gpu_hours", 800
        )
        assert is_consistent is True
        
        # Inconsistent GPU hours
        extraction = {
            "gpu_count": 8,
            "training_time": 100,
            "gpu_hours": 2000  # Should be 800
        }
        is_consistent = self.detector._check_field_consistency(
            extraction, "gpu_hours", 2000
        )
        assert is_consistent is False
    
    def test_analyze_outlier_pattern(self):
        """Test outlier pattern analysis."""
        # Create outlier results
        outliers = [
            OutlierResult(
                index=0,
                value=1000,
                method=OutlierMethod.Z_SCORE,
                score=4.5,
                reason="High z-score"
            ),
            OutlierResult(
                index=1,
                value=2000,
                method=OutlierMethod.IQR,
                score=5.0,
                reason="Outside IQR"
            )
        ]
        
        # Add field attribute for testing
        outliers[0].field = "gpu_hours"
        outliers[1].field = "gpu_hours"
        
        papers = [
            Paper(paper_id="1", title="Paper 1", year=2022,
            authors=[],
            venue="",
            citations=0),
            Paper(paper_id="2", title="Paper 2", year=2023,
            authors=[],
            venue="",
            citations=0)
        ]
        
        pattern_analysis = self.detector.analyze_outlier_pattern(outliers, papers)
        
        assert pattern_analysis["total_outliers"] == 2
        assert pattern_analysis["outlier_rate"] == 1.0
        assert "gpu_hours" in pattern_analysis["outliers_by_field"]
        assert pattern_analysis["outliers_by_field"]["gpu_hours"] == 2
    
    def test_no_outliers(self):
        """Test behavior with no outliers."""
        normal_data = list(np.random.normal(100, 5, 50))
        outliers = self.detector.detect_outliers(normal_data, method="combined")
        
        # Should detect few or no outliers in normal data
        assert len(outliers) < 3