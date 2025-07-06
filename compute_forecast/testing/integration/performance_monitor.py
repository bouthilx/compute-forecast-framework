"""
Performance monitoring system for pipeline testing.
Provides detailed resource tracking and bottleneck analysis.
"""

import time
import threading
import psutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import statistics

from compute_forecast.testing.integration.pipeline_test_framework import PipelinePhase


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time"""

    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float = 0.0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    thread_count: int = 0
    open_files: int = 0

    def io_total_bytes(self) -> int:
        """Total I/O bytes"""
        return self.io_read_bytes + self.io_write_bytes

    def network_total_bytes(self) -> int:
        """Total network bytes"""
        return self.network_bytes_sent + self.network_bytes_recv


class PerformanceProfile:
    """Performance profile for a pipeline phase"""

    def __init__(self, phase: PipelinePhase):
        self.phase = phase
        self.snapshots: List[ResourceSnapshot] = []
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.duration_seconds: float = 0.0
        self.peak_cpu: float = 0.0
        self.peak_memory_mb: float = 0.0
        self.total_io_bytes: int = 0
        self.total_network_bytes: int = 0

    def add_snapshot(self, snapshot: ResourceSnapshot) -> None:
        """Add a resource snapshot"""
        self.snapshots.append(snapshot)

        # Update peaks
        self.peak_cpu = max(self.peak_cpu, snapshot.cpu_percent)
        self.peak_memory_mb = max(self.peak_memory_mb, snapshot.memory_mb)

    def finalize(self) -> None:
        """Mark profile as complete"""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time

        # Calculate total I/O and network
        if len(self.snapshots) >= 2:
            first = self.snapshots[0]
            last = self.snapshots[-1]
            self.total_io_bytes = (last.io_read_bytes - first.io_read_bytes) + (
                last.io_write_bytes - first.io_write_bytes
            )
            self.total_network_bytes = (
                last.network_bytes_sent - first.network_bytes_sent
            ) + (last.network_bytes_recv - first.network_bytes_recv)

    def calculate_averages(self) -> Dict[str, float]:
        """Calculate average metrics"""
        if not self.snapshots:
            return {
                "avg_cpu_percent": 0.0,
                "avg_memory_mb": 0.0,
                "peak_cpu_percent": 0.0,
                "peak_memory_mb": 0.0,
                "min_cpu_percent": 0.0,
                "min_memory_mb": 0.0,
                "cpu_std_dev": 0.0,
                "memory_std_dev": 0.0,
            }

        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]

        return {
            "avg_cpu_percent": statistics.mean(cpu_values),
            "avg_memory_mb": statistics.mean(memory_values),
            "peak_cpu_percent": max(cpu_values),
            "peak_memory_mb": max(memory_values),
            "min_cpu_percent": min(cpu_values),
            "min_memory_mb": min(memory_values),
            "cpu_std_dev": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0.0,
            "memory_std_dev": statistics.stdev(memory_values)
            if len(memory_values) > 1
            else 0.0,
        }

    def get_io_rate_mbps(self) -> float:
        """Calculate I/O rate in MB/s"""
        if self.duration_seconds > 0:
            return (self.total_io_bytes / 1024 / 1024) / self.duration_seconds
        return 0.0

    def get_network_rate_mbps(self) -> float:
        """Calculate network rate in MB/s"""
        if self.duration_seconds > 0:
            return (self.total_network_bytes / 1024 / 1024) / self.duration_seconds
        return 0.0


class PerformanceMonitor:
    """
    Monitor system performance during pipeline execution.
    Tracks CPU, memory, I/O, and network usage per phase.
    """

    def __init__(self, monitoring_interval: float = 0.5):
        self.monitoring_interval = monitoring_interval
        self.profiles: Dict[PipelinePhase, PerformanceProfile] = {}
        self.current_phase: Optional[PipelinePhase] = None
        self.is_monitoring: bool = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Initialize process handle
        try:
            self._process = psutil.Process()
        except Exception:
            self._process = None

    def start_monitoring(self) -> None:
        """Start the monitoring thread"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self._stop_event.clear()
            self._monitoring_thread = threading.Thread(target=self._monitor_loop)
            self._monitoring_thread.daemon = True
            self._monitoring_thread.start()

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        if self.is_monitoring:
            self.is_monitoring = False
            self._stop_event.set()
            if self._monitoring_thread:
                self._monitoring_thread.join(timeout=2)

    def start_phase_monitoring(self, phase: PipelinePhase) -> None:
        """Start monitoring a specific phase"""
        self.current_phase = phase
        self.profiles[phase] = PerformanceProfile(phase)

    def stop_phase_monitoring(self, phase: PipelinePhase) -> PerformanceProfile:
        """Stop monitoring a phase and return its profile"""
        if phase in self.profiles:
            profile = self.profiles[phase]
            profile.finalize()

        if self.current_phase == phase:
            self.current_phase = None

        return self.profiles.get(phase)

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                if self.current_phase and self.current_phase in self.profiles:
                    snapshot = self._collect_snapshot()
                    self.profiles[self.current_phase].add_snapshot(snapshot)

                self._stop_event.wait(self.monitoring_interval)

            except Exception as e:
                print(f"Monitoring error: {e}")

    def _collect_snapshot(self) -> ResourceSnapshot:
        """Collect current resource usage"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(), cpu_percent=0.0, memory_mb=0.0
        )

        if self._process:
            try:
                # CPU usage
                snapshot.cpu_percent = self._process.cpu_percent(interval=0.1)

                # Memory usage
                memory_info = self._process.memory_info()
                snapshot.memory_mb = memory_info.rss / 1024 / 1024
                snapshot.memory_percent = self._process.memory_percent()

                # I/O counters
                try:
                    io_counters = self._process.io_counters()
                    snapshot.io_read_bytes = io_counters.read_bytes
                    snapshot.io_write_bytes = io_counters.write_bytes
                except Exception:
                    pass  # Not available on all platforms

                # Network (system-wide, not process-specific)
                try:
                    net_counters = psutil.net_io_counters()
                    snapshot.network_bytes_sent = net_counters.bytes_sent
                    snapshot.network_bytes_recv = net_counters.bytes_recv
                except Exception:
                    pass

                # Thread count
                snapshot.thread_count = self._process.num_threads()

                # Open files
                try:
                    snapshot.open_files = len(self._process.open_files())
                except Exception:
                    pass

            except psutil.NoSuchProcess:
                pass  # Process terminated

        return snapshot

    def get_phase_summary(self, phase: PipelinePhase) -> Dict[str, Any]:
        """Get performance summary for a phase"""
        if phase not in self.profiles:
            return {}

        profile = self.profiles[phase]
        averages = profile.calculate_averages()

        return {
            "phase": phase.value,
            "duration_seconds": profile.duration_seconds,
            "snapshot_count": len(profile.snapshots),
            "peak_cpu_percent": profile.peak_cpu,
            "peak_memory_mb": profile.peak_memory_mb,
            "avg_cpu_percent": averages["avg_cpu_percent"],
            "avg_memory_mb": averages["avg_memory_mb"],
            "cpu_std_dev": averages["cpu_std_dev"],
            "memory_std_dev": averages["memory_std_dev"],
            "total_io_mb": profile.total_io_bytes / 1024 / 1024,
            "io_rate_mbps": profile.get_io_rate_mbps(),
            "total_network_mb": profile.total_network_bytes / 1024 / 1024,
            "network_rate_mbps": profile.get_network_rate_mbps(),
        }

    def get_all_summaries(self) -> Dict[PipelinePhase, Dict[str, Any]]:
        """Get summaries for all monitored phases"""
        return {phase: self.get_phase_summary(phase) for phase in self.profiles}


class BottleneckAnalyzer:
    """Analyze performance profiles to identify bottlenecks"""

    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold_percent: float = 80.0,
        io_threshold_mbps: float = 100.0,
    ):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold_percent = memory_threshold_percent
        self.io_threshold_mbps = io_threshold_mbps

    def analyze_profile(
        self, profile: PerformanceProfile, max_memory_mb: float = 4096.0
    ) -> List[str]:
        """Analyze a performance profile for bottlenecks"""
        bottlenecks = []

        if not profile.snapshots:
            return bottlenecks

        averages = profile.calculate_averages()

        # CPU bottleneck
        if averages["avg_cpu_percent"] > self.cpu_threshold:
            bottlenecks.append(
                f"High CPU usage detected (avg: {averages['avg_cpu_percent']:.1f}%, "
                f"peak: {profile.peak_cpu:.1f}%)"
            )

        # Memory bottleneck
        memory_percent = (profile.peak_memory_mb / max_memory_mb) * 100
        if memory_percent > self.memory_threshold_percent:
            bottlenecks.append(
                f"High memory usage detected (peak: {profile.peak_memory_mb:.0f}MB, "
                f"{memory_percent:.1f}% of limit)"
            )

        # I/O bottleneck
        io_rate = profile.get_io_rate_mbps()
        if io_rate > self.io_threshold_mbps:
            bottlenecks.append(f"High I/O rate detected ({io_rate:.1f} MB/s)")

        # Duration bottleneck (phase taking too long)
        if profile.duration_seconds > 60:  # More than 1 minute per phase
            bottlenecks.append(
                f"Slow execution detected (duration: {profile.duration_seconds:.1f}s)"
            )

        # High variance (unstable performance)
        if averages["cpu_std_dev"] > 20:
            bottlenecks.append(
                f"Unstable CPU usage detected (std dev: {averages['cpu_std_dev']:.1f}%)"
            )

        return bottlenecks

    def analyze_all_profiles(
        self,
        profiles: Dict[PipelinePhase, PerformanceProfile],
        max_memory_mb: float = 4096.0,
    ) -> Dict[PipelinePhase, List[str]]:
        """Analyze all profiles for bottlenecks"""
        results = {}

        for phase, profile in profiles.items():
            results[phase] = self.analyze_profile(profile, max_memory_mb)

        return results

    def generate_recommendations(self, bottlenecks: List[str]) -> List[str]:
        """Generate recommendations based on bottlenecks"""
        recommendations = []

        for bottleneck in bottlenecks:
            if "High CPU usage" in bottleneck:
                recommendations.append(
                    "Consider implementing parallel processing or optimizing algorithms"
                )
                recommendations.append(
                    "Profile CPU-intensive operations to identify optimization opportunities"
                )

            elif "High memory usage" in bottleneck:
                recommendations.append(
                    "Implement streaming or batch processing to reduce memory footprint"
                )
                recommendations.append(
                    "Consider using memory-efficient data structures"
                )

            elif "High I/O rate" in bottleneck:
                recommendations.append(
                    "Implement caching to reduce redundant I/O operations"
                )
                recommendations.append(
                    "Consider using bulk operations or asynchronous I/O"
                )

            elif "Slow execution" in bottleneck:
                recommendations.append(
                    "Break down the phase into smaller, parallelizable tasks"
                )
                recommendations.append(
                    "Consider implementing progress checkpoints for long-running operations"
                )

            elif "Unstable CPU usage" in bottleneck:
                recommendations.append("Investigate sources of performance variance")
                recommendations.append(
                    "Consider implementing resource pooling or connection reuse"
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return unique_recommendations
