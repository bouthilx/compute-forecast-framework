"""
Smart alert rules for the paper collection system.
Defines intelligent conditions for API health, collection progress, and system monitoring.
"""

import logging
from typing import Dict, Any, List, Callable
from datetime import datetime, timedelta

from .alerting_engine import AlertRule, AlertSeverity, EscalationRule

logger = logging.getLogger(__name__)


class AlertRuleFactory:
    """Factory for creating predefined alert rules"""
    
    @staticmethod
    def create_default_rules() -> List[AlertRule]:
        """Create default set of alert rules for paper collection system"""
        rules = []
        
        # API Health Rules
        rules.extend(AlertRuleFactory.create_api_health_rules())
        
        # Collection Progress Rules
        rules.extend(AlertRuleFactory.create_collection_progress_rules())
        
        # System Resource Rules
        rules.extend(AlertRuleFactory.create_system_resource_rules())
        
        # Error Detection Rules
        rules.extend(AlertRuleFactory.create_error_detection_rules())
        
        # State Management Rules
        rules.extend(AlertRuleFactory.create_state_management_rules())
        
        return rules
    
    @staticmethod
    def create_api_health_rules() -> List[AlertRule]:
        """Create API health monitoring rules"""
        rules = []
        
        # Critical: API completely down
        rules.append(AlertRule(
            id="api_down_critical",
            name="API Service Down",
            description="One or more API services are completely unavailable",
            condition=AlertRuleFactory._condition_api_down,
            severity=AlertSeverity.CRITICAL,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=1,
            escalation_rules=[
                EscalationRule(
                    escalation_delay_minutes=5,
                    additional_channels=["webhook"],
                    max_escalations=3
                )
            ],
            metadata={"source_component": "api_health"}
        ))
        
        # High: API success rate below 80%
        rules.append(AlertRule(
            id="api_success_rate_low",
            name="API Success Rate Low",
            description="API success rate has dropped below acceptable threshold",
            condition=AlertRuleFactory._condition_api_success_rate_low,
            severity=AlertSeverity.HIGH,
            channels=["slack", "dashboard"],
            rate_limit_minutes=10,
            metadata={"source_component": "api_health"}
        ))
        
        # Medium: API response time high
        rules.append(AlertRule(
            id="api_response_time_high",
            name="API Response Time High",
            description="API response times are higher than normal",
            condition=AlertRuleFactory._condition_api_response_time_high,
            severity=AlertSeverity.MEDIUM,
            channels=["dashboard"],
            rate_limit_minutes=15,
            metadata={"source_component": "api_health"}
        ))
        
        # Medium: Rate limit warnings
        rules.append(AlertRule(
            id="api_rate_limit_warning",
            name="API Rate Limit Warning",
            description="Approaching API rate limits",
            condition=AlertRuleFactory._condition_api_rate_limit_warning,
            severity=AlertSeverity.MEDIUM,
            channels=["dashboard"],
            rate_limit_minutes=30,
            metadata={"source_component": "api_health"}
        ))
        
        return rules
    
    @staticmethod
    def create_collection_progress_rules() -> List[AlertRule]:
        """Create collection progress monitoring rules"""
        rules = []
        
        # High: Collection stalled
        rules.append(AlertRule(
            id="collection_stalled",
            name="Collection Progress Stalled",
            description="Paper collection has stalled - no progress in 30 minutes",
            condition=AlertRuleFactory._condition_collection_stalled,
            severity=AlertSeverity.HIGH,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=15,
            metadata={"source_component": "collection_progress"}
        ))
        
        # Medium: Collection rate below target
        rules.append(AlertRule(
            id="collection_rate_low",
            name="Collection Rate Below Target",
            description="Paper collection rate is below target threshold",
            condition=AlertRuleFactory._condition_collection_rate_low,
            severity=AlertSeverity.MEDIUM,
            channels=["dashboard"],
            rate_limit_minutes=20,
            metadata={"source_component": "collection_progress"}
        ))
        
        # Low: Venue collection completed
        rules.append(AlertRule(
            id="venue_completed",
            name="Venue Collection Completed",
            description="A venue collection has completed successfully",
            condition=AlertRuleFactory._condition_venue_completed,
            severity=AlertSeverity.LOW,
            channels=["dashboard"],
            rate_limit_minutes=1,
            metadata={"source_component": "collection_progress"}
        ))
        
        return rules
    
    @staticmethod
    def create_system_resource_rules() -> List[AlertRule]:
        """Create system resource monitoring rules"""
        rules = []
        
        # Critical: Memory usage very high
        rules.append(AlertRule(
            id="memory_critical",
            name="Memory Usage Critical",
            description="System memory usage is critically high",
            condition=AlertRuleFactory._condition_memory_critical,
            severity=AlertSeverity.CRITICAL,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=5,
            escalation_rules=[
                EscalationRule(
                    escalation_delay_minutes=10,
                    additional_channels=["webhook"],
                    max_escalations=2
                )
            ],
            metadata={"source_component": "system_resources"}
        ))
        
        # High: CPU usage very high
        rules.append(AlertRule(
            id="cpu_high",
            name="CPU Usage High",
            description="System CPU usage is consistently high",
            condition=AlertRuleFactory._condition_cpu_high,
            severity=AlertSeverity.HIGH,
            channels=["slack", "dashboard"],
            rate_limit_minutes=10,
            metadata={"source_component": "system_resources"}
        ))
        
        # High: Disk space low
        rules.append(AlertRule(
            id="disk_space_low",
            name="Disk Space Low",
            description="Available disk space is running low",
            condition=AlertRuleFactory._condition_disk_space_low,
            severity=AlertSeverity.HIGH,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=30,
            metadata={"source_component": "system_resources"}
        ))
        
        return rules
    
    @staticmethod
    def create_error_detection_rules() -> List[AlertRule]:
        """Create error detection and monitoring rules"""
        rules = []
        
        # High: Processing errors increasing
        rules.append(AlertRule(
            id="processing_errors_high",
            name="Processing Errors High",
            description="Data processing error rate is increasing",
            condition=AlertRuleFactory._condition_processing_errors_high,
            severity=AlertSeverity.HIGH,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=15,
            metadata={"source_component": "data_processing"}
        ))
        
        # Medium: State validation errors
        rules.append(AlertRule(
            id="state_validation_errors",
            name="State Validation Errors",
            description="State management validation errors detected",
            condition=AlertRuleFactory._condition_state_validation_errors,
            severity=AlertSeverity.MEDIUM,
            channels=["dashboard"],
            rate_limit_minutes=20,
            metadata={"source_component": "state_management"}
        ))
        
        return rules
    
    @staticmethod
    def create_state_management_rules() -> List[AlertRule]:
        """Create state management monitoring rules"""
        rules = []
        
        # High: Checkpoint failures
        rules.append(AlertRule(
            id="checkpoint_failures",
            name="Checkpoint Save Failures",
            description="Multiple checkpoint save failures detected",
            condition=AlertRuleFactory._condition_checkpoint_failures,
            severity=AlertSeverity.HIGH,
            channels=["email", "slack", "dashboard"],
            rate_limit_minutes=10,
            metadata={"source_component": "state_management"}
        ))
        
        # Medium: Checkpoint size growing
        rules.append(AlertRule(
            id="checkpoint_size_large",
            name="Checkpoint Size Large",
            description="Checkpoint files are growing larger than expected",
            condition=AlertRuleFactory._condition_checkpoint_size_large,
            severity=AlertSeverity.MEDIUM,
            channels=["dashboard"],
            rate_limit_minutes=60,
            metadata={"source_component": "state_management"}
        ))
        
        return rules
    
    # Condition functions for alert rules
    
    @staticmethod
    def _condition_api_down(metrics: Dict[str, Any]) -> bool:
        """Check if any API is completely down"""
        api_metrics = metrics.get('api_metrics', {})
        for api_name, api_data in api_metrics.items():
            if hasattr(api_data, 'health_status') and api_data.health_status == 'unhealthy':
                return True
            if hasattr(api_data, 'success_rate') and api_data.success_rate == 0.0:
                return True
        return False
    
    @staticmethod
    def _condition_api_success_rate_low(metrics: Dict[str, Any]) -> bool:
        """Check if API success rate is below 80%"""
        api_metrics = metrics.get('api_metrics', {})
        for api_name, api_data in api_metrics.items():
            if hasattr(api_data, 'success_rate') and api_data.success_rate < 0.8:
                return True
        return False
    
    @staticmethod
    def _condition_api_response_time_high(metrics: Dict[str, Any]) -> bool:
        """Check if API response time is high (>5000ms)"""
        api_metrics = metrics.get('api_metrics', {})
        for api_name, api_data in api_metrics.items():
            if hasattr(api_data, 'avg_response_time_ms') and api_data.avg_response_time_ms > 5000:
                return True
        return False
    
    @staticmethod
    def _condition_api_rate_limit_warning(metrics: Dict[str, Any]) -> bool:
        """Check if approaching API rate limits"""
        # This would need specific rate limit metrics
        # For now, we'll use a placeholder
        return False
    
    @staticmethod
    def _condition_collection_stalled(metrics: Dict[str, Any]) -> bool:
        """Check if collection has stalled (no progress in 30+ minutes)"""
        collection_progress = metrics.get('collection_progress')
        if not collection_progress:
            return False
        
        # Check if papers per minute is 0 and session has been running for more than 30 minutes
        if (hasattr(collection_progress, 'papers_per_minute') and 
            collection_progress.papers_per_minute == 0 and
            hasattr(collection_progress, 'session_duration_minutes') and
            collection_progress.session_duration_minutes > 30):
            return True
        return False
    
    @staticmethod
    def _condition_collection_rate_low(metrics: Dict[str, Any]) -> bool:
        """Check if collection rate is below target (20 papers/minute)"""
        collection_progress = metrics.get('collection_progress')
        if not collection_progress:
            return False
        
        if (hasattr(collection_progress, 'papers_per_minute') and 
            collection_progress.papers_per_minute < 20 and
            hasattr(collection_progress, 'session_duration_minutes') and
            collection_progress.session_duration_minutes > 5):  # Give it some time to ramp up
            return True
        return False
    
    @staticmethod
    def _condition_venue_completed(metrics: Dict[str, Any]) -> bool:
        """Check if a venue has just completed"""
        venue_progress = metrics.get('venue_progress', {})
        for venue_key, venue_data in venue_progress.items():
            if (hasattr(venue_data, 'status') and 
                venue_data.status == 'completed' and
                hasattr(venue_data, 'last_activity')):
                # Check if completed recently (within last 2 minutes)
                if venue_data.last_activity:
                    age_minutes = (datetime.now() - venue_data.last_activity).total_seconds() / 60
                    if age_minutes <= 2:
                        return True
        return False
    
    @staticmethod
    def _condition_memory_critical(metrics: Dict[str, Any]) -> bool:
        """Check if memory usage is critical (>90%)"""
        system_metrics = metrics.get('system_metrics')
        if not system_metrics:
            return False
        
        return (hasattr(system_metrics, 'memory_usage_percent') and 
                system_metrics.memory_usage_percent > 90)
    
    @staticmethod
    def _condition_cpu_high(metrics: Dict[str, Any]) -> bool:
        """Check if CPU usage is high (>85%)"""
        system_metrics = metrics.get('system_metrics')
        if not system_metrics:
            return False
        
        return (hasattr(system_metrics, 'cpu_usage_percent') and 
                system_metrics.cpu_usage_percent > 85)
    
    @staticmethod
    def _condition_disk_space_low(metrics: Dict[str, Any]) -> bool:
        """Check if disk space is low (<1GB free)"""
        system_metrics = metrics.get('system_metrics')
        if not system_metrics:
            return False
        
        return (hasattr(system_metrics, 'disk_free_mb') and 
                system_metrics.disk_free_mb < 1024)  # Less than 1GB
    
    @staticmethod
    def _condition_processing_errors_high(metrics: Dict[str, Any]) -> bool:
        """Check if processing error rate is high"""
        processing_metrics = metrics.get('processing_metrics')
        if not processing_metrics:
            return False
        
        if (hasattr(processing_metrics, 'processing_errors') and 
            hasattr(processing_metrics, 'papers_processed')):
            if processing_metrics.papers_processed > 0:
                error_rate = processing_metrics.processing_errors / processing_metrics.papers_processed
                return error_rate > 0.1  # More than 10% error rate
        return False
    
    @staticmethod
    def _condition_state_validation_errors(metrics: Dict[str, Any]) -> bool:
        """Check for state validation errors"""
        state_metrics = metrics.get('state_metrics')
        if not state_metrics:
            return False
        
        return (hasattr(state_metrics, 'state_validation_errors') and 
                state_metrics.state_validation_errors > 0)
    
    @staticmethod
    def _condition_checkpoint_failures(metrics: Dict[str, Any]) -> bool:
        """Check for checkpoint save failures"""
        # This would need specific checkpoint failure metrics
        # For now, we'll use a placeholder
        return False
    
    @staticmethod
    def _condition_checkpoint_size_large(metrics: Dict[str, Any]) -> bool:
        """Check if checkpoint size is larger than expected (>100MB)"""
        state_metrics = metrics.get('state_metrics')
        if not state_metrics:
            return False
        
        return (hasattr(state_metrics, 'checkpoint_size_mb') and 
                state_metrics.checkpoint_size_mb > 100)


class CustomAlertRule:
    """Helper for creating custom alert rules"""
    
    @staticmethod
    def create_metric_threshold_rule(
        rule_id: str,
        name: str,
        description: str,
        metric_path: str,
        threshold: float,
        comparison: str = "greater_than",
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        channels: List[str] = None
    ) -> AlertRule:
        """
        Create a custom alert rule based on metric threshold
        
        Args:
            metric_path: Dot notation path to metric (e.g., 'system_metrics.memory_usage_percent')
            threshold: Threshold value
            comparison: 'greater_than', 'less_than', 'equals', 'not_equals'
        """
        if channels is None:
            channels = ["dashboard"]
        
        def condition_func(metrics: Dict[str, Any]) -> bool:
            """Dynamic condition function based on metric path and threshold"""
            try:
                # Navigate to metric value using dot notation
                value = metrics
                for key in metric_path.split('.'):
                    if hasattr(value, key):
                        value = getattr(value, key)
                    elif isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return False
                
                # Apply comparison
                if comparison == "greater_than":
                    return value > threshold
                elif comparison == "less_than":
                    return value < threshold
                elif comparison == "equals":
                    return value == threshold
                elif comparison == "not_equals":
                    return value != threshold
                else:
                    return False
                    
            except Exception as e:
                logger.debug(f"Error evaluating custom rule {rule_id}: {e}")
                return False
        
        return AlertRule(
            id=rule_id,
            name=name,
            description=description,
            condition=condition_func,
            severity=severity,
            channels=channels,
            metadata={"custom_rule": True, "metric_path": metric_path}
        )
    
    @staticmethod
    def create_composite_rule(
        rule_id: str,
        name: str,
        description: str,
        conditions: List[Callable[[Dict[str, Any]], bool]],
        logic: str = "AND",
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        channels: List[str] = None
    ) -> AlertRule:
        """
        Create composite alert rule with multiple conditions
        
        Args:
            conditions: List of condition functions
            logic: 'AND' or 'OR' logic for combining conditions
        """
        if channels is None:
            channels = ["dashboard"]
        
        def composite_condition(metrics: Dict[str, Any]) -> bool:
            """Composite condition combining multiple conditions"""
            try:
                results = [condition(metrics) for condition in conditions]
                
                if logic.upper() == "AND":
                    return all(results)
                elif logic.upper() == "OR":
                    return any(results)
                else:
                    return False
                    
            except Exception as e:
                logger.debug(f"Error evaluating composite rule {rule_id}: {e}")
                return False
        
        return AlertRule(
            id=rule_id,
            name=name,
            description=description,
            condition=composite_condition,
            severity=severity,
            channels=channels,
            metadata={"composite_rule": True, "logic": logic}
        )