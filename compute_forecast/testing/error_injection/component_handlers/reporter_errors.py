"""Error handler for reporting components."""

import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

from ..injection_framework import ErrorType

logger = logging.getLogger(__name__)


@dataclass
class OutputConfig:
    """Configuration for an output destination."""

    path: str
    output_type: str  # file, memory, network
    priority: int = 0
    enabled: bool = True


class ReporterErrorHandler:
    """
    Test error handling in reporting/output components.

    Simulates output failures, disk space issues, and format errors.
    Verifies alternative output methods.
    """

    def __init__(self):
        """Initialize reporter error handler."""
        self._output_path: Optional[str] = None
        self._output_error_type: Optional[str] = None
        self._alternative_outputs: Dict[str, OutputConfig] = {}
        self._active_output: str = "primary"
        self._format_errors: Dict[str, bool] = {}
        self._last_error: Optional[Dict[str, Any]] = None
        self._disk_space_mb = 1000.0  # Default 1GB

    def set_output_path(self, path: str) -> None:
        """
        Set primary output path.

        Args:
            path: Output path
        """
        self._output_path = path
        self._alternative_outputs["primary"] = OutputConfig(
            path=path, output_type="file", priority=10, enabled=True
        )
        logger.info(f"Set primary output path: {path}")

    def simulate_output_failure(self, failure_type: str) -> None:
        """
        Simulate output failure.

        Args:
            failure_type: Type of failure (permission_denied, path_not_found, io_error)
        """
        valid_types = ["permission_denied", "path_not_found", "io_error", "disk_full"]
        if failure_type not in valid_types:
            raise ValueError(f"Invalid failure type. Must be one of: {valid_types}")

        logger.error(f"Simulating output failure: {failure_type}")
        self._output_error_type = failure_type

        # Disable primary output
        if "primary" in self._alternative_outputs:
            self._alternative_outputs["primary"].enabled = False

    def simulate_disk_full(self) -> None:
        """Simulate disk full condition."""
        logger.error("Simulating disk full")
        self._output_error_type = "disk_full"
        self._disk_space_mb = 0.0

        # Disable all file-based outputs
        for name, config in self._alternative_outputs.items():
            if config.output_type == "file":
                config.enabled = False

    def can_write_output(self) -> bool:
        """
        Check if output can be written.

        Returns:
            True if output is possible
        """
        if self._active_output in self._alternative_outputs:
            config = self._alternative_outputs[self._active_output]
            return config.enabled and self._output_error_type is None
        return False

    def get_available_space_mb(self) -> float:
        """
        Get available disk space.

        Returns:
            Available space in MB
        """
        if self._output_error_type == "disk_full":
            return 0.0
        return float(self._disk_space_mb)

    def add_alternative_output(
        self, path: str, name: str, output_type: str = "file", priority: int = 5
    ) -> None:
        """
        Add alternative output destination.

        Args:
            path: Output path or connection string
            name: Name for this output
            output_type: Type of output (file, memory, network)
            priority: Priority for fallback order
        """
        self._alternative_outputs[name] = OutputConfig(
            path=path, output_type=output_type, priority=priority, enabled=True
        )
        logger.info(f"Added alternative output '{name}': {path} (type: {output_type})")

    def verify_alternative_output(self) -> Dict[str, Any]:
        """
        Verify alternative output methods work.

        Returns:
            Dictionary with alternative output status
        """
        # Find available alternatives
        available = [
            (name, config)
            for name, config in self._alternative_outputs.items()
            if config.enabled
            and (config.output_type != "file" or self._output_error_type != "disk_full")
        ]

        if not available:
            return {
                "alternative_available": False,
                "active_output": None,
                "reason": "No alternative outputs available",
            }

        # Sort by priority
        available.sort(key=lambda x: x[1].priority, reverse=True)

        # Select highest priority alternative
        selected_name, selected_config = available[0]
        self._active_output = selected_name

        logger.info(f"Switched to alternative output: {selected_name}")

        return {
            "alternative_available": True,
            "active_output": selected_name,
            "output_type": selected_config.output_type,
            "output_path": selected_config.path,
        }

    def simulate_format_error(self, format_type: str) -> None:
        """
        Simulate format error.

        Args:
            format_type: Format that will fail (json, csv, markdown)
        """
        logger.warning(f"Simulating format error for: {format_type}")
        self._format_errors[format_type] = True

    def format_output(self, data: Any, format_type: str) -> Optional[Any]:
        """
        Attempt to format output data.

        Args:
            data: Data to format
            format_type: Desired format

        Returns:
            Formatted data or None if error
        """
        if format_type in self._format_errors:
            self._last_error = {
                "error_type": ErrorType.INVALID_DATA_FORMAT.value,
                "format": format_type,
                "message": f"Format error for {format_type}",
            }
            logger.error(f"Format error: {format_type}")
            return None

        # Simulate successful formatting
        return data

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """
        Get last error details.

        Returns:
            Last error or None
        """
        return self._last_error

    def attempt_recovery(self) -> Dict[str, Any]:
        """
        Attempt to recover from output errors.

        Returns:
            Recovery result
        """
        if self._output_error_type is None:
            return {"recovered": True, "reason": "No error to recover from"}

        # Try alternative outputs
        alt_result = self.verify_alternative_output()

        if alt_result["alternative_available"]:
            # Clear error if using non-file output for disk issues
            if (
                self._output_error_type == "disk_full"
                and alt_result["output_type"] != "file"
            ):
                self._output_error_type = None

            return {
                "recovered": True,
                "recovery_method": "alternative_output",
                "active_output": alt_result["active_output"],
            }

        return {
            "recovered": False,
            "reason": "No recovery options available",
            "error_type": self._output_error_type,
        }

    def clear_errors(self) -> None:
        """Clear all active errors."""
        self._output_error_type = None
        self._format_errors.clear()
        self._last_error = None
        self._disk_space_mb = 1000.0  # Reset to default

        # Re-enable all outputs
        for config in self._alternative_outputs.values():
            config.enabled = True

        logger.info("All reporter errors cleared")
