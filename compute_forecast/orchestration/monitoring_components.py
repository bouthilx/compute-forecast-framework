"""
Simple monitoring components for Agent Delta functionality.
Includes metrics collection, dashboard, and alerting.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass 
class SystemMetrics:
    timestamp: datetime
    session_id: str
    papers_collected: int
    papers_per_minute: float
    api_calls_made: int
    api_success_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_components: List[str] = field(default_factory=list)
    errors_count: int = 0

class SimpleMetricsCollector:
    """Simple metrics collection system"""
    
    def __init__(self, collection_interval: int = 5):
        self.collection_interval = collection_interval  # seconds
        self.session_metrics: Dict[str, List[SystemMetrics]] = defaultdict(list)
        self.is_collecting: Dict[str, bool] = {}
        self.start_times: Dict[str, datetime] = {}
        
    def start_session_monitoring(self, session_id: str):
        """Start metrics collection for session"""
        logger.info(f"Starting metrics collection for session {session_id}")
        self.is_collecting[session_id] = True
        self.start_times[session_id] = datetime.now()
        
    def stop_session_monitoring(self, session_id: str):
        """Stop metrics collection for session"""
        logger.info(f"Stopping metrics collection for session {session_id}")
        self.is_collecting[session_id] = False
        
    def resume_session_monitoring(self, session_id: str):
        """Resume metrics collection for recovered session"""
        logger.info(f"Resuming metrics collection for session {session_id}")
        self.is_collecting[session_id] = True
        
    def collect_current_metrics(self, session_id: str = "default") -> SystemMetrics:
        """Collect current system metrics"""
        now = datetime.now()
        
        # Calculate papers per minute
        papers_per_minute = 0.0
        if session_id in self.start_times:
            duration_minutes = (now - self.start_times[session_id]).total_seconds() / 60
            if duration_minutes > 0:
                total_papers = sum(m.papers_collected for m in self.session_metrics[session_id])
                papers_per_minute = total_papers / duration_minutes
        
        metrics = SystemMetrics(
            timestamp=now,
            session_id=session_id,
            papers_collected=0,  # Will be updated by caller
            papers_per_minute=papers_per_minute,
            api_calls_made=0,    # Simplified
            api_success_rate=0.95,  # Mock value
            memory_usage_mb=100.0,  # Mock value
            cpu_usage_percent=25.0,  # Mock value
            active_components=["agent_alpha", "agent_beta", "agent_gamma", "agent_delta"]
        )
        
        # Store metrics
        self.session_metrics[session_id].append(metrics)
        
        return metrics
    
    def record_venue_completion(self, venue_metrics: Dict[str, Any]):
        """Record completion of venue collection"""
        session_id = venue_metrics.get('session_id', 'default')
        
        # Update metrics with venue data
        if session_id in self.session_metrics and self.session_metrics[session_id]:
            latest_metrics = self.session_metrics[session_id][-1]
            latest_metrics.papers_collected += venue_metrics.get('papers_collected', 0)
        
        logger.info(f"Recorded venue completion: {venue_metrics}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of session metrics"""
        if session_id not in self.session_metrics:
            return {}
        
        metrics_list = self.session_metrics[session_id]
        if not metrics_list:
            return {}
        
        total_papers = sum(m.papers_collected for m in metrics_list)
        avg_papers_per_minute = sum(m.papers_per_minute for m in metrics_list) / len(metrics_list)
        
        return {
            'session_id': session_id,
            'total_papers': total_papers,
            'avg_papers_per_minute': avg_papers_per_minute,
            'metrics_collected': len(metrics_list),
            'session_duration_minutes': (
                (metrics_list[-1].timestamp - metrics_list[0].timestamp).total_seconds() / 60
                if len(metrics_list) > 1 else 0
            )
        }

class SimpleDashboard:
    """Simple dashboard for collection monitoring"""
    
    def __init__(self):
        self.active_dashboards: Dict[str, Dict[str, Any]] = {}
        
    def create_session_dashboard(self, session_id: str):
        """Create dashboard for session"""
        logger.info(f"Creating dashboard for session {session_id}")
        
        self.active_dashboards[session_id] = {
            'session_id': session_id,
            'created_at': datetime.now(),
            'status': 'active',
            'last_update': datetime.now(),
            'papers_collected': 0,
            'venues_completed': 0,
            'current_venue': None
        }
    
    def restore_session_dashboard(self, session_id: str):
        """Restore dashboard for recovered session"""
        logger.info(f"Restoring dashboard for session {session_id}")
        
        if session_id not in self.active_dashboards:
            self.create_session_dashboard(session_id)
        
        self.active_dashboards[session_id]['status'] = 'restored'
        self.active_dashboards[session_id]['last_update'] = datetime.now()
    
    def close_session_dashboard(self, session_id: str):
        """Close dashboard for session"""
        logger.info(f"Closing dashboard for session {session_id}")
        
        if session_id in self.active_dashboards:
            self.active_dashboards[session_id]['status'] = 'closed'
            self.active_dashboards[session_id]['closed_at'] = datetime.now()
    
    def update_progress(self, session_id: str, papers_collected: int, current_venue: str = None):
        """Update dashboard progress"""
        if session_id in self.active_dashboards:
            dashboard = self.active_dashboards[session_id]
            dashboard['papers_collected'] = papers_collected
            dashboard['last_update'] = datetime.now()
            if current_venue:
                dashboard['current_venue'] = current_venue
    
    def get_dashboard_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current dashboard data"""
        return self.active_dashboards.get(session_id)
    
    def list_active_dashboards(self) -> List[str]:
        """List all active dashboard session IDs"""
        return [
            session_id for session_id, data in self.active_dashboards.items()
            if data.get('status') == 'active'
        ]

class SimpleAlertSystem:
    """Simple alerting system for collection monitoring"""
    
    def __init__(self):
        self.alert_rules = {
            'low_collection_rate': {'threshold': 5.0, 'enabled': True},  # papers per minute
            'high_error_rate': {'threshold': 0.1, 'enabled': True},      # 10% error rate
            'api_failure': {'threshold': 0.5, 'enabled': True},          # 50% API success rate
            'long_venue_time': {'threshold': 1800, 'enabled': True},     # 30 minutes per venue
        }
        self.active_alerts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.alert_history: List[Dict[str, Any]] = []
    
    def check_alerts(self, session_id: str, metrics: SystemMetrics) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        new_alerts = []
        
        # Low collection rate
        if (self.alert_rules['low_collection_rate']['enabled'] and 
            metrics.papers_per_minute < self.alert_rules['low_collection_rate']['threshold']):
            alert = {
                'type': 'low_collection_rate',
                'severity': 'warning',
                'message': f"Low collection rate: {metrics.papers_per_minute:.1f} papers/min",
                'timestamp': datetime.now(),
                'session_id': session_id
            }
            new_alerts.append(alert)
        
        # High error rate
        if (self.alert_rules['high_error_rate']['enabled'] and 
            metrics.errors_count > 0):
            error_rate = metrics.errors_count / max(metrics.papers_collected, 1)
            if error_rate > self.alert_rules['high_error_rate']['threshold']:
                alert = {
                    'type': 'high_error_rate',
                    'severity': 'critical',
                    'message': f"High error rate: {error_rate:.1%}",
                    'timestamp': datetime.now(),
                    'session_id': session_id
                }
                new_alerts.append(alert)
        
        # API failure
        if (self.alert_rules['api_failure']['enabled'] and 
            metrics.api_success_rate < self.alert_rules['api_failure']['threshold']):
            alert = {
                'type': 'api_failure',
                'severity': 'critical',
                'message': f"API success rate low: {metrics.api_success_rate:.1%}",
                'timestamp': datetime.now(),
                'session_id': session_id
            }
            new_alerts.append(alert)
        
        # Store and log new alerts
        for alert in new_alerts:
            self.active_alerts[session_id].append(alert)
            self.alert_history.append(alert)
            logger.warning(f"ALERT [{alert['severity']}]: {alert['message']}")
        
        return new_alerts
    
    def clear_alerts(self, session_id: str, alert_types: List[str] = None):
        """Clear alerts for session"""
        if session_id not in self.active_alerts:
            return
        
        if alert_types is None:
            # Clear all alerts
            self.active_alerts[session_id] = []
        else:
            # Clear specific alert types
            self.active_alerts[session_id] = [
                alert for alert in self.active_alerts[session_id]
                if alert['type'] not in alert_types
            ]
    
    def get_active_alerts(self, session_id: str) -> List[Dict[str, Any]]:
        """Get active alerts for session"""
        return self.active_alerts.get(session_id, [])
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts"""
        total_alerts = sum(len(alerts) for alerts in self.active_alerts.values())
        critical_alerts = sum(
            len([a for a in alerts if a['severity'] == 'critical'])
            for alerts in self.active_alerts.values()
        )
        
        return {
            'total_active_alerts': total_alerts,
            'critical_alerts': critical_alerts,
            'sessions_with_alerts': len([s for s in self.active_alerts.values() if s]),
            'alert_history_count': len(self.alert_history)
        }