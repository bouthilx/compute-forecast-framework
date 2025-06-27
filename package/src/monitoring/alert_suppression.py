"""
Alert Suppression Manager - Manages alert suppression rules and logic.

Handles temporary suppression of alerts based on patterns, duration,
and manual suppression rules to prevent notification spam.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from .alert_structures import Alert, SuppressionRule


logger = logging.getLogger(__name__)


class AlertSuppressionManager:
    """
    Manages alert suppression to prevent notification spam
    
    Handles both automatic suppression (based on alert rules) and
    manual suppression rules created by users or system logic.
    """
    
    def __init__(self):
        self.suppression_rules: Dict[str, SuppressionRule] = {}
        self.auto_suppressed_alerts: Dict[str, datetime] = {}  # rule_id -> suppression_end_time
        self.suppression_stats = {
            'total_suppressions': 0,
            'active_suppressions': 0,
            'suppressed_alerts_count': 0
        }
        self._lock = threading.RLock()
        
    def is_suppressed(self, alert: Alert) -> bool:
        """
        Check if alert should be suppressed
        
        Returns True if the alert matches any active suppression rule
        or is auto-suppressed based on its rule configuration.
        """
        with self._lock:
            # Check auto-suppression first
            if self._is_auto_suppressed(alert):
                return True
            
            # Check manual suppression rules
            if self._matches_suppression_rule(alert):
                self.suppression_stats['suppressed_alerts_count'] += 1
                return True
            
            return False
    
    def add_suppression_rule(self, pattern: str, duration_minutes: int, reason: str, created_by: str = "system") -> str:
        """
        Add new suppression rule
        
        Args:
            pattern: Pattern to match against alert titles/messages/rule_ids
            duration_minutes: How long to suppress matching alerts
            reason: Explanation for the suppression
            created_by: Who created this suppression rule
            
        Returns:
            rule_id: Unique identifier for the suppression rule
        """
        with self._lock:
            rule_id = f"suppression_{int(datetime.now().timestamp())}"
            
            suppression_rule = SuppressionRule(
                pattern=pattern,
                duration_minutes=duration_minutes,
                reason=reason,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=duration_minutes),
                created_by=created_by
            )
            
            self.suppression_rules[rule_id] = suppression_rule
            self.suppression_stats['total_suppressions'] += 1
            
            logger.info(f"Added suppression rule '{pattern}' for {duration_minutes} minutes: {reason}")
            
            return rule_id
    
    def remove_suppression_rule(self, pattern: str) -> bool:
        """
        Remove suppression rule by pattern
        
        Args:
            pattern: Pattern to match for removal
            
        Returns:
            bool: True if rule was found and removed
        """
        with self._lock:
            rules_to_remove = []
            
            for rule_id, rule in self.suppression_rules.items():
                if rule.pattern == pattern:
                    rules_to_remove.append(rule_id)
            
            for rule_id in rules_to_remove:
                del self.suppression_rules[rule_id]
                logger.info(f"Removed suppression rule: {pattern}")
            
            return len(rules_to_remove) > 0
    
    def remove_suppression_rule_by_id(self, rule_id: str) -> bool:
        """Remove suppression rule by ID"""
        with self._lock:
            if rule_id in self.suppression_rules:
                pattern = self.suppression_rules[rule_id].pattern
                del self.suppression_rules[rule_id]
                logger.info(f"Removed suppression rule by ID {rule_id}: {pattern}")
                return True
            return False
    
    def auto_suppress_alert_rule(self, rule_id: str, duration_minutes: int):
        """
        Automatically suppress alerts from a specific rule
        
        This is called when an alert rule triggers and has auto-suppression configured.
        """
        with self._lock:
            suppression_end = datetime.now() + timedelta(minutes=duration_minutes)
            self.auto_suppressed_alerts[rule_id] = suppression_end
            
            logger.info(f"Auto-suppressed rule '{rule_id}' for {duration_minutes} minutes")
    
    def cleanup_expired_suppressions(self):
        """Remove expired suppression rules and auto-suppressions"""
        with self._lock:
            current_time = datetime.now()
            
            # Clean up manual suppression rules
            expired_rules = []
            for rule_id, rule in self.suppression_rules.items():
                if not rule.is_active():
                    expired_rules.append(rule_id)
            
            for rule_id in expired_rules:
                pattern = self.suppression_rules[rule_id].pattern
                del self.suppression_rules[rule_id]
                logger.debug(f"Expired suppression rule: {pattern}")
            
            # Clean up auto-suppressions
            expired_auto = []
            for rule_id, expiry_time in self.auto_suppressed_alerts.items():
                if current_time >= expiry_time:
                    expired_auto.append(rule_id)
            
            for rule_id in expired_auto:
                del self.auto_suppressed_alerts[rule_id]
                logger.debug(f"Expired auto-suppression for rule: {rule_id}")
            
            # Update stats
            self.suppression_stats['active_suppressions'] = (
                len(self.suppression_rules) + len(self.auto_suppressed_alerts)
            )
    
    def get_active_suppressions(self) -> List[Dict[str, any]]:
        """Get list of all active suppression rules"""
        with self._lock:
            self.cleanup_expired_suppressions()
            
            active_suppressions = []
            
            # Manual suppression rules
            for rule_id, rule in self.suppression_rules.items():
                if rule.is_active():
                    active_suppressions.append({
                        'rule_id': rule_id,
                        'type': 'manual',
                        'pattern': rule.pattern,
                        'reason': rule.reason,
                        'created_at': rule.created_at,
                        'expires_at': rule.expires_at,
                        'created_by': rule.created_by,
                        'remaining_minutes': (rule.expires_at - datetime.now()).total_seconds() / 60
                    })
            
            # Auto-suppressions
            for rule_id, expiry_time in self.auto_suppressed_alerts.items():
                if datetime.now() < expiry_time:
                    active_suppressions.append({
                        'rule_id': rule_id,
                        'type': 'auto',
                        'pattern': f"rule:{rule_id}",
                        'reason': 'Auto-suppression after alert triggered',
                        'created_at': expiry_time - timedelta(minutes=60),  # Estimate
                        'expires_at': expiry_time,
                        'created_by': 'system',
                        'remaining_minutes': (expiry_time - datetime.now()).total_seconds() / 60
                    })
            
            return active_suppressions
    
    def get_suppression_statistics(self) -> Dict[str, any]:
        """Get suppression statistics"""
        with self._lock:
            self.cleanup_expired_suppressions()
            
            return {
                'total_suppressions_created': self.suppression_stats['total_suppressions'],
                'active_suppression_rules': len(self.suppression_rules),
                'active_auto_suppressions': len(self.auto_suppressed_alerts),
                'total_active_suppressions': len(self.suppression_rules) + len(self.auto_suppressed_alerts),
                'alerts_suppressed': self.suppression_stats['suppressed_alerts_count']
            }
    
    def _is_auto_suppressed(self, alert: Alert) -> bool:
        """Check if alert is auto-suppressed based on rule configuration"""
        rule_id = alert.rule_id
        
        if rule_id in self.auto_suppressed_alerts:
            suppression_end = self.auto_suppressed_alerts[rule_id]
            if datetime.now() < suppression_end:
                return True
            else:
                # Suppression expired, remove it
                del self.auto_suppressed_alerts[rule_id]
        
        return False
    
    def _matches_suppression_rule(self, alert: Alert) -> bool:
        """Check if alert matches any active manual suppression rule"""
        for rule in self.suppression_rules.values():
            if rule.matches_alert(alert):
                return True
        return False
    
    def suppress_similar_alerts(self, reference_alert: Alert, duration_minutes: int = 60):
        """
        Create suppression rule for alerts similar to the reference alert
        
        This is useful for suppressing cascading alerts that are related
        to the same underlying issue.
        """
        # Create a pattern based on the alert's rule ID and severity
        pattern = f"{reference_alert.rule_id}_{reference_alert.severity}"
        reason = f"Suppressing similar alerts to {reference_alert.alert_id}"
        
        self.add_suppression_rule(
            pattern=pattern,
            duration_minutes=duration_minutes,
            reason=reason,
            created_by="auto_suppression"
        )
    
    def bulk_suppress_by_component(self, component: str, duration_minutes: int, reason: str):
        """
        Suppress all alerts related to a specific component
        
        Useful when a component is known to be having issues and
        you want to suppress related alerts temporarily.
        """
        pattern = component.lower()
        self.add_suppression_rule(
            pattern=pattern,
            duration_minutes=duration_minutes,
            reason=f"Component maintenance: {reason}",
            created_by="system"
        )
    
    def emergency_suppress_all(self, duration_minutes: int = 30):
        """
        Emergency suppression of all alerts
        
        Use sparingly - suppresses ALL alerts for the specified duration.
        Useful during system maintenance or when alert system is malfunctioning.
        """
        self.add_suppression_rule(
            pattern="*",  # Matches everything
            duration_minutes=duration_minutes,
            reason="Emergency suppression - all alerts",
            created_by="emergency"
        )
        
        logger.warning(f"EMERGENCY: Suppressed ALL alerts for {duration_minutes} minutes")


class SuppressionRuleManager:
    """
    Higher-level manager for complex suppression scenarios
    
    Provides intelligent suppression patterns and automatic
    suppression rule creation based on alert patterns.
    """
    
    def __init__(self, suppression_manager: AlertSuppressionManager):
        self.suppression_manager = suppression_manager
        self.alert_patterns = defaultdict(list)  # pattern -> list of recent alerts
        self.pattern_thresholds = {
            'burst_suppression_count': 5,  # Suppress after 5 similar alerts
            'burst_suppression_window_minutes': 10,  # Within 10 minutes
            'burst_suppression_duration_minutes': 30  # Suppress for 30 minutes
        }
        self._lock = threading.RLock()
    
    def analyze_and_suppress(self, alert: Alert) -> bool:
        """
        Analyze alert patterns and create suppression rules if needed
        
        Returns True if a new suppression rule was created
        """
        with self._lock:
            pattern_key = f"{alert.rule_id}_{alert.severity}"
            current_time = datetime.now()
            
            # Add alert to pattern tracking
            self.alert_patterns[pattern_key].append(current_time)
            
            # Clean old alerts from pattern tracking
            cutoff_time = current_time - timedelta(minutes=self.pattern_thresholds['burst_suppression_window_minutes'])
            self.alert_patterns[pattern_key] = [
                t for t in self.alert_patterns[pattern_key] if t > cutoff_time
            ]
            
            # Check if we should create a burst suppression rule
            if len(self.alert_patterns[pattern_key]) >= self.pattern_thresholds['burst_suppression_count']:
                self.suppression_manager.add_suppression_rule(
                    pattern=pattern_key,
                    duration_minutes=self.pattern_thresholds['burst_suppression_duration_minutes'],
                    reason=f"Auto-suppression: {self.pattern_thresholds['burst_suppression_count']} similar alerts in {self.pattern_thresholds['burst_suppression_window_minutes']} minutes",
                    created_by="pattern_analysis"
                )
                
                # Clear the pattern to start fresh
                self.alert_patterns[pattern_key] = []
                
                logger.info(f"Created burst suppression rule for pattern: {pattern_key}")
                return True
            
            return False
    
    def create_maintenance_suppression(self, component: str, start_time: datetime, end_time: datetime, reason: str):
        """Create a suppression rule for scheduled maintenance"""
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        if start_time <= datetime.now():
            # Maintenance is starting now or already started
            self.suppression_manager.bulk_suppress_by_component(
                component=component,
                duration_minutes=duration_minutes,
                reason=f"Scheduled maintenance: {reason}"
            )
        else:
            # Schedule for future - would need a scheduler implementation
            logger.info(f"Scheduled maintenance suppression for {component} from {start_time} to {end_time}")
    
    def get_suppression_recommendations(self, recent_alerts: List[Alert]) -> List[Dict[str, any]]:
        """
        Analyze recent alerts and provide suppression recommendations
        
        Returns list of recommended suppression rules based on alert patterns
        """
        recommendations = []
        
        # Group alerts by rule and severity
        alert_groups = defaultdict(list)
        for alert in recent_alerts:
            key = f"{alert.rule_id}_{alert.severity}"
            alert_groups[key].append(alert)
        
        # Analyze each group for suppression opportunities
        for group_key, alerts in alert_groups.items():
            if len(alerts) >= 3:  # Suggest suppression for groups with 3+ alerts
                rule_id, severity = group_key.rsplit('_', 1)
                
                # Calculate time span of alerts
                timestamps = [alert.timestamp for alert in alerts]
                time_span = (max(timestamps) - min(timestamps)).total_seconds() / 60
                
                if time_span <= 60:  # All within an hour
                    recommendations.append({
                        'pattern': group_key,
                        'alert_count': len(alerts),
                        'time_span_minutes': time_span,
                        'recommended_duration_minutes': 30,
                        'reason': f"Multiple {severity} alerts from {rule_id} rule",
                        'confidence': 'high' if len(alerts) >= 5 else 'medium'
                    })
        
        return recommendations