"""
Multi-channel notification system for Issue #12 Intelligent Alerting System.
Provides console, dashboard, log, email, and webhook notification channels.
"""

import time
import threading
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from pathlib import Path

from .alert_structures import Alert, AlertSeverity, NotificationResult

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    @abstractmethod
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send notification for alert"""
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """Get channel identifier"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if channel is available for notifications"""
        pass


class ConsoleNotificationChannel(NotificationChannel):
    """Console output notification channel with color coding"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.color_codes = {
            AlertSeverity.INFO: '\033[94m',      # Blue
            AlertSeverity.WARNING: '\033[93m',   # Yellow
            AlertSeverity.ERROR: '\033[91m',     # Red
            AlertSeverity.CRITICAL: '\033[95m'   # Magenta
        }
        self.reset_code = '\033[0m'
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert to console with color coding"""
        start_time = time.time()
        
        try:
            # Format alert message
            color = self.color_codes.get(alert.severity, '')
            severity_icon = self._get_severity_icon(alert.severity)
            
            message = f"{color}🚨 {severity_icon} [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}{self.reset_code}"
            
            if self.verbose:
                message += f"\n   Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                message += f"\n   Alert ID: {alert.alert_id}"
                if alert.metric_values:
                    message += f"\n   Metrics: {json.dumps(alert.metric_values, indent=4)}"
            
            print(message)
            
            latency = (time.time() - start_time) * 1000
            
            return NotificationResult(
                channel="console",
                success=True,
                timestamp=datetime.now(),
                latency_ms=latency
            )
            
        except Exception as e:
            logger.error(f"Error sending console notification: {e}")
            return NotificationResult(
                channel="console",
                success=False,
                timestamp=datetime.now(),
                latency_ms=0.0,
                error_message=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "console"
    
    def is_available(self) -> bool:
        return True
    
    def _get_severity_icon(self, severity: AlertSeverity) -> str:
        """Get emoji icon for severity level"""
        icons = {
            AlertSeverity.INFO: 'ℹ️',
            AlertSeverity.WARNING: '⚠️',
            AlertSeverity.ERROR: '❌',
            AlertSeverity.CRITICAL: '💥'
        }
        return icons.get(severity, '📢')


class DashboardNotificationChannel(NotificationChannel):
    """WebSocket dashboard notification channel"""
    
    def __init__(self, dashboard_server=None):
        self.dashboard_server = dashboard_server
        self._notifications_sent = 0
        self._lock = threading.RLock()
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert to dashboard via WebSocket"""
        start_time = time.time()
        
        try:
            if not self.dashboard_server:
                return NotificationResult(
                    channel="dashboard",
                    success=False,
                    timestamp=datetime.now(),
                    latency_ms=0.0,
                    error_message="Dashboard server not configured"
                )
            
            # Format alert for dashboard
            alert_data = {
                'alert_id': alert.alert_id,
                'rule_name': alert.rule_name,
                'message': alert.message,
                'severity': alert.severity.value,
                'timestamp': alert.timestamp.isoformat(),
                'metric_values': alert.metric_values,
                'tags': alert.tags
            }
            
            # Send via WebSocket if dashboard has socketio
            if hasattr(self.dashboard_server, 'socketio'):
                self.dashboard_server.socketio.emit('alert_notification', alert_data, broadcast=True)
            
            with self._lock:
                self._notifications_sent += 1
            
            latency = (time.time() - start_time) * 1000
            
            return NotificationResult(
                channel="dashboard",
                success=True,
                timestamp=datetime.now(),
                latency_ms=latency,
                delivery_id=f"dashboard_{self._notifications_sent}"
            )
            
        except Exception as e:
            logger.error(f"Error sending dashboard notification: {e}")
            return NotificationResult(
                channel="dashboard",
                success=False,
                timestamp=datetime.now(),
                latency_ms=0.0,
                error_message=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "dashboard"
    
    def is_available(self) -> bool:
        return self.dashboard_server is not None


class LogNotificationChannel(NotificationChannel):
    """File-based log notification channel with structured JSON logging"""
    
    def __init__(self, log_file_path: str = "alerts.log", structured_format: bool = True):
        self.log_file_path = Path(log_file_path)
        self.structured_format = structured_format
        self._ensure_log_directory()
        
        # Setup dedicated logger for alerts
        self.alert_logger = logging.getLogger(f"alerts.{self.get_channel_name()}")
        self.alert_logger.setLevel(logging.INFO)
        
        # Create file handler if not exists
        if not self.alert_logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            if structured_format:
                formatter = logging.Formatter('%(message)s')  # JSON will be the message
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )
            handler.setFormatter(formatter)
            self.alert_logger.addHandler(handler)
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Log alert to file with structured format"""
        start_time = time.time()
        
        try:
            if self.structured_format:
                # Structured JSON logging
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'alert_id': alert.alert_id,
                    'rule_id': alert.rule_id,
                    'rule_name': alert.rule_name,
                    'severity': alert.severity.value,
                    'status': alert.status.value,
                    'message': alert.message,
                    'description': alert.description,
                    'alert_timestamp': alert.timestamp.isoformat(),
                    'metric_values': alert.metric_values,
                    'system_context': alert.system_context,
                    'tags': alert.tags,
                    'notification_count': alert.notification_count
                }
                
                self.alert_logger.info(json.dumps(log_entry, indent=None))
            else:
                # Human-readable logging
                message = (
                    f"[{alert.severity.value.upper()}] {alert.rule_name}: {alert.message} "
                    f"(ID: {alert.alert_id}, Time: {alert.timestamp.isoformat()})"
                )
                self.alert_logger.info(message)
            
            latency = (time.time() - start_time) * 1000
            
            return NotificationResult(
                channel="log",
                success=True,
                timestamp=datetime.now(),
                latency_ms=latency,
                delivery_id=f"log_{alert.alert_id}"
            )
            
        except Exception as e:
            logger.error(f"Error sending log notification: {e}")
            return NotificationResult(
                channel="log",
                success=False,
                timestamp=datetime.now(),
                latency_ms=0.0,
                error_message=str(e)
            )
    
    def get_channel_name(self) -> str:
        return "log"
    
    def is_available(self) -> bool:
        return self.log_file_path.parent.exists()
    
    def _ensure_log_directory(self) -> None:
        """Ensure log directory exists"""
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)


class NotificationChannelManager:
    """
    Manages multiple notification channels with routing and delivery tracking.
    
    Features:
    - Multi-channel routing
    - Channel availability checking
    - Delivery confirmation tracking
    - Performance monitoring
    """
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.delivery_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        # Default channels
        self._setup_default_channels()
        
        logger.info("NotificationChannelManager initialized")
    
    def add_channel(self, channel: NotificationChannel) -> None:
        """Add notification channel"""
        with self._lock:
            channel_name = channel.get_channel_name()
            self.channels[channel_name] = channel
            
            if channel_name not in self.delivery_stats:
                self.delivery_stats[channel_name] = {
                    'total_attempts': 0,
                    'successful_deliveries': 0,
                    'failed_deliveries': 0,
                    'avg_latency_ms': 0.0,
                    'last_delivery': None
                }
            
            logger.info(f"Added notification channel: {channel_name}")
    
    def send_notification(self, alert: Alert, channel_name: str) -> NotificationResult:
        """Send notification via specific channel"""
        with self._lock:
            if channel_name not in self.channels:
                return NotificationResult(
                    channel=channel_name,
                    success=False,
                    timestamp=datetime.now(),
                    latency_ms=0.0,
                    error_message=f"Channel '{channel_name}' not found"
                )
            
            channel = self.channels[channel_name]
            
            # Check channel availability
            if not channel.is_available():
                return NotificationResult(
                    channel=channel_name,
                    success=False,
                    timestamp=datetime.now(),
                    latency_ms=0.0,
                    error_message=f"Channel '{channel_name}' not available"
                )
            
            # Send notification
            result = channel.send_notification(alert)
            
            # Update delivery statistics
            self._update_delivery_stats(channel_name, result)
            
            return result
    
    def send_to_multiple_channels(self, alert: Alert, channel_names: List[str]) -> List[NotificationResult]:
        """Send notification to multiple channels"""
        results = []
        
        for channel_name in channel_names:
            result = self.send_notification(alert, channel_name)
            results.append(result)
        
        return results
    
    def get_available_channels(self) -> List[str]:
        """Get list of available channels"""
        with self._lock:
            return [
                name for name, channel in self.channels.items()
                if channel.is_available()
            ]
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics for all channels"""
        with self._lock:
            return {
                'channels': dict(self.delivery_stats),
                'total_channels': len(self.channels),
                'available_channels': len(self.get_available_channels()),
                'overall_success_rate': self._calculate_overall_success_rate()
            }
    
    def _setup_default_channels(self) -> None:
        """Setup default notification channels"""
        # Console channel (always available)
        self.add_channel(ConsoleNotificationChannel(verbose=False))
        
        # Log channel
        self.add_channel(LogNotificationChannel())
    
    def _update_delivery_stats(self, channel_name: str, result: NotificationResult) -> None:
        """Update delivery statistics for channel"""
        if channel_name not in self.delivery_stats:
            return
        
        stats = self.delivery_stats[channel_name]
        stats['total_attempts'] += 1
        stats['last_delivery'] = result.timestamp
        
        if result.success:
            stats['successful_deliveries'] += 1
        else:
            stats['failed_deliveries'] += 1
        
        # Update average latency
        if result.success and result.latency_ms > 0:
            current_avg = stats['avg_latency_ms']
            total_success = stats['successful_deliveries']
            stats['avg_latency_ms'] = (
                (current_avg * (total_success - 1) + result.latency_ms) / total_success
            )
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all channels"""
        total_attempts = sum(stats.get('total_attempts', 0) for stats in self.delivery_stats.values())
        total_successful = sum(stats.get('successful_deliveries', 0) for stats in self.delivery_stats.values())
        
        return (total_successful / max(total_attempts, 1)) * 100


class DashboardNotificationChannel(NotificationChannel):
    """Dashboard notification channel for real-time alerts"""
    
    def __init__(self, channel_name: str, dashboard_instance):
        self.channel_name = channel_name
        self.dashboard = dashboard_instance
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert to dashboard via WebSocket"""
        start_time = time.time()
        
        try:
            # Prepare alert data for dashboard
            alert_data = {
                'alert_id': alert.alert_id,
                'severity': alert.severity.value,
                'rule_name': alert.rule_name,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'metric_values': alert.metric_values or {},
                'channel': self.channel_name
            }
            
            # Broadcast to dashboard
            if hasattr(self.dashboard, 'socketio'):
                self.dashboard.socketio.emit('alert_notification', alert_data, broadcast=True)
            elif hasattr(self.dashboard, 'broadcast_alert'):
                self.dashboard.broadcast_alert(alert_data)
            else:
                raise Exception("Dashboard does not support alert broadcasting")
            
            latency = (time.time() - start_time) * 1000
            
            return NotificationResult(
                channel=self.channel_name,
                success=True,
                timestamp=datetime.now(),
                latency_ms=latency
            )
            
        except Exception as e:
            logger.error(f"Error sending dashboard notification: {e}")
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                timestamp=datetime.now(),
                latency_ms=0.0,
                error_message=str(e)
            )
    
    def get_channel_name(self) -> str:
        return self.channel_name
    
    def is_available(self) -> bool:
        return self.dashboard is not None


# Factory function for creating notification channels
def create_notification_channel(channel_type: str, **kwargs) -> NotificationChannel:
    """
    Factory function to create notification channels
    
    Args:
        channel_type: Type of channel ('console', 'dashboard', 'log', 'email', 'webhook')
        **kwargs: Channel-specific configuration parameters
    
    Returns:
        NotificationChannel instance
    
    Raises:
        ValueError: If channel_type is not supported
    """
    if channel_type.lower() == 'console':
        verbose = kwargs.get('verbose', False)
        return ConsoleNotificationChannel(verbose=verbose)
    
    elif channel_type.lower() == 'dashboard':
        channel_name = kwargs.get('channel_name', 'dashboard')
        dashboard_instance = kwargs.get('dashboard_instance')
        if not dashboard_instance:
            raise ValueError("dashboard_instance is required for dashboard channel")
        return DashboardNotificationChannel(channel_name, dashboard_instance)
    
    elif channel_type.lower() == 'log':
        log_file = kwargs.get('log_file', 'alerts.log')
        return LogNotificationChannel(log_file=log_file)
    
    elif channel_type.lower() == 'email':
        smtp_config = kwargs.get('smtp_config', {})
        recipients = kwargs.get('recipients', [])
        return EmailNotificationChannel(smtp_config=smtp_config, recipients=recipients)
    
    elif channel_type.lower() == 'webhook':
        webhook_url = kwargs.get('webhook_url')
        if not webhook_url:
            raise ValueError("webhook_url is required for webhook channel")
        return WebhookNotificationChannel(webhook_url=webhook_url)
    
    else:
        raise ValueError(f"Unsupported channel type: {channel_type}")


# Default channel configuration
DEFAULT_NOTIFICATION_CHANNELS = {
    'console': {'type': 'console', 'verbose': False},
    'dashboard': {'type': 'dashboard', 'channel_name': 'main_dashboard'},
    'log': {'type': 'log', 'log_file': 'system_alerts.log'}
}
