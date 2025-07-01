"""Resource exhaustion scenarios for error injection testing."""

import logging
from typing import List, Dict, Any

from ..injection_framework import ErrorScenario, ErrorType

logger = logging.getLogger(__name__)


class ResourceExhaustionScenarios:
    """Pre-defined resource exhaustion scenarios for testing."""
    
    @staticmethod
    def get_memory_exhaustion_scenario() -> List[ErrorScenario]:
        """
        Get scenario for memory exhaustion.
        
        Returns:
            List of error scenarios simulating memory exhaustion
        """
        return [
            ErrorScenario(
                error_type=ErrorType.MEMORY_EXHAUSTION,
                component="analyzer",
                probability=0.3,
                severity="critical",
                recovery_expected=True,
                max_recovery_time_seconds=120.0,
                metadata={
                    "memory_limit_mb": 500,
                    "trigger_threshold_mb": 450,
                    "recovery_method": "reduce_batch_size"
                }
            ),
            ErrorScenario(
                error_type=ErrorType.MEMORY_EXHAUSTION,
                component="deduplicator",
                probability=0.2,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=90.0,
                metadata={
                    "memory_limit_mb": 300,
                    "recovery_method": "streaming_deduplication"
                }
            )
        ]
    
    @staticmethod
    def get_disk_space_scenario() -> List[ErrorScenario]:
        """
        Get scenario for disk space exhaustion.
        
        Returns:
            List of error scenarios simulating disk full conditions
        """
        return [
            ErrorScenario(
                error_type=ErrorType.DISK_FULL,
                component="checkpoint_manager",
                probability=0.1,
                severity="high",
                recovery_expected=False,  # Disk full typically needs manual intervention
                max_recovery_time_seconds=0.0,
                metadata={
                    "available_space_mb": 10,
                    "required_space_mb": 100,
                    "cleanup_possible": True
                }
            ),
            ErrorScenario(
                error_type=ErrorType.DISK_FULL,
                component="report_writer",
                probability=0.15,
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=60.0,
                metadata={
                    "alternative_output": "memory",
                    "compression_enabled": True
                }
            )
        ]
    
    @staticmethod
    def get_cpu_exhaustion_scenario() -> List[ErrorScenario]:
        """
        Get scenario for CPU exhaustion.
        
        Returns:
            List of error scenarios simulating high CPU usage
        """
        return [
            ErrorScenario(
                error_type=ErrorType.COMPONENT_CRASH,  # CPU exhaustion can cause crashes
                component="citation_analyzer",
                probability=0.1,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=180.0,
                metadata={
                    "cause": "cpu_exhaustion",
                    "cpu_threshold": 95,
                    "recovery_method": "reduce_parallelism"
                }
            )
        ]
    
    @staticmethod
    def get_progressive_resource_exhaustion_scenario() -> List[ErrorScenario]:
        """
        Get scenario for gradually increasing resource pressure.
        
        Returns:
            List of error scenarios with increasing resource pressure
        """
        scenarios = []
        
        # Memory pressure increasing over time
        memory_limits = [2000, 1000, 500, 250, 100]  # MB
        for i, limit in enumerate(memory_limits):
            scenarios.append(
                ErrorScenario(
                    error_type=ErrorType.MEMORY_EXHAUSTION,
                    component="data_processor",
                    probability=0.1 + (i * 0.1),  # Increasing probability
                    severity="low" if i < 2 else "medium" if i < 4 else "critical",
                    recovery_expected=i < 4,  # Last stage might not recover
                    max_recovery_time_seconds=60.0 + (i * 30),
                    metadata={
                        "stage": i + 1,
                        "memory_limit_mb": limit,
                        "pressure_level": ["low", "moderate", "high", "severe", "critical"][i]
                    }
                )
            )
        
        return scenarios
    
    @staticmethod
    def get_multi_resource_scenario() -> List[ErrorScenario]:
        """
        Get scenario with multiple resource constraints.
        
        Returns:
            List of error scenarios with combined resource issues
        """
        return [
            # Memory pressure
            ErrorScenario(
                error_type=ErrorType.MEMORY_EXHAUSTION,
                component="analyzer",
                probability=0.3,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=90.0
            ),
            # Disk pressure at the same time
            ErrorScenario(
                error_type=ErrorType.DISK_FULL,
                component="checkpoint_manager",
                probability=0.2,
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=60.0
            ),
            # CPU pressure adding to the mix
            ErrorScenario(
                error_type=ErrorType.COMPONENT_CRASH,
                component="processor",
                probability=0.15,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=120.0,
                metadata={"cause": "resource_contention"}
            )
        ]
    
    @staticmethod
    def validate_resource_recovery(recovery_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate resource exhaustion recovery.
        
        Args:
            recovery_metrics: Metrics from recovery testing
            
        Returns:
            Validation results
        """
        validation = {
            "passed": True,
            "checks": [],
            "failures": []
        }
        
        # Check memory recovery
        memory_recovery = recovery_metrics.get("memory_recovery_success_rate", 0)
        if memory_recovery < 0.9:  # 90% success rate
            validation["passed"] = False
            validation["failures"].append(
                f"Memory recovery rate {memory_recovery:.1%} below 90% threshold"
            )
        else:
            validation["checks"].append("Memory exhaustion recovery working")
        
        # Check graceful degradation
        graceful_degradation = recovery_metrics.get("graceful_degradation_rate", 0)
        if graceful_degradation < 0.95:
            validation["passed"] = False
            validation["failures"].append(
                f"Graceful degradation rate {graceful_degradation:.1%} below 95% threshold"
            )
        else:
            validation["checks"].append("Graceful degradation verified")
        
        # Check resource optimization
        optimization_effective = recovery_metrics.get("resource_optimization_effective", False)
        if not optimization_effective:
            validation["failures"].append("Resource optimization not effective")
        else:
            validation["checks"].append("Resource optimization working")
        
        # Check no cascading resource failures
        cascading_failures = recovery_metrics.get("resource_cascade_failures", 0)
        if cascading_failures > 0:
            validation["passed"] = False
            validation["failures"].append(
                f"Detected {cascading_failures} cascading resource failures"
            )
        else:
            validation["checks"].append("No cascading resource failures")
        
        return validation