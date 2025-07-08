"""Data corruption scenarios for error injection testing."""

import logging
from typing import List, Dict, Any

from ..injection_framework import ErrorScenario, ErrorType

logger = logging.getLogger(__name__)


class DataCorruptionScenarios:
    """Pre-defined data corruption scenarios for testing."""

    @staticmethod
    def get_paper_corruption_scenario() -> List[ErrorScenario]:
        """
        Get scenario for corrupted paper data.

        Returns:
            List of error scenarios simulating paper data corruption
        """
        return [
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                component="paper_parser",
                probability=0.2,  # 20% of papers corrupted
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=30.0,
                metadata={
                    "corruption_type": "missing_fields",
                    "affected_fields": ["title", "abstract", "authors"],
                },
            ),
            ErrorScenario(
                error_type=ErrorType.INVALID_DATA_FORMAT,
                component="json_decoder",
                probability=0.1,  # 10% format errors
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=10.0,
                metadata={"format_issues": ["invalid_json", "encoding_errors"]},
            ),
        ]

    @staticmethod
    def get_venue_data_corruption_scenario() -> List[ErrorScenario]:
        """
        Get scenario for corrupted venue data.

        Returns:
            List of error scenarios simulating venue data corruption
        """
        return [
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                component="venue_normalizer",
                probability=0.15,
                severity="medium",
                recovery_expected=True,
                max_recovery_time_seconds=20.0,
                metadata={
                    "corruption_type": "inconsistent_naming",
                    "examples": ["NIPS vs NeurIPS", "ICML vs ICML'23"],
                },
            ),
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                component="venue_database",
                probability=0.05,
                severity="high",
                recovery_expected=True,
                max_recovery_time_seconds=60.0,
                metadata={
                    "corruption_type": "database_inconsistency",
                    "recovery_method": "rebuild_index",
                },
            ),
        ]

    @staticmethod
    def get_checkpoint_corruption_scenario() -> List[ErrorScenario]:
        """
        Get scenario for corrupted checkpoint data.

        Returns:
            List of error scenarios simulating checkpoint corruption
        """
        return [
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                component="checkpoint_manager",
                probability=0.05,  # 5% chance - should be rare
                severity="critical",
                recovery_expected=True,
                max_recovery_time_seconds=180.0,
                metadata={
                    "corruption_type": "partial_write",
                    "recovery_method": "use_previous_checkpoint",
                },
            ),
            ErrorScenario(
                error_type=ErrorType.INVALID_DATA_FORMAT,
                component="state_persistence",
                probability=0.02,
                severity="critical",
                recovery_expected=True,
                max_recovery_time_seconds=120.0,
                metadata={
                    "corruption_type": "schema_mismatch",
                    "recovery_method": "migrate_schema",
                },
            ),
        ]

    @staticmethod
    def get_progressive_corruption_scenario() -> List[ErrorScenario]:
        """
        Get scenario for progressive data corruption.

        Returns:
            List of error scenarios simulating increasing corruption
        """
        scenarios = []

        # Start with low corruption that increases over time
        for i in range(5):
            probability = 0.05 + (i * 0.05)  # 5%, 10%, 15%, 20%, 25%
            severity = "low" if i < 2 else "medium" if i < 4 else "high"

            scenarios.append(
                ErrorScenario(
                    error_type=ErrorType.DATA_CORRUPTION,
                    component="data_processor",
                    probability=probability,
                    severity=severity,
                    recovery_expected=True,
                    max_recovery_time_seconds=30.0 + (i * 10),
                    metadata={"stage": i + 1, "corruption_level": f"{probability:.0%}"},
                )
            )

        return scenarios

    @staticmethod
    def validate_data_integrity(recovery_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data integrity after corruption recovery.

        Args:
            recovery_metrics: Metrics from recovery testing

        Returns:
            Validation results
        """
        validation = {"passed": True, "checks": [], "failures": []}

        # Check data preservation
        data_preserved = recovery_metrics.get("data_preservation_rate", 0)
        if data_preserved < 0.95:  # 95% threshold
            validation["passed"] = False
            validation["failures"].append(
                f"Data preservation rate {data_preserved:.1%} below 95% threshold"
            )
        else:
            validation["checks"].append(
                f"Data preservation rate {data_preserved:.1%} meets requirement"
            )

        # Check corruption detection
        detection_rate = recovery_metrics.get("corruption_detection_rate", 0)
        if detection_rate < 0.99:  # 99% detection required
            validation["passed"] = False
            validation["failures"].append(
                f"Corruption detection rate {detection_rate:.1%} below 99% threshold"
            )
        else:
            validation["checks"].append("Corruption detection working correctly")

        # Check recovery success
        recovery_success = recovery_metrics.get("corruption_recovery_rate", 0)
        if recovery_success < 0.95:
            validation["passed"] = False
            validation["failures"].append(
                f"Corruption recovery rate {recovery_success:.1%} below 95% threshold"
            )
        else:
            validation["checks"].append("Corruption recovery successful")

        # Check no data loss for critical components
        critical_loss = recovery_metrics.get("critical_data_loss", False)
        if critical_loss:
            validation["passed"] = False
            validation["failures"].append("Critical data loss detected")
        else:
            validation["checks"].append("No critical data loss")

        return validation
