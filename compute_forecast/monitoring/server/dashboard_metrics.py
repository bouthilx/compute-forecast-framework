"""
Data structures for dashboard metrics and system monitoring.

Defines all metrics classes required for real-time collection monitoring.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from collections import deque
import psutil
import threading


@dataclass
class CollectionProgressMetrics:
    """Metrics for overall collection progress"""

    session_id: Optional[str]
    total_venues: int
    completed_venues: int
    in_progress_venues: int
    failed_venues: int

    # Paper statistics
    papers_collected: int
    papers_per_minute: float
    estimated_total_papers: int
    completion_percentage: float

    # Time estimates
    session_duration_minutes: float
    estimated_remaining_minutes: float
    estimated_completion_time: Optional[datetime]

    # Additional fields from incoming version
    venues_remaining: int = 0
    current_year: Optional[int] = None


@dataclass
class APIMetrics:
    """Metrics for individual API performance"""

    api_name: str
    health_status: str  # APIHealthStatus from models.py

    # Request statistics
    requests_made: int
    successful_requests: int
    failed_requests: int
    success_rate: float

    # Performance
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float

    # Rate limiting
    rate_limit_status: Dict[str, Any]
    requests_throttled: int

    # Papers collected
    papers_collected: int
    papers_per_request: float

    # Additional fields from incoming version
    requests_per_minute: float = 0.0
    rate_limit_hits: int = 0
    last_request_time: Optional[datetime] = None


@dataclass
class ProcessingMetrics:
    """Metrics for data processing operations"""

    # Venue normalization
    venues_normalized: int
    normalization_accuracy: float
    normalization_rate_per_second: float

    # Deduplication
    papers_deduplicated: int
    duplicates_removed: int
    deduplication_rate: float
    deduplication_confidence: float

    # Citation filtering
    papers_analyzed: int
    papers_above_threshold: int
    breakthrough_papers_found: int
    filtering_rate_per_second: float

    # Additional fields from incoming version
    papers_processed: int = 0
    papers_filtered: int = 0
    papers_normalized: int = 0
    processing_rate_per_minute: float = 0.0
    filter_rate: float = 0.0
    processing_queue_size: int = 0
    processing_errors: int = 0


@dataclass
class SystemResourceMetrics:
    """System resource utilization metrics"""

    # Memory
    memory_usage_percentage: float
    memory_used_mb: float
    memory_available_mb: float

    # CPU
    cpu_usage_percentage: float
    cpu_count: int

    # Network
    network_bytes_sent: int
    network_bytes_received: int
    network_connections: int

    # Disk
    disk_usage_percentage: float
    disk_free_gb: float

    # Process specific
    process_memory_mb: float
    process_cpu_percentage: float
    thread_count: int

    # Additional fields from incoming version
    disk_usage_mb: float = 0.0
    disk_free_mb: float = 0.0
    active_threads: int = 0
    open_file_descriptors: int = 0

    @classmethod
    def collect_current(cls) -> "SystemResourceMetrics":
        """Collect current system resource metrics"""
        # Memory stats
        memory = psutil.virtual_memory()

        # CPU stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        # Network stats
        network = psutil.net_io_counters()
        network_connections = len(psutil.net_connections())

        # Disk stats
        disk = psutil.disk_usage("/")

        # Process stats
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        process_cpu = process.cpu_percent()
        thread_count = process.num_threads()

        return cls(
            memory_usage_percentage=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            cpu_usage_percentage=cpu_percent,
            cpu_count=cpu_count or 1,
            network_bytes_sent=network.bytes_sent,
            network_bytes_received=network.bytes_recv,
            network_connections=network_connections,
            disk_usage_percentage=(disk.used / disk.total) * 100,
            disk_free_gb=disk.free / 1024 / 1024 / 1024,
            process_memory_mb=process_memory,
            process_cpu_percentage=process_cpu,
            thread_count=thread_count,
            disk_usage_mb=disk.used / 1024 / 1024,
            disk_free_mb=disk.free / 1024 / 1024,
            active_threads=thread_count,
            open_file_descriptors=process.num_fds()
            if hasattr(process, "num_fds")
            else 0,
        )


@dataclass
class StateManagementMetrics:
    """Metrics for state management and checkpointing"""

    # Checkpoint frequency
    checkpoints_created: int
    last_checkpoint_time: Optional[datetime]
    checkpoint_creation_rate_per_hour: float

    # Recovery status
    recovery_possible: bool
    last_recovery_time: Optional[datetime]
    recovery_success_rate: float

    # State size
    state_size_mb: float
    checkpoint_size_mb: float

    # Performance
    checkpoint_creation_time_ms: float
    state_save_time_ms: float

    # Additional fields from incoming version
    recovery_time_seconds: float = 0.0
    state_validation_errors: int = 0
    backup_count: int = 0


@dataclass
class VenueProgressMetrics:
    """Progress metrics for individual venue collection"""

    venue_name: str
    year: int
    status: Literal["not_started", "in_progress", "completed", "failed", "paused"]
    papers_collected: int
    target_papers: int
    completion_percentage: float
    last_update_time: datetime
    collection_duration_minutes: float
    estimated_remaining_minutes: float

    # Additional fields from incoming version
    progress_percent: float = 0.0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    api_source: str = ""
    error_count: int = 0
    last_activity: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """Complete system metrics snapshot"""

    timestamp: datetime

    # Collection progress
    collection_progress: CollectionProgressMetrics

    # API health and performance
    api_metrics: Dict[str, APIMetrics]

    # Data processing metrics
    processing_metrics: ProcessingMetrics

    # System resource metrics
    system_metrics: SystemResourceMetrics

    # State management metrics
    state_metrics: StateManagementMetrics

    # Individual venue progress
    venue_progress: Dict[str, VenueProgressMetrics]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "collection_progress": self.collection_progress.__dict__,
            "api_metrics": {k: v.__dict__ for k, v in self.api_metrics.items()},
            "processing_metrics": self.processing_metrics.__dict__,
            "system_metrics": self.system_metrics.__dict__,
            "state_metrics": self.state_metrics.__dict__,
            "venue_progress": {k: v.__dict__ for k, v in self.venue_progress.items()},
        }


@dataclass
class MetricsSummary:
    """Aggregated metrics over time window"""

    time_period_minutes: int
    start_time: datetime
    end_time: datetime

    # Aggregated statistics
    avg_collection_rate: float
    peak_collection_rate: float
    total_papers_collected: int

    # API performance summary
    api_success_rates: Dict[str, float]
    api_avg_response_times: Dict[str, float]

    # System performance summary
    avg_memory_usage: float
    peak_memory_usage: float
    avg_cpu_usage: float
    peak_cpu_usage: float

    # Processing summary
    total_venues_completed: int
    total_processing_time_minutes: float
    processing_throughput: float


@dataclass
class DashboardStatus:
    """Dashboard server status"""

    is_running: bool
    connected_clients: int
    port: int
    uptime_seconds: float
    messages_sent: int
    last_broadcast_time: Optional[datetime]
    server_start_time: datetime

    def update_broadcast_stats(self, message_count: int = 1):
        """Update broadcast statistics"""
        self.messages_sent += message_count
        self.last_broadcast_time = datetime.now()

    def get_uptime_minutes(self) -> float:
        """Get uptime in minutes"""
        return (datetime.now() - self.server_start_time).total_seconds() / 60


class MetricsBuffer:
    """Thread-safe buffer for storing metrics history"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def add_metrics(self, metrics: SystemMetrics) -> None:
        """Add new metrics to buffer"""
        with self._lock:
            self._buffer.append(metrics)

    @property
    def metrics(self) -> List[SystemMetrics]:
        """Get all metrics in buffer"""
        with self._lock:
            return list(self._buffer)

    def get_recent_metrics(self, count: int = 10) -> List[SystemMetrics]:
        """Get most recent metrics"""
        with self._lock:
            return list(self._buffer)[-count:] if self._buffer else []

    def get_metrics_in_window(self, minutes: int) -> List[SystemMetrics]:
        """Get metrics within time window"""
        with self._lock:
            cutoff_time = datetime.now().timestamp() - (minutes * 60)
            return [m for m in self._buffer if m.timestamp.timestamp() > cutoff_time]

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics (alias for compatibility)"""
        return self.get_current_metrics()

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

    def __len__(self) -> int:
        """Get current buffer size (for len() built-in)"""
        return self.size()
