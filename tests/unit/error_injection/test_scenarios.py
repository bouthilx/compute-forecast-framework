"""Test suite for error injection scenarios."""

import pytest
from compute_forecast.testing.error_injection.scenarios import (
    APIFailureScenarios,
    DataCorruptionScenarios,
    ResourceExhaustionScenarios
)
from compute_forecast.testing.error_injection import ErrorType


class TestAPIFailureScenarios:
    """Test API failure scenarios."""
    
    def test_get_timeout_cascade_scenario(self):
        """Test timeout cascade scenario creation."""
        scenarios = APIFailureScenarios.get_timeout_cascade_scenario()
        
        assert len(scenarios) == 3
        assert all(s.error_type == ErrorType.API_TIMEOUT for s in scenarios)
        assert scenarios[0].component == "semantic_scholar"
        assert scenarios[1].component == "openalex"
        assert scenarios[2].component == "crossref"
    
    def test_get_rate_limit_scenario(self):
        """Test rate limit scenario creation."""
        scenarios = APIFailureScenarios.get_rate_limit_scenario()
        
        assert len(scenarios) == 2
        assert all(s.error_type == ErrorType.API_RATE_LIMIT for s in scenarios)
    
    def test_get_mixed_api_failures_scenario(self):
        """Test mixed API failures scenario."""
        scenarios = APIFailureScenarios.get_mixed_api_failures_scenario()
        
        assert len(scenarios) >= 4  # At least 4 mixed scenarios
        error_types = {s.error_type for s in scenarios}
        assert ErrorType.API_TIMEOUT in error_types
        assert ErrorType.API_RATE_LIMIT in error_types
        # Check we have network error instead of auth failure
        assert ErrorType.NETWORK_ERROR in error_types
    
    def test_validate_api_recovery(self):
        """Test API recovery validation."""
        # Test successful recovery
        result = APIFailureScenarios.validate_api_recovery({
            "avg_recovery_time": 120.0,  # 2 minutes
            "fallback_success_rate": 0.98,
            "cascade_failures": 0
        })
        
        assert result["passed"] is True
        assert len(result["checks"]) > 0
        
        # Test failed recovery
        result = APIFailureScenarios.validate_api_recovery({
            "avg_recovery_time": 360.0,  # 6 minutes - too long
            "fallback_success_rate": 0.80,  # Below threshold
            "cascade_failures": 3
        })
        
        assert result["passed"] is False
        assert len(result["failures"]) > 0


class TestDataCorruptionScenarios:
    """Test data corruption scenarios."""
    
    def test_get_paper_corruption_scenario(self):
        """Test paper corruption scenario creation."""
        scenarios = DataCorruptionScenarios.get_paper_corruption_scenario()
        
        assert len(scenarios) == 2
        assert scenarios[0].error_type == ErrorType.DATA_CORRUPTION
        assert scenarios[0].component == "paper_parser"
        assert scenarios[1].error_type == ErrorType.INVALID_DATA_FORMAT
    
    def test_get_venue_data_corruption_scenario(self):
        """Test venue data corruption scenario."""
        scenarios = DataCorruptionScenarios.get_venue_data_corruption_scenario()
        
        assert len(scenarios) == 2
        assert all(s.error_type == ErrorType.DATA_CORRUPTION for s in scenarios)
        assert scenarios[0].component == "venue_normalizer"
        assert scenarios[1].component == "venue_database"
    
    def test_get_checkpoint_corruption_scenario(self):
        """Test checkpoint corruption scenario."""
        scenarios = DataCorruptionScenarios.get_checkpoint_corruption_scenario()
        
        assert len(scenarios) == 2
        assert scenarios[0].severity == "critical"
        assert scenarios[1].component == "state_persistence"
    
    def test_get_progressive_corruption_scenario(self):
        """Test progressive corruption scenario."""
        scenarios = DataCorruptionScenarios.get_progressive_corruption_scenario()
        
        assert len(scenarios) == 5
        # Check progression
        assert scenarios[0].probability < scenarios[-1].probability
        assert scenarios[0].severity == "low"
        assert scenarios[-1].severity == "high"
    
    def test_validate_data_integrity(self):
        """Test data integrity validation."""
        # Test passing validation
        result = DataCorruptionScenarios.validate_data_integrity({
            "data_preservation_rate": 0.97,
            "corruption_detection_rate": 0.995,
            "corruption_recovery_rate": 0.96,
            "critical_data_loss": False
        })
        
        assert result["passed"] is True
        assert len(result["checks"]) == 4
        
        # Test failing validation
        result = DataCorruptionScenarios.validate_data_integrity({
            "data_preservation_rate": 0.90,  # Below threshold
            "corruption_detection_rate": 0.95,  # Below threshold
            "corruption_recovery_rate": 0.80,  # Below threshold
            "critical_data_loss": True
        })
        
        assert result["passed"] is False
        assert len(result["failures"]) == 4


class TestResourceExhaustionScenarios:
    """Test resource exhaustion scenarios."""
    
    def test_get_memory_exhaustion_scenario(self):
        """Test memory exhaustion scenario creation."""
        scenarios = ResourceExhaustionScenarios.get_memory_exhaustion_scenario()
        
        assert len(scenarios) == 2
        assert all(s.error_type == ErrorType.MEMORY_EXHAUSTION for s in scenarios)
        assert scenarios[0].component == "analyzer"
        assert scenarios[1].component == "deduplicator"
    
    def test_get_disk_space_scenario(self):
        """Test disk space exhaustion scenario."""
        scenarios = ResourceExhaustionScenarios.get_disk_space_scenario()
        
        assert len(scenarios) == 2
        assert all(s.error_type == ErrorType.DISK_FULL for s in scenarios)
        assert scenarios[0].recovery_expected is False  # Disk full needs manual intervention
        assert scenarios[1].recovery_expected is True  # Report writer can use alternatives
    
    def test_get_cpu_exhaustion_scenario(self):
        """Test CPU exhaustion scenario."""
        scenarios = ResourceExhaustionScenarios.get_cpu_exhaustion_scenario()
        
        assert len(scenarios) == 1
        assert scenarios[0].error_type == ErrorType.COMPONENT_CRASH
        assert scenarios[0].metadata["cause"] == "cpu_exhaustion"
    
    def test_get_progressive_resource_exhaustion_scenario(self):
        """Test progressive resource exhaustion."""
        scenarios = ResourceExhaustionScenarios.get_progressive_resource_exhaustion_scenario()
        
        assert len(scenarios) == 5
        # Check memory limits decrease
        memory_limits = [s.metadata["memory_limit_mb"] for s in scenarios]
        assert memory_limits == [2000, 1000, 500, 250, 100]
        
        # Check severity increases
        assert scenarios[0].severity == "low"
        assert scenarios[-1].severity == "critical"
        
        # Check recovery expectation
        assert scenarios[-1].recovery_expected is False
    
    def test_get_multi_resource_scenario(self):
        """Test multi-resource exhaustion scenario."""
        scenarios = ResourceExhaustionScenarios.get_multi_resource_scenario()
        
        assert len(scenarios) == 3
        error_types = {s.error_type for s in scenarios}
        assert ErrorType.MEMORY_EXHAUSTION in error_types
        assert ErrorType.DISK_FULL in error_types
        assert ErrorType.COMPONENT_CRASH in error_types
    
    def test_validate_resource_recovery(self):
        """Test resource recovery validation."""
        # Test successful validation
        result = ResourceExhaustionScenarios.validate_resource_recovery({
            "memory_recovery_success_rate": 0.95,
            "graceful_degradation_rate": 0.98,
            "resource_optimization_effective": True,
            "resource_cascade_failures": 0
        })
        
        assert result["passed"] is True
        assert len(result["checks"]) == 4
        
        # Test failed validation
        result = ResourceExhaustionScenarios.validate_resource_recovery({
            "memory_recovery_success_rate": 0.85,  # Below threshold
            "graceful_degradation_rate": 0.90,  # Below threshold
            "resource_optimization_effective": False,
            "resource_cascade_failures": 2
        })
        
        assert result["passed"] is False
        assert len(result["failures"]) == 4