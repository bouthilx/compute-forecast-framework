"""Comprehensive tests for error handling components"""

import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import requests

from compute_forecast.data.sources.scrapers.error_handling import (
    ErrorType,
    ScrapingError,
    ScrapingMonitor,
    retry_on_error,
    RateLimiter,
)


class TestErrorType:
    """Test ErrorType enum"""

    def test_error_type_values(self):
        """Test all error type values are properly defined"""
        assert ErrorType.NETWORK_ERROR.value == "network_error"
        assert ErrorType.PARSING_ERROR.value == "parsing_error"
        assert ErrorType.RATE_LIMIT_ERROR.value == "rate_limit_error"
        assert ErrorType.AUTHENTICATION_ERROR.value == "auth_error"
        assert ErrorType.DATA_VALIDATION_ERROR.value == "validation_error"

    def test_error_type_count(self):
        """Test expected number of error types"""
        assert len(ErrorType) == 5


class TestScrapingError:
    """Test ScrapingError dataclass"""

    def test_minimal_error_creation(self):
        """Test creating error with minimal required fields"""
        error = ScrapingError(
            error_type=ErrorType.NETWORK_ERROR, message="Connection failed"
        )

        assert error.error_type == ErrorType.NETWORK_ERROR
        assert error.message == "Connection failed"
        assert error.url is None
        assert error.venue is None
        assert error.year is None
        assert error.retry_count == 0
        assert isinstance(error.timestamp, datetime)
        assert error.traceback is None

    def test_full_error_creation(self):
        """Test creating error with all fields"""
        timestamp = datetime.now()
        traceback_str = "Traceback details"

        error = ScrapingError(
            error_type=ErrorType.PARSING_ERROR,
            message="Failed to parse HTML",
            url="https://example.com",
            venue="CVPR",
            year=2023,
            timestamp=timestamp,
            traceback=traceback_str,
            retry_count=3,
        )

        assert error.error_type == ErrorType.PARSING_ERROR
        assert error.message == "Failed to parse HTML"
        assert error.url == "https://example.com"
        assert error.venue == "CVPR"
        assert error.year == 2023
        assert error.timestamp == timestamp
        assert error.traceback == traceback_str
        assert error.retry_count == 3

    def test_error_string_representation(self):
        """Test string representation of error"""
        error = ScrapingError(
            error_type=ErrorType.RATE_LIMIT_ERROR,
            message="Too many requests",
            url="https://api.example.com",
            venue="NeurIPS",
            year=2023,
            retry_count=2,
        )

        error_str = str(error)
        assert "rate_limit_error: Too many requests" in error_str
        assert "URL: https://api.example.com" in error_str
        assert "Venue: NeurIPS" in error_str
        assert "Year: 2023" in error_str
        assert "Retries: 2" in error_str

    def test_error_string_minimal(self):
        """Test string representation with minimal fields"""
        error = ScrapingError(
            error_type=ErrorType.NETWORK_ERROR, message="Connection timeout"
        )

        error_str = str(error)
        assert error_str == "network_error: Connection timeout"


class TestScrapingMonitor:
    """Test ScrapingMonitor class"""

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = ScrapingMonitor()

        assert monitor.errors == []
        assert monitor.stats["papers_collected"] == 0
        assert monitor.stats["venues_processed"] == 0
        assert monitor.stats["errors_total"] == 0
        assert monitor.stats["start_time"] is None
        assert monitor.stats["end_time"] is None

    def test_start_end_monitoring(self):
        """Test starting and ending monitoring sessions"""
        monitor = ScrapingMonitor()

        # Start monitoring
        start_time = datetime.now()
        monitor.start_monitoring()

        assert monitor.stats["start_time"] is not None
        assert monitor.stats["start_time"] >= start_time

        # End monitoring
        time.sleep(0.1)  # Small delay to ensure time difference
        monitor.end_monitoring()

        assert monitor.stats["end_time"] is not None
        assert monitor.stats["end_time"] >= monitor.stats["start_time"]
        # Allow some tolerance for timing differences
        time_diff = monitor.stats["end_time"] - monitor.stats["start_time"]
        assert time_diff.total_seconds() >= 0.1

    def test_record_error(self):
        """Test recording errors"""
        monitor = ScrapingMonitor()

        error1 = ScrapingError(ErrorType.NETWORK_ERROR, "Network failed")
        error2 = ScrapingError(ErrorType.PARSING_ERROR, "Parse failed")

        monitor.record_error(error1)
        monitor.record_error(error2)

        assert len(monitor.errors) == 2
        assert monitor.stats["errors_total"] == 2
        assert monitor.errors[0] == error1
        assert monitor.errors[1] == error2

    def test_record_success(self):
        """Test recording successful operations"""
        monitor = ScrapingMonitor()

        monitor.record_success(25, "ICML", 2023)
        monitor.record_success(30, "NeurIPS", 2023)

        assert monitor.stats["papers_collected"] == 55
        assert monitor.stats["venues_processed"] == 2

    def test_get_error_summary(self):
        """Test error summary generation"""
        monitor = ScrapingMonitor()

        # Add various errors
        monitor.record_error(ScrapingError(ErrorType.NETWORK_ERROR, "Network 1"))
        monitor.record_error(ScrapingError(ErrorType.NETWORK_ERROR, "Network 2"))
        monitor.record_error(ScrapingError(ErrorType.PARSING_ERROR, "Parse 1"))
        monitor.record_error(ScrapingError(ErrorType.RATE_LIMIT_ERROR, "Rate limit"))

        summary = monitor.get_error_summary()

        assert summary["network_error"] == 2
        assert summary["parsing_error"] == 1
        assert summary["rate_limit_error"] == 1
        assert len(summary) == 3

    def test_get_performance_report(self):
        """Test performance report generation"""
        monitor = ScrapingMonitor()

        # Start monitoring and add some data
        monitor.start_monitoring()
        monitor.record_success(100, "CVPR", 2023)
        monitor.record_success(50, "ICCV", 2023)
        monitor.record_error(ScrapingError(ErrorType.NETWORK_ERROR, "Network failed"))

        time.sleep(0.1)  # Small delay for duration calculation
        monitor.end_monitoring()

        report = monitor.get_performance_report()

        assert report["papers_collected"] == 150
        assert report["venues_processed"] == 2
        assert report["total_errors"] == 1
        assert report["error_rate"] == 0.5  # 1 error / 2 venues
        assert report["duration_seconds"] > 0
        assert report["papers_per_second"] > 0
        assert "error_summary" in report

    def test_get_performance_report_no_end_time(self):
        """Test performance report with ongoing monitoring"""
        monitor = ScrapingMonitor()

        monitor.start_monitoring()
        monitor.record_success(10, "AAAI", 2023)

        # Don't end monitoring
        report = monitor.get_performance_report()

        assert report["papers_collected"] == 10
        assert report["venues_processed"] == 1
        assert report["duration_seconds"] > 0  # Should calculate from start to now

    def test_get_recent_errors(self):
        """Test getting recent errors"""
        monitor = ScrapingMonitor()

        # Add errors with different timestamps
        old_error = ScrapingError(ErrorType.NETWORK_ERROR, "Old error")
        old_error.timestamp = datetime.now() - timedelta(hours=1)

        recent_error = ScrapingError(ErrorType.PARSING_ERROR, "Recent error")
        recent_error.timestamp = datetime.now()

        monitor.record_error(old_error)
        monitor.record_error(recent_error)

        recent_errors = monitor.get_recent_errors(limit=1)

        assert len(recent_errors) == 1
        assert recent_errors[0] == recent_error

    @patch("compute_forecast.data.sources.scrapers.error_handling.logging.getLogger")
    def test_logging_integration(self, mock_get_logger):
        """Test that monitor integrates with logging"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        monitor = ScrapingMonitor()

        # Test start monitoring logging
        monitor.start_monitoring()
        mock_logger.info.assert_called_with("Started scraping monitoring session")

        # Test error logging
        error = ScrapingError(ErrorType.NETWORK_ERROR, "Test error")
        monitor.record_error(error)
        mock_logger.warning.assert_called()

        # Test success logging
        monitor.record_success(10, "CVPR", 2023)
        mock_logger.info.assert_called_with(
            "Successfully scraped 10 papers from CVPR 2023"
        )


class TestRetryOnError:
    """Test retry_on_error decorator"""

    def test_successful_function(self):
        """Test decorator with function that succeeds"""
        call_count = 0

        @retry_on_error(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_network_error_retry(self):
        """Test retrying on network errors"""
        call_count = 0

        @retry_on_error(max_retries=2, delay=0.01)
        def failing_network_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Network error")
            return "success"

        result = failing_network_function()

        assert result == "success"
        assert call_count == 3

    def test_network_error_max_retries_exceeded(self):
        """Test failing after max retries on network errors"""
        call_count = 0

        @retry_on_error(max_retries=2, delay=0.01)
        def always_failing_network_function():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Network error")

        with pytest.raises(ScrapingError) as exc_info:
            always_failing_network_function()

        assert exc_info.value.error_type == ErrorType.NETWORK_ERROR
        assert "Network error after 2 retries" in exc_info.value.message
        assert exc_info.value.retry_count == 2
        assert call_count == 3  # Original + 2 retries

    def test_parsing_error_no_retry(self):
        """Test that parsing errors don't retry"""
        call_count = 0

        @retry_on_error(max_retries=3)
        def parsing_error_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Parsing error")

        with pytest.raises(ScrapingError) as exc_info:
            parsing_error_function()

        assert exc_info.value.error_type == ErrorType.PARSING_ERROR
        assert "Unexpected error: Parsing error" in exc_info.value.message
        assert call_count == 1  # No retries for parsing errors

    def test_exponential_backoff(self):
        """Test exponential backoff timing"""
        call_times = []

        @retry_on_error(max_retries=3, delay=0.1, backoff=2.0)
        def timing_function():
            call_times.append(time.time())
            raise requests.exceptions.ConnectionError("Network error")

        with pytest.raises(ScrapingError):
            timing_function()

        assert len(call_times) == 4  # Original + 3 retries

        # Check that delays are increasing (allowing for some timing variance)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        delay3 = call_times[3] - call_times[2]

        assert delay1 >= 0.1
        assert delay2 >= 0.2
        assert delay3 >= 0.4


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(requests_per_second=2.0)

        assert limiter.min_interval == 0.5
        assert limiter.last_request_time == 0.0
        assert limiter.consecutive_errors == 0
        assert limiter.max_backoff_multiplier == 32

    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        limiter = RateLimiter(requests_per_second=10.0)  # 0.1 second interval

        start_time = time.time()
        limiter.wait()
        first_wait_time = time.time()

        limiter.wait()
        second_wait_time = time.time()

        # Second wait should be at least min_interval after first
        time_diff = second_wait_time - first_wait_time
        assert time_diff >= 0.1

    def test_error_backoff(self):
        """Test exponential backoff on errors"""
        limiter = RateLimiter(requests_per_second=10.0)  # 0.1 second base interval

        # No errors - should use base interval
        assert limiter.get_current_delay() == 0.1

        # One error - should double
        limiter.record_error()
        assert limiter.get_current_delay() == 0.2

        # Two errors - should quadruple
        limiter.record_error()
        assert limiter.get_current_delay() == 0.4

        # Success should reset
        limiter.record_success()
        assert limiter.get_current_delay() == 0.1

    def test_max_backoff_cap(self):
        """Test that backoff is capped at max_backoff_multiplier"""
        limiter = RateLimiter(requests_per_second=1.0)  # 1 second base interval

        # Add many errors to exceed max backoff
        for _ in range(10):
            limiter.record_error()

        # Should be capped at max_backoff_multiplier
        expected_delay = 1.0 * limiter.max_backoff_multiplier
        assert limiter.get_current_delay() == expected_delay

    def test_reset_functionality(self):
        """Test reset functionality"""
        limiter = RateLimiter(requests_per_second=1.0)

        # Add errors and make request
        limiter.record_error()
        limiter.record_error()
        limiter.wait()

        # Reset should clear everything
        limiter.reset()

        assert limiter.consecutive_errors == 0
        assert limiter.last_request_time == 0.0
        assert limiter.get_current_delay() == 1.0

    def test_no_wait_if_enough_time_passed(self):
        """Test that no additional wait occurs if enough time has passed"""
        limiter = RateLimiter(requests_per_second=1.0)  # 1 second interval

        # Simulate a request from 2 seconds ago
        limiter.last_request_time = time.time() - 2.0

        # Should not wait since 2 seconds > 1 second required interval
        start_time = time.time()
        limiter.wait()
        end_time = time.time()

        # Should be very quick since no sleep was needed
        assert end_time - start_time < 0.1


class TestIntegration:
    """Integration tests for error handling components"""

    def test_monitor_with_retry_decorator(self):
        """Test integration of monitor with retry decorator"""
        monitor = ScrapingMonitor()

        @retry_on_error(max_retries=2, delay=0.01)
        def monitored_function():
            monitor.record_success(10, "CVPR", 2023)
            return "success"

        result = monitored_function()

        assert result == "success"
        assert monitor.stats["papers_collected"] == 10
        assert monitor.stats["venues_processed"] == 1

    def test_monitor_with_rate_limiter(self):
        """Test integration of monitor with rate limiter"""
        monitor = ScrapingMonitor()
        limiter = RateLimiter(requests_per_second=100.0)  # Fast for testing

        # Simulate successful scraping with rate limiting
        limiter.wait()
        monitor.record_success(5, "ICML", 2023)
        limiter.record_success()

        limiter.wait()
        monitor.record_success(8, "NeurIPS", 2023)
        limiter.record_success()

        assert monitor.stats["papers_collected"] == 13
        assert monitor.stats["venues_processed"] == 2
        assert limiter.consecutive_errors == 0

    def test_full_error_handling_workflow(self):
        """Test complete error handling workflow"""
        monitor = ScrapingMonitor()
        limiter = RateLimiter(requests_per_second=100.0)  # Fast for testing

        monitor.start_monitoring()

        # Simulate mixed success/failure scenario
        @retry_on_error(max_retries=1, delay=0.01)
        def mixed_function(should_fail=False):
            limiter.wait()
            if should_fail:
                limiter.record_error()
                raise requests.exceptions.ConnectionError("Network error")
            else:
                limiter.record_success()
                monitor.record_success(10, "AAAI", 2023)
                return "success"

        # Successful calls
        result1 = mixed_function(should_fail=False)
        result2 = mixed_function(should_fail=False)

        # Failed call
        with pytest.raises(ScrapingError):
            mixed_function(should_fail=True)

        monitor.end_monitoring()

        # Verify monitor state
        assert monitor.stats["papers_collected"] == 20
        assert monitor.stats["venues_processed"] == 2

        # Verify rate limiter adapted to errors
        assert (
            limiter.consecutive_errors == 2
        )  # From the failed call (original + 1 retry)

        # Verify performance report
        report = monitor.get_performance_report()
        assert report["papers_collected"] == 20
        assert report["venues_processed"] == 2
        assert report["duration_seconds"] > 0
