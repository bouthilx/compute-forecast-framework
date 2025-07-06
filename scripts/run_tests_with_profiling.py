#!/usr/bin/env python3
"""Run pytest with profiling and generate performance report."""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_pytest_with_profiling():
    """Run pytest with various profiling options."""

    # Create profile results directory
    profile_dir = Path("profile_results")
    profile_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Run pytest with profiling
    cmd = [
        "pytest",
        "--durations=50",  # Show 50 slowest tests
        "--profile",  # Enable profiling
        f"--pstats-dir={profile_dir}",
        "--profile-svg",  # Generate SVG graph
        f"--junit-xml=test_results_{timestamp}.xml",
        "--timeout=300",  # 5 minute timeout per test
        "--timeout-method=thread",
        "-v",
        "--tb=short",  # Shorter traceback format
    ]

    # Add benchmark options if running performance tests
    if "--benchmark" in sys.argv:
        cmd.extend(
            [
                "--benchmark-only",
                f"--benchmark-json=benchmark_results_{timestamp}.json",
                "--benchmark-verbose",
                "--benchmark-autosave",
            ]
        )

    # Add coverage if requested
    if "--coverage" in sys.argv:
        cmd.extend(
            [
                "--cov=compute_forecast",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=90",
            ]
        )

    # Add specific test paths if provided
    test_paths = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if test_paths:
        cmd.extend(test_paths)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    # Generate summary report
    if result.returncode == 0:
        print("\n✅ Tests passed successfully!")
        print(f"Profile results saved to: {profile_dir}/")
        print(f"Test results saved to: test_results_{timestamp}.xml")
    else:
        print("\n❌ Tests failed!")
        sys.exit(result.returncode)


if __name__ == "__main__":
    run_pytest_with_profiling()
