"""
Intelligent Alert System - Main alerting system for collection monitoring.

Coordinates alert rule evaluation, suppression management, and notification delivery
to provide proactive alerting during 4-6 hour collection sessions.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque

from .alert_structures import (
    AlertRule, Alert, AlertConfiguration, AlertDeliveryResult, AlertSummary,
    EvaluationContext, BUILT_IN_ALERT_RULES
)
from .alert_suppression import AlertSuppressionManager, SuppressionRuleManager
from .notification_channels import (
    NotificationChannelManager, ConsoleNotificationChannel, 
    DashboardNotificationChannel, LogNotificationChannel
)
from .dashboard_metrics import SystemMetrics


logger = logging.getLogger(__name__)


class IntelligentAlertSystem:
    """
    Proactive alerting system for collection issues and optimization opportunities
    
    Monitors collection health, detects problems early, and provides actionable alerts
    during 4-6 hour collection sessions with intelligent suppression and routing.
    """
    
    def __init__(self, alert_config: AlertConfiguration):
        self.config = alert_config
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        # Core components
        self.suppression_manager = AlertSuppressionManager()
        self.suppression_rule_manager = SuppressionRuleManager(self.suppression_manager)
        self.notification_manager = NotificationChannelManager()
        
        # Auto-action handlers
        self.auto_action_handlers: Dict[str, callable] = {}
        
        # Performance tracking
        self.evaluation_stats = {
            'total_evaluations': 0,
            'alerts_triggered': 0,
            'alerts_suppressed': 0,
            'avg_evaluation_time_ms': 0.0,
            'last_evaluation_time': None
        }
        
        self._lock = threading.RLock()
        
        # Initialize with built-in alert rules
        self._load_alert_rules()
        
        # Set up default notification channels
        self._setup_default_notification_channels()
    
    def evaluate_alerts(self, metrics: SystemMetrics) -> List[Alert]:
        """
        Evaluate all alert rules against current metrics
        
        REQUIREMENTS:
        - Must evaluate all rules within 500ms
        - Must apply alert suppression logic
        - Must calculate alert severity automatically
        - Must provide actionable recommendations
        """
        evaluation_start = time.time()
        triggered_alerts = []
        
        with self._lock:
            self.evaluation_stats['total_evaluations'] += 1
            
            for rule_id, rule in self.alert_rules.items():
                try:
                    if not rule.enabled:
                        continue
                    
                    # Check if rule is in cooldown
                    if not rule.can_trigger():
                        continue
                    
                    # Evaluate rule condition
                    alert = self._evaluate_single_rule(rule, metrics)
                    
                    if alert:
                        # Check suppression before adding to triggered alerts
                        if not self.suppression_manager.is_suppressed(alert):
                            triggered_alerts.append(alert)
                            self.evaluation_stats['alerts_triggered'] += 1
                            
                            # Update rule trigger tracking
                            rule.record_trigger_attempt(True)
                            
                            # Apply auto-suppression if configured
                            if rule.suppress_duration_minutes > 0:
                                self.suppression_manager.auto_suppress_alert_rule(
                                    rule_id, rule.suppress_duration_minutes
                                )
                        else:
                            self.evaluation_stats['alerts_suppressed'] += 1
                            logger.debug(f"Alert suppressed: {rule_id}")
                
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule_id}: {e}")
                    rule.record_trigger_attempt(False)
            
            # Update performance statistics
            evaluation_time = (time.time() - evaluation_start) * 1000  # Convert to ms
            self._update_evaluation_stats(evaluation_time)
            
            # Check evaluation performance requirement
            if evaluation_time > 500:
                logger.warning(f"Alert evaluation took {evaluation_time:.1f}ms (>500ms limit)")
            
            # Store triggered alerts in history
            for alert in triggered_alerts:
                self.alert_history.append(alert)
            
            # Analyze patterns for intelligent suppression
            for alert in triggered_alerts:
                self.suppression_rule_manager.analyze_and_suppress(alert)
            
            self.evaluation_stats['last_evaluation_time'] = datetime.now()
        
        return triggered_alerts
    
    def send_alert(self, alert: Alert) -> AlertDeliveryResult:
        """
        Send alert through configured notification channels
        
        REQUIREMENTS:
        - Must respect alert suppression rules
        - Must retry failed deliveries
        - Must log all alert attempts
        - Must support multiple notification channels
        """
        delivery_start = time.time()
        
        # Get rule configuration
        rule = self.alert_rules.get(alert.rule_id)
        if not rule:
            return AlertDeliveryResult(
                alert_id=alert.alert_id,
                success=False,
                delivery_channels=[],
                failed_channels=[],
                delivery_time=datetime.now(),
                error_messages=[f"Rule {alert.rule_id} not found"]
            )
        
        # Send to configured channels
        notification_results = self.notification_manager.send_to_channels(
            alert, rule.notification_channels
        )
        
        # Process results
        successful_channels = [r.channel for r in notification_results if r.success]
        failed_channels = [r.channel for r in notification_results if not r.success]
        error_messages = []
        
        for result in notification_results:
            if not result.success:
                error_messages.extend(result.error_messages)
        
        delivery_result = AlertDeliveryResult(
            alert_id=alert.alert_id,
            success=len(successful_channels) > 0,
            delivery_channels=successful_channels,
            failed_channels=failed_channels,
            delivery_time=datetime.now(),
            error_messages=error_messages
        )
        
        # Execute auto-actions if delivery successful and actions configured
        if delivery_result.success and rule.auto_actions:
            self._execute_auto_actions(alert, rule.auto_actions)
        
        # Log delivery attempt
        delivery_time = (time.time() - delivery_start) * 1000
        logger.info(f"Alert delivery: {alert.alert_id} -> {successful_channels} "
                   f"({delivery_time:.1f}ms)")
        
        return delivery_result
    
    def configure_alert_rule(self, rule: AlertRule) -> bool:
        """Add or update alert rule"""
        try:
            with self._lock:
                self.alert_rules[rule.rule_id] = rule
                logger.info(f"Configured alert rule: {rule.rule_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to configure alert rule {rule.rule_id}: {e}")
            return False
    
    def suppress_alerts(self, alert_pattern: str, duration_minutes: int, reason: str) -> None:
        """Temporarily suppress alerts matching pattern"""
        self.suppression_manager.add_suppression_rule(
            pattern=alert_pattern,
            duration_minutes=duration_minutes,
            reason=reason,
            created_by="manual"
        )
        logger.info(f"Suppressed alerts matching '{alert_pattern}' for {duration_minutes} minutes")
    
    def get_alert_summary(self, hours: int = 24) -> AlertSummary:
        """Get alert statistics and trends"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter alerts within time window
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
        
        if not recent_alerts:
            return AlertSummary(
                time_period_hours=hours,
                total_alerts=0,
                alerts_by_severity={},
                alerts_by_rule={},
                most_triggered_rules=[],
                alert_rate_trend="stable",
                avg_alerts_per_hour=0.0,
                resolved_alerts=0,
                avg_resolution_time_minutes=0.0,
                unresolved_alerts=0
            )
        
        # Calculate statistics
        total_alerts = len(recent_alerts)
        
        # Group by severity
        alerts_by_severity = {}
        for alert in recent_alerts:
            alerts_by_severity[alert.severity] = alerts_by_severity.get(alert.severity, 0) + 1
        
        # Group by rule
        alerts_by_rule = {}
        for alert in recent_alerts:
            alerts_by_rule[alert.rule_id] = alerts_by_rule.get(alert.rule_id, 0) + 1
        
        # Most triggered rules
        most_triggered_rules = sorted(
            [(rule_id, count) for rule_id, count in alerts_by_rule.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Calculate trend
        mid_point = cutoff_time + timedelta(hours=hours/2)
        first_half = [a for a in recent_alerts if a.timestamp <= mid_point]
        second_half = [a for a in recent_alerts if a.timestamp > mid_point]
        
        if len(first_half) == 0:
            trend = "increasing"
        elif len(second_half) == 0:
            trend = "decreasing"
        else:
            first_rate = len(first_half) / (hours / 2)
            second_rate = len(second_half) / (hours / 2)
            
            if second_rate > first_rate * 1.2:
                trend = "increasing"
            elif second_rate < first_rate * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        
        # Resolution statistics
        resolved_alerts = len([a for a in recent_alerts if a.status == "resolved"])
        unresolved_alerts = total_alerts - resolved_alerts
        
        # Calculate average resolution time
        resolved_with_time = [
            a for a in recent_alerts 
            if a.status == "resolved" and a.resolution_time
        ]
        
        avg_resolution_time = 0.0
        if resolved_with_time:
            total_resolution_time = sum(
                (a.resolution_time - a.timestamp).total_seconds() / 60
                for a in resolved_with_time
            )
            avg_resolution_time = total_resolution_time / len(resolved_with_time)
        
        return AlertSummary(
            time_period_hours=hours,
            total_alerts=total_alerts,
            alerts_by_severity=alerts_by_severity,
            alerts_by_rule=alerts_by_rule,
            most_triggered_rules=most_triggered_rules,
            alert_rate_trend=trend,
            avg_alerts_per_hour=total_alerts / hours,
            resolved_alerts=resolved_alerts,
            avg_resolution_time_minutes=avg_resolution_time,
            unresolved_alerts=unresolved_alerts
        )
    
    # Built-in alert rule implementations
    def check_collection_rate_alert(self, metrics: SystemMetrics) -> Optional[Alert]:
        """Alert if collection rate drops below threshold"""
        current_rate = metrics.collection_progress.papers_per_minute
        threshold = self.config.collection_rate_threshold
        
        if current_rate < threshold:
            return self._create_alert(
                rule_id="collection_rate_low",
                title="Collection Rate Below Threshold",
                message=f"Collection rate ({current_rate:.1f} papers/min) is below threshold ({threshold} papers/min)",
                current_value=current_rate,
                threshold_value=threshold,
                affected_components=["collection_engine"],
                metrics_context={"collection_progress": metrics.collection_progress.__dict__}
            )
        return None
    
    def check_api_health_alert(self, metrics: SystemMetrics) -> Optional[Alert]:
        """Alert if API health degrades"""
        degraded_apis = []
        
        for api_name, api_data in metrics.api_metrics.items():
            if api_data.health_status in ['degraded', 'critical']:
                degraded_apis.append(api_name)
        
        if degraded_apis:
            return self._create_alert(
                rule_id="api_health_degraded",
                title="API Health Degraded",
                message=f"APIs with degraded health: {', '.join(degraded_apis)}",
                current_value=degraded_apis,
                threshold_value="healthy",
                affected_components=degraded_apis,
                metrics_context={"api_metrics": {k: v.__dict__ for k, v in metrics.api_metrics.items()}}
            )
        return None
    
    def check_error_rate_alert(self, metrics: SystemMetrics) -> Optional[Alert]:
        """Alert if error rate exceeds threshold"""
        if not metrics.api_metrics:
            return None
        
        total_requests = sum(api.requests_made for api in metrics.api_metrics.values())
        total_failures = sum(api.failed_requests for api in metrics.api_metrics.values())
        
        if total_requests == 0:
            return None
        
        error_rate = total_failures / total_requests
        threshold = self.config.api_error_rate_threshold
        
        if error_rate > threshold:
            return self._create_alert(
                rule_id="high_error_rate",
                title="High Error Rate",
                message=f"Error rate ({error_rate:.1%}) exceeds threshold ({threshold:.1%})",
                current_value=error_rate,
                threshold_value=threshold,
                affected_components=["api_layer"],
                metrics_context={"error_rate": error_rate, "total_requests": total_requests}
            )
        return None
    
    def check_memory_usage_alert(self, metrics: SystemMetrics) -> Optional[Alert]:
        """Alert if memory usage too high"""
        current_usage = metrics.system_metrics.memory_usage_percentage
        threshold = self.config.memory_usage_threshold * 100  # Convert to percentage
        
        if current_usage > threshold:
            return self._create_alert(
                rule_id="memory_usage_high",
                title="High Memory Usage",
                message=f"Memory usage ({current_usage:.1f}%) exceeds threshold ({threshold:.1f}%)",
                current_value=current_usage,
                threshold_value=threshold,
                affected_components=["system"],
                metrics_context={"system_metrics": metrics.system_metrics.__dict__}
            )
        return None
    
    def check_venue_stall_alert(self, metrics: SystemMetrics) -> Optional[Alert]:
        """Alert if venue collection stalls"""
        stalled_venues = []
        threshold_minutes = self.config.venue_stall_threshold_minutes
        cutoff_time = datetime.now() - timedelta(minutes=threshold_minutes)
        
        for venue_key, venue_progress in metrics.venue_progress.items():
            if (venue_progress.status == "in_progress" and 
                venue_progress.last_update_time < cutoff_time):
                stalled_venues.append(venue_key)
        
        if stalled_venues:
            return self._create_alert(
                rule_id="venue_collection_stalled",
                title="Venue Collection Stalled",
                message=f"Venues stalled for >{threshold_minutes} minutes: {', '.join(stalled_venues)}",
                current_value=len(stalled_venues),
                threshold_value=0,
                affected_components=stalled_venues,
                metrics_context={"stalled_venues": stalled_venues}
            )
        return None
    
    def _load_alert_rules(self):
        """Load built-in alert rules"""
        for rule_id, rule in BUILT_IN_ALERT_RULES.items():
            self.alert_rules[rule_id] = rule
        
        logger.info(f"Loaded {len(BUILT_IN_ALERT_RULES)} built-in alert rules")
    
    def _setup_default_notification_channels(self):
        """Set up default notification channels"""
        # Console channel
        if self.config.console_notifications:
            console_channel = ConsoleNotificationChannel(use_colors=True, verbose=True)
            self.notification_manager.add_channel(console_channel)
        
        # Dashboard channel (will be set up when dashboard is available)
        if self.config.dashboard_notifications:
            dashboard_channel = DashboardNotificationChannel()
            self.notification_manager.add_channel(dashboard_channel)
        
        # Log channel for persistence
        log_channel = LogNotificationChannel()
        self.notification_manager.add_channel(log_channel)
        
        # Set up routing by severity
        self.notification_manager.set_channel_routing("info", ["console", "log"])
        self.notification_manager.set_channel_routing("warning", ["console", "dashboard", "log"])
        self.notification_manager.set_channel_routing("error", ["console", "dashboard", "log"])
        self.notification_manager.set_channel_routing("critical", ["console", "dashboard", "log"])
    
    def _evaluate_single_rule(self, rule: AlertRule, metrics: SystemMetrics) -> Optional[Alert]:
        """Evaluate a single alert rule"""
        try:
            # Create safe evaluation context
            context = EvaluationContext.create_safe_context(metrics, rule.threshold_value)
            
            # Evaluate condition
            condition_result = eval(rule.condition, {"__builtins__": {}}, context.__dict__)
            
            if condition_result:
                # Check minimum trigger count
                if rule.check_minimum_triggers():
                    return self._create_alert_from_rule(rule, metrics)
            else:
                # Reset trigger history if condition is false
                rule._trigger_history.clear()
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return None
    
    def _create_alert_from_rule(self, rule: AlertRule, metrics: SystemMetrics) -> Alert:
        """Create alert instance from triggered rule"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"
        
        # Extract current value based on rule condition
        current_value = self._extract_current_value(rule, metrics)
        
        # Identify affected components
        affected_components = self._identify_affected_components(rule, metrics)
        
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            timestamp=datetime.now(),
            severity=rule.severity,
            title=rule.rule_name,
            message=self._generate_alert_message(rule, current_value, metrics),
            affected_components=affected_components,
            current_value=current_value,
            threshold_value=rule.threshold_value,
            metrics_context=self._create_metrics_context(metrics, rule),
            recommended_actions=rule.recommended_actions.copy(),
            status="active"
        )
        
        return alert
    
    def _create_alert(self, rule_id: str, title: str, message: str, current_value: Any,
                     threshold_value: Any, affected_components: List[str], 
                     metrics_context: Dict[str, Any]) -> Alert:
        """Helper to create alert instances"""
        rule = self.alert_rules.get(rule_id)
        severity = rule.severity if rule else "warning"
        
        return Alert(
            alert_id=f"{rule_id}_{int(time.time())}",
            rule_id=rule_id,
            timestamp=datetime.now(),
            severity=severity,
            title=title,
            message=message,
            affected_components=affected_components,
            current_value=current_value,
            threshold_value=threshold_value,
            metrics_context=metrics_context,
            recommended_actions=rule.recommended_actions if rule else [],
            status="active"
        )
    
    def _extract_current_value(self, rule: AlertRule, metrics: SystemMetrics) -> Any:
        """Extract current value for display in alert"""
        try:
            # Simple value extraction based on common patterns
            if "papers_per_minute" in rule.condition:
                return metrics.collection_progress.papers_per_minute
            elif "memory_usage_percentage" in rule.condition:
                return metrics.system_metrics.memory_usage_percentage
            elif "api_metrics" in rule.condition:
                return len(metrics.api_metrics)
            else:
                return "N/A"
        except Exception:
            return "N/A"
    
    def _identify_affected_components(self, rule: AlertRule, metrics: SystemMetrics) -> List[str]:
        """Identify affected components based on rule and metrics"""
        components = []
        
        # Basic component identification
        if "collection_progress" in rule.condition:
            components.append("collection_engine")
        if "api_metrics" in rule.condition:
            components.extend(list(metrics.api_metrics.keys()))
        if "system_metrics" in rule.condition:
            components.append("system")
        if "venue_progress" in rule.condition:
            components.append("venue_processor")
        
        return components if components else ["system"]
    
    def _generate_alert_message(self, rule: AlertRule, current_value: Any, metrics: SystemMetrics) -> str:
        """Generate descriptive alert message"""
        base_message = rule.description
        
        if current_value != "N/A":
            if isinstance(current_value, (int, float)):
                base_message += f" (Current: {current_value}, Threshold: {rule.threshold_value})"
            else:
                base_message += f" (Current: {current_value})"
        
        return base_message
    
    def _create_metrics_context(self, metrics: SystemMetrics, rule: AlertRule) -> Dict[str, Any]:
        """Create relevant metrics context for alert"""
        context = {
            "timestamp": metrics.timestamp.isoformat(),
            "rule_id": rule.rule_id
        }
        
        # Add relevant metrics based on rule
        if "collection_progress" in rule.condition:
            context["collection_progress"] = metrics.collection_progress.__dict__
        if "api_metrics" in rule.condition:
            context["api_metrics"] = {k: v.__dict__ for k, v in metrics.api_metrics.items()}
        if "system_metrics" in rule.condition:
            context["system_metrics"] = metrics.system_metrics.__dict__
        
        return context
    
    def _execute_auto_actions(self, alert: Alert, auto_actions: List[str]):
        """Execute automatic actions for alert"""
        for action in auto_actions:
            try:
                if action in self.auto_action_handlers:
                    self.auto_action_handlers[action](alert)
                    logger.info(f"Executed auto-action '{action}' for alert {alert.alert_id}")
                else:
                    logger.warning(f"Auto-action handler not found: {action}")
            except Exception as e:
                logger.error(f"Failed to execute auto-action '{action}': {e}")
    
    def _update_evaluation_stats(self, evaluation_time_ms: float):
        """Update evaluation performance statistics"""
        total = self.evaluation_stats['total_evaluations']
        current_avg = self.evaluation_stats['avg_evaluation_time_ms']
        
        # Calculate running average
        new_avg = ((current_avg * (total - 1)) + evaluation_time_ms) / total
        self.evaluation_stats['avg_evaluation_time_ms'] = new_avg
    
    def register_auto_action_handler(self, action_name: str, handler: callable):
        """Register handler for auto-action"""
        self.auto_action_handlers[action_name] = handler
        logger.info(f"Registered auto-action handler: {action_name}")
    
    def set_dashboard_server(self, dashboard_server):
        """Set dashboard server for dashboard notifications"""
        dashboard_channel = self.notification_manager.channels.get("dashboard")
        if dashboard_channel:
            dashboard_channel.set_dashboard_server(dashboard_server)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get alert system status and statistics"""
        with self._lock:
            return {
                "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
                "total_rules": len(self.alert_rules),
                "evaluation_stats": self.evaluation_stats.copy(),
                "suppression_stats": self.suppression_manager.get_suppression_statistics(),
                "notification_stats": self.notification_manager.get_channel_statistics(),
                "alert_history_size": len(self.alert_history)
            }