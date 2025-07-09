"""Tests for default extraction templates."""

from compute_forecast.pipeline.content_extraction.templates.default_templates import (
    DefaultTemplates,
)
from compute_forecast.pipeline.content_extraction.templates.template_engine import (
    ExtractionField,
)


class TestDefaultTemplates:
    """Test default template definitions."""

    def test_nlp_training_template(self):
        """Test NLP training template configuration."""
        template = DefaultTemplates.nlp_training_template()

        # Check basic properties
        assert template.template_id == "nlp_training_v1"
        assert template.template_name == "NLP Model Training Requirements"
        assert template.version == "1.0"

        # Check required fields
        required = template.required_fields
        assert ExtractionField.GPU_TYPE in required
        assert ExtractionField.TRAINING_TIME_HOURS in required
        assert ExtractionField.PARAMETERS_COUNT in required
        assert ExtractionField.DATASET_SIZE_GB in required

        # Check optional fields
        optional = template.optional_fields
        assert ExtractionField.GPU_COUNT in optional
        assert ExtractionField.BATCH_SIZE in optional
        assert ExtractionField.SEQUENCE_LENGTH in optional
        assert ExtractionField.GRADIENT_ACCUMULATION in optional

        # Check validation rules
        assert ExtractionField.GPU_COUNT in template.validation_rules
        assert template.validation_rules[ExtractionField.GPU_COUNT]["min"] == 1
        assert template.validation_rules[ExtractionField.GPU_COUNT]["max"] == 10000

        # Check normalization rules
        assert ExtractionField.PARAMETERS_COUNT in template.normalization_rules
        assert (
            template.normalization_rules[ExtractionField.PARAMETERS_COUNT]
            == "convert_to_millions"
        )

    def test_cv_training_template(self):
        """Test computer vision training template configuration."""
        template = DefaultTemplates.cv_training_template()

        # Check basic properties
        assert template.template_id == "cv_training_v1"
        assert template.template_name == "Computer Vision Training Requirements"
        assert template.version == "1.0"

        # Check CV-specific required fields
        required = template.required_fields
        assert ExtractionField.GPU_TYPE in required
        assert ExtractionField.TRAINING_TIME_HOURS in required
        assert ExtractionField.DATASET_SIZE_GB in required

        # Should have GPU memory as important for CV
        assert (
            ExtractionField.GPU_MEMORY_GB in required
            or ExtractionField.GPU_MEMORY_GB in template.optional_fields
        )

        # Check for batch size (important for CV)
        all_fields = required + template.optional_fields
        assert ExtractionField.BATCH_SIZE in all_fields

    def test_rl_training_template(self):
        """Test reinforcement learning training template configuration."""
        template = DefaultTemplates.rl_training_template()

        # Check basic properties
        assert template.template_id == "rl_training_v1"
        assert template.template_name == "Reinforcement Learning Training Requirements"
        assert template.version == "1.0"

        # Check RL-specific fields
        all_fields = template.required_fields + template.optional_fields

        # RL often uses different metrics than supervised learning
        assert ExtractionField.TRAINING_TIME_HOURS in template.required_fields
        assert ExtractionField.TRAINING_STEPS in all_fields  # RL uses steps/episodes

    def test_generic_training_template(self):
        """Test generic ML training template."""
        template = DefaultTemplates.generic_training_template()

        # Check basic properties
        assert template.template_id == "generic_training_v1"
        assert template.template_name == "Generic ML Training Requirements"
        assert template.version == "1.0"

        # Should have minimal required fields
        required = template.required_fields
        assert len(required) <= 3  # Keep it minimal

        # Should have many optional fields for flexibility
        optional = template.optional_fields
        assert len(optional) >= 5

    def test_inference_template(self):
        """Test inference/deployment template."""
        template = DefaultTemplates.inference_template()

        # Check basic properties
        assert template.template_id == "inference_v1"
        assert template.template_name == "Model Inference Requirements"
        assert template.version == "1.0"

        # Inference has different requirements than training
        all_fields = template.required_fields + template.optional_fields

        # Should focus on runtime requirements
        assert ExtractionField.GPU_TYPE in all_fields
        assert ExtractionField.GPU_MEMORY_GB in all_fields
        assert ExtractionField.BATCH_SIZE in all_fields

        # Training time is less relevant for inference
        assert ExtractionField.TRAINING_TIME_HOURS not in template.required_fields

    def test_all_templates_valid(self):
        """Test that all templates are valid and complete."""
        templates = [
            DefaultTemplates.nlp_training_template(),
            DefaultTemplates.cv_training_template(),
            DefaultTemplates.rl_training_template(),
            DefaultTemplates.generic_training_template(),
            DefaultTemplates.inference_template(),
        ]

        for template in templates:
            # Check basic structure
            assert template.template_id
            assert template.template_name
            assert template.version
            assert isinstance(template.required_fields, list)
            assert isinstance(template.optional_fields, list)
            assert isinstance(template.validation_rules, dict)
            assert isinstance(template.normalization_rules, dict)

            # Check no field is both required and optional
            required_set = set(template.required_fields)
            optional_set = set(template.optional_fields)
            assert len(required_set & optional_set) == 0

            # Check validation rules only apply to fields in template
            all_fields = required_set | optional_set
            for field in template.validation_rules:
                assert field in all_fields

    def test_template_registration(self):
        """Test that templates can be registered with engine."""
        from compute_forecast.pipeline.content_extraction.templates.template_engine import (
            ExtractionTemplateEngine,
        )

        engine = ExtractionTemplateEngine()

        # Default templates should be loaded
        assert len(engine.templates) > 0

        # Check specific templates are loaded
        assert "nlp_training_v1" in engine.templates
        assert "cv_training_v1" in engine.templates
        assert "rl_training_v1" in engine.templates
