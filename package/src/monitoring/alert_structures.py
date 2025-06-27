"""
Alert data structures for the Intelligent Alerting System.

Defines all alert-related data classes including rules, alerts, configurations,
and related structures for proactive collection monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal, Tuple, Union
from datetime import datetime, timedelta
from collections import deque


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    rule_name: str
    description: str
    condition: str                              # Python expression to evaluate
    severity: Literal["info", "warning", "error", "critical"]
    
    # Thresholds and timing
    threshold_value: Union[float, int, str]
    evaluation_window_minutes: int
    minimum_trigger_count: int                  # How many times condition must be true
    cooldown_period_minutes: int               # Minimum time between alerts
    
    # Notification settings
    notification_channels: List[str]
    suppress_duration_minutes: int              # Auto-suppression after triggering
    escalation_rules: List[str]                # Rules for escalation
    
    # Actions
    recommended_actions: List[str]
    auto_actions: List[str]                     # Automated responses
    
    # Metadata
    created_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    enabled: bool = True
    
    # Internal tracking
    _trigger_history: deque = field(default_factory=lambda: deque(maxlen=100))
    _last_evaluation: Optional[datetime] = None
    
    def can_trigger(self) -> bool:
        """Check if rule can trigger based on cooldown"""
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        time_since_last = datetime.now() - self.last_triggered
        return time_since_last >= timedelta(minutes=self.cooldown_period_minutes)
    
    def check_minimum_triggers(self) -> bool:
        """Check if minimum trigger count is met within evaluation window"""
        if self.minimum_trigger_count <= 1:
            return True
        
        cutoff_time = datetime.now() - timedelta(minutes=self.evaluation_window_minutes)
        recent_triggers = sum(1 for t in self._trigger_history if t > cutoff_time)
        
        return recent_triggers >= self.minimum_trigger_count
    
    def record_trigger_attempt(self, successful: bool = True):
        """Record a trigger attempt"""
        now = datetime.now()
        self._last_evaluation = now
        
        if successful:
            self._trigger_history.append(now)
            self.trigger_count += 1
            self.last_triggered = now


@dataclass
class Alert:
    """Generated alert instance"""
    alert_id: str
    rule_id: str
    timestamp: datetime
    severity: Literal["info", "warning", "error", "critical"]
    
    # Content
    title: str
    message: str
    affected_components: List[str]
    current_value: Union[float, int, str]
    threshold_value: Union[float, int, str]
    
    # Context
    metrics_context: Dict[str, Any]             # Relevant metrics at alert time
    recommended_actions: List[str]
    
    # Status
    status: Literal["active", "acknowledged", "resolved", "suppressed"]
    acknowledgment_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    acknowledgment_user: Optional[str] = None
    
    # Escalation
    escalation_level: int = 0
    escalated_at: Optional[datetime] = None
    
    def acknowledge(self, user: str = "system"):
        """Acknowledge the alert"""
        self.status = "acknowledged"
        self.acknowledgment_time = datetime.now()
        self.acknowledgment_user = user
    
    def resolve(self):
        """Mark alert as resolved"""
        self.status = "resolved"
        self.resolution_time = datetime.now()
    
    def suppress(self):
        """Suppress the alert"""
        self.status = "suppressed"
    
    def escalate(self):
        """Escalate the alert"""
        self.escalation_level += 1
        self.escalated_at = datetime.now()
    
    def get_age_minutes(self) -> float:
        """Get alert age in minutes"""
        return (datetime.now() - self.timestamp).total_seconds() / 60


@dataclass
class AlertConfiguration:
    """System-wide alert configuration"""
    # Default thresholds
    collection_rate_threshold: float = 10.0     # Papers per minute
    api_error_rate_threshold: float = 0.1       # 10% error rate
    memory_usage_threshold: float = 0.8         # 80% memory usage
    response_time_threshold: float = 5000.0     # 5 second response time
    venue_stall_threshold_minutes: int = 30     # 30 minutes no progress
    
    # Notification settings
    console_notifications: bool = True
    dashboard_notifications: bool = True
    
    # Alert behavior
    enable_auto_suppression: bool = True
    max_alerts_per_hour: int = 10
    critical_alert_retry_count: int = 3
    default_cooldown_minutes: int = 15
    
    # Escalation settings
    enable_escalation: bool = False
    escalation_delay_minutes: int = 60


@dataclass
class AlertDeliveryResult:
    """Result of alert delivery attempt"""
    alert_id: str
    success: bool
    delivery_channels: List[str]
    failed_channels: List[str]
    delivery_time: datetime
    retry_count: int = 0
    error_messages: List[str] = field(default_factory=list)


@dataclass
class AlertSummary:
    """Alert statistics and trends"""
    time_period_hours: int
    total_alerts: int
    alerts_by_severity: Dict[str, int]          # severity -> count
    alerts_by_rule: Dict[str, int]              # rule_id -> count
    most_triggered_rules: List[Tuple[str, int]] # (rule_name, count)
    
    # Trends
    alert_rate_trend: str                       # "increasing", "decreasing", "stable"
    avg_alerts_per_hour: float
    
    # Resolution
    resolved_alerts: int
    avg_resolution_time_minutes: float
    unresolved_alerts: int


@dataclass
class SuppressionRule:
    """Alert suppression rule"""
    pattern: str                                # Pattern to match alert titles/messages
    duration_minutes: int                       # How long to suppress
    reason: str                                 # Why this is being suppressed
    created_at: datetime
    expires_at: datetime
    created_by: str = "system"
    
    def is_active(self) -> bool:
        """Check if suppression rule is still active"""
        return datetime.now() < self.expires_at
    
    def matches_alert(self, alert: Alert) -> bool:
        """Check if this suppression rule matches an alert"""
        import re
        
        if not self.is_active():
            return False
        
        # Simple pattern matching - could be enhanced with regex
        pattern_lower = self.pattern.lower()
        title_lower = alert.title.lower()
        message_lower = alert.message.lower()
        
        return (pattern_lower in title_lower or 
                pattern_lower in message_lower or
                pattern_lower == alert.rule_id.lower())


@dataclass
class NotificationResult:
    """Result of notification delivery"""
    success: bool
    channel: str
    delivery_time: datetime = field(default_factory=datetime.now)
    error_messages: List[str] = field(default_factory=list)
    retry_count: int = 0


@dataclass
class EvaluationContext:
    """Context for alert rule evaluation"""
    metrics: Any                                # SystemMetrics instance
    threshold_value: Union[float, int, str]
    datetime: Any                               # datetime module
    timedelta: Any                              # timedelta class
    any: Any                                    # any function
    all: Any                                    # all function
    sum: Any                                    # sum function
    max: Any                                    # max function
    min: Any                                    # min function
    len: Any                                    # len function
    
    # Additional helper functions can be added here
    
    @classmethod
    def create_safe_context(cls, metrics, threshold_value):
        """Create a safe evaluation context with restricted builtins"""
        return cls(
            metrics=metrics,
            threshold_value=threshold_value,
            datetime=datetime,
            timedelta=timedelta,
            any=any,
            all=all,
            sum=sum,
            max=max,
            min=min,
            len=len
        )


# Built-in alert rules as constants
BUILT_IN_ALERT_RULES = {
    "collection_rate_low": AlertRule(
        rule_id="collection_rate_low",
        rule_name="Collection Rate Below Threshold",
        description="Alert when paper collection rate drops below expected threshold",
        condition="metrics.collection_progress.papers_per_minute < threshold_value",
        severity="warning",
        threshold_value=10.0,
        evaluation_window_minutes=10,
        minimum_trigger_count=3,
        cooldown_period_minutes=15,
        notification_channels=["console", "dashboard"],
        suppress_duration_minutes=30,
        escalation_rules=[],
        recommended_actions=[
            "Check API health and rate limits",
            "Verify network connectivity",
            "Review venue collection strategy",
            "Check for system resource constraints"
        ],
        auto_actions=[],
        created_at=datetime.now()
    ),
    
    "api_health_degraded": AlertRule(
        rule_id="api_health_degraded",
        rule_name="API Health Degraded",
        description="Alert when API health status becomes degraded or critical",
        condition="any(api.health_status in ['degraded', 'critical'] for api in metrics.api_metrics.values())",
        severity="error",
        threshold_value="degraded",
        evaluation_window_minutes=5,
        minimum_trigger_count=2,
        cooldown_period_minutes=10,
        notification_channels=["console", "dashboard"],
        suppress_duration_minutes=20,
        escalation_rules=[],
        recommended_actions=[
            "Check API service status",
            "Reduce request rate for affected APIs",
            "Switch to alternative APIs if available",
            "Monitor for API recovery"
        ],
        auto_actions=["increase_api_delays"],
        created_at=datetime.now()
    ),
    
    "high_error_rate": AlertRule(
        rule_id="high_error_rate",
        rule_name="High Error Rate",
        description="Alert when system error rate exceeds threshold",
        condition="sum(api.failed_requests for api in metrics.api_metrics.values()) / max(sum(api.requests_made for api in metrics.api_metrics.values()), 1) > threshold_value",
        severity="critical",
        threshold_value=0.1,
        evaluation_window_minutes=15,
        minimum_trigger_count=2,
        cooldown_period_minutes=20,
        notification_channels=["console", "dashboard"],
        suppress_duration_minutes=45,
        escalation_rules=[],
        recommended_actions=[
            "Review error logs for patterns",
            "Check network stability",
            "Verify API endpoints and authentication",
            "Consider pausing collection to investigate"
        ],
        auto_actions=[],
        created_at=datetime.now()
    ),
    
    "memory_usage_high": AlertRule(
        rule_id="memory_usage_high",
        rule_name="High Memory Usage",
        description="Alert when system memory usage exceeds threshold",
        condition="metrics.system_metrics.memory_usage_percentage > threshold_value",
        severity="warning",
        threshold_value=80.0,
        evaluation_window_minutes=5,
        minimum_trigger_count=3,
        cooldown_period_minutes=10,
        notification_channels=["console", "dashboard"],
        suppress_duration_minutes=30,
        escalation_rules=[],
        recommended_actions=[
            "Check for memory leaks in processing",
            "Reduce batch sizes",
            "Clear unnecessary caches",
            "Consider restarting collection with smaller batches"
        ],
        auto_actions=["reduce_batch_sizes"],
        created_at=datetime.now()
    ),
    
    "venue_collection_stalled": AlertRule(
        rule_id="venue_collection_stalled",
        rule_name="Venue Collection Stalled",
        description="Alert when a venue shows no collection progress for extended period",
        condition="any(venue_progress.last_update_time < datetime.now() - timedelta(minutes=threshold_value) for venue_progress in metrics.venue_progress.values())",
        severity="error",
        threshold_value=30,
        evaluation_window_minutes=30,
        minimum_trigger_count=1,
        cooldown_period_minutes=45,
        notification_channels=["console", "dashboard"],
        suppress_duration_minutes=60,
        escalation_rules=[],
        recommended_actions=[
            "Check venue-specific API issues",
            "Verify venue name normalization",
            "Review venue collection logs",
            "Consider restarting venue collection"
        ],
        auto_actions=["restart_stalled_venue"],
        created_at=datetime.now()
    )
}