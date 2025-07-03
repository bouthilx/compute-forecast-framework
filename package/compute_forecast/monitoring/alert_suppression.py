"""
<<<<<<< HEAD
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

=======
Alert suppression managers for Issue #12 Intelligent Alerting System.
Provides intelligent alert suppression with pattern matching and burst detection.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import re

from .alert_structures import (
    Alert, AlertSeverity, AlertStatus, SuppressionRule,
    BUILT_IN_SUPPRESSION_RULES
)
>>>>>>> 79c0ec5 (Implement Intelligent Alerting System (Issue #12) - Complete Implementation)

logger = logging.getLogger(__name__)


class AlertSuppressionManager:
    """
<<<<<<< HEAD
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
=======
    Manages alert suppression with intelligent pattern detection.
    
    Features:
    - Manual and automatic suppression rules
    - Burst detection and prevention
    - Pattern-based suppression
    - Time-based suppression windows
    - Emergency override for critical alerts
    """
    
    def __init__(self):
        # Suppression rules
        self.suppression_rules: Dict[str, SuppressionRule] = {}
        self._load_built_in_rules()
        
        # Suppression state
        self.suppressed_patterns: Dict[str, datetime] = {}  # pattern -> expiry time
        self.alert_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.burst_tracking: Dict[str, List[datetime]] = defaultdict(list)
        
        # Emergency and maintenance
        self.emergency_mode = False
        self.maintenance_mode = False
        self.global_suppression = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance tracking
        self._suppression_stats = {
            'total_evaluations': 0,
            'suppressed_alerts': 0,
            'burst_suppressions': 0,
            'pattern_suppressions': 0,
            'manual_suppressions': 0
        }
        
        logger.info("AlertSuppressionManager initialized")
    
    def should_suppress_alert(self, alert: Alert) -> bool:
        """
        Check if alert should be suppressed based on all configured rules.
        Returns True if alert should be suppressed.
        """
        with self._lock:
            self._suppression_stats['total_evaluations'] += 1
            
            # Check global suppression
            if self.global_suppression:
                logger.debug(f"Alert {alert.alert_id} suppressed: global suppression enabled")
                self._suppression_stats['suppressed_alerts'] += 1
                return True
            
            # Check maintenance mode (allow critical alerts)
            if self.maintenance_mode and alert.severity != AlertSeverity.CRITICAL:
                logger.debug(f"Alert {alert.alert_id} suppressed: maintenance mode")
                self._suppression_stats['suppressed_alerts'] += 1
                return True
            
            # Emergency mode allows only critical alerts
            if self.emergency_mode and alert.severity != AlertSeverity.CRITICAL:
                logger.debug(f"Alert {alert.alert_id} suppressed: emergency mode")
                self._suppression_stats['suppressed_alerts'] += 1
                return True
            
            # Check suppression rules
            for rule_id, rule in self.suppression_rules.items():
                if not rule.enabled:
                    continue
                
                if self._should_suppress_by_rule(alert, rule):
                    logger.debug(f"Alert {alert.alert_id} suppressed by rule: {rule_id}")
                    self._suppression_stats['suppressed_alerts'] += 1
                    self._update_suppression_tracking(alert, rule)
                    return True
            
            # Check for burst detection
            if self._is_burst_alert(alert):
                logger.debug(f"Alert {alert.alert_id} suppressed: burst detected")
                self._suppression_stats['burst_suppressions'] += 1
                self._suppression_stats['suppressed_alerts'] += 1
>>>>>>> 79c0ec5 (Implement Intelligent Alerting System (Issue #12) - Complete Implementation)
                return True
            
            return False
    
<<<<<<< HEAD
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
=======
    def add_suppression_rule(self, rule: SuppressionRule) -> None:
        """Add or update a suppression rule"""
        with self._lock:
            self.suppression_rules[rule.rule_id] = rule
            logger.info(f"Added suppression rule: {rule.rule_id}")
    
    def remove_suppression_rule(self, rule_id: str) -> bool:
        """Remove a suppression rule"""
        with self._lock:
            if rule_id in self.suppression_rules:
                del self.suppression_rules[rule_id]
                logger.info(f"Removed suppression rule: {rule_id}")
                return True
            return False
    
    def enable_maintenance_mode(self, duration_minutes: int = 60) -> None:
        """Enable maintenance mode suppression"""
        with self._lock:
            self.maintenance_mode = True
            # Set up auto-disable (would need a timer in production)
            logger.info(f"Maintenance mode enabled for {duration_minutes} minutes")
    
    def disable_maintenance_mode(self) -> None:
        """Disable maintenance mode suppression"""
        with self._lock:
            self.maintenance_mode = False
            logger.info("Maintenance mode disabled")
    
    def enable_emergency_mode(self) -> None:
        """Enable emergency mode (critical alerts only)"""
        with self._lock:
            self.emergency_mode = True
            logger.warning("Emergency mode enabled - only critical alerts will be sent")
    
    def disable_emergency_mode(self) -> None:
        """Disable emergency mode"""
        with self._lock:
            self.emergency_mode = False
            logger.info("Emergency mode disabled")
    
    def suppress_pattern(self, pattern: str, duration_minutes: int = 30) -> None:
        """Manually suppress alerts matching a pattern"""
        with self._lock:
            expiry_time = datetime.now() + timedelta(minutes=duration_minutes)
            self.suppressed_patterns[pattern] = expiry_time
            self._suppression_stats['manual_suppressions'] += 1
            logger.info(f"Manually suppressed pattern '{pattern}' for {duration_minutes} minutes")
    
    def unsuppress_pattern(self, pattern: str) -> bool:
        """Remove pattern suppression"""
        with self._lock:
            if pattern in self.suppressed_patterns:
                del self.suppressed_patterns[pattern]
                logger.info(f"Removed suppression for pattern: {pattern}")
                return True
            return False
    
    def get_suppression_status(self) -> Dict[str, any]:
        """Get current suppression system status"""
        with self._lock:
            # Clean expired patterns
            self._cleanup_expired_patterns()
            
            return {
                'global_suppression': self.global_suppression,
                'maintenance_mode': self.maintenance_mode,
                'emergency_mode': self.emergency_mode,
                'active_rules': len([r for r in self.suppression_rules.values() if r.enabled]),
                'total_rules': len(self.suppression_rules),
                'suppressed_patterns': len(self.suppressed_patterns),
                'stats': self._suppression_stats.copy()
            }
    
    def get_suppression_stats(self) -> Dict[str, any]:
        """Get detailed suppression statistics"""
        with self._lock:
            total_evals = self._suppression_stats['total_evaluations']
            suppressed = self._suppression_stats['suppressed_alerts']
            
            return {
                'total_evaluations': total_evals,
                'suppressed_alerts': suppressed,
                'suppression_rate': (suppressed / max(total_evals, 1)) * 100,
                'burst_suppressions': self._suppression_stats['burst_suppressions'],
                'pattern_suppressions': self._suppression_stats['pattern_suppressions'],
                'manual_suppressions': self._suppression_stats['manual_suppressions'],
                'active_suppression_rules': len([r for r in self.suppression_rules.values() if r.enabled])
            }
    
    def _load_built_in_rules(self) -> None:
        """Load built-in suppression rules"""
        for rule_id, rule in BUILT_IN_SUPPRESSION_RULES.items():
            self.suppression_rules[rule_id] = rule
        
        logger.info(f"Loaded {len(BUILT_IN_SUPPRESSION_RULES)} built-in suppression rules")
    
    def _should_suppress_by_rule(self, alert: Alert, rule: SuppressionRule) -> bool:
        """Check if alert should be suppressed by specific rule"""
        try:
            # Check if rule pattern matches alert
            if not self._rule_matches_alert(alert, rule):
                return False
            
            # Check severity threshold
            if alert.severity.value != AlertSeverity.CRITICAL.value and rule.escalation_override:
                pass  # Allow non-critical alerts to be evaluated
            elif self._severity_exceeds_threshold(alert.severity, rule.severity_threshold):
                return False  # Don't suppress alerts above threshold
            
            # Check rate limiting (alerts per window)
            if self._exceeds_rate_limit(alert, rule):
                return True
            
            # Check burst detection
            if self._exceeds_burst_threshold(alert, rule):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating suppression rule {rule.rule_id}: {e}")
            return False
    
    def _rule_matches_alert(self, alert: Alert, rule: SuppressionRule) -> bool:
        """Check if suppression rule pattern matches alert"""
        if not rule.pattern_matching:
            return True
        
        try:
            # Match against rule name
            if re.search(rule.alert_rule_pattern, alert.rule_name, re.IGNORECASE):
                return True
            
            # Match against rule ID
            if re.search(rule.alert_rule_pattern, alert.rule_id, re.IGNORECASE):
                return True
            
            # If similar_context_only is enabled, check context similarity
            if rule.similar_context_only:
                return self._has_similar_context(alert, rule)
            
            return False
            
        except re.error as e:
            logger.error(f"Invalid regex pattern in suppression rule {rule.rule_id}: {e}")
            return False
    
    def _severity_exceeds_threshold(self, alert_severity: AlertSeverity, threshold: AlertSeverity) -> bool:
        """Check if alert severity exceeds suppression threshold"""
        severity_levels = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3
        }
        
        return severity_levels.get(alert_severity, 0) > severity_levels.get(threshold, 0)
    
    def _exceeds_rate_limit(self, alert: Alert, rule: SuppressionRule) -> bool:
        """Check if alert exceeds rate limit for the rule"""
        window_start = datetime.now() - timedelta(minutes=rule.time_window_minutes)
        
        # Count recent alerts for this rule pattern
        rule_key = f"{rule.rule_id}:{alert.rule_id}"
        recent_alerts = [
            timestamp for timestamp in self.alert_counts[rule_key]
            if timestamp >= window_start
        ]
        
        return len(recent_alerts) >= rule.max_alerts_per_window
    
    def _exceeds_burst_threshold(self, alert: Alert, rule: SuppressionRule) -> bool:
        """Check if alert is part of a burst"""
        if rule.burst_threshold <= 0:
            return False
        
        burst_window_start = datetime.now() - timedelta(seconds=rule.burst_window_seconds)
        rule_key = f"{rule.rule_id}:{alert.rule_id}"
        
        # Count recent burst alerts
        recent_burst = [
            timestamp for timestamp in self.burst_tracking[rule_key]
            if timestamp >= burst_window_start
        ]
        
        return len(recent_burst) >= rule.burst_threshold
    
    def _has_similar_context(self, alert: Alert, rule: SuppressionRule) -> bool:
        """Check if alert has similar context to recently suppressed alerts"""
        # This would compare alert context with recent alerts
        # For now, just return True if similar_context_only is enabled
        return True
    
    def _is_burst_alert(self, alert: Alert) -> bool:
        """Check if alert is part of a burst using general burst detection"""
        burst_window = timedelta(seconds=60)  # 1 minute burst window
        burst_threshold = 5  # 5 alerts in 1 minute = burst
        
        window_start = datetime.now() - burst_window
        rule_key = alert.rule_id
        
        # Count recent alerts for this rule
        if rule_key in self.alert_counts:
            recent_count = sum(
                1 for timestamp in self.alert_counts[rule_key]
                if timestamp >= window_start
            )
            return recent_count >= burst_threshold
        
        return False
    
    def _update_suppression_tracking(self, alert: Alert, rule: SuppressionRule) -> None:
        """Update tracking data for suppressed alert"""
        current_time = datetime.now()
        rule_key = f"{rule.rule_id}:{alert.rule_id}"
        
        # Update alert counts
        self.alert_counts[rule_key].append(current_time)
        
        # Update burst tracking
        self.burst_tracking[rule_key].append(current_time)
        
        # Clean old burst tracking data
        burst_cutoff = current_time - timedelta(seconds=rule.burst_window_seconds)
        self.burst_tracking[rule_key] = [
            timestamp for timestamp in self.burst_tracking[rule_key]
            if timestamp >= burst_cutoff
        ]
    
    def _cleanup_expired_patterns(self) -> None:
        """Remove expired manual pattern suppressions"""
        current_time = datetime.now()
        expired_patterns = [
            pattern for pattern, expiry in self.suppressed_patterns.items()
            if current_time >= expiry
        ]
        
        for pattern in expired_patterns:
            del self.suppressed_patterns[pattern]
            logger.debug(f"Expired suppression pattern: {pattern}")
>>>>>>> 79c0ec5 (Implement Intelligent Alerting System (Issue #12) - Complete Implementation)


class SuppressionRuleManager:
    """
<<<<<<< HEAD
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
=======
    Manages suppression rules with intelligent analysis and recommendations.
    
    Features:
    - Dynamic rule optimization
    - Pattern analysis
    - Suppression effectiveness tracking
    - Automatic rule suggestions
    """
    
    def __init__(self):
        self.rule_effectiveness: Dict[str, Dict[str, any]] = {}
        self.pattern_analysis: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        
        logger.info("SuppressionRuleManager initialized")
    
    def analyze_suppression_patterns(self, alerts: List[Alert]) -> Dict[str, any]:
        """Analyze alert patterns to suggest suppression rules"""
        with self._lock:
            pattern_frequency = defaultdict(int)
            burst_patterns = defaultdict(list)
            
            # Analyze alert patterns
            for alert in alerts:
                # Count by rule
                pattern_frequency[alert.rule_id] += 1
                
                # Track timing for burst detection
                burst_patterns[alert.rule_id].append(alert.timestamp)
            
            # Identify burst patterns
            burst_candidates = {}
            for rule_id, timestamps in burst_patterns.items():
                if len(timestamps) >= 3:  # Minimum for burst analysis
                    sorted_times = sorted(timestamps)
                    # Check for rapid succession
                    rapid_alerts = 0
                    for i in range(1, len(sorted_times)):
                        if (sorted_times[i] - sorted_times[i-1]).total_seconds() < 60:
                            rapid_alerts += 1
                    
                    if rapid_alerts >= 2:
                        burst_candidates[rule_id] = {
                            'total_alerts': len(timestamps),
                            'rapid_succession_count': rapid_alerts,
                            'burst_severity': rapid_alerts / len(timestamps)
                        }
            
            return {
                'frequent_patterns': dict(pattern_frequency),
                'burst_candidates': burst_candidates,
                'recommendations': self._generate_rule_recommendations(pattern_frequency, burst_candidates)
            }
    
    def track_rule_effectiveness(self, rule_id: str, suppressed_count: int, 
                               total_evaluated: int) -> None:
        """Track effectiveness of suppression rules"""
        with self._lock:
            if rule_id not in self.rule_effectiveness:
                self.rule_effectiveness[rule_id] = {
                    'suppressed_count': 0,
                    'total_evaluated': 0,
                    'effectiveness_rate': 0.0,
                    'last_updated': datetime.now()
                }
            
            stats = self.rule_effectiveness[rule_id]
            stats['suppressed_count'] += suppressed_count
            stats['total_evaluated'] += total_evaluated
            stats['effectiveness_rate'] = (
                stats['suppressed_count'] / max(stats['total_evaluated'], 1)
            ) * 100
            stats['last_updated'] = datetime.now()
    
    def get_rule_recommendations(self) -> List[Dict[str, any]]:
        """Get recommendations for new suppression rules"""
        with self._lock:
            recommendations = []
            
            # Analyze current effectiveness
            for rule_id, stats in self.rule_effectiveness.items():
                if stats['effectiveness_rate'] < 50 and stats['total_evaluated'] > 10:
                    recommendations.append({
                        'type': 'optimize_rule',
                        'rule_id': rule_id,
                        'reason': f"Low effectiveness rate: {stats['effectiveness_rate']:.1f}%",
                        'suggestion': 'Consider adjusting rule parameters or conditions'
                    })
            
            # Add pattern-based recommendations
            for pattern, frequency in self.pattern_analysis.items():
                if frequency > 20:  # High frequency pattern
                    recommendations.append({
                        'type': 'new_suppression_rule',
                        'pattern': pattern,
                        'reason': f"High frequency pattern: {frequency} occurrences",
                        'suggestion': f'Create suppression rule for pattern: {pattern}'
                    })
            
            return recommendations
    
    def _generate_rule_recommendations(self, patterns: Dict[str, int], 
                                     bursts: Dict[str, Dict]) -> List[Dict[str, any]]:
        """Generate specific rule recommendations based on analysis"""
        recommendations = []
        
        # High frequency rules
        for rule_id, count in patterns.items():
            if count > 10:
                recommendations.append({
                    'type': 'frequency_suppression',
                    'rule_id': rule_id,
                    'alert_count': count,
                    'suggestion': f'Consider rate limiting for rule {rule_id} (triggered {count} times)'
                })
        
        # Burst patterns
        for rule_id, burst_info in bursts.items():
            if burst_info['burst_severity'] > 0.5:
                recommendations.append({
                    'type': 'burst_suppression',
                    'rule_id': rule_id,
                    'burst_severity': burst_info['burst_severity'],
                    'suggestion': f'Create burst suppression for rule {rule_id} (high burst activity)'
                })
>>>>>>> 79c0ec5 (Implement Intelligent Alerting System (Issue #12) - Complete Implementation)
        
        return recommendations