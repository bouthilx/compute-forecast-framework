"""
Unit tests for dashboard metrics data structures and metrics buffer.
Tests the core components of Issue #8 Real-Time Collection Dashboard.
"""

import unittest
from datetime import datetime, timedelta
import threading
import time

from src.monitoring.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
    APIMetrics,
    ProcessingMetrics,
    SystemResourceMetrics,
    StateManagementMetrics,
    VenueProgressMetrics,
    MetricsBuffer
)


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