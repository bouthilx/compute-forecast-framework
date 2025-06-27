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
    BUILT_IN_ALERT_RULES, AlertStatus
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
    
    def get_metric_context(self, rule: AlertRule, context: EvaluationContext) -> Dict[str, Any]:
        """Extract relevant metric values for alert context"""
        metric_context = {}
        
        try:
            # Extract metrics mentioned in condition
            condition_lower = rule.condition.lower()
            
            if 'papers_per_minute' in condition_lower:
                metric_context['papers_per_minute'] = context.metrics.collection_progress.papers_per_minute
            
            if 'memory_usage_percent' in condition_lower:
                metric_context['memory_usage_percent'] = context.metrics.system_metrics.memory_usage_percent
            
            if 'api_metrics' in condition_lower:
                api_health = {}
                for api_name, api_data in context.metrics.api_metrics.items():
                    api_health[api_name] = {
                        'health_status': api_data.health_status,
                        'success_rate': api_data.success_rate,
                        'avg_response_time_ms': api_data.avg_response_time_ms
                    }
                metric_context['api_health'] = api_health
            
            if 'processing_errors' in condition_lower:
                metric_context['processing_errors'] = context.metrics.processing_metrics.processing_errors
                metric_context['papers_processed'] = context.metrics.processing_metrics.papers_processed
            
            if 'venue_progress' in condition_lower:
                stalled_venues = []
                for venue_key, venue_data in context.metrics.venue_progress.items():
                    if venue_data.status == 'in_progress' and venue_data.last_activity:
                        stall_time = (context.current_time - venue_data.last_activity).total_seconds()
                        stalled_venues.append({
                            'venue': venue_data.venue_name,
                            'year': venue_data.year,
                            'stall_time_seconds': stall_time
                        })
                metric_context['stalled_venues'] = stalled_venues
            
        except Exception as e:
            logger.debug(f"Error extracting metric context for rule {rule.rule_id}: {e}")
        
        return metric_context


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
            
            # Process triggered alerts through suppression
            processed_alerts = self._process_alerts(triggered_alerts)
            
            # Update active alerts
            for alert in processed_alerts:
                if alert.status == AlertStatus.ACTIVE:
                    self.active_alerts[alert.alert_id] = alert
                    self.alert_history.append(alert)
            
            # Track evaluation performance
            evaluation_time = (time.time() - start_time) * 1000  # Convert to ms
            self._evaluation_times.append(evaluation_time)
            
            if evaluation_time > 500:
                logger.warning(f"Alert evaluation took {evaluation_time:.1f}ms (requirement: <500ms)")
            
            return processed_alerts
            
        except Exception as e:
            logger.error(f"Error in alert evaluation: {e}")
            return []
    
    def send_notifications(self, alerts: List[Alert]) -> List[NotificationResult]:
        """Send notifications for alerts through configured channels"""
        if not self.notification_manager:
            logger.warning("No notification manager configured")
            return []
        
        start_time = time.time()
        results = []
        
        try:
            for alert in alerts:
                if alert.status != AlertStatus.ACTIVE:
                    continue
                
                # Get notification channels for this alert
                channels = self._get_notification_channels(alert)
                
                # Send notifications
                for channel in channels:
                    try:
                        result = self.notification_manager.send_notification(alert, channel)
                        results.append(result)
                        
                        # Update alert notification tracking
                        if result.success:
                            alert.notifications_sent.append(channel)
                            alert.last_notification = result.timestamp
                            alert.notification_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error sending notification via {channel}: {e}")
                        results.append(NotificationResult(
                            channel=channel,
                            success=False,
                            timestamp=datetime.now(),
                            latency_ms=0.0,
                            error_message=str(e)
                        ))
            
            # Track notification performance
            notification_time = (time.time() - start_time) * 1000
            self._notification_times.append(notification_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in notification processing: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledge(user)
            logger.info(f"Alert {alert_id} acknowledged by {user}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, reason: str = "manual") -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolve(reason)
            del self.active_alerts[alert_id]
            logger.info(f"Alert {alert_id} resolved: {reason}")
            return True
        return False
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.rule_id}")
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def get_alert_summary(self, time_period_hours: int = 24) -> AlertSummary:
        """Generate alert summary for specified time period"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_period_hours)
        
        # Filter alerts in time period
        period_alerts = [
            alert for alert in self.alert_history
            if start_time <= alert.timestamp <= end_time
        ]
        
        # Calculate summary statistics
        summary = AlertSummary(
            time_period=f"{time_period_hours}h",
            start_time=start_time,
            end_time=end_time,
            total_alerts=len(period_alerts)
        )
        
        # Count by severity
        for alert in period_alerts:
            if alert.severity == AlertSeverity.INFO:
                summary.info_alerts += 1
            elif alert.severity == AlertSeverity.WARNING:
                summary.warning_alerts += 1
            elif alert.severity == AlertSeverity.ERROR:
                summary.error_alerts += 1
            elif alert.severity == AlertSeverity.CRITICAL:
                summary.critical_alerts += 1
        
        # Count by status
        for alert in period_alerts:
            if alert.status == AlertStatus.ACTIVE:
                summary.active_alerts += 1
            elif alert.status == AlertStatus.ACKNOWLEDGED:
                summary.acknowledged_alerts += 1
            elif alert.status == AlertStatus.RESOLVED:
                summary.resolved_alerts += 1
            elif alert.status == AlertStatus.SUPPRESSED:
                summary.suppressed_alerts += 1
        
        # Calculate performance metrics
        if period_alerts:
            resolved_alerts = [a for a in period_alerts if a.resolved_at]
            if resolved_alerts:
                avg_resolution = sum(
                    (a.resolved_at - a.timestamp).total_seconds() 
                    for a in resolved_alerts
                ) / len(resolved_alerts) / 60  # Convert to minutes
                summary.avg_resolution_time_minutes = avg_resolution
        
        if self._evaluation_times:
            summary.avg_notification_latency_ms = sum(self._evaluation_times) / len(self._evaluation_times)
        
        return summary
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get alert system performance statistics"""
        stats = {
            'avg_evaluation_time_ms': 0.0,
            'max_evaluation_time_ms': 0.0,
            'evaluation_count': len(self._evaluation_times),
            'active_alerts_count': len(self.active_alerts),
            'total_rules': len(self.alert_rules),
            'enabled_rules': sum(1 for rule in self.alert_rules.values() if rule.enabled)
        }
        
        if self._evaluation_times:
            stats['avg_evaluation_time_ms'] = sum(self._evaluation_times) / len(self._evaluation_times)
            stats['max_evaluation_time_ms'] = max(self._evaluation_times)
        
        return stats
    
    def _load_built_in_rules(self) -> None:
        """Load built-in alert rules"""
        for rule_id, rule in BUILT_IN_ALERT_RULES.items():
            self.alert_rules[rule_id] = rule
        
        logger.info(f"Loaded {len(BUILT_IN_ALERT_RULES)} built-in alert rules")
    
    def _evaluation_loop(self) -> None:
        """Main evaluation loop running in background"""
        while self._running:
            try:
                time.sleep(self.config.evaluation_interval_seconds)
                
                # Auto-resolve alerts if configured
                self._check_auto_resolution()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                time.sleep(1)
    
    def _should_evaluate_rule(self, rule: AlertRule, context: EvaluationContext) -> bool:
        """Check if rule should be evaluated based on cooldown and other factors"""
        # Check if rule is in cooldown
        recent_alerts = [
            alert for alert in self.rule_history[rule.rule_id]
            if (context.current_time - alert.timestamp).total_seconds() < rule.cooldown_minutes * 60
        ]
        
        if recent_alerts:
            return False
        
        # Check minimum trigger count
        if rule.minimum_trigger_count > 1:
            window_start = context.current_time - timedelta(minutes=rule.time_window_minutes)
            window_alerts = [
                alert for alert in self.rule_history[rule.rule_id]
                if alert.timestamp >= window_start
            ]
            
            if len(window_alerts) < rule.minimum_trigger_count - 1:
                return False
        
        return True
    
    def _create_alert(self, rule: AlertRule, context: EvaluationContext) -> Alert:
        """Create alert instance from triggered rule"""
        # Get metric context for alert
        metric_context = self.rule_evaluator.get_metric_context(rule, context)
        
        alert = Alert(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            message=f"{rule.name}: {rule.description}",
            description=rule.description,
            severity=rule.severity,
            timestamp=context.current_time,
            metric_values=metric_context,
            tags=rule.tags.copy()
        )
        
        return alert
    
    def _process_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Process alerts through suppression and other filters"""
        if not self.suppression_manager:
            return alerts
        
        processed_alerts = []
        
        for alert in alerts:
            # Check if alert should be suppressed
            if self.suppression_manager.should_suppress_alert(alert):
                alert.suppress("automatic suppression")
                logger.debug(f"Alert {alert.alert_id} suppressed")
            
            processed_alerts.append(alert)
        
        return processed_alerts
    
    def _get_notification_channels(self, alert: Alert) -> List[str]:
        """Get notification channels for alert"""
        # Get channels from rule
        rule = self.alert_rules.get(alert.rule_id)
        if rule and rule.notification_channels:
            return rule.notification_channels
        
        # Use default channels
        return self.config.default_channels
    
    def _check_auto_resolution(self) -> None:
        """Check for auto-resolution of alerts"""
        for alert_id, alert in list(self.active_alerts.items()):
            rule = self.alert_rules.get(alert.rule_id)
            
            if rule and rule.auto_resolve and rule.auto_resolve_condition:
                try:
                    # This would need current metrics to evaluate
                    # For now, just log that auto-resolution is configured
                    logger.debug(f"Auto-resolution configured for alert {alert_id}")
                except Exception as e:
                    logger.debug(f"Error checking auto-resolution for {alert_id}: {e}")
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts from active alerts"""
        current_time = datetime.now()
        retention_cutoff = current_time - timedelta(days=self.config.alert_retention_days)
        
        # Remove old alerts from history
        while (self.alert_history and 
               self.alert_history[0].timestamp < retention_cutoff):
            self.alert_history.popleft()
        
        # Clean up rule history
        for rule_id, history in self.rule_history.items():
            while history and history[0].timestamp < retention_cutoff:
                history.popleft()