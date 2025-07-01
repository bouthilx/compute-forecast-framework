"""Tests for Error Injection Framework."""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
from typing import Dict, Any

from src.testing.error_injection.injection_framework import (
    ErrorType, ErrorScenario, ErrorInjectionFramework
)


class TestErrorInjectionFramework:
    """Test suite for ErrorInjectionFramework."""
    
    def test_initialization(self):
        """Test framework initialization."""
        framework = ErrorInjectionFramework()
        
        assert framework.scenarios == []
        assert framework.injection_points == {}
        assert framework._active_injections == {}
        assert framework._injection_history == []
    
    def test_register_injection_point(self):
        """Test registering injection points."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        assert "api_client" in framework.injection_points
        assert framework.injection_points["api_client"] == mock_injector
    
    def test_register_duplicate_injection_point(self):
        """Test registering duplicate injection point overwrites."""
        framework = ErrorInjectionFramework()
        mock_injector1 = Mock()
        mock_injector2 = Mock()
        
        framework.register_injection_point("api_client", mock_injector1)
        framework.register_injection_point("api_client", mock_injector2)
        
        assert framework.injection_points["api_client"] == mock_injector2
    
    def test_add_scenario(self):
        """Test adding error scenarios."""
        framework = ErrorInjectionFramework()
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="semantic_scholar",
            probability=0.5,
            severity="high",
            recovery_expected=True,
            max_recovery_time_seconds=30.0
        )
        
        framework.add_scenario(scenario)
        
        assert len(framework.scenarios) == 1
        assert framework.scenarios[0] == scenario
    
    def test_inject_error_without_injection_point(self):
        """Test error injection fails without registered injection point."""
        framework = ErrorInjectionFramework()
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="unknown_component",
            probability=1.0
        )
        
        with pytest.raises(ValueError, match="No injection point registered"):
            framework.inject_error(scenario)
    
    def test_inject_error_success(self):
        """Test successful error injection."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            probability=1.0
        )
        
        framework.inject_error(scenario)
        
        mock_injector.assert_called_once_with(ErrorType.API_TIMEOUT)
        assert "api_client" in framework._active_injections
        assert len(framework._injection_history) == 1
    
    def test_inject_error_with_probability(self):
        """Test error injection respects probability."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            probability=0.0  # Never inject
        )
        
        # Try multiple times, should never inject
        for _ in range(10):
            framework.inject_error(scenario)
        
        mock_injector.assert_not_called()
    
    @patch('random.random')
    def test_inject_error_probability_threshold(self, mock_random):
        """Test error injection at probability threshold."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            probability=0.5
        )
        
        # Test when random < probability (should inject)
        mock_random.return_value = 0.3
        framework.inject_error(scenario)
        mock_injector.assert_called_once()
        
        # Test when random >= probability (should not inject)
        mock_injector.reset_mock()
        mock_random.return_value = 0.7
        framework.inject_error(scenario)
        mock_injector.assert_not_called()
    
    def test_run_scenario_suite(self):
        """Test running a suite of error scenarios."""
        framework = ErrorInjectionFramework()
        
        # Register injection points
        mock_api_injector = Mock()
        mock_parser_injector = Mock()
        framework.register_injection_point("api_client", mock_api_injector)
        framework.register_injection_point("parser", mock_parser_injector)
        
        # Add scenarios
        scenarios = [
            ErrorScenario(
                error_type=ErrorType.API_TIMEOUT,
                component="api_client",
                probability=1.0,
                severity="high"
            ),
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                component="parser",
                probability=1.0,
                severity="medium"
            ),
            ErrorScenario(
                error_type=ErrorType.API_RATE_LIMIT,
                component="api_client",
                probability=1.0,
                severity="low"
            )
        ]
        
        for scenario in scenarios:
            framework.add_scenario(scenario)
        
        # Run scenario suite
        results = framework.run_scenario_suite()
        
        # Verify all scenarios were executed
        assert results["total_scenarios"] == 3
        assert results["scenarios_executed"] == 3
        assert results["injection_success_rate"] == 1.0
        
        # Verify injection points were called correctly
        assert mock_api_injector.call_count == 2
        assert mock_parser_injector.call_count == 1
        
        # Verify injection history
        assert len(framework._injection_history) == 3
    
    def test_get_active_injections(self):
        """Test getting active injections."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            probability=1.0
        )
        
        # Before injection
        assert framework.get_active_injections() == {}
        
        # After injection
        framework.inject_error(scenario)
        active = framework.get_active_injections()
        
        assert "api_client" in active
        assert active["api_client"]["error_type"] == ErrorType.API_TIMEOUT
        assert "timestamp" in active["api_client"]
    
    def test_clear_injection(self):
        """Test clearing specific injection."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        scenario = ErrorScenario(
            error_type=ErrorType.API_TIMEOUT,
            component="api_client",
            probability=1.0
        )
        
        framework.inject_error(scenario)
        assert "api_client" in framework._active_injections
        
        framework.clear_injection("api_client")
        assert "api_client" not in framework._active_injections
    
    def test_clear_all_injections(self):
        """Test clearing all injections."""
        framework = ErrorInjectionFramework()
        
        # Setup multiple injection points
        for component in ["api_client", "parser", "analyzer"]:
            framework.register_injection_point(component, Mock())
            scenario = ErrorScenario(
                error_type=ErrorType.API_TIMEOUT,
                component=component,
                probability=1.0
            )
            framework.inject_error(scenario)
        
        assert len(framework._active_injections) == 3
        
        framework.clear_all_injections()
        assert len(framework._active_injections) == 0
    
    def test_get_injection_history(self):
        """Test getting injection history."""
        framework = ErrorInjectionFramework()
        mock_injector = Mock()
        
        framework.register_injection_point("api_client", mock_injector)
        
        # Inject multiple errors
        for error_type in [ErrorType.API_TIMEOUT, ErrorType.API_RATE_LIMIT]:
            scenario = ErrorScenario(
                error_type=error_type,
                component="api_client",
                probability=1.0
            )
            framework.inject_error(scenario)
        
        history = framework.get_injection_history()
        
        assert len(history) == 2
        assert all("component" in record for record in history)
        assert all("error_type" in record for record in history)
        assert all("timestamp" in record for record in history)
        assert all("severity" in record for record in history)
    
    def test_get_injection_statistics(self):
        """Test getting injection statistics."""
        framework = ErrorInjectionFramework()
        
        # Setup components
        components = ["api_client", "parser"]
        for component in components:
            framework.register_injection_point(component, Mock())
        
        # Inject various errors
        error_configs = [
            (ErrorType.API_TIMEOUT, "api_client", "high"),
            (ErrorType.API_TIMEOUT, "api_client", "high"),
            (ErrorType.DATA_CORRUPTION, "parser", "medium"),
            (ErrorType.API_RATE_LIMIT, "api_client", "low"),
        ]
        
        for error_type, component, severity in error_configs:
            scenario = ErrorScenario(
                error_type=error_type,
                component=component,
                probability=1.0,
                severity=severity
            )
            framework.inject_error(scenario)
        
        stats = framework.get_injection_statistics()
        
        assert stats["total_injections"] == 4
        assert stats["by_component"]["api_client"] == 3
        assert stats["by_component"]["parser"] == 1
        assert stats["by_error_type"][ErrorType.API_TIMEOUT] == 2
        assert stats["by_error_type"][ErrorType.DATA_CORRUPTION] == 1
        assert stats["by_error_type"][ErrorType.API_RATE_LIMIT] == 1
        assert stats["by_severity"]["high"] == 2
        assert stats["by_severity"]["medium"] == 1
        assert stats["by_severity"]["low"] == 1