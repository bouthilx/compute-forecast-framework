"""Default extraction templates for different scenarios."""

from .template_engine import ExtractionTemplate, ExtractionField


class DefaultTemplates:
    """Default extraction templates for different scenarios."""
    
    @staticmethod
    def nlp_training_template() -> ExtractionTemplate:
        """NLP model training requirements template."""
        return ExtractionTemplate(
            template_id="nlp_training_v1",
            template_name="NLP Model Training Requirements",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.TRAINING_TIME_HOURS,
                ExtractionField.PARAMETERS_COUNT,
                ExtractionField.DATASET_SIZE_GB
            ],
            optional_fields=[
                ExtractionField.GPU_COUNT,
                ExtractionField.BATCH_SIZE,
                ExtractionField.SEQUENCE_LENGTH,
                ExtractionField.GRADIENT_ACCUMULATION
            ],
            validation_rules={
                ExtractionField.GPU_COUNT: {"min": 1, "max": 10000},
                ExtractionField.PARAMETERS_COUNT: {"min": 1e6, "max": 1e12},
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 50000},
                ExtractionField.SEQUENCE_LENGTH: {"min": 32, "max": 100000}
            },
            normalization_rules={
                ExtractionField.PARAMETERS_COUNT: "convert_to_millions",
                ExtractionField.DATASET_SIZE_GB: "convert_to_gb",
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours"
            }
        )