"""Integration tests for the extraction template system."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.extraction import (
    ExtractionTemplateEngine,
    ExtractionTemplate,
    ExtractionField,
)
from compute_forecast.data.models import Paper


class TestExtractionIntegration:
    """Test the complete extraction workflow."""

    @pytest.fixture
    def sample_paper_nlp(self):
        """Create a sample NLP paper."""
        paper = Mock(spec=Paper)
        paper.title = "BERT: Pre-training of Deep Bidirectional Transformers"
        paper.abstract = """
        We trained BERT-Large on 16 TPU chips for 4 days. The model has 340M parameters
        and was trained on the BookCorpus (800M words) and Wikipedia (2,500M words).
        We used a batch size of 256 sequences with 512 tokens each.
        """
        paper.content = ""
        paper.full_text = ""
        return paper

    @pytest.fixture
    def sample_paper_cv(self):
        """Create a sample computer vision paper."""
        paper = Mock(spec=Paper)
        paper.title = "ResNet-50 Training on ImageNet"
        paper.abstract = """
        We trained ResNet-50 on 8 V100 GPUs for 90 epochs, taking approximately
        29 hours. The ImageNet dataset contains 14 million images (150GB).
        Training used a batch size of 256 with mixed precision.
        """
        paper.content = ""
        paper.full_text = ""
        return paper

    @pytest.fixture
    def mock_analyzer_nlp_result(self):
        """Mock ComputationalAnalyzer result for NLP paper."""
        return {
            "computational_richness": 0.92,
            "keyword_matches": {
                "infrastructure": {"score": 8, "keywords": ["GPU", "TPU", "training"]},
                "ml_terms": {
                    "score": 10,
                    "keywords": ["transformer", "BERT", "attention"],
                },
            },
            "resource_metrics": {
                "gpu_type": "TPU v3",
                "tpu_cores": 16,
                "training_time": "4 days",
                "model_parameters": "340M",
                "batch_size": 256,
                "sequence_length": 512,
                "dataset_size": "3.3B words",
            },
            "experimental_indicators": {
                "is_experimental_paper": True,
                "has_ablation_study": True,
            },
        }

    @pytest.fixture
    def mock_analyzer_cv_result(self):
        """Mock ComputationalAnalyzer result for CV paper."""
        return {
            "computational_richness": 0.88,
            "keyword_matches": {
                "infrastructure": {"score": 6, "keywords": ["GPU", "V100"]},
                "ml_terms": {"score": 7, "keywords": ["ResNet", "convolution"]},
            },
            "resource_metrics": {
                "gpu_type": "V100",
                "gpu_count": 8,
                "training_time": "29 hours",
                "dataset_size": "150GB",
                "batch_size": 256,
                "model_parameters": "25.6M",
            },
            "experimental_indicators": {
                "is_experimental_paper": True,
                "has_ablation_study": False,
            },
        }

    @patch("compute_forecast.extraction.template_engine.ComputationalAnalyzer")
    def test_nlp_extraction_workflow(
        self, mock_analyzer_class, sample_paper_nlp, mock_analyzer_nlp_result
    ):
        """Test complete extraction workflow for NLP paper."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_analyzer_nlp_result
        mock_analyzer.get_confidence_score.return_value = 0.92
        mock_analyzer_class.return_value = mock_analyzer

        # Create engine and extract
        engine = ExtractionTemplateEngine()
        result = engine.extract_to_template(sample_paper_nlp, "nlp_training_v1")

        # Check extraction
        assert result["template_id"] == "nlp_training_v1"
        assert result["completeness"] > 0.5  # Should have most required fields

        # Check extracted fields
        fields = result["extracted_fields"]
        assert ExtractionField.TRAINING_TIME_HOURS in fields
        assert fields[ExtractionField.TRAINING_TIME_HOURS] == 96.0  # 4 days = 96 hours

        assert ExtractionField.PARAMETERS_COUNT in fields
        assert (
            fields[ExtractionField.PARAMETERS_COUNT] == 340.0
        )  # Normalized to millions

        assert ExtractionField.BATCH_SIZE in fields
        assert fields[ExtractionField.BATCH_SIZE] == 256

        # Check validation passed
        if not result["validation_results"]["passed"]:
            print("Validation errors:", result["validation_results"]["errors"])
            print("Extracted fields:", fields)
        assert result["validation_results"]["passed"] is True

        # Check confidence scores
        assert all(0 <= score <= 1 for score in result["confidence_scores"].values())

    @patch("compute_forecast.extraction.template_engine.ComputationalAnalyzer")
    def test_cv_extraction_workflow(
        self, mock_analyzer_class, sample_paper_cv, mock_analyzer_cv_result
    ):
        """Test complete extraction workflow for CV paper."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_analyzer_cv_result
        mock_analyzer.get_confidence_score.return_value = 0.88
        mock_analyzer_class.return_value = mock_analyzer

        # Create engine and extract
        engine = ExtractionTemplateEngine()
        result = engine.extract_to_template(sample_paper_cv, "cv_training_v1")

        # Check extraction
        assert result["template_id"] == "cv_training_v1"

        # Check normalization worked
        fields = result["extracted_fields"]
        assert ExtractionField.GPU_TYPE in fields
        assert fields[ExtractionField.GPU_TYPE] == "V100"  # Normalized

        assert ExtractionField.TRAINING_TIME_HOURS in fields
        assert fields[ExtractionField.TRAINING_TIME_HOURS] == 29.0  # Already in hours

        assert ExtractionField.DATASET_SIZE_GB in fields
        assert fields[ExtractionField.DATASET_SIZE_GB] == 150.0

        # Check validation
        assert result["validation_results"]["passed"] is True

    @patch("compute_forecast.extraction.template_engine.ComputationalAnalyzer")
    def test_validation_failure(self, mock_analyzer_class):
        """Test extraction with validation failures."""
        # Mock unrealistic values
        mock_result = {
            "computational_richness": 0.5,
            "resource_metrics": {
                "gpu_type": "RTX 3090",
                "gpu_count": 50000,  # Unrealistic
                "training_time": "0.01 hours",  # Too short
                "model_parameters": "1e15",  # Too large
            },
            "experimental_indicators": {},
        }

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer.get_confidence_score.return_value = 0.5
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()
        paper = Mock(spec=Paper)

        result = engine.extract_to_template(paper, "generic_training_v1")

        # Should have validation errors
        validation = result["validation_results"]
        assert validation["passed"] is False
        assert len(validation["errors"]) > 0

    @patch("compute_forecast.extraction.template_engine.ComputationalAnalyzer")
    def test_template_selection(self, mock_analyzer_class):
        """Test selecting appropriate template based on paper content."""
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "computational_richness": 0.7,
            "keyword_matches": {},
            "resource_metrics": {},
            "experimental_indicators": {},
        }
        mock_analyzer.get_confidence_score.return_value = 0.7
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()
        paper = Mock(spec=Paper)

        # Should be able to extract with different templates
        templates_to_test = [
            "nlp_training_v1",
            "cv_training_v1",
            "rl_training_v1",
            "generic_training_v1",
            "inference_v1",
        ]

        for template_id in templates_to_test:
            result = engine.extract_to_template(paper, template_id)
            assert result["template_id"] == template_id
            assert "extracted_fields" in result
            assert "validation_results" in result

    def test_custom_template_registration(self):
        """Test registering and using custom templates."""
        # Create custom template
        custom_template = ExtractionTemplate(
            template_id="custom_test",
            template_name="Custom Test Template",
            version="1.0",
            required_fields=[ExtractionField.GPU_COUNT],
            optional_fields=[ExtractionField.BATCH_SIZE],
            validation_rules={ExtractionField.GPU_COUNT: {"min": 1, "max": 100}},
            normalization_rules={},
        )

        engine = ExtractionTemplateEngine()
        engine.register_template(custom_template)

        # Verify registration
        assert "custom_test" in engine.templates
        assert engine.templates["custom_test"] == custom_template

    @patch("compute_forecast.extraction.template_engine.ComputationalAnalyzer")
    def test_end_to_end_with_all_components(self, mock_analyzer_class):
        """Test complete end-to-end workflow with all components."""
        # Complex mock result with various field types
        mock_result = {
            "computational_richness": 0.95,
            "resource_metrics": {
                "gpu_type": "NVIDIA A100-SXM4",  # Needs normalization
                "gpu_count": 64,
                "training_time": "7 days",  # Needs conversion
                "model_parameters": "175B",  # Needs normalization
                "batch_size": 2048,
                "sequence_length": 2048,
                "dataset_size": "1.5TB",  # Needs conversion
                "gpu_memory": "80GB",  # Needs extraction
            },
            "experimental_indicators": {"is_experimental_paper": True},
        }

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_result
        mock_analyzer.get_confidence_score.return_value = 0.95
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()
        paper = Mock(spec=Paper)
        paper.title = "GPT-3: Language Models are Few-Shot Learners"

        result = engine.extract_to_template(paper, "nlp_training_v1")

        # Verify complete workflow
        fields = result["extracted_fields"]

        # Check normalization
        assert fields[ExtractionField.GPU_TYPE] == "A100"
        assert fields[ExtractionField.TRAINING_TIME_HOURS] == 168.0  # 7 days
        assert fields[ExtractionField.PARAMETERS_COUNT] == 175000.0  # 175B in millions
        assert fields[ExtractionField.DATASET_SIZE_GB] == 1536.0  # 1.5TB in GB

        # Check validation passed
        assert result["validation_results"]["passed"] is True

        # Check completeness is perfect (all required fields present)
        assert result["completeness"] == 1.0

        # Check confidence scores
        assert all(score == 0.95 for score in result["confidence_scores"].values())
