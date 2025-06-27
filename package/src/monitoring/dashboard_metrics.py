"""
Core data structures for dashboard metrics and monitoring.
Defines comprehensive metrics hierarchy for real-time collection monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from collections import deque
import threading


@dataclass
class CollectionProgressMetrics:
    """Metrics for overall collection progress"""
    total_papers_collected: int = 0
    papers_per_minute: float = 0.0
    estimated_completion_time: Optional[datetime] = None
    venues_completed: int = 0
    venues_in_progress: int = 0
    venues_remaining: int = 0
    total_venues: int = 0
    current_year: Optional[int] = None
    session_duration_minutes: float = 0.0


@dataclass  
class APIMetrics:
    """Metrics for individual API performance"""
    api_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    requests_per_minute: float = 0.0
    rate_limit_hits: int = 0
    last_request_time: Optional[datetime] = None
    health_status: Literal["healthy", "degraded", "critical", "offline"] = "healthy"


@dataclass
class ProcessingMetrics:
    """Metrics for data processing pipeline"""
    papers_processed: int = 0
    papers_filtered: int = 0
    papers_normalized: int = 0
    papers_deduplicated: int = 0
    processing_rate_per_minute: float = 0.0
    filter_rate: float = 0.0
    deduplication_rate: float = 0.0
    processing_queue_size: int = 0
    processing_errors: int = 0


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics"""
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_mb: float = 0.0
    disk_free_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0
    active_threads: int = 0
    open_file_descriptors: int = 0


@dataclass
class StateManagementMetrics:
    """State management and checkpoint metrics"""
    total_checkpoints: int = 0
    last_checkpoint_time: Optional[datetime] = None
    checkpoint_size_mb: float = 0.0
    checkpoints_per_hour: float = 0.0
    recovery_time_seconds: float = 0.0
    state_validation_errors: int = 0
    backup_count: int = 0


@dataclass
class VenueProgressMetrics:
    """Progress metrics for individual venue collection"""
    venue_name: str
    year: int
    status: Literal["not_started", "in_progress", "completed", "failed", "paused"] = "not_started"
    papers_collected: int = 0
    target_papers: int = 50
    progress_percent: float = 0.0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    api_source: str = ""
    error_count: int = 0
    last_activity: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """Top-level system metrics container"""
    timestamp: datetime
    collection_progress: CollectionProgressMetrics
    api_metrics: Dict[str, APIMetrics]
    processing_metrics: ProcessingMetrics
    system_metrics: SystemResourceMetrics
    state_metrics: StateManagementMetrics
    venue_progress: Dict[str, VenueProgressMetrics]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'collection_progress': self.collection_progress.__dict__,
            'api_metrics': {k: v.__dict__ for k, v in self.api_metrics.items()},
            'processing_metrics': self.processing_metrics.__dict__,
            'system_metrics': self.system_metrics.__dict__,
            'state_metrics': self.state_metrics.__dict__,
            'venue_progress': {k: v.__dict__ for k, v in self.venue_progress.items()}
        }


class MetricsBuffer:
    """Thread-safe buffer for storing historical metrics"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()
    
    def add_metrics(self, metrics: SystemMetrics) -> None:
        """Add metrics to buffer"""
        with self._lock:
            self._buffer.append(metrics)
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        with self._lock:
            return self._buffer[-1] if self._buffer else None
    
    def get_metrics_history(self, count: int = 100) -> List[SystemMetrics]:
        """Get recent metrics history"""
        with self._lock:
            return list(self._buffer)[-count:]
    
    def get_metrics_since(self, since: datetime) -> List[SystemMetrics]:
        """Get metrics since specified time"""
        with self._lock:
            return [m for m in self._buffer if m.timestamp >= since]
    
    def clear(self) -> None:
        """Clear all metrics"""
        with self._lock:
            self._buffer.clear()
    
    def size(self) -> int:
        """Get current buffer size"""
        with self._lock:
            return len(self._buffer)