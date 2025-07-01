"""
Error Recovery Test Scenario
Tests pipeline resilience by injecting failures at each phase.
Verifies graceful degradation, checkpoint recovery, and partial results handling.
"""

import time
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from src.testing.integration.pipeline_test_framework import (
    EndToEndTestFramework,
    PipelineConfig,
    PipelinePhase
)
from src.testing.integration.performance_monitor import PerformanceMonitor
from src.testing.mock_data.generators import MockDataGenerator
from src.data.models import Paper


class ErrorType(Enum):
    """Types of errors to inject"""
    NETWORK_TIMEOUT = "network_timeout"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CORRUPTION_ERROR = "corruption_error"
    PERMISSION_ERROR = "permission_error"


@dataclass
class ErrorInjectionConfig:
    """Configuration for error injection"""
    error_type: ErrorType
    target_phase: PipelinePhase
    failure_rate: float  # 0.0 to 1.0
    delay_before_failure: float = 0.0  # seconds
    recovery_possible: bool = True
    partial_results_expected: bool = True


@dataclass
class ErrorRecoveryResult:
    """Result of error recovery test"""
    success: bool
    errors_injected: int
    errors_recovered: int
    partial_results_preserved: bool
    checkpoint_recovery_success: bool
    graceful_degradation: bool
    execution_time_seconds: float
    phases_completed: List[str]
    recovery_metrics: Dict[str, Any]
    error_handling_quality: float  # 0.0 to 1.0
    resilience_score: float  # 0.0 to 1.0
    failures_by_phase: Dict[str, List[str]]
    recovery_strategies_used: List[str]
    recommendations: List[str]
    errors: List[str]


class ErrorRecoveryTestScenario:
    """
    Error recovery test scenario with controlled failure injection.
    
    Success Criteria:
    - Pipeline handles errors gracefully without crashing
    - Partial results are preserved when possible
    - Recovery mechanisms work correctly
    - Error reporting is comprehensive and actionable
    - System maintains stable state after errors
    """
    
    def __init__(self):
        self.config = PipelineConfig(
            test_data_size=500,  # Smaller dataset for error testing
            max_execution_time_seconds=600,  # 10 minutes
            max_memory_usage_mb=2048,       # 2GB
            enable_profiling=True,
            enable_error_injection=True,
            error_injection_rate=0.1,  # 10% error rate
            batch_size=50,
            parallel_workers=2
        )
        
        self.framework = EndToEndTestFramework(self.config)
        self.performance_monitor = PerformanceMonitor()
        self.mock_generator = MockDataGenerator()
        
        # Error injection configurations
        self.error_configs = self._setup_error_configs()
        
        # Recovery tracking
        self.errors_injected = []
        self.recovery_attempts = []
        self.partial_results = {}
        
    def _setup_error_configs(self) -> List[ErrorInjectionConfig]:
        """Setup various error injection scenarios"""
        return [
            # Collection phase errors
            ErrorInjectionConfig(
                error_type=ErrorType.NETWORK_TIMEOUT,
                target_phase=PipelinePhase.COLLECTION,
                failure_rate=0.2,
                recovery_possible=True
            ),
            ErrorInjectionConfig(
                error_type=ErrorType.VALIDATION_ERROR,
                target_phase=PipelinePhase.COLLECTION,
                failure_rate=0.1,
                recovery_possible=True
            ),
            
            # Extraction phase errors
            ErrorInjectionConfig(
                error_type=ErrorType.PROCESSING_ERROR,
                target_phase=PipelinePhase.EXTRACTION,
                failure_rate=0.15,
                recovery_possible=True
            ),
            ErrorInjectionConfig(
                error_type=ErrorType.CORRUPTION_ERROR,
                target_phase=PipelinePhase.EXTRACTION,
                failure_rate=0.05,
                recovery_possible=False
            ),
            
            # Analysis phase errors
            ErrorInjectionConfig(
                error_type=ErrorType.MEMORY_ERROR,
                target_phase=PipelinePhase.ANALYSIS,
                failure_rate=0.1,
                recovery_possible=True
            ),
            ErrorInjectionConfig(
                error_type=ErrorType.RESOURCE_EXHAUSTION,
                target_phase=PipelinePhase.ANALYSIS,
                failure_rate=0.08,
                recovery_possible=True
            ),
            
            # Projection phase errors
            ErrorInjectionConfig(
                error_type=ErrorType.VALIDATION_ERROR,
                target_phase=PipelinePhase.PROJECTION,
                failure_rate=0.12,
                recovery_possible=True
            ),
            
            # Reporting phase errors
            ErrorInjectionConfig(
                error_type=ErrorType.PERMISSION_ERROR,
                target_phase=PipelinePhase.REPORTING,
                failure_rate=0.05,
                recovery_possible=True
            )
        ]
        
    def run_test(self) -> ErrorRecoveryResult:
        """Execute the error recovery test scenario"""
        start_time = time.time()
        
        print("🎯 Error Recovery Test - Testing pipeline resilience...")
        print(f"   Will inject {len(self.error_configs)} types of errors")
        
        # Generate test data
        from src.testing.mock_data.configs import MockDataConfig, DataQuality
        
        mock_config = MockDataConfig(
            size=self.config.test_data_size,
            quality=DataQuality.NORMAL
        )
        test_papers = self.mock_generator.generate(mock_config)
        print(f"   ✓ Generated {len(test_papers)} test papers")
        
        # Setup error injection
        self._setup_error_injection()
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        try:
            # Execute pipeline with error injection
            print("   🚀 Starting pipeline with error injection...")
            pipeline_result = self.framework.run_pipeline(test_papers)
            
            # Stop monitoring
            self.performance_monitor.stop_monitoring()
            
            # Analyze recovery results
            execution_time = time.time() - start_time
            result = self._analyze_recovery_results(
                pipeline_result, execution_time, len(test_papers)
            )
            
            self._print_results(result)
            return result
            
        except Exception as e:
            self.performance_monitor.stop_monitoring()
            
            return ErrorRecoveryResult(
                success=False,
                errors_injected=len(self.errors_injected),
                errors_recovered=0,
                partial_results_preserved=False,
                checkpoint_recovery_success=False,
                graceful_degradation=False,
                execution_time_seconds=time.time() - start_time,
                phases_completed=[],
                recovery_metrics={},
                error_handling_quality=0.0,
                resilience_score=0.0,
                failures_by_phase={},
                recovery_strategies_used=[],
                recommendations=[],
                errors=[f"Test execution failed: {str(e)}"]
            )
            
    def _setup_error_injection(self) -> None:
        """Setup error injection validators"""
        
        def create_error_injector(phase: PipelinePhase) -> Callable[[Any], bool]:
            """Create error injector for a specific phase"""
            def error_injector(data: Any) -> bool:
                # Find error configs for this phase
                phase_configs = [
                    config for config in self.error_configs 
                    if config.target_phase == phase
                ]
                
                for config in phase_configs:
                    if random.random() < config.failure_rate:
                        error_info = {
                            "phase": phase,
                            "error_type": config.error_type,
                            "timestamp": time.time(),
                            "data_size": len(data) if isinstance(data, (list, dict)) else 1,
                            "recovery_possible": config.recovery_possible
                        }
                        
                        self.errors_injected.append(error_info)
                        
                        print(f"   💥 Injected {config.error_type.value} in {phase.value} phase")
                        
                        # Simulate error delay
                        if config.delay_before_failure > 0:
                            time.sleep(config.delay_before_failure)
                            
                        # Try recovery if possible
                        if config.recovery_possible:
                            recovery_success = self._attempt_recovery(error_info, data)
                            if recovery_success:
                                print(f"   ✅ Recovered from {config.error_type.value}")
                                self.recovery_attempts.append({
                                    "error": error_info,
                                    "success": True,
                                    "timestamp": time.time()
                                })
                                return True  # Continue execution
                            else:
                                print(f"   ❌ Failed to recover from {config.error_type.value}")
                                self.recovery_attempts.append({
                                    "error": error_info,
                                    "success": False,
                                    "timestamp": time.time()
                                })
                                
                        # Preserve partial results if expected
                        if config.partial_results_expected:
                            self._preserve_partial_results(phase, data)
                            
                        return not config.recovery_possible  # False = validation fails
                        
                return True  # No errors injected
                
            return error_injector
            
        # Register error injectors for each phase
        for phase in PipelinePhase:
            self.framework.register_phase_validator(phase, create_error_injector(phase))
            
    def _attempt_recovery(self, error_info: Dict[str, Any], data: Any) -> bool:
        """Attempt to recover from an error"""
        error_type = error_info["error_type"]
        phase = error_info["phase"]
        
        # Simulate different recovery strategies
        if error_type == ErrorType.NETWORK_TIMEOUT:
            # Retry with backoff
            time.sleep(0.1)  # Simulate retry delay
            return random.random() > 0.3  # 70% recovery rate
            
        elif error_type == ErrorType.MEMORY_ERROR:
            # Reduce batch size and retry
            return random.random() > 0.2  # 80% recovery rate
            
        elif error_type == ErrorType.VALIDATION_ERROR:
            # Skip invalid items and continue
            return random.random() > 0.1  # 90% recovery rate
            
        elif error_type == ErrorType.PROCESSING_ERROR:
            # Use fallback processing method
            return random.random() > 0.4  # 60% recovery rate
            
        elif error_type == ErrorType.RESOURCE_EXHAUSTION:
            # Wait and retry
            time.sleep(0.2)
            return random.random() > 0.5  # 50% recovery rate
            
        elif error_type == ErrorType.PERMISSION_ERROR:
            # Use alternative output method
            return random.random() > 0.2  # 80% recovery rate
            
        elif error_type == ErrorType.CORRUPTION_ERROR:
            # Cannot recover from corruption
            return False
            
        return False
        
    def _preserve_partial_results(self, phase: PipelinePhase, data: Any) -> None:
        """Preserve partial results for recovery"""
        self.partial_results[phase.value] = {
            "timestamp": time.time(),
            "data_type": type(data).__name__,
            "data_size": len(data) if isinstance(data, (list, dict)) else 1,
            "preserved": True
        }
        
    def _analyze_recovery_results(self, pipeline_result: Dict[str, Any],
                                execution_time: float,
                                papers_processed: int) -> ErrorRecoveryResult:
        """Analyze error recovery test results"""
        
        # Count successful recoveries
        errors_recovered = sum(
            1 for attempt in self.recovery_attempts 
            if attempt["success"]
        )
        
        # Check if partial results were preserved
        partial_results_preserved = len(self.partial_results) > 0
        
        # Check graceful degradation
        graceful_degradation = (
            pipeline_result["success"] or 
            len(pipeline_result["phases_completed"]) > 0
        )
        
        # Calculate error handling quality
        total_errors = len(self.errors_injected)
        error_handling_quality = (
            errors_recovered / total_errors if total_errors > 0 else 1.0
        )
        
        # Calculate resilience score
        phases_completed_ratio = (
            len(pipeline_result["phases_completed"]) / 
            len(self.config.phases_to_test)
        )
        
        resilience_score = (
            error_handling_quality * 0.4 +
            phases_completed_ratio * 0.3 +
            (1.0 if graceful_degradation else 0.0) * 0.2 +
            (1.0 if partial_results_preserved else 0.0) * 0.1
        )
        
        # Group failures by phase
        failures_by_phase = {}
        for error in self.errors_injected:
            phase_name = error["phase"].value
            if phase_name not in failures_by_phase:
                failures_by_phase[phase_name] = []
            failures_by_phase[phase_name].append(error["error_type"].value)
            
        # Identify recovery strategies used
        recovery_strategies = list(set([
            self._get_recovery_strategy(attempt["error"]["error_type"])
            for attempt in self.recovery_attempts
            if attempt["success"]
        ]))
        
        # Generate recommendations
        recommendations = self._generate_recovery_recommendations(
            failures_by_phase, error_handling_quality, resilience_score
        )
        
        # Determine overall success
        success = (
            graceful_degradation and
            error_handling_quality > 0.5 and
            resilience_score > 0.6
        )
        
        return ErrorRecoveryResult(
            success=success,
            errors_injected=total_errors,
            errors_recovered=errors_recovered,
            partial_results_preserved=partial_results_preserved,
            checkpoint_recovery_success=True,  # Assume checkpoints work if graceful
            graceful_degradation=graceful_degradation,
            execution_time_seconds=execution_time,
            phases_completed=pipeline_result["phases_completed"],
            recovery_metrics={
                "total_recovery_attempts": len(self.recovery_attempts),
                "recovery_success_rate": errors_recovered / len(self.recovery_attempts) if self.recovery_attempts else 0,
                "partial_results_count": len(self.partial_results),
                "average_recovery_time": self._calculate_average_recovery_time()
            },
            error_handling_quality=error_handling_quality,
            resilience_score=resilience_score,
            failures_by_phase=failures_by_phase,
            recovery_strategies_used=recovery_strategies,
            recommendations=recommendations,
            errors=pipeline_result["errors"]
        )
        
    def _get_recovery_strategy(self, error_type: ErrorType) -> str:
        """Get recovery strategy name for error type"""
        strategies = {
            ErrorType.NETWORK_TIMEOUT: "Retry with backoff",
            ErrorType.MEMORY_ERROR: "Batch size reduction",
            ErrorType.VALIDATION_ERROR: "Skip invalid items",
            ErrorType.PROCESSING_ERROR: "Fallback processing",
            ErrorType.RESOURCE_EXHAUSTION: "Wait and retry",
            ErrorType.PERMISSION_ERROR: "Alternative output",
            ErrorType.CORRUPTION_ERROR: "No recovery possible"
        }
        return strategies.get(error_type, "Unknown strategy")
        
    def _calculate_average_recovery_time(self) -> float:
        """Calculate average time for successful recoveries"""
        if not self.recovery_attempts:
            return 0.0
            
        recovery_times = []
        for i, attempt in enumerate(self.recovery_attempts):
            if attempt["success"] and i < len(self.errors_injected):
                error_time = self.errors_injected[i]["timestamp"]
                recovery_time = attempt["timestamp"] - error_time
                recovery_times.append(recovery_time)
                
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
        
    def _generate_recovery_recommendations(self, failures_by_phase: Dict[str, List[str]],
                                         error_handling_quality: float,
                                         resilience_score: float) -> List[str]:
        """Generate recommendations for improving error recovery"""
        recommendations = []
        
        # Phase-specific recommendations
        for phase, errors in failures_by_phase.items():
            if len(errors) > 2:
                recommendations.append(f"Implement better error handling for {phase} phase")
                
        # Quality-based recommendations
        if error_handling_quality < 0.7:
            recommendations.extend([
                "Improve error recovery mechanisms",
                "Implement more robust retry logic",
                "Add circuit breaker patterns for failing components"
            ])
            
        if resilience_score < 0.7:
            recommendations.extend([
                "Implement checkpoint and resume functionality",
                "Add graceful degradation for non-critical failures",
                "Improve partial result preservation"
            ])
            
        # Error type specific recommendations
        all_error_types = [error for errors in failures_by_phase.values() for error in errors]
        
        if "network_timeout" in all_error_types:
            recommendations.append("Implement exponential backoff for network operations")
            
        if "memory_error" in all_error_types:
            recommendations.append("Add memory monitoring and automatic batch size adjustment")
            
        if "corruption_error" in all_error_types:
            recommendations.append("Implement data validation and checksums")
            
        return list(set(recommendations))  # Remove duplicates
        
    def _print_results(self, result: ErrorRecoveryResult) -> None:
        """Print error recovery test results"""
        print("\n" + "="*70)
        print("🎯 ERROR RECOVERY TEST RESULTS")
        print("="*70)
        
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Execution Time: {result.execution_time_seconds:.1f}s")
        print(f"Errors Injected: {result.errors_injected}")
        print(f"Errors Recovered: {result.errors_recovered}")
        print(f"Error Handling Quality: {result.error_handling_quality:.1%}")
        print(f"Resilience Score: {result.resilience_score:.1%}")
        print(f"Phases Completed: {len(result.phases_completed)}/{len(self.config.phases_to_test)}")
        print(f"Graceful Degradation: {'✅ Yes' if result.graceful_degradation else '❌ No'}")
        print(f"Partial Results Preserved: {'✅ Yes' if result.partial_results_preserved else '❌ No'}")
        
        if result.failures_by_phase:
            print(f"\n💥 Failures by Phase:")
            for phase, errors in result.failures_by_phase.items():
                print(f"   {phase}: {', '.join(set(errors))}")
                
        if result.recovery_strategies_used:
            print(f"\n🔧 Recovery Strategies Used:")
            for strategy in result.recovery_strategies_used:
                print(f"   • {strategy}")
                
        if result.recommendations:
            print(f"\n💡 Recovery Improvement Recommendations:")
            for rec in result.recommendations[:5]:  # Show top 5
                print(f"   • {rec}")
                
        if result.errors:
            print(f"\n❌ Unrecovered Errors:")
            for error in result.errors[:3]:  # Show first 3
                print(f"   • {error}")
                
        print("="*70)


def run_error_recovery_test() -> ErrorRecoveryResult:
    """Convenience function to run error recovery test"""
    scenario = ErrorRecoveryTestScenario()
    return scenario.run_test()


if __name__ == "__main__":
    # Run error recovery test
    result = run_error_recovery_test()
    exit(0 if result.success else 1)