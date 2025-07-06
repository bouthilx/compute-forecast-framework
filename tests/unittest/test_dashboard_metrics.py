"""
<<<<<<< HEAD
Unit tests for dashboard metrics data structures and functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import psutil
=======
Unit tests for dashboard metrics data structures and metrics buffer.
Tests the core components of Issue #8 Real-Time Collection Dashboard.
"""

import unittest
from datetime import datetime, timedelta
import threading
import time
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)

from compute_forecast.monitoring.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    VenueProgressMetrics,
<<<<<<< HEAD
    MetricsSummary,
    DashboardStatus,
=======
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
    MetricsBuffer
)


<<<<<<< HEAD
class TestSystemResourceMetrics:
    """Test system resource metrics collection"""
    
    def test_collect_current_metrics(self):
        """Test collection of current system metrics"""
        metrics = SystemResourceMetrics.collect_current()
        
        assert isinstance(metrics, SystemResourceMetrics)
        assert metrics.memory_usage_percentage >= 0
        assert metrics.memory_usage_percentage <= 100
        assert metrics.cpu_usage_percentage >= 0
        assert metrics.memory_used_mb > 0
        assert metrics.memory_available_mb > 0
        assert metrics.cpu_count > 0
        assert metrics.process_memory_mb > 0
        assert metrics.thread_count > 0
        assert metrics.disk_usage_percentage >= 0
        assert metrics.disk_free_gb >= 0
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.disk_usage')
    @patch('psutil.Process')
    def test_collect_current_mocked(self, mock_process, mock_disk, mock_net_conn, 
                                   mock_net_io, mock_cpu_count, mock_cpu_percent, 
                                   mock_memory):
        """Test with mocked psutil data"""
        # Mock memory
        mock_memory.return_value = Mock(
            percent=75.5,
            used=8000000000,  # 8GB
            available=2000000000  # 2GB
        )
        
        # Mock CPU
        mock_cpu_percent.return_value = 45.2
        mock_cpu_count.return_value = 8
        
        # Mock network
        mock_net_io.return_value = Mock(
            bytes_sent=1000000,
            bytes_recv=2000000
        )
        mock_net_conn.return_value = [Mock(), Mock(), Mock()]  # 3 connections
        
        # Mock disk
        mock_disk.return_value = Mock(
            used=500000000000,
            total=1000000000000,
            free=500000000000
        )
        
        # Mock process
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = Mock(rss=100000000)  # 100MB
        mock_process_instance.cpu_percent.return_value = 15.5
        mock_process_instance.num_threads.return_value = 12
        mock_process.return_value = mock_process_instance
        
        metrics = SystemResourceMetrics.collect_current()
        
        assert metrics.memory_usage_percentage == 75.5
        assert metrics.memory_used_mb == pytest.approx(7629.4, rel=1e-1)
        assert metrics.memory_available_mb == pytest.approx(1907.3, rel=1e-1)
        assert metrics.cpu_usage_percentage == 45.2
        assert metrics.cpu_count == 8
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_received == 2000000
        assert metrics.network_connections == 3
        assert metrics.disk_usage_percentage == 50.0
        assert metrics.disk_free_gb == pytest.approx(465.66, rel=1e-1)
        assert metrics.process_memory_mb == pytest.approx(95.37, rel=1e-1)
        assert metrics.process_cpu_percentage == 15.5
        assert metrics.thread_count == 12


class TestMetricsBuffer:
    """Test metrics buffer functionality"""
    
    def test_buffer_initialization(self):
        """Test buffer initialization"""
        buffer = MetricsBuffer(max_size=100)
        assert len(buffer.metrics) == 0
        assert buffer.max_size == 100
    
    def test_add_metrics(self):
        """Test adding metrics to buffer"""
        buffer = MetricsBuffer(max_size=3)
        
        # Create test metrics
        for i in range(5):
            metrics = self._create_test_metrics(i)
            buffer.add_metrics(metrics)
        
        # Should only keep last 3
        assert len(buffer.metrics) == 3
        assert buffer.metrics[0].collection_progress.papers_collected == 2
        assert buffer.metrics[-1].collection_progress.papers_collected == 4
    
    def test_get_recent_metrics(self):
        """Test retrieving recent metrics"""
        buffer = MetricsBuffer(max_size=10)
        
        # Add some metrics
        for i in range(5):
            metrics = self._create_test_metrics(i)
            buffer.add_metrics(metrics)
        
        # Get recent metrics
        recent = buffer.get_recent_metrics(count=3)
        assert len(recent) == 3
        assert recent[0].collection_progress.papers_collected == 2
        assert recent[-1].collection_progress.papers_collected == 4
    
    def test_get_metrics_in_window(self):
        """Test retrieving metrics within time window"""
        buffer = MetricsBuffer(max_size=10)
        
        # Add metrics with different timestamps
        now = datetime.now()
        for i in range(5):
            metrics = self._create_test_metrics(i)
            metrics.timestamp = now - timedelta(minutes=i*10)
            buffer.add_metrics(metrics)
        
        # Get metrics within 25 minutes
        windowed = buffer.get_metrics_in_window(25)
        assert len(windowed) == 3  # Should get metrics from 0, 10, 20 minutes ago
    
    def test_get_current_metrics(self):
        """Test getting most recent metrics"""
        buffer = MetricsBuffer(max_size=10)
        
        # Empty buffer
        assert buffer.get_current_metrics() is None
        
        # Add metrics
        metrics = self._create_test_metrics(42)
        buffer.add_metrics(metrics)
        
        current = buffer.get_current_metrics()
        assert current is not None
        assert current.collection_progress.papers_collected == 42
    
    def test_clear_buffer(self):
        """Test clearing buffer"""
        buffer = MetricsBuffer(max_size=10)
        
        # Add metrics
        for i in range(3):
            metrics = self._create_test_metrics(i)
            buffer.add_metrics(metrics)
        
        assert len(buffer.metrics) == 3
        
        buffer.clear()
        assert len(buffer.metrics) == 0
    
    def _create_test_metrics(self, papers_collected: int) -> SystemMetrics:
        """Create test SystemMetrics instance"""
        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                session_id=f"test_session_{papers_collected}",
                total_venues=100,
                completed_venues=papers_collected // 10,
                in_progress_venues=1,
                failed_venues=0,
                papers_collected=papers_collected,
                papers_per_minute=5.0,
                estimated_total_papers=1000,
                completion_percentage=papers_collected / 10.0,
                session_duration_minutes=papers_collected * 0.2,
                estimated_remaining_minutes=(1000 - papers_collected) * 0.2,
                estimated_completion_time=datetime.now() + timedelta(minutes=(1000 - papers_collected) * 0.2)
            ),
            api_metrics={},
            processing_metrics=ProcessingMetrics(
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
            ),
            system_metrics=SystemResourceMetrics(
                memory_usage_percentage=50.0,
                memory_used_mb=1000.0,
                memory_available_mb=1000.0,
                cpu_usage_percentage=25.0,
                cpu_count=4,
                network_bytes_sent=1000,
                network_bytes_received=2000,
                network_connections=5,
                disk_usage_percentage=60.0,
                disk_free_gb=100.0,
                process_memory_mb=50.0,
                process_cpu_percentage=10.0,
                thread_count=8
            ),
            state_metrics=StateManagementMetrics(
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
            ),
            venue_progress={}
        )


class TestDashboardStatus:
    """Test dashboard status functionality"""
    
    def test_dashboard_status_initialization(self):
        """Test dashboard status initialization"""
        status = DashboardStatus(
            is_running=False,
            connected_clients=0,
            port=8080,
            uptime_seconds=0.0,
            messages_sent=0,
            last_broadcast_time=None,
            server_start_time=datetime.now()
        )
        
        assert not status.is_running
        assert status.connected_clients == 0
        assert status.port == 8080
        assert status.messages_sent == 0
        assert status.last_broadcast_time is None
    
    def test_update_broadcast_stats(self):
        """Test updating broadcast statistics"""
        status = DashboardStatus(
            is_running=True,
            connected_clients=1,
            port=8080,
            uptime_seconds=0.0,
            messages_sent=0,
            last_broadcast_time=None,
            server_start_time=datetime.now()
        )
        
        # Update with default message count
        status.update_broadcast_stats()
        assert status.messages_sent == 1
        assert status.last_broadcast_time is not None
        
        # Update with specific message count
        old_time = status.last_broadcast_time
        status.update_broadcast_stats(5)
        assert status.messages_sent == 6
        assert status.last_broadcast_time > old_time
    
    def test_get_uptime_minutes(self):
        """Test uptime calculation"""
        start_time = datetime.now() - timedelta(minutes=30)
        status = DashboardStatus(
            is_running=True,
            connected_clients=1,
            port=8080,
            uptime_seconds=0.0,
            messages_sent=0,
            last_broadcast_time=None,
            server_start_time=start_time
        )
        
        uptime = status.get_uptime_minutes()
        assert 29.5 <= uptime <= 30.5  # Allow some tolerance for test execution time


class TestCollectionProgressMetrics:
    """Test collection progress metrics"""
    
    def test_collection_progress_creation(self):
        """Test creating collection progress metrics"""
        metrics = CollectionProgressMetrics(
            session_id="test_session",
            total_venues=150,
            completed_venues=45,
            in_progress_venues=3,
            failed_venues=2,
            papers_collected=4500,
            papers_per_minute=15.5,
            estimated_total_papers=15000,
            completion_percentage=30.0,
            session_duration_minutes=290.0,
            estimated_remaining_minutes=670.0,
            estimated_completion_time=datetime.now() + timedelta(minutes=670)
        )
        
        assert metrics.session_id == "test_session"
        assert metrics.total_venues == 150
        assert metrics.completed_venues == 45
        assert metrics.papers_collected == 4500
        assert metrics.papers_per_minute == 15.5
        assert metrics.completion_percentage == 30.0


class TestAPIMetrics:
    """Test API metrics"""
    
    def test_api_metrics_creation(self):
        """Test creating API metrics"""
        metrics = APIMetrics(
            api_name="semantic_scholar",
            health_status="healthy",
            requests_made=1000,
            successful_requests=950,
            failed_requests=50,
            success_rate=0.95,
            avg_response_time_ms=450.0,
            min_response_time_ms=200.0,
            max_response_time_ms=2000.0,
            rate_limit_status={},
            requests_throttled=5,
            papers_collected=2500,
            papers_per_request=2.5
        )
        
        assert metrics.api_name == "semantic_scholar"
        assert metrics.health_status == "healthy"
        assert metrics.success_rate == 0.95
        assert metrics.papers_per_request == 2.5
=======
class TestDashboardMetrics(unittest.TestCase):
    """Test dashboard metrics data structures"""
    
    def test_collection_progress_metrics(self):
        """Test CollectionProgressMetrics data structure"""
        metrics = CollectionProgressMetrics(
            total_papers_collected=1500,
            papers_per_minute=25.5,
            venues_completed=3,
            venues_in_progress=2,
            venues_remaining=5,
            total_venues=10,
            session_duration_minutes=60.0
        )
        
        self.assertEqual(metrics.total_papers_collected, 1500)
        self.assertEqual(metrics.papers_per_minute, 25.5)
        self.assertEqual(metrics.venues_completed, 3)
        self.assertEqual(metrics.total_venues, 10)
    
    def test_api_metrics(self):
        """Test APIMetrics data structure"""
        metrics = APIMetrics(
            api_name="semantic_scholar",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            success_rate=0.95,
            avg_response_time_ms=750.0,
            health_status="healthy"
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
            progress_percent=50.0,
            start_time=start_time,
            api_source="semantic_scholar"
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
            collection_progress=CollectionProgressMetrics(total_papers_collected=100),
            api_metrics={"test_api": APIMetrics(api_name="test_api")},
            processing_metrics=ProcessingMetrics(),
            system_metrics=SystemResourceMetrics(),
            state_metrics=StateManagementMetrics(),
            venue_progress={}
        )
        
        metrics_dict = system_metrics.to_dict()
        
        self.assertIn('timestamp', metrics_dict)
        self.assertIn('collection_progress', metrics_dict)
        self.assertIn('api_metrics', metrics_dict)
        self.assertIn('venue_progress', metrics_dict)
        
        # Check timestamp serialization
        self.assertEqual(metrics_dict['timestamp'], timestamp.isoformat())
        
        # Check nested structure serialization
        self.assertEqual(
            metrics_dict['collection_progress']['total_papers_collected'], 
            100
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
            collection_progress=CollectionProgressMetrics(total_papers_collected=papers_count),
            api_metrics={},
            processing_metrics=ProcessingMetrics(),
            system_metrics=SystemResourceMetrics(),
            state_metrics=StateManagementMetrics(),
            venue_progress={}
        )
    
    def test_add_metrics(self):
        """Test adding metrics to buffer"""
        self.assertEqual(self.buffer.size(), 0)
        
        self.buffer.add_metrics(self.test_metrics)
        self.assertEqual(self.buffer.size(), 1)
        
        latest = self.buffer.get_latest_metrics()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.collection_progress.total_papers_collected, 100)
    
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
        self.assertEqual(latest.collection_progress.total_papers_collected, 14)
    
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
        self.assertEqual(recent[-1].collection_progress.total_papers_collected, 4)
        self.assertEqual(recent[-2].collection_progress.total_papers_collected, 3)
        self.assertEqual(recent[-3].collection_progress.total_papers_collected, 2)
    
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
            thread = threading.Thread(
                target=add_metrics_worker,
                args=(worker_id, 10)
            )
            threads.append(thread)
        
        # 2 reader threads
        for _ in range(2):
            thread = threading.Thread(
                target=read_metrics_worker,
                args=(20,)
            )
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
        self.assertGreater(self.buffer.size(), 0)     # Has some data
        
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


if __name__ == '__main__':
    unittest.main()
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
