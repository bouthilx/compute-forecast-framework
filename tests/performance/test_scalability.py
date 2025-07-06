"""
Scalability Tests for validating system performance at scale.
"""

import time
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Any

from compute_forecast.orchestration.venue_collection_orchestrator import (
    VenueCollectionOrchestrator,
)
from compute_forecast.data.models import CollectionConfig


@dataclass
class ScalabilityTestResult:
    """Scalability test result"""

    test_name: str
    success: bool
    duration_seconds: float
    scale_factor: int
    baseline_throughput: float
    scaled_throughput: float
    scalability_efficiency: float
    resource_scaling: Dict[str, float]
    bottlenecks_at_scale: List[str] = field(default_factory=list)
    scaling_recommendations: List[str] = field(default_factory=list)


@dataclass
class LoadTestResult:
    """Load test result"""

    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    peak_response_time: float
    throughput_per_second: float
    error_rate: float
    resource_utilization: Dict[str, float] = field(default_factory=dict)


class ScalabilityTest:
    """System scalability testing"""

    def test_horizontal_scaling(self) -> ScalabilityTestResult:
        """Test horizontal scaling with multiple orchestrator instances"""

        test_start = time.time()

        result = ScalabilityTestResult(
            test_name="horizontal_scaling",
            success=False,
            duration_seconds=0.0,
            scale_factor=0,
            baseline_throughput=0.0,
            scaled_throughput=0.0,
            scalability_efficiency=0.0,
            resource_scaling={},
        )

        try:
            # Test with 1, 2, and 4 instances
            scaling_results = []

            for instance_count in [1, 2, 4]:
                instance_start = time.time()
                initial_memory = psutil.virtual_memory().used / (1024**2)

                # Create multiple orchestrator instances
                orchestrators = []
                session_ids = []

                for i in range(instance_count):
                    config = CollectionConfig(
                        max_venues_per_batch=2, batch_timeout_seconds=180
                    )
                    orchestrator = VenueCollectionOrchestrator(config)
                    init_result = orchestrator.initialize_system()

                    if init_result.success:
                        orchestrators.append(orchestrator)
                        session_id = orchestrator.start_collection_session()
                        session_ids.append(session_id)

                if not orchestrators:
                    continue

                # Run collections concurrently
                with ThreadPoolExecutor(max_workers=instance_count) as executor:
                    futures = []

                    for i, (orchestrator, session_id) in enumerate(
                        zip(orchestrators, session_ids)
                    ):
                        # Each instance gets different venues to avoid conflicts
                        test_venues = [["ICML"], ["ICLR"], ["NeurIPS"], ["AAAI"]][i % 4]
                        future = executor.submit(
                            orchestrator.execute_venue_collection,
                            session_id,
                            test_venues,
                            [2024],
                        )
                        futures.append(future)

                    # Collect results
                    total_papers = 0
                    successful_collections = 0

                    for future in as_completed(
                        futures, timeout=300
                    ):  # 5 minute timeout
                        try:
                            collection_result = future.result()
                            if collection_result.success:
                                total_papers += collection_result.raw_papers_collected
                                successful_collections += 1
                        except Exception:
                            pass

                instance_duration = time.time() - instance_start
                final_memory = psutil.virtual_memory().used / (1024**2)

                throughput = (
                    total_papers / (instance_duration / 60)
                    if instance_duration > 0
                    else 0
                )

                scaling_results.append(
                    {
                        "instances": instance_count,
                        "throughput": throughput,
                        "papers_collected": total_papers,
                        "successful_collections": successful_collections,
                        "memory_usage": final_memory - initial_memory,
                        "duration": instance_duration,
                    }
                )

                # Cleanup
                for orchestrator in orchestrators:
                    try:
                        orchestrator.shutdown_system()
                    except:
                        pass

            # Analyze scaling results
            if len(scaling_results) >= 2:
                baseline = scaling_results[0]
                scaled = scaling_results[-1]

                result.baseline_throughput = baseline["throughput"]
                result.scaled_throughput = scaled["throughput"]
                result.scale_factor = scaled["instances"]

                # Calculate efficiency (ideally should be 1.0 for perfect scaling)
                expected_throughput = baseline["throughput"] * scaled["instances"]
                result.scalability_efficiency = (
                    scaled["throughput"] / expected_throughput
                    if expected_throughput > 0
                    else 0
                )

                result.resource_scaling = {
                    "memory_per_instance": scaled["memory_usage"] / scaled["instances"],
                    "throughput_per_instance": scaled["throughput"]
                    / scaled["instances"],
                }

                # Success if efficiency is > 70%
                result.success = result.scalability_efficiency > 0.7

                # Analysis
                if result.scalability_efficiency < 0.5:
                    result.bottlenecks_at_scale.append("poor_horizontal_scaling")
                    result.scaling_recommendations.append(
                        "Investigate resource contention and optimize concurrent processing"
                    )
                elif result.scalability_efficiency < 0.8:
                    result.bottlenecks_at_scale.append("moderate_scaling_overhead")
                    result.scaling_recommendations.append(
                        "Optimize resource sharing and reduce synchronization overhead"
                    )

        except Exception as e:
            result.bottlenecks_at_scale.append(
                f"horizontal_scaling_test_failed: {str(e)}"
            )

        finally:
            result.duration_seconds = time.time() - test_start

        return result

    def test_vertical_scaling(self) -> ScalabilityTestResult:
        """Test vertical scaling with increased resources per instance"""

        test_start = time.time()

        result = ScalabilityTestResult(
            test_name="vertical_scaling",
            success=False,
            duration_seconds=0.0,
            scale_factor=0,
            baseline_throughput=0.0,
            scaled_throughput=0.0,
            scalability_efficiency=0.0,
            resource_scaling={},
        )

        try:
            # Test with different batch sizes (simulating resource scaling)
            scaling_configs = [
                {"batch_size": 2, "timeout": 120},  # Small resources
                {"batch_size": 5, "timeout": 300},  # Medium resources
                {"batch_size": 10, "timeout": 600},  # Large resources
            ]

            scaling_results = []

            for i, config_params in enumerate(scaling_configs):
                config = CollectionConfig(
                    max_venues_per_batch=config_params["batch_size"],
                    batch_timeout_seconds=config_params["timeout"],
                )

                orchestrator = VenueCollectionOrchestrator(config)
                init_result = orchestrator.initialize_system()

                if not init_result.success:
                    continue

                session_id = orchestrator.start_collection_session()

                # Test with larger venue set for bigger configurations
                test_venues = ["ICML", "ICLR", "NeurIPS", "AAAI", "CVPR"][
                    : config_params["batch_size"]
                ]

                scale_start = time.time()
                initial_memory = psutil.virtual_memory().used / (1024**2)

                collection_result = orchestrator.execute_venue_collection(
                    session_id, test_venues, [2024]
                )

                scale_duration = time.time() - scale_start
                final_memory = psutil.virtual_memory().used / (1024**2)

                throughput = (
                    collection_result.raw_papers_collected / (scale_duration / 60)
                    if scale_duration > 0
                    else 0
                )

                scaling_results.append(
                    {
                        "config_level": i + 1,
                        "batch_size": config_params["batch_size"],
                        "throughput": throughput,
                        "papers_collected": collection_result.raw_papers_collected,
                        "memory_usage": final_memory - initial_memory,
                        "duration": scale_duration,
                        "venues_processed": len(test_venues),
                    }
                )

                orchestrator.shutdown_system()

            # Analyze vertical scaling
            if len(scaling_results) >= 2:
                baseline = scaling_results[0]
                scaled = scaling_results[-1]

                result.baseline_throughput = baseline["throughput"]
                result.scaled_throughput = scaled["throughput"]
                result.scale_factor = scaled["batch_size"]

                # Calculate efficiency based on resource increase
                resource_multiplier = scaled["batch_size"] / baseline["batch_size"]
                expected_throughput = baseline["throughput"] * resource_multiplier
                result.scalability_efficiency = (
                    scaled["throughput"] / expected_throughput
                    if expected_throughput > 0
                    else 0
                )

                result.resource_scaling = {
                    "memory_scaling_factor": (
                        scaled["memory_usage"] / baseline["memory_usage"]
                    )
                    if baseline["memory_usage"] > 0
                    else 1.0,
                    "throughput_scaling_factor": (
                        scaled["throughput"] / baseline["throughput"]
                    )
                    if baseline["throughput"] > 0
                    else 1.0,
                }

                # Success if we get reasonable scaling
                result.success = result.scalability_efficiency > 0.6

                # Analysis
                if (
                    result.resource_scaling["memory_scaling_factor"]
                    > resource_multiplier * 1.5
                ):
                    result.bottlenecks_at_scale.append("excessive_memory_scaling")
                    result.scaling_recommendations.append(
                        "Optimize memory usage for larger batch sizes"
                    )

                if result.scalability_efficiency < 0.7:
                    result.bottlenecks_at_scale.append("suboptimal_vertical_scaling")
                    result.scaling_recommendations.append(
                        "Investigate processing bottlenecks with larger batches"
                    )

        except Exception as e:
            result.bottlenecks_at_scale.append(
                f"vertical_scaling_test_failed: {str(e)}"
            )

        finally:
            result.duration_seconds = time.time() - test_start

        return result

    def test_data_volume_scaling(self) -> ScalabilityTestResult:
        """Test scaling with increasing data volumes"""

        test_start = time.time()

        result = ScalabilityTestResult(
            test_name="data_volume_scaling",
            success=False,
            duration_seconds=0.0,
            scale_factor=0,
            baseline_throughput=0.0,
            scaled_throughput=0.0,
            scalability_efficiency=0.0,
            resource_scaling={},
        )

        try:
            # Test with increasing data volumes
            volume_tests = [
                {"venues": ["ICML"], "years": [2024], "expected_scale": 1},
                {"venues": ["ICML", "ICLR"], "years": [2024], "expected_scale": 2},
                {
                    "venues": ["ICML", "ICLR", "NeurIPS"],
                    "years": [2023, 2024],
                    "expected_scale": 6,
                },
            ]

            volume_results = []

            for test_config in volume_tests:
                config = CollectionConfig()
                orchestrator = VenueCollectionOrchestrator(config)
                init_result = orchestrator.initialize_system()

                if not init_result.success:
                    continue

                session_id = orchestrator.start_collection_session()

                volume_start = time.time()
                initial_memory = psutil.virtual_memory().used / (1024**2)

                collection_result = orchestrator.execute_venue_collection(
                    session_id, test_config["venues"], test_config["years"]
                )

                volume_duration = time.time() - volume_start
                final_memory = psutil.virtual_memory().used / (1024**2)

                throughput = (
                    collection_result.raw_papers_collected / (volume_duration / 60)
                    if volume_duration > 0
                    else 0
                )

                volume_results.append(
                    {
                        "scale": test_config["expected_scale"],
                        "venues": len(test_config["venues"]),
                        "years": len(test_config["years"]),
                        "throughput": throughput,
                        "papers_collected": collection_result.raw_papers_collected,
                        "memory_usage": final_memory - initial_memory,
                        "duration": volume_duration,
                    }
                )

                orchestrator.shutdown_system()

            # Analyze data volume scaling
            if len(volume_results) >= 2:
                baseline = volume_results[0]
                scaled = volume_results[-1]

                result.baseline_throughput = baseline["throughput"]
                result.scaled_throughput = scaled["throughput"]
                result.scale_factor = scaled["scale"]

                # Check if throughput degrades significantly with scale
                throughput_ratio = (
                    scaled["throughput"] / baseline["throughput"]
                    if baseline["throughput"] > 0
                    else 1.0
                )

                # For data volume scaling, we expect some degradation but not below 50%
                result.scalability_efficiency = min(1.0, throughput_ratio)

                result.resource_scaling = {
                    "memory_per_scale_unit": scaled["memory_usage"] / scaled["scale"]
                    if scaled["scale"] > 0
                    else 0,
                    "duration_scaling": scaled["duration"] / baseline["duration"]
                    if baseline["duration"] > 0
                    else 1.0,
                }

                # Success if throughput doesn't degrade too much
                result.success = result.scalability_efficiency > 0.5

                # Analysis
                if result.scalability_efficiency < 0.3:
                    result.bottlenecks_at_scale.append(
                        "severe_performance_degradation_with_volume"
                    )
                    result.scaling_recommendations.append(
                        "Implement data partitioning and parallel processing"
                    )
                elif result.scalability_efficiency < 0.7:
                    result.bottlenecks_at_scale.append(
                        "moderate_performance_impact_with_volume"
                    )
                    result.scaling_recommendations.append(
                        "Optimize data structures for larger datasets"
                    )

        except Exception as e:
            result.bottlenecks_at_scale.append(
                f"data_volume_scaling_test_failed: {str(e)}"
            )

        finally:
            result.duration_seconds = time.time() - test_start

        return result

    def test_concurrent_load(self, max_concurrent_users: int = 5) -> LoadTestResult:
        """Test system under concurrent load"""

        result = LoadTestResult(
            concurrent_users=max_concurrent_users,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_response_time=0.0,
            peak_response_time=0.0,
            throughput_per_second=0.0,
            error_rate=0.0,
        )

        response_times = []
        successful_operations = 0
        failed_operations = 0

        def simulate_user_load(user_id: int):
            """Simulate individual user load"""
            try:
                config = CollectionConfig()
                orchestrator = VenueCollectionOrchestrator(config)

                operation_start = time.time()
                init_result = orchestrator.initialize_system()

                if not init_result.success:
                    return {"success": False, "duration": time.time() - operation_start}

                session_id = orchestrator.start_collection_session()

                # Small collection per user
                test_venues = ["ICML"] if user_id % 2 == 0 else ["ICLR"]
                collection_result = orchestrator.execute_venue_collection(
                    session_id, test_venues, [2024]
                )

                operation_duration = time.time() - operation_start

                orchestrator.shutdown_system()

                return {
                    "success": collection_result.success,
                    "duration": operation_duration,
                    "papers": collection_result.raw_papers_collected,
                }

            except Exception as e:
                return {
                    "success": False,
                    "duration": time.time() - operation_start,
                    "error": str(e),
                }

        # Run concurrent load test
        load_start = time.time()

        with ThreadPoolExecutor(max_workers=max_concurrent_users) as executor:
            futures = []

            for user_id in range(max_concurrent_users):
                future = executor.submit(simulate_user_load, user_id)
                futures.append(future)

            # Collect results
            for future in as_completed(futures, timeout=600):  # 10 minute timeout
                try:
                    user_result = future.result()
                    response_times.append(user_result["duration"])

                    if user_result["success"]:
                        successful_operations += 1
                    else:
                        failed_operations += 1

                except Exception:
                    failed_operations += 1
                    response_times.append(600.0)  # Timeout duration

        load_duration = time.time() - load_start

        # Calculate metrics
        result.total_requests = len(response_times)
        result.successful_requests = successful_operations
        result.failed_requests = failed_operations
        result.average_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        result.peak_response_time = max(response_times) if response_times else 0
        result.throughput_per_second = (
            successful_operations / load_duration if load_duration > 0 else 0
        )
        result.error_rate = (
            failed_operations / result.total_requests
            if result.total_requests > 0
            else 0
        )

        # Resource utilization
        result.resource_utilization = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_io": psutil.disk_io_counters().read_bytes
            + psutil.disk_io_counters().write_bytes
            if psutil.disk_io_counters()
            else 0,
        }

        return result


class ScalabilityTestRunner:
    """Runner for scalability tests"""

    def run_all_scalability_tests(self) -> List[ScalabilityTestResult]:
        """Run complete scalability test suite"""

        scalability_test = ScalabilityTest()

        tests = [
            scalability_test.test_horizontal_scaling(),
            scalability_test.test_vertical_scaling(),
            scalability_test.test_data_volume_scaling(),
        ]

        return tests

    def run_load_test(self, concurrent_users: int = 3) -> LoadTestResult:
        """Run load test with specified concurrent users"""

        scalability_test = ScalabilityTest()
        return scalability_test.test_concurrent_load(concurrent_users)

    def analyze_scalability_results(
        self, results: List[ScalabilityTestResult]
    ) -> Dict[str, Any]:
        """Analyze scalability test results"""

        total_tests = len(results)
        passed_tests = len([r for r in results if r.success])

        # Collect efficiency metrics
        efficiencies = [
            r.scalability_efficiency for r in results if r.scalability_efficiency > 0
        ]

        # Collect all bottlenecks and recommendations
        all_bottlenecks = []
        all_recommendations = []

        for result in results:
            all_bottlenecks.extend(result.bottlenecks_at_scale)
            all_recommendations.extend(result.scaling_recommendations)

        analysis = {
            "overall_scalability": "good"
            if passed_tests >= total_tests * 0.7
            else "needs_improvement",
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "average_scalability_efficiency": sum(efficiencies) / len(efficiencies)
            if efficiencies
            else 0,
            "min_scalability_efficiency": min(efficiencies) if efficiencies else 0,
            "max_scalability_efficiency": max(efficiencies) if efficiencies else 0,
            "common_bottlenecks": list(set(all_bottlenecks)),
            "scaling_recommendations": list(set(all_recommendations)),
            "scalability_targets_met": passed_tests == total_tests,
        }

        return analysis
