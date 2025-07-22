"""Unit tests for quality configuration management."""

import pytest
from pydantic import ValidationError

from compute_forecast.quality.core.config import (
    QualityThresholds,
    QualityConfigModel,
    get_default_quality_config,
    create_quality_config,
    validate_quality_config,
)


class TestQualityThresholds:
    """Test quality thresholds configuration."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = QualityThresholds()

        assert thresholds.min_completeness == 0.8
        assert thresholds.min_coverage == 0.7
        assert thresholds.min_consistency == 0.9
        assert thresholds.min_accuracy == 0.85

    def test_threshold_validation(self):
        """Test threshold value validation."""
        # Valid thresholds
        thresholds = QualityThresholds(
            min_completeness=0.95,
            min_coverage=0.5,
            min_consistency=1.0,
            min_accuracy=0.0,
        )
        assert thresholds.min_completeness == 0.95

        # Invalid: > 1.0
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(min_completeness=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

        # Invalid: < 0.0
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(min_coverage=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestQualityConfigModel:
    """Test quality configuration model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = QualityConfigModel(stage="collection")

        assert config.stage == "collection"
        assert config.output_format == "text"
        assert config.verbose is False
        assert config.skip_checks == []
        assert isinstance(config.thresholds, QualityThresholds)

    def test_stage_validation(self):
        """Test stage name validation."""
        # Valid stage with whitespace
        config = QualityConfigModel(stage="  Collection  ")
        assert config.stage == "collection"

        # Empty stage
        with pytest.raises(ValidationError) as exc_info:
            QualityConfigModel(stage="")
        assert "Stage name cannot be empty" in str(exc_info.value)

        # Whitespace-only stage
        with pytest.raises(ValidationError) as exc_info:
            QualityConfigModel(stage="   ")
        assert "Stage name cannot be empty" in str(exc_info.value)

    def test_skip_checks_validation(self):
        """Test skip checks list validation."""
        config = QualityConfigModel(
            stage="collection",
            skip_checks=["  url_check  ", "", "abstract_check", "  "],
        )
        # Should filter out empty strings and strip whitespace
        assert config.skip_checks == ["url_check", "abstract_check"]

    def test_output_format_validation(self):
        """Test output format validation."""
        # Valid formats
        for fmt in ["text", "json", "markdown"]:
            config = QualityConfigModel(stage="collection", output_format=fmt)
            assert config.output_format == fmt

        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            QualityConfigModel(stage="collection", output_format="invalid")
        assert "literal_error" in str(exc_info.value)

    def test_to_quality_config(self):
        """Test conversion to QualityConfig dataclass."""
        model = QualityConfigModel(
            stage="collection",
            thresholds=QualityThresholds(min_completeness=0.9),
            skip_checks=["url_check"],
            output_format="json",
            verbose=True,
        )

        config = model.to_quality_config()

        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.9
        assert config.thresholds["min_coverage"] == 0.7  # Default
        assert config.skip_checks == ["url_check"]
        assert config.output_format == "json"
        assert config.verbose is True


class TestConfigurationFunctions:
    """Test configuration helper functions."""

    def test_get_default_quality_config_collection(self):
        """Test getting default collection configuration."""
        config = get_default_quality_config("collection")

        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.8
        assert config.thresholds["min_coverage"] == 0.7
        assert config.thresholds["min_consistency"] == 0.9
        assert config.thresholds["min_accuracy"] == 0.85

    def test_get_default_quality_config_consolidation(self):
        """Test getting default consolidation configuration."""
        config = get_default_quality_config("consolidation")

        assert config.stage == "consolidation"
        assert config.thresholds["min_completeness"] == 0.85
        assert config.thresholds["min_coverage"] == 0.8

    def test_get_default_quality_config_extraction(self):
        """Test getting default extraction configuration."""
        config = get_default_quality_config("extraction")

        assert config.stage == "extraction"
        assert config.thresholds["min_completeness"] == 0.9
        assert config.thresholds["min_consistency"] == 0.95

    def test_get_default_quality_config_unknown_stage(self):
        """Test getting default configuration for unknown stage."""
        config = get_default_quality_config("unknown_stage")

        assert config.stage == "unknown_stage"
        # Should use base default thresholds
        assert config.thresholds["min_completeness"] == 0.8
        assert config.thresholds["min_coverage"] == 0.7

    def test_create_quality_config_defaults(self):
        """Test creating configuration with defaults."""
        config = create_quality_config("collection")

        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.8
        assert config.output_format == "text"
        assert config.verbose is False

    def test_create_quality_config_with_overrides(self):
        """Test creating configuration with custom overrides."""
        config = create_quality_config(
            stage="collection",
            thresholds={"min_completeness": 0.95, "min_coverage": 0.85},
            skip_checks=["url_check", "abstract_check"],
            output_format="json",
            verbose=True,
        )

        assert config.thresholds["min_completeness"] == 0.95
        assert config.thresholds["min_coverage"] == 0.85
        assert config.thresholds["min_consistency"] == 0.9  # Should keep default
        assert config.thresholds["min_accuracy"] == 0.85  # Should keep default
        assert set(config.skip_checks) == {"url_check", "abstract_check"}
        assert config.output_format == "json"
        assert config.verbose is True

    def test_create_quality_config_validation_error(self):
        """Test validation errors in configuration creation."""
        # Invalid threshold value
        with pytest.raises(ValidationError):
            create_quality_config(
                stage="collection", thresholds={"min_completeness": 1.5}
            )

        # Invalid output format
        with pytest.raises(ValidationError):
            create_quality_config(stage="collection", output_format="invalid")

    def test_validate_quality_config(self):
        """Test configuration validation from dictionary."""
        # Valid configuration
        config_dict = {
            "stage": "collection",
            "thresholds": {"min_completeness": 0.9, "min_coverage": 0.8},
            "skip_checks": ["url_check"],
            "output_format": "json",
            "verbose": True,
        }

        config = validate_quality_config(config_dict)

        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.9
        assert config.output_format == "json"

        # Invalid configuration
        with pytest.raises(ValidationError):
            validate_quality_config(
                {
                    "stage": "",  # Empty stage
                    "output_format": "invalid",
                }
            )
