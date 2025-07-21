"""Profiling utilities for performance analysis"""

import time
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TimingRecord:
    """Record for a single timing measurement"""

    name: str
    start_time: float
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time


class PerformanceProfiler:
    """Collect and analyze performance timing data"""

    def __init__(self, name: str):
        self.name = name
        self.records: List[TimingRecord] = []
        self.active_records: Dict[str, TimingRecord] = {}
        self.logger = logging.getLogger(f"profiler.{name}")

    @contextmanager
    def measure(self, operation: str, **metadata):
        """Context manager to measure operation timing"""
        record = TimingRecord(name=operation, start_time=time.time(), metadata=metadata)

        # Handle nested measurements
        key = f"{operation}_{id(record)}"
        self.active_records[key] = record

        try:
            yield record
        finally:
            record.end_time = time.time()
            self.records.append(record)
            del self.active_records[key]

            # Log timing
            self.logger.debug(
                f"{operation}: {record.duration:.3f}s "
                + " ".join(f"{k}={v}" for k, v in metadata.items())
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get timing summary statistics"""
        if not self.records:
            return {}

        # Group by operation name
        operations: Dict[str, Dict[str, Any]] = {}
        for record in self.records:
            if record.duration is None:
                continue

            if record.name not in operations:
                operations[record.name] = {
                    "count": 0,
                    "total": 0.0,
                    "min": float("inf"),
                    "max": 0.0,
                    "records": [],
                }

            op = operations[record.name]
            op["count"] += 1
            op["total"] += record.duration
            op["min"] = min(op["min"], record.duration)
            op["max"] = max(op["max"], record.duration)
            op["records"].append(record)

        # Calculate averages and format
        summary: Dict[str, Any] = {
            "total_time": sum(r.duration for r in self.records if r.duration),
            "operations": {},
        }

        for name, stats in operations.items():
            summary["operations"][name] = {
                "count": stats["count"],
                "total": stats["total"],
                "average": stats["total"] / stats["count"],
                "min": stats["min"],
                "max": stats["max"],
            }

        return summary

    def print_report(self):
        """Print formatted timing report"""
        summary = self.get_summary()

        print(f"\n{'=' * 60}")
        print(f"Performance Report: {self.name}")
        print(f"{'=' * 60}")
        print(f"Total time: {summary.get('total_time', 0):.2f}s")
        print("\nOperation breakdown:")
        print(
            f"{'Operation':<30} {'Count':>8} {'Total':>10} {'Avg':>10} {'Min':>10} {'Max':>10}"
        )
        print(f"{'-' * 30} {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")

        # Sort by total time descending
        ops = summary.get("operations", {})
        for name, stats in sorted(
            ops.items(), key=lambda x: x[1]["total"], reverse=True
        ):
            print(
                f"{name:<30} {stats['count']:>8} {stats['total']:>10.3f} "
                f"{stats['average']:>10.3f} {stats['min']:>10.3f} {stats['max']:>10.3f}"
            )

        print(f"{'=' * 60}\n")

    def get_detailed_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown with metadata analysis"""
        breakdown: Dict[str, Any] = {}

        for record in self.records:
            if record.duration is None:
                continue

            # Create hierarchical breakdown based on metadata
            if "source" in record.metadata:
                source = record.metadata["source"]
                if source not in breakdown:
                    breakdown[source] = {}

                if record.name not in breakdown[source]:
                    breakdown[source][record.name] = []

                breakdown[source][record.name].append(
                    {"duration": record.duration, "metadata": record.metadata}
                )

        return breakdown


# Global profiler instance for easy access
_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> Optional[PerformanceProfiler]:
    """Get global profiler instance"""
    return _profiler


def set_profiler(profiler: PerformanceProfiler):
    """Set global profiler instance"""
    global _profiler
    _profiler = profiler


@contextmanager
def profile_operation(operation: str, **metadata):
    """Convenience function to profile if profiler is active"""
    profiler = get_profiler()
    if profiler:
        with profiler.measure(operation, **metadata) as record:
            yield record
    else:
        yield None
