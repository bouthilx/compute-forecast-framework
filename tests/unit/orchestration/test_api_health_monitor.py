"""
Tests for APIHealthMonitor - API Health Monitoring and Status Tracking
Following TDD approach - focused essential tests
"""

import pytest
from unittest.mock import Mock
import requests

from compute_forecast.pipeline.metadata_collection.models import APIHealthStatus


class TestAPIHealthMonitor:
    """Test the APIHealthMonitor class"""

    def setup_method(self):
        """Setup test fixtures"""
        from compute_forecast.pipeline.metadata_collection.collectors.api_health_monitor import (
            APIHealthMonitor,
        )

        self.monitor = APIHealthMonitor()

    def test_monitor_api_health_successful_response(self):
        """Test monitoring healthy API responses"""
        api_name = "semantic_scholar"

        # Mock successful response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True

        status = self.monitor.monitor_api_health(api_name, mock_response, 500.0)

        assert isinstance(status, APIHealthStatus)
        assert status.api_name == api_name
        assert status.status == "healthy"
        assert status.success_rate > 0.9
        assert status.avg_response_time_ms > 0
        assert status.consecutive_errors == 0

    def test_monitor_api_health_failed_response(self):
        """Test monitoring failed API responses"""
        api_name = "semantic_scholar"

        # Mock failed response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.ok = False

        status = self.monitor.monitor_api_health(api_name, mock_response, 5000.0)

        assert status.status in ["degraded", "critical"]
        assert status.consecutive_errors > 0
        assert status.last_error is not None

    def test_get_health_status_returns_current_status(self):
        """Test getting current health status"""
        api_name = "openalex"

        # Monitor some requests first
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True

        self.monitor.monitor_api_health(api_name, mock_response, 300.0)

        # Get status
        status = self.monitor.get_health_status(api_name)
        assert isinstance(status, APIHealthStatus)
        assert status.api_name == api_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
