"""
Alert data structures for Issue #12 Intelligent Alerting System.
Defines comprehensive alert hierarchy with built-in rules and smart suppression.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid


class AlertSeverity(Enum):
    """Alert severity levels with escalation priorities"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Defines conditions and actions for alert evaluation"""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression for evaluation
    severity: AlertSeverity
    enabled: bool = True

    # Evaluation parameters
    threshold_value: Optional[float] = None
    time_window_minutes: int = 5
    minimum_trigger_count: int = 1

    # Notification settings
    notification_channels: List[str] = field(default_factory=list)
    cooldown_minutes: int = 15
    escalation_delay_minutes: int = 60

    # Advanced settings
    auto_resolve: bool = False
    auto_resolve_condition: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.notification_channels:
            self.notification_channels = ["console", "dashboard"]


@dataclass
class EvaluationContext:
    """Context provided to alert rule evaluation"""
    metrics: Any  # SystemMetrics object
    current_time: datetime
    rule_history: Dict[str, List['Alert']]
    system_config: Dict[str, Any] = field(default_factory=dict)

    def get_metric_value(self, path: str) -> Any:
        """Get metric value using dot notation path"""
        try:
            obj = self.metrics
            for part in path.split('.'):
                obj = getattr(obj, part)
            return obj
        except (AttributeError, KeyError):
            return None


@dataclass
class Alert:
    """Individual alert instance"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    rule_name: str = ""

    # Alert content
    message: str = ""
    description: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    status: AlertStatus = AlertStatus.ACTIVE

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Context
    metric_values: Dict[str, Any] = field(default_factory=dict)
    system_context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    # Notification tracking
    notifications_sent: List[str] = field(default_factory=list)
    last_notification: Optional[datetime] = None
    notification_count: int = 0

    # Escalation
    escalation_level: int = 0
    escalated_at: Optional[datetime] = None

    def acknowledge(self, user: str = "system") -> None:
        """Mark alert as acknowledged"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.system_context["acknowledged_by"] = user

    def resolve(self, reason: str = "auto-resolved") -> None:
        """Mark alert as resolved"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.system_context["resolution_reason"] = reason

    def suppress(self, reason: str = "auto-suppressed") -> None:
        """Mark alert as suppressed"""
        self.status = AlertStatus.SUPPRESSED
        self.system_context["suppression_reason"] = reason


@dataclass
class SuppressionRule:
    """Rules for automatic alert suppression"""
    rule_id: str
    name: str
    description: str

    # Matching criteria
    alert_rule_pattern: str  # Regex pattern for rule names
    severity_threshold: AlertSeverity = AlertSeverity.WARNING

    # Suppression conditions
    max_alerts_per_window: int = 5
    time_window_minutes: int = 10
    burst_threshold: int = 3  # Alerts in rapid succession
    burst_window_seconds: int = 60

    # Suppression duration
    suppression_duration_minutes: int = 30
    escalation_override: bool = False  # Allow critical alerts to override

    # Advanced features
    pattern_matching: bool = True
    similar_context_only: bool = True
    auto_unsuppress: bool = True

    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class NotificationResult:
    """Result of a notification attempt"""
    channel: str
    success: bool
    timestamp: datetime
    latency_ms: float
    error_message: Optional[str] = None
    delivery_id: Optional[str] = None


@dataclass
class AlertConfiguration:
    """System-wide alert configuration"""
    enabled: bool = True

    # Global settings
    max_alerts_per_minute: int = 60
    max_alert_history_size: int = 10000
    alert_retention_days: int = 30

    # Evaluation settings
    evaluation_interval_seconds: int = 30
    evaluation_timeout_seconds: int = 5
    batch_evaluation: bool = True

    # Notification settings
    default_channels: List[str] = field(default_factory=lambda: ["console", "dashboard"])
    notification_timeout_seconds: int = 10
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5

    # Suppression settings
    enable_auto_suppression: bool = True
    global_suppression_enabled: bool = False
    maintenance_mode: bool = False

    # Emergency settings
    emergency_contact_enabled: bool = False
    emergency_contact_channels: List[str] = field(default_factory=list)
    emergency_severity_threshold: AlertSeverity = AlertSeverity.CRITICAL

    # Performance settings
    async_notifications: bool = True
    notification_queue_size: int = 1000


@dataclass
class AlertSummary:
    """Summary of alert activity for reporting"""
    time_period: str
    start_time: datetime
    end_time: datetime

    # Alert counts by severity
    total_alerts: int = 0
    info_alerts: int = 0
    warning_alerts: int = 0
    error_alerts: int = 0
    critical_alerts: int = 0

    # Alert status counts
    active_alerts: int = 0
    acknowledged_alerts: int = 0
    resolved_alerts: int = 0
    suppressed_alerts: int = 0

    # Performance metrics
    avg_resolution_time_minutes: float = 0.0
    avg_notification_latency_ms: float = 0.0
    notification_success_rate: float = 1.0

    # Top alerts
    most_frequent_rules: List[str] = field(default_factory=list)
    longest_duration_alerts: List[str] = field(default_factory=list)

    # System impact
    system_availability: float = 100.0
    affected_components: List[str] = field(default_factory=list)


# Built-in alert rules for common collection issues
BUILT_IN_ALERT_RULES = {
    "collection_rate_low": AlertRule(
        rule_id="collection_rate_low",
        name="Collection Rate Low",
        description="Paper collection rate has dropped below expected threshold",
        condition="metrics.collection_progress.papers_per_minute < threshold_value",
        severity=AlertSeverity.WARNING,
        threshold_value=10.0,
        time_window_minutes=5,
        notification_channels=["console", "dashboard"],
        cooldown_minutes=15,
        tags={"category": "performance", "component": "collection"}
    ),

    "api_health_degraded": AlertRule(
        rule_id="api_health_degraded",
        name="API Health Degraded",
        description="API health status has degraded or become critical",
        condition="any(api.health_status in ['degraded', 'critical', 'offline'] for api in metrics.api_metrics.values())",
        severity=AlertSeverity.ERROR,
        time_window_minutes=2,
        notification_channels=["console", "dashboard", "log"],
        cooldown_minutes=10,
        escalation_delay_minutes=30,
        tags={"category": "infrastructure", "component": "api"}
    ),

    "high_error_rate": AlertRule(
        rule_id="high_error_rate",
        name="High Error Rate",
        description="System error rate has exceeded acceptable threshold",
        condition="(metrics.processing_metrics.processing_errors / max(metrics.processing_metrics.papers_processed, 1)) > threshold_value",
        severity=AlertSeverity.CRITICAL,
        threshold_value=0.1,  # 10% error rate
        time_window_minutes=3,
        minimum_trigger_count=2,
        notification_channels=["console", "dashboard", "log"],
        cooldown_minutes=5,
        escalation_delay_minutes=15,
        tags={"category": "quality", "component": "processing"}
    ),

    "memory_usage_high": AlertRule(
        rule_id="memory_usage_high",
        name="High Memory Usage",
        description="System memory usage has exceeded safe operating threshold",
        condition="metrics.system_metrics.memory_usage_percent > threshold_value",
        severity=AlertSeverity.WARNING,
        threshold_value=80.0,
        time_window_minutes=5,
        notification_channels=["console", "dashboard"],
        cooldown_minutes=20,
        auto_resolve=True,
        auto_resolve_condition="metrics.system_metrics.memory_usage_percent < 70.0",
        tags={"category": "system", "component": "resources"}
    ),

    "venue_collection_stalled": AlertRule(
        rule_id="venue_collection_stalled",
        name="Venue Collection Stalled",
        description="A venue has been in progress for an unusually long time",
        condition="any(venue.status == 'in_progress' and venue.last_activity and (context.current_time - venue.last_activity).total_seconds() > threshold_value for venue in metrics.venue_progress.values())",
        severity=AlertSeverity.ERROR,
        threshold_value=1800,  # 30 minutes in seconds
        time_window_minutes=10,
        notification_channels=["console", "dashboard", "log"],
        cooldown_minutes=30,
        tags={"category": "performance", "component": "venues"}
    )
}


# Built-in suppression rules
BUILT_IN_SUPPRESSION_RULES = {
    "burst_suppression": SuppressionRule(
        rule_id="burst_suppression",
        name="Burst Alert Suppression",
        description="Suppress burst of similar alerts to prevent spam",
        alert_rule_pattern=".*",  # Match all rules
        max_alerts_per_window=5,
        time_window_minutes=10,
        burst_threshold=3,
        burst_window_seconds=60,
        suppression_duration_minutes=15,
        escalation_override=True,  # Critical alerts override suppression
        tags={"type": "burst", "auto": "true"}
    ),

    "maintenance_suppression": SuppressionRule(
        rule_id="maintenance_suppression",
        name="Maintenance Window Suppression",
        description="Suppress non-critical alerts during maintenance",
        alert_rule_pattern="^(?!.*critical).*",  # Exclude critical alerts
        severity_threshold=AlertSeverity.ERROR,
        max_alerts_per_window=1,
        time_window_minutes=1,
        suppression_duration_minutes=60,
        escalation_override=False,
        enabled=False,  # Manually enabled during maintenance
        tags={"type": "maintenance", "manual": "true"}
    )
}