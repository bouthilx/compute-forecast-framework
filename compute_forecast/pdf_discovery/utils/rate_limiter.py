"""Shared rate limiter utility for API requests."""

import time
import threading
from typing import Union


class RateLimiter:
    """Thread-safe rate limiter for API requests."""

    def __init__(self, min_interval: float):
        """Initialize rate limiter with minimum interval between requests.

        Args:
            min_interval: Minimum time (in seconds) between requests
        """
        self.min_interval = min_interval
        self.last_request_time = 0.0
        self._lock = threading.Lock()

    @classmethod
    def per_minute(cls, requests_per_minute: int) -> "RateLimiter":
        """Create rate limiter with requests per minute limit.

        Args:
            requests_per_minute: Maximum number of requests per minute

        Returns:
            RateLimiter instance
        """
        min_interval = 60.0 / requests_per_minute
        return cls(min_interval)

    @classmethod
    def per_second(cls, requests_per_second: Union[int, float]) -> "RateLimiter":
        """Create rate limiter with requests per second limit.

        Args:
            requests_per_second: Maximum number of requests per second

        Returns:
            RateLimiter instance
        """
        min_interval = 1.0 / requests_per_second
        return cls(min_interval)

    def wait(self):
        """Wait if necessary to respect rate limit."""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()
