"""Error handler for data collection components."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from compute_forecast.testing.error_injection.injection_framework import ErrorType

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for an API."""

    name: str
    client: Any
    priority: int = 0
    enabled: bool = True


class CollectorErrorHandler:
    """
    Test error handling in data collection components.

    Simulates API-related errors like timeouts, rate limits,
    and authentication failures. Verifies fallback behavior.
    """

    def __init__(self):
        """Initialize collector error handler."""
        self._apis: Dict[str, APIConfig] = {}
        self._active_errors: Dict[str, ErrorType] = {}
        self._fallback_order: List[str] = []
        self._current_api_index = 0

    def register_api(self, api_name: str, api_client: Any, priority: int = 0) -> None:
        """
        Register an API for error simulation.

        Args:
            api_name: Name of the API
            api_client: API client instance
            priority: Priority for fallback order (higher = preferred)
        """
        self._apis[api_name] = APIConfig(
            name=api_name, client=api_client, priority=priority
        )
        logger.info(f"Registered API: {api_name} with priority {priority}")

    def simulate_api_timeout(self, api_name: str) -> None:
        """
        Simulate API timeout scenario.

        Args:
            api_name: Name of the API to timeout
        """
        if api_name not in self._apis:
            raise ValueError(f"API {api_name} not registered")

        logger.warning(f"Simulating timeout for API: {api_name}")
        self._active_errors[api_name] = ErrorType.API_TIMEOUT

        # Disable the API temporarily
        self._apis[api_name].enabled = False

    def simulate_rate_limit(self, api_name: str) -> None:
        """
        Simulate hitting rate limits.

        Args:
            api_name: Name of the API to rate limit
        """
        if api_name not in self._apis:
            raise ValueError(f"API {api_name} not registered")

        logger.warning(f"Simulating rate limit for API: {api_name}")
        self._active_errors[api_name] = ErrorType.API_RATE_LIMIT

        # Disable the API temporarily
        self._apis[api_name].enabled = False

    def simulate_auth_failure(self, api_name: str) -> None:
        """
        Simulate authentication failure.

        Args:
            api_name: Name of the API with auth failure
        """
        if api_name not in self._apis:
            raise ValueError(f"API {api_name} not registered")

        logger.error(f"Simulating auth failure for API: {api_name}")
        self._active_errors[api_name] = ErrorType.API_AUTH_FAILURE

        # Disable the API completely
        self._apis[api_name].enabled = False

    def verify_fallback_behavior(self) -> bool:
        """
        Verify collector falls back to other sources.

        Returns:
            True if fallback is working correctly
        """
        # Check if we have alternative APIs available
        available_apis = [
            api
            for api in self._apis.values()
            if api.enabled and api.name not in self._active_errors
        ]

        if not available_apis:
            logger.error("No available APIs for fallback")
            return False

        # Sort by priority
        available_apis.sort(key=lambda x: x.priority, reverse=True)

        # Update current API to the highest priority available
        if self._fallback_order:
            for api_name in self._fallback_order:
                if api_name in [api.name for api in available_apis]:
                    self._current_api_index = self._fallback_order.index(api_name)
                    logger.info(f"Fell back to API: {api_name}")
                    return True

        # Use first available if no fallback order set
        if available_apis:
            logger.info(f"Fell back to API: {available_apis[0].name}")
            return True

        return False

    def set_fallback_order(self, api_names: List[str]) -> None:
        """
        Set the fallback order for APIs.

        Args:
            api_names: List of API names in fallback order
        """
        self._fallback_order = api_names
        self._current_api_index = 0
        logger.info(f"Set fallback order: {api_names}")

    def get_active_api(self) -> Optional[str]:
        """
        Get the currently active API.

        Returns:
            Name of the active API or None
        """
        # Try fallback order first
        if self._fallback_order:
            for i in range(self._current_api_index, len(self._fallback_order)):
                api_name = self._fallback_order[i]
                if (
                    api_name in self._apis
                    and self._apis[api_name].enabled
                    and api_name not in self._active_errors
                ):
                    return api_name

        # Otherwise find any available API
        for api in self._apis.values():
            if api.enabled and api.name not in self._active_errors:
                return api.name

        return None

    def clear_error(self, api_name: str) -> None:
        """
        Clear error for an API.

        Args:
            api_name: Name of the API to clear error for
        """
        if api_name in self._active_errors:
            del self._active_errors[api_name]

        if api_name in self._apis:
            self._apis[api_name].enabled = True

        logger.info(f"Cleared error for API: {api_name}")

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of current errors.

        Returns:
            Dictionary with error information
        """
        return {
            "active_errors": {
                api: error.value for api, error in self._active_errors.items()
            },
            "disabled_apis": [
                api.name for api in self._apis.values() if not api.enabled
            ],
            "available_apis": [
                api.name
                for api in self._apis.values()
                if api.enabled and api.name not in self._active_errors
            ],
            "current_api": self.get_active_api(),
        }
