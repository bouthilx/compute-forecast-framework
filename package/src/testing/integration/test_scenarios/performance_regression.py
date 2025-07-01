"""
Performance Regression Test Scenario
Compares current pipeline performance against established baselines.
Detects performance degradation and generates optimization recommendations.
"""

import time
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from src.testing.integration.pipeline_test_framework import (
    EndToEndTestFramework,
    PipelineConfig,
    PipelinePhase
)
from src.testing.integration.performance_monitor import PerformanceMonitor, BottleneckAnalyzer
from src.testing.mock_data.generators import MockDataGenerator
from src.data.models import Paper


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison"""
    version: str
    date: str
    test_data_size: int
    execution_time_seconds: float
    peak_memory_mb: float
    throughput_papers_per_second: float
    phase_metrics: Dict[str, Dict[str, float]]
    cpu_utilization: float
    memory_efficiency: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceBaseline':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class RegressionAnalysis:
    """Analysis of performance regression"""
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    is_regression: bool
    severity: str  # "low", "medium", "high", "critical"
    
    
@dataclass
class PerformanceRegressionResult:
    """Result of performance regression test"""
    success: bool
    baseline_version: str
    current_performance: PerformanceBaseline
    regression_analysis: List[RegressionAnalysis]
    overall_regression_score: float  # 0.0 (bad) to 1.0 (good)
    performance_improvements: List[str]
    performance_regressions: List[str]
    critical_issues: List[str]
    recommendations: List[str]
    execution_time_seconds: float
    errors: List[str]


class PerformanceRegressionTestScenario:
    """
    Performance regression test scenario.
    
    Success Criteria:
    - No critical performance regressions (>50% degradation)
    - Overall performance score > 0.8
    - Execution time within 20% of baseline
    - Memory usage within 30% of baseline
    - Throughput within 15% of baseline
    """
    
    def __init__(self, baseline_file: Optional[str] = None):
        self.config = PipelineConfig(
            test_data_size=1000,  # Standard size for consistent comparison
            max_execution_time_seconds=600,  # 10 minutes
            max_memory_usage_mb=4096,       # 4GB
            enable_profiling=True,
            enable_error_injection=False,
            batch_size=100,
            parallel_workers=4
        )
        
        self.framework = EndToEndTestFramework(self.config)
        self.performance_monitor = PerformanceMonitor()
        self.bottleneck_analyzer = BottleneckAnalyzer()
        self.mock_generator = MockDataGenerator()
        
        # Baseline management
        self.baseline_file = baseline_file or "performance_baseline.json"
        self.baseline = self._load_baseline()
        
        # Regression thresholds
        self.regression_thresholds = {
            "execution_time": {"warning": 0.2, "critical": 0.5},  # 20%, 50%
            "memory": {"warning": 0.3, "critical": 0.7},         # 30%, 70%
            "throughput": {"warning": -0.15, "critical": -0.3},   # -15%, -30%
            "cpu_utilization": {"warning": 0.25, "critical": 0.5}  # 25%, 50%
        }
        
    def _load_baseline(self) -> Optional[PerformanceBaseline]:
        """Load performance baseline from file"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                return PerformanceBaseline.from_dict(data)
            except Exception as e:
                print(f"⚠️ Could not load baseline: {e}")
                return None
        return None
        
    def _save_baseline(self, baseline: PerformanceBaseline) -> None:
        """Save performance baseline to file"""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(baseline.to_dict(), f, indent=2)
            print(f"✅ Saved new baseline to {self.baseline_file}")
        except Exception as e:
            print(f"⚠️ Could not save baseline: {e}")
            
    def run_test(self, save_as_baseline: bool = False) -> PerformanceRegressionResult:
        """Execute the performance regression test"""
        start_time = time.time()
        
        print("🎯 Performance Regression Test - Measuring current performance...")
        
        if self.baseline:
            print(f"   📊 Comparing against baseline: {self.baseline.version} ({self.baseline.date})")
        else:
            print("   📊 No baseline found - will establish new baseline")
            save_as_baseline = True
            
        # Generate test data
        test_papers = self.mock_generator.generate_test_papers(self.config.test_data_size)
        print(f"   ✓ Generated {len(test_papers)} test papers")
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        
        try:
            # Execute pipeline
            print("   🚀 Starting performance measurement...")
            pipeline_result = self.framework.run_pipeline(test_papers)
            
            # Stop monitoring
            self.performance_monitor.stop_monitoring()
            
            # Measure current performance
            execution_time = time.time() - start_time
            current_performance = self._measure_current_performance(
                pipeline_result, execution_time, len(test_papers)
            )
            
            # Save as baseline if requested
            if save_as_baseline:
                self._save_baseline(current_performance)
                if not self.baseline:
                    # First run, no comparison possible
                    return self._create_baseline_result(current_performance, execution_time)
                    
            # Perform regression analysis
            if self.baseline:
                result = self._analyze_regression(current_performance, execution_time)
            else:
                result = self._create_baseline_result(current_performance, execution_time)
                
            self._print_results(result)
            return result
            
        except Exception as e:
            self.performance_monitor.stop_monitoring()
            
            return PerformanceRegressionResult(
                success=False,
                baseline_version="unknown",
                current_performance=self._create_empty_baseline(),
                regression_analysis=[],
                overall_regression_score=0.0,
                performance_improvements=[],
                performance_regressions=[],
                critical_issues=[f"Test execution failed: {str(e)}"],
                recommendations=[],
                execution_time_seconds=time.time() - start_time,
                errors=[str(e)]
            )
            
    def _measure_current_performance(self, pipeline_result: Dict[str, Any],
                                   execution_time: float,
                                   papers_processed: int) -> PerformanceBaseline:
        """Measure current performance metrics"""
        
        # Calculate throughput
        throughput = papers_processed / execution_time if execution_time > 0 else 0
        
        # Get peak memory and CPU utilization
        peak_memory = 0.0
        cpu_utilization = 0.0
        phase_metrics = {}
        
        for phase, profile in self.performance_monitor.profiles.items():
            if profile.snapshots:
                averages = profile.calculate_averages()
                peak_memory = max(peak_memory, profile.peak_memory_mb)
                cpu_utilization = max(cpu_utilization, profile.peak_cpu)
                
                phase_metrics[phase.value] = {
                    "duration": profile.duration_seconds,
                    "peak_cpu": profile.peak_cpu,
                    "peak_memory": profile.peak_memory_mb,
                    "avg_cpu": averages["avg_cpu_percent"],
                    "avg_memory": averages["avg_memory_mb"],
                    "io_rate": profile.get_io_rate_mbps(),
                    "network_rate": profile.get_network_rate_mbps()
                }
                
        # Calculate memory efficiency
        memory_efficiency = papers_processed / peak_memory if peak_memory > 0 else 0
        
        return PerformanceBaseline(
            version=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            date=datetime.now().isoformat(),
            test_data_size=papers_processed,
            execution_time_seconds=execution_time,
            peak_memory_mb=peak_memory,
            throughput_papers_per_second=throughput,
            phase_metrics=phase_metrics,
            cpu_utilization=cpu_utilization,
            memory_efficiency=memory_efficiency
        )
        
    def _analyze_regression(self, current: PerformanceBaseline,
                          execution_time: float) -> PerformanceRegressionResult:
        """Analyze performance regression against baseline"""
        
        regression_analyses = []
        improvements = []
        regressions = []
        critical_issues = []
        
        # Overall metrics analysis
        analyses = [
            self._analyze_metric("execution_time", self.baseline.execution_time_seconds, 
                               current.execution_time_seconds, lower_is_better=True),
            self._analyze_metric("peak_memory", self.baseline.peak_memory_mb,
                               current.peak_memory_mb, lower_is_better=True),
            self._analyze_metric("throughput", self.baseline.throughput_papers_per_second,
                               current.throughput_papers_per_second, lower_is_better=False),
            self._analyze_metric("cpu_utilization", self.baseline.cpu_utilization,
                               current.cpu_utilization, lower_is_better=True),
            self._analyze_metric("memory_efficiency", self.baseline.memory_efficiency,
                               current.memory_efficiency, lower_is_better=False)
        ]
        
        regression_analyses.extend(analyses)
        
        # Phase-level analysis
        for phase_name in set(self.baseline.phase_metrics.keys()) | set(current.phase_metrics.keys()):
            baseline_phase = self.baseline.phase_metrics.get(phase_name, {})
            current_phase = current.phase_metrics.get(phase_name, {})
            
            if baseline_phase and current_phase:
                phase_analyses = [
                    self._analyze_metric(f"{phase_name}_duration", 
                                       baseline_phase.get("duration", 0),
                                       current_phase.get("duration", 0), 
                                       lower_is_better=True),
                    self._analyze_metric(f"{phase_name}_peak_memory",
                                       baseline_phase.get("peak_memory", 0),
                                       current_phase.get("peak_memory", 0),
                                       lower_is_better=True)
                ]
                regression_analyses.extend(phase_analyses)
                
        # Categorize results
        for analysis in regression_analyses:
            if analysis.is_regression:
                if analysis.severity == "critical":
                    critical_issues.append(f"Critical regression in {analysis.metric_name}: "
                                         f"{analysis.change_percent:+.1%}")
                else:
                    regressions.append(f"{analysis.metric_name}: {analysis.change_percent:+.1%}")
            elif analysis.change_percent < -0.05:  # 5% improvement
                improvements.append(f"{analysis.metric_name}: {analysis.change_percent:+.1%}")
                
        # Calculate overall regression score
        regression_score = self._calculate_regression_score(regression_analyses)
        
        # Generate recommendations
        recommendations = self._generate_regression_recommendations(
            regression_analyses, critical_issues
        )
        
        # Determine success
        success = (
            len(critical_issues) == 0 and
            regression_score > 0.8
        )
        
        return PerformanceRegressionResult(
            success=success,
            baseline_version=self.baseline.version,
            current_performance=current,
            regression_analysis=regression_analyses,
            overall_regression_score=regression_score,
            performance_improvements=improvements,
            performance_regressions=regressions,
            critical_issues=critical_issues,
            recommendations=recommendations,
            execution_time_seconds=execution_time,
            errors=[]
        )
        
    def _analyze_metric(self, metric_name: str, baseline_value: float,
                       current_value: float, lower_is_better: bool = True) -> RegressionAnalysis:
        """Analyze a single performance metric"""
        
        if baseline_value == 0:
            change_percent = 0.0
        else:
            change_percent = (current_value - baseline_value) / baseline_value
            
        # Determine if this is a regression
        if lower_is_better:
            is_regression = change_percent > 0
        else:
            is_regression = change_percent < 0
            
        # Determine severity
        abs_change = abs(change_percent)
        if abs_change < 0.05:  # 5%
            severity = "low"
        elif abs_change < 0.15:  # 15%
            severity = "medium"
        elif abs_change < 0.3:  # 30%
            severity = "high"
        else:
            severity = "critical"
            
        return RegressionAnalysis(
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            is_regression=is_regression and abs_change > 0.05,  # Only count >5% as regression
            severity=severity if is_regression else "low"
        )
        
    def _calculate_regression_score(self, analyses: List[RegressionAnalysis]) -> float:
        """Calculate overall regression score (0.0 = bad, 1.0 = good)"""
        if not analyses:
            return 1.0
            
        total_score = 0.0
        weights = {"critical": 0.0, "high": 0.3, "medium": 0.6, "low": 1.0}
        
        for analysis in analyses:
            if analysis.is_regression:
                total_score += weights.get(analysis.severity, 0.5)
            else:
                total_score += 1.0
                
        return total_score / len(analyses)
        
    def _generate_regression_recommendations(self, analyses: List[RegressionAnalysis],
                                           critical_issues: List[str]) -> List[str]:
        """Generate recommendations for addressing regressions"""
        recommendations = []
        
        # Critical issue recommendations
        if critical_issues:
            recommendations.append("Immediately investigate critical performance regressions")
            recommendations.append("Consider reverting recent changes until issues are resolved")
            
        # Metric-specific recommendations
        metric_issues = {}
        for analysis in analyses:
            if analysis.is_regression and analysis.severity in ["medium", "high", "critical"]:
                metric_type = analysis.metric_name.split("_")[0]
                if metric_type not in metric_issues:
                    metric_issues[metric_type] = []
                metric_issues[metric_type].append(analysis)
                
        if "execution" in metric_issues:
            recommendations.append("Profile code to identify performance bottlenecks")
            recommendations.append("Optimize algorithms and data structures")
            
        if "memory" in metric_issues:
            recommendations.append("Implement memory optimization strategies")
            recommendations.append("Consider streaming or batch processing")
            
        if "throughput" in metric_issues:
            recommendations.append("Optimize I/O operations and caching")
            recommendations.append("Consider parallel processing improvements")
            
        if "cpu" in metric_issues:
            recommendations.append("Optimize CPU-intensive operations")
            recommendations.append("Consider algorithmic improvements")
            
        # General recommendations
        if len([a for a in analyses if a.is_regression]) > len(analyses) * 0.3:
            recommendations.append("Consider comprehensive performance review")
            recommendations.append("Implement continuous performance monitoring")
            
        return recommendations
        
    def _create_baseline_result(self, current: PerformanceBaseline,
                              execution_time: float) -> PerformanceRegressionResult:
        """Create result for baseline establishment"""
        return PerformanceRegressionResult(
            success=True,
            baseline_version="baseline_established",
            current_performance=current,
            regression_analysis=[],
            overall_regression_score=1.0,
            performance_improvements=[],
            performance_regressions=[],
            critical_issues=[],
            recommendations=["Baseline established - future runs will compare against this"],
            execution_time_seconds=execution_time,
            errors=[]
        )
        
    def _create_empty_baseline(self) -> PerformanceBaseline:
        """Create empty baseline for error cases"""
        return PerformanceBaseline(
            version="error",
            date=datetime.now().isoformat(),
            test_data_size=0,
            execution_time_seconds=0.0,
            peak_memory_mb=0.0,
            throughput_papers_per_second=0.0,
            phase_metrics={},
            cpu_utilization=0.0,
            memory_efficiency=0.0
        )
        
    def _print_results(self, result: PerformanceRegressionResult) -> None:
        """Print performance regression test results"""
        print("\n" + "="*70)
        print("🎯 PERFORMANCE REGRESSION TEST RESULTS")
        print("="*70)
        
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Baseline Version: {result.baseline_version}")
        print(f"Overall Regression Score: {result.overall_regression_score:.2f}/1.0")
        print(f"Execution Time: {result.execution_time_seconds:.1f}s")
        
        # Current performance summary
        current = result.current_performance
        print(f"\n📊 Current Performance:")
        print(f"   Throughput: {current.throughput_papers_per_second:.1f} papers/sec")
        print(f"   Peak Memory: {current.peak_memory_mb:.0f}MB")
        print(f"   CPU Utilization: {current.cpu_utilization:.1f}%")
        print(f"   Memory Efficiency: {current.memory_efficiency:.2f} papers/MB")
        
        if result.critical_issues:
            print(f"\n🚨 Critical Issues:")
            for issue in result.critical_issues:
                print(f"   • {issue}")
                
        if result.performance_regressions:
            print(f"\n📉 Performance Regressions:")
            for regression in result.performance_regressions[:5]:  # Show top 5
                print(f"   • {regression}")
                
        if result.performance_improvements:
            print(f"\n📈 Performance Improvements:")
            for improvement in result.performance_improvements[:5]:  # Show top 5
                print(f"   • {improvement}")
                
        if result.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in result.recommendations[:5]:  # Show top 5
                print(f"   • {rec}")
                
        print("="*70)


def run_performance_regression_test(baseline_file: Optional[str] = None,
                                  save_as_baseline: bool = False) -> PerformanceRegressionResult:
    """Convenience function to run performance regression test"""
    scenario = PerformanceRegressionTestScenario(baseline_file)
    return scenario.run_test(save_as_baseline)


if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    save_baseline = "--save-baseline" in sys.argv
    baseline_file = None
    
    # Look for baseline file argument
    for i, arg in enumerate(sys.argv):
        if arg == "--baseline" and i + 1 < len(sys.argv):
            baseline_file = sys.argv[i + 1]
            break
            
    # Run performance regression test
    result = run_performance_regression_test(baseline_file, save_baseline)
    exit(0 if result.success else 1)