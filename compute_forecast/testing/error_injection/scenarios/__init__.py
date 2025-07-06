"""Pre-defined error scenarios for testing."""

from .api_failures import APIFailureScenarios
from .data_corruption import DataCorruptionScenarios
from .resource_exhaustion import ResourceExhaustionScenarios

__all__ = [
    "APIFailureScenarios",
    "DataCorruptionScenarios",
    "ResourceExhaustionScenarios",
]
