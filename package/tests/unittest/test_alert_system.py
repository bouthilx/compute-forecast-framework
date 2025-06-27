"""
Unit tests for the Intelligent Alert System functionality.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from collections import deque

from src.monitoring.alert_system import IntelligentAlertSystem
from src.monitoring.alert_structures import (
    AlertConfiguration, AlertRule, Alert, BUILT_IN_ALERT_RULES
)
from src.monitoring.dashboard_metrics import (
    SystemMetrics, CollectionProgressMetrics, APIMetrics, 
    ProcessingMetrics, SystemResourceMetrics, StateManagementMetrics
)


class TestIntelligentAlertSystem:
    """Test IntelligentAlertSystem functionality"""
    
    @pytest.fixture
    def alert_config(self):
        """Create test alert configuration"""
        return AlertConfiguration(
            collection_rate_threshold=10.0,
            api_error_rate_threshold=0.1,
            memory_usage_threshold=0.8,
            console_notifications=True,
            dashboard_notifications=False,  # Disable for testing
            enable_auto_suppression=True,
            max_alerts_per_hour=20,
            default_cooldown_minutes=5
        )
    
    @pytest.fixture
    def alert_system(self, alert_config):
        """Create test alert system"""
        return IntelligentAlertSystem(alert_config)
    
    @pytest.fixture
    def test_metrics(self):
        """Create test system metrics"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                session_id="test_session",
                total_venues=100,
                completed_venues=25,
                in_progress_venues=3,
                failed_venues=2,
                papers_collected=2500,
                papers_per_minute=15.5,
                estimated_total_papers=10000,
                completion_percentage=25.0,
                session_duration_minutes=160.0,
                estimated_remaining_minutes=480.0,
                estimated_completion_time=datetime.now() + timedelta(minutes=480)
            ),
            api_metrics={
                'semantic_scholar': APIMetrics(
                    api_name='semantic_scholar',
                    health_status='healthy',
                    requests_made=1000,
                    successful_requests=950,
                    failed_requests=50,
                    success_rate=0.95,
                    avg_response_time_ms=450.0,
                    min_response_time_ms=200.0,
                    max_response_time_ms=1000.0,
                    rate_limit_status={},
                    requests_throttled=0,
                    papers_collected=1500,
                    papers_per_request=1.5
                )
            },
            processing_metrics=ProcessingMetrics(
                venues_normalized=75,
                normalization_accuracy=0.95,
                normalization_rate_per_second=10.0,
                papers_deduplicated=2400,
                duplicates_removed=100,
                deduplication_rate=0.04,
                deduplication_confidence=0.92,
                papers_analyzed=2300,
                papers_above_threshold=1800,
                breakthrough_papers_found=45,
                filtering_rate_per_second=12.0
            ),
            system_metrics=SystemResourceMetrics.collect_current(),
            state_metrics=StateManagementMetrics(
                checkpoints_created=8,
                last_checkpoint_time=datetime.now() - timedelta(minutes=30),
                checkpoint_creation_rate_per_hour=2.0,
                recovery_possible=True,
                last_recovery_time=None,
                recovery_success_rate=1.0,
                state_size_mb=15.5,
                checkpoint_size_mb=7.8,
                checkpoint_creation_time_ms=200.0,
                state_save_time_ms=100.0
            ),
            venue_progress={}
        )
    
    def test_initialization(self, alert_system):
        """Test alert system initialization"""
        assert alert_system.config is not None
        assert len(alert_system.alert_rules) > 0  # Should have built-in rules
        assert alert_system.suppression_manager is not None
        assert alert_system.notification_manager is not None
        assert len(alert_system.alert_history) == 0
    
    def test_built_in_rules_loaded(self, alert_system):
        """Test that built-in alert rules are loaded"""
        assert len(alert_system.alert_rules) == len(BUILT_IN_ALERT_RULES)
        
        # Check specific built-in rules
        assert "collection_rate_low" in alert_system.alert_rules
        assert "api_health_degraded" in alert_system.alert_rules
        assert "high_error_rate" in alert_system.alert_rules
        assert "memory_usage_high" in alert_system.alert_rules
        assert "venue_collection_stalled" in alert_system.alert_rules
    
    def test_configure_alert_rule(self, alert_system):
        """Test configuring custom alert rules"""
        custom_rule = AlertRule(
            rule_id="test_rule",
            rule_name="Test Rule",
            description="Test alert rule",
            condition="metrics.collection_progress.papers_collected > 1000",
            severity="info",
            threshold_value=1000,
            evaluation_window_minutes=10,
            minimum_trigger_count=1,
            cooldown_period_minutes=5,
            notification_channels=["console"],
            suppress_duration_minutes=0,
            escalation_rules=[],
            recommended_actions=["Test action"],
            auto_actions=[],
            created_at=datetime.now()
        )
        
        result = alert_system.configure_alert_rule(custom_rule)
        assert result is True
        assert "test_rule" in alert_system.alert_rules
        assert alert_system.alert_rules["test_rule"] == custom_rule
    
    def test_evaluate_alerts_performance(self, alert_system, test_metrics):
        """Test that alert evaluation meets performance requirements (<500ms)"""
        start_time = time.time()
        alerts = alert_system.evaluate_alerts(test_metrics)
        evaluation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Should complete within 500ms requirement
        assert evaluation_time < 500
        assert isinstance(alerts, list)
    
    def test_evaluate_alerts_with_triggers(self, alert_system):
        """Test alert evaluation with conditions that should trigger"""
        # Create metrics that should trigger low collection rate alert
        low_rate_metrics = self._create_test_metrics(papers_per_minute=5.0)  # Below threshold of 10
        
        alerts = alert_system.evaluate_alerts(low_rate_metrics)
        
        # Should trigger collection_rate_low alert
        collection_rate_alerts = [a for a in alerts if a.rule_id == "collection_rate_low"]
        assert len(collection_rate_alerts) > 0
        
        alert = collection_rate_alerts[0]
        assert alert.severity == "warning"
        assert alert.current_value == 5.0
        assert alert.threshold_value == 10.0
    
    def test_evaluate_alerts_with_high_memory(self, alert_system):
        """Test memory usage alert"""
        # Create metrics with high memory usage
        high_memory_metrics = self._create_test_metrics(memory_usage=85.0)  # Above 80% threshold
        
        alerts = alert_system.evaluate_alerts(high_memory_metrics)
        
        # Should trigger memory usage alert
        memory_alerts = [a for a in alerts if a.rule_id == "memory_usage_high"]
        assert len(memory_alerts) > 0
        
        alert = memory_alerts[0]
        assert alert.severity == "warning"
        assert float(alert.current_value) == 85.0
    
    def test_alert_suppression(self, alert_system):
        """Test alert suppression functionality"""
        # Add suppression rule
        alert_system.suppress_alerts("collection_rate_low", 30, "Testing suppression")
        
        # Create triggering metrics
        low_rate_metrics = self._create_test_metrics(papers_per_minute=5.0)
        
        # Evaluate alerts - should be suppressed
        alerts = alert_system.evaluate_alerts(low_rate_metrics)
        
        # Should not trigger due to suppression
        collection_rate_alerts = [a for a in alerts if a.rule_id == "collection_rate_low"]
        assert len(collection_rate_alerts) == 0
        
        # Check suppression stats
        stats = alert_system.suppression_manager.get_suppression_statistics()
        assert stats['total_active_suppressions'] > 0
    
    def test_alert_cooldown(self, alert_system):
        """Test alert cooldown functionality"""
        low_rate_metrics = self._create_test_metrics(papers_per_minute=5.0)
        
        # First evaluation should trigger
        alerts1 = alert_system.evaluate_alerts(low_rate_metrics)
        collection_rate_alerts1 = [a for a in alerts1 if a.rule_id == "collection_rate_low"]
        assert len(collection_rate_alerts1) > 0
        
        # Immediate second evaluation should not trigger due to cooldown
        alerts2 = alert_system.evaluate_alerts(low_rate_metrics)
        collection_rate_alerts2 = [a for a in alerts2 if a.rule_id == "collection_rate_low"]
        assert len(collection_rate_alerts2) == 0
    
    def test_send_alert(self, alert_system):
        """Test sending alerts through notification channels"""
        # Create test alert
        test_alert = Alert(
            alert_id="test_alert_001",
            rule_id="collection_rate_low",
            timestamp=datetime.now(),
            severity="warning",
            title="Test Alert",
            message="Test alert message",
            affected_components=["test"],
            current_value=5.0,
            threshold_value=10.0,
            metrics_context={},
            recommended_actions=["Test action"],
            status="active"
        )
        
        # Send alert
        delivery_result = alert_system.send_alert(test_alert)
        
        assert delivery_result.alert_id == "test_alert_001"
        # Should succeed with console channel (dashboard disabled in test config)
        assert delivery_result.success
        assert "console" in delivery_result.delivery_channels
    
    def test_get_alert_summary(self, alert_system):
        """Test alert summary generation"""
        # Add some test alerts to history
        for i in range(5):
            test_alert = Alert(
                alert_id=f"test_alert_{i}",
                rule_id="test_rule",
                timestamp=datetime.now() - timedelta(minutes=i*10),
                severity="warning" if i % 2 == 0 else "error",
                title=f"Test Alert {i}",
                message=f"Test message {i}",
                affected_components=["test"],
                current_value=i,
                threshold_value=10,
                metrics_context={},
                recommended_actions=[],
                status="active"
            )
            alert_system.alert_history.append(test_alert)
        
        # Get summary
        summary = alert_system.get_alert_summary(1)  # Last 1 hour
        
        assert summary.time_period_hours == 1
        assert summary.total_alerts == 5
        assert "warning" in summary.alerts_by_severity
        assert "error" in summary.alerts_by_severity
        assert "test_rule" in summary.alerts_by_rule
        assert summary.avg_alerts_per_hour == 5.0
    
    def test_built_in_collection_rate_check(self, alert_system):
        """Test built-in collection rate check"""
        low_rate_metrics = self._create_test_metrics(papers_per_minute=5.0)
        
        alert = alert_system.check_collection_rate_alert(low_rate_metrics)
        
        assert alert is not None
        assert alert.rule_id == "collection_rate_low"
        assert alert.current_value == 5.0
        assert alert.threshold_value == 10.0
    
    def test_built_in_memory_usage_check(self, alert_system):
        """Test built-in memory usage check"""
        high_memory_metrics = self._create_test_metrics(memory_usage=85.0)
        
        alert = alert_system.check_memory_usage_alert(high_memory_metrics)
        
        assert alert is not None
        assert alert.rule_id == "memory_usage_high"
        assert float(alert.current_value) == 85.0
    
    def test_built_in_api_health_check(self, alert_system):
        """Test built-in API health check"""
        degraded_api_metrics = self._create_test_metrics()
        degraded_api_metrics.api_metrics['test_api'] = APIMetrics(
            api_name='test_api',
            health_status='degraded',  # This should trigger alert
            requests_made=100,
            successful_requests=80,
            failed_requests=20,
            success_rate=0.8,
            avg_response_time_ms=1000.0,
            min_response_time_ms=500.0,
            max_response_time_ms=2000.0,
            rate_limit_status={},
            requests_throttled=0,
            papers_collected=100,
            papers_per_request=1.0
        )
        
        alert = alert_system.check_api_health_alert(degraded_api_metrics)
        
        assert alert is not None
        assert alert.rule_id == "api_health_degraded"
        assert "test_api" in alert.affected_components
    
    def test_get_system_status(self, alert_system):
        """Test getting system status"""
        status = alert_system.get_system_status()
        
        assert "enabled_rules" in status
        assert "total_rules" in status
        assert "evaluation_stats" in status
        assert "suppression_stats" in status
        assert "notification_stats" in status
        assert "alert_history_size" in status
        
        assert status["total_rules"] > 0
        assert status["enabled_rules"] <= status["total_rules"]
    
    def test_auto_action_registration(self, alert_system):
        """Test registering auto-action handlers"""
        action_called = False
        
        def test_action_handler(alert):
            nonlocal action_called
            action_called = True
        
        alert_system.register_auto_action_handler("test_action", test_action_handler)
        
        # Create alert with auto-action
        test_alert = Alert(
            alert_id="test_alert_auto",
            rule_id="test_rule_auto",
            timestamp=datetime.now(),
            severity="warning",
            title="Test Auto Alert",
            message="Test auto action",
            affected_components=["test"],
            current_value=1,
            threshold_value=2,
            metrics_context={},
            recommended_actions=[],
            status="active"
        )
        
        # Configure rule with auto-action
        auto_rule = AlertRule(
            rule_id="test_rule_auto",
            rule_name="Test Auto Rule",
            description="Test auto rule",
            condition="True",
            severity="warning",
            threshold_value=1,
            evaluation_window_minutes=5,
            minimum_trigger_count=1,
            cooldown_period_minutes=1,
            notification_channels=["console"],
            suppress_duration_minutes=0,
            escalation_rules=[],
            recommended_actions=[],
            auto_actions=["test_action"],
            created_at=datetime.now()
        )
        
        alert_system.configure_alert_rule(auto_rule)
        
        # Send alert - should trigger auto-action
        delivery_result = alert_system.send_alert(test_alert)
        
        assert delivery_result.success
        assert action_called
    
    def _create_test_metrics(self, papers_per_minute=15.0, memory_usage=50.0) -> SystemMetrics:
        """Helper to create test metrics with specific values"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                session_id="test",
                total_venues=100,
                completed_venues=25,
                in_progress_venues=1,
                failed_venues=0,
                papers_collected=1500,
                papers_per_minute=papers_per_minute,
                estimated_total_papers=6000,
                completion_percentage=25.0,
                session_duration_minutes=100.0,
                estimated_remaining_minutes=300.0,
                estimated_completion_time=datetime.now() + timedelta(minutes=300)
            ),
            api_metrics={
                'semantic_scholar': APIMetrics(
                    api_name='semantic_scholar',
                    health_status='healthy',
                    requests_made=500,
                    successful_requests=475,
                    failed_requests=25,
                    success_rate=0.95,
                    avg_response_time_ms=400.0,
                    min_response_time_ms=200.0,
                    max_response_time_ms=800.0,
                    rate_limit_status={},
                    requests_throttled=0,
                    papers_collected=750,
                    papers_per_request=1.5
                )
            },
            processing_metrics=ProcessingMetrics(
                venues_normalized=50,
                normalization_accuracy=0.96,
                normalization_rate_per_second=8.0,
                papers_deduplicated=1450,
                duplicates_removed=50,
                deduplication_rate=0.033,
                deduplication_confidence=0.94,
                papers_analyzed=1400,
                papers_above_threshold=1100,
                breakthrough_papers_found=25,
                filtering_rate_per_second=10.0
            ),
            system_metrics=SystemResourceMetrics(
                memory_usage_percentage=memory_usage,
                memory_used_mb=memory_usage * 16000 / 100,  # Assume 16GB total
                memory_available_mb=(100 - memory_usage) * 16000 / 100,
                cpu_usage_percentage=30.0,
                cpu_count=8,
                network_bytes_sent=5000000,
                network_bytes_received=10000000,
                network_connections=15,
                disk_usage_percentage=40.0,
                disk_free_gb=500.0,
                process_memory_mb=200.0,
                process_cpu_percentage=5.0,
                thread_count=12
            ),
            state_metrics=StateManagementMetrics(
                checkpoints_created=5,
                last_checkpoint_time=datetime.now() - timedelta(minutes=20),
                checkpoint_creation_rate_per_hour=3.0,
                recovery_possible=True,
                last_recovery_time=None,
                recovery_success_rate=1.0,
                state_size_mb=10.0,
                checkpoint_size_mb=5.0,
                checkpoint_creation_time_ms=150.0,
                state_save_time_ms=75.0
            ),
            venue_progress={}
        )