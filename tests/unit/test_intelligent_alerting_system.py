"""
Unit tests for the Intelligent Alerting System implementation.
Tests all components: AlertingEngine, notification channels, alert rules, and integration.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from compute_forecast.monitoring.intelligent_alerting_system import (
    IntelligentAlertingSystem,
    create_intelligent_alerting_system,
)
from compute_forecast.monitoring.alerting_engine import (
    AlertingEngine,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
)
from compute_forecast.monitoring.notification_channels import (
    ConsoleNotificationChannel,
    DashboardNotificationChannel,
    create_notification_channel,
)
from compute_forecast.monitoring.alert_rules import AlertRuleFactory, CustomAlertRule
from compute_forecast.monitoring.metrics_collector import MetricsCollector
from compute_forecast.monitoring.dashboard_metrics import (
    APIMetrics,
    SystemResourceMetrics,
)


class TestAlertingEngine(unittest.TestCase):
    """Test the core AlertingEngine functionality"""

    def setUp(self):
        self.engine = AlertingEngine()

        # Create test notification channel
        self.test_channel = Mock()
        self.test_channel.name = "test_channel"
        self.test_channel.send_notification.return_value = True
        self.engine.add_notification_channel("test", self.test_channel)

    def test_alert_rule_management(self):
        """Test adding and removing alert rules"""

        # Create test rule
        def test_condition(metrics):
            return metrics.get("test_value", 0) > 10

        rule = AlertRule(
            id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            condition=test_condition,
            severity=AlertSeverity.MEDIUM,
            channels=["test"],
        )

        # Add rule
        self.engine.add_alert_rule(rule)
        self.assertIn("test_rule", self.engine.alert_rules)

        # Remove rule
        self.engine.remove_alert_rule("test_rule")
        self.assertNotIn("test_rule", self.engine.alert_rules)

    def test_alert_evaluation_and_sending(self):
        """Test alert evaluation and sending"""

        # Create test rule that triggers
        def always_trigger(metrics):
            return True

        rule = AlertRule(
            id="trigger_rule",
            name="Always Trigger",
            description="Always triggers",
            condition=always_trigger,
            severity=AlertSeverity.HIGH,
            channels=["test"],
        )

        self.engine.add_alert_rule(rule)

        # Evaluate alerts
        test_metrics = {"test_value": 15}
        triggered_alerts = self.engine.evaluate_alerts(test_metrics)

        # Should have triggered an alert
        self.assertEqual(len(triggered_alerts), 1)
        self.assertEqual(triggered_alerts[0].rule_id, "trigger_rule")
        self.assertEqual(triggered_alerts[0].severity, AlertSeverity.HIGH)

    def test_alert_acknowledgment_and_resolution(self):
        """Test alert acknowledgment and resolution"""

        # Create and trigger an alert
        def trigger_condition(metrics):
            return True

        rule = AlertRule(
            id="ack_test_rule",
            name="Acknowledgment Test",
            description="Test acknowledgment",
            condition=trigger_condition,
            severity=AlertSeverity.MEDIUM,
            channels=["test"],
        )

        self.engine.add_alert_rule(rule)
        alerts = self.engine.evaluate_alerts({"test": True})
        alert = alerts[0]

        # Acknowledge alert
        success = self.engine.acknowledge_alert(alert.id, "test_user")
        self.assertTrue(success)
        self.assertEqual(alert.status, AlertStatus.ACKNOWLEDGED)
        self.assertEqual(alert.acknowledged_by, "test_user")

        # Resolve alert
        success = self.engine.resolve_alert(alert.id)
        self.assertTrue(success)
        self.assertEqual(alert.status, AlertStatus.RESOLVED)
        self.assertNotIn(alert.id, self.engine.active_alerts)

    def test_rate_limiting(self):
        """Test alert rate limiting"""

        # Create rule with short rate limit
        def always_trigger(metrics):
            return True

        rule = AlertRule(
            id="rate_limit_rule",
            name="Rate Limited Rule",
            description="Rate limited rule",
            condition=always_trigger,
            severity=AlertSeverity.LOW,
            channels=["test"],
            rate_limit_minutes=1,
        )

        self.engine.add_alert_rule(rule)

        # First evaluation should trigger
        alerts1 = self.engine.evaluate_alerts({"test": True})
        self.assertEqual(len(alerts1), 1)

        # Second evaluation immediately should not trigger due to rate limiting
        alerts2 = self.engine.evaluate_alerts({"test": True})
        self.assertEqual(len(alerts2), 0)


class TestNotificationChannels(unittest.TestCase):
    """Test notification channel implementations"""

    def test_console_notification_channel(self):
        """Test console notification channel"""
        channel = ConsoleNotificationChannel("test_console")

        # Create test alert
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            timestamp=datetime.now(),
        )

        # Send notification (should not raise exception)
        result = channel.send_notification(alert)
        self.assertTrue(result)

        # Test connection should always be True for console
        self.assertTrue(channel.test_connection())

    def test_dashboard_notification_channel(self):
        """Test dashboard notification channel"""
        channel = DashboardNotificationChannel("test_dashboard")

        # Create test alert
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            severity=AlertSeverity.MEDIUM,
            title="Dashboard Test Alert",
            message="Testing dashboard notifications",
            timestamp=datetime.now(),
        )

        # Send notification
        result = channel.send_notification(alert)
        self.assertTrue(result)

        # Check alert was queued
        recent_alerts = channel.get_recent_alerts(10)
        self.assertEqual(len(recent_alerts), 1)
        self.assertEqual(recent_alerts[0].title, "Dashboard Test Alert")

    def test_channel_factory(self):
        """Test notification channel factory"""
        # Test console channel creation
        console_config = {
            "type": "console",
            "name": "test_console",
            "log_level": "INFO",
        }

        channel = create_notification_channel(console_config)
        self.assertIsInstance(channel, ConsoleNotificationChannel)
        self.assertEqual(channel.name, "test_console")

        # Test dashboard channel creation
        dashboard_config = {"type": "dashboard", "name": "test_dashboard"}

        channel = create_notification_channel(dashboard_config)
        self.assertIsInstance(channel, DashboardNotificationChannel)
        self.assertEqual(channel.name, "test_dashboard")


class TestAlertRules(unittest.TestCase):
    """Test alert rule implementations"""

    def test_default_rule_creation(self):
        """Test creation of default alert rules"""
        rules = AlertRuleFactory.create_default_rules()

        # Should have created multiple rules
        self.assertGreater(len(rules), 0)

        # Check that we have different types of rules
        rule_ids = [rule.id for rule in rules]

        # Should have API health rules
        api_rules = [r for r in rule_ids if "api" in r]
        self.assertGreater(len(api_rules), 0)

        # Should have system resource rules
        system_rules = [
            r for r in rule_ids if "memory" in r or "cpu" in r or "disk" in r
        ]
        self.assertGreater(len(system_rules), 0)

        # Should have collection progress rules
        collection_rules = [r for r in rule_ids if "collection" in r]
        self.assertGreater(len(collection_rules), 0)

    def test_custom_threshold_rule(self):
        """Test custom threshold rule creation"""
        rule = CustomAlertRule.create_metric_threshold_rule(
            rule_id="custom_memory_test",
            name="Custom Memory Test",
            description="Test custom memory rule",
            metric_path="system_metrics.memory_usage_percent",
            threshold=80.0,
            comparison="greater_than",
            severity=AlertSeverity.HIGH,
            channels=["test"],
        )

        # Test rule properties
        self.assertEqual(rule.id, "custom_memory_test")
        self.assertEqual(rule.severity, AlertSeverity.HIGH)
        self.assertEqual(rule.channels, ["test"])

        # Test condition function
        # Create mock metrics with high memory usage
        mock_metrics = {"system_metrics": Mock()}
        mock_metrics["system_metrics"].memory_usage_percent = 85.0

        result = rule.condition(mock_metrics)
        self.assertTrue(result)

        # Test with low memory usage
        mock_metrics["system_metrics"].memory_usage_percent = 70.0
        result = rule.condition(mock_metrics)
        self.assertFalse(result)

    def test_api_health_conditions(self):
        """Test API health alert conditions"""
        # Test API down condition
        {
            "api_metrics": {
                "semantic_scholar": Mock(health_status="unhealthy", success_rate=0.0)
            }
        }

        # This would require the actual condition function
        # For now, we'll test that the rule exists
        rules = AlertRuleFactory.create_api_health_rules()
        api_down_rule = next((r for r in rules if r.id == "api_down_critical"), None)
        self.assertIsNotNone(api_down_rule)

        # Test success rate condition
        {
            "api_metrics": {
                "semantic_scholar": Mock(success_rate=0.7, health_status="degraded")
            }
        }

        low_success_rule = next(
            (r for r in rules if r.id == "api_success_rate_low"), None
        )
        self.assertIsNotNone(low_success_rule)


class TestIntelligentAlertingSystem(unittest.TestCase):
    """Test the main IntelligentAlertingSystem class"""

    def setUp(self):
        # Create test configuration
        self.test_config = {
            "enable_default_rules": True,
            "enable_console_alerts": True,
            "enable_dashboard_alerts": True,
            "notification_channels": [
                {"type": "console", "name": "test_console", "log_level": "INFO"}
            ],
        }

        self.alerting_system = IntelligentAlertingSystem(self.test_config)

        # Create mock metrics collector
        self.mock_metrics_collector = Mock(spec=MetricsCollector)

    def test_initialization(self):
        """Test alerting system initialization"""
        # Initialize with metrics collector
        self.alerting_system.initialize(self.mock_metrics_collector)

        # Should be initialized
        self.assertTrue(self.alerting_system._initialized)
        self.assertIsNotNone(self.alerting_system.metrics_collector)

        # Should have default channels
        channels = list(
            self.alerting_system.alerting_engine.notification_channels.keys()
        )
        self.assertIn("console", channels)
        self.assertIn("dashboard", channels)

        # Should have default rules
        rules = list(self.alerting_system.alerting_engine.alert_rules.keys())
        self.assertGreater(len(rules), 0)

    def test_start_stop(self):
        """Test starting and stopping the alerting system"""
        self.alerting_system.initialize(self.mock_metrics_collector)

        # Start system
        self.alerting_system.start()
        self.assertTrue(self.alerting_system._running)

        # Stop system
        self.alerting_system.stop()
        self.assertFalse(self.alerting_system._running)

    def test_test_alert_sending(self):
        """Test sending test alerts"""
        self.alerting_system.initialize(self.mock_metrics_collector)

        # Send test alert
        results = self.alerting_system.send_test_alert("medium")

        # Should have results for available channels
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)

    def test_system_status(self):
        """Test system status reporting"""
        self.alerting_system.initialize(self.mock_metrics_collector)

        status = self.alerting_system.get_system_status()

        # Check status structure
        self.assertIn("initialized", status)
        self.assertIn("running", status)
        self.assertIn("alert_statistics", status)
        self.assertIn("notification_channels", status)
        self.assertIn("alert_rules", status)
        self.assertIn("channel_health", status)

        self.assertTrue(status["initialized"])

    def test_factory_function(self):
        """Test factory function for creating alerting system"""
        system = create_intelligent_alerting_system(self.test_config)

        self.assertIsInstance(system, IntelligentAlertingSystem)
        self.assertEqual(system.config, self.test_config)


class TestAlertEscalation(unittest.TestCase):
    """Test alert escalation functionality"""

    def setUp(self):
        self.engine = AlertingEngine()

        # Create mock channels
        self.primary_channel = Mock()
        self.primary_channel.name = "primary"
        self.primary_channel.send_notification.return_value = True

        self.escalation_channel = Mock()
        self.escalation_channel.name = "escalation"
        self.escalation_channel.send_notification.return_value = True

        self.engine.add_notification_channel("primary", self.primary_channel)
        self.engine.add_notification_channel("escalation", self.escalation_channel)

    def test_escalation_rule_creation(self):
        """Test creation of escalation rules"""
        from monitoring.alerting_engine import EscalationRule

        escalation_rule = EscalationRule(
            escalation_delay_minutes=5,
            additional_channels=["escalation"],
            max_escalations=2,
        )

        # Create alert rule with escalation
        def trigger_condition(metrics):
            return True

        rule = AlertRule(
            id="escalation_test",
            name="Escalation Test",
            description="Test escalation",
            condition=trigger_condition,
            severity=AlertSeverity.HIGH,
            channels=["primary"],
            escalation_rules=[escalation_rule],
        )

        self.engine.add_alert_rule(rule)

        # Trigger alert
        alerts = self.engine.evaluate_alerts({"test": True})
        alert = alerts[0]

        # Simulate time passing for escalation
        alert.timestamp = datetime.now() - timedelta(minutes=6)

        # Check if should escalate
        should_escalate = rule.should_escalate(alert)
        self.assertTrue(should_escalate)

        # Get escalation channels
        escalation_channels = rule.get_escalation_channels(alert)
        self.assertIn("escalation", escalation_channels)


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios with realistic metrics"""

    def setUp(self):
        self.alerting_system = IntelligentAlertingSystem(
            {"enable_default_rules": True, "enable_console_alerts": True}
        )

        # Create mock metrics collector with realistic data
        self.mock_metrics_collector = Mock(spec=MetricsCollector)
        self.alerting_system.initialize(self.mock_metrics_collector)

    def test_api_health_alert_scenario(self):
        """Test API health degradation alert scenario"""
        # Create metrics indicating API problems

        api_metrics = {
            "semantic_scholar": APIMetrics(
                api_name="semantic_scholar",
                success_rate=0.75,  # Below 80% threshold
                avg_response_time_ms=6000,  # High response time
                health_status="degraded",
                last_request_time=datetime.now(),
            )
        }

        metrics_dict = {"api_metrics": api_metrics, "timestamp": datetime.now()}

        # Evaluate alerts
        triggered_alerts = self.alerting_system.alerting_engine.evaluate_alerts(
            metrics_dict
        )

        # Should trigger API success rate alert
        success_rate_alerts = [
            a for a in triggered_alerts if "success_rate" in a.rule_id
        ]
        self.assertGreater(len(success_rate_alerts), 0)

    def test_system_resource_alert_scenario(self):
        """Test system resource alert scenario"""

        system_metrics = SystemResourceMetrics(
            memory_usage_mb=8192,
            memory_usage_percent=95.0,  # Critical memory usage
            cpu_usage_percent=88.0,  # High CPU usage
            disk_usage_mb=450000,
            disk_free_mb=512,  # Low disk space
            network_bytes_sent=1000000,
            network_bytes_received=2000000,
            active_threads=25,
            open_file_descriptors=150,
        )

        metrics_dict = {"system_metrics": system_metrics, "timestamp": datetime.now()}

        # Evaluate alerts
        triggered_alerts = self.alerting_system.alerting_engine.evaluate_alerts(
            metrics_dict
        )

        # Should trigger memory and CPU alerts
        memory_alerts = [a for a in triggered_alerts if "memory" in a.rule_id]
        cpu_alerts = [a for a in triggered_alerts if "cpu" in a.rule_id]

        self.assertGreater(len(memory_alerts) + len(cpu_alerts), 0)


if __name__ == "__main__":
    # Create test suite
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestAlertingEngine,
        TestNotificationChannels,
        TestAlertRules,
        TestIntelligentAlertingSystem,
        TestAlertEscalation,
        TestIntegrationScenarios,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'='*50}")
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*50}")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
