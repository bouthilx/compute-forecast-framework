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

__all__ = [
    'SystemMetrics',
    'CollectionProgressMetrics', 
    'APIMetrics',
    'ProcessingMetrics',
    'SystemResourceMetrics',
    'StateManagementMetrics',
    'MetricsSummary',
    'DashboardStatus',
    'MetricsCollector',
    'CollectionDashboard'
]