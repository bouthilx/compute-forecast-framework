"""
Comprehensive Test Runner for End-to-End Pipeline Testing
Orchestrates all test scenarios and generates comprehensive reports.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .normal_flow import run_normal_flow_test, NormalFlowResult
from .large_scale import run_large_scale_test, LargeScaleResult
from .error_recovery import run_error_recovery_test, ErrorRecoveryResult
from .performance_regression import (
    run_performance_regression_test,
    PerformanceRegressionResult,
)


@dataclass
class TestSuiteResult:
    """Overall test suite result"""

    success: bool
    execution_time_seconds: float
    tests_run: int
    tests_passed: int
    tests_failed: int
    normal_flow_result: Optional[NormalFlowResult]
    large_scale_result: Optional[LargeScaleResult]
    error_recovery_result: Optional[ErrorRecoveryResult]
    performance_regression_result: Optional[PerformanceRegressionResult]
    overall_score: float  # 0.0 to 1.0
    summary: Dict[str, Any]
    recommendations: List[str]
    critical_issues: List[str]
    timestamp: str


class EndToEndTestRunner:
    """
    Comprehensive test runner for all end-to-end test scenarios.

    Runs all test scenarios in sequence and generates comprehensive reports.
    """

    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = output_dir
        self.results: Dict[str, Any] = {}

    def run_all_tests(
        self,
        include_large_scale: bool = True,
        include_error_recovery: bool = True,
        include_regression: bool = True,
        save_performance_baseline: bool = False,
    ) -> TestSuiteResult:
        """Run all test scenarios"""

        start_time = time.time()
        print("🎯 Starting End-to-End Pipeline Test Suite")
        print("=" * 60)

        results = {}
        tests_run = 0
        tests_passed = 0

        # 1. Normal Flow Test (always run)
        print("\n1️⃣ Running Normal Flow Test...")
        try:
            normal_result = run_normal_flow_test()
            results["normal_flow"] = normal_result
            tests_run += 1
            if normal_result.success:
                tests_passed += 1
                print("   ✅ Normal Flow Test PASSED")
            else:
                print("   ❌ Normal Flow Test FAILED")
        except Exception as e:
            print(f"   💥 Normal Flow Test ERROR: {e}")
            results["normal_flow"] = None
            tests_run += 1

        # 2. Large Scale Test (optional)
        if include_large_scale:
            print("\n2️⃣ Running Large Scale Test...")
            try:
                # Use normal flow time as baseline if available
                baseline_time = (
                    results["normal_flow"].execution_time_seconds
                    if results["normal_flow"] and results["normal_flow"].success
                    else 300.0
                )

                large_scale_result = run_large_scale_test(baseline_time)
                results["large_scale"] = large_scale_result
                tests_run += 1
                if large_scale_result.success:
                    tests_passed += 1
                    print("   ✅ Large Scale Test PASSED")
                else:
                    print("   ❌ Large Scale Test FAILED")
            except Exception as e:
                print(f"   💥 Large Scale Test ERROR: {e}")
                results["large_scale"] = None
                tests_run += 1
        else:
            results["large_scale"] = None

        # 3. Error Recovery Test (optional)
        if include_error_recovery:
            print("\n3️⃣ Running Error Recovery Test...")
            try:
                error_recovery_result = run_error_recovery_test()
                results["error_recovery"] = error_recovery_result
                tests_run += 1
                if error_recovery_result.success:
                    tests_passed += 1
                    print("   ✅ Error Recovery Test PASSED")
                else:
                    print("   ❌ Error Recovery Test FAILED")
            except Exception as e:
                print(f"   💥 Error Recovery Test ERROR: {e}")
                results["error_recovery"] = None
                tests_run += 1
        else:
            results["error_recovery"] = None

        # 4. Performance Regression Test (optional)
        if include_regression:
            print("\n4️⃣ Running Performance Regression Test...")
            try:
                regression_result = run_performance_regression_test(
                    save_as_baseline=save_performance_baseline
                )
                results["performance_regression"] = regression_result
                tests_run += 1
                if regression_result.success:
                    tests_passed += 1
                    print("   ✅ Performance Regression Test PASSED")
                else:
                    print("   ❌ Performance Regression Test FAILED")
            except Exception as e:
                print(f"   💥 Performance Regression Test ERROR: {e}")
                results["performance_regression"] = None
                tests_run += 1
        else:
            results["performance_regression"] = None

        # Calculate results
        execution_time = time.time() - start_time
        tests_failed = tests_run - tests_passed

        # Generate comprehensive analysis
        suite_result = self._analyze_suite_results(
            results, execution_time, tests_run, tests_passed, tests_failed
        )

        # Save results
        self._save_results(suite_result)

        # Print final summary
        self._print_final_summary(suite_result)

        return suite_result

    def _analyze_suite_results(
        self,
        results: Dict[str, Any],
        execution_time: float,
        tests_run: int,
        tests_passed: int,
        tests_failed: int,
    ) -> TestSuiteResult:
        """Analyze overall test suite results"""

        # Calculate overall success
        overall_success = tests_failed == 0

        # Calculate overall score
        scores = []
        if results["normal_flow"] and results["normal_flow"].success:
            scores.append(1.0)
        elif results["normal_flow"]:
            scores.append(0.5)  # Partial credit for running
        else:
            scores.append(0.0)

        if results["large_scale"]:
            if results["large_scale"].success:
                scores.append(1.0)
            else:
                # Partial score based on scaling factor
                scaling_factor = getattr(results["large_scale"], "scaling_factor", 3.0)
                scores.append(max(0.0, 1.0 - (scaling_factor - 1.0)))
        else:
            scores.append(0.5)  # Neutral if not run

        if results["error_recovery"]:
            if results["error_recovery"].success:
                scores.append(1.0)
            else:
                # Partial score based on resilience
                resilience = getattr(results["error_recovery"], "resilience_score", 0.0)
                scores.append(resilience)
        else:
            scores.append(0.5)  # Neutral if not run

        if results["performance_regression"]:
            if results["performance_regression"].success:
                scores.append(1.0)
            else:
                # Partial score based on regression score
                reg_score = getattr(
                    results["performance_regression"], "overall_regression_score", 0.0
                )
                scores.append(reg_score)
        else:
            scores.append(0.5)  # Neutral if not run

        overall_score = sum(scores) / len(scores)

        # Collect critical issues
        critical_issues = []
        if results["normal_flow"] and not results["normal_flow"].success:
            critical_issues.append(
                "Normal flow test failed - basic pipeline functionality compromised"
            )

        if results["large_scale"] and hasattr(results["large_scale"], "scaling_issues"):
            critical_issues.extend(
                [
                    issue
                    for issue in results["large_scale"].scaling_issues
                    if "critical" in issue.lower()
                ]
            )

        if results["performance_regression"] and hasattr(
            results["performance_regression"], "critical_issues"
        ):
            critical_issues.extend(results["performance_regression"].critical_issues)

        # Collect recommendations
        recommendations = []
        for test_name, test_result in results.items():
            if test_result and hasattr(test_result, "recommendations"):
                recommendations.extend(
                    [f"[{test_name}] {rec}" for rec in test_result.recommendations[:3]]
                )

        # Generate summary
        summary = {
            "pipeline_functionality": "✅ Working"
            if results["normal_flow"] and results["normal_flow"].success
            else "❌ Issues",
            "scalability": self._assess_scalability(results.get("large_scale")),
            "error_resilience": self._assess_error_resilience(
                results.get("error_recovery")
            ),
            "performance_stability": self._assess_performance_stability(
                results.get("performance_regression")
            ),
            "overall_health": "✅ Healthy"
            if overall_score > 0.8
            else "⚠️ Needs Attention"
            if overall_score > 0.6
            else "❌ Critical Issues",
        }

        return TestSuiteResult(
            success=overall_success,
            execution_time_seconds=execution_time,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            normal_flow_result=results["normal_flow"],
            large_scale_result=results["large_scale"],
            error_recovery_result=results["error_recovery"],
            performance_regression_result=results["performance_regression"],
            overall_score=overall_score,
            summary=summary,
            recommendations=recommendations[:10],  # Top 10
            critical_issues=critical_issues,
            timestamp=datetime.now().isoformat(),
        )

    def _assess_scalability(self, large_scale_result) -> str:
        """Assess scalability status"""
        if not large_scale_result:
            return "🔄 Not Tested"
        if large_scale_result.success:
            return "✅ Good"
        elif (
            hasattr(large_scale_result, "scaling_factor")
            and large_scale_result.scaling_factor < 2.0
        ):
            return "⚠️ Acceptable"
        else:
            return "❌ Poor"

    def _assess_error_resilience(self, error_recovery_result) -> str:
        """Assess error resilience status"""
        if not error_recovery_result:
            return "🔄 Not Tested"
        if error_recovery_result.success:
            return "✅ Resilient"
        elif (
            hasattr(error_recovery_result, "resilience_score")
            and error_recovery_result.resilience_score > 0.6
        ):
            return "⚠️ Moderate"
        else:
            return "❌ Fragile"

    def _assess_performance_stability(self, regression_result) -> str:
        """Assess performance stability status"""
        if not regression_result:
            return "🔄 Not Tested"
        if regression_result.success:
            return "✅ Stable"
        elif (
            hasattr(regression_result, "overall_regression_score")
            and regression_result.overall_regression_score > 0.7
        ):
            return "⚠️ Minor Issues"
        else:
            return "❌ Unstable"

    def _save_results(self, suite_result: TestSuiteResult) -> None:
        """Save test results to file"""
        try:
            import os

            os.makedirs(self.output_dir, exist_ok=True)

            # Convert to serializable format
            result_dict = asdict(suite_result)

            # Save detailed results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/pipeline_test_results_{timestamp}.json"

            with open(filename, "w") as f:
                json.dump(result_dict, f, indent=2, default=str)

            print(f"\n💾 Results saved to: {filename}")

        except Exception as e:
            print(f"⚠️ Could not save results: {e}")

    def _print_final_summary(self, result: TestSuiteResult) -> None:
        """Print final test suite summary"""
        print("\n" + "=" * 80)
        print("🎯 END-TO-END PIPELINE TEST SUITE SUMMARY")
        print("=" * 80)

        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"Overall Status: {status}")
        print(f"Overall Score: {result.overall_score:.2f}/1.0")
        print(f"Execution Time: {result.execution_time_seconds:.1f}s")
        print(f"Tests: {result.tests_passed}/{result.tests_run} passed")

        print("\n📊 System Health Assessment:")
        for aspect, status in result.summary.items():
            aspect_formatted = aspect.replace("_", " ").title()
            print(f"   {aspect_formatted}: {status}")

        if result.critical_issues:
            print(f"\n🚨 Critical Issues ({len(result.critical_issues)}):")
            for issue in result.critical_issues[:5]:  # Show top 5
                print(f"   • {issue}")

        if result.recommendations:
            print(f"\n💡 Top Recommendations ({len(result.recommendations)}):")
            for rec in result.recommendations[:8]:  # Show top 8
                print(f"   • {rec}")

        print("\n📈 Individual Test Results:")

        if result.normal_flow_result:
            status = "✅" if result.normal_flow_result.success else "❌"
            print(
                f"   Normal Flow: {status} ({result.normal_flow_result.execution_time_seconds:.1f}s)"
            )

        if result.large_scale_result:
            status = "✅" if result.large_scale_result.success else "❌"
            scaling = getattr(result.large_scale_result, "scaling_factor", 0)
            print(f"   Large Scale: {status} ({scaling:.2f}x scaling)")

        if result.error_recovery_result:
            status = "✅" if result.error_recovery_result.success else "❌"
            resilience = getattr(result.error_recovery_result, "resilience_score", 0)
            print(f"   Error Recovery: {status} ({resilience:.1%} resilience)")

        if result.performance_regression_result:
            status = "✅" if result.performance_regression_result.success else "❌"
            reg_score = getattr(
                result.performance_regression_result, "overall_regression_score", 0
            )
            print(f"   Performance Regression: {status} ({reg_score:.2f} score)")

        print("\n" + "=" * 80)

        # Final recommendation
        if result.overall_score > 0.9:
            print("🎉 Excellent! Pipeline is performing optimally.")
        elif result.overall_score > 0.8:
            print(
                "👍 Good! Pipeline is performing well with minor areas for improvement."
            )
        elif result.overall_score > 0.6:
            print("⚠️ Caution! Pipeline has some issues that should be addressed.")
        else:
            print(
                "🚨 Alert! Pipeline has significant issues requiring immediate attention."
            )

        print("=" * 80)


def run_comprehensive_test_suite(
    include_large_scale: bool = True,
    include_error_recovery: bool = True,
    include_regression: bool = True,
    save_performance_baseline: bool = False,
    output_dir: str = "test_results",
) -> TestSuiteResult:
    """Run the comprehensive end-to-end test suite"""

    runner = EndToEndTestRunner(output_dir)
    return runner.run_all_tests(
        include_large_scale=include_large_scale,
        include_error_recovery=include_error_recovery,
        include_regression=include_regression,
        save_performance_baseline=save_performance_baseline,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run End-to-End Pipeline Test Suite")
    parser.add_argument(
        "--skip-large-scale", action="store_true", help="Skip large scale test"
    )
    parser.add_argument(
        "--skip-error-recovery", action="store_true", help="Skip error recovery test"
    )
    parser.add_argument(
        "--skip-regression",
        action="store_true",
        help="Skip performance regression test",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current run as performance baseline",
    )
    parser.add_argument(
        "--output-dir", default="test_results", help="Output directory for test results"
    )

    args = parser.parse_args()

    # Run test suite
    result = run_comprehensive_test_suite(
        include_large_scale=not args.skip_large_scale,
        include_error_recovery=not args.skip_error_recovery,
        include_regression=not args.skip_regression,
        save_performance_baseline=args.save_baseline,
        output_dir=args.output_dir,
    )

    exit(0 if result.success else 1)
