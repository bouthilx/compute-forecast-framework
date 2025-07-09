"""
Intelligent Alerting System - Main integration class.
Provides complete alerting solution with smart rules, multi-channel notifications,
and integration with the paper collection monitoring system.
"""

import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

from .alerting_engine import (
    AlertingEngine,
    AlertRule,
    Alert,
    NotificationChannel as AlertingEngineNotificationChannel,
)
from .notification_channels import (
    create_notification_channel,
    DashboardNotificationChannel,
    ConsoleNotificationChannel,
)
from .alert_rules import AlertRuleFactory, CustomAlertRule
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class IntelligentAlertingSystem:
    """
    Complete intelligent alerting system for paper collection monitoring.
    Integrates alerting engine, notification channels, and smart rules.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize intelligent alerting system

        Args:
            config: Configuration dictionary with alerting settings
        """
        self.config = config or {}

        # Initialize core components
        self.alerting_engine = AlertingEngine()
        self.metrics_collector: Optional[MetricsCollector] = None

        # State tracking
        self._initialized = False
        self._running = False
        self._lock = threading.RLock()

        # Configuration
        self.enable_default_rules = self.config.get("enable_default_rules", True)
        self.enable_console_alerts = self.config.get("enable_console_alerts", True)
        self.enable_dashboard_alerts = self.config.get("enable_dashboard_alerts", True)

        logger.info("IntelligentAlertingSystem initialized")

    def initialize(self, metrics_collector: MetricsCollector) -> None:
        """
        Initialize the alerting system with metrics collector

        Args:
            metrics_collector: MetricsCollector instance for system monitoring
        """
        with self._lock:
            if self._initialized:
                logger.warning("Alerting system already initialized")
                return

            self.metrics_collector = metrics_collector

            # Setup default notification channels
            self._setup_default_channels()

            # Setup default alert rules
            if self.enable_default_rules:
                self._setup_default_rules()

            # Setup custom rules from config
            self._setup_custom_rules()

            self._initialized = True
            logger.info("IntelligentAlertingSystem initialized successfully")

    def start(self) -> None:
        """Start the alerting system"""
        with self._lock:
            if not self._initialized:
                raise RuntimeError(
                    "Alerting system not initialized. Call initialize() first."
                )

            if self._running:
                logger.warning("Alerting system already running")
                return

            # Start alerting engine
            self.alerting_engine.start_alerting()

            # Start metrics-based alert evaluation
            self._start_metrics_evaluation()

            self._running = True
            logger.info("IntelligentAlertingSystem started")

    def stop(self) -> None:
        """Stop the alerting system"""
        with self._lock:
            if not self._running:
                return

            self._running = False

            # Stop alerting engine
            self.alerting_engine.stop_alerting()

            logger.info("IntelligentAlertingSystem stopped")

    def add_notification_channel(self, channel_config: Dict[str, Any]) -> bool:
        """
        Add notification channel from configuration

        Args:
            channel_config: Channel configuration dictionary

        Returns:
            True if channel added successfully
        """
        try:
            channel = create_notification_channel(channel_config)
            # Cast to the expected type
            casted_channel = AlertingEngineNotificationChannel(
                channel.get_channel_name()
            )
            self.alerting_engine.add_notification_channel(
                channel.get_channel_name(), casted_channel
            )
            logger.info(f"Added notification channel: {channel.get_channel_name()}")
            return True
        except Exception as e:
            logger.error(f"Failed to add notification channel: {e}")
            return False

    def add_custom_alert_rule(self, rule_config: Dict[str, Any]) -> bool:
        """
        Add custom alert rule from configuration

        Args:
            rule_config: Rule configuration dictionary

        Returns:
            True if rule added successfully
        """
        try:
            rule = self._create_rule_from_config(rule_config)
            self.alerting_engine.add_alert_rule(rule)
            logger.info(f"Added custom alert rule: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add custom alert rule: {e}")
            return False

    def send_test_alert(
        self, severity: str = "low", channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send test alert to verify notification channels

        Args:
            severity: Test alert severity
            channels: Specific channels to test (None for all)

        Returns:
            Dictionary of channel results
        """
        try:
            from .alerting_engine import AlertSeverity

            # Create test alert
            test_alert = Alert(
                id=f"test_alert_{int(datetime.now().timestamp())}",
                rule_id="test_rule",
                severity=AlertSeverity(severity),
                title="Test Alert - Paper Collection System",
                message="This is a test alert to verify notification channels are working properly.",
                timestamp=datetime.now(),
                source_component="alerting_system",
            )

            # Send test alert
            if channels is None:
                channels = list(self.alerting_engine.notification_channels.keys())

            results = self.alerting_engine.send_alert(test_alert, channels)

            logger.info(f"Test alert sent. Results: {results}")
            return results

        except Exception as e:
            logger.error(f"Failed to send test alert: {e}")
            return {}

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive alerting system status"""
        with self._lock:
            status = {
                "initialized": self._initialized,
                "running": self._running,
                "alert_statistics": self.alerting_engine.get_alert_statistics(),
                "notification_channels": list(
                    self.alerting_engine.notification_channels.keys()
                ),
                "alert_rules": {
                    rule_id: {
                        "name": rule.name,
                        "enabled": rule.enabled,
                        "severity": rule.severity.value,
                        "channels": rule.channels,
                    }
                    for rule_id, rule in self.alerting_engine.alert_rules.items()
                },
            }

            # Add channel health status
            channel_health = {}
            for name, channel in self.alerting_engine.notification_channels.items():
                try:
                    channel_health[name] = channel.test_connection()
                except Exception as e:
                    logger.debug(f"Error testing channel {name}: {e}")
                    channel_health[name] = False

            status["channel_health"] = channel_health

            return status

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        alerts = self.alerting_engine.get_active_alerts()
        return [alert.to_dict() for alert in alerts]

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history"""
        history = self.alerting_engine.get_alert_history(hours)
        return [alert.to_dict() for alert in history]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert"""
        return self.alerting_engine.acknowledge_alert(alert_id, acknowledged_by)

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        return self.alerting_engine.resolve_alert(alert_id)

    def _setup_default_channels(self) -> None:
        """Setup default notification channels"""
        # Always add console channel for development
        if self.enable_console_alerts:
            console_channel = ConsoleNotificationChannel(verbose=True)
            console_casted = AlertingEngineNotificationChannel("console")
            self.alerting_engine.add_notification_channel("console", console_casted)

        # Add dashboard channel if enabled
        if self.enable_dashboard_alerts:
            dashboard_channel = DashboardNotificationChannel()
            dashboard_casted = AlertingEngineNotificationChannel("dashboard")
            self.alerting_engine.add_notification_channel("dashboard", dashboard_casted)

        # Add channels from config
        channels_config = self.config.get("notification_channels", [])
        for channel_config in channels_config:
            try:
                channel = create_notification_channel(channel_config)
                channel_casted = AlertingEngineNotificationChannel(
                    channel.get_channel_name()
                )
                self.alerting_engine.add_notification_channel(
                    channel.get_channel_name(), channel_casted
                )
            except Exception as e:
                logger.error(f"Failed to setup channel from config: {e}")

    def _setup_default_rules(self) -> None:
        """Setup default alert rules"""
        try:
            default_rules = AlertRuleFactory.create_default_rules()

            for rule in default_rules:
                # Filter channels to only include available ones
                available_channels = list(
                    self.alerting_engine.notification_channels.keys()
                )
                rule.channels = [ch for ch in rule.channels if ch in available_channels]

                # Add console as fallback if no channels available
                if not rule.channels and "console" in available_channels:
                    rule.channels = ["console"]

                self.alerting_engine.add_alert_rule(rule)

            logger.info(f"Added {len(default_rules)} default alert rules")

        except Exception as e:
            logger.error(f"Failed to setup default alert rules: {e}")

    def _setup_custom_rules(self) -> None:
        """Setup custom alert rules from configuration"""
        custom_rules = self.config.get("custom_alert_rules", [])

        for rule_config in custom_rules:
            try:
                rule = self._create_rule_from_config(rule_config)
                self.alerting_engine.add_alert_rule(rule)
            except Exception as e:
                logger.error(f"Failed to setup custom rule: {e}")

    def _create_rule_from_config(self, rule_config: Dict[str, Any]) -> AlertRule:
        """Create alert rule from configuration dictionary"""
        rule_type = rule_config.get("type", "threshold")

        if rule_type == "threshold":
            return CustomAlertRule.create_metric_threshold_rule(
                rule_id=rule_config["id"],
                name=rule_config["name"],
                description=rule_config.get("description", ""),
                metric_path=rule_config["metric_path"],
                threshold=rule_config["threshold"],
                comparison=rule_config.get("comparison", "greater_than"),
                severity=rule_config.get("severity", "medium"),
                channels=rule_config.get("channels", ["dashboard"]),
            )
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")

    def _start_metrics_evaluation(self) -> None:
        """Start metrics-based alert evaluation"""
        if not self.metrics_collector:
            logger.warning("No metrics collector available for alert evaluation")
            return

        # Create evaluation thread
        def evaluation_loop():
            """Continuous evaluation of alerts based on metrics"""
            while self._running:
                try:
                    # Get current metrics
                    current_metrics = self.metrics_collector.get_latest_metrics()

                    if current_metrics:
                        # Convert metrics to dictionary for rule evaluation
                        metrics_dict = {
                            "timestamp": current_metrics.timestamp,
                            "collection_progress": current_metrics.collection_progress,
                            "api_metrics": current_metrics.api_metrics,
                            "processing_metrics": current_metrics.processing_metrics,
                            "system_metrics": current_metrics.system_metrics,
                            "state_metrics": current_metrics.state_metrics,
                            "venue_progress": current_metrics.venue_progress,
                        }

                        # Evaluate alert rules
                        triggered_alerts = self.alerting_engine.evaluate_alerts(
                            metrics_dict
                        )

                        # Send triggered alerts
                        for alert in triggered_alerts:
                            self.alerting_engine.send_alert(alert)

                    # Sleep for evaluation interval
                    import time

                    time.sleep(30)  # Evaluate every 30 seconds

                except Exception as e:
                    logger.error(f"Error in alert evaluation loop: {e}")
                    import time

                    time.sleep(10)  # Short delay on error

        # Start evaluation thread
        evaluation_thread = threading.Thread(
            target=evaluation_loop, daemon=True, name="AlertEvaluation"
        )
        evaluation_thread.start()

        logger.info("Started metrics-based alert evaluation")


# Factory function for easy instantiation
def create_intelligent_alerting_system(
    config: Optional[Dict[str, Any]] = None,
) -> IntelligentAlertingSystem:
    """
    Create and configure intelligent alerting system

    Args:
        config: Configuration dictionary

    Returns:
        Configured IntelligentAlertingSystem instance
    """
    return IntelligentAlertingSystem(config)


# Example configuration for reference
EXAMPLE_CONFIG = {
    "enable_default_rules": True,
    "enable_console_alerts": True,
    "enable_dashboard_alerts": True,
    "notification_channels": [
        {
            "type": "email",
            "name": "email_alerts",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "alerts@yourcompany.com",
            "password": "your_app_password",
            "from_email": "alerts@yourcompany.com",
            "recipients": ["admin@yourcompany.com"],
            "use_tls": True,
        },
        {
            "type": "slack",
            "name": "slack_alerts",
            "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
            "channel": "#paper-collection-alerts",
        },
        {
            "type": "webhook",
            "name": "webhook_alerts",
            "webhook_url": "https://your-monitoring-system.com/alerts",
            "headers": {
                "Authorization": "Bearer your_token_here",
                "Content-Type": "application/json",
            },
        },
    ],
    "custom_alert_rules": [
        {
            "type": "threshold",
            "id": "custom_memory_warning",
            "name": "Custom Memory Warning",
            "description": "Custom memory usage warning at 75%",
            "metric_path": "system_metrics.memory_usage_percent",
            "threshold": 75.0,
            "comparison": "greater_than",
            "severity": "medium",
            "channels": ["dashboard", "slack"],
        }
    ],
}
