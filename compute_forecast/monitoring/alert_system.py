"""
IntelligentAlertSystem - Main coordination class for Issue #12.
Provides 500ms alert evaluation with built-in rules and intelligent suppression.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, deque
import re

from .alert_structures import (
    Alert, AlertRule, AlertSeverity, AlertStatus, EvaluationContext,
    AlertConfiguration, AlertSummary, NotificationResult,
    BUILT_IN_ALERT_RULES
)
from .dashboard_metrics import SystemMetrics

logger = logging.getLogger(__name__)


class AlertRuleEvaluator:
    """Evaluates alert rules against system metrics with safe expression parsing"""

    def __init__(self):
        self._safe_builtins = {
            'any': any,
            'all': all,
            'len': len,
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,
            '__builtins__': {}  # Disable dangerous builtins
        }

    def evaluate_rule(self, rule: AlertRule, context: EvaluationContext) -> bool:
        """
        Safely evaluate alert rule condition.
        Returns True if alert should be triggered.
        """
        try:
            # Create safe evaluation environment
            eval_globals = self._safe_builtins.copy()
            eval_locals = {
                'metrics': context.metrics,
                'context': context,
                'threshold_value': rule.threshold_value,
                'rule': rule
            }

            # Evaluate the condition
            result = eval(rule.condition, eval_globals, eval_locals)
            return bool(result)

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return False


class AlertNotificationManager:
    """Manages alert notification delivery across multiple channels"""

    def __init__(self):
        self.channels = {}
        self._notification_stats = defaultdict(lambda: {
            'sent': 0,
            'failed': 0,
            'total_latency_ms': 0.0
        })

    def add_channel(self, name: str, handler: callable) -> None:
        """Add a notification channel"""
        self.channels[name] = handler

    def send_notification(self, alert: Alert, channel_name: str) -> NotificationResult:
        """Send alert notification to specific channel"""
        start_time = time.time()

        try:
            if channel_name not in self.channels:
                raise ValueError(f"Unknown notification channel: {channel_name}")

            handler = self.channels[channel_name]
            success = handler(alert)

            latency_ms = (time.time() - start_time) * 1000
            self._update_stats(channel_name, success, latency_ms)

            return NotificationResult(
                channel=channel_name,
                success=success,
                timestamp=datetime.now(),
                latency_ms=latency_ms
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._update_stats(channel_name, False, latency_ms)

            return NotificationResult(
                channel=channel_name,
                success=False,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                error_message=str(e)
            )

    def send_to_all_channels(self, alert: Alert, channels: List[str]) -> List[NotificationResult]:
        """Send alert to multiple channels"""
        results = []

        for channel in channels:
            if channel in self.channels:
                result = self.send_notification(alert, channel)
                results.append(result)

        return results

    def _update_stats(self, channel: str, success: bool, latency_ms: float) -> None:
        """Update notification statistics"""
        stats = self._notification_stats[channel]

        if success:
            stats['sent'] += 1
        else:
            stats['failed'] += 1

        stats['total_latency_ms'] += latency_ms

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return dict(self._notification_stats)


class IntelligentAlertSystem:
    """
    Main intelligent alerting system coordinator.

    Provides 500ms alert evaluation with intelligent suppression,
    multi-channel notifications, and built-in rules.
    """

    def __init__(self, config: Optional[AlertConfiguration] = None):
        self.config = config or AlertConfiguration()

        # Core components
        self.rule_evaluator = AlertRuleEvaluator()
        self.notification_manager = None  # Set via dependency injection
        self.suppression_manager = None   # Set via dependency injection

        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=self.config.max_alert_history_size)
        self.rule_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Alert rules
        self.alert_rules: Dict[str, AlertRule] = {}
        self._load_built_in_rules()

        # Evaluation state
        self._running = False
        self._evaluation_thread: Optional[threading.Thread] = None
        self._last_evaluation = datetime.now()
        self._evaluation_lock = threading.RLock()

        # Performance tracking
        self._evaluation_times: deque = deque(maxlen=100)
        self._notification_times: deque = deque(maxlen=100)

        logger.info("IntelligentAlertSystem initialized")

    def set_notification_manager(self, manager) -> None:
        """Set notification manager dependency"""
        self.notification_manager = manager

    def set_suppression_manager(self, manager) -> None:
        """Set suppression manager dependency"""
        self.suppression_manager = manager

    def start(self) -> None:
        """Start alert evaluation and processing"""
        with self._evaluation_lock:
            if self._running:
                return

            self._running = True
            self._evaluation_thread = threading.Thread(
                target=self._evaluation_loop,
                daemon=True,
                name="AlertEvaluator"
            )
            self._evaluation_thread.start()

        logger.info("Alert system started")

    def stop(self) -> None:
        """Stop alert evaluation and processing"""
        with self._evaluation_lock:
            self._running = False

        if self._evaluation_thread:
            self._evaluation_thread.join(timeout=10.0)

        logger.info("Alert system stopped")

    def evaluate_alerts(self, metrics: SystemMetrics) -> List[Alert]:
        """
        Evaluate all active alert rules against system metrics.
        Must complete within 500ms per requirement.
        """
        start_time = time.time()
        triggered_alerts = []

        try:
            # Create evaluation context
            context = EvaluationContext(
                metrics=metrics,
                current_time=datetime.now(),
                rule_history=dict(self.rule_history),
                system_config={}
            )

            # Evaluate each enabled rule
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue

                try:
                    # Check if rule should be evaluated (cooldown, etc.)
                    if not self._should_evaluate_rule(rule, context):
                        continue

                    # Evaluate rule condition
                    if self.rule_evaluator.evaluate_rule(rule, context):
                        alert = self._create_alert(rule, context)
                        triggered_alerts.append(alert)

                        # Add to rule history
                        self.rule_history[rule_id].append(alert)

                except Exception as e:
                    logger.error(f"Error evaluating rule {rule_id}: {e}")

            # Process alerts (suppression, deduplication, etc.)
            processed_alerts = self._process_alerts(triggered_alerts)

            # Track evaluation time
            eval_time_ms = (time.time() - start_time) * 1000
            self._evaluation_times.append(eval_time_ms)

            if eval_time_ms > 500:
                logger.warning(f"Alert evaluation took {eval_time_ms:.1f}ms (>500ms limit)")

            return processed_alerts

        except Exception as e:
            logger.error(f"Critical error in alert evaluation: {e}")
            return []

    def send_notifications(self, alerts: List[Alert]) -> Dict[str, List[NotificationResult]]:
        """Send notifications for alerts"""
        if not self.notification_manager:
            logger.warning("No notification manager configured")
            return {}

        notification_results = {}
        start_time = time.time()

        for alert in alerts:
            if alert.status == AlertStatus.SUPPRESSED:
                continue

            try:
                results = self.notification_manager.send_to_all_channels(
                    alert,
                    alert.rule_id in self.alert_rules and
                    self.alert_rules[alert.rule_id].notification_channels or
                    self.config.default_channels
                )

                notification_results[alert.alert_id] = results

                # Update alert notification tracking
                alert.notifications_sent.extend([r.channel for r in results if r.success])
                alert.last_notification = datetime.now()
                alert.notification_count += 1

            except Exception as e:
                logger.error(f"Error sending notifications for alert {alert.alert_id}: {e}")

        # Track notification time
        notif_time_ms = (time.time() - start_time) * 1000
        self._notification_times.append(notif_time_ms)

        return notification_results

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule"""
        with self._evaluation_lock:
            self.alert_rules[rule.rule_id] = rule
            logger.info(f"Added alert rule: {rule.rule_id}")

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        with self._evaluation_lock:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"Removed alert rule: {rule_id}")
                return True
            return False

    def enable_alert_rule(self, rule_id: str) -> bool:
        """Enable an alert rule"""
        with self._evaluation_lock:
            if rule_id in self.alert_rules:
                self.alert_rules[rule_id].enabled = True
                logger.info(f"Enabled alert rule: {rule_id}")
                return True
            return False

    def disable_alert_rule(self, rule_id: str) -> bool:
        """Disable an alert rule"""
        with self._evaluation_lock:
            if rule_id in self.alert_rules:
                self.alert_rules[rule_id].enabled = False
                logger.info(f"Disabled alert rule: {rule_id}")
                return True
            return False

    def get_alert_summary(self, hours: int = 1) -> AlertSummary:
        """Get summary of alert activity"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Count alerts by severity and status
        severity_counts = defaultdict(int)
        status_counts = defaultdict(int)
        
        for alert in self.alert_history:
            if alert.timestamp >= cutoff_time:
                severity_counts[alert.severity.value] += 1
                status_counts[alert.status.value] += 1

        # Calculate resolution times
        resolution_times = []
        for alert in self.alert_history:
            if alert.resolved_at and alert.timestamp >= cutoff_time:
                resolution_time = (alert.resolved_at - alert.timestamp).total_seconds() / 60
                resolution_times.append(resolution_time)

        # Get most frequent rules
        rule_frequency = defaultdict(int)
        for alert in self.alert_history:
            if alert.timestamp >= cutoff_time:
                rule_frequency[alert.rule_name] += 1

        most_frequent = sorted(rule_frequency.items(), key=lambda x: x[1], reverse=True)[:5]

        return AlertSummary(
            time_period=f"Last {hours} hour(s)",
            start_time=cutoff_time,
            end_time=datetime.now(),
            total_alerts=sum(severity_counts.values()),
            info_alerts=severity_counts.get('info', 0),
            warning_alerts=severity_counts.get('warning', 0),
            error_alerts=severity_counts.get('error', 0),
            critical_alerts=severity_counts.get('critical', 0),
            active_alerts=status_counts.get('active', 0),
            acknowledged_alerts=status_counts.get('acknowledged', 0),
            resolved_alerts=status_counts.get('resolved', 0),
            suppressed_alerts=status_counts.get('suppressed', 0),
            avg_resolution_time_minutes=sum(resolution_times) / len(resolution_times) if resolution_times else 0.0,
            avg_notification_latency_ms=sum(self._notification_times) / len(self._notification_times) if self._notification_times else 0.0,
            most_frequent_rules=[rule for rule, _ in most_frequent]
        )

    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts"""
        with self._evaluation_lock:
            return [
                alert for alert in self.active_alerts.values()
                if alert.status == AlertStatus.ACTIVE
            ]

    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        with self._evaluation_lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledge(user)
                return True
            return False

    def resolve_alert(self, alert_id: str, reason: str = "manual resolution") -> bool:
        """Resolve an alert"""
        with self._evaluation_lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolve(reason)
                
                # Move to history and remove from active
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                
                return True
            return False

    def _load_built_in_rules(self) -> None:
        """Load built-in alert rules"""
        for rule_id, rule in BUILT_IN_ALERT_RULES.items():
            self.alert_rules[rule_id] = rule

        logger.info(f"Loaded {len(BUILT_IN_ALERT_RULES)} built-in alert rules")

    def _should_evaluate_rule(self, rule: AlertRule, context: EvaluationContext) -> bool:
        """Check if rule should be evaluated based on cooldown and other factors"""
        # Check cooldown
        if rule.rule_id in self.rule_history:
            recent_alerts = self.rule_history[rule.rule_id]
            if recent_alerts:
                last_alert = recent_alerts[-1]
                time_since_last = (context.current_time - last_alert.timestamp).total_seconds() / 60
                
                if time_since_last < rule.cooldown_minutes:
                    return False

        # Check minimum trigger count within time window
        if rule.minimum_trigger_count > 1:
            window_start = context.current_time - timedelta(minutes=rule.time_window_minutes)
            recent_triggers = sum(
                1 for alert in self.rule_history.get(rule.rule_id, [])
                if alert.timestamp >= window_start
            )
            
            if recent_triggers < rule.minimum_trigger_count - 1:
                return True  # Need more triggers
            
        return True

    def _create_alert(self, rule: AlertRule, context: EvaluationContext) -> Alert:
        """Create alert from triggered rule"""
        alert = Alert(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            message=rule.description,
            description=f"Alert triggered: {rule.description}",
            severity=rule.severity,
            metric_values=self._extract_metric_values(rule, context),
            system_context={
                'threshold_value': rule.threshold_value,
                'evaluation_time': context.current_time.isoformat()
            },
            tags=rule.tags
        )

        return alert

    def _extract_metric_values(self, rule: AlertRule, context: EvaluationContext) -> Dict[str, Any]:
        """Extract relevant metric values for alert context"""
        metric_values = {}

        # Extract values mentioned in rule condition
        # This is a simplified implementation - could be enhanced with AST parsing
        try:
            if 'collection_progress' in rule.condition:
                metric_values['collection_progress'] = {
                    'papers_per_minute': context.metrics.collection_progress.papers_per_minute,
                    'total_papers': context.metrics.collection_progress.papers_collected
                }

            if 'api_metrics' in rule.condition:
                metric_values['api_health'] = {
                    api_name: {
                        'status': api.health_status,
                        'requests': api.requests_made,
                        'failed': api.failed_requests
                    }
                    for api_name, api in context.metrics.api_metrics.items()
                }

            if 'memory_usage' in rule.condition:
                metric_values['memory_usage_percent'] = context.metrics.system_metrics.memory_usage_percent

        except Exception as e:
            logger.debug(f"Error extracting metric values: {e}")

        return metric_values

    def _process_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Process alerts through suppression and deduplication"""
        if not self.suppression_manager:
            return alerts

        processed_alerts = []

        for alert in alerts:
            # Check suppression
            if self.suppression_manager.should_suppress_alert(alert):
                alert.suppress("automatic suppression")
                logger.debug(f"Alert {alert.alert_id} suppressed")

            # Add to active alerts
            self.active_alerts[alert.alert_id] = alert
            
            # Add to history
            self.alert_history.append(alert)
            
            processed_alerts.append(alert)

        return processed_alerts

    def _evaluation_loop(self) -> None:
        """Main evaluation loop that runs periodically"""
        while self._running:
            try:
                # Wait for next evaluation interval
                time.sleep(self.config.evaluation_interval_seconds)

                # Skip if no metrics provider is available
                if not hasattr(self, 'metrics_provider'):
                    continue

                # Get current metrics
                metrics = self.metrics_provider()
                
                # Evaluate alerts
                alerts = self.evaluate_alerts(metrics)
                
                # Send notifications for new alerts
                if alerts:
                    self.send_notifications([
                        alert for alert in alerts
                        if alert.status == AlertStatus.ACTIVE
                    ])

                # Check for auto-resolution
                self._check_auto_resolution(metrics)

                self._last_evaluation = datetime.now()

            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")

    def _check_auto_resolution(self, metrics: SystemMetrics) -> None:
        """Check if any active alerts can be auto-resolved"""
        with self._evaluation_lock:
            for alert_id, alert in list(self.active_alerts.items()):
                if alert.status != AlertStatus.ACTIVE:
                    continue

                rule = self.alert_rules.get(alert.rule_id)
                if not rule or not rule.auto_resolve:
                    continue

                # Create evaluation context
                context = EvaluationContext(
                    metrics=metrics,
                    current_time=datetime.now(),
                    rule_history=dict(self.rule_history),
                    system_config={}
                )

                # Check auto-resolve condition
                try:
                    if rule.auto_resolve_condition:
                        eval_globals = self.rule_evaluator._safe_builtins.copy()
                        eval_locals = {
                            'metrics': metrics,
                            'context': context,
                            'alert': alert
                        }

                        if eval(rule.auto_resolve_condition, eval_globals, eval_locals):
                            self.resolve_alert(alert_id, "auto-resolved")
                            logger.info(f"Auto-resolved alert {alert_id}")

                except Exception as e:
                    logger.error(f"Error checking auto-resolve for {alert_id}: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self._evaluation_lock:
            avg_eval_time = sum(self._evaluation_times) / len(self._evaluation_times) if self._evaluation_times else 0
            avg_notif_time = sum(self._notification_times) / len(self._notification_times) if self._notification_times else 0

            return {
                'running': self._running,
                'enabled_rules': sum(1 for r in self.alert_rules.values() if r.enabled),
                'total_rules': len(self.alert_rules),
                'active_alerts': len([a for a in self.active_alerts.values() if a.status == AlertStatus.ACTIVE]),
                'total_alerts_in_memory': len(self.active_alerts),
                'last_evaluation': self._last_evaluation.isoformat(),
                'avg_evaluation_time_ms': avg_eval_time,
                'avg_notification_time_ms': avg_notif_time,
                'evaluation_performance': 'good' if avg_eval_time < 500 else 'degraded'
            }


class AlertSystemFactory:
    """Factory for creating and configuring alert system instances"""

    @staticmethod
    def create_default_system() -> IntelligentAlertSystem:
        """Create alert system with default configuration"""
        from .alert_suppression import AlertSuppressionManager
        
        # Create system
        alert_system = IntelligentAlertSystem()
        
        # Create and inject dependencies
        notification_manager = AlertNotificationManager()
        suppression_manager = AlertSuppressionManager()
        
        # Import notification channels
        from .notification_channels import (
            ConsoleNotificationChannel,
            DashboardNotificationChannel,
            LogNotificationChannel
        )
        
        # Add default notification channels using wrapper lambdas
        console_channel = ConsoleNotificationChannel(verbose=False)
        notification_manager.add_channel('console', lambda alert: console_channel.send_notification(alert).success)
        
        dashboard_channel = DashboardNotificationChannel()
        notification_manager.add_channel('dashboard', lambda alert: dashboard_channel.send_notification(alert).success)
        
        log_channel = LogNotificationChannel()
        notification_manager.add_channel('log', lambda alert: log_channel.send_notification(alert).success)
        
        # Inject dependencies
        alert_system.set_notification_manager(notification_manager)
        alert_system.set_suppression_manager(suppression_manager)
        
        return alert_system

    @staticmethod
    def create_test_system() -> IntelligentAlertSystem:
        """Create alert system for testing with minimal configuration"""
        config = AlertConfiguration(
            evaluation_interval_seconds=1,
            max_alert_history_size=100,
            enable_auto_suppression=False
        )
        
        return IntelligentAlertSystem(config)