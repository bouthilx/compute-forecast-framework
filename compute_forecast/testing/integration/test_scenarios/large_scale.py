"""
Large Scale Test Scenario
Tests pipeline scalability with 10,000 papers to validate linear scaling.
Verifies memory optimization and streaming/batching capabilities.
"""

import time
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from compute_forecast.testing.integration.pipeline_test_framework import (
    EndToEndTestFramework,
    PipelineConfig,
)
from compute_forecast.testing.integration.performance_monitor import (
    PerformanceMonitor,
    BottleneckAnalyzer,
)
from compute_forecast.testing.mock_data.generators import MockDataGenerator
from compute_forecast.data.models import Paper


@dataclass
class LargeScaleResult:
    """Result of large scale test"""

    success: bool
    execution_time_seconds: float
    papers_processed: int
    throughput_papers_per_second: float
    peak_memory_mb: float
    memory_efficiency: float  # Papers per MB
    scaling_factor: float  # Actual vs expected performance
    phases_completed: List[str]
    performance_metrics: Dict[str, Any]
    memory_usage_over_time: List[Dict[str, float]]
    bottlenecks: List[str]
    scaling_issues: List[str]
    recommendations: List[str]
    errors: List[str]


class LargeScaleTestScenario:
    """
    Large scale test scenario for 10,000 papers.

    Success Criteria:
    - Linear scaling compared to 1000 paper baseline
    - Memory usage stays under 8GB (2x the 4GB baseline)
    - Throughput maintains reasonable rate (>5 papers/second)
    - No memory leaks (stable memory growth pattern)
    - Successful completion of all phases
    """

    def __init__(self, baseline_time_1k: float = 300.0):
        self.config = PipelineConfig(
            test_data_size=10000,
            max_execution_time_seconds=3600,  # 1 hour max
            max_memory_usage_mb=8192,  # 8GB
            enable_profiling=True,
            enable_error_injection=False,
            batch_size=500,  # Larger batches for efficiency
            parallel_workers=8,  # More workers for scalability
        )

        self.baseline_time_1k = baseline_time_1k
        self.expected_time_10k = baseline_time_1k * 10  # Linear scaling expectation

        self.framework = EndToEndTestFramework(self.config)
        self.performance_monitor = PerformanceMonitor(
            monitoring_interval=1.0
        )  # Sample every second
        self.bottleneck_analyzer = BottleneckAnalyzer()

        # Memory tracking for leak detection
        self.memory_samples: List[Dict[str, Any]] = []
        self._memory_tracking_thread: Optional[threading.Thread] = None
        self._stop_memory_tracking = threading.Event()

        # Setup mock data generator with larger datasets
        self.mock_generator = MockDataGenerator()

        # Import configs

    def run_test(self) -> LargeScaleResult:
        """Execute the large scale test scenario"""
        start_time = time.time()

        print("🎯 Large Scale Test - Generating 10,000 test papers...")
        print("   This test validates pipeline scalability and memory efficiency")

        # Generate test data in batches to avoid memory issues during generation
        test_papers = self._generate_test_data_batched()
        print(f"   ✓ Generated {len(test_papers)} papers")

        # Start detailed monitoring
        self._start_memory_tracking()
        self.performance_monitor.start_monitoring()

        try:
            # Execute pipeline
            print("   🚀 Starting large-scale pipeline execution...")
            pipeline_result = self.framework.run_pipeline(test_papers)

            # Stop monitoring
            self._stop_memory_tracking_thread()
            self.performance_monitor.stop_monitoring()

            # Analyze results
            execution_time = time.time() - start_time
            result = self._analyze_large_scale_results(
                pipeline_result, execution_time, len(test_papers)
            )

            self._print_results(result)
            return result

        except Exception as e:
            self._stop_memory_tracking_thread()
            self.performance_monitor.stop_monitoring()

            return LargeScaleResult(
                success=False,
                execution_time_seconds=time.time() - start_time,
                papers_processed=len(test_papers),
                throughput_papers_per_second=0,
                peak_memory_mb=0,
                memory_efficiency=0,
                scaling_factor=0,
                phases_completed=[],
                performance_metrics={},
                memory_usage_over_time=self.memory_samples,
                bottlenecks=[],
                scaling_issues=[f"Test execution failed: {str(e)}"],
                recommendations=[],
                errors=[str(e)],
            )

    def _generate_test_data_batched(self) -> List[Paper]:
        """Generate test data in batches to manage memory"""
        from compute_forecast.testing.mock_data.configs import (
            MockDataConfig,
            DataQuality,
        )

        print("   📝 Generating papers in batches...")

        batch_size = 1000
        all_papers = []

        for batch_num in range(0, self.config.test_data_size, batch_size):
            current_batch_size = min(batch_size, self.config.test_data_size - batch_num)

            mock_config = MockDataConfig(
                size=current_batch_size, quality=DataQuality.NORMAL
            )
            batch_papers = self.mock_generator.generate(mock_config)
            all_papers.extend(batch_papers)

            if (batch_num // batch_size + 1) % 5 == 0:  # Progress every 5 batches
                print(f"      Generated {len(all_papers)} papers...")

        return all_papers

    def _start_memory_tracking(self) -> None:
        """Start detailed memory tracking thread"""
        self._stop_memory_tracking.clear()
        self._memory_tracking_thread = threading.Thread(
            target=self._memory_tracking_loop
        )
        self._memory_tracking_thread.daemon = True
        self._memory_tracking_thread.start()

    def _memory_tracking_loop(self) -> None:
        """Track memory usage over time"""
        import psutil

        process = psutil.Process()

        while not self._stop_memory_tracking.is_set():
            try:
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=0.1)

                self.memory_samples.append(
                    {
                        "timestamp": time.time(),
                        "memory_mb": memory_mb,
                        "cpu_percent": cpu_percent,
                    }
                )

                self._stop_memory_tracking.wait(2.0)  # Sample every 2 seconds

            except Exception as e:
                print(f"Memory tracking error: {e}")
                break

    def _stop_memory_tracking_thread(self) -> None:
        """Stop memory tracking thread"""
        if self._memory_tracking_thread:
            self._stop_memory_tracking.set()
            self._memory_tracking_thread.join(timeout=5)

    def _analyze_large_scale_results(
        self,
        pipeline_result: Dict[str, Any],
        execution_time: float,
        papers_processed: int,
    ) -> LargeScaleResult:
        """Analyze large scale test results"""

        # Calculate throughput
        throughput = papers_processed / execution_time if execution_time > 0 else 0

        # Get peak memory
        peak_memory = self._get_peak_memory_usage()

        # Calculate memory efficiency
        memory_efficiency = papers_processed / peak_memory if peak_memory > 0 else 0

        # Calculate scaling factor (actual vs expected)
        scaling_factor = (
            execution_time / self.expected_time_10k if self.expected_time_10k > 0 else 0
        )

        # Analyze performance metrics
        performance_metrics = self._analyze_performance_metrics()

        # Identify bottlenecks and scaling issues
        bottlenecks = self._identify_bottlenecks(performance_metrics)
        scaling_issues = self._identify_scaling_issues(
            execution_time, peak_memory, throughput, scaling_factor
        )

        # Generate recommendations
        recommendations = self._generate_scaling_recommendations(
            bottlenecks, scaling_issues, performance_metrics
        )

        # Determine success
        success = (
            pipeline_result["success"]
            and execution_time < self.config.max_execution_time_seconds
            and peak_memory < self.config.max_memory_usage_mb
            and throughput > 5.0  # Minimum 5 papers/second
            and scaling_factor < 2.0  # No worse than 2x linear scaling
        )

        return LargeScaleResult(
            success=success,
            execution_time_seconds=execution_time,
            papers_processed=papers_processed,
            throughput_papers_per_second=throughput,
            peak_memory_mb=peak_memory,
            memory_efficiency=memory_efficiency,
            scaling_factor=scaling_factor,
            phases_completed=pipeline_result["phases_completed"],
            performance_metrics=performance_metrics,
            memory_usage_over_time=self.memory_samples,
            bottlenecks=bottlenecks,
            scaling_issues=scaling_issues,
            recommendations=recommendations,
            errors=pipeline_result["errors"],
        )

    def _get_peak_memory_usage(self) -> float:
        """Get peak memory usage from samples"""
        if not self.memory_samples:
            return 0.0
        return float(max(sample["memory_mb"] for sample in self.memory_samples))

    def _analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analyze detailed performance metrics"""
        profiles = self.performance_monitor.profiles
        analysis = {
            "overall": {
                "total_phases": len(profiles),
                "total_snapshots": sum(len(p.snapshots) for p in profiles.values()),
            }
        }

        for phase, profile in profiles.items():
            if profile.snapshots:
                averages = profile.calculate_averages()
                analysis[phase.value] = {
                    "duration": int(profile.duration_seconds),
                    "snapshots": len(profile.snapshots),
                    "peak_cpu": int(profile.peak_cpu),
                    "peak_memory": int(profile.peak_memory_mb),
                    "avg_cpu": int(averages["avg_cpu_percent"]),
                    "avg_memory": int(averages["avg_memory_mb"]),
                    "cpu_variance": int(averages["cpu_std_dev"]),
                    "memory_variance": int(averages["memory_std_dev"]),
                    "io_rate": int(profile.get_io_rate_mbps()),
                    "network_rate": int(profile.get_network_rate_mbps()),
                }

        return analysis

    def _identify_bottlenecks(self, performance_metrics: Dict[str, Any]) -> List[str]:
        """Identify performance bottlenecks specific to large scale"""
        bottlenecks = []

        for phase_name, phase_data in performance_metrics.items():
            if phase_name == "overall" or not isinstance(phase_data, dict):
                continue

            # CPU bottlenecks (more lenient for large scale)
            if phase_data.get("avg_cpu", 0) > 85:
                bottlenecks.append(
                    f"{phase_name}: Very high CPU usage ({phase_data['avg_cpu']:.1f}%)"
                )

            # Memory bottlenecks
            if phase_data.get("peak_memory", 0) > 6000:  # 75% of 8GB
                bottlenecks.append(
                    f"{phase_name}: High memory usage ({phase_data['peak_memory']:.0f}MB)"
                )

            # Duration bottlenecks (proportional to scale)
            if phase_data.get("duration", 0) > 600:  # 10 minutes per phase
                bottlenecks.append(
                    f"{phase_name}: Very slow execution ({phase_data['duration']:.1f}s)"
                )

            # High variance indicates instability
            if phase_data.get("cpu_variance", 0) > 30:
                bottlenecks.append(
                    f"{phase_name}: Unstable CPU performance (variance: {phase_data['cpu_variance']:.1f})"
                )

        return bottlenecks

    def _identify_scaling_issues(
        self,
        execution_time: float,
        peak_memory: float,
        throughput: float,
        scaling_factor: float,
    ) -> List[str]:
        """Identify scaling-specific issues"""
        issues = []

        # Poor scaling
        if scaling_factor > 1.5:
            issues.append(f"Poor scaling: {scaling_factor:.2f}x worse than linear")

        # Memory scaling issues
        expected_memory = 4096 * 10  # Linear scaling from 4GB baseline
        if peak_memory > expected_memory * 0.5:  # More than 50% of linear scaling
            issues.append(
                f"Memory scaling issue: {peak_memory:.0f}MB (expected ~{expected_memory * 0.5:.0f}MB)"
            )

        # Throughput issues
        if throughput < 5:
            issues.append(f"Low throughput: {throughput:.1f} papers/second")

        # Memory leak detection
        if len(self.memory_samples) > 10:
            early_avg = sum(s["memory_mb"] for s in self.memory_samples[:5]) / 5
            late_avg = sum(s["memory_mb"] for s in self.memory_samples[-5:]) / 5
            growth_rate = (late_avg - early_avg) / early_avg

            if growth_rate > 0.5:  # 50% growth suggests leak
                issues.append(
                    f"Potential memory leak: {growth_rate * 100:.1f}% growth during execution"
                )

        return issues

    def _generate_scaling_recommendations(
        self,
        bottlenecks: List[str],
        scaling_issues: List[str],
        performance_metrics: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations for large scale optimization"""
        recommendations = []

        # Memory optimization
        if any("memory" in issue.lower() for issue in scaling_issues + bottlenecks):
            recommendations.extend(
                [
                    "Implement streaming processing to reduce memory footprint",
                    "Consider using memory-mapped files for large datasets",
                    "Implement garbage collection optimization",
                    "Use batch processing with smaller batch sizes",
                ]
            )

        # Performance optimization
        if any("cpu" in bottleneck.lower() for bottleneck in bottlenecks):
            recommendations.extend(
                [
                    "Implement parallel processing for CPU-intensive phases",
                    "Consider using multiprocessing instead of threading",
                    "Profile and optimize hot code paths",
                ]
            )

        # Scaling optimization
        if any("scaling" in issue.lower() for issue in scaling_issues):
            recommendations.extend(
                [
                    "Implement horizontal scaling across multiple machines",
                    "Use asynchronous processing where possible",
                    "Consider distributed computing frameworks",
                ]
            )

        # Throughput optimization
        if any("throughput" in issue.lower() for issue in scaling_issues):
            recommendations.extend(
                [
                    "Optimize I/O operations with caching",
                    "Implement connection pooling",
                    "Use bulk operations instead of individual processing",
                ]
            )

        return list(set(recommendations))  # Remove duplicates

    def _print_results(self, result: LargeScaleResult) -> None:
        """Print large scale test results"""
        print("\n" + "=" * 70)
        print("🎯 LARGE SCALE TEST RESULTS (10,000 Papers)")
        print("=" * 70)

        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Execution Time: {result.execution_time_seconds:.1f}s")
        print(f"Expected Time (linear): {self.expected_time_10k:.1f}s")
        print(f"Scaling Factor: {result.scaling_factor:.2f}x")
        print(f"Throughput: {result.throughput_papers_per_second:.1f} papers/second")
        print(
            f"Peak Memory: {result.peak_memory_mb:.0f}MB (limit: {self.config.max_memory_usage_mb}MB)"
        )
        print(f"Memory Efficiency: {result.memory_efficiency:.2f} papers/MB")
        print(f"Papers Processed: {result.papers_processed}")
        print(
            f"Phases Completed: {len(result.phases_completed)}/{len(self.config.phases_to_test or [])}"
        )

        if result.scaling_issues:
            print("\n⚠️ Scaling Issues:")
            for issue in result.scaling_issues:
                print(f"   • {issue}")

        if result.bottlenecks:
            print("\n🔍 Performance Bottlenecks:")
            for bottleneck in result.bottlenecks:
                print(f"   • {bottleneck}")

        if result.recommendations:
            print("\n💡 Scaling Recommendations:")
            for rec in result.recommendations[:5]:  # Show top 5
                print(f"   • {rec}")

        if result.errors:
            print("\n❌ Errors:")
            for error in result.errors:
                print(f"   • {error}")

        print("=" * 70)


def run_large_scale_test(baseline_time_1k: float = 300.0) -> LargeScaleResult:
    """Convenience function to run large scale test"""
    scenario = LargeScaleTestScenario(baseline_time_1k)
    return scenario.run_test()


if __name__ == "__main__":
    # Run large scale test
    result = run_large_scale_test()
    exit(0 if result.success else 1)
