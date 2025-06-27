"""
Notification Channels - Delivery mechanisms for alert notifications.

Implements different notification channels including console output,
dashboard integration, and extensible base classes for additional channels.
"""

import sys
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List

from .alert_structures import Alert, NotificationResult


logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Base class for notification channels"""
    
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.enabled = True
        self.delivery_stats = {
            'total_attempts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'last_delivery_time': None
        }
    
    @abstractmethod
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert notification through this channel"""
        pass
    
    def test_connection(self) -> bool:
        """Test if notification channel is working"""
        try:
            # Default implementation - subclasses should override
            return self.enabled
        except Exception as e:
            logger.error(f"Connection test failed for {self.channel_name}: {e}")
            return False
    
    def _update_delivery_stats(self, success: bool):
        """Update delivery statistics"""
        self.delivery_stats['total_attempts'] += 1
        if success:
            self.delivery_stats['successful_deliveries'] += 1
        else:
            self.delivery_stats['failed_deliveries'] += 1
        self.delivery_stats['last_delivery_time'] = datetime.now()
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics for this channel"""
        total = self.delivery_stats['total_attempts']
        success_rate = (self.delivery_stats['successful_deliveries'] / total) if total > 0 else 0.0
        
        return {
            'channel_name': self.channel_name,
            'enabled': self.enabled,
            'total_attempts': total,
            'successful_deliveries': self.delivery_stats['successful_deliveries'],
            'failed_deliveries': self.delivery_stats['failed_deliveries'],
            'success_rate': success_rate,
            'last_delivery_time': self.delivery_stats['last_delivery_time']
        }


class ConsoleNotificationChannel(NotificationChannel):
    """Console/stdout notification channel"""
    
    def __init__(self, use_colors: bool = True, verbose: bool = False):
        super().__init__("console")
        self.use_colors = use_colors
        self.verbose = verbose
        
        # ANSI color codes
        self.color_codes = {
            "info": "\033[94m",      # Blue
            "warning": "\033[93m",   # Yellow
            "error": "\033[91m",     # Red
            "critical": "\033[95m"   # Magenta
        } if use_colors else {}
        
        self.reset_code = "\033[0m" if use_colors else ""
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert to console"""
        try:
            # Format alert for console display
            message = self._format_alert_message(alert)
            
            # Print to stdout for visibility
            print(message, file=sys.stdout)
            sys.stdout.flush()
            
            # Also log for persistence
            logger.info(f"ALERT: {alert.title} - {alert.message}")
            
            self._update_delivery_stats(True)
            
            return NotificationResult(
                success=True,
                channel="console",
                delivery_time=datetime.now()
            )
            
        except Exception as e:
            self._update_delivery_stats(False)
            
            return NotificationResult(
                success=False,
                channel="console",
                error_messages=[str(e)],
                delivery_time=datetime.now()
            )
    
    def _format_alert_message(self, alert: Alert) -> str:
        """Format alert for console display"""
        # Get color for severity
        color = self.color_codes.get(alert.severity, "")
        
        # Build basic message
        message_lines = [
            f"{color}[{alert.severity.upper()}] {alert.title}{self.reset_code}",
            f"  {alert.message}",
            f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Alert ID: {alert.alert_id}"
        ]
        
        # Add current vs threshold if available
        if alert.current_value is not None and alert.threshold_value is not None:
            message_lines.append(f"  Current: {alert.current_value}, Threshold: {alert.threshold_value}")
        
        # Add affected components
        if alert.affected_components:
            message_lines.append(f"  Affected: {', '.join(alert.affected_components)}")
        
        # Add recommended actions in verbose mode
        if self.verbose and alert.recommended_actions:
            message_lines.append("  Recommended Actions:")
            for action in alert.recommended_actions:
                message_lines.append(f"    - {action}")
        
        return "\n".join(message_lines) + "\n"
    
    def test_connection(self) -> bool:
        """Test console output"""
        try:
            test_message = f"[TEST] Console notification channel test at {datetime.now()}"
            print(test_message, file=sys.stdout)
            sys.stdout.flush()
            return True
        except Exception as e:
            logger.error(f"Console test failed: {e}")
            return False


class DashboardNotificationChannel(NotificationChannel):
    """Dashboard notification channel using SocketIO"""
    
    def __init__(self, dashboard_server=None):
        super().__init__("dashboard")
        self.dashboard_server = dashboard_server
        self.socketio = None
        
        # Set up SocketIO reference if dashboard server is provided
        if dashboard_server and hasattr(dashboard_server, 'socketio'):
            self.socketio = dashboard_server.socketio
    
    def set_dashboard_server(self, dashboard_server):
        """Set dashboard server reference after initialization"""
        self.dashboard_server = dashboard_server
        if dashboard_server and hasattr(dashboard_server, 'socketio'):
            self.socketio = dashboard_server.socketio
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert to dashboard clients"""
        try:
            if not self.socketio:
                raise Exception("Dashboard SocketIO not available")
            
            # Format alert for dashboard
            alert_data = self._format_alert_for_dashboard(alert)
            
            # Broadcast to dashboard clients
            self.socketio.emit('alert_triggered', alert_data)
            
            self._update_delivery_stats(True)
            
            return NotificationResult(
                success=True,
                channel="dashboard",
                delivery_time=datetime.now()
            )
            
        except Exception as e:
            self._update_delivery_stats(False)
            
            return NotificationResult(
                success=False,
                channel="dashboard",
                error_messages=[str(e)],
                delivery_time=datetime.now()
            )
    
    def _format_alert_for_dashboard(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for dashboard consumption"""
        return {
            'alert_id': alert.alert_id,
            'rule_id': alert.rule_id,
            'severity': alert.severity,
            'title': alert.title,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'current_value': alert.current_value,
            'threshold_value': alert.threshold_value,
            'affected_components': alert.affected_components,
            'recommended_actions': alert.recommended_actions,
            'status': alert.status,
            'escalation_level': alert.escalation_level
        }
    
    def test_connection(self) -> bool:
        """Test dashboard connection"""
        try:
            if not self.socketio:
                return False
            
            # Test by emitting a test event
            test_data = {
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'message': 'Dashboard notification channel test'
            }
            self.socketio.emit('notification_test', test_data)
            return True
            
        except Exception as e:
            logger.error(f"Dashboard test failed: {e}")
            return False


class LogNotificationChannel(NotificationChannel):
    """File-based logging notification channel"""
    
    def __init__(self, log_file: str = "alerts.log", log_level: str = "INFO"):
        super().__init__("log")
        self.log_file = log_file
        self.log_level = log_level.upper()
        
        # Set up dedicated logger for alerts
        self.alert_logger = logging.getLogger('alerts')
        
        # Create file handler if not exists
        if not any(isinstance(h, logging.FileHandler) for h in self.alert_logger.handlers):
            file_handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.alert_logger.addHandler(file_handler)
            self.alert_logger.setLevel(getattr(logging, log_level))
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Log alert to file"""
        try:
            # Create structured log entry
            log_data = {
                'alert_id': alert.alert_id,
                'rule_id': alert.rule_id,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'affected_components': alert.affected_components
            }
            
            # Log at appropriate level
            log_message = f"ALERT: {json.dumps(log_data, separators=(',', ':'))}"
            
            if alert.severity == "critical":
                self.alert_logger.critical(log_message)
            elif alert.severity == "error":
                self.alert_logger.error(log_message)
            elif alert.severity == "warning":
                self.alert_logger.warning(log_message)
            else:
                self.alert_logger.info(log_message)
            
            self._update_delivery_stats(True)
            
            return NotificationResult(
                success=True,
                channel="log",
                delivery_time=datetime.now()
            )
            
        except Exception as e:
            self._update_delivery_stats(False)
            
            return NotificationResult(
                success=False,
                channel="log",
                error_messages=[str(e)],
                delivery_time=datetime.now()
            )
    
    def test_connection(self) -> bool:
        """Test log file writing"""
        try:
            test_message = f"Log notification channel test at {datetime.now()}"
            self.alert_logger.info(test_message)
            return True
        except Exception as e:
            logger.error(f"Log test failed: {e}")
            return False


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel (placeholder implementation)"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 recipients: List[str], use_tls: bool = True):
        super().__init__("email")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
        self.use_tls = use_tls
        
        # Note: This is a placeholder implementation
        # Full email functionality would require additional dependencies
        logger.warning("EmailNotificationChannel is a placeholder implementation")
    
    def send_notification(self, alert: Alert) -> NotificationResult:
        """Send alert via email (placeholder)"""
        try:
            # Placeholder implementation
            logger.info(f"Would send email alert: {alert.title} to {self.recipients}")
            
            self._update_delivery_stats(True)
            
            return NotificationResult(
                success=True,
                channel="email",
                delivery_time=datetime.now()
            )
            
        except Exception as e:
            self._update_delivery_stats(False)
            
            return NotificationResult(
                success=False,
                channel="email",
                error_messages=[str(e)],
                delivery_time=datetime.now()
            )
    
    def test_connection(self) -> bool:
        """Test email connection (placeholder)"""
        # Placeholder - would test SMTP connection
        logger.info("Email connection test (placeholder)")
        return True


class NotificationChannelManager:
    """Manager for multiple notification channels"""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.channel_routing: Dict[str, List[str]] = {}  # severity -> list of channel names
        self.global_enabled = True
    
    def add_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        self.channels[channel.channel_name] = channel
        logger.info(f"Added notification channel: {channel.channel_name}")
    
    def remove_channel(self, channel_name: str) -> bool:
        """Remove a notification channel"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            logger.info(f"Removed notification channel: {channel_name}")
            return True
        return False
    
    def set_channel_routing(self, severity: str, channel_names: List[str]):
        """Set which channels should receive alerts of specific severity"""
        self.channel_routing[severity] = channel_names
    
    def send_to_channels(self, alert: Alert, channel_names: List[str]) -> List[NotificationResult]:
        """Send alert to specific channels"""
        if not self.global_enabled:
            return []
        
        results = []
        
        for channel_name in channel_names:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                if channel.enabled:
                    try:
                        result = channel.send_notification(alert)
                        results.append(result)
                    except Exception as e:
                        results.append(NotificationResult(
                            success=False,
                            channel=channel_name,
                            error_messages=[str(e)],
                            delivery_time=datetime.now()
                        ))
                else:
                    logger.debug(f"Channel {channel_name} is disabled")
            else:
                logger.warning(f"Channel {channel_name} not found")
                results.append(NotificationResult(
                    success=False,
                    channel=channel_name,
                    error_messages=[f"Channel {channel_name} not found"],
                    delivery_time=datetime.now()
                ))
        
        return results
    
    def send_with_routing(self, alert: Alert) -> List[NotificationResult]:
        """Send alert using severity-based routing"""
        channel_names = self.channel_routing.get(alert.severity, [])
        return self.send_to_channels(alert, channel_names)
    
    def test_all_channels(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}
        
        for channel_name, channel in self.channels.items():
            try:
                results[channel_name] = channel.test_connection()
            except Exception as e:
                logger.error(f"Test failed for {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def get_channel_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get delivery statistics for all channels"""
        return {
            channel_name: channel.get_delivery_stats()
            for channel_name, channel in self.channels.items()
        }
    
    def enable_all_channels(self):
        """Enable all notification channels"""
        for channel in self.channels.values():
            channel.enabled = True
        self.global_enabled = True
    
    def disable_all_channels(self):
        """Disable all notification channels"""
        for channel in self.channels.values():
            channel.enabled = False
        self.global_enabled = False