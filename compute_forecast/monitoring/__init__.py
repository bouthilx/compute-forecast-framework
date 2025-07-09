"""
Monitoring module for real-time collection dashboard and intelligent alerting.

Provides system metrics collection, dashboard visualization, and proactive alerting
for 4-6 hour paper collection sessions.
"""

from .server.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    MetricsSummary,
    DashboardStatus,
    VenueProgressMetrics,
    MetricsBuffer,
)

from .metrics.metrics_collector import MetricsCollector
from .server.dashboard_server import CollectionDashboard

# Intelligent Alerting System components
from .alerting.alert_structures import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    SuppressionRule,
    AlertConfiguration,
    AlertSummary,
    NotificationResult,
    EvaluationContext,
    BUILT_IN_ALERT_RULES,
    BUILT_IN_SUPPRESSION_RULES,
)

from .alerting.alert_system import IntelligentAlertSystem, AlertRuleEvaluator

from .alerting.alert_suppression import AlertSuppressionManager, SuppressionRuleManager

from .alerting.notification_channels import (
    NotificationChannel,
    ConsoleNotificationChannel,
    DashboardNotificationChannel,
    LogNotificationChannel,
    NotificationChannelManager,
)

# Advanced Analytics Dashboard components
from .server.advanced_analytics_engine import (
    AdvancedAnalyticsEngine,
    AnalyticsTimeWindow,
    TrendAnalysis,
    PerformanceAnalytics,
    PredictiveAnalytics,
    AnalyticsSummary,
)

from .server.advanced_dashboard_server import (
    AdvancedAnalyticsDashboard,
    create_advanced_analytics_dashboard,
    AnalyticsDashboardAdapter,
    EXAMPLE_ANALYTICS_CONFIG,
)

__all__ = [
    # Core monitoring
    "SystemMetrics",
    "CollectionProgressMetrics",
    "APIMetrics",
    "ProcessingMetrics",
    "SystemResourceMetrics",
    "StateManagementMetrics",
    "MetricsSummary",
    "DashboardStatus",
    "VenueProgressMetrics",
    "MetricsBuffer",
    "MetricsCollector",
    "CollectionDashboard",
    # Intelligent Alerting System
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertStatus",
    "AlertDeliveryResult",
    "SuppressionRule",
    "AlertConfiguration",
    "AlertSummary",
    "NotificationResult",
    "EvaluationContext",
    "BUILT_IN_ALERT_RULES",
    "BUILT_IN_SUPPRESSION_RULES",
    # Alert System
    "IntelligentAlertSystem",
    "AlertRuleEvaluator",
    # Alert Suppression
    "AlertSuppressionManager",
    "SuppressionRuleManager",
    # Notification Channels
    "NotificationChannel",
    "ConsoleNotificationChannel",
    "DashboardNotificationChannel",
    "LogNotificationChannel",
    "NotificationChannelManager",
    # Advanced Analytics Dashboard
    "AdvancedAnalyticsEngine",
    "AnalyticsTimeWindow",
    "TrendAnalysis",
    "PerformanceAnalytics",
    "PredictiveAnalytics",
    "AnalyticsSummary",
    "AdvancedAnalyticsDashboard",
    "create_advanced_analytics_dashboard",
    "AnalyticsDashboardAdapter",
    "EXAMPLE_ANALYTICS_CONFIG",
]
