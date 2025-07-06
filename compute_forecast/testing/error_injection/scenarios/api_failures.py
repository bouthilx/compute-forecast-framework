"""API failure scenarios for error injection testing."""

import logging
from typing import List, Dict, Any

from ..injection_framework import ErrorScenario, ErrorType

logger = logging.getLogger(__name__)


class APIFailureScenarios:
    """Pre-defined API failure scenarios for testing."""

    @staticmethod
    def get_timeout_cascade_scenario() -> List[ErrorScenario]:
        """
        Get scenario for cascading API timeouts.

        Returns:
            List of error scenarios simulating timeout cascade
        """
        return [
            ErrorScenario(
                error_type=ErrorType.API_TIMEOUT,
                component="semantic_scholar",
                probability=1.0,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=60.0,
                metadata={"initial_failure": True},
            ),
            ErrorScenario(
                error_type=ErrorType.API_TIMEOUT,
                component="openalex",
                probability=0.8,  # 80% chance of cascading
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=90.0,
                metadata={"cascade_from": "semantic_scholar"},
            ),
            ErrorScenario(
                error_type=ErrorType.API_TIMEOUT,
                component="crossref",
                probability=0.6,  # 60% chance of further cascade
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=120.0,
                metadata={"cascade_from": "openalex"},
            ),
        ]

    @staticmethod
    def get_rate_limit_scenario() -> List[ErrorScenario]:
        """
        Get scenario for API rate limiting.

        Returns:
            List of error scenarios simulating rate limits
        """
        return [
            ErrorScenario(
                error_type=ErrorType.API_RATE_LIMIT,
                component="openalex",
                probability=1.0,
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=300.0,  # 5 minutes
                metadata={"wait_time_seconds": 60},
            ),
            ErrorScenario(
                error_type=ErrorType.API_RATE_LIMIT,
                component="semantic_scholar",
                probability=0.5,
                severity="low",
                recovery_expected=True,
                max_recovery_time_seconds=180.0,
                metadata={"wait_time_seconds": 30},
            ),
        ]

    @staticmethod
    def get_auth_failure_scenario() -> List[ErrorScenario]:
        """
        Get scenario for authentication failures.

        Returns:
            List of error scenarios simulating auth failures
        """
        return [
            ErrorScenario(
                error_type=ErrorType.API_AUTH_FAILURE,
                component="crossref",
                probability=1.0,
                severity="critical",
                recovery_expected=False,  # Auth failures typically need manual intervention
                max_recovery_time_seconds=0.0,
                metadata={"error_code": 401, "requires_manual_fix": True},
            )
        ]

    @staticmethod
    def get_mixed_api_failures_scenario() -> List[ErrorScenario]:
        """
        Get scenario with mixed API failures.

        Returns:
            List of error scenarios with various API failures
        """
        scenarios = []

        # Add timeouts
        scenarios.extend(
            [
                ErrorScenario(
                    error_type=ErrorType.API_TIMEOUT,
                    component="semantic_scholar",
                    probability=0.3,
                    severity="medium",
                    recovery_expected=True,
                    max_recovery_time_seconds=45.0,
                ),
                ErrorScenario(
                    error_type=ErrorType.API_TIMEOUT,
                    component="crossref",
                    probability=0.2,
                    severity="low",
                    recovery_expected=True,
                    max_recovery_time_seconds=30.0,
                ),
            ]
        )

        # Add rate limits
        scenarios.append(
            ErrorScenario(
                error_type=ErrorType.API_RATE_LIMIT,
                component="openalex",
                probability=0.4,
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=120.0,
            )
        )

        # Add network errors
        scenarios.append(
            ErrorScenario(
                error_type=ErrorType.NETWORK_ERROR,
                component="semantic_scholar",
                probability=0.1,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=60.0,
            )
        )

        return scenarios

    @staticmethod
    def validate_api_recovery(recovery_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate API recovery meets requirements.

        Args:
            recovery_metrics: Metrics from recovery testing

        Returns:
            Validation results
        """
        validation = {"passed": True, "checks": [], "failures": []}

        # Check recovery time
        if recovery_metrics.get("avg_recovery_time", 0) > 300:  # 5 minutes
            validation["passed"] = False
            validation["failures"].append(
                f"Average recovery time {recovery_metrics['avg_recovery_time']:.1f}s exceeds 5 minute limit"
            )
        else:
            validation["checks"].append("Recovery time within 5 minute limit")

        # Check fallback behavior
        if recovery_metrics.get("fallback_success_rate", 0) < 0.9:  # 90% success
            validation["passed"] = False
            validation["failures"].append(
                f"Fallback success rate {recovery_metrics['fallback_success_rate']:.1%} below 90% threshold"
            )
        else:
            validation["checks"].append("API fallback working correctly")

        # Check no cascading failures
        if recovery_metrics.get("cascade_failures", 0) > 0:
            validation["passed"] = False
            validation["failures"].append(
                f"Detected {recovery_metrics['cascade_failures']} cascading failures"
            )
        else:
            validation["checks"].append("No cascading failures detected")

        return validation
