"""
MetricsCollector - Collects system metrics from all components.
Provides real-time metrics gathering with <2 second collection time requirement.
"""

import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from .dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    VenueProgressMetrics,
    MetricsBuffer,
    MetricsSummary,
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

        # Metrics storage
        self.metrics_buffer = MetricsBuffer(max_size=1000)
        self._current_metrics: Optional[SystemMetrics] = None

        # Component references
        self.venue_engine = None
        self.state_manager = None
        self.api_managers: Dict[str, Any] = {}
        self.data_processors: Dict[str, Any] = {}

        # Collection control
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Performance tracking
        self._last_collection_time = 0.0
        self._collection_count = 0
        self._collection_errors = 0
        self._session_id = None

        logger.info(
            f"MetricsCollector initialized with {collection_interval_seconds}s interval"
        )

    @property
    def is_collecting(self) -> bool:
        """Check if metrics collection is currently running"""
        return self._running

    @property
    def collection_thread(self) -> Optional[threading.Thread]:
        """Get the collection thread instance"""
        return self._collection_thread

    @property
    def collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        with self._lock:
            return {
                "metrics_collected": self._collection_count,
                "collection_errors": self._collection_errors,
            }

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self._session_id

    def start_collection(
        self,
        venue_engine,
        state_manager,
        api_managers: Dict[str, Any],
        data_processors: Dict[str, Any],
    ) -> None:
        """
        Start automatic metrics collection from all system components

        Args:
            venue_engine: Venue collection engine instance
            state_manager: State management instance
            api_managers: Dict of API manager instances
            data_processors: Dict of data processor instances
        """
        with self._lock:
            if self._running:
                logger.warning("Metrics collection already running")
                return

            # Store component references
            self.venue_engine = venue_engine
            self.state_manager = state_manager
            self.api_managers = api_managers
            self.data_processors = data_processors

            # Generate session ID
            import uuid
            self._session_id = str(uuid.uuid4())

            # Start collection thread
            self._running = True
            self._collection_thread = threading.Thread(
                target=self._collection_loop, name="MetricsCollector", daemon=True
            )
            self._collection_thread.start()

            logger.info("Metrics collection started")

    def stop_collection(self) -> None:
        """Stop metrics collection"""
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Wait for collection thread to finish
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=10)

        logger.info("Metrics collection stopped")

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent collected metrics"""
        with self._lock:
            return self._current_metrics

    def collect_current_metrics(self) -> SystemMetrics:
        """Collect fresh metrics from all system components"""
        return self.collect_metrics()

    def get_metrics_summary(self, time_window_minutes: int = 60) -> MetricsSummary:
        """Get aggregated metrics summary over time window"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)
        
        # Get metrics from buffer within time window
        metrics_history = self.metrics_buffer.get_metrics_since(start_time)
        
        if not metrics_history:
            # Return empty summary if no metrics
            return MetricsSummary(
                time_period_minutes=time_window_minutes,
                start_time=start_time,
                end_time=end_time,
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
                total_processing_time_minutes=time_window_minutes,
            )
        
        # Calculate collection rates
        collection_rates = [m.collection_progress.papers_per_minute for m in metrics_history]
        avg_collection_rate = sum(collection_rates) / len(collection_rates)
        peak_collection_rate = max(collection_rates)
        
        # Get total papers from latest metrics
        total_papers_collected = metrics_history[-1].collection_progress.papers_collected
        
        # Calculate API metrics
        api_success_rates = {}
        api_avg_response_times = {}
        
        for metrics in metrics_history:
            for api_name, api_metrics in metrics.api_metrics.items():
                if api_name not in api_success_rates:
                    api_success_rates[api_name] = []
                    api_avg_response_times[api_name] = []
                api_success_rates[api_name].append(api_metrics.success_rate)
                api_avg_response_times[api_name].append(api_metrics.avg_response_time_ms)
        
        # Average the API metrics
        for api_name in api_success_rates:
            api_success_rates[api_name] = sum(api_success_rates[api_name]) / len(api_success_rates[api_name])
            api_avg_response_times[api_name] = sum(api_avg_response_times[api_name]) / len(api_avg_response_times[api_name])
        
        # Calculate system metrics
        memory_usage = [m.system_metrics.memory_usage_percentage for m in metrics_history]
        cpu_usage = [m.system_metrics.cpu_usage_percentage for m in metrics_history]
        
        avg_memory_usage = sum(memory_usage) / len(memory_usage)
        peak_memory_usage = max(memory_usage)
        avg_cpu_usage = sum(cpu_usage) / len(cpu_usage)
        peak_cpu_usage = max(cpu_usage)
        
        return MetricsSummary(
            time_period_minutes=time_window_minutes,
            start_time=start_time,
            end_time=end_time,
            avg_collection_rate=avg_collection_rate,
            peak_collection_rate=peak_collection_rate,
            total_papers_collected=total_papers_collected,
            api_success_rates=api_success_rates,
            api_avg_response_times=api_avg_response_times,
            avg_memory_usage=avg_memory_usage,
            peak_memory_usage=peak_memory_usage,
            avg_cpu_usage=avg_cpu_usage,
            peak_cpu_usage=peak_cpu_usage,
            total_venues_completed=0,  # TODO: Calculate from metrics
            total_processing_time_minutes=time_window_minutes,
        )

    def collect_metrics(self) -> SystemMetrics:
        """
        Collect metrics from all system components

        Performance requirement: Complete within 2 seconds
        """
        start_time = time.time()

        try:
            # Collect from each component
            collection_progress = self._collect_collection_progress()
            api_metrics = self._collect_api_metrics()
            processing_metrics = self._collect_processing_metrics()
            system_metrics = self._collect_system_metrics()
            state_metrics = self._collect_state_metrics()
            venue_progress = self._collect_venue_progress()

            # Create metrics snapshot
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                collection_progress=collection_progress,
                api_metrics=api_metrics,
                processing_metrics=processing_metrics,
                system_metrics=system_metrics,
                state_metrics=state_metrics,
                venue_progress=venue_progress,
            )

            # Track collection time
            collection_time = time.time() - start_time
            if collection_time > 2.0:
                logger.warning(
                    f"Metrics collection took {collection_time:.2f}s (>2s requirement)"
                )

            # Update current metrics
            with self._lock:
                self._current_metrics = metrics
                self._collection_count += 1
                self._last_collection_time = collection_time

            # Store in buffer
            self.metrics_buffer.add_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            with self._lock:
                self._collection_errors += 1
            raise

    def _collection_loop(self) -> None:
        """Background thread for periodic metrics collection"""
        logger.info("Starting metrics collection loop")

        while self._running:
            try:
                # Collect metrics
                self.collect_metrics()

                # Sleep for interval
                time.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                time.sleep(self.collection_interval)

        logger.info("Metrics collection loop stopped")

    def _collect_collection_progress(self) -> CollectionProgressMetrics:
        """Collect overall collection progress metrics"""
        if not self.venue_engine:
            return self._empty_collection_progress()

        try:
            # Get progress from venue engine
            progress = self.venue_engine.get_collection_progress()

            # Calculate derived metrics
            total_venues = progress.get("total_venues", 0)
            completed = progress.get("completed_venues", 0)
            in_progress = progress.get("in_progress_venues", 0)
            failed = progress.get("failed_venues", 0)

            completion_pct = (completed / max(total_venues, 1)) * 100

            # Calculate paper collection rate
            papers = progress.get("papers_collected", 0)
            duration = progress.get("session_duration_minutes", 1)
            papers_per_minute = papers / max(duration, 1)

            # Estimate remaining time
            venues_remaining = total_venues - completed
            avg_time_per_venue = duration / max(completed, 1)
            estimated_remaining = venues_remaining * avg_time_per_venue

            return CollectionProgressMetrics(
                session_id=progress.get("session_id"),
                total_venues=total_venues,
                completed_venues=completed,
                in_progress_venues=in_progress,
                failed_venues=failed,
                papers_collected=papers,
                papers_per_minute=papers_per_minute,
                estimated_total_papers=progress.get("estimated_total_papers", 0),
                completion_percentage=completion_pct,
                session_duration_minutes=duration,
                estimated_remaining_minutes=estimated_remaining,
                estimated_completion_time=datetime.now()
                + timedelta(minutes=estimated_remaining),
                venues_remaining=venues_remaining,
                current_year=progress.get("current_year"),
            )

        except Exception as e:
            logger.error(f"Error collecting progress metrics: {e}")
            return self._empty_collection_progress()

    def _collect_api_metrics(self) -> Dict[str, APIMetrics]:
        """Collect metrics from all API managers"""
        api_metrics = {}

        for api_name, manager in self.api_managers.items():
            try:
                stats = manager.get_statistics()

                # Calculate derived metrics
                total_requests = stats.get("requests_made", 0)
                successful = stats.get("successful_requests", 0)
                success_rate = successful / max(total_requests, 1)

                api_metrics[api_name] = APIMetrics(
                    api_name=api_name,
                    health_status=stats.get("health_status", "unknown"),
                    requests_made=total_requests,
                    successful_requests=successful,
                    failed_requests=stats.get("failed_requests", 0),
                    success_rate=success_rate,
                    avg_response_time_ms=stats.get("avg_response_time_ms", 0),
                    min_response_time_ms=stats.get("min_response_time_ms", 0),
                    max_response_time_ms=stats.get("max_response_time_ms", 0),
                    rate_limit_status=stats.get("rate_limit_status", {}),
                    requests_throttled=stats.get("requests_throttled", 0),
                    papers_collected=stats.get("papers_collected", 0),
                    papers_per_request=stats.get("papers_per_request", 0),
                    requests_per_minute=stats.get("requests_per_minute", 0),
                    rate_limit_hits=stats.get("rate_limit_hits", 0),
                    last_request_time=stats.get("last_request_time"),
                )

            except Exception as e:
                logger.error(f"Error collecting metrics for API {api_name}: {e}")

        return api_metrics

    def _collect_processing_metrics(self) -> ProcessingMetrics:
        """Collect data processing metrics"""
        try:
            # Aggregate metrics from all processors
            total_processed = 0
            total_deduplicated = 0
            duplicates_removed = 0
            papers_above_threshold = 0
            breakthrough_papers = 0

            for processor_name, processor in self.data_processors.items():
                if hasattr(processor, "get_statistics"):
                    stats = processor.get_statistics()
                    total_processed += stats.get("papers_processed", 0)
                    total_deduplicated += stats.get("papers_deduplicated", 0)
                    duplicates_removed += stats.get("duplicates_removed", 0)
                    papers_above_threshold += stats.get("papers_above_threshold", 0)
                    breakthrough_papers += stats.get("breakthrough_papers_found", 0)

            # Calculate rates
            dedup_rate = duplicates_removed / max(total_processed, 1)

            return ProcessingMetrics(
                venues_normalized=0,  # TODO: Implement venue normalization tracking
                normalization_accuracy=0.0,
                normalization_rate_per_second=0.0,
                papers_deduplicated=total_deduplicated,
                duplicates_removed=duplicates_removed,
                deduplication_rate=dedup_rate,
                deduplication_confidence=0.95,  # TODO: Calculate actual confidence
                papers_analyzed=total_processed,
                papers_above_threshold=papers_above_threshold,
                breakthrough_papers_found=breakthrough_papers,
                filtering_rate_per_second=0.0,  # TODO: Calculate actual rate
                papers_processed=total_processed,
                papers_filtered=0,  # TODO: Track filtered papers
                papers_normalized=0,  # TODO: Track normalized papers
                processing_rate_per_minute=0.0,  # TODO: Calculate rate
                filter_rate=0.0,  # TODO: Calculate filter rate
                processing_queue_size=0,  # TODO: Track queue size
            )

        except Exception as e:
            logger.error(f"Error collecting processing metrics: {e}")
            return self._empty_processing_metrics()

    def _collect_system_metrics(self) -> SystemResourceMetrics:
        """Collect system resource metrics using psutil"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_used_mb = disk.used / (1024 * 1024)
            disk_free_mb = disk.free / (1024 * 1024)

            # Network metrics (cumulative)
            net_io = psutil.net_io_counters()
            network_sent_mb = net_io.bytes_sent / (1024 * 1024)
            network_recv_mb = net_io.bytes_recv / (1024 * 1024)

            # Process metrics
            process = psutil.Process()
            thread_count = process.num_threads()
            open_fds = process.num_fds() if hasattr(process, "num_fds") else 0

            return SystemResourceMetrics(
                cpu_usage_percentage=cpu_percent,
                cpu_count=cpu_count,
                memory_usage_percentage=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percentage=disk_percent,
                disk_usage_mb=disk_used_mb,
                disk_free_mb=disk_free_mb,
                network_bytes_sent=int(network_sent_mb * 1024 * 1024),
                network_bytes_received=int(network_recv_mb * 1024 * 1024),
                network_connections=0,  # TODO: Implement network connections count
                disk_free_gb=disk_free_mb / 1024,
                process_memory_mb=memory_used_mb,  # TODO: Get process-specific memory
                process_cpu_percentage=cpu_percent,  # TODO: Get process-specific CPU
                thread_count=thread_count,
                active_threads=thread_count,
                open_file_descriptors=open_fds,
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return self._empty_system_metrics()

    def _collect_state_metrics(self) -> StateManagementMetrics:
        """Collect state management metrics"""
        if not self.state_manager:
            return self._empty_state_metrics()

        try:
            stats = self.state_manager.get_statistics()

            return StateManagementMetrics(
                checkpoints_created=stats.get("checkpoints_created", 0),
                last_checkpoint_time=stats.get("last_checkpoint_time"),
                checkpoint_creation_rate_per_hour=stats.get("checkpoint_rate", 0),
                recovery_possible=stats.get("recovery_possible", False),
                last_recovery_time=stats.get("last_recovery_time"),
                recovery_success_rate=stats.get("recovery_success_rate", 1.0),
                state_size_mb=stats.get("state_size_mb", 0),
                checkpoint_size_mb=stats.get("checkpoint_size_mb", 0),
                checkpoint_creation_time_ms=stats.get("checkpoint_time_ms", 0),
                state_save_time_ms=stats.get("state_save_time_ms", 0),
                recovery_time_seconds=stats.get("recovery_time_seconds", 0),
                state_validation_errors=stats.get("validation_errors", 0),
                backup_count=stats.get("backup_count", 0),
            )

        except Exception as e:
            logger.error(f"Error collecting state metrics: {e}")
            return self._empty_state_metrics()

    def _collect_venue_progress(self) -> Dict[str, VenueProgressMetrics]:
        """Collect individual venue progress metrics"""
        venue_progress: Dict[str, VenueProgressMetrics] = {}

        if not self.venue_engine:
            return venue_progress

        try:
            # Get venue status from engine
            venue_statuses = self.venue_engine.get_venue_statuses()

            for venue_key, status in venue_statuses.items():
                venue_name = status.get("venue_name", "")
                year = status.get("year", 0)

                # Calculate progress
                papers = status.get("papers_collected", 0)
                target = status.get("target_papers", 100)
                completion_pct = (papers / max(target, 1)) * 100

                # Calculate time estimates
                duration = status.get("collection_duration_minutes", 0)
                papers_per_minute = papers / max(duration, 1) if duration > 0 else 0
                remaining_papers = max(target - papers, 0)
                estimated_remaining = (
                    remaining_papers / max(papers_per_minute, 1)
                    if papers_per_minute > 0
                    else 0
                )

                venue_progress[venue_key] = VenueProgressMetrics(
                    venue_name=venue_name,
                    year=year,
                    status=status.get("status", "not_started"),
                    papers_collected=papers,
                    target_papers=target,
                    completion_percentage=completion_pct,
                    last_update_time=status.get("last_update_time", datetime.now()),
                    collection_duration_minutes=duration,
                    estimated_remaining_minutes=estimated_remaining,
                    retry_count=status.get("retry_count", 0),
                    error_count=status.get("error_count", 0),
                    last_activity=status.get("last_activity"),
                )

        except Exception as e:
            logger.error(f"Error collecting venue progress: {e}")

        return venue_progress

    def get_collection_statistics(self) -> Dict[str, Any]:
        """Get metrics collector statistics"""
        with self._lock:
            return {
                "collection_count": self._collection_count,
                "collection_errors": self._collection_errors,
                "last_collection_time_seconds": self._last_collection_time,
                "buffer_size": len(self.metrics_buffer),
                "is_collecting": self._running,
            }

    # Empty metric factory methods for error cases
    def _empty_collection_progress(self) -> CollectionProgressMetrics:
        return CollectionProgressMetrics(
            session_id=None,
            total_venues=0,
            completed_venues=0,
            in_progress_venues=0,
            failed_venues=0,
            papers_collected=0,
            papers_per_minute=0.0,
            estimated_total_papers=0,
            completion_percentage=0.0,
            session_duration_minutes=0.0,
            estimated_remaining_minutes=0.0,
            estimated_completion_time=None,
            venues_remaining=0,
            current_year=None,
        )

    def _empty_processing_metrics(self) -> ProcessingMetrics:
        return ProcessingMetrics(
            venues_normalized=0,
            normalization_accuracy=0.0,
            normalization_rate_per_second=0.0,
            papers_deduplicated=0,
            duplicates_removed=0,
            deduplication_rate=0.0,
            deduplication_confidence=0.0,
            papers_analyzed=0,
            papers_above_threshold=0,
            breakthrough_papers_found=0,
            filtering_rate_per_second=0.0,
            papers_processed=0,
            papers_filtered=0,
            papers_normalized=0,
            processing_rate_per_minute=0.0,
            filter_rate=0.0,
            processing_queue_size=0,
        )

    def _empty_system_metrics(self) -> SystemResourceMetrics:
        return SystemResourceMetrics(
            cpu_usage_percentage=0.0,
            cpu_count=0,
            memory_usage_percentage=0.0,
            memory_used_mb=0.0,
            memory_available_mb=0.0,
            disk_usage_percentage=0.0,
            disk_usage_mb=0.0,
            disk_free_mb=0.0,
            network_bytes_sent=0,
            network_bytes_received=0,
            network_connections=0,
            disk_free_gb=0.0,
            process_memory_mb=0.0,
            process_cpu_percentage=0.0,
            thread_count=0,
            active_threads=0,
            open_file_descriptors=0,
        )

    def _empty_state_metrics(self) -> StateManagementMetrics:
        return StateManagementMetrics(
            checkpoints_created=0,
            last_checkpoint_time=None,
            checkpoint_creation_rate_per_hour=0.0,
            recovery_possible=False,
            last_recovery_time=None,
            recovery_success_rate=0.0,
            state_size_mb=0.0,
            checkpoint_size_mb=0.0,
            checkpoint_creation_time_ms=0.0,
            state_save_time_ms=0.0,
            recovery_time_seconds=0.0,
            state_validation_errors=0,
            backup_count=0,
        )
