"""
Rate Limit Manager - Adaptive Rate Limiting with API Health Monitoring
Real implementation with thread-safe rolling windows and adaptive delays
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from ..models import (
    APIConfig,
    RateLimitStatus,
    APIHealthStatus,
    RollingWindow,
    RateLimitingConfig,
    HealthMonitoringConfig,
)
import logging


logger = logging.getLogger(__name__)


class RateLimitManager:
    """
    Thread-safe rate limit manager with adaptive delays based on API health

    REQUIREMENTS:
    - <10ms response time for can_make_request
    - Thread-safe for 20+ concurrent threads
    - 5-minute rolling windows
    - Adaptive delays based on API health
    - Never wait longer than 60 seconds
    """

    def __init__(self, api_configs: Dict[str, APIConfig]):
        self.api_configs = api_configs
        self.request_windows: Dict[str, RollingWindow] = {}
        self.health_multipliers: Dict[str, float] = {}
        self.consecutive_failures: Dict[
            str, int
        ] = {}  # Track consecutive failures for exponential backoff
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

        # Initialize windows and locks for each API
        for api_name, config in api_configs.items():
            self.request_windows[api_name] = RollingWindow(
                window_seconds=RateLimitingConfig.DEFAULT_WINDOW_SECONDS,
                max_requests=config.requests_per_window,
            )
            self.health_multipliers[api_name] = 1.0  # Start healthy
            self.consecutive_failures[api_name] = 0  # Start with no failures
            self._locks[api_name] = threading.RLock()

    def can_make_request(self, api_name: str, request_size: int = 1) -> bool:
        """
        Check if API request can be made without violating limits

        REQUIREMENTS:
        - Must track requests in 5-minute rolling windows
        - Must account for API health degradation
        - Must be thread-safe
        - Must have <10ms response time

        Raises:
            ValueError: If api_name is not configured
        """
        if api_name not in self.api_configs:
            error_msg = f"Cannot check rate limit for unknown API '{api_name}'. Available APIs: {list(self.api_configs.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        with self._locks[api_name]:
            window = self.request_windows[api_name]

            # Quick check: if we have capacity in the window
            current_count = window.get_current_count()
            available_capacity = window.max_requests - current_count

            # Account for health degradation (degraded APIs get lower effective capacity)
            health_multiplier = self.health_multipliers.get(api_name, 1.0)
            if health_multiplier > 1.0:
                # Degraded API - reduce effective capacity
                effective_capacity = int(available_capacity / health_multiplier)
                return request_size <= effective_capacity

            return request_size <= available_capacity

    def wait_if_needed(self, api_name: str, request_size: int = 1) -> float:
        """
        Wait if necessary to respect rate limits

        REQUIREMENTS:
        - Must implement exponential backoff for degraded APIs
        - Must not wait longer than 60 seconds
        - Must log wait reasons

        Raises:
            ValueError: If api_name is not configured
        """
        if api_name not in self.api_configs:
            error_msg = f"Cannot calculate wait time for unknown API '{api_name}'. Available APIs: {list(self.api_configs.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        with self._locks[api_name]:
            window = self.request_windows[api_name]
            config = self.api_configs[api_name]

            # Check for exponential backoff due to consecutive failures
            failures = self.consecutive_failures.get(api_name, 0)
            exponential_wait = 0.0
            if failures > 0:
                # Exponential backoff: 2^failures * base_delay
                exponential_wait = config.base_delay_seconds * (2**failures)
                exponential_wait = min(exponential_wait, config.max_delay_seconds)

            # Calculate base wait time from rolling window
            base_wait = window.time_until_next_slot()

            # Apply health-based multiplier
            health_multiplier = self.health_multipliers.get(api_name, 1.0)
            health_adjusted_wait = base_wait * health_multiplier

            # Use the maximum of window-based wait, health-adjusted wait, and exponential backoff
            adjusted_wait = max(health_adjusted_wait, exponential_wait)

            # Apply size multiplier for large requests
            if request_size > 1:
                size_multiplier = min(
                    request_size / RateLimitingConfig.BATCH_SIZE_DIVISOR,
                    RateLimitingConfig.BATCH_SIZE_MULTIPLIER_CAP,
                )
                adjusted_wait *= size_multiplier

            # Ensure we never exceed maximum wait time
            final_wait = min(adjusted_wait, RateLimitingConfig.MAX_WAIT_TIME_SECONDS)

            if final_wait > 0:
                logger.info(
                    f"Rate limiting {api_name}: waiting {final_wait:.2f}s (health_multiplier={health_multiplier:.2f})"
                )

            return final_wait

    def record_request(
        self, api_name: str, success: bool, response_time_ms: int, request_size: int = 1
    ) -> None:
        """
        Record API request for rate limiting and health tracking

        REQUIREMENTS:
        - Must update rolling windows
        - Must trigger health recalculation
        - Must be called for ALL requests

        Raises:
            ValueError: If api_name is not configured
        """
        if api_name not in self.api_configs:
            error_msg = f"Cannot record request for unknown API '{api_name}'. Available APIs: {list(self.api_configs.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        with self._locks[api_name]:
            window = self.request_windows[api_name]

            # Add requests to rolling window (one entry per request in batch)
            timestamp = datetime.now()
            for _ in range(request_size):
                window.add_request(timestamp)

            # Update consecutive failures counter
            if success:
                self.consecutive_failures[api_name] = 0  # Reset on success
            else:
                self.consecutive_failures[api_name] += 1  # Increment on failure

            # Update health multiplier based on request success
            self._update_health_multiplier(api_name, success, response_time_ms)

            logger.debug(
                f"Recorded {request_size} requests for {api_name}: success={success}, response_time={response_time_ms}ms"
            )

    def get_current_usage(self, api_name: str) -> Optional[RateLimitStatus]:
        """Get current rate limit usage for API"""
        if api_name not in self.api_configs:
            return None

        with self._locks[api_name]:
            config = self.api_configs[api_name]
            window = self.request_windows[api_name]

            current_count = window.get_current_count()
            next_slot_time = datetime.now() + timedelta(
                seconds=window.time_until_next_slot()
            )

            # Calculate current delay based on config and health
            health_multiplier = self.health_multipliers.get(api_name, 1.0)
            current_delay = config.base_delay_seconds * health_multiplier

            return RateLimitStatus(
                api_name=api_name,
                requests_in_window=current_count,
                window_capacity=config.requests_per_window,
                next_available_slot=next_slot_time,
                current_delay_seconds=min(current_delay, config.max_delay_seconds),
                health_multiplier=health_multiplier,
            )

    def update_api_health(self, api_name: str, health_status: APIHealthStatus) -> None:
        """Update rate limiting based on API health"""
        if api_name not in self.api_configs:
            return

        with self._locks[api_name]:
            # Convert health status to multiplier
            if health_status.status == "healthy":
                self.health_multipliers[api_name] = (
                    RateLimitingConfig.HEALTHY_MULTIPLIER
                )
            elif health_status.status == "degraded":
                self.health_multipliers[api_name] = (
                    RateLimitingConfig.DEGRADED_MULTIPLIER
                )
            elif health_status.status == "critical":
                self.health_multipliers[api_name] = (
                    RateLimitingConfig.CRITICAL_MULTIPLIER
                )
            elif health_status.status == "offline":
                self.health_multipliers[api_name] = (
                    RateLimitingConfig.OFFLINE_MULTIPLIER
                )

            logger.info(
                f"Updated health multiplier for {api_name}: {self.health_multipliers[api_name]:.1f}x (status: {health_status.status})"
            )

    def _update_health_multiplier(
        self, api_name: str, success: bool, response_time_ms: int
    ) -> None:
        """Update health multiplier based on request outcome"""
        current_multiplier = self.health_multipliers.get(api_name, 1.0)

        if success:
            # Successful request - gradually improve health
            if (
                response_time_ms < HealthMonitoringConfig.FAST_RESPONSE_THRESHOLD_MS
            ):  # Fast response
                new_multiplier = max(
                    RateLimitingConfig.HEALTHY_MULTIPLIER,
                    current_multiplier * RateLimitingConfig.FAST_RESPONSE_IMPROVEMENT,
                )
            elif (
                response_time_ms < HealthMonitoringConfig.NORMAL_RESPONSE_THRESHOLD_MS
            ):  # Normal response
                new_multiplier = max(
                    RateLimitingConfig.HEALTHY_MULTIPLIER,
                    current_multiplier * RateLimitingConfig.NORMAL_RESPONSE_IMPROVEMENT,
                )
            else:  # Slow response
                new_multiplier = min(
                    RateLimitingConfig.OFFLINE_MULTIPLIER,
                    current_multiplier * RateLimitingConfig.SLOW_RESPONSE_DEGRADATION,
                )
        else:
            # Failed request - degrade health
            new_multiplier = min(
                RateLimitingConfig.OFFLINE_MULTIPLIER,
                current_multiplier * RateLimitingConfig.FAILURE_DEGRADATION,
            )

        self.health_multipliers[api_name] = new_multiplier
