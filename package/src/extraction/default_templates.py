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
                ExtractionField.GRADIENT_ACCUMULATION,
                ExtractionField.ATTENTION_HEADS,
                ExtractionField.HIDDEN_SIZE,
                ExtractionField.LAYERS_COUNT
            ],
            validation_rules={
                ExtractionField.GPU_COUNT: {"min": 1, "max": 10000},
                ExtractionField.PARAMETERS_COUNT: {"min": 1, "max": 1000000},  # In millions
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 50000},
                ExtractionField.SEQUENCE_LENGTH: {"min": 32, "max": 100000},
                ExtractionField.BATCH_SIZE: {"min": 1, "max": 10000},
                ExtractionField.ATTENTION_HEADS: {"min": 1, "max": 256},
                ExtractionField.HIDDEN_SIZE: {"min": 64, "max": 100000}
            },
            normalization_rules={
                ExtractionField.PARAMETERS_COUNT: "convert_to_millions",
                ExtractionField.DATASET_SIZE_GB: "convert_to_gb",
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours"
            }
        )
    
    @staticmethod
    def cv_training_template() -> ExtractionTemplate:
        """Computer vision training requirements template."""
        return ExtractionTemplate(
            template_id="cv_training_v1",
            template_name="Computer Vision Training Requirements",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.TRAINING_TIME_HOURS,
                ExtractionField.DATASET_SIZE_GB
            ],
            optional_fields=[
                ExtractionField.GPU_COUNT,
                ExtractionField.GPU_MEMORY_GB,
                ExtractionField.BATCH_SIZE,
                ExtractionField.PARAMETERS_COUNT,
                ExtractionField.LAYERS_COUNT,
                ExtractionField.DATASET_SAMPLES
            ],
            validation_rules={
                ExtractionField.GPU_COUNT: {"min": 1, "max": 10000},
                ExtractionField.GPU_MEMORY_GB: {"min": 4, "max": 100},
                ExtractionField.BATCH_SIZE: {"min": 1, "max": 10000},
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 50000},
                ExtractionField.DATASET_SIZE_GB: {"min": 0.001, "max": 100000}
            },
            normalization_rules={
                ExtractionField.DATASET_SIZE_GB: "convert_to_gb",
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours",
                ExtractionField.GPU_MEMORY_GB: "convert_to_gb"
            }
        )
    
    @staticmethod
    def rl_training_template() -> ExtractionTemplate:
        """Reinforcement learning training requirements template."""
        return ExtractionTemplate(
            template_id="rl_training_v1",
            template_name="Reinforcement Learning Training Requirements",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.TRAINING_TIME_HOURS
            ],
            optional_fields=[
                ExtractionField.GPU_COUNT,
                ExtractionField.TRAINING_STEPS,
                ExtractionField.PARAMETERS_COUNT,
                ExtractionField.BATCH_SIZE,
                ExtractionField.GPU_MEMORY_GB,
                ExtractionField.TOTAL_COMPUTE_HOURS
            ],
            validation_rules={
                ExtractionField.GPU_COUNT: {"min": 1, "max": 10000},
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 100000},
                ExtractionField.TRAINING_STEPS: {"min": 1000, "max": 1e12},
                ExtractionField.BATCH_SIZE: {"min": 1, "max": 100000}
            },
            normalization_rules={
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours",
                ExtractionField.TOTAL_COMPUTE_HOURS: "convert_to_hours"
            }
        )
    
    @staticmethod
    def generic_training_template() -> ExtractionTemplate:
        """Generic ML training requirements template."""
        return ExtractionTemplate(
            template_id="generic_training_v1",
            template_name="Generic ML Training Requirements",
            version="1.0",
            required_fields=[
                ExtractionField.TRAINING_TIME_HOURS
            ],
            optional_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.GPU_COUNT,
                ExtractionField.GPU_MEMORY_GB,
                ExtractionField.TPU_VERSION,
                ExtractionField.TPU_CORES,
                ExtractionField.PARAMETERS_COUNT,
                ExtractionField.DATASET_SIZE_GB,
                ExtractionField.BATCH_SIZE,
                ExtractionField.TRAINING_STEPS,
                ExtractionField.TOTAL_COMPUTE_HOURS,
                ExtractionField.ESTIMATED_COST_USD
            ],
            validation_rules={
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.01, "max": 100000},
                ExtractionField.GPU_COUNT: {"min": 1, "max": 100000},
                ExtractionField.TPU_CORES: {"min": 1, "max": 10000},
                ExtractionField.ESTIMATED_COST_USD: {"min": 0, "max": 10000000}
            },
            normalization_rules={
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours",
                ExtractionField.DATASET_SIZE_GB: "convert_to_gb",
                ExtractionField.PARAMETERS_COUNT: "convert_to_millions"
            }
        )
    
    @staticmethod
    def inference_template() -> ExtractionTemplate:
        """Model inference requirements template."""
        return ExtractionTemplate(
            template_id="inference_v1",
            template_name="Model Inference Requirements",
            version="1.0",
            required_fields=[
                ExtractionField.GPU_TYPE,
                ExtractionField.GPU_MEMORY_GB
            ],
            optional_fields=[
                ExtractionField.GPU_COUNT,
                ExtractionField.BATCH_SIZE,
                ExtractionField.PARAMETERS_COUNT,
                ExtractionField.SEQUENCE_LENGTH,
                ExtractionField.HIDDEN_SIZE,
                ExtractionField.LAYERS_COUNT
            ],
            validation_rules={
                ExtractionField.GPU_MEMORY_GB: {"min": 1, "max": 100},
                ExtractionField.BATCH_SIZE: {"min": 1, "max": 10000},
                ExtractionField.GPU_COUNT: {"min": 1, "max": 1000},
                ExtractionField.SEQUENCE_LENGTH: {"min": 1, "max": 100000}
            },
            normalization_rules={
                ExtractionField.GPU_MEMORY_GB: "convert_to_gb",
                ExtractionField.PARAMETERS_COUNT: "convert_to_millions"
            }
        )