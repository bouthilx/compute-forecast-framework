"""
Normal Flow Test Scenario
Tests the standard pipeline execution with 1000 papers under normal conditions.
Target: <5 minutes execution, <4GB memory usage.
"""

import time
from typing import List, Dict, Any
from dataclasses import dataclass

from compute_forecast.testing.integration.pipeline_test_framework import (
    EndToEndTestFramework,
    PipelineConfig,
    PipelinePhase,
)
from compute_forecast.testing.integration.performance_monitor import (
    PerformanceMonitor,
    BottleneckAnalyzer,
)
from compute_forecast.testing.integration.phase_validators import (
    CollectionPhaseValidator,
    ExtractionPhaseValidator,
    ProjectionPhaseValidator,
    ReportingPhaseValidator,
    TransitionValidator,
)
from compute_forecast.testing.mock_data.generators import MockDataGenerator
from compute_forecast.data.models import Paper


@dataclass
class NormalFlowResult:
    """Result of normal flow test"""

    success: bool
    execution_time_seconds: float
    peak_memory_mb: float
    papers_processed: int
    phases_completed: List[str]
    performance_metrics: Dict[str, Any]
    validation_results: Dict[str, Any]
    bottlenecks: List[str]
    recommendations: List[str]
    errors: List[str]
    warnings: List[str]


class NormalFlowTestScenario:
    """
    Normal flow test scenario for 1000 papers.

    Success Criteria:
    - Complete pipeline execution in <5 minutes
    - Memory usage stays under 4GB
    - All phases complete successfully
    - Data validation passes at each phase
    - Final dataset passes quality checks
    """

    def __init__(self):
        self.config = PipelineConfig(
            test_data_size=1000,
            max_execution_time_seconds=300,  # 5 minutes
            max_memory_usage_mb=4096,  # 4GB
            enable_profiling=True,
            enable_error_injection=False,
            batch_size=100,
            parallel_workers=4,
        )

        self.framework = EndToEndTestFramework(self.config)
        self.performance_monitor = PerformanceMonitor()
        self.bottleneck_analyzer = BottleneckAnalyzer()
        self.transition_validator = TransitionValidator()

        # Setup phase validators
        self._setup_validators()

        # Setup mock data generator
        self.mock_generator = MockDataGenerator()

        # Import configs

    def _setup_validators(self) -> None:
        """Setup validators for each phase"""
        # Register phase validators
        collection_validator = CollectionPhaseValidator(min_papers=800)
        extraction_validator = ExtractionPhaseValidator()
        # analysis_validator = AnalysisPhaseValidator()  # Using simple function instead
        projection_validator = ProjectionPhaseValidator()
        reporting_validator = ReportingPhaseValidator()

        # Custom validation functions for framework
        def validate_collection(data):
            return collection_validator.validate(data).is_valid

        def validate_extraction(data):
            return extraction_validator.validate(data).is_valid

        def validate_analysis(data):
            if isinstance(data, list):
                return len(data) > 0
            return True

        def validate_projection(data):
            return projection_validator.validate(data).is_valid

        def validate_reporting(data):
            return reporting_validator.validate(data).is_valid

        # Register with framework
        self.framework.register_phase_validator(
            PipelinePhase.COLLECTION, validate_collection
        )
        self.framework.register_phase_validator(
            PipelinePhase.EXTRACTION, validate_extraction
        )
        self.framework.register_phase_validator(
            PipelinePhase.ANALYSIS, validate_analysis
        )
        self.framework.register_phase_validator(
            PipelinePhase.PROJECTION, validate_projection
        )
        self.framework.register_phase_validator(
            PipelinePhase.REPORTING, validate_reporting
        )

    def run_test(self) -> NormalFlowResult:
        """Execute the normal flow test scenario"""
        start_time = time.time()

        # Generate test data
        print("🎯 Normal Flow Test - Generating 1000 test papers...")
        test_papers = self._generate_test_data()

        print(f"   ✓ Generated {len(test_papers)} papers")

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        try:
            # Execute pipeline
            print("   🚀 Starting pipeline execution...")
            pipeline_result = self.framework.run_pipeline(test_papers)

            # Stop monitoring
            self.performance_monitor.stop_monitoring()

            # Analyze results
            validation_results = self._validate_results(pipeline_result)
            performance_analysis = self._analyze_performance()

            # Create final result
            execution_time = time.time() - start_time

            result = NormalFlowResult(
                success=pipeline_result["success"]
                and self._meets_success_criteria(execution_time, performance_analysis),
                execution_time_seconds=execution_time,
                peak_memory_mb=self._get_peak_memory(performance_analysis),
                papers_processed=len(test_papers),
                phases_completed=pipeline_result["phases_completed"],
                performance_metrics=performance_analysis,
                validation_results=validation_results,
                bottlenecks=self._identify_bottlenecks(performance_analysis),
                recommendations=self._generate_recommendations(performance_analysis),
                errors=pipeline_result["errors"],
                warnings=[],
            )

            self._print_results(result)
            return result

        except Exception as e:
            self.performance_monitor.stop_monitoring()

            return NormalFlowResult(
                success=False,
                execution_time_seconds=time.time() - start_time,
                peak_memory_mb=0,
                papers_processed=len(test_papers),
                phases_completed=[],
                performance_metrics={},
                validation_results={},
                bottlenecks=[],
                recommendations=[],
                errors=[f"Test execution failed: {str(e)}"],
                warnings=[],
            )

    def _generate_test_data(self) -> List[Paper]:
        """Generate test papers for normal flow"""
        from compute_forecast.testing.mock_data.configs import (
            MockDataConfig,
            DataQuality,
        )

        mock_config = MockDataConfig(
            size=self.config.test_data_size, quality=DataQuality.NORMAL
        )
        return self.mock_generator.generate(mock_config)

    def _validate_results(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pipeline results"""
        validation_results = {
            "pipeline_success": pipeline_result["success"],
            "phases_completed": len(pipeline_result["phases_completed"]),
            "total_phases": len(self.config.phases_to_test),
            "completion_rate": len(pipeline_result["phases_completed"])
            / len(self.config.phases_to_test),
        }

        # Add phase-specific validation
        for phase_name, metrics in pipeline_result["phase_metrics"].items():
            validation_results[f"{phase_name}_success"] = metrics.success
            validation_results[f"{phase_name}_duration"] = (
                metrics.execution_time_seconds
            )
            validation_results[f"{phase_name}_records"] = metrics.records_processed

        return validation_results

    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics"""
        profiles = self.performance_monitor.profiles
        analysis = {}

        for phase, profile in profiles.items():
            if profile.snapshots:
                averages = profile.calculate_averages()
                analysis[phase.value] = {
                    "duration": profile.duration_seconds,
                    "peak_cpu": profile.peak_cpu,
                    "peak_memory": profile.peak_memory_mb,
                    "avg_cpu": averages["avg_cpu_percent"],
                    "avg_memory": averages["avg_memory_mb"],
                    "io_rate": profile.get_io_rate_mbps(),
                    "network_rate": profile.get_network_rate_mbps(),
                }

        return analysis

    def _meets_success_criteria(
        self, execution_time: float, performance_analysis: Dict[str, Any]
    ) -> bool:
        """Check if test meets success criteria"""
        # Check execution time (5 minutes = 300 seconds)
        if execution_time > 300:
            return False

        # Check memory usage (4GB = 4096MB)
        peak_memory = self._get_peak_memory(performance_analysis)
        if peak_memory > 4096:
            return False

        return True

    def _get_peak_memory(self, performance_analysis: Dict[str, Any]) -> float:
        """Get peak memory usage across all phases"""
        peak = 0.0
        for phase_data in performance_analysis.values():
            if isinstance(phase_data, dict) and "peak_memory" in phase_data:
                peak = max(peak, phase_data["peak_memory"])
        return peak

    def _identify_bottlenecks(self, performance_analysis: Dict[str, Any]) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        for phase_name, phase_data in performance_analysis.items():
            if isinstance(phase_data, dict):
                # Check CPU bottlenecks
                if phase_data.get("peak_cpu", 0) > 80:
                    bottlenecks.append(
                        f"{phase_name}: High CPU usage ({phase_data['peak_cpu']:.1f}%)"
                    )

                # Check memory bottlenecks
                if phase_data.get("peak_memory", 0) > 3000:  # 75% of 4GB
                    bottlenecks.append(
                        f"{phase_name}: High memory usage ({phase_data['peak_memory']:.0f}MB)"
                    )

                # Check duration bottlenecks
                if phase_data.get("duration", 0) > 60:  # More than 1 minute per phase
                    bottlenecks.append(
                        f"{phase_name}: Slow execution ({phase_data['duration']:.1f}s)"
                    )

        return bottlenecks

    def _generate_recommendations(
        self, performance_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []

        # Analyze overall performance
        total_duration = sum(
            phase_data.get("duration", 0)
            for phase_data in performance_analysis.values()
            if isinstance(phase_data, dict)
        )

        if total_duration > 240:  # 4 minutes, close to limit
            recommendations.append(
                "Consider optimizing slow phases to improve overall execution time"
            )

        peak_memory = self._get_peak_memory(performance_analysis)
        if peak_memory > 3000:  # 75% of limit
            recommendations.append(
                "Implement memory optimization to prevent hitting 4GB limit"
            )

        # Phase-specific recommendations
        for phase_name, phase_data in performance_analysis.items():
            if isinstance(phase_data, dict):
                if phase_data.get("duration", 0) > 60:
                    recommendations.append(
                        f"Optimize {phase_name} phase execution time"
                    )

        return recommendations

    def _print_results(self, result: NormalFlowResult) -> None:
        """Print test results"""
        print("\n" + "=" * 60)
        print("🎯 NORMAL FLOW TEST RESULTS")
        print("=" * 60)

        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Execution Time: {result.execution_time_seconds:.1f}s (target: <300s)")
        print(f"Peak Memory: {result.peak_memory_mb:.0f}MB (target: <4096MB)")
        print(f"Papers Processed: {result.papers_processed}")
        print(
            f"Phases Completed: {len(result.phases_completed)}/{len(self.config.phases_to_test)}"
        )

        if result.bottlenecks:
            print("\n⚠️ Bottlenecks Identified:")
            for bottleneck in result.bottlenecks:
                print(f"   • {bottleneck}")

        if result.recommendations:
            print("\n💡 Recommendations:")
            for rec in result.recommendations:
                print(f"   • {rec}")

        if result.errors:
            print("\n❌ Errors:")
            for error in result.errors:
                print(f"   • {error}")

        print("=" * 60)


def run_normal_flow_test() -> NormalFlowResult:
    """Convenience function to run normal flow test"""
    scenario = NormalFlowTestScenario()
    return scenario.run_test()


if __name__ == "__main__":
    # Run normal flow test
    result = run_normal_flow_test()
    exit(0 if result.success else 1)
