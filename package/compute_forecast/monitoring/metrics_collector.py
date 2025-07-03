"""
<<<<<<< HEAD
MetricsCollector - Collects system metrics from all components for dashboard monitoring.

Gathers metrics from venue collection engine, state management, data processing,
and system resources to provide comprehensive monitoring data.
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict

from .dashboard_metrics import (
    SystemMetrics, CollectionProgressMetrics, APIMetrics, ProcessingMetrics,
    SystemResourceMetrics, StateManagementMetrics, VenueProgressMetrics,
    MetricsSummary, MetricsBuffer
)
from ..data.models import APIHealthStatus

=======
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
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
<<<<<<< HEAD
    Collects metrics from all system components for dashboard monitoring
    
    Runs in separate thread to avoid impacting collection performance,
    gathering metrics every 5 seconds from all active components.
=======
    Collects comprehensive system metrics from all collection components.
    
    Performance requirement: Complete metrics collection within 2 seconds.
    Thread-safe design for concurrent access.
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
    """
    
    def __init__(self, collection_interval_seconds: int = 5):
        self.collection_interval = collection_interval_seconds
<<<<<<< HEAD
        self.is_collecting = False
        self.collection_thread: Optional[threading.Thread] = None
        self.metrics_buffer = MetricsBuffer(max_size=1000)
        
        # Component references (set during start_collection)
        self.venue_engine = None
        self.state_manager = None
        self.data_processors = None
        
        # Session tracking
        self.session_start_time = datetime.now()
        self.session_id = None
        
        # Collection statistics
        self.collection_stats = {
            'metrics_collected': 0,
            'collection_errors': 0,
            'last_collection_time': None,
            'collection_failures': []
        }
        
        self._lock = threading.RLock()
        
    def start_collection(self, venue_engine, state_manager, data_processors: Dict[str, Any]) -> None:
        """
        Start automatic metrics collection from all system components
        
        REQUIREMENTS:
        - Must collect metrics every 5 seconds
        - Must not impact performance of collection process
        - Must handle component failures gracefully
        - Must run in separate thread
        """
        with self._lock:
            if self.is_collecting:
                logger.warning("Metrics collection already running")
                return
            
            # Store component references
            self.venue_engine = venue_engine
            self.state_manager = state_manager
            self.data_processors = data_processors or {}
            
            # Initialize session
            self.session_start_time = datetime.now()
            self.session_id = f"session_{int(self.session_start_time.timestamp())}"
            
            # Start collection thread
            self.is_collecting = True
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                name="MetricsCollector",
                daemon=True
            )
            self.collection_thread.start()
            
            logger.info(f"Started metrics collection with {self.collection_interval}s interval")
    
    def stop_collection(self) -> None:
        """Stop metrics collection gracefully"""
        with self._lock:
            if not self.is_collecting:
                return
            
            self.is_collecting = False
            
            # Wait for collection thread to finish
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=10)
            
=======
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
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            logger.info("Stopped metrics collection")
    
    def collect_current_metrics(self) -> SystemMetrics:
        """
<<<<<<< HEAD
        Collect current system metrics from all components
        
        REQUIREMENTS:
        - Must complete within 2 seconds
        - Must handle component unavailability
        - Must include all required metric categories
        """
        collection_start = time.time()
        
        try:
            # Collect all metric components
            collection_progress = self._collect_collection_progress()
            api_metrics = self._collect_api_metrics()
            processing_metrics = self._collect_processing_metrics()
            system_metrics = SystemResourceMetrics.collect_current()
            state_metrics = self._collect_state_metrics()
            venue_progress = self._collect_venue_progress()
            
            # Create complete metrics snapshot
=======
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
            
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                collection_progress=collection_progress,
                api_metrics=api_metrics,
                processing_metrics=processing_metrics,
                system_metrics=system_metrics,
                state_metrics=state_metrics,
                venue_progress=venue_progress
            )
            
<<<<<<< HEAD
            collection_time = time.time() - collection_start
            
            # Check performance requirement
            if collection_time > 2.0:
                logger.warning(f"Metrics collection took {collection_time:.2f}s (>2s limit)")
            
            # Update collection statistics
            with self._lock:
                self.collection_stats['metrics_collected'] += 1
                self.collection_stats['last_collection_time'] = datetime.now()
=======
            # Add to buffer
            self.metrics_buffer.add_metrics(metrics)
            
            collection_time = time.time() - start_time
            if collection_time > 2.0:
                logger.warning(f"Metrics collection took {collection_time:.2f}s (requirement: <2s)")
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            
            return metrics
            
        except Exception as e:
<<<<<<< HEAD
            with self._lock:
                self.collection_stats['collection_errors'] += 1
                self.collection_stats['collection_failures'].append({
                    'timestamp': datetime.now(),
                    'error': str(e)
                })
            
            logger.error(f"Failed to collect metrics: {e}")
            raise
    
    def get_metrics_summary(self, time_window_minutes: int = 30) -> MetricsSummary:
        """Get aggregated metrics over time window"""
        metrics_in_window = self.metrics_buffer.get_metrics_in_window(time_window_minutes)
        
        if not metrics_in_window:
            # Return default summary if no data
            return self._create_default_summary(time_window_minutes)
        
        start_time = min(m.timestamp for m in metrics_in_window)
        end_time = max(m.timestamp for m in metrics_in_window)
        
        # Calculate aggregated statistics
        collection_rates = [m.collection_progress.papers_per_minute for m in metrics_in_window]
        memory_usages = [m.system_metrics.memory_usage_percentage for m in metrics_in_window]
        cpu_usages = [m.system_metrics.cpu_usage_percentage for m in metrics_in_window]
        
        # API performance aggregation
        api_success_rates = defaultdict(list)
        api_response_times = defaultdict(list)
        
        for metrics in metrics_in_window:
            for api_name, api_data in metrics.api_metrics.items():
                api_success_rates[api_name].append(api_data.success_rate)
                api_response_times[api_name].append(api_data.avg_response_time_ms)
        
        # Create summary
        return MetricsSummary(
            time_period_minutes=time_window_minutes,
            start_time=start_time,
            end_time=end_time,
            avg_collection_rate=sum(collection_rates) / len(collection_rates),
            peak_collection_rate=max(collection_rates),
            total_papers_collected=max(m.collection_progress.papers_collected for m in metrics_in_window),
            api_success_rates={
                api: sum(rates) / len(rates) 
                for api, rates in api_success_rates.items()
            },
            api_avg_response_times={
                api: sum(times) / len(times)
                for api, times in api_response_times.items()
            },
            avg_memory_usage=sum(memory_usages) / len(memory_usages),
            peak_memory_usage=max(memory_usages),
            avg_cpu_usage=sum(cpu_usages) / len(cpu_usages),
            peak_cpu_usage=max(cpu_usages),
            total_venues_completed=max(m.collection_progress.completed_venues for m in metrics_in_window),
            total_processing_time_minutes=(end_time - start_time).total_seconds() / 60,
            processing_throughput=sum(m.processing_metrics.filtering_rate_per_second for m in metrics_in_window) / len(metrics_in_window)
        )
    
    def _collection_loop(self):
        """Main collection loop running in separate thread"""
        logger.info("Metrics collection loop started")
        
        while self.is_collecting:
            try:
                # Collect metrics and add to buffer
                metrics = self.collect_current_metrics()
                self.metrics_buffer.add_metrics(metrics)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                with self._lock:
                    self.collection_stats['collection_errors'] += 1
            
            # Wait for next collection interval
            time.sleep(self.collection_interval)
        
        logger.info("Metrics collection loop stopped")
    
    def _collect_collection_progress(self) -> CollectionProgressMetrics:
        """Collect overall collection progress metrics"""
        try:
            if not self.venue_engine:
                return self._create_default_collection_progress()
            
            # Get progress from venue engine
            progress_data = getattr(self.venue_engine, 'get_collection_progress', lambda: {})()
            
            total_venues = progress_data.get('total_venues', 0)
            completed_venues = progress_data.get('completed_venues', 0)
            in_progress_venues = progress_data.get('in_progress_venues', 0)
            failed_venues = progress_data.get('failed_venues', 0)
            
            papers_collected = progress_data.get('papers_collected', 0)
            estimated_total = progress_data.get('estimated_total_papers', 1000)
            
            # Calculate rates and estimates
            session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60
            papers_per_minute = papers_collected / max(session_duration, 1.0)
            completion_percentage = (papers_collected / max(estimated_total, 1)) * 100
            
            remaining_papers = max(0, estimated_total - papers_collected)
            estimated_remaining_minutes = remaining_papers / max(papers_per_minute, 0.1)
            estimated_completion = datetime.now() + timedelta(minutes=estimated_remaining_minutes)
            
            return CollectionProgressMetrics(
                session_id=self.session_id,
                total_venues=total_venues,
                completed_venues=completed_venues,
                in_progress_venues=in_progress_venues,
                failed_venues=failed_venues,
                papers_collected=papers_collected,
                papers_per_minute=papers_per_minute,
                estimated_total_papers=estimated_total,
                completion_percentage=min(completion_percentage, 100.0),
                session_duration_minutes=session_duration,
                estimated_remaining_minutes=estimated_remaining_minutes,
                estimated_completion_time=estimated_completion
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect collection progress: {e}")
            return self._create_default_collection_progress()
    
    def _collect_api_metrics(self) -> Dict[str, APIMetrics]:
        """Collect API health and performance metrics"""
        api_metrics = {}
        
        try:
            if not self.venue_engine:
                return {}
            
            # Get API health data from venue engine
            api_health_data = getattr(self.venue_engine, 'get_api_health_status', lambda: {})()
            
            for api_name, health_status in api_health_data.items():
                if isinstance(health_status, APIHealthStatus):
                    # Extract metrics from health status
                    api_metrics[api_name] = APIMetrics(
                        api_name=api_name,
                        health_status=health_status.status,
                        requests_made=getattr(health_status, 'requests_made', 0),
                        successful_requests=int(getattr(health_status, 'requests_made', 0) * health_status.success_rate),
                        failed_requests=getattr(health_status, 'requests_made', 0) - int(getattr(health_status, 'requests_made', 0) * health_status.success_rate),
                        success_rate=health_status.success_rate,
                        avg_response_time_ms=health_status.avg_response_time_ms,
                        min_response_time_ms=getattr(health_status, 'min_response_time_ms', health_status.avg_response_time_ms * 0.5),
                        max_response_time_ms=getattr(health_status, 'max_response_time_ms', health_status.avg_response_time_ms * 2.0),
                        rate_limit_status={},  # Would be populated from rate limiter
                        requests_throttled=0,
                        papers_collected=getattr(health_status, 'papers_collected', 0),
                        papers_per_request=getattr(health_status, 'papers_per_request', 0.0)
                    )
                
        except Exception as e:
            logger.warning(f"Failed to collect API metrics: {e}")
=======
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
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
        
        return api_metrics
    
    def _collect_processing_metrics(self) -> ProcessingMetrics:
<<<<<<< HEAD
        """Collect data processing metrics"""
        try:
            # Default metrics if no processors available
            if not self.data_processors:
                return ProcessingMetrics(
                    venues_normalized=0,
                    normalization_accuracy=1.0,
                    normalization_rate_per_second=0.0,
                    papers_deduplicated=0,
                    duplicates_removed=0,
                    deduplication_rate=0.0,
                    deduplication_confidence=1.0,
                    papers_analyzed=0,
                    papers_above_threshold=0,
                    breakthrough_papers_found=0,
                    filtering_rate_per_second=0.0
                )
            
            # Collect from venue normalizer
            venue_normalizer = self.data_processors.get('venue_normalizer')
            venue_stats = {}
            if venue_normalizer and hasattr(venue_normalizer, 'get_mapping_statistics'):
                venue_stats = venue_normalizer.get_mapping_statistics()
            
            # Collect from deduplicator
            deduplicator = self.data_processors.get('deduplicator')
            dedup_stats = {}
            if deduplicator and hasattr(deduplicator, 'get_statistics'):
                dedup_stats = deduplicator.get_statistics()
            
            # Collect from computational filter
            comp_filter = self.data_processors.get('computational_filter')
            filter_stats = {}
            if comp_filter and hasattr(comp_filter, 'get_statistics'):
                filter_stats = comp_filter.get_statistics()
            
            return ProcessingMetrics(
                venues_normalized=venue_stats.get('venues_normalized', 0),
                normalization_accuracy=venue_stats.get('accuracy', 1.0),
                normalization_rate_per_second=venue_stats.get('rate_per_second', 0.0),
                papers_deduplicated=dedup_stats.get('papers_processed', 0),
                duplicates_removed=dedup_stats.get('duplicates_removed', 0),
                deduplication_rate=dedup_stats.get('deduplication_rate', 0.0),
                deduplication_confidence=dedup_stats.get('confidence', 1.0),
                papers_analyzed=filter_stats.get('papers_analyzed', 0),
                papers_above_threshold=filter_stats.get('papers_above_threshold', 0),
                breakthrough_papers_found=filter_stats.get('breakthrough_papers', 0),
                filtering_rate_per_second=filter_stats.get('rate_per_second', 0.0)
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect processing metrics: {e}")
            return ProcessingMetrics(
                venues_normalized=0,
                normalization_accuracy=1.0,
                normalization_rate_per_second=0.0,
                papers_deduplicated=0,
                duplicates_removed=0,
                deduplication_rate=0.0,
                deduplication_confidence=1.0,
                papers_analyzed=0,
                papers_above_threshold=0,
                breakthrough_papers_found=0,
                filtering_rate_per_second=0.0
            )
    
    def _collect_state_metrics(self) -> StateManagementMetrics:
        """Collect state management and checkpointing metrics"""
        try:
            if not self.state_manager:
                return self._create_default_state_metrics()
            
            # Get checkpoint statistics
            checkpoint_stats = getattr(self.state_manager, 'get_checkpoint_statistics', lambda: {})()
            
            return StateManagementMetrics(
                checkpoints_created=checkpoint_stats.get('checkpoints_created', 0),
                last_checkpoint_time=checkpoint_stats.get('last_checkpoint_time'),
                checkpoint_creation_rate_per_hour=checkpoint_stats.get('rate_per_hour', 0.0),
                recovery_possible=checkpoint_stats.get('recovery_possible', True),
                last_recovery_time=checkpoint_stats.get('last_recovery_time'),
                recovery_success_rate=checkpoint_stats.get('recovery_success_rate', 1.0),
                state_size_mb=checkpoint_stats.get('state_size_mb', 0.0),
                checkpoint_size_mb=checkpoint_stats.get('checkpoint_size_mb', 0.0),
                checkpoint_creation_time_ms=checkpoint_stats.get('creation_time_ms', 0.0),
                state_save_time_ms=checkpoint_stats.get('save_time_ms', 0.0)
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect state metrics: {e}")
            return self._create_default_state_metrics()
    
    def _collect_venue_progress(self) -> Dict[str, VenueProgressMetrics]:
        """Collect individual venue progress metrics"""
        venue_progress = {}
        
        try:
            if not self.venue_engine:
                return {}
            
            # Get venue progress data
            venue_data = getattr(self.venue_engine, 'get_venue_progress', lambda: {})()
            
            for venue_key, progress in venue_data.items():
                # Parse venue and year from key (e.g., "NeurIPS_2024")
                if '_' in venue_key:
                    venue_name, year_str = venue_key.rsplit('_', 1)
                    try:
                        year = int(year_str)
                    except ValueError:
                        venue_name = venue_key
                        year = 2024
                else:
                    venue_name = venue_key
                    year = 2024
                
                venue_progress[venue_key] = VenueProgressMetrics(
                    venue_name=venue_name,
                    year=year,
                    status=progress.get('status', 'not_started'),
                    papers_collected=progress.get('papers_collected', 0),
                    target_papers=progress.get('target_papers', 100),
                    completion_percentage=progress.get('completion_percentage', 0.0),
                    last_update_time=progress.get('last_update_time', datetime.now()),
                    collection_duration_minutes=progress.get('duration_minutes', 0.0),
                    estimated_remaining_minutes=progress.get('estimated_remaining_minutes', 0.0)
                )
                
        except Exception as e:
            logger.warning(f"Failed to collect venue progress: {e}")
        
        return venue_progress
    
    def _create_default_collection_progress(self) -> CollectionProgressMetrics:
        """Create default collection progress when no data available"""
        return CollectionProgressMetrics(
            session_id=self.session_id,
            total_venues=0,
            completed_venues=0,
            in_progress_venues=0,
            failed_venues=0,
            papers_collected=0,
            papers_per_minute=0.0,
            estimated_total_papers=1000,
            completion_percentage=0.0,
            session_duration_minutes=0.0,
            estimated_remaining_minutes=0.0,
            estimated_completion_time=datetime.now()
        )
    
    def _create_default_state_metrics(self) -> StateManagementMetrics:
        """Create default state metrics when no data available"""
        return StateManagementMetrics(
            checkpoints_created=0,
            last_checkpoint_time=None,
            checkpoint_creation_rate_per_hour=0.0,
            recovery_possible=True,
            last_recovery_time=None,
            recovery_success_rate=1.0,
            state_size_mb=0.0,
            checkpoint_size_mb=0.0,
            checkpoint_creation_time_ms=0.0,
            state_save_time_ms=0.0
        )
    
    def _create_default_summary(self, time_window_minutes: int) -> MetricsSummary:
        """Create default summary when no metrics available"""
        return MetricsSummary(
            time_period_minutes=time_window_minutes,
            start_time=datetime.now() - timedelta(minutes=time_window_minutes),
            end_time=datetime.now(),
            avg_collection_rate=0.0,
            peak_collection_rate=0.0,
            total_papers_collected=0,
            api_success_rates={},
            api_avg_response_times={},
            avg_memory_usage=0.0,
            peak_memory_usage=0.0,
            avg_cpu_usage=0.0,
            peak_cpu_usage=0.0,
            total_venues_completed=0,
            total_processing_time_minutes=0.0,
            processing_throughput=0.0
        )
    
    def get_collection_statistics(self) -> Dict[str, Any]:
        """Get metrics collection statistics"""
        with self._lock:
            return {
                'is_collecting': self.is_collecting,
                'session_id': self.session_id,
                'session_start_time': self.session_start_time,
                'metrics_collected': self.collection_stats['metrics_collected'],
                'collection_errors': self.collection_stats['collection_errors'],
                'last_collection_time': self.collection_stats['last_collection_time'],
                'collection_interval_seconds': self.collection_interval,
                'metrics_buffer_size': len(self.metrics_buffer.metrics),
                'recent_failures': self.collection_stats['collection_failures'][-5:]  # Last 5 failures
            }
=======
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
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
