"""Configuration classes for mock data generation."""

from dataclasses import dataclass
from enum import Enum


class DataQuality(Enum):
    """Data quality levels for generated mock data."""

    NORMAL = "normal"
    EDGE_CASE = "edge_case"
    CORRUPTED = "corrupted"


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""

    quality: DataQuality
    size: int = 100
    seed: int = 42
