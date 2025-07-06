"""
Unit tests for MetricsCollector functionality.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from compute_forecast.monitoring.metrics_collector import MetricsCollector
from compute_forecast.monitoring.dashboard_metrics import (
    SystemMetrics,
    CollectionProgressMetrics,
)
from compute_forecast.data.models import APIHealthStatus


class TestMetricsCollector:
    """Test MetricsCollector functionality"""

    def test_initialization(self):
        """Test metrics collector initialization"""
        collector = MetricsCollector(collection_interval_seconds=10)

        assert collector.collection_interval == 10
        assert not collector.is_collecting
        assert collector.collection_thread is None
        assert collector.venue_engine is None
        assert collector.state_manager is None
        assert collector.data_processors is None
        assert collector.session_id is None
        assert collector.collection_stats["metrics_collected"] == 0
        assert collector.collection_stats["collection_errors"] == 0

    def test_start_collection(self):
        """Test starting metrics collection"""
        collector = MetricsCollector(collection_interval_seconds=1)

        # Mock components
        venue_engine = Mock()
        state_manager = Mock()
        data_processors = {"test_processor": Mock()}

        collector.start_collection(venue_engine, state_manager, data_processors)

        assert collector.is_collecting
        assert collector.venue_engine == venue_engine
        assert collector.state_manager == state_manager
        assert collector.data_processors == data_processors
        assert collector.session_id is not None
        assert collector.collection_thread is not None
        assert collector.collection_thread.is_alive()

        # Cleanup
        collector.stop_collection()

    def test_stop_collection(self):
        """Test stopping metrics collection"""
        collector = MetricsCollector(collection_interval_seconds=1)

        # Start collection
        venue_engine = Mock()
        collector.start_collection(venue_engine, Mock(), {})

        assert collector.is_collecting

        # Stop collection
        collector.stop_collection()

        assert not collector.is_collecting
        # Thread should stop within reasonable time
        time.sleep(2)
        assert not collector.collection_thread.is_alive()

    def test_collect_current_metrics_with_mocks(self):
        """Test collecting current metrics with mocked components"""
        collector = MetricsCollector()

        # Mock venue engine
        venue_engine = Mock()
        venue_engine.get_collection_progress.return_value = {
            "total_venues": 100,
            "completed_venues": 25,
            "in_progress_venues": 3,
            "failed_venues": 2,
            "papers_collected": 2500,
            "estimated_total_papers": 10000,
        }
        venue_engine.get_api_health_status.return_value = {
            "semantic_scholar": APIHealthStatus(
                api_name="semantic_scholar",
                status="healthy",
                success_rate=0.95,
                avg_response_time_ms=450.0,
                consecutive_errors=0,
            )
        }
        venue_engine.get_venue_progress.return_value = {
            "NeurIPS_2024": {
                "status": "completed",
                "papers_collected": 100,
                "target_papers": 100,
                "completion_percentage": 100.0,
                "last_update_time": datetime.now(),
                "duration_minutes": 60.0,
                "estimated_remaining_minutes": 0.0,
            }
        }

        # Mock state manager
        state_manager = Mock()
        state_manager.get_checkpoint_statistics.return_value = {
            "checkpoints_created": 5,
            "last_checkpoint_time": datetime.now(),
            "rate_per_hour": 2.0,
            "recovery_possible": True,
            "recovery_success_rate": 1.0,
            "state_size_mb": 10.5,
            "checkpoint_size_mb": 5.2,
            "creation_time_ms": 150.0,
            "save_time_ms": 75.0,
        }

        # Mock data processors
        processors = {
            "venue_normalizer": Mock(),
            "deduplicator": Mock(),
            "computational_filter": Mock(),
        }
        processors["venue_normalizer"].get_mapping_statistics.return_value = {
            "venues_normalized": 50,
            "accuracy": 0.95,
            "rate_per_second": 10.0,
        }
        processors["deduplicator"].get_statistics.return_value = {
            "papers_processed": 2000,
            "duplicates_removed": 100,
            "deduplication_rate": 0.05,
            "confidence": 0.9,
        }
        processors["computational_filter"].get_statistics.return_value = {
            "papers_analyzed": 1900,
            "papers_above_threshold": 1500,
            "breakthrough_papers": 25,
            "rate_per_second": 5.0,
        }

        # Set up collector with mocks
        collector.venue_engine = venue_engine
        collector.state_manager = state_manager
        collector.data_processors = processors
        collector.session_start_time = datetime.now() - timedelta(minutes=30)
        collector.session_id = "test_session"

        # Collect metrics
        metrics = collector.collect_current_metrics()

        # Verify metrics
        assert isinstance(metrics, SystemMetrics)
        assert metrics.collection_progress.total_venues == 100
        assert metrics.collection_progress.papers_collected == 2500
        assert metrics.collection_progress.session_id == "test_session"
        assert "semantic_scholar" in metrics.api_metrics
        assert metrics.processing_metrics.venues_normalized == 50
        assert metrics.state_metrics.checkpoints_created == 5
        assert "NeurIPS_2024" in metrics.venue_progress

    def test_collect_current_metrics_performance(self):
        """Test that metrics collection completes within 2 seconds"""
        collector = MetricsCollector()

        # Set up minimal mocks to avoid none errors
        collector.venue_engine = None
        collector.state_manager = None
        collector.data_processors = {}
        collector.session_start_time = datetime.now()
        collector.session_id = "perf_test"

        # Measure collection time
        start_time = time.time()
        metrics = collector.collect_current_metrics()
        collection_time = time.time() - start_time

        # Should complete within 2 seconds
        assert collection_time < 2.0
        assert isinstance(metrics, SystemMetrics)

    def test_collect_current_metrics_error_handling(self):
        """Test error handling in metrics collection"""
        collector = MetricsCollector()

        # Mock venue engine that raises exception
        venue_engine = Mock()
        venue_engine.get_collection_progress.side_effect = Exception("Mock error")

        collector.venue_engine = venue_engine
        collector.state_manager = None
        collector.data_processors = {}
        collector.session_start_time = datetime.now()
        collector.session_id = "error_test"

        # Should handle error gracefully and return default metrics
        metrics = collector.collect_current_metrics()
        assert isinstance(metrics, SystemMetrics)
        assert metrics.collection_progress.papers_collected == 0

    def test_get_metrics_summary(self):
        """Test metrics summary generation"""
        collector = MetricsCollector()

        # Add some test metrics to buffer
        for i in range(5):
            test_metrics = self._create_test_metrics(i * 100, i * 2.0)
            collector.metrics_buffer.add_metrics(test_metrics)

        # Get summary
        summary = collector.get_metrics_summary(time_window_minutes=60)

        assert summary.time_period_minutes == 60
        assert summary.total_papers_collected == 400  # Max from test data
        assert summary.avg_collection_rate == 4.0  # Average of 0, 2, 4, 6, 8
        assert summary.peak_collection_rate == 8.0  # Max from test data

    def test_collection_statistics(self):
        """Test collection statistics tracking"""
        collector = MetricsCollector()
        collector.session_id = "stats_test"
        collector.session_start_time = datetime.now()

        # Simulate some collection activity
        collector.collection_stats["metrics_collected"] = 10
        collector.collection_stats["collection_errors"] = 2
        collector.collection_stats["last_collection_time"] = datetime.now()

        stats = collector.get_collection_statistics()

        assert stats["session_id"] == "stats_test"
        assert stats["metrics_collected"] == 10
        assert stats["collection_errors"] == 2
        assert not stats["is_collecting"]
        assert "session_start_time" in stats
        assert "collection_interval_seconds" in stats

    @patch("time.sleep")  # Mock sleep to speed up test
    def test_collection_loop_integration(self, mock_sleep):
        """Test the collection loop runs correctly"""
        # Make sleep return immediately
        mock_sleep.return_value = None

        collector = MetricsCollector(collection_interval_seconds=0.1)

        # Mock components
        venue_engine = Mock()
        venue_engine.get_collection_progress.return_value = {"papers_collected": 100}
        venue_engine.get_api_health_status.return_value = {}
        venue_engine.get_venue_progress.return_value = {}

        # Start collection
        collector.start_collection(venue_engine, Mock(), {})

        # Let it run briefly
        time.sleep(0.5)

        # Stop collection
        collector.stop_collection()

        # Should have collected some metrics
        assert collector.collection_stats["metrics_collected"] > 0
        assert len(collector.metrics_buffer.metrics) > 0

    def _create_test_metrics(
        self, papers_collected: int, papers_per_minute: float
    ) -> SystemMetrics:
        """Helper to create test metrics"""
        from compute_forecast.monitoring.dashboard_metrics import (
            SystemMetrics,
            ProcessingMetrics,
            SystemResourceMetrics,
            StateManagementMetrics,
        )

        return SystemMetrics(
            timestamp=datetime.now(),
            collection_progress=CollectionProgressMetrics(
                session_id="test",
                total_venues=100,
                completed_venues=papers_collected // 100,
                in_progress_venues=1,
                failed_venues=0,
                papers_collected=papers_collected,
                papers_per_minute=papers_per_minute,
                estimated_total_papers=1000,
                completion_percentage=papers_collected / 10.0,
                session_duration_minutes=papers_collected * 0.1,
                estimated_remaining_minutes=(1000 - papers_collected) * 0.1,
                estimated_completion_time=datetime.now(),
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
                filtering_rate_per_second=0.0,
            ),
            system_metrics=SystemResourceMetrics.collect_current(),
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
                state_save_time_ms=0.0,
            ),
            venue_progress={},
        )
