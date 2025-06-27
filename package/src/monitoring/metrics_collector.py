"""
MetricsCollector - Collects system metrics from all components.
Provides real-time metrics gathering with <2 second collection time requirement.
"""

import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from .dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    VenueProgressMetrics,
    MetricsBuffer
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects comprehensive system metrics from all collection components.
    
    Performance requirement: Complete metrics collection within 2 seconds.
    Thread-safe design for concurrent access.
    """
    
    def __init__(self, collection_interval_seconds: int = 5):
        self.collection_interval = collection_interval_seconds
        self.metrics_buffer = MetricsBuffer(max_size=1000)
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Component references (injected)
        self.venue_engine = None
        self.state_manager = None
        self.data_processors = None
        self.api_health_monitors = {}
        
        # Metrics state
        self._start_time = datetime.now()
        self._last_network_stats = self._get_network_stats()
    
    def set_venue_engine(self, venue_engine) -> None:
        """Set venue collection engine reference"""
        with self._lock:
            self.venue_engine = venue_engine
    
    def set_state_manager(self, state_manager) -> None:
        """Set state manager reference"""
        with self._lock:
            self.state_manager = state_manager
    
    def set_data_processors(self, processors) -> None:
        """Set data processors reference"""
        with self._lock:
            self.data_processors = processors
    
    def add_api_health_monitor(self, api_name: str, monitor) -> None:
        """Add API health monitor"""
        with self._lock:
            self.api_health_monitors[api_name] = monitor
    
    def start_collection(self) -> None:
        """Start metrics collection in background thread"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True,
                name="MetricsCollector"
            )
            self._collection_thread.start()
            logger.info("Started metrics collection")
    
    def stop_collection(self) -> None:
        """Stop metrics collection"""
        with self._lock:
            self._running = False
            
        if self._collection_thread:
            self._collection_thread.join(timeout=5.0)
            logger.info("Stopped metrics collection")
    
    def collect_current_metrics(self) -> SystemMetrics:
        """
        Collect current system metrics from all components.
        Must complete within 2 seconds per requirement.
        """
        start_time = time.time()
        
        try:
            # Collect metrics in parallel where possible
            collection_progress = self._collect_collection_progress()
            api_metrics = self._collect_api_metrics()
            processing_metrics = self._collect_processing_metrics()
            system_metrics = self._collect_system_resources()
            state_metrics = self._collect_state_metrics()
            venue_progress = self._collect_venue_progress()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                collection_progress=collection_progress,
                api_metrics=api_metrics,
                processing_metrics=processing_metrics,
                system_metrics=system_metrics,
                state_metrics=state_metrics,
                venue_progress=venue_progress
            )
            
            # Add to buffer
            self.metrics_buffer.add_metrics(metrics)
            
            collection_time = time.time() - start_time
            if collection_time > 2.0:
                logger.warning(f"Metrics collection took {collection_time:.2f}s (requirement: <2s)")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            # Return empty metrics on error
            return self._create_empty_metrics()
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        return self.metrics_buffer.get_latest_metrics()
    
    def get_metrics_history(self, count: int = 100) -> List[SystemMetrics]:
        """Get recent metrics history"""
        return self.metrics_buffer.get_metrics_history(count)
    
    def _collection_loop(self) -> None:
        """Main collection loop running in background"""
        while self._running:
            try:
                self.collect_current_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                time.sleep(1)  # Short delay on error
    
    def _collect_collection_progress(self) -> CollectionProgressMetrics:
        """Collect overall collection progress metrics"""
        progress = CollectionProgressMetrics()
        
        if self.venue_engine:
            try:
                # Get stats from venue engine if available
                stats = getattr(self.venue_engine, 'get_collection_stats', lambda: {})()
                progress.total_papers_collected = stats.get('total_papers', 0)
                progress.venues_completed = stats.get('venues_completed', 0)
                progress.venues_in_progress = stats.get('venues_in_progress', 0)
                progress.venues_remaining = stats.get('venues_remaining', 0)
                progress.total_venues = stats.get('total_venues', 0)
                
                # Calculate papers per minute
                session_duration = (datetime.now() - self._start_time).total_seconds() / 60
                if session_duration > 0:
                    progress.papers_per_minute = progress.total_papers_collected / session_duration
                    progress.session_duration_minutes = session_duration
                
            except Exception as e:
                logger.debug(f"Could not collect venue engine stats: {e}")
        
        return progress
    
    def _collect_api_metrics(self) -> Dict[str, APIMetrics]:
        """Collect API performance metrics"""
        api_metrics = {}
        
        for api_name, monitor in self.api_health_monitors.items():
            try:
                health_status = monitor.get_health_status(api_name)
                
                metrics = APIMetrics(
                    api_name=api_name,
                    success_rate=health_status.success_rate,
                    avg_response_time_ms=health_status.avg_response_time_ms,
                    health_status=health_status.status,
                    last_request_time=health_status.last_successful_request
                )
                
                api_metrics[api_name] = metrics
                
            except Exception as e:
                logger.debug(f"Could not collect API metrics for {api_name}: {e}")
        
        return api_metrics
    
    def _collect_processing_metrics(self) -> ProcessingMetrics:
        """Collect data processing pipeline metrics"""
        metrics = ProcessingMetrics()
        
        if self.data_processors:
            try:
                stats = getattr(self.data_processors, 'get_processing_stats', lambda: {})()
                metrics.papers_processed = stats.get('papers_processed', 0)
                metrics.papers_filtered = stats.get('papers_filtered', 0)
                metrics.papers_normalized = stats.get('papers_normalized', 0)
                metrics.papers_deduplicated = stats.get('papers_deduplicated', 0)
                metrics.processing_queue_size = stats.get('queue_size', 0)
                metrics.processing_errors = stats.get('processing_errors', 0)
                
                # Calculate rates
                if metrics.papers_processed > 0:
                    session_time = (datetime.now() - self._start_time).total_seconds() / 60
                    if session_time > 0:
                        metrics.processing_rate_per_minute = metrics.papers_processed / session_time
                        
                    metrics.filter_rate = metrics.papers_filtered / metrics.papers_processed
                    if metrics.papers_processed > 0:
                        metrics.deduplication_rate = metrics.papers_deduplicated / metrics.papers_processed
                        
            except Exception as e:
                logger.debug(f"Could not collect processing metrics: {e}")
        
        return metrics
    
    def _collect_system_resources(self) -> SystemResourceMetrics:
        """Collect system resource usage metrics"""
        metrics = SystemResourceMetrics()
        
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.memory_usage_mb = memory.used / (1024 * 1024)
            metrics.memory_usage_percent = memory.percent
            
            # CPU usage
            metrics.cpu_usage_percent = psutil.cpu_percent()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.disk_usage_mb = disk.used / (1024 * 1024)
            metrics.disk_free_mb = disk.free / (1024 * 1024)
            
            # Network stats
            network_stats = self._get_network_stats()
            metrics.network_bytes_sent = network_stats['bytes_sent']
            metrics.network_bytes_received = network_stats['bytes_recv']
            
            # Process stats
            process = psutil.Process()
            metrics.active_threads = process.num_threads()
            metrics.open_file_descriptors = process.num_fds()
            
        except Exception as e:
            logger.debug(f"Could not collect system metrics: {e}")
        
        return metrics
    
    def _collect_state_metrics(self) -> StateManagementMetrics:
        """Collect state management metrics"""
        metrics = StateManagementMetrics()
        
        if self.state_manager:
            try:
                stats = getattr(self.state_manager, 'get_state_stats', lambda: {})()
                metrics.total_checkpoints = stats.get('total_checkpoints', 0)
                metrics.last_checkpoint_time = stats.get('last_checkpoint_time')
                metrics.checkpoint_size_mb = stats.get('checkpoint_size_mb', 0.0)
                metrics.state_validation_errors = stats.get('validation_errors', 0)
                metrics.backup_count = stats.get('backup_count', 0)
                
                # Calculate checkpoint rate
                session_time = (datetime.now() - self._start_time).total_seconds() / 3600  # hours
                if session_time > 0:
                    metrics.checkpoints_per_hour = metrics.total_checkpoints / session_time
                    
            except Exception as e:
                logger.debug(f"Could not collect state metrics: {e}")
        
        return metrics
    
    def _collect_venue_progress(self) -> Dict[str, VenueProgressMetrics]:
        """Collect venue-specific progress metrics"""
        venue_progress = {}
        
        if self.venue_engine:
            try:
                venues = getattr(self.venue_engine, 'get_venue_progress', lambda: {})()
                
                for venue_key, venue_data in venues.items():
                    progress = VenueProgressMetrics(
                        venue_name=venue_data.get('venue_name', venue_key),
                        year=venue_data.get('year', 0),
                        status=venue_data.get('status', 'not_started'),
                        papers_collected=venue_data.get('papers_collected', 0),
                        target_papers=venue_data.get('target_papers', 50),
                        start_time=venue_data.get('start_time'),
                        estimated_completion=venue_data.get('estimated_completion'),
                        api_source=venue_data.get('api_source', ''),
                        error_count=venue_data.get('error_count', 0),
                        last_activity=venue_data.get('last_activity')
                    )
                    
                    # Calculate progress percentage
                    if progress.target_papers > 0:
                        progress.progress_percent = min(100.0, 
                            (progress.papers_collected / progress.target_papers) * 100)
                    
                    venue_progress[venue_key] = progress
                    
            except Exception as e:
                logger.debug(f"Could not collect venue progress: {e}")
        
        return venue_progress
    
    def _get_network_stats(self) -> Dict[str, int]:
        """Get current network statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
        except:
            return {'bytes_sent': 0, 'bytes_recv': 0}
    
    def _create_empty_metrics(self) -> SystemMetrics:
        """Create empty metrics structure on error"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(),
            api_metrics={},
            processing_metrics=ProcessingMetrics(),
            system_metrics=SystemResourceMetrics(),
            state_metrics=StateManagementMetrics(),
            venue_progress={}
        )