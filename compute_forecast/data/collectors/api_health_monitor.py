"""
API Health Monitor - Monitors API health and performance
Real implementation with request tracking and health status calculation
"""

import threading
from collections import deque
from datetime import datetime
from typing import Dict
from ..models import APIHealthStatus, APIError, HealthMonitoringConfig
import logging


logger = logging.getLogger(__name__)


class APIHealthMonitor:
    """
    Monitor and track API health based on response patterns

    Tracks success rates, response times, and error patterns
    to determine API health status and guide rate limiting
    """

    def __init__(
        self, history_size: int = HealthMonitoringConfig.DEFAULT_HISTORY_SIZE
    ) -> None:
        self.history_size = history_size
        self.request_histories: Dict[str, deque] = {}
        self.health_statuses: Dict[str, APIHealthStatus] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

    def monitor_api_health(
        self, api_name: str, response, duration_ms: float
    ) -> APIHealthStatus:
        """Monitor and update API health based on response"""

        # Initialize tracking for new API
        if api_name not in self.request_histories:
            with self._global_lock:
                if api_name not in self.request_histories:
                    self.request_histories[api_name] = deque(maxlen=self.history_size)
                    self._locks[api_name] = threading.RLock()

        with self._locks[api_name]:
            # Determine if request was successful
            success = self._is_successful_response(response)

            # Record request
            request_record = {
                "timestamp": datetime.now(),
                "success": success,
                "response_time_ms": duration_ms,
                "status_code": getattr(response, "status_code", 0),
            }

            self.request_histories[api_name].append(request_record)

            # Update health status
            return self._calculate_health_status(api_name, request_record)

    def get_health_status(self, api_name: str) -> APIHealthStatus:
        """Get current health status for API"""
        # Ensure API is initialized with proper lock
        if api_name not in self._locks:
            with self._global_lock:
                if api_name not in self._locks:
                    self.request_histories[api_name] = deque(maxlen=self.history_size)
                    self._locks[api_name] = threading.RLock()

        with self._locks[api_name]:
            if api_name in self.health_statuses:
                return self.health_statuses[api_name]

            # Return default healthy status for unknown APIs
            return APIHealthStatus(
                api_name=api_name,
                status="healthy",
                success_rate=1.0,
                avg_response_time_ms=500.0,
                consecutive_errors=0,
                last_successful_request=datetime.now(),
            )

    def _is_successful_response(self, response) -> bool:
        """Determine if response indicates success"""
        if hasattr(response, "status_code"):
            return 200 <= response.status_code < 300
        elif hasattr(response, "ok"):
            return response.ok
        else:
            # Assume success if we can't determine
            return True

    def _calculate_health_status(
        self, api_name: str, latest_request: dict
    ) -> APIHealthStatus:
        """Calculate current health status based on request history"""

        history = self.request_histories[api_name]
        if not history:
            return self._create_default_status(api_name)

        # Calculate metrics from recent history
        recent_requests = list(history)[
            -HealthMonitoringConfig.RECENT_REQUESTS_WINDOW :
        ]
        total_requests = len(recent_requests)

        if total_requests == 0:
            return self._create_default_status(api_name)

        # Calculate success rate
        successful_requests = sum(1 for req in recent_requests if req["success"])
        success_rate = successful_requests / total_requests

        # Calculate average response time
        avg_response_time = (
            sum(req["response_time_ms"] for req in recent_requests) / total_requests
        )

        # Count consecutive errors from the end
        consecutive_errors = 0
        for req in reversed(recent_requests):
            if not req["success"]:
                consecutive_errors += 1
            else:
                break

        # Find last successful request
        last_successful_request = None
        for req in reversed(recent_requests):
            if req["success"]:
                last_successful_request = req["timestamp"]
                break

        # Determine status
        status = self._determine_status_level(
            success_rate, avg_response_time, consecutive_errors
        )

        # Create error if latest request failed
        last_error = None
        if not latest_request["success"]:
            last_error = APIError(
                error_type="api_request_failed",
                message=f"API request failed with status {latest_request.get('status_code', 'unknown')}",
                status_code=latest_request.get("status_code"),
                timestamp=latest_request["timestamp"],
            )

        # Create and store health status
        health_status = APIHealthStatus(
            api_name=api_name,
            status=status,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            consecutive_errors=consecutive_errors,
            last_error=last_error,
            last_successful_request=last_successful_request,
        )

        self.health_statuses[api_name] = health_status

        logger.debug(
            f"API {api_name} health: {status} (success_rate={success_rate:.2f}, "
            f"avg_response_time={avg_response_time:.0f}ms, consecutive_errors={consecutive_errors})"
        )

        return health_status

    def _determine_status_level(
        self, success_rate: float, avg_response_time: float, consecutive_errors: int
    ) -> str:
        """Determine health status level based on metrics"""

        # Critical conditions
        if consecutive_errors >= HealthMonitoringConfig.OFFLINE_CONSECUTIVE_ERRORS:
            return "offline"

        if (
            consecutive_errors >= HealthMonitoringConfig.CRITICAL_CONSECUTIVE_ERRORS
            or success_rate < HealthMonitoringConfig.CRITICAL_SUCCESS_RATE_THRESHOLD
        ):
            return "critical"

        # Degraded conditions
        if (
            consecutive_errors >= HealthMonitoringConfig.DEGRADED_CONSECUTIVE_ERRORS
            or success_rate < HealthMonitoringConfig.DEGRADED_SUCCESS_RATE_THRESHOLD
            or avg_response_time > HealthMonitoringConfig.SLOW_RESPONSE_THRESHOLD_MS
        ):
            return "degraded"

        # Healthy
        return "healthy"

    def _create_default_status(self, api_name: str) -> APIHealthStatus:
        """Create default healthy status for new APIs"""
        return APIHealthStatus(
            api_name=api_name,
            status="healthy",
            success_rate=1.0,
            avg_response_time_ms=500.0,
            consecutive_errors=0,
            last_successful_request=datetime.now(),
        )
