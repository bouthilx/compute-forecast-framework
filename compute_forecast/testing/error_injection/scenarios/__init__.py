"""Pre-defined error scenarios for testing."""

from compute_forecast.testing.error_injection.scenarios.api_failures import (
    APIFailureScenarios,
)
from compute_forecast.testing.error_injection.scenarios.data_corruption import (
    DataCorruptionScenarios,
)
from compute_forecast.testing.error_injection.scenarios.resource_exhaustion import (
    ResourceExhaustionScenarios,
)

__all__ = [
    "APIFailureScenarios",
    "DataCorruptionScenarios",
    "ResourceExhaustionScenarios",
]
