"""Robust error handling, monitoring, and retry logic for all scrapers"""

import time
import logging
from typing import Optional, Callable, Any, Dict, List
from functools import wraps
from enum import Enum
import traceback
from dataclasses import dataclass, field
from datetime import datetime
import requests


class ErrorType(Enum):
    """Classification of scraping errors"""

    NETWORK_ERROR = "network_error"
    PARSING_ERROR = "parsing_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "auth_error"
    DATA_VALIDATION_ERROR = "validation_error"


@dataclass
class ScrapingError(Exception):
    """Detailed error information for scraping operations"""

    error_type: ErrorType
    message: str
    url: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: Optional[str] = None
    retry_count: int = 0

    def __str__(self) -> str:
        """String representation of the error"""
        parts = [f"{self.error_type.value}: {self.message}"]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.venue:
            parts.append(f"Venue: {self.venue}")
        if self.year:
            parts.append(f"Year: {self.year}")
        if self.retry_count > 0:
            parts.append(f"Retries: {self.retry_count}")
        return " | ".join(parts)


class ScrapingMonitor:
    """Monitor scraping operations and track errors across all scrapers"""

    def __init__(self):
        self.errors: List[ScrapingError] = []
        self.stats = {
            "papers_collected": 0,
            "venues_processed": 0,
            "errors_total": 0,
            "start_time": None,
            "end_time": None,
        }
        self.logger = logging.getLogger("scraper.monitor")

    def start_monitoring(self):
        """Start monitoring session"""
        self.stats["start_time"] = datetime.now()
        self.logger.info("Started scraping monitoring session")

    def end_monitoring(self):
        """End monitoring session"""
        self.stats["end_time"] = datetime.now()
        report = self.get_performance_report()
        self.logger.info(f"Monitoring session ended. Report: {report}")

    def record_error(self, error: ScrapingError):
        """Record an error that occurred during scraping"""
        self.errors.append(error)
        self.stats["errors_total"] += 1

        # Log error with appropriate level
        if error.error_type == ErrorType.RATE_LIMIT_ERROR:
            self.logger.warning(f"Rate limit error: {error}")
        elif error.error_type == ErrorType.NETWORK_ERROR:
            self.logger.warning(f"Network error: {error}")
        else:
            self.logger.error(f"Scraping error: {error}")

    def record_success(self, papers_count: int, venue: str, year: int):
        """Record successful scraping operation"""
        self.stats["papers_collected"] += papers_count
        self.stats["venues_processed"] += 1

        self.logger.info(
            f"Successfully scraped {papers_count} papers from {venue} {year}"
        )

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type"""
        summary = {}
        for error in self.errors:
            error_type = error.error_type.value
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        duration = None
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()
        elif self.stats["start_time"]:
            duration = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            "papers_collected": self.stats["papers_collected"],
            "venues_processed": self.stats["venues_processed"],
            "total_errors": self.stats["errors_total"],
            "error_rate": self.stats["errors_total"]
            / max(1, self.stats["venues_processed"]),
            "duration_seconds": duration,
            "papers_per_second": self.stats["papers_collected"] / max(1, duration or 1),
            "error_summary": self.get_error_summary(),
        }

    def get_recent_errors(self, limit: int = 10) -> List[ScrapingError]:
        """Get most recent errors"""
        return sorted(self.errors, key=lambda e: e.timestamp, reverse=True)[:limit]


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying functions on specific errors with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            current_delay = delay

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.RequestException as e:
                    retries += 1

                    if retries > max_retries:
                        raise ScrapingError(
                            error_type=ErrorType.NETWORK_ERROR,
                            message=f"Network error after {max_retries} retries: {str(e)}",
                            traceback=traceback.format_exc(),
                            retry_count=retries - 1,
                        )

                    time.sleep(current_delay)
                    current_delay *= backoff

                except Exception as e:
                    # Don't retry on non-network errors by default
                    raise ScrapingError(
                        error_type=ErrorType.PARSING_ERROR,
                        message=f"Unexpected error: {str(e)}",
                        traceback=traceback.format_exc(),
                        retry_count=retries,
                    )

        return wrapper

    return decorator


class RateLimiter:
    """Intelligent rate limiting with adaptive backoff based on errors"""

    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self.consecutive_errors = 0
        self.max_backoff_multiplier = 32  # Cap exponential backoff

    def wait(self):
        """Wait appropriate amount based on rate limit and recent errors"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Base delay from configured rate limit
        required_delay = self.min_interval

        # Exponential backoff for consecutive errors
        if self.consecutive_errors > 0:
            backoff_multiplier = min(
                2**self.consecutive_errors, self.max_backoff_multiplier
            )
            required_delay *= backoff_multiplier

        # Only sleep if we haven't waited long enough
        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def record_success(self):
        """Record successful request - resets error count"""
        self.consecutive_errors = 0

    def record_error(self):
        """Record failed request - increases backoff"""
        self.consecutive_errors += 1

    def get_current_delay(self) -> float:
        """Get current delay without applying it"""
        if self.consecutive_errors == 0:
            return self.min_interval

        backoff_multiplier = min(
            2**self.consecutive_errors, self.max_backoff_multiplier
        )
        return self.min_interval * backoff_multiplier

    def reset(self):
        """Reset the rate limiter state"""
        self.consecutive_errors = 0
        self.last_request_time = 0.0
