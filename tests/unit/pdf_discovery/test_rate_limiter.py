"""Tests for shared rate limiter utility."""

import time
from unittest.mock import patch

from compute_forecast.pipeline.pdf_acquisition.discovery.utils.rate_limiter import (
    RateLimiter,
)


class TestRateLimiter:
    """Tests for the RateLimiter utility class."""

    def test_init_requests_per_minute(self):
        """Test initialization with requests per minute."""
        limiter = RateLimiter.per_minute(120)
        assert limiter.min_interval == 0.5  # 60/120

    def test_init_requests_per_second(self):
        """Test initialization with requests per second."""
        limiter = RateLimiter.per_second(2.0)
        assert limiter.min_interval == 0.5  # 1/2

    def test_wait_respects_rate_limit(self):
        """Test that wait() enforces the rate limit."""
        limiter = RateLimiter.per_second(2.0)  # 0.5 second interval

        time.time()
        limiter.wait()  # First call should not wait
        first_call_time = time.time()

        limiter.wait()  # Second call should wait ~0.5 seconds
        second_call_time = time.time()

        # Allow some tolerance for timing
        elapsed = second_call_time - first_call_time
        assert elapsed >= 0.4  # Should wait at least 0.4 seconds
        assert elapsed <= 0.7  # But not more than 0.7 seconds

    def test_wait_no_delay_when_interval_passed(self):
        """Test that wait() doesn't delay when interval has passed."""
        limiter = RateLimiter.per_second(10.0)  # 0.1 second interval

        limiter.wait()  # First call
        time.sleep(0.2)  # Wait longer than interval

        start_time = time.time()
        limiter.wait()  # Should not wait
        end_time = time.time()

        # Should complete almost immediately
        assert end_time - start_time < 0.05

    @patch("compute_forecast.pipeline.pdf_acquisition.discovery.utils.rate_limiter.time.sleep")
    @patch("compute_forecast.pipeline.pdf_acquisition.discovery.utils.rate_limiter.time.time")
    def test_wait_calculation_precision(self, mock_time, mock_sleep):
        """Test precise wait time calculation."""
        # Set up mock times: current time when checking interval, then time after sleep
        mock_time.side_effect = [0.3, 0.3]  # current=0.3, after_sleep=0.3

        limiter = RateLimiter.per_second(2.0)  # 0.5 second interval
        limiter.last_request_time = 0.0

        limiter.wait()

        # Should sleep for 0.2 seconds (0.5 - 0.3)
        mock_sleep.assert_called_once_with(0.2)

    def test_concurrent_usage_thread_safety(self):
        """Test basic thread safety of rate limiter."""
        import threading

        limiter = RateLimiter.per_second(5.0)  # 0.2 second interval
        results = []

        def make_request(request_id):
            start = time.time()
            limiter.wait()
            end = time.time()
            results.append((request_id, start, end))

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)

        # Start all threads roughly at the same time
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Sort by start time
        results.sort(key=lambda x: x[1])

        # Verify rate limiting worked (requests spaced apart)
        assert len(results) == 3
        if len(results) >= 2:
            gap = results[1][2] - results[0][2]  # End of first to end of second
            assert gap >= 0.15  # Should be roughly 0.2 seconds apart
