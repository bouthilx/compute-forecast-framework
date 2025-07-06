"""
Integration Test for End-to-End API Collection Workflow
Tests the complete workflow from rate limiting through health monitoring to API collection
"""

import pytest
import time
import threading
from unittest.mock import Mock

from compute_forecast.data.models import (
    APIConfig,
    HealthMonitoringConfig,
    RateLimitingConfig,
)
from compute_forecast.data.collectors.rate_limit_manager import RateLimitManager
from compute_forecast.data.collectors.api_health_monitor import APIHealthMonitor


class TestIntegrationWorkflow:
    """Integration tests for complete API collection workflow"""

    def setup_method(self):
        """Setup integrated system components"""
        # Configure APIs with realistic settings
        self.api_configs = {
            "semantic_scholar": APIConfig(
                requests_per_window=100,
                base_delay_seconds=1.0,
                max_delay_seconds=30.0,
                health_degradation_threshold=0.9,
                burst_allowance=5,
            ),
            "openalex": APIConfig(
                requests_per_window=200,
                base_delay_seconds=0.5,
                max_delay_seconds=15.0,
                health_degradation_threshold=0.85,
                burst_allowance=10,
            ),
        }

        self.rate_limiter = RateLimitManager(self.api_configs)
        self.health_monitor = APIHealthMonitor()

    def test_complete_api_collection_workflow(self):
        """Test complete workflow: rate limiting -> API call -> health monitoring -> adaptation"""
        api_name = "semantic_scholar"

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True

        # Simulate complete workflow cycle
        workflow_results = []

        for i in range(10):
            # 1. Check rate limits
            can_proceed = self.rate_limiter.can_make_request(api_name)
            assert can_proceed, f"Rate limiter should allow request {i}"

            # 2. Simulate API call timing
            start_time = time.time()
            # Mock API processing time
            time.sleep(0.01)  # 10ms simulated API call
            response_time_ms = (time.time() - start_time) * 1000

            # 3. Monitor API health
            health_status = self.health_monitor.monitor_api_health(
                api_name, mock_response, response_time_ms
            )

            # 4. Record request for rate limiting
            self.rate_limiter.record_request(api_name, True, int(response_time_ms))

            # 5. Update rate limiter with health status
            self.rate_limiter.update_api_health(api_name, health_status)

            workflow_results.append(
                {
                    "iteration": i,
                    "can_proceed": can_proceed,
                    "response_time": response_time_ms,
                    "health_status": health_status.status,
                    "success_rate": health_status.success_rate,
                }
            )

        # Verify workflow completed successfully
        assert len(workflow_results) == 10
        assert all(result["can_proceed"] for result in workflow_results)
        assert all(result["health_status"] == "healthy" for result in workflow_results)

        # Verify rate limiting is tracking correctly
        usage = self.rate_limiter.get_current_usage(api_name)
        assert usage.requests_in_window == 10

    def test_degraded_api_adaptive_behavior(self):
        """Test system adaptation when API becomes degraded"""
        api_name = "openalex"

        # Start with healthy responses
        healthy_response = Mock()
        healthy_response.status_code = 200
        healthy_response.ok = True

        # Make initial successful requests
        for _ in range(5):
            self.rate_limiter.record_request(api_name, True, 200)
            self.health_monitor.monitor_api_health(api_name, healthy_response, 200.0)

        initial_usage = self.rate_limiter.get_current_usage(api_name)
        initial_health = self.health_monitor.get_health_status(api_name)

        assert initial_health.status == "healthy"
        assert initial_usage.health_multiplier == RateLimitingConfig.HEALTHY_MULTIPLIER

        # Simulate API degradation with slow responses and errors
        degraded_response = Mock()
        degraded_response.status_code = 500
        degraded_response.ok = False

        # Generate enough errors to trigger degradation
        for _ in range(HealthMonitoringConfig.DEGRADED_CONSECUTIVE_ERRORS + 1):
            self.rate_limiter.record_request(api_name, False, 5000)
            health_status = self.health_monitor.monitor_api_health(
                api_name, degraded_response, 5000.0
            )
            self.rate_limiter.update_api_health(api_name, health_status)

        # Verify system adapted to degraded state
        degraded_usage = self.rate_limiter.get_current_usage(api_name)
        degraded_health = self.health_monitor.get_health_status(api_name)

        assert degraded_health.status in ["degraded", "critical"]
        assert degraded_usage.health_multiplier > initial_usage.health_multiplier
        assert (
            degraded_usage.current_delay_seconds > initial_usage.current_delay_seconds
        )

    def test_concurrent_api_usage_isolation(self):
        """Test that multiple APIs are properly isolated and don't interfere"""
        apis = ["semantic_scholar", "openalex"]
        results = {}

        def api_worker(api_name):
            """Worker function to simulate concurrent API usage"""
            worker_results = []
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True

            for i in range(15):
                # Different APIs have different patterns
                response_time = 300 if api_name == "semantic_scholar" else 150
                success = True

                if self.rate_limiter.can_make_request(api_name):
                    self.rate_limiter.record_request(api_name, success, response_time)
                    health_status = self.health_monitor.monitor_api_health(
                        api_name, mock_response, response_time
                    )
                    self.rate_limiter.update_api_health(api_name, health_status)
                    worker_results.append(True)
                else:
                    worker_results.append(False)

                # Small delay between requests
                time.sleep(0.001)

            results[api_name] = worker_results

        # Run concurrent workers
        threads = [threading.Thread(target=api_worker, args=(api,)) for api in apis]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify isolation - each API should have independent tracking
        for api_name in apis:
            usage = self.rate_limiter.get_current_usage(api_name)
            health = self.health_monitor.get_health_status(api_name)

            assert usage is not None, f"Usage tracking failed for {api_name}"
            assert health is not None, f"Health monitoring failed for {api_name}"
            assert (
                len(results[api_name]) == 15
            ), f"Worker didn't complete for {api_name}"

            # Should have successfully made most requests
            success_rate = sum(results[api_name]) / len(results[api_name])
            assert (
                success_rate > 0.8
            ), f"Success rate too low for {api_name}: {success_rate}"

    def test_recovery_from_api_outage(self):
        """Test system recovery when API comes back online after outage"""
        api_name = "semantic_scholar"

        # Simulate complete API outage
        failed_response = Mock()
        failed_response.status_code = 503
        failed_response.ok = False

        # Generate enough failures to mark API as offline
        for _ in range(HealthMonitoringConfig.OFFLINE_CONSECUTIVE_ERRORS + 2):
            self.rate_limiter.record_request(api_name, False, 10000)
            health_status = self.health_monitor.monitor_api_health(
                api_name, failed_response, 10000.0
            )
            self.rate_limiter.update_api_health(api_name, health_status)

        # Verify API is marked as offline
        offline_health = self.health_monitor.get_health_status(api_name)
        offline_usage = self.rate_limiter.get_current_usage(api_name)

        assert offline_health.status == "offline"
        assert offline_usage.health_multiplier == RateLimitingConfig.OFFLINE_MULTIPLIER

        # Simulate API recovery with successful responses
        healthy_response = Mock()
        healthy_response.status_code = 200
        healthy_response.ok = True

        # Generate successful requests to trigger recovery
        recovery_iterations = 20
        for i in range(recovery_iterations):
            self.rate_limiter.record_request(api_name, True, 200)
            health_status = self.health_monitor.monitor_api_health(
                api_name, healthy_response, 200.0
            )
            self.rate_limiter.update_api_health(api_name, health_status)

            # Check if recovery occurred
            if health_status.status == "healthy":
                break

        # Verify recovery
        recovered_health = self.health_monitor.get_health_status(api_name)
        recovered_usage = self.rate_limiter.get_current_usage(api_name)

        # Should recover to at least degraded status, ideally healthy
        assert recovered_health.status in ["healthy", "degraded"]
        assert recovered_usage.health_multiplier < offline_usage.health_multiplier
        assert recovered_health.consecutive_errors == 0

    def test_rate_limit_enforcement_under_load(self):
        """Test rate limiting enforcement under high concurrent load"""
        api_name = "openalex"  # 200 requests per 5-minute window
        request_attempts = []
        successful_requests = []

        def load_worker():
            """Worker that attempts many requests quickly"""
            for _ in range(50):
                if self.rate_limiter.can_make_request(api_name):
                    self.rate_limiter.record_request(api_name, True, 100)
                    successful_requests.append(1)
                request_attempts.append(1)

        # Run high-concurrency load
        threads = [threading.Thread(target=load_worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify rate limiting worked correctly
        total_attempts = len(request_attempts)
        total_successful = len(successful_requests)

        # Should have attempted many requests
        assert total_attempts == 8 * 50  # 400 attempts

        # But limited successful requests to API capacity
        usage = self.rate_limiter.get_current_usage(api_name)
        assert usage.requests_in_window <= 200  # OpenAlex limit
        assert total_successful <= 200

        # Rate limiting should be effective
        limitation_rate = (total_attempts - total_successful) / total_attempts
        assert (
            limitation_rate > 0.5
        ), f"Rate limiting too permissive: {limitation_rate:.2%}"

    def test_performance_requirements_under_integration(self):
        """Test that performance requirements are met during integrated operation"""
        api_name = "semantic_scholar"

        # Warm up the system
        for _ in range(10):
            self.rate_limiter.can_make_request(api_name)
            self.rate_limiter.record_request(api_name, True, 200)

        # Measure integrated performance
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            # Full workflow cycle
            can_proceed = self.rate_limiter.can_make_request(api_name)
            if can_proceed:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.ok = True

                health_status = self.health_monitor.monitor_api_health(
                    api_name, mock_response, 200.0
                )
                self.rate_limiter.record_request(api_name, True, 200)
                self.rate_limiter.update_api_health(api_name, health_status)

        end_time = time.time()

        # Verify performance requirements
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_operation = total_time_ms / iterations

        # Should maintain fast operation even with full integration
        assert (
            avg_time_per_operation < 15.0
        ), f"Integrated operation too slow: {avg_time_per_operation:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
