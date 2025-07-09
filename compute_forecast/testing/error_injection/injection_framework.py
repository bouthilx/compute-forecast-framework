"""Error Injection Framework for systematic error testing."""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can be injected."""

    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    API_AUTH_FAILURE = "api_auth_failure"
    NETWORK_ERROR = "network_error"
    DATA_CORRUPTION = "data_corruption"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_FULL = "disk_full"
    INVALID_DATA_FORMAT = "invalid_data_format"
    COMPONENT_CRASH = "component_crash"


@dataclass
class ErrorScenario:
    """Configuration for an error injection scenario."""

    error_type: ErrorType
    component: str  # Component to inject error into
    probability: float = 1.0  # Probability of error occurring
    severity: str = "medium"  # low, medium, high, critical
    recovery_expected: bool = True
    max_recovery_time_seconds: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorInjectionFramework:
    """
    Framework for systematic error injection into components.

    Provides controlled error injection with configurable scenarios,
    tracking, and statistics for comprehensive error recovery testing.
    """

    def __init__(self):
        """Initialize the error injection framework."""
        self.scenarios: List[ErrorScenario] = []
        self.injection_points: Dict[str, Callable[[ErrorType], None]] = {}
        self._active_injections: Dict[str, Dict[str, Any]] = {}
        self._injection_history: List[Dict[str, Any]] = []

    def register_injection_point(
        self, component: str, injector: Callable[[ErrorType], None]
    ) -> None:
        """
        Register where errors can be injected.

        Args:
            component: Name of the component
            injector: Function that performs the error injection
        """
        logger.info(f"Registering injection point for component: {component}")
        self.injection_points[component] = injector

    def add_scenario(self, scenario: ErrorScenario) -> None:
        """
        Add error scenario to test.

        Args:
            scenario: Error scenario configuration
        """
        logger.info(
            f"Adding error scenario: {scenario.error_type.value} for {scenario.component}"
        )
        self.scenarios.append(scenario)

    def inject_error(self, scenario: ErrorScenario) -> None:
        """
        Inject specific error into system.

        Args:
            scenario: Error scenario to inject

        Raises:
            ValueError: If no injection point is registered for the component
        """
        # Check if injection point exists
        if scenario.component not in self.injection_points:
            raise ValueError(
                f"No injection point registered for component: {scenario.component}"
            )

        # Check probability
        if random.random() >= scenario.probability:
            logger.debug(
                f"Skipping injection due to probability ({scenario.probability})"
            )
            return

        # Perform injection
        logger.warning(
            f"Injecting {scenario.error_type.value} into {scenario.component}"
        )

        timestamp = datetime.now()

        # Record active injection
        self._active_injections[scenario.component] = {
            "error_type": scenario.error_type,
            "timestamp": timestamp,
            "severity": scenario.severity,
            "recovery_expected": scenario.recovery_expected,
        }

        # Record in history
        self._injection_history.append(
            {
                "component": scenario.component,
                "error_type": scenario.error_type,
                "timestamp": timestamp,
                "severity": scenario.severity,
                "recovery_expected": scenario.recovery_expected,
                "max_recovery_time_seconds": scenario.max_recovery_time_seconds,
            }
        )

        # Call the injector
        injector = self.injection_points[scenario.component]
        injector(scenario.error_type)

    def run_scenario_suite(self) -> Dict[str, Any]:
        """
        Run all registered error scenarios.

        Returns:
            Dictionary containing execution results and statistics
        """
        logger.info(
            f"Running error scenario suite with {len(self.scenarios)} scenarios"
        )

        results: Dict[str, Any] = {
            "total_scenarios": len(self.scenarios),
            "scenarios_executed": 0,
            "injection_success_rate": 0.0,
            "by_component": defaultdict(int),
            "by_error_type": defaultdict(int),
            "start_time": datetime.now(),
            "end_time": None,
            "errors": [],
        }

        initial_history_length = len(self._injection_history)

        for scenario in self.scenarios:
            try:
                self.inject_error(scenario)
                results["scenarios_executed"] += 1
                results["by_component"][scenario.component] += 1
                results["by_error_type"][scenario.error_type.value] += 1
            except Exception as e:
                logger.error(f"Failed to inject error for {scenario.component}: {e}")
                results["errors"].append(str(e))

        results["end_time"] = datetime.now()

        # Calculate injection success rate based on actual injections
        actual_injections = len(self._injection_history) - initial_history_length
        if results["scenarios_executed"] > 0:
            results["injection_success_rate"] = (
                actual_injections / results["scenarios_executed"]
            )

        return results

    def get_active_injections(self) -> Dict[str, Dict[str, Any]]:
        """
        Get currently active error injections.

        Returns:
            Dictionary of active injections by component
        """
        return self._active_injections.copy()

    def clear_injection(self, component: str) -> None:
        """
        Clear error injection for a specific component.

        Args:
            component: Component name to clear injection for
        """
        if component in self._active_injections:
            logger.info(f"Clearing injection for component: {component}")
            del self._active_injections[component]

    def clear_all_injections(self) -> None:
        """Clear all active error injections."""
        logger.info(f"Clearing all {len(self._active_injections)} active injections")
        self._active_injections.clear()

    def get_injection_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all error injections.

        Returns:
            List of injection records
        """
        return self._injection_history.copy()

    def get_injection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about error injections.

        Returns:
            Dictionary containing injection statistics
        """
        stats: Dict[str, Any] = {
            "total_injections": len(self._injection_history),
            "active_injections": len(self._active_injections),
            "by_component": defaultdict(int),
            "by_error_type": defaultdict(int),
            "by_severity": defaultdict(int),
        }

        for record in self._injection_history:
            stats["by_component"][record["component"]] += 1
            stats["by_error_type"][record["error_type"]] += 1
            stats["by_severity"][record["severity"]] += 1

        return dict(stats)
