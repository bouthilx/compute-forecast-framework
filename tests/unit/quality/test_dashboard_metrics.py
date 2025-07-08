"""
Unit tests for dashboard metrics data structures and metrics buffer.
Tests the core components of Issue #8 Real-Time Collection Dashboard.
"""

import unittest
from datetime import datetime, timedelta
import threading
import time

from compute_forecast.monitoring.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    VenueProgressMetrics,
    MetricsBuffer,
)


class TestDashboardMetrics(unittest.TestCase):
    """Test dashboard metrics data structures"""

    def test_collection_progress_metrics(self):
        """Test CollectionProgressMetrics data structure"""
        metrics = CollectionProgressMetrics(
            session_id="test_session_metrics",
            total_venues=10,
            completed_venues=3,
            in_progress_venues=2,
            failed_venues=0,
            papers_collected=1500,
            papers_per_minute=25.5,
            estimated_total_papers=2000,
            completion_percentage=75.0,
            session_duration_minutes=60.0,
            estimated_remaining_minutes=15.0,
            estimated_completion_time=None,
            venues_remaining=5,
        )

        self.assertEqual(metrics.papers_collected, 1500)
        self.assertEqual(metrics.papers_per_minute, 25.5)
        self.assertEqual(metrics.completed_venues, 3)
        self.assertEqual(metrics.total_venues, 10)

    def test_api_metrics(self):
        """Test APIMetrics data structure"""
        metrics = APIMetrics(
            api_name="semantic_scholar",
            health_status="healthy",
            requests_made=100,
            successful_requests=95,
            failed_requests=5,
            success_rate=0.95,
            avg_response_time_ms=750.0,
            min_response_time_ms=200.0,
            max_response_time_ms=1500.0,
            rate_limit_status={},
            requests_throttled=0,
            papers_collected=80,
            papers_per_request=0.8,
        )

        self.assertEqual(metrics.api_name, "semantic_scholar")
        self.assertEqual(metrics.success_rate, 0.95)
        self.assertEqual(metrics.health_status, "healthy")

    def test_venue_progress_metrics(self):
        """Test VenueProgressMetrics data structure"""
        start_time = datetime.now()
        metrics = VenueProgressMetrics(
            venue_name="ICML",
            year=2024,
            status="in_progress",
            papers_collected=25,
            target_papers=50,
            completion_percentage=50.0,
            last_update_time=start_time,
            collection_duration_minutes=30.0,
            estimated_remaining_minutes=30.0,
            progress_percent=50.0,
            start_time=start_time,
            api_source="semantic_scholar",
        )

        self.assertEqual(metrics.venue_name, "ICML")
        self.assertEqual(metrics.year, 2024)
        self.assertEqual(metrics.status, "in_progress")
        self.assertEqual(metrics.progress_percent, 50.0)
        self.assertEqual(metrics.start_time, start_time)

    def test_system_metrics_to_dict(self):
        """Test SystemMetrics serialization to dictionary"""
        timestamp = datetime.now()

        system_metrics = SystemMetrics(
            timestamp=timestamp,
            collection_progress=CollectionProgressMetrics(
                session_id="test_dict_session",
                total_venues=5,
                completed_venues=2,
                in_progress_venues=1,
                failed_venues=0,
                papers_collected=100,
                papers_per_minute=10.0,
                estimated_total_papers=200,
                completion_percentage=50.0,
                session_duration_minutes=10.0,
                estimated_remaining_minutes=10.0,
                estimated_completion_time=None,
                venues_remaining=2,
            ),
            api_metrics={"test_api": APIMetrics(
                api_name="test_api",
                health_status="healthy",
                requests_made=10,
                successful_requests=9,
                failed_requests=1,
                success_rate=0.9,
                avg_response_time_ms=500.0,
                min_response_time_ms=100.0,
                max_response_time_ms=1000.0,
                rate_limit_status={},
                requests_throttled=0,
                papers_collected=8,
                papers_per_request=0.8,
            )},
            processing_metrics=ProcessingMetrics(
                venues_normalized=10,
                normalization_accuracy=0.9,
                normalization_rate_per_second=2.0,
                papers_deduplicated=90,
                duplicates_removed=5,
                deduplication_rate=0.95,
                deduplication_confidence=0.9,
                papers_analyzed=100,
                papers_above_threshold=80,
                breakthrough_papers_found=3,
                filtering_rate_per_second=1.5,
            ),
            system_metrics=SystemResourceMetrics(
                memory_usage_percentage=70.0,
                memory_used_mb=1400.0,
                memory_available_mb=600.0,
                cpu_usage_percentage=40.0,
                cpu_count=4,
                network_bytes_sent=300000,
                network_bytes_received=600000,
                network_connections=5,
                disk_usage_percentage=50.0,
                disk_free_gb=120.0,
                process_memory_mb=200.0,
                process_cpu_percentage=20.0,
                thread_count=4,
            ),
            state_metrics=StateManagementMetrics(
                checkpoints_created=3,
                last_checkpoint_time=datetime.now(),
                checkpoint_creation_rate_per_hour=0.5,
                recovery_possible=True,
                last_recovery_time=None,
                recovery_success_rate=1.0,
                state_size_mb=10.0,
                checkpoint_size_mb=5.0,
                checkpoint_creation_time_ms=50.0,
                state_save_time_ms=25.0,
            ),
            venue_progress={},
        )

        metrics_dict = system_metrics.to_dict()

        self.assertIn("timestamp", metrics_dict)
        self.assertIn("collection_progress", metrics_dict)
        self.assertIn("api_metrics", metrics_dict)
        self.assertIn("venue_progress", metrics_dict)

        # Check timestamp serialization
        self.assertEqual(metrics_dict["timestamp"], timestamp.isoformat())

        # Check nested structure serialization
        self.assertEqual(
            metrics_dict["collection_progress"]["papers_collected"], 100
        )


class TestMetricsBuffer(unittest.TestCase):
    """Test MetricsBuffer thread-safe storage"""

    def setUp(self):
        """Set up test metrics buffer"""
        self.buffer = MetricsBuffer(max_size=10)
        self.test_metrics = self._create_test_metrics()

    def _create_test_metrics(self, papers_count=100):
        """Create test SystemMetrics instance"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                session_id="test_buffer_session",
                total_venues=8,
                completed_venues=3,
                in_progress_venues=2,
                failed_venues=1,
                papers_collected=papers_count,
                papers_per_minute=15.0,
                estimated_total_papers=papers_count + 50,
                completion_percentage=60.0,
                session_duration_minutes=25.0,
                estimated_remaining_minutes=15.0,
                estimated_completion_time=None,
                venues_remaining=2,
            ),
            api_metrics={},
            processing_metrics=ProcessingMetrics(
                venues_normalized=15,
                normalization_accuracy=0.88,
                normalization_rate_per_second=1.8,
                papers_deduplicated=papers_count,
                duplicates_removed=8,
                deduplication_rate=0.92,
                deduplication_confidence=0.85,
                papers_analyzed=papers_count,
                papers_above_threshold=papers_count - 20,
                breakthrough_papers_found=2,
                filtering_rate_per_second=1.3,
            ),
            system_metrics=SystemResourceMetrics(
                memory_usage_percentage=65.0,
                memory_used_mb=1300.0,
                memory_available_mb=700.0,
                cpu_usage_percentage=35.0,
                cpu_count=4,
                network_bytes_sent=250000,
                network_bytes_received=500000,
                network_connections=3,
                disk_usage_percentage=45.0,
                disk_free_gb=130.0,
                process_memory_mb=180.0,
                process_cpu_percentage=18.0,
                thread_count=5,
            ),
            state_metrics=StateManagementMetrics(
                checkpoints_created=6,
                last_checkpoint_time=datetime.now(),
                checkpoint_creation_rate_per_hour=1.2,
                recovery_possible=True,
                last_recovery_time=None,
                recovery_success_rate=0.95,
                state_size_mb=15.0,
                checkpoint_size_mb=8.0,
                checkpoint_creation_time_ms=80.0,
                state_save_time_ms=40.0,
            ),
            venue_progress={},
        )

    def test_add_metrics(self):
        """Test adding metrics to buffer"""
        self.assertEqual(self.buffer.size(), 0)

        self.buffer.add_metrics(self.test_metrics)
        self.assertEqual(self.buffer.size(), 1)

        latest = self.buffer.get_latest_metrics()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.collection_progress.papers_collected, 100)

    def test_buffer_max_size(self):
        """Test buffer respects maximum size"""
        # Add more metrics than max_size
        for i in range(15):
            metrics = self._create_test_metrics(papers_count=i)
            self.buffer.add_metrics(metrics)

        # Should only keep last 10
        self.assertEqual(self.buffer.size(), 10)

        # Latest should be the last added (papers_count=14)
        latest = self.buffer.get_latest_metrics()
        self.assertEqual(latest.collection_progress.papers_collected, 14)

    def test_get_metrics_history(self):
        """Test retrieving metrics history"""
        # Add some metrics
        for i in range(5):
            metrics = self._create_test_metrics(papers_count=i)
            self.buffer.add_metrics(metrics)

        # Get all history
        history = self.buffer.get_metrics_history(10)
        self.assertEqual(len(history), 5)

        # Get limited history
        recent = self.buffer.get_metrics_history(3)
        self.assertEqual(len(recent), 3)

        # Should be the most recent 3
        self.assertEqual(recent[-1].collection_progress.papers_collected, 4)
        self.assertEqual(recent[-2].collection_progress.papers_collected, 3)
        self.assertEqual(recent[-3].collection_progress.papers_collected, 2)

    def test_get_metrics_since(self):
        """Test retrieving metrics since specific time"""
        base_time = datetime.now()

        # Add metrics with different timestamps
        for i in range(5):
            metrics = self._create_test_metrics(papers_count=i)
            metrics.timestamp = base_time + timedelta(minutes=i)
            self.buffer.add_metrics(metrics)

        # Get metrics since 2 minutes ago
        since_time = base_time + timedelta(minutes=2)
        recent_metrics = self.buffer.get_metrics_since(since_time)

        # Should get metrics from minute 2, 3, 4
        self.assertEqual(len(recent_metrics), 3)
        self.assertTrue(all(m.timestamp >= since_time for m in recent_metrics))

    def test_thread_safety(self):
        """Test buffer thread safety with concurrent access"""

        def add_metrics_worker(worker_id, count):
            """Worker function to add metrics"""
            for i in range(count):
                metrics = self._create_test_metrics(papers_count=worker_id * 100 + i)
                self.buffer.add_metrics(metrics)
                time.sleep(0.001)  # Small delay to increase contention

        def read_metrics_worker(read_count):
            """Worker function to read metrics"""
            for _ in range(read_count):
                self.buffer.get_latest_metrics()
                self.buffer.get_metrics_history(5)
                time.sleep(0.001)

        # Start multiple threads
        threads = []

        # 3 writer threads
        for worker_id in range(3):
            thread = threading.Thread(target=add_metrics_worker, args=(worker_id, 10))
            threads.append(thread)

        # 2 reader threads
        for _ in range(2):
            thread = threading.Thread(target=read_metrics_worker, args=(20,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
            self.assertFalse(thread.is_alive(), "Thread should have completed")

        # Verify buffer is in valid state
        self.assertLessEqual(self.buffer.size(), 10)  # Respects max size
        self.assertGreater(self.buffer.size(), 0)  # Has some data

        latest = self.buffer.get_latest_metrics()
        self.assertIsNotNone(latest)

    def test_clear_buffer(self):
        """Test clearing the buffer"""
        # Add some metrics
        for i in range(5):
            self.buffer.add_metrics(self._create_test_metrics(papers_count=i))

        self.assertEqual(self.buffer.size(), 5)

        # Clear buffer
        self.buffer.clear()

        self.assertEqual(self.buffer.size(), 0)
        self.assertIsNone(self.buffer.get_latest_metrics())
        self.assertEqual(len(self.buffer.get_metrics_history(10)), 0)


if __name__ == "__main__":
    unittest.main()
