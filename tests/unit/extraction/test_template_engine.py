"""Tests for extraction template engine."""

import pytest
from dataclasses import FrozenInstanceError

from compute_forecast.pipeline.content_extraction.templates.template_engine import (
    ExtractionTemplate,
    ExtractionField,
)


class TestExtractionField:
    """Test ExtractionField enum."""

    def test_hardware_fields(self):
        """Test hardware specification fields exist."""
        assert ExtractionField.GPU_COUNT.value == "gpu_count"
        assert ExtractionField.GPU_TYPE.value == "gpu_type"
        assert ExtractionField.GPU_MEMORY_GB.value == "gpu_memory_gb"
        assert ExtractionField.TPU_VERSION.value == "tpu_version"
        assert ExtractionField.TPU_CORES.value == "tpu_cores"

    def test_training_fields(self):
        """Test training metrics fields exist."""
        assert ExtractionField.TRAINING_TIME_HOURS.value == "training_time_hours"
        assert ExtractionField.TRAINING_STEPS.value == "training_steps"
        assert ExtractionField.BATCH_SIZE.value == "batch_size"
        assert ExtractionField.GRADIENT_ACCUMULATION.value == "gradient_accumulation"

    def test_model_fields(self):
        """Test model specification fields exist."""
        assert ExtractionField.PARAMETERS_COUNT.value == "parameters_count"
        assert ExtractionField.LAYERS_COUNT.value == "layers_count"
        assert ExtractionField.ATTENTION_HEADS.value == "attention_heads"
        assert ExtractionField.HIDDEN_SIZE.value == "hidden_size"

    def test_dataset_fields(self):
        """Test dataset specification fields exist."""
        assert ExtractionField.DATASET_SIZE_GB.value == "dataset_size_gb"
        assert ExtractionField.DATASET_SAMPLES.value == "dataset_samples"
        assert ExtractionField.SEQUENCE_LENGTH.value == "sequence_length"

    def test_cost_fields(self):
        """Test computational cost fields exist."""
        assert ExtractionField.TOTAL_COMPUTE_HOURS.value == "total_compute_hours"
        assert ExtractionField.ESTIMATED_COST_USD.value == "estimated_cost_usd"
        assert ExtractionField.CARBON_FOOTPRINT_KG.value == "carbon_footprint_kg"


class TestExtractionTemplate:
    """Test ExtractionTemplate dataclass."""

    def test_template_creation(self):
        """Test creating a basic extraction template."""
        template = ExtractionTemplate(
            template_id="test_template",
            template_name="Test Template",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.TRAINING_TIME_HOURS,
            ],
            optional_fields=[ExtractionField.BATCH_SIZE],
            validation_rules={
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 10000}
            },
            normalization_rules={
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours"
            },
        )

        assert template.template_id == "test_template"
        assert template.template_name == "Test Template"
        assert template.version == "1.0"
        assert len(template.required_fields) == 2
        assert ExtractionField.GPU_TYPE in template.required_fields
        assert ExtractionField.BATCH_SIZE in template.optional_fields

    def test_template_immutability(self):
        """Test that template is immutable after creation."""
        template = ExtractionTemplate(
            template_id="test_template",
            template_name="Test Template",
            version="1.0",
            required_fields=[],
            optional_fields=[],
            validation_rules={},
            normalization_rules={},
        )

        # Should not be able to modify fields
        with pytest.raises(FrozenInstanceError):
            template.template_id = "modified"

    def test_template_field_validation(self):
        """Test that template validates field types."""
        # Should accept only ExtractionField enums
        with pytest.raises(TypeError):
            ExtractionTemplate(
                template_id="test",
                template_name="Test",
                version="1.0",
                required_fields=["not_an_enum"],  # Invalid type
                optional_fields=[],
                validation_rules={},
                normalization_rules={},
            )

    def test_template_completeness_calculation(self):
        """Test calculating template completeness."""
        template = ExtractionTemplate(
            template_id="test",
            template_name="Test",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.TRAINING_TIME_HOURS,
                ExtractionField.PARAMETERS_COUNT,
            ],
            optional_fields=[
                ExtractionField.BATCH_SIZE,
                ExtractionField.SEQUENCE_LENGTH,
            ],
            validation_rules={},
            normalization_rules={},
        )

        # Test with all required fields
        extracted_fields = {
            ExtractionField.GPU_TYPE: "A100",
            ExtractionField.TRAINING_TIME_HOURS: 100.0,
            ExtractionField.PARAMETERS_COUNT: 1e9,
        }
        assert template.calculate_completeness(extracted_fields) == 1.0

        # Test with missing required field
        extracted_fields = {
            ExtractionField.GPU_TYPE: "A100",
            ExtractionField.TRAINING_TIME_HOURS: 100.0,
        }
        assert template.calculate_completeness(extracted_fields) == 2 / 3

        # Test with optional fields included
        extracted_fields = {
            ExtractionField.GPU_TYPE: "A100",
            ExtractionField.TRAINING_TIME_HOURS: 100.0,
            ExtractionField.PARAMETERS_COUNT: 1e9,
            ExtractionField.BATCH_SIZE: 32,
        }
        # Should still be 1.0 as all required fields are present
        assert template.calculate_completeness(extracted_fields) == 1.0
