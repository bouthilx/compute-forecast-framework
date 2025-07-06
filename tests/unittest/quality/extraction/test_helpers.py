"""
Test helpers for extraction validation tests.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MockComputationalAnalysis:
    """Mock computational analysis with individual fields for testing."""
    gpu_hours: Optional[float] = None
    gpu_type: Optional[str] = None
    gpu_count: Optional[int] = None
    training_time: Optional[float] = None
    parameters: Optional[float] = None
    gpu_memory: Optional[float] = None
    batch_size: Optional[int] = None
    dataset_size: Optional[float] = None
    epochs: Optional[int] = None
    learning_rate: Optional[float] = None
    optimizer: Optional[str] = None
    framework: Optional[str] = None
    cost_estimate: Optional[float] = None
    model_size_gb: Optional[float] = None
    
    def __post_init__(self):
        """Make the object dict-like for compatibility."""
        self.__dict__.update(self.__dict__)


def create_mock_computational_analysis(**kwargs) -> MockComputationalAnalysis:
    """Create a mock computational analysis object."""
    return MockComputationalAnalysis(**kwargs)