"""Tests for Recovery Validator."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from src.testing.error_injection.recovery_validator import (
    RecoveryMetrics, RecoveryValidator
)
from src.testing.error_injection.injection_framework import ErrorType, ErrorScenario


class TestRecoveryValidator:
    """Test suite for RecoveryValidator."""
    
    @patch('src.testing.error_injection.recovery_validator.InterruptionRecoveryEngine')
    @patch('src.testing.error_injection.recovery_validator.StatePersistenceManager')
    def test_initialization(self, mock_state_manager, mock_recovery_engine):
        """Test validator initialization."""
        validator = RecoveryValidator()
        
        assert validator.recovery_engine is not None
        assert validator.state_manager is not None
        assert validator.validation_results == []
        assert validator.recovery_metrics == []
    
    def test_validate_recovery_successful(self):
        """Test successful recovery validation."""
        validator = RecoveryValidator()
        
        # Mock pre and post states
        pre_state = {
            "session_id": "test_session",
            "papers_collected": 100,
            "venues_completed": ["venue1", "venue2"],
            "timestamp": datetime.now() - timedelta(minutes=5)
        }
        
        post_state = {
            "session_id": "test_session",
            "papers_collected": 100,
            "venues_completed": ["venue1", "venue2"],
            "timestamp": datetime.now()
        }
        
        error_scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            recovery_expected=True,
            max_recovery_time_seconds=300.0
        )
        
        metrics = validator.validate_recovery(error_scenario, pre_state, post_state)
        
        assert metrics.error_type == ErrorType.API_TIMEOUT
        assert metrics.recovery_attempted is True
        assert metrics.recovery_successful is True
        assert metrics.data_loss_percentage == 0.0
        assert metrics.partial_results_available is True
    
    def test_validate_recovery_with_data_loss(self):
        """Test recovery validation with data loss."""
        validator = RecoveryValidator()
        
        # Mock states with data loss
        pre_state = {
            "papers_collected": 100,
            "venues_completed": ["venue1", "venue2", "venue3"],
            "data_size_bytes": 1000000
        }
        
        post_state = {
            "papers_collected": 95,  # Lost 5 papers
            "venues_completed": ["venue1", "venue2"],  # Lost venue3
            "data_size_bytes": 950000
        }
        
        error_scenario = ErrorScenario(
            error_type=ErrorType.DATA_CORRUPTION,
            component="parser",
            recovery_expected=True
        )
        
        metrics = validator.validate_recovery(error_scenario, pre_state, post_state)
        
        assert metrics.recovery_attempted is True
        assert metrics.recovery_successful is True  # Partial recovery is still success
        assert metrics.data_loss_percentage == 5.0  # 5% data loss
        assert metrics.partial_results_available is True
    
    def test_validate_recovery_failed(self):
        """Test failed recovery validation."""
        validator = RecoveryValidator()
        
        pre_state = {
            "papers_collected": 100,
            "status": "running"
        }
        
        # Post state shows complete failure
        post_state = {
            "papers_collected": 0,
            "status": "failed",
            "error": "Critical failure"
        }
        
        error_scenario = ErrorScenario(
            error_type=ErrorType.COMPONENT_CRASH,
            component="analyzer",
            recovery_expected=False
        )
        
        metrics = validator.validate_recovery(error_scenario, pre_state, post_state)
        
        assert metrics.recovery_attempted is True
        assert metrics.recovery_successful is False
        assert metrics.data_loss_percentage == 100.0
        assert metrics.partial_results_available is False
    
    def test_measure_data_integrity(self):
        """Test data integrity measurement."""
        validator = RecoveryValidator()
        
        # Test with identical data
        expected = {"papers": [1, 2, 3], "venues": ["a", "b"]}
        actual = {"papers": [1, 2, 3], "venues": ["a", "b"]}
        
        integrity = validator.measure_data_integrity(expected, actual)
        assert integrity == 100.0
        
        # Test with partial data
        expected = {"papers": [1, 2, 3, 4], "venues": ["a", "b", "c"]}
        actual = {"papers": [1, 2, 3], "venues": ["a", "b"]}
        
        integrity = validator.measure_data_integrity(expected, actual)
        assert integrity == 75.0  # 3/4 papers, 2/3 venues
    
    def test_measure_data_integrity_with_missing_fields(self):
        """Test data integrity with missing fields."""
        validator = RecoveryValidator()
        
        expected = {"papers": [1, 2, 3], "venues": ["a", "b"], "metadata": {}}
        actual = {"papers": [1, 2, 3]}  # Missing venues and metadata
        
        integrity = validator.measure_data_integrity(expected, actual)
        assert integrity < 100.0
    
    def test_verify_graceful_degradation_healthy(self):
        """Test graceful degradation verification for healthy component."""
        validator = RecoveryValidator()
        
        # Mock healthy component state
        validator.recovery_engine.get_recovery_status = Mock(return_value={
            "is_recovering": False,
            "recovery_attempts": 0
        })
        
        validator.state_manager.get_component_status = Mock(return_value={
            "status": "healthy",
            "error_count": 0
        })
        
        result = validator.verify_graceful_degradation("api_client", ErrorType.API_TIMEOUT)
        assert result is True
    
    def test_verify_graceful_degradation_degraded(self):
        """Test graceful degradation for degraded component."""
        validator = RecoveryValidator()
        
        # Mock degraded but functional component
        validator.recovery_engine.get_recovery_status = Mock(return_value={
            "is_recovering": True,
            "recovery_attempts": 2
        })
        
        validator.state_manager.get_component_status = Mock(return_value={
            "status": "degraded",
            "error_count": 5,
            "partial_functionality": True
        })
        
        result = validator.verify_graceful_degradation("api_client", ErrorType.API_RATE_LIMIT)
        assert result is True  # Degraded but still graceful
    
    def test_verify_graceful_degradation_failed(self):
        """Test graceful degradation verification for failed component."""
        validator = RecoveryValidator()
        
        # Mock completely failed component
        validator.recovery_engine.get_recovery_status = Mock(return_value={
            "is_recovering": False,
            "recovery_attempts": 10,
            "max_attempts": 3
        })
        
        validator.state_manager.get_component_status = Mock(return_value={
            "status": "failed",
            "error_count": 50,
            "partial_functionality": False
        })
        
        result = validator.verify_graceful_degradation("api_client", ErrorType.COMPONENT_CRASH)
        assert result is False
    
    def test_validate_recovery_time_within_limit(self):
        """Test recovery time validation within limit."""
        validator = RecoveryValidator()
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=120)  # 2 minutes
        
        result = validator.validate_recovery_time(
            start_time=start_time,
            end_time=end_time,
            max_recovery_seconds=300.0  # 5 minutes limit
        )
        
        assert result["within_limit"] is True
        assert result["recovery_time_seconds"] == 120.0
        assert result["limit_seconds"] == 300.0
    
    def test_validate_recovery_time_exceeds_limit(self):
        """Test recovery time validation exceeding limit."""
        validator = RecoveryValidator()
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=400)  # 6.67 minutes
        
        result = validator.validate_recovery_time(
            start_time=start_time,
            end_time=end_time,
            max_recovery_seconds=300.0  # 5 minutes limit
        )
        
        assert result["within_limit"] is False
        assert result["recovery_time_seconds"] == 400.0
        assert result["limit_seconds"] == 300.0
    
    def test_generate_validation_report(self):
        """Test validation report generation."""
        validator = RecoveryValidator()
        
        # Add some validation results
        validator.recovery_metrics = [
            RecoveryMetrics(
                error_type=ErrorType.API_TIMEOUT,
                recovery_attempted=True,
                recovery_successful=True,
                recovery_time_seconds=120.0,
                data_loss_percentage=0.0,
                partial_results_available=True
            ),
            RecoveryMetrics(
                error_type=ErrorType.DATA_CORRUPTION,
                recovery_attempted=True,
                recovery_successful=False,
                recovery_time_seconds=350.0,
                data_loss_percentage=15.0,
                partial_results_available=True
            )
        ]
        
        report = validator.generate_validation_report()
        
        assert report["total_validations"] == 2
        assert report["successful_recoveries"] == 1
        assert report["failed_recoveries"] == 1
        assert report["success_rate"] == 0.5
        assert report["average_recovery_time"] == 235.0  # (120 + 350) / 2
        assert report["average_data_loss"] == 7.5  # (0 + 15) / 2
        assert "by_error_type" in report
        assert "recommendations" in report
    
    def test_recommendations_generation(self):
        """Test recommendation generation based on metrics."""
        validator = RecoveryValidator()
        
        # Add various failure scenarios
        validator.recovery_metrics = [
            RecoveryMetrics(
                error_type=ErrorType.API_TIMEOUT,
                recovery_attempted=True,
                recovery_successful=False,
                recovery_time_seconds=400.0,  # Exceeds 5 min
                data_loss_percentage=0.0,
                partial_results_available=True
            ),
            RecoveryMetrics(
                error_type=ErrorType.DATA_CORRUPTION,
                recovery_attempted=True,
                recovery_successful=True,
                recovery_time_seconds=100.0,
                data_loss_percentage=10.0,  # >5% data loss
                partial_results_available=True
            )
        ]
        
        report = validator.generate_validation_report()
        recommendations = report["recommendations"]
        
        # Should recommend improvements for slow recovery and data loss
        assert any("recovery time" in rec.lower() for rec in recommendations)
        assert any("data integrity" in rec.lower() for rec in recommendations)