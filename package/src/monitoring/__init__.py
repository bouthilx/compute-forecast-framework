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
    DashboardStatus
)

from .metrics_collector import MetricsCollector
from .dashboard_server import CollectionDashboard

from .alert_structures import (
    AlertRule,
    Alert,
    AlertConfiguration,
    AlertDeliveryResult,
    AlertSummary,
    SuppressionRule,
    NotificationResult
)

from .alert_system import IntelligentAlertSystem
from .alert_suppression import AlertSuppressionManager
from .notification_channels import (
    NotificationChannel,
    ConsoleNotificationChannel,
    DashboardNotificationChannel,
    LogNotificationChannel,
    NotificationChannelManager
)

__all__ = [
    # Dashboard components
    'SystemMetrics',
    'CollectionProgressMetrics', 
    'APIMetrics',
    'ProcessingMetrics',
    'SystemResourceMetrics',
    'StateManagementMetrics',
    'MetricsSummary',
    'DashboardStatus',
    'MetricsCollector',
    'CollectionDashboard',
    
    # Alerting components
    'AlertRule',
    'Alert',
    'AlertConfiguration',
    'AlertDeliveryResult',
    'AlertSummary',
    'SuppressionRule',
    'NotificationResult',
    'IntelligentAlertSystem',
    'AlertSuppressionManager',
    'NotificationChannel',
    'ConsoleNotificationChannel',
    'DashboardNotificationChannel',
    'LogNotificationChannel',
    'NotificationChannelManager'
]