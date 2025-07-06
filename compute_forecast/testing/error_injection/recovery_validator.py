"""Recovery Validator for error injection testing."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .injection_framework import ErrorType, ErrorScenario

# Avoiding circular imports - these would be injected in production
InterruptionRecoveryEngine = None
StatePersistenceManager = None

logger = logging.getLogger(__name__)


@dataclass
class RecoveryMetrics:
    """Metrics for recovery validation."""

    error_type: ErrorType
    recovery_attempted: bool
    recovery_successful: bool
    recovery_time_seconds: float
    data_loss_percentage: float
    partial_results_available: bool
    component: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class RecoveryValidator:
    """
    Validates recovery effectiveness after error injection.

    Measures recovery time, data integrity, and graceful degradation
    to ensure the system meets recovery requirements.
    """

    def __init__(self, recovery_engine=None, state_manager=None):
        """Initialize recovery validator with existing recovery systems."""
        # Use provided or mock recovery systems
        self.recovery_engine = recovery_engine
        self.state_manager = state_manager

        # Validation tracking
        self.validation_results: List[Dict[str, Any]] = []
        self.recovery_metrics: List[RecoveryMetrics] = []

    def validate_recovery(
        self,
        error_scenario: ErrorScenario,
        pre_error_state: Dict[str, Any],
        post_recovery_state: Dict[str, Any],
    ) -> RecoveryMetrics:
        """
        Validate recovery effectiveness.

        Args:
            error_scenario: The error scenario that was injected
            pre_error_state: System state before error
            post_recovery_state: System state after recovery attempt

        Returns:
            RecoveryMetrics with validation results
        """
        logger.info(f"Validating recovery for {error_scenario.error_type.value}")

        # Calculate recovery time if timestamps available
        recovery_time = 0.0
        if "timestamp" in pre_error_state and "timestamp" in post_recovery_state:
            pre_time = pre_error_state["timestamp"]
            post_time = post_recovery_state["timestamp"]
            if isinstance(pre_time, datetime) and isinstance(post_time, datetime):
                recovery_time = (post_time - pre_time).total_seconds()

        # Measure data integrity
        data_integrity = self.measure_data_integrity(
            pre_error_state, post_recovery_state
        )
        data_loss_percentage = 100.0 - data_integrity

        # Determine if recovery was successful
        recovery_successful = self._is_recovery_successful(
            pre_error_state, post_recovery_state, error_scenario
        )

        # Check for partial results
        partial_results = self._check_partial_results(post_recovery_state)

        # Create metrics
        metrics = RecoveryMetrics(
            error_type=error_scenario.error_type,
            recovery_attempted=True,
            recovery_successful=recovery_successful,
            recovery_time_seconds=recovery_time,
            data_loss_percentage=data_loss_percentage,
            partial_results_available=partial_results,
            component=error_scenario.component,
        )

        # Store metrics
        self.recovery_metrics.append(metrics)

        # Log validation result
        self._log_validation_result(metrics, error_scenario)

        return metrics

    def measure_data_integrity(self, expected: Any, actual: Any) -> float:
        """
        Measure how much data was preserved.

        Args:
            expected: Expected data/state
            actual: Actual data/state after recovery

        Returns:
            Percentage of data preserved (0-100)
        """
        if expected == actual:
            return 100.0

        # Handle different data types
        if isinstance(expected, dict) and isinstance(actual, dict):
            return self._measure_dict_integrity(expected, actual)
        elif isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
            return self._measure_list_integrity(expected, actual)
        elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return self._measure_numeric_integrity(expected, actual)
        else:
            # Simple equality check for other types
            return 100.0 if expected == actual else 0.0

    def verify_graceful_degradation(
        self, component: str, error_type: ErrorType
    ) -> bool:
        """
        Verify system degrades gracefully.

        Args:
            component: Component that experienced error
            error_type: Type of error injected

        Returns:
            True if degradation was graceful
        """
        # Check recovery status
        recovery_status = self.recovery_engine.get_recovery_status("current_session")

        # Check component status
        component_status = self.state_manager.get_component_status(component)

        # Graceful degradation criteria
        graceful = True

        # Check if recovery attempts are within limits
        if recovery_status.get("recovery_attempts", 0) > recovery_status.get(
            "max_attempts", 3
        ):
            graceful = False
            logger.warning(f"Recovery attempts exceeded for {component}")

        # Check if component maintains partial functionality
        if component_status:
            if component_status.get("status") == "failed" and not component_status.get(
                "partial_functionality", False
            ):
                graceful = False
                logger.warning(
                    f"Component {component} completely failed without partial functionality"
                )

        return graceful

    def validate_recovery_time(
        self, start_time: datetime, end_time: datetime, max_recovery_seconds: float
    ) -> Dict[str, Any]:
        """
        Validate recovery completed within time limit.

        Args:
            start_time: Recovery start time
            end_time: Recovery end time
            max_recovery_seconds: Maximum allowed recovery time

        Returns:
            Validation result with timing details
        """
        recovery_duration = (end_time - start_time).total_seconds()
        within_limit = recovery_duration <= max_recovery_seconds

        result = {
            "within_limit": within_limit,
            "recovery_time_seconds": recovery_duration,
            "limit_seconds": max_recovery_seconds,
            "exceeded_by_seconds": max(0, recovery_duration - max_recovery_seconds),
        }

        if not within_limit:
            logger.warning(
                f"Recovery exceeded time limit by {result['exceeded_by_seconds']:.1f}s"
            )

        return result

    def generate_validation_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.

        Returns:
            Report with statistics and recommendations
        """
        if not self.recovery_metrics:
            return {
                "total_validations": 0,
                "successful_recoveries": 0,
                "failed_recoveries": 0,
                "success_rate": 0.0,
                "average_recovery_time": 0.0,
                "average_data_loss": 0.0,
                "by_error_type": {},
                "recommendations": ["No validation data available"],
            }

        # Calculate statistics
        total = len(self.recovery_metrics)
        successful = sum(1 for m in self.recovery_metrics if m.recovery_successful)
        failed = total - successful

        # Average metrics
        avg_recovery_time = (
            sum(m.recovery_time_seconds for m in self.recovery_metrics) / total
        )
        avg_data_loss = (
            sum(m.data_loss_percentage for m in self.recovery_metrics) / total
        )

        # Group by error type
        by_error_type = defaultdict(
            lambda: {"total": 0, "successful": 0, "avg_time": 0.0}
        )
        for metric in self.recovery_metrics:
            error_type_key = metric.error_type.value
            by_error_type[error_type_key]["total"] += 1
            if metric.recovery_successful:
                by_error_type[error_type_key]["successful"] += 1
            by_error_type[error_type_key]["avg_time"] += metric.recovery_time_seconds

        # Calculate averages for error types
        for error_type, stats in by_error_type.items():
            stats["avg_time"] /= stats["total"]
            stats["success_rate"] = stats["successful"] / stats["total"]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_recovery_time, avg_data_loss, by_error_type
        )

        return {
            "total_validations": total,
            "successful_recoveries": successful,
            "failed_recoveries": failed,
            "success_rate": successful / total,
            "average_recovery_time": avg_recovery_time,
            "average_data_loss": avg_data_loss,
            "by_error_type": dict(by_error_type),
            "recommendations": recommendations,
        }

    def _is_recovery_successful(
        self,
        pre_state: Dict[str, Any],
        post_state: Dict[str, Any],
        error_scenario: ErrorScenario,
    ) -> bool:
        """Determine if recovery was successful."""
        # Check if critical data was preserved
        if "status" in post_state and post_state["status"] == "failed":
            return False

        # Check if error was cleared
        if "error" in post_state and post_state["error"] is not None:
            return False

        # Check data preservation threshold
        data_integrity = self.measure_data_integrity(pre_state, post_state)
        if data_integrity < 50.0:  # Less than 50% data preserved
            return False

        # For non-recoverable errors, any recovery is a success
        if not error_scenario.recovery_expected:
            return (
                "papers_collected" in post_state and post_state["papers_collected"] > 0
            )

        return True

    def _check_partial_results(self, state: Dict[str, Any]) -> bool:
        """Check if partial results are available."""
        # Check for any data that indicates partial results
        partial_indicators = [
            "papers_collected",
            "venues_completed",
            "data_size_bytes",
            "partial_results",
        ]

        for indicator in partial_indicators:
            if indicator in state and state[indicator]:
                if isinstance(state[indicator], (int, float)):
                    return state[indicator] > 0
                elif isinstance(state[indicator], (list, dict)):
                    return len(state[indicator]) > 0
                else:
                    return bool(state[indicator])

        return False

    def _measure_dict_integrity(self, expected: dict, actual: dict) -> float:
        """Measure integrity between dictionaries."""
        if not expected:
            return 100.0 if not actual else 0.0

        total_keys = len(expected)
        matching_keys = sum(1 for k in expected if k in actual)

        # Check value integrity for matching keys
        value_integrity = 0.0
        for key in expected:
            if key in actual:
                if expected[key] == actual[key]:
                    value_integrity += 1.0
                else:
                    # Recursive integrity check for nested structures
                    nested_integrity = self.measure_data_integrity(
                        expected[key], actual[key]
                    )
                    value_integrity += nested_integrity / 100.0

        # Combine key and value integrity
        key_integrity = (matching_keys / total_keys) * 100 if total_keys > 0 else 100
        value_integrity = (
            (value_integrity / total_keys) * 100 if total_keys > 0 else 100
        )

        return (key_integrity + value_integrity) / 2

    def _measure_list_integrity(self, expected: list, actual: list) -> float:
        """Measure integrity between lists."""
        if not expected:
            return 100.0 if not actual else 0.0

        expected_len = len(expected)
        actual_len = len(actual)

        # Simple percentage based on length
        if actual_len >= expected_len:
            return 100.0
        else:
            return (actual_len / expected_len) * 100

    def _measure_numeric_integrity(self, expected: float, actual: float) -> float:
        """Measure integrity between numeric values."""
        if expected == 0:
            return 100.0 if actual == 0 else 0.0

        # Calculate percentage of expected value
        percentage = (actual / expected) * 100
        return min(100.0, percentage)

    def _log_validation_result(
        self, metrics: RecoveryMetrics, scenario: ErrorScenario
    ) -> None:
        """Log validation result for monitoring."""
        status = "SUCCESS" if metrics.recovery_successful else "FAILED"
        logger.info(
            f"Recovery validation {status} for {scenario.error_type.value} in {scenario.component}: "
            f"Time={metrics.recovery_time_seconds:.1f}s, DataLoss={metrics.data_loss_percentage:.1f}%"
        )

    def _generate_recommendations(
        self,
        avg_recovery_time: float,
        avg_data_loss: float,
        by_error_type: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        # Recovery time recommendations
        if avg_recovery_time > 300:  # 5 minutes
            recommendations.append(
                f"Improve recovery time - current average {avg_recovery_time:.1f}s exceeds 5-minute requirement"
            )

        # Data loss recommendations
        if avg_data_loss > 5.0:
            recommendations.append(
                f"Enhance data integrity mechanisms - average data loss {avg_data_loss:.1f}% exceeds 5% threshold"
            )

        # Error type specific recommendations
        for error_type, stats in by_error_type.items():
            if stats["success_rate"] < 0.8:
                recommendations.append(
                    f"Improve {error_type} recovery - success rate only {stats['success_rate']:.1%}"
                )
            if stats["avg_time"] > 360:
                recommendations.append(
                    f"Optimize {error_type} recovery time - currently {stats['avg_time']:.1f}s"
                )

        # General recommendations
        if not recommendations:
            recommendations.append("All recovery metrics within acceptable limits")

        return recommendations
