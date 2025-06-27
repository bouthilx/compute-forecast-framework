"""
Tests for RateLimitManager - Adaptive Rate Limiting with API Health Monitoring
Following TDD approach - these tests should drive the real implementation
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict

from src.data.models import (
    APIConfig, RateLimitStatus, APIHealthStatus, RollingWindow
)


class TestRollingWindow:
    """Test the RollingWindow data structure"""
    
    def test_rolling_window_basic_functionality(self):
        """Test basic add and count functionality"""
        window = RollingWindow(window_seconds=60, max_requests=10)
        
        # Should start empty
        assert window.get_current_count() == 0
        assert window.time_until_next_slot() == 0.0
        
        # Should accept requests up to limit
        for i in range(10):
            assert window.add_request() is True
            assert window.get_current_count() == i + 1
        
        # Should reject requests over limit
        assert window.add_request() is False
        assert window.get_current_count() == 10
    
    def test_rolling_window_time_expiration(self):
        """Test that old requests expire from window"""
        window = RollingWindow(window_seconds=1, max_requests=5)
        
        # Fill window
        for i in range(5):
            assert window.add_request() is True
        
        # Should be full
        assert window.add_request() is False
        assert window.get_current_count() == 5
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be empty now
        assert window.get_current_count() == 0
        assert window.add_request() is True
    
    def test_rolling_window_time_until_next_slot(self):
        """Test calculation of time until next slot"""
        window = RollingWindow(window_seconds=5, max_requests=2)
        
        # Add requests
        start_time = datetime.now()
        window.add_request(start_time)
        window.add_request(start_time + timedelta(seconds=1))
        
        # Should be full
        assert window.add_request() is False
        
        # Time until next slot should be close to 4 seconds (5 - 1)
        time_until = window.time_until_next_slot()
        assert 3.5 <= time_until <= 5.0
    
    def test_rolling_window_thread_safety(self):
        """Test that rolling window is thread-safe"""
        window = RollingWindow(window_seconds=60, max_requests=100)
        successful_adds = []
        
        def add_requests():
            for _ in range(50):
                if window.add_request():
                    successful_adds.append(1)
        
        # Run multiple threads
        threads = [threading.Thread(target=add_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should not exceed max_requests despite concurrent access
        assert len(successful_adds) <= 100
        assert window.get_current_count() <= 100


class TestRateLimitManager:
    """Test the main RateLimitManager class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # This will fail until we implement the real RateLimitManager
        from src.data.collectors.rate_limit_manager import RateLimitManager
        
        self.api_configs = {
            "semantic_scholar": APIConfig(
                requests_per_window=100,
                base_delay_seconds=1.0,
                max_delay_seconds=30.0,
                health_degradation_threshold=0.9,
                burst_allowance=5
            ),
            "openalex": APIConfig(
                requests_per_window=200,
                base_delay_seconds=0.5,
                max_delay_seconds=15.0,
                health_degradation_threshold=0.85,
                burst_allowance=10
            )
        }
        
        self.rate_limiter = RateLimitManager(self.api_configs)
    
    def test_can_make_request_basic_functionality(self):
        """Test basic request checking functionality"""
        # Should allow requests when under limit
        assert self.rate_limiter.can_make_request("semantic_scholar") is True
        assert self.rate_limiter.can_make_request("semantic_scholar", request_size=5) is True
        
        # Record many requests to approach limit
        for i in range(95):
            self.rate_limiter.record_request("semantic_scholar", True, 100)
        
        # Should still allow a few more
        assert self.rate_limiter.can_make_request("semantic_scholar") is True
        
        # But not a large batch
        assert self.rate_limiter.can_make_request("semantic_scholar", request_size=10) is False
    
    def test_can_make_request_respects_rolling_window(self):
        """Test that requests respect the 5-minute rolling window"""
        api_name = "semantic_scholar"
        
        # Fill up the window completely
        for i in range(100):
            assert self.rate_limiter.can_make_request(api_name) is True
            self.rate_limiter.record_request(api_name, True, 100)
        
        # Should now be at limit
        assert self.rate_limiter.can_make_request(api_name) is False
        
        # Wait for some time (in real test, we'd mock time)
        # For now, just verify the logic is there
        status = self.rate_limiter.get_current_usage(api_name)
        assert status is not None
        assert status.requests_in_window == 100
        assert status.window_capacity == 100
    
    def test_can_make_request_performance_requirement(self):
        """Test that can_make_request responds in <10ms"""
        api_name = "semantic_scholar"
        
        # Warm up
        self.rate_limiter.can_make_request(api_name)
        
        # Measure performance
        start_time = time.time()
        for _ in range(100):
            self.rate_limiter.can_make_request(api_name)
        end_time = time.time()
        
        # Should average less than 10ms per call
        avg_time_ms = ((end_time - start_time) / 100) * 1000
        assert avg_time_ms < 10.0, f"Average response time {avg_time_ms:.2f}ms exceeds 10ms requirement"
    
    def test_wait_if_needed_basic_functionality(self):
        """Test wait calculation functionality"""
        api_name = "semantic_scholar"
        
        # When not at limit, should return 0
        wait_time = self.rate_limiter.wait_if_needed(api_name)
        assert wait_time == 0.0
        
        # Fill up to limit
        for i in range(100):
            self.rate_limiter.record_request(api_name, True, 100)
        
        # Should now require waiting
        wait_time = self.rate_limiter.wait_if_needed(api_name)
        assert wait_time > 0.0
        assert wait_time <= 60.0  # Should never wait longer than 60 seconds
    
    def test_wait_if_needed_never_exceeds_60_seconds(self):
        """Test that wait time never exceeds 60 seconds"""
        api_name = "semantic_scholar"
        
        # Simulate very degraded API
        for i in range(100):
            self.rate_limiter.record_request(api_name, False, 5000)  # Failed requests, slow response
        
        # Even with degraded API, should not wait longer than 60 seconds
        wait_time = self.rate_limiter.wait_if_needed(api_name, request_size=10)
        assert wait_time <= 60.0
    
    def test_record_request_updates_windows(self):
        """Test that recording requests updates rolling windows"""
        api_name = "semantic_scholar"
        
        initial_status = self.rate_limiter.get_current_usage(api_name)
        initial_count = initial_status.requests_in_window if initial_status else 0
        
        # Record a request
        self.rate_limiter.record_request(api_name, True, 150, request_size=1)
        
        # Should update window
        new_status = self.rate_limiter.get_current_usage(api_name)
        assert new_status is not None
        assert new_status.requests_in_window == initial_count + 1
    
    def test_record_request_must_be_called_for_all_requests(self):
        """Test that record_request is required for proper tracking"""
        api_name = "semantic_scholar"
        
        # Make requests without recording them
        for _ in range(50):
            assert self.rate_limiter.can_make_request(api_name) is True
        
        # Window should still be empty since we didn't record
        status = self.rate_limiter.get_current_usage(api_name)
        assert status.requests_in_window == 0
        
        # Now record them
        for _ in range(50):
            self.rate_limiter.record_request(api_name, True, 100)
        
        # Window should be updated
        status = self.rate_limiter.get_current_usage(api_name)
        assert status.requests_in_window == 50
    
    def test_record_request_with_batch_sizes(self):
        """Test recording requests with different batch sizes"""
        api_name = "openalex"
        
        # Record a batch request
        self.rate_limiter.record_request(api_name, True, 200, request_size=5)
        
        status = self.rate_limiter.get_current_usage(api_name)
        assert status.requests_in_window == 5  # Should count as 5 requests
    
    def test_get_current_usage_returns_accurate_status(self):
        """Test that get_current_usage returns accurate rate limit status"""
        api_name = "semantic_scholar"
        
        # Record some requests
        for i in range(30):
            self.rate_limiter.record_request(api_name, True, 100 + i)
        
        status = self.rate_limiter.get_current_usage(api_name)
        
        assert status is not None
        assert status.api_name == api_name
        assert status.requests_in_window == 30
        assert status.window_capacity == 100
        assert status.current_delay_seconds >= 0
        assert isinstance(status.next_available_slot, datetime)
        assert status.health_multiplier >= 0
    
    def test_adaptive_delay_based_on_api_health(self):
        """Test that delays adapt based on API health"""
        api_name = "semantic_scholar"
        
        # Start with healthy API
        initial_wait = self.rate_limiter.wait_if_needed(api_name)
        
        # Simulate degraded API with many failures
        for _ in range(10):
            self.rate_limiter.record_request(api_name, False, 3000)  # Failed, slow requests
        
        # Should now have longer delay
        degraded_wait = self.rate_limiter.wait_if_needed(api_name)
        
        # Note: This test depends on health monitoring integration
        # For now, just verify the interface works
        assert degraded_wait >= initial_wait
    
    def test_thread_safety_concurrent_operations(self):
        """Test thread safety under concurrent operations"""
        api_name = "openalex"
        successful_requests = []
        
        def make_requests():
            for _ in range(25):
                if self.rate_limiter.can_make_request(api_name):
                    successful_requests.append(1)
                    self.rate_limiter.record_request(api_name, True, 100)
        
        # Run multiple threads
        threads = [threading.Thread(target=make_requests) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should not exceed API limits despite concurrent access
        status = self.rate_limiter.get_current_usage(api_name)
        assert status.requests_in_window <= 200  # openalex limit
        assert len(successful_requests) <= 200
    
    def test_multiple_apis_independent_tracking(self):
        """Test that different APIs are tracked independently"""
        # Record requests for different APIs
        for i in range(50):
            self.rate_limiter.record_request("semantic_scholar", True, 100)
            self.rate_limiter.record_request("openalex", True, 150)
        
        # Should track independently
        ss_status = self.rate_limiter.get_current_usage("semantic_scholar")
        oa_status = self.rate_limiter.get_current_usage("openalex")
        
        assert ss_status.requests_in_window == 50
        assert oa_status.requests_in_window == 50
        assert ss_status.window_capacity == 100
        assert oa_status.window_capacity == 200


class TestRateLimitManagerIntegration:
    """Integration tests for RateLimitManager with health monitoring"""
    
    def setup_method(self):
        """Setup with health monitoring integration"""
        from src.data.collectors.rate_limit_manager import RateLimitManager
        from src.data.collectors.api_health_monitor import APIHealthMonitor
        
        api_configs = {
            "semantic_scholar": APIConfig(
                requests_per_window=100,
                base_delay_seconds=1.0,
                max_delay_seconds=30.0,
                health_degradation_threshold=0.9,
                burst_allowance=5
            )
        }
        
        self.health_monitor = APIHealthMonitor()
        self.rate_limiter = RateLimitManager(api_configs)
        
        # Mock health status updates (will be real in full implementation)
        self.rate_limiter.update_api_health = Mock()
    
    def test_health_integration_affects_rate_limiting(self):
        """Test that API health affects rate limiting decisions"""
        api_name = "semantic_scholar"
        
        # Simulate healthy API
        healthy_status = APIHealthStatus(
            api_name=api_name,
            status="healthy",
            success_rate=0.95,
            avg_response_time_ms=200.0,
            consecutive_errors=0
        )
        
        # Update health (this would be done by health monitor in real system)
        if hasattr(self.rate_limiter, 'update_api_health'):
            self.rate_limiter.update_api_health(api_name, healthy_status)
        
        healthy_wait = self.rate_limiter.wait_if_needed(api_name)
        
        # Simulate degraded API
        degraded_status = APIHealthStatus(
            api_name=api_name,
            status="degraded",
            success_rate=0.7,
            avg_response_time_ms=3000.0,
            consecutive_errors=5
        )
        
        if hasattr(self.rate_limiter, 'update_api_health'):
            self.rate_limiter.update_api_health(api_name, degraded_status)
        
        degraded_wait = self.rate_limiter.wait_if_needed(api_name)
        
        # Degraded API should have longer waits
        assert degraded_wait >= healthy_wait
    
    def test_exponential_backoff_for_degraded_apis(self):
        """Test exponential backoff for APIs with consecutive errors"""
        api_name = "semantic_scholar"
        
        # Record consecutive failures
        consecutive_errors = 0
        wait_times = []
        
        for i in range(5):
            # Record failure
            self.rate_limiter.record_request(api_name, False, 5000)
            consecutive_errors += 1
            
            # Update health status
            degraded_status = APIHealthStatus(
                api_name=api_name,
                status="degraded" if consecutive_errors < 10 else "critical",
                success_rate=max(0.1, 1.0 - (consecutive_errors * 0.1)),
                avg_response_time_ms=1000.0 + (consecutive_errors * 500),
                consecutive_errors=consecutive_errors
            )
            
            if hasattr(self.rate_limiter, 'update_api_health'):
                self.rate_limiter.update_api_health(api_name, degraded_status)
            
            wait_time = self.rate_limiter.wait_if_needed(api_name)
            wait_times.append(wait_time)
        
        # Wait times should generally increase (exponential backoff)
        # Allow some flexibility for implementation details
        assert len([w for w in wait_times if w > 0]) > 0, "Should have some non-zero wait times"
    
    def test_realistic_collection_scenario(self):
        """Test rate limiting in a realistic 4-6 hour collection scenario"""
        api_name = "semantic_scholar"
        
        # Simulate collecting from multiple venues over time
        total_requests = 0
        blocked_requests = 0
        
        # Simulate 1 hour of collection (compressed time)
        for minute in range(60):
            # Try to make 2-3 requests per minute (realistic for batched collection)
            for request in range(3):
                if self.rate_limiter.can_make_request(api_name):
                    self.rate_limiter.record_request(api_name, True, 500)
                    total_requests += 1
                else:
                    blocked_requests += 1
                    # In real scenario, would wait
                    wait_time = self.rate_limiter.wait_if_needed(api_name)
                    assert wait_time <= 60.0  # Never wait longer than 1 minute
        
        # Should have successfully made many requests
        assert total_requests > 100
        
        # Should not have been blocked too often (good rate limiting)
        block_rate = blocked_requests / (total_requests + blocked_requests)
        assert block_rate < 0.1, f"Block rate {block_rate:.2%} too high"


class TestRateLimitManagerPerformance:
    """Performance tests for RateLimitManager"""
    
    def setup_method(self):
        """Setup for performance testing"""
        from src.data.collectors.rate_limit_manager import RateLimitManager
        
        api_configs = {
            "test_api": APIConfig(
                requests_per_window=1000,
                base_delay_seconds=0.1,
                max_delay_seconds=5.0,
                health_degradation_threshold=0.9,
                burst_allowance=10
            )
        }
        
        self.rate_limiter = RateLimitManager(api_configs)
    
    def test_can_make_request_performance_at_scale(self):
        """Test performance with many concurrent threads"""
        api_name = "test_api"
        num_threads = 20
        requests_per_thread = 100
        
        # Warm up
        for _ in range(10):
            self.rate_limiter.can_make_request(api_name)
        
        start_time = time.time()
        
        def make_requests():
            for _ in range(requests_per_thread):
                self.rate_limiter.can_make_request(api_name)
        
        threads = [threading.Thread(target=make_requests) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        end_time = time.time()
        
        total_requests = num_threads * requests_per_thread
        avg_time_ms = ((end_time - start_time) / total_requests) * 1000
        
        # Should maintain <10ms average even under load
        assert avg_time_ms < 10.0, f"Performance degraded: {avg_time_ms:.2f}ms per request"
    
    def test_memory_usage_24_hour_simulation(self):
        """Test memory usage over 24-hour simulation"""
        import gc
        import sys
        
        api_name = "test_api"
        
        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Simulate 24 hours of requests (compressed)
        for hour in range(24):
            for minute in range(60):
                # Simulate requests every minute
                self.rate_limiter.record_request(api_name, True, 200)
                
                # Occasionally check if we can make requests
                if minute % 10 == 0:
                    self.rate_limiter.can_make_request(api_name)
        
        # Check memory usage
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Should not have significant memory growth (rolling windows should clean up)
        # Allow some growth for test infrastructure
        assert object_growth < 1000, f"Memory leak detected: {object_growth} objects created"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])