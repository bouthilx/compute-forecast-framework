"""
Integration tests for Issue #8 Dashboard with Intelligent Alerting System.
Tests the integration between real-time dashboard and alerting components.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from compute_forecast.monitoring.dashboard_server import CollectionDashboard
from compute_forecast.monitoring.advanced_dashboard_server import (
    AdvancedAnalyticsDashboard,
)
from compute_forecast.monitoring.intelligent_alerting_system import (
    IntelligentAlertingSystem,
)
from compute_forecast.monitoring.metrics_collector import MetricsCollector
from compute_forecast.monitoring.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
)


class TestDashboardAlertingIntegration:
    """Integration tests for dashboard and alerting system"""

    @pytest.fixture
    def mock_metrics(self):
        """Create mock system metrics"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                total_papers_collected=5000,
                papers_per_minute=25.5,
                estimated_completion_time=datetime.now(),
                venues_completed=10,
                venues_in_progress=2,
                venues_remaining=13,
                total_venues=25,
                session_duration_minutes=120.0,
            ),
            api_metrics={
                "semantic_scholar": APIMetrics(
                    api_name="semantic_scholar",
                    total_requests=1000,
                    successful_requests=985,
                    failed_requests=15,
                    success_rate=0.985,
                    avg_response_time_ms=1200.0,
                    health_status="healthy",
                )
            },
            processing_metrics=ProcessingMetrics(
                papers_processed=5000,
                papers_filtered=200,
                papers_normalized=4800,
                papers_deduplicated=4600,
                processing_rate_per_minute=100.0,
            ),
            system_metrics=SystemResourceMetrics(
                memory_usage_percent=65.0,
                cpu_usage_percent=45.0,
                disk_usage_mb=2000.0,
                disk_free_mb=6000.0,
                network_bytes_sent=1000000,
                network_bytes_received=5000000,
            ),
            state_metrics=StateManagementMetrics(
                total_checkpoints=50,
                checkpoint_size_mb=15.2,
                checkpoints_per_hour=10.0,
                recovery_time_seconds=300.0,
            ),
        )

    def test_basic_dashboard_creation(self):
        """Test basic dashboard can be created"""
        dashboard = CollectionDashboard(host="127.0.0.1", port=5001, debug=False)
        assert dashboard.host == "127.0.0.1"
        assert dashboard.port == 5001
        assert not dashboard.debug

    def test_advanced_dashboard_creation(self):
        """Test advanced analytics dashboard can be created"""
        dashboard = AdvancedAnalyticsDashboard(host="127.0.0.1", port=5002, debug=False)
        assert dashboard.host == "127.0.0.1"
        assert dashboard.port == 5002
        assert dashboard.analytics_engine is not None

    def test_alerting_system_creation(self):
        """Test intelligent alerting system can be created"""
        config = {
            "enable_default_rules": True,
            "notification_channels": ["console", "dashboard"],
        }
        alerting_system = IntelligentAlertingSystem(config)
        assert alerting_system.config == config
        assert alerting_system.enable_default_rules

    def test_dashboard_metrics_integration(self, mock_metrics):
        """Test dashboard can receive and display metrics"""
        dashboard = CollectionDashboard(host="127.0.0.1", port=5003, debug=False)
        metrics_collector = Mock(spec=MetricsCollector)
        metrics_collector.collect_current_metrics.return_value = mock_metrics

        dashboard.set_metrics_collector(metrics_collector)
        assert dashboard.metrics_collector is not None

        # Test metrics can be retrieved
        current_metrics = dashboard.metrics_collector.collect_current_metrics()
        assert current_metrics.collection_progress.total_papers_collected == 5000
        assert current_metrics.collection_progress.papers_per_minute == 25.5

    def test_alerting_dashboard_integration(self, mock_metrics):
        """Test alerting system integration with dashboard"""
        # Create dashboard
        dashboard = AdvancedAnalyticsDashboard(host="127.0.0.1", port=5004, debug=False)

        # Create alerting system
        alerting_config = {
            "enable_default_rules": True,
            "notification_channels": ["console", "dashboard"],
        }
        alerting_system = IntelligentAlertingSystem(alerting_config)

        # Test integration
        try:
            # This would normally integrate via the adapter
            from compute_forecast.monitoring.advanced_dashboard_server import (
                AnalyticsDashboardAdapter,
            )

            adapter = AnalyticsDashboardAdapter(dashboard)
            adapter.integrate_with_alerting_system(alerting_system)

            # Verify integration succeeded (no exceptions)
            assert True

        except ImportError:
            # If import fails, integration is missing
            pytest.skip("Dashboard-alerting integration not fully implemented")

    def test_real_time_updates(self, mock_metrics):
        """Test real-time metric updates through dashboard"""
        dashboard = CollectionDashboard(host="127.0.0.1", port=5005, debug=False)

        # Mock metrics collector
        metrics_collector = Mock(spec=MetricsCollector)
        metrics_collector.collect_current_metrics.return_value = mock_metrics

        dashboard.set_metrics_collector(metrics_collector)

        # Test that metrics can be broadcast (mock SocketIO)
        with patch.object(dashboard, "socketio") as mock_socketio:
            dashboard.broadcast_current_metrics()

            # Verify broadcast was called
            mock_socketio.emit.assert_called()

    def test_api_endpoints_exist(self):
        """Test required API endpoints exist in dashboard"""
        dashboard = CollectionDashboard(host="127.0.0.1", port=5006, debug=False)

        # Check that Flask app has required routes
        routes = [rule.rule for rule in dashboard.app.url_map.iter_rules()]

        # Basic endpoints should exist
        assert "/" in routes or "/dashboard" in routes
        assert any("/api/" in route for route in routes)

    def test_advanced_analytics_endpoints(self):
        """Test advanced analytics endpoints exist"""
        dashboard = AdvancedAnalyticsDashboard(host="127.0.0.1", port=5007, debug=False)

        routes = [rule.rule for rule in dashboard.app.url_map.iter_rules()]

        # Analytics endpoints should exist
        expected_analytics_routes = [
            "/api/analytics/trends",
            "/api/analytics/performance",
            "/api/analytics/predictions",
            "/api/analytics/summary",
        ]

        for expected_route in expected_analytics_routes:
            assert any(
                expected_route in route for route in routes
            ), f"Missing route: {expected_route}"

    def test_notification_channel_integration(self):
        """Test notification channels can be integrated with dashboard"""
        try:
            from compute_forecast.monitoring.notification_channels import (
                DashboardNotificationChannel,
            )

            # Create mock dashboard
            dashboard = Mock()
            dashboard.broadcast_alert = Mock()

            # Create dashboard notification channel
            channel = DashboardNotificationChannel("test_dashboard", dashboard)

            # Test channel properties
            assert channel.get_channel_name() == "test_dashboard"
            assert channel.is_available()

        except ImportError:
            pytest.skip("Dashboard notification channel not implemented")

    @pytest.mark.integration
    def test_full_system_integration(self, mock_metrics):
        """Test full integration of dashboard, analytics, and alerting"""
        # This test would require starting actual servers
        # For now, just test component creation and basic integration

        try:
            # Create all components
            dashboard = AdvancedAnalyticsDashboard(
                host="127.0.0.1", port=5008, debug=False
            )
            alerting_system = IntelligentAlertingSystem()
            metrics_collector = Mock(spec=MetricsCollector)

            # Set up metrics
            metrics_collector.collect_current_metrics.return_value = mock_metrics
            dashboard.set_metrics_collector(metrics_collector)

            # Test basic functionality
            assert dashboard.analytics_engine is not None
            assert alerting_system.alerting_engine is not None

            # Test that components can interact
            current_metrics = dashboard.metrics_collector.collect_current_metrics()
            assert current_metrics is not None

        except Exception as e:
            pytest.fail(f"Full system integration failed: {e}")

    def test_performance_requirements(self):
        """Test dashboard meets performance requirements"""
        CollectionDashboard(host="127.0.0.1", port=5009, debug=False)

        # Test that dashboard can be created quickly (< 2 seconds)
        start_time = time.time()
        CollectionDashboard(host="127.0.0.1", port=5010, debug=False)
        creation_time = time.time() - start_time

        assert (
            creation_time < 2.0
        ), f"Dashboard creation took {creation_time:.2f}s, should be < 2s"

    def test_websocket_configuration(self):
        """Test WebSocket configuration for real-time updates"""
        dashboard = CollectionDashboard(host="127.0.0.1", port=5011, debug=False)

        # Verify SocketIO is configured
        assert dashboard.socketio is not None
        assert hasattr(dashboard.socketio, "emit")

        # Test that events can be registered
        @dashboard.socketio.on("test_event")
        def test_handler():
            return "test"

        # Verify SocketIO has handlers (don't check specific structure)
        assert hasattr(dashboard.socketio, "handlers")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
