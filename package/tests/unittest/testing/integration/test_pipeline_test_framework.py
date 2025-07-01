"""
Unit tests for End-to-End Pipeline Testing Framework
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# Import components to test (will fail initially)
from src.testing.integration.pipeline_test_framework import (
    PipelinePhase,
    PhaseMetrics,
    PipelineConfig,
    EndToEndTestFramework
)
from src.data.models import Paper


class TestPipelinePhase:
    """Test PipelinePhase enum"""
    
    def test_pipeline_phases_defined(self):
        """Test all required pipeline phases are defined"""
        assert PipelinePhase.COLLECTION.value == "collection"
        assert PipelinePhase.EXTRACTION.value == "extraction"
        assert PipelinePhase.ANALYSIS.value == "analysis"
        assert PipelinePhase.PROJECTION.value == "projection"
        assert PipelinePhase.REPORTING.value == "reporting"
        
    def test_phase_ordering(self):
        """Test phases maintain correct order"""
        phases = list(PipelinePhase)
        assert phases[0] == PipelinePhase.COLLECTION
        assert phases[-1] == PipelinePhase.REPORTING


class TestPhaseMetrics:
    """Test PhaseMetrics dataclass"""
    
    def test_phase_metrics_creation(self):
        """Test creating phase metrics"""
        metrics = PhaseMetrics(
            phase=PipelinePhase.COLLECTION,
            execution_time_seconds=10.5,
            memory_usage_mb=512.0,
            records_processed=100,
            errors_encountered=["error1", "error2"],
            success=True
        )
        
        assert metrics.phase == PipelinePhase.COLLECTION
        assert metrics.execution_time_seconds == 10.5
        assert metrics.memory_usage_mb == 512.0
        assert metrics.records_processed == 100
        assert len(metrics.errors_encountered) == 2
        assert metrics.success is True


class TestPipelineConfig:
    """Test PipelineConfig dataclass"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = PipelineConfig()
        
        assert config.test_data_size == 1000
        assert config.max_execution_time_seconds == 300
        assert config.max_memory_usage_mb == 4096
        assert config.enable_profiling is True
        
    def test_custom_configuration(self):
        """Test custom configuration"""
        config = PipelineConfig(
            test_data_size=5000,
            max_execution_time_seconds=600,
            phases_to_test=[PipelinePhase.COLLECTION, PipelinePhase.ANALYSIS]
        )
        
        assert config.test_data_size == 5000
        assert config.max_execution_time_seconds == 600
        assert len(config.phases_to_test) == 2


class TestEndToEndTestFramework:
    """Test EndToEndTestFramework class"""
    
    @pytest.fixture
    def framework(self):
        """Create test framework instance"""
        config = PipelineConfig()
        return EndToEndTestFramework(config)
        
    def test_framework_initialization(self, framework):
        """Test framework initializes correctly"""
        assert framework.config is not None
        assert framework.phase_validators == {}
        
    def test_register_phase_validator(self, framework):
        """Test registering custom phase validators"""
        mock_validator = Mock(return_value=True)
        
        framework.register_phase_validator(
            PipelinePhase.COLLECTION,
            mock_validator
        )
        
        assert PipelinePhase.COLLECTION in framework.phase_validators
        assert framework.phase_validators[PipelinePhase.COLLECTION] == mock_validator
        
    def test_run_pipeline_basic(self, framework):
        """Test basic pipeline execution"""
        # Create test data
        test_papers = [
            Mock(spec=Paper, paper_id=f"paper_{i}") 
            for i in range(10)
        ]
        
        # Run pipeline
        result = framework.run_pipeline(test_papers)
        
        # Verify result structure
        assert "phases_completed" in result
        assert "total_duration" in result
        assert "phase_metrics" in result
        assert "success" in result
        
    def test_validate_phase_transition(self, framework):
        """Test phase transition validation"""
        # Test valid transition
        assert framework.validate_phase_transition(
            PipelinePhase.COLLECTION,
            PipelinePhase.EXTRACTION,
            {"papers": [1, 2, 3]}
        ) is True
        
        # Test invalid transition (skipping phases)
        assert framework.validate_phase_transition(
            PipelinePhase.COLLECTION,
            PipelinePhase.PROJECTION,
            {"papers": [1, 2, 3]}
        ) is False
        
    def test_get_performance_report(self, framework):
        """Test performance report generation"""
        # Run a pipeline first
        test_papers = [Mock(spec=Paper) for _ in range(5)]
        framework.run_pipeline(test_papers)
        
        # Get performance report
        report = framework.get_performance_report()
        
        assert isinstance(report, dict)
        assert all(isinstance(metrics, PhaseMetrics) for metrics in report.values())
        
    def test_pipeline_with_errors(self, framework):
        """Test pipeline handles errors gracefully"""
        # Create test data that will cause errors
        test_papers = [Mock(spec=Paper, paper_id=None)]  # Invalid paper
        
        result = framework.run_pipeline(test_papers)
        
        assert result["success"] is False
        assert len(result.get("errors", [])) > 0
        
    def test_memory_monitoring(self, framework):
        """Test memory usage monitoring during pipeline"""
        test_papers = [Mock(spec=Paper) for _ in range(100)]
        
        result = framework.run_pipeline(test_papers)
        
        # Check memory metrics exist for each phase
        for phase_name, metrics in result["phase_metrics"].items():
            assert metrics.memory_usage_mb > 0
            assert metrics.memory_usage_mb < framework.config.max_memory_usage_mb
            
    def test_execution_time_limits(self, framework):
        """Test pipeline respects execution time limits"""
        # Configure strict time limit
        framework.config.max_execution_time_seconds = 1
        
        # Create slow validator
        def slow_validator(data):
            time.sleep(2)
            return True
            
        framework.register_phase_validator(
            PipelinePhase.COLLECTION,
            slow_validator
        )
        
        test_papers = [Mock(spec=Paper)]
        result = framework.run_pipeline(test_papers)
        
        assert result["success"] is False
        assert "timed out" in str(result.get("errors", [])).lower()
        
    def test_phase_filtering(self, framework):
        """Test running only specific phases"""
        framework.config.phases_to_test = [
            PipelinePhase.COLLECTION,
            PipelinePhase.ANALYSIS
        ]
        
        test_papers = [Mock(spec=Paper) for _ in range(5)]
        result = framework.run_pipeline(test_papers)
        
        # Only configured phases should be in results
        assert PipelinePhase.COLLECTION.value in result["phase_metrics"]
        assert PipelinePhase.ANALYSIS.value in result["phase_metrics"]
        assert PipelinePhase.EXTRACTION.value not in result["phase_metrics"]