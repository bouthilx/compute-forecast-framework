"""Tests for the extraction template engine functionality."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.content_extraction.templates.template_engine import (
    ExtractionTemplateEngine,
    ExtractionTemplate,
    ExtractionField,
)
from compute_forecast.pipeline.metadata_collection.models import Paper


class TestExtractionTemplateEngine:
    """Test ExtractionTemplateEngine functionality."""

    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing."""
        return ExtractionTemplate(
            template_id="test_template",
            template_name="Test Template",
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
            validation_rules={
                ExtractionField.TRAINING_TIME_HOURS: {"min": 0.1, "max": 10000},
                ExtractionField.PARAMETERS_COUNT: {"min": 1e6, "max": 1e12},
            },
            normalization_rules={
                ExtractionField.TRAINING_TIME_HOURS: "convert_to_hours",
                ExtractionField.PARAMETERS_COUNT: "convert_to_millions",
            },
        )

    @pytest.fixture
    def mock_analyzer_result(self):
        """Mock result from ComputationalAnalyzer."""
        return {
            "computational_richness": 0.85,
            "keyword_matches": {
                "infrastructure": {"score": 5, "keywords": ["GPU", "training"]},
                "ml_terms": {"score": 8, "keywords": ["transformer", "attention"]},
            },
            "resource_metrics": {
                "gpu_type": "A100",
                "gpu_count": 8,
                "training_time": 168.0,  # hours
                "model_parameters": 340000000,  # 340M
                "batch_size": 2048,
                "sequence_length": 512,
            },
            "experimental_indicators": {
                "is_experimental_paper": True,
                "has_ablation_study": True,
            },
        }

    def test_engine_initialization(self):
        """Test that engine initializes properly."""
        engine = ExtractionTemplateEngine()
        assert hasattr(engine, "analyzer")
        assert hasattr(engine, "templates")
        assert isinstance(engine.templates, dict)

    def test_register_template(self, sample_template):
        """Test registering a new template."""
        engine = ExtractionTemplateEngine()
        engine.register_template(sample_template)

        assert sample_template.template_id in engine.templates
        assert engine.templates[sample_template.template_id] == sample_template

    @patch("compute_forecast.pipeline.content_extraction.templates.template_engine.ComputationalAnalyzer")
    def test_extract_to_template(
        self, mock_analyzer_class, sample_template, mock_analyzer_result
    ):
        """Test extracting paper data to template format."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_analyzer_result
        mock_analyzer.get_confidence_score.return_value = 0.9
        mock_analyzer_class.return_value = mock_analyzer

        # Create engine and register template
        engine = ExtractionTemplateEngine()
        engine.register_template(sample_template)

        # Create mock paper
        paper = Mock(spec=Paper)
        paper.title = "Test Paper"
        paper.abstract = "This is a test abstract"

        # Extract to template
        result = engine.extract_to_template(paper, sample_template.template_id)

        # Verify structure
        assert result["template_id"] == sample_template.template_id
        assert "extracted_fields" in result
        assert "validation_results" in result
        assert "confidence_scores" in result
        assert "completeness" in result

        # Verify extracted fields
        extracted = result["extracted_fields"]
        assert ExtractionField.GPU_TYPE in extracted
        assert extracted[ExtractionField.GPU_TYPE] == "A100"
        assert ExtractionField.TRAINING_TIME_HOURS in extracted
        assert extracted[ExtractionField.TRAINING_TIME_HOURS] == 168.0
        assert ExtractionField.PARAMETERS_COUNT in extracted
        # Parameters are normalized to millions
        assert extracted[ExtractionField.PARAMETERS_COUNT] == 340.0

        # Verify completeness (all required fields present)
        assert result["completeness"] == 1.0

    def test_extract_with_missing_template(self):
        """Test extraction with non-existent template."""
        engine = ExtractionTemplateEngine()
        paper = Mock(spec=Paper)

        with pytest.raises(ValueError, match="Template 'non_existent' not found"):
            engine.extract_to_template(paper, "non_existent")

    @patch("compute_forecast.pipeline.content_extraction.templates.template_engine.ComputationalAnalyzer")
    def test_map_to_template(
        self, mock_analyzer_class, sample_template, mock_analyzer_result
    ):
        """Test mapping analyzer output to template fields."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()

        # Map analyzer result to template
        mapped = engine.map_to_template(mock_analyzer_result, sample_template)

        # Check that only template fields are included
        assert ExtractionField.GPU_TYPE in mapped
        assert ExtractionField.TRAINING_TIME_HOURS in mapped
        assert ExtractionField.PARAMETERS_COUNT in mapped
        assert ExtractionField.BATCH_SIZE in mapped
        assert ExtractionField.SEQUENCE_LENGTH in mapped

        # GPU_COUNT is not in template fields, so shouldn't be included
        assert ExtractionField.GPU_COUNT not in mapped

    @patch("compute_forecast.pipeline.content_extraction.templates.template_engine.ComputationalAnalyzer")
    def test_partial_extraction(self, mock_analyzer_class, sample_template):
        """Test extraction when some required fields are missing."""
        # Mock analyzer with missing fields
        partial_result = {
            "computational_richness": 0.6,
            "resource_metrics": {
                "gpu_type": "V100",
                "model_parameters": 125000000,
                # missing training_time
            },
            "experimental_indicators": {"is_experimental_paper": False},
        }

        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = partial_result
        mock_analyzer.get_confidence_score.return_value = 0.7
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()
        engine.register_template(sample_template)

        paper = Mock(spec=Paper)
        result = engine.extract_to_template(paper, sample_template.template_id)

        # Check completeness is less than 1.0 (2 out of 3 required fields)
        assert result["completeness"] == 2 / 3

        # Check that available fields are extracted
        extracted = result["extracted_fields"]
        assert ExtractionField.GPU_TYPE in extracted
        assert ExtractionField.PARAMETERS_COUNT in extracted
        assert ExtractionField.TRAINING_TIME_HOURS not in extracted

    @patch("compute_forecast.pipeline.content_extraction.templates.template_engine.ComputationalAnalyzer")
    def test_confidence_scores(
        self, mock_analyzer_class, sample_template, mock_analyzer_result
    ):
        """Test confidence score calculation for fields."""
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_analyzer_result
        mock_analyzer.get_confidence_score.return_value = 0.85
        mock_analyzer_class.return_value = mock_analyzer

        engine = ExtractionTemplateEngine()
        engine.register_template(sample_template)

        paper = Mock(spec=Paper)
        result = engine.extract_to_template(paper, sample_template.template_id)

        # Check confidence scores
        confidence_scores = result["confidence_scores"]
        for field in result["extracted_fields"]:
            assert field in confidence_scores
            assert 0 <= confidence_scores[field] <= 1.0
            assert confidence_scores[field] == 0.85  # Base confidence
