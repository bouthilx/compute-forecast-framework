#!/usr/bin/env python3
"""Analyze test execution times and generate sorted report."""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET


def run_tests_with_timing():
    """Run pytest and collect timing information."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run pytest with junit XML output for detailed timing
    cmd = [
        "pytest",
        "--tb=short",
        "-v",
        f"--junit-xml=test_times_{timestamp}.xml",
        "--durations=0",  # Show ALL test durations
    ]
    
    # Add test paths if provided
    test_paths = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if test_paths:
        cmd.extend(test_paths)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    # Parse the XML to get detailed timing
    xml_file = f"test_times_{timestamp}.xml"
    return xml_file, result.returncode


def analyze_test_times(xml_file):
    """Parse test results and generate timing report."""
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    test_times = []
    total_time = 0
    
    for testcase in root.findall('.//testcase'):
        classname = testcase.get('classname', 'Unknown')
        name = testcase.get('name', 'Unknown')
        time = float(testcase.get('time', 0))
        
        # Check if test failed or was skipped
        status = 'passed'
        if testcase.find('failure') is not None:
            status = 'failed'
        elif testcase.find('skipped') is not None:
            status = 'skipped'
        elif testcase.find('error') is not None:
            status = 'error'
        
        test_times.append({
            'name': f"{classname}::{name}",
            'time': time,
            'status': status
        })
        total_time += time
    
    # Sort by time (longest first)
    test_times.sort(key=lambda x: x['time'], reverse=True)
    
    # Generate report
    print("\n" + "="*80)
    print("TEST EXECUTION TIME REPORT")
    print("="*80)
    print(f"Total tests: {len(test_times)}")
    print(f"Total time: {total_time:.2f}s")
    print("="*80)
    
    # Show all tests sorted by time
    print("\nAll tests sorted by execution time:")
    print("-"*80)
    print(f"{'Time (s)':>10} {'Status':>10}  Test Name")
    print("-"*80)
    
    for test in test_times:
        status_marker = {
            'passed': '✓',
            'failed': '✗',
            'skipped': '-',
            'error': '!'
        }.get(test['status'], '?')
        
        print(f"{test['time']:10.3f} {status_marker:>10}  {test['name']}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    # Tests by status
    status_counts = {}
    for test in test_times:
        status_counts[test['status']] = status_counts.get(test['status'], 0) + 1
    
    print("\nTests by status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Time statistics
    if test_times:
        times = [t['time'] for t in test_times]
        print(f"\nTiming statistics:")
        print(f"  Slowest test: {max(times):.3f}s")
        print(f"  Fastest test: {min(times):.3f}s")
        print(f"  Average time: {sum(times)/len(times):.3f}s")
        print(f"  Median time: {sorted(times)[len(times)//2]:.3f}s")
        
        # Show tests taking more than certain thresholds
        thresholds = [10, 5, 1, 0.5]
        print("\nTests by duration threshold:")
        for threshold in thresholds:
            slow_tests = [t for t in test_times if t['time'] >= threshold]
            if slow_tests:
                print(f"  Tests ≥ {threshold}s: {len(slow_tests)} ({len(slow_tests)/len(test_times)*100:.1f}%)")
    
    # Save detailed results to JSON
    json_file = xml_file.replace('.xml', '_analysis.json')
    with open(json_file, 'w') as f:
        json.dump({
            'total_tests': len(test_times),
            'total_time': total_time,
            'test_times': test_times,
            'status_counts': status_counts,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {json_file}")
    
    return test_times


if __name__ == "__main__":
    xml_file, return_code = run_tests_with_timing()
    analyze_test_times(xml_file)
    
    if return_code != 0:
        sys.exit(return_code)