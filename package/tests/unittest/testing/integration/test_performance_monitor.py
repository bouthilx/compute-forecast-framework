"""
Unit tests for Performance Monitor component
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.testing.integration.performance_monitor import (
    PerformanceMonitor,
    PerformanceProfile,
    ResourceSnapshot,
    BottleneckAnalyzer
)
from src.testing.integration.pipeline_test_framework import PipelinePhase


class TestResourceSnapshot:
    """Test ResourceSnapshot dataclass"""
    
    def test_snapshot_creation(self):
        """Test creating resource snapshot"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=45.5,
            memory_mb=1024.0,
            memory_percent=25.0,
            io_read_bytes=1000000,
            io_write_bytes=500000,
            network_bytes_sent=100000,
            network_bytes_recv=200000,
            thread_count=10,
            open_files=50
        )
        
        assert snapshot.cpu_percent == 45.5
        assert snapshot.memory_mb == 1024.0
        assert snapshot.io_read_bytes == 1000000
        
    def test_snapshot_comparison(self):
        """Test comparing snapshots for delta calculation"""
        snapshot1 = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=30.0,
            memory_mb=1000.0,
            io_read_bytes=1000000,
            io_write_bytes=500000
        )
        
        time.sleep(0.1)
        
        snapshot2 = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_mb=1200.0,
            io_read_bytes=1500000,
            io_write_bytes=700000
        )
        
        # Calculate deltas
        cpu_delta = snapshot2.cpu_percent - snapshot1.cpu_percent
        memory_delta = snapshot2.memory_mb - snapshot1.memory_mb
        io_read_delta = snapshot2.io_read_bytes - snapshot1.io_read_bytes
        
        assert cpu_delta == 20.0
        assert memory_delta == 200.0
        assert io_read_delta == 500000


class TestPerformanceProfile:
    """Test PerformanceProfile class"""
    
    def test_profile_initialization(self):
        """Test profile initialization"""
        profile = PerformanceProfile(phase=PipelinePhase.COLLECTION)
        
        assert profile.phase == PipelinePhase.COLLECTION
        assert len(profile.snapshots) == 0
        assert profile.peak_cpu == 0.0
        assert profile.peak_memory_mb == 0.0
        
    def test_add_snapshot(self):
        """Test adding snapshots to profile"""
        profile = PerformanceProfile(phase=PipelinePhase.ANALYSIS)
        
        snapshot1 = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=30.0,
            memory_mb=1000.0
        )
        
        snapshot2 = ResourceSnapshot(
            timestamp=time.time() + 1,
            cpu_percent=50.0,
            memory_mb=1200.0
        )
        
        profile.add_snapshot(snapshot1)
        profile.add_snapshot(snapshot2)
        
        assert len(profile.snapshots) == 2
        assert profile.peak_cpu == 50.0
        assert profile.peak_memory_mb == 1200.0
        
    def test_calculate_averages(self):
        """Test calculating average metrics"""
        profile = PerformanceProfile(phase=PipelinePhase.EXTRACTION)
        
        # Add multiple snapshots
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=time.time() + i,
                cpu_percent=20.0 + i * 10,  # 20, 30, 40, 50, 60
                memory_mb=1000.0 + i * 100   # 1000, 1100, 1200, 1300, 1400
            )
            profile.add_snapshot(snapshot)
            
        averages = profile.calculate_averages()
        
        assert averages["avg_cpu_percent"] == 40.0  # (20+30+40+50+60)/5
        assert averages["avg_memory_mb"] == 1200.0  # (1000+1100+1200+1300+1400)/5
        assert averages["peak_cpu_percent"] == 60.0
        assert averages["peak_memory_mb"] == 1400.0


class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""
    
    @pytest.fixture
    def monitor(self):
        """Create monitor instance"""
        return PerformanceMonitor()
        
    def test_monitor_initialization(self, monitor):
        """Test monitor initializes correctly"""
        assert monitor.profiles == {}
        assert monitor.is_monitoring is False
        assert monitor.monitoring_interval == 0.5
        
    def test_start_phase_monitoring(self, monitor):
        """Test starting monitoring for a phase"""
        monitor.start_phase_monitoring(PipelinePhase.COLLECTION)
        
        assert PipelinePhase.COLLECTION in monitor.profiles
        assert isinstance(monitor.profiles[PipelinePhase.COLLECTION], PerformanceProfile)
        
    @patch('psutil.Process')
    def test_collect_snapshot(self, mock_process_class, monitor):
        """Test collecting resource snapshot"""
        # Mock process metrics
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 45.5
        mock_process.memory_info.return_value.rss = 1073741824  # 1GB
        mock_process.memory_percent.return_value = 25.0
        mock_process.io_counters.return_value.read_bytes = 1000000
        mock_process.io_counters.return_value.write_bytes = 500000
        mock_process.num_threads.return_value = 10
        mock_process.open_files.return_value = []
        
        mock_process_class.return_value = mock_process
        
        # Reinitialize to use mocked process
        monitor = PerformanceMonitor()
        snapshot = monitor._collect_snapshot()
        
        assert snapshot.cpu_percent == 45.5
        assert snapshot.memory_mb == 1024.0  # 1GB in MB
        assert snapshot.io_read_bytes == 1000000
        
    def test_stop_phase_monitoring(self, monitor):
        """Test stopping monitoring for a phase"""
        monitor.start_phase_monitoring(PipelinePhase.ANALYSIS)
        time.sleep(0.1)  # Let it collect some data
        
        profile = monitor.stop_phase_monitoring(PipelinePhase.ANALYSIS)
        
        assert profile is not None
        assert profile.phase == PipelinePhase.ANALYSIS
        assert profile.end_time is not None
        assert profile.duration_seconds > 0
        
    def test_get_phase_summary(self, monitor):
        """Test getting phase performance summary"""
        # Start and stop monitoring
        monitor.start_phase_monitoring(PipelinePhase.PROJECTION)
        time.sleep(0.1)
        monitor.stop_phase_monitoring(PipelinePhase.PROJECTION)
        
        summary = monitor.get_phase_summary(PipelinePhase.PROJECTION)
        
        assert "phase" in summary
        assert "duration_seconds" in summary
        assert "peak_cpu_percent" in summary
        assert "peak_memory_mb" in summary
        assert summary["phase"] == "projection"
        
    def test_monitoring_thread_lifecycle(self, monitor):
        """Test monitoring thread starts and stops correctly"""
        monitor.start_monitoring()
        
        assert monitor.is_monitoring is True
        assert monitor._monitoring_thread is not None
        assert monitor._monitoring_thread.is_alive()
        
        monitor.stop_monitoring()
        
        assert monitor.is_monitoring is False
        # Thread should have stopped
        monitor._monitoring_thread.join(timeout=2)
        assert not monitor._monitoring_thread.is_alive()


class TestBottleneckAnalyzer:
    """Test BottleneckAnalyzer class"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return BottleneckAnalyzer()
        
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly"""
        assert analyzer.cpu_threshold == 80.0
        assert analyzer.memory_threshold_percent == 80.0
        assert analyzer.io_threshold_mbps == 100.0
        
    def test_analyze_cpu_bottleneck(self, analyzer):
        """Test CPU bottleneck detection"""
        profile = PerformanceProfile(phase=PipelinePhase.ANALYSIS)
        
        # Add high CPU snapshots
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=time.time() + i,
                cpu_percent=85.0 + i,  # All above threshold
                memory_mb=1000.0
            )
            profile.add_snapshot(snapshot)
            
        bottlenecks = analyzer.analyze_profile(profile)
        
        assert any("High CPU usage" in b for b in bottlenecks)
        
    def test_analyze_memory_bottleneck(self, analyzer):
        """Test memory bottleneck detection"""
        profile = PerformanceProfile(phase=PipelinePhase.EXTRACTION)
        
        # Add high memory snapshots
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=time.time() + i,
                cpu_percent=50.0,
                memory_mb=3500.0,  # High memory usage
                memory_percent=85.0  # Above threshold
            )
            profile.add_snapshot(snapshot)
            
        bottlenecks = analyzer.analyze_profile(profile, max_memory_mb=4096)
        
        assert any("High memory usage" in b for b in bottlenecks)
        
    def test_analyze_io_bottleneck(self, analyzer):
        """Test I/O bottleneck detection"""
        profile = PerformanceProfile(phase=PipelinePhase.COLLECTION)
        
        # Add snapshots with high I/O
        prev_io = 0
        for i in range(5):
            io_bytes = prev_io + (150 * 1024 * 1024)  # 150MB/s
            snapshot = ResourceSnapshot(
                timestamp=time.time() + i,
                cpu_percent=50.0,
                memory_mb=1000.0,
                io_read_bytes=io_bytes,
                io_write_bytes=io_bytes // 2
            )
            profile.add_snapshot(snapshot)
            prev_io = io_bytes
            
        # Finalize profile to calculate rates
        profile.finalize()
        
        bottlenecks = analyzer.analyze_profile(profile)
        
        assert any("High I/O" in b for b in bottlenecks)
        
    def test_generate_recommendations(self, analyzer):
        """Test recommendation generation"""
        bottlenecks = [
            "High CPU usage detected (avg: 85.0%)",
            "High memory usage detected (peak: 3800MB)",
            "Slow execution detected (duration: 120s)"
        ]
        
        recommendations = analyzer.generate_recommendations(bottlenecks)
        
        assert len(recommendations) > 0
        assert any("parallel processing" in r.lower() for r in recommendations)
        assert any("memory" in r.lower() for r in recommendations)
        assert any("batch" in r.lower() for r in recommendations)