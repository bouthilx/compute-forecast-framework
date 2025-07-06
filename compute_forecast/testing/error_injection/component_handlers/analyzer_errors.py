"""Error handler for analysis components."""

import logging
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..injection_framework import ErrorType

logger = logging.getLogger(__name__)


@dataclass
class MemoryState:
    """Current memory state for simulation."""

    total_mb: float
    used_mb: float
    available_mb: float
    pressure_active: bool = False


class AnalyzerErrorHandler:
    """
    Test error handling in analysis pipeline.

    Simulates corrupted inputs, memory pressure, and processing errors.
    Verifies partial result preservation.
    """

    def __init__(self):
        """Initialize analyzer error handler."""
        self._active_corruption_type: Optional[str] = None
        self._memory_state = MemoryState(
            total_mb=8192.0,  # 8GB default
            used_mb=2048.0,  # 2GB used
            available_mb=6144.0,
        )
        self._memory_pressure_active = False
        self._processing_errors_active = False
        self._error_rate = 0.0
        self._total_papers = 0
        self._processed_papers = 0
        self._processing_errors: List[Dict[str, Any]] = []

    def simulate_corrupted_input(self, corruption_type: str) -> None:
        """
        Simulate corrupted paper data.

        Args:
            corruption_type: Type of corruption (missing_fields, invalid_format, encoding_error)
        """
        valid_types = [
            "missing_fields",
            "invalid_format",
            "encoding_error",
            "truncated_data",
        ]
        if corruption_type not in valid_types:
            raise ValueError(f"Invalid corruption type. Must be one of: {valid_types}")

        logger.warning(f"Simulating corrupted input: {corruption_type}")
        self._active_corruption_type = corruption_type

    def simulate_memory_pressure(self) -> None:
        """Simulate low memory conditions."""
        logger.warning("Simulating memory pressure")
        self._memory_pressure_active = True

        # Reduce available memory significantly
        self._memory_state.available_mb = min(
            100.0, self._memory_state.available_mb * 0.1
        )
        self._memory_state.used_mb = (
            self._memory_state.total_mb - self._memory_state.available_mb
        )
        self._memory_state.pressure_active = True

    def verify_partial_analysis(self) -> Dict[str, Any]:
        """
        Verify partial results are preserved.

        Returns:
            Dictionary with partial analysis results
        """
        completion_percentage = (
            (self._processed_papers / self._total_papers * 100)
            if self._total_papers > 0
            else 0
        )

        partial_results = {
            "partial_results_available": self._processed_papers > 0,
            "papers_processed": self._processed_papers,
            "papers_skipped": self._total_papers - self._processed_papers,
            "completion_percentage": completion_percentage,
            "errors_encountered": len(self._processing_errors),
            "memory_pressure_active": self._memory_pressure_active,
            "corruption_detected": self._active_corruption_type is not None,
        }

        if self._memory_pressure_active:
            partial_results["memory_stats"] = {
                "available_mb": self._memory_state.available_mb,
                "used_mb": self._memory_state.used_mb,
                "pressure": True,
            }

        logger.info(f"Partial analysis results: {completion_percentage:.1f}% complete")
        return partial_results

    def set_memory_limit_mb(self, limit_mb: float) -> None:
        """
        Set memory limit for simulation.

        Args:
            limit_mb: Memory limit in megabytes
        """
        self._memory_state.total_mb = limit_mb
        # Ensure we don't have negative available memory
        self._memory_state.available_mb = max(0, limit_mb - self._memory_state.used_mb)
        # Adjust used memory if it exceeds the new limit
        if self._memory_state.used_mb > limit_mb:
            self._memory_state.used_mb = limit_mb * 0.8  # Use 80% of limit
            self._memory_state.available_mb = limit_mb * 0.2
        logger.info(f"Set memory limit to {limit_mb}MB")

    def get_available_memory_mb(self) -> float:
        """
        Get available memory.

        Returns:
            Available memory in MB
        """
        return self._memory_state.available_mb

    def set_total_papers(self, count: int) -> None:
        """
        Set total number of papers to process.

        Args:
            count: Total paper count
        """
        self._total_papers = count
        logger.info(f"Set total papers to process: {count}")

    def process_papers_batch(self, batch_size: int) -> Dict[str, Any]:
        """
        Simulate processing a batch of papers.

        Args:
            batch_size: Number of papers to process

        Returns:
            Processing results
        """
        results = {"processed": 0, "failed": 0, "errors": []}

        for i in range(batch_size):
            # Check memory pressure
            if self._memory_pressure_active and self._memory_state.available_mb < 10:
                error = {
                    "paper_index": self._processed_papers + i,
                    "error_type": ErrorType.MEMORY_EXHAUSTION.value,
                    "message": "Insufficient memory to process paper",
                }
                results["errors"].append(error)
                self._processing_errors.append(error)
                results["failed"] += 1
                continue

            # Check for corruption
            if self._active_corruption_type:
                if (
                    random.random() < 0.3
                ):  # 30% chance of corruption affecting processing
                    error = {
                        "paper_index": self._processed_papers + i,
                        "error_type": ErrorType.DATA_CORRUPTION.value,
                        "corruption_type": self._active_corruption_type,
                        "message": f"Corrupted data: {self._active_corruption_type}",
                    }
                    results["errors"].append(error)
                    self._processing_errors.append(error)
                    results["failed"] += 1
                    continue

            # Check for random processing errors
            if self._processing_errors_active and random.random() < self._error_rate:
                error = {
                    "paper_index": self._processed_papers + i,
                    "error_type": "processing_error",
                    "message": "Random processing error",
                }
                results["errors"].append(error)
                self._processing_errors.append(error)
                results["failed"] += 1
                continue

            # Successful processing
            results["processed"] += 1

            # Simulate memory usage
            if self._memory_pressure_active:
                self._memory_state.used_mb += random.uniform(0.5, 2.0)
                self._memory_state.available_mb = max(
                    0, self._memory_state.total_mb - self._memory_state.used_mb
                )

        self._processed_papers += results["processed"]

        logger.info(
            f"Processed batch: {results['processed']} successful, {results['failed']} failed"
        )
        return results

    def set_error_rate(self, rate: float) -> None:
        """
        Set error injection rate.

        Args:
            rate: Error rate (0.0 to 1.0)
        """
        self._error_rate = max(0.0, min(1.0, rate))
        logger.info(f"Set error rate to {self._error_rate:.1%}")

    def simulate_processing_errors(self) -> None:
        """Enable random processing errors."""
        self._processing_errors_active = True
        logger.warning("Processing errors simulation activated")

    def clear_errors(self) -> None:
        """Clear all active errors."""
        self._active_corruption_type = None
        self._memory_pressure_active = False
        self._processing_errors_active = False
        self._memory_state.pressure_active = False
        self._memory_state.available_mb = (
            self._memory_state.total_mb - 2048.0
        )  # Reset to default
        logger.info("All analyzer errors cleared")
