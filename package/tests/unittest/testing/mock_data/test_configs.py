"""Tests for mock data configurations."""

import pytest

from src.testing.mock_data import MockDataConfig, DataQuality


class TestMockDataConfig:
    """Test MockDataConfig functionality."""
    
    def test_config_creation_with_defaults(self):
        """Test config creation with default values."""
        config = MockDataConfig(quality=DataQuality.NORMAL)
        
        assert config.quality == DataQuality.NORMAL
        assert config.size == 100
        assert config.seed == 42
    
    def test_config_creation_with_custom_values(self):
        """Test config creation with custom values."""
        config = MockDataConfig(
            quality=DataQuality.EDGE_CASE,
            size=500,
            seed=12345
        )
        
        assert config.quality == DataQuality.EDGE_CASE
        assert config.size == 500
        assert config.seed == 12345
    
    def test_data_quality_enum_values(self):
        """Test DataQuality enum values."""
        assert DataQuality.NORMAL.value == "normal"
        assert DataQuality.EDGE_CASE.value == "edge_case"
        assert DataQuality.CORRUPTED.value == "corrupted"
    
    def test_config_equality(self):
        """Test config equality comparison."""
        config1 = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
        config2 = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
        config3 = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=43)
        
        assert config1 == config2
        assert config1 != config3