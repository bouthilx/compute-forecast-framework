"""Simple demonstration of error injection framework capabilities."""

from unittest.mock import Mock

from compute_forecast.testing.error_injection import (
    ErrorInjectionFramework,
    RecoveryValidator,
    ErrorType,
    ErrorScenario,
)
from compute_forecast.testing.error_injection.component_handlers import (
    CollectorErrorHandler,
    AnalyzerErrorHandler,
    ReporterErrorHandler,
)


def test_error_injection_framework_demo():
    """Demonstrate basic framework usage."""
    # 1. Create framework
    framework = ErrorInjectionFramework()

    # 2. Register injection points
    mock_api = Mock()
    framework.register_injection_point("test_api", mock_api)

    # 3. Create error scenario
    scenario = ErrorScenario(
        error_type=ErrorType.API_TIMEOUT,
        component="test_api",
        probability=1.0,  # Always inject
        severity="high",
        recovery_expected=True,
        max_recovery_time_seconds=60.0,
    )

    # 4. Add scenario to framework
    framework.add_scenario(scenario)

    # 5. Run scenario
    results = framework.run_scenario_suite()

    # Verify
    assert results["total_scenarios"] == 1
    assert results["scenarios_executed"] == 1
    assert mock_api.called


def test_collector_error_handler_demo():
    """Demonstrate collector error handler."""
    handler = CollectorErrorHandler()

    # Register multiple APIs
    handler.register_api("primary_api", Mock(), priority=10)
    handler.register_api("backup_api", Mock(), priority=5)

    # Initial state - primary API active
    assert handler.get_active_api() == "primary_api"

    # Simulate primary API failure
    handler.simulate_api_timeout("primary_api")

    # Should fallback to backup
    assert handler.get_active_api() == "backup_api"
    assert handler.verify_fallback_behavior() is True

    # Clear error
    handler.clear_error("primary_api")
    assert handler.get_active_api() == "primary_api"


def test_analyzer_error_handler_demo():
    """Demonstrate analyzer error handler."""
    handler = AnalyzerErrorHandler()

    # Set memory limit
    handler.set_memory_limit_mb(1000)
    assert handler.get_available_memory_mb() > 0

    # Simulate memory pressure
    handler.simulate_memory_pressure()
    assert handler.get_available_memory_mb() < 100  # Should be very low

    # Process papers with memory pressure
    handler.set_total_papers(10)
    result = handler.process_papers_batch(10)

    # Some should fail due to memory
    assert result["failed"] > 0
    assert any(
        e["error_type"] == ErrorType.MEMORY_EXHAUSTION.value for e in result["errors"]
    )


def test_reporter_error_handler_demo():
    """Demonstrate reporter error handler."""
    handler = ReporterErrorHandler()

    # Setup primary output
    handler.set_output_path("/primary/output")
    assert handler.can_write_output() is True

    # Add alternative output
    handler.add_alternative_output("memory://", "memory_buffer", "memory")

    # Simulate disk full
    handler.simulate_disk_full()
    assert handler.can_write_output() is False

    # Verify alternative output
    alt_result = handler.verify_alternative_output()
    assert alt_result["alternative_available"] is True
    assert alt_result["active_output"] == "memory_buffer"

    # Recovery should work
    recovery = handler.attempt_recovery()
    assert recovery["recovered"] is True


def test_recovery_validator_demo():
    """Demonstrate recovery validator."""
    validator = RecoveryValidator()

    # Create pre/post states
    pre_state = {"papers_collected": 100, "status": "running"}

    post_state = {
        "papers_collected": 95,  # Lost 5 papers
        "status": "recovered",
    }

    scenario = ErrorScenario(
        error_type=ErrorType.API_TIMEOUT,
        component="test_component",
        recovery_expected=True,
    )

    # Validate recovery
    metrics = validator.validate_recovery(scenario, pre_state, post_state)

    assert metrics.recovery_attempted is True
    assert metrics.recovery_successful is True
    # Data loss percentage is calculated based on entire state, not just papers
    assert metrics.data_loss_percentage > 0  # Some data was lost
    assert metrics.data_loss_percentage < 50  # But less than 50%
    assert metrics.partial_results_available is True
