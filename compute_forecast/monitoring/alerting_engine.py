"""
Intelligent Alerting System - Core AlertingEngine implementation.
Provides multi-channel notification system with smart alert rules and escalation.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status tracking"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Individual alert instance"""

    id: str
    rule_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_component: str = ""
    escalation_count: int = 0
    last_escalation: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization"""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata,
            "source_component": self.source_component,
            "escalation_count": self.escalation_count,
            "last_escalation": self.last_escalation.isoformat()
            if self.last_escalation
            else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AlertRule:
    """Alert rule definition"""

    id: str
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    channels: List[str]
    rate_limit_minutes: int = 5
    escalation_rules: List["EscalationRule"] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_escalate(self, alert: Alert) -> bool:
        """Check if alert should be escalated"""
        for escalation_rule in self.escalation_rules:
            if escalation_rule.should_escalate(alert):
                return True
        return False

    def get_escalation_channels(self, alert: Alert) -> List[str]:
        """Get escalation channels for alert"""
        channels = set(self.channels)
        for escalation_rule in self.escalation_rules:
            if escalation_rule.should_escalate(alert):
                channels.update(escalation_rule.additional_channels)
        return list(channels)


@dataclass
class EscalationRule:
    """Alert escalation rule"""

    escalation_delay_minutes: int
    additional_channels: List[str]
    max_escalations: int = 3

    def should_escalate(self, alert: Alert) -> bool:
        """Check if alert should be escalated"""
        if alert.escalation_count >= self.max_escalations:
            return False

        if alert.last_escalation is None:
            # First escalation based on age
            age_minutes = (datetime.now() - alert.timestamp).total_seconds() / 60
            return age_minutes >= self.escalation_delay_minutes
        else:
            # Subsequent escalations based on last escalation
            time_since_last = (
                datetime.now() - alert.last_escalation
            ).total_seconds() / 60
            return time_since_last >= self.escalation_delay_minutes


class AlertingEngine:
    """
    Core intelligent alerting engine with multi-channel notifications,
    smart alert rules, rate limiting, and escalation management.
    """

    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_channels: Dict[str, "NotificationChannel"] = {}
        self.alert_history: List[Alert] = []
        self.rate_limiter = AlertRateLimiter()
        self.deduplicator = AlertDeduplicator()

        # Threading
        self._lock = threading.RLock()
        self._running = False
        self._evaluation_thread: Optional[threading.Thread] = None
        self._escalation_thread: Optional[threading.Thread] = None

        # Configuration
        self.evaluation_interval_seconds = 30
        self.escalation_check_interval_seconds = 60
        self.max_history_size = 10000

        logger.info("AlertingEngine initialized")

    def add_notification_channel(
        self, name: str, channel: "NotificationChannel"
    ) -> None:
        """Add notification channel"""
        with self._lock:
            self.notification_channels[name] = channel
            logger.info(f"Added notification channel: {name}")

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add alert rule"""
        with self._lock:
            self.alert_rules[rule.id] = rule
            logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_id: str) -> None:
        """Remove alert rule"""
        with self._lock:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"Removed alert rule: {rule_id}")

    def start_alerting(self) -> None:
        """Start alerting engine"""
        with self._lock:
            if self._running:
                return

            self._running = True

            # Start evaluation thread
            self._evaluation_thread = threading.Thread(
                target=self._evaluation_loop, daemon=True, name="AlertEvaluation"
            )
            self._evaluation_thread.start()

            # Start escalation thread
            self._escalation_thread = threading.Thread(
                target=self._escalation_loop, daemon=True, name="AlertEscalation"
            )
            self._escalation_thread.start()

            logger.info("AlertingEngine started")

    def stop_alerting(self) -> None:
        """Stop alerting engine"""
        with self._lock:
            self._running = False

        if self._evaluation_thread:
            self._evaluation_thread.join(timeout=5.0)
        if self._escalation_thread:
            self._escalation_thread.join(timeout=5.0)

        logger.info("AlertingEngine stopped")

    def evaluate_alerts(self, system_metrics: Dict[str, Any]) -> List[Alert]:
        """Evaluate all alert rules against current system metrics"""
        triggered_alerts = []

        with self._lock:
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue

                try:
                    if rule.condition(system_metrics):
                        alert = self._create_alert(rule, system_metrics)
                        if self._should_send_alert(alert):
                            triggered_alerts.append(alert)
                            self._add_active_alert(alert)

                except Exception as e:
                    logger.error(f"Error evaluating alert rule {rule.name}: {e}")

        return triggered_alerts

    def send_alert(
        self, alert: Alert, channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send alert to specified channels"""
        if channels is None:
            rule = self.alert_rules.get(alert.rule_id)
            channels = rule.channels if rule else []

        results = {}

        for channel_name in channels:
            channel = self.notification_channels.get(channel_name)
            if channel:
                try:
                    success = channel.send_notification(alert)
                    results[channel_name] = success
                    if success:
                        logger.info(f"Alert sent to {channel_name}: {alert.title}")
                    else:
                        logger.warning(
                            f"Failed to send alert to {channel_name}: {alert.title}"
                        )
                except Exception as e:
                    logger.error(f"Error sending alert to {channel_name}: {e}")
                    results[channel_name] = False
            else:
                logger.warning(f"Unknown notification channel: {channel_name}")
                results[channel_name] = False

        return results

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        with self._lock:
            alert = self.active_alerts.get(alert_id)
            if alert:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self._lock:
            alert = self.active_alerts.get(alert_id)
            if alert:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False

    def get_active_alerts(
        self, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        with self._lock:
            alerts = list(self.active_alerts.values())
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            return [a for a in self.alert_history if a.timestamp >= cutoff]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        with self._lock:
            active_by_severity = {}
            for severity in AlertSeverity:
                active_by_severity[severity.value] = len(
                    [a for a in self.active_alerts.values() if a.severity == severity]
                )

            return {
                "active_alerts_count": len(self.active_alerts),
                "active_by_severity": active_by_severity,
                "total_rules": len(self.alert_rules),
                "enabled_rules": len(
                    [r for r in self.alert_rules.values() if r.enabled]
                ),
                "notification_channels": len(self.notification_channels),
                "history_size": len(self.alert_history),
            }

    def _evaluation_loop(self) -> None:
        """Main alert evaluation loop"""
        while self._running:
            try:
                # This would be called with actual system metrics
                # For now, we'll skip evaluation in the background loop
                # Real evaluation happens when evaluate_alerts is called
                time.sleep(self.evaluation_interval_seconds)
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                time.sleep(5)

    def _escalation_loop(self) -> None:
        """Alert escalation check loop"""
        while self._running:
            try:
                self._check_escalations()
                time.sleep(self.escalation_check_interval_seconds)
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")
                time.sleep(10)

    def _check_escalations(self) -> None:
        """Check for alerts that need escalation"""
        with self._lock:
            for alert in list(self.active_alerts.values()):
                if alert.status == AlertStatus.ACTIVE:
                    rule = self.alert_rules.get(alert.rule_id)
                    if rule and rule.should_escalate(alert):
                        self._escalate_alert(alert, rule)

    def _escalate_alert(self, alert: Alert, rule: AlertRule) -> None:
        """Escalate an alert"""
        alert.escalation_count += 1
        alert.last_escalation = datetime.now()

        # Get escalation channels
        escalation_channels = rule.get_escalation_channels(alert)

        # Send escalated alert
        self.send_alert(alert, escalation_channels)

        logger.warning(
            f"Alert escalated: {alert.title} (escalation #{alert.escalation_count})"
        )

    def _create_alert(self, rule: AlertRule, system_metrics: Dict[str, Any]) -> Alert:
        """Create alert from rule and metrics"""
        alert_id = f"{rule.id}_{int(time.time())}"

        # Extract relevant metrics for message
        message = self._format_alert_message(rule, system_metrics)

        return Alert(
            id=alert_id,
            rule_id=rule.id,
            severity=rule.severity,
            title=rule.name,
            message=message,
            timestamp=datetime.now(),
            metadata=system_metrics.copy(),
            source_component=rule.metadata.get("source_component", "system"),
        )

    def _format_alert_message(
        self, rule: AlertRule, system_metrics: Dict[str, Any]
    ) -> str:
        """Format alert message with metrics data"""
        base_message = rule.description

        # Add relevant metrics to message
        if "api_metrics" in system_metrics:
            api_info = []
            for api_name, metrics in system_metrics["api_metrics"].items():
                if hasattr(metrics, "success_rate") and metrics.success_rate < 0.8:
                    api_info.append(
                        f"{api_name}: {metrics.success_rate:.1%} success rate"
                    )

            if api_info:
                base_message += f"\nAPI Issues: {', '.join(api_info)}"

        if "system_metrics" in system_metrics:
            sys_metrics = system_metrics["system_metrics"]
            if (
                hasattr(sys_metrics, "memory_usage_percent")
                and sys_metrics.memory_usage_percent > 80
            ):
                base_message += (
                    f"\nMemory usage: {sys_metrics.memory_usage_percent:.1f}%"
                )
            if (
                hasattr(sys_metrics, "cpu_usage_percent")
                and sys_metrics.cpu_usage_percent > 90
            ):
                base_message += f"\nCPU usage: {sys_metrics.cpu_usage_percent:.1f}%"

        return base_message

    def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent (rate limiting, deduplication)"""
        # Check rate limiting
        if not self.rate_limiter.should_send_alert(alert):
            return False

        # Check deduplication
        if self.deduplicator.is_duplicate(alert):
            return False

        return True

    def _add_active_alert(self, alert: Alert) -> None:
        """Add alert to active alerts"""
        self.active_alerts[alert.id] = alert

        # Maintain history size limit
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size // 2 :]


class AlertRateLimiter:
    """Rate limiting for alerts to prevent spam"""

    def __init__(self):
        self._send_history: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()

    def should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on rate limits"""
        rule = alert.rule_id

        with self._lock:
            now = datetime.now()

            # Get send history for this rule
            if rule not in self._send_history:
                self._send_history[rule] = []

            send_times = self._send_history[rule]

            # Get rate limit from alert metadata or use default
            rate_limit_minutes = 5  # Default
            if hasattr(alert, "metadata") and "rate_limit_minutes" in alert.metadata:
                rate_limit_minutes = alert.metadata["rate_limit_minutes"]

            # Remove old entries
            cutoff = now - timedelta(minutes=rate_limit_minutes)
            send_times[:] = [t for t in send_times if t > cutoff]

            # Check if we can send (no recent sends)
            if not send_times:
                send_times.append(now)
                return True

            return False


class AlertDeduplicator:
    """Alert deduplication to prevent duplicate alerts"""

    def __init__(self):
        self._recent_alerts: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate of recent alert"""
        # Create deduplication key based on rule and key metrics
        dedup_key = f"{alert.rule_id}_{alert.severity.value}"

        with self._lock:
            now = datetime.now()

            # Check if we've seen this alert recently (within 5 minutes)
            if dedup_key in self._recent_alerts:
                last_seen = self._recent_alerts[dedup_key]
                if (now - last_seen).total_seconds() < 300:  # 5 minutes
                    return True

            # Update recent alerts
            self._recent_alerts[dedup_key] = now

            # Clean up old entries
            cutoff = now - timedelta(minutes=10)
            self._recent_alerts = {
                k: v for k, v in self._recent_alerts.items() if v > cutoff
            }

            return False


# Abstract base class for notification channels
class NotificationChannel:
    """Base class for notification channels"""

    def __init__(self, name: str):
        self.name = name

    def send_notification(self, alert: Alert) -> bool:
        """Send notification for alert. Return True if successful."""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """Test if notification channel is working"""
        raise NotImplementedError
