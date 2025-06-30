"""
Monitoring module for real-time collection dashboard and intelligent alerting.

Provides system metrics collection, dashboard visualization, and proactive alerting
for 4-6 hour paper collection sessions.
"""

from .dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    MetricsSummary,
    DashboardStatus,
    VenueProgressMetrics,
    MetricsBuffer
)

from .metrics_collector import MetricsCollector
from .dashboard_server import CollectionDashboard

# Intelligent Alerting System components
from .alert_structures import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    AlertDeliveryResult,
    SuppressionRule,
    AlertConfiguration,
    AlertSummary,
    NotificationResult,
    EvaluationContext,
    BUILT_IN_ALERT_RULES,
    BUILT_IN_SUPPRESSION_RULES
)

from .alert_system import (
    IntelligentAlertSystem,
    AlertRuleEvaluator
)

from .alert_suppression import (
    AlertSuppressionManager,
    SuppressionRuleManager
)

from .notification_channels import (
    NotificationChannel,
    ConsoleNotificationChannel,
    DashboardNotificationChannel,
    LogNotificationChannel,
    NotificationChannelManager
)

__all__ = [
    # Core monitoring
    'SystemMetrics',
    'CollectionProgressMetrics', 
    'APIMetrics',
    'ProcessingMetrics',
    'SystemResourceMetrics',
    'StateManagementMetrics',
    'MetricsSummary',
    'DashboardStatus',
    'VenueProgressMetrics',
    'MetricsBuffer',
    'MetricsCollector',
    'CollectionDashboard',
    
    # Intelligent Alerting System
    'Alert',
    'AlertRule',
    'AlertSeverity',
    'AlertStatus',
    'AlertDeliveryResult',
    'SuppressionRule',
    'AlertConfiguration',
    'AlertSummary',
    'NotificationResult',
    'EvaluationContext',
    'BUILT_IN_ALERT_RULES',
    'BUILT_IN_SUPPRESSION_RULES',
    
    # Alert System
    'IntelligentAlertSystem',
    'AlertRuleEvaluator',
    
    # Alert Suppression
    'AlertSuppressionManager',
    'SuppressionRuleManager',
    
    # Notification Channels
    'NotificationChannel',
    'ConsoleNotificationChannel',
    'DashboardNotificationChannel',
    'LogNotificationChannel',
    'NotificationChannelManager'
]