"""Tests for template coverage reporting."""

import pytest

from compute_forecast.extraction import (
    CoverageReporter,
    ExtractionField,
    ExtractionTemplate,
    DefaultTemplates
)


class TestCoverageReporter:
    """Test coverage reporting functionality."""

    @pytest.fixture
    def sample_extraction_results(self):
        """Create sample extraction results for testing."""
        return [
            {
                "template_id": "nlp_training_v1",
                "extracted_fields": {
                    ExtractionField.GPU_TYPE: "A100",
                    ExtractionField.GPU_COUNT: 8,
                    ExtractionField.TRAINING_TIME_HOURS: 168.0,
                    ExtractionField.PARAMETERS_COUNT: 1300.0,
                    ExtractionField.DATASET_SIZE_GB: 500.0,
                    ExtractionField.BATCH_SIZE: 2048
                },
                "validation_results": {"passed": True, "errors": [], "warnings": []},
                "confidence_scores": {
                    ExtractionField.GPU_TYPE: 0.95,
                    ExtractionField.GPU_COUNT: 0.90,
                    ExtractionField.TRAINING_TIME_HOURS: 0.92,
                    ExtractionField.PARAMETERS_COUNT: 0.98,
                    ExtractionField.DATASET_SIZE_GB: 0.85,
                    ExtractionField.BATCH_SIZE: 0.88
                },
                "completeness": 1.0
            },
            {
                "template_id": "nlp_training_v1",
                "extracted_fields": {
                    ExtractionField.GPU_TYPE: "V100",
                    ExtractionField.TRAINING_TIME_HOURS: 240.0,
                    ExtractionField.PARAMETERS_COUNT: 340.0
                    # Missing DATASET_SIZE_GB (required field)
                },
                "validation_results": {"passed": True, "errors": [], "warnings": []},
                "confidence_scores": {
                    ExtractionField.GPU_TYPE: 0.88,
                    ExtractionField.TRAINING_TIME_HOURS: 0.85,
                    ExtractionField.PARAMETERS_COUNT: 0.90
                },
                "completeness": 0.75
            },
            {
                "template_id": "nlp_training_v1",
                "extracted_fields": {
                    ExtractionField.GPU_TYPE: "RTX 3090",
                    ExtractionField.GPU_COUNT: 50000,  # Will fail validation
                    ExtractionField.TRAINING_TIME_HOURS: 10.0,
                    ExtractionField.PARAMETERS_COUNT: 50.0,
                    ExtractionField.DATASET_SIZE_GB: 10.0
                },
                "validation_results": {
                    "passed": False,
                    "errors": [
                        {
                            "field": "gpu_count",
                            "message": "Value 50000 outside range [1, 10000]",
                            "severity": "error"
                        }
                    ],
                    "warnings": []
                },
                "confidence_scores": {
                    ExtractionField.GPU_TYPE: 0.70,
                    ExtractionField.GPU_COUNT: 0.65,
                    ExtractionField.TRAINING_TIME_HOURS: 0.72,
                    ExtractionField.PARAMETERS_COUNT: 0.68,
                    ExtractionField.DATASET_SIZE_GB: 0.71
                },
                "completeness": 1.0
            }
        ]

    def test_reporter_initialization(self):
        """Test that reporter initializes properly."""
        reporter = CoverageReporter()
        assert hasattr(reporter, 'template_reports')
        assert hasattr(reporter, 'extraction_results')
        assert len(reporter.template_reports) == 0
        assert len(reporter.extraction_results) == 0

    def test_add_extraction_result(self, sample_extraction_results):
        """Test adding extraction results to reporter."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        assert len(reporter.extraction_results) == 3
        assert "nlp_training_v1" in reporter.template_reports
        
        report = reporter.template_reports["nlp_training_v1"]
        assert report.total_papers == 3
        assert report.successful_extractions == 2
        assert report.validation_failures == 1

    def test_field_coverage_stats(self, sample_extraction_results):
        """Test field coverage statistics calculation."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report = reporter.template_reports["nlp_training_v1"]
        
        # GPU_TYPE appears in all 3 papers
        gpu_type_stats = report.field_coverage[ExtractionField.GPU_TYPE]
        assert gpu_type_stats.papers_with_field == 3
        assert gpu_type_stats.coverage_percentage == 100.0
        assert len(gpu_type_stats.unique_values) == 3  # A100, V100, RTX 3090
        
        # DATASET_SIZE_GB missing in one paper
        dataset_stats = report.field_coverage[ExtractionField.DATASET_SIZE_GB]
        assert dataset_stats.papers_with_field == 2
        assert dataset_stats.coverage_percentage == pytest.approx(66.67, rel=0.1)
        
        # GPU_COUNT has one validation failure
        gpu_count_stats = report.field_coverage[ExtractionField.GPU_COUNT]
        assert gpu_count_stats.validation_failures == 1

    def test_confidence_score_tracking(self, sample_extraction_results):
        """Test confidence score tracking and averaging."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report = reporter.template_reports["nlp_training_v1"]
        
        # Check average confidence for GPU_TYPE
        gpu_type_stats = report.field_coverage[ExtractionField.GPU_TYPE]
        expected_avg = (0.95 + 0.88 + 0.70) / 3
        assert gpu_type_stats.average_confidence == pytest.approx(expected_avg, rel=0.01)

    def test_completeness_tracking(self, sample_extraction_results):
        """Test completeness score tracking."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report = reporter.template_reports["nlp_training_v1"]
        
        # Average completeness should be (1.0 + 0.75 + 1.0) / 3
        assert report.average_completeness == pytest.approx(0.917, rel=0.01)
        assert len(report.completeness_scores) == 3

    def test_common_validation_issues(self, sample_extraction_results):
        """Test tracking of common validation issues."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report = reporter.template_reports["nlp_training_v1"]
        assert len(report.common_validation_issues) == 1
        assert "Value 50000 outside range" in report.common_validation_issues[0]

    def test_get_low_coverage_fields(self, sample_extraction_results):
        """Test identification of low coverage fields."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report = reporter.template_reports["nlp_training_v1"]
        
        # SEQUENCE_LENGTH is optional and not present in any result
        low_coverage = report.get_low_coverage_fields(threshold=50.0)
        assert ExtractionField.SEQUENCE_LENGTH in low_coverage
        
        # GPU_TYPE should not be in low coverage (100% coverage)
        assert ExtractionField.GPU_TYPE not in low_coverage

    def test_generate_summary_report(self, sample_extraction_results):
        """Test summary report generation."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        summary = reporter.generate_summary_report()
        
        assert summary["total_extractions"] == 3
        assert summary["templates_used"] == 1
        assert "nlp_training_v1" in summary["template_summaries"]
        
        template_summary = summary["template_summaries"]["nlp_training_v1"]
        assert template_summary["total_papers"] == 3
        assert template_summary["success_rate"] == "66.7%"
        assert template_summary["validation_failures"] == 1

    def test_field_insights(self, sample_extraction_results):
        """Test field insights across templates."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        insights = reporter.get_field_insights(ExtractionField.GPU_TYPE)
        
        assert insights["field"] == "gpu_type"
        assert insights["overall_coverage"] == "100.0%"
        assert len(insights["common_values"]) == 3
        
        # Check value frequency
        values = {v["value"]: v["count"] for v in insights["common_values"]}
        assert values["A100"] == 1
        assert values["V100"] == 1
        assert values["RTX 3090"] == 1

    def test_export_detailed_report(self, sample_extraction_results):
        """Test detailed report export."""
        reporter = CoverageReporter()
        template = DefaultTemplates.nlp_training_template()
        
        for result in sample_extraction_results:
            reporter.add_extraction_result(result, template)
        
        report_text = reporter.export_detailed_report("nlp_training_v1")
        
        # Check report contains key information
        assert "Template Coverage Report: NLP Model Training Requirements" in report_text
        assert "Total Papers Analyzed: 3" in report_text
        assert "Success Rate: 66.7%" in report_text
        assert "Field Coverage Statistics" in report_text
        assert "gpu_type" in report_text
        assert "100.0%" in report_text  # GPU type coverage
        
        # Check validation issues section
        assert "Common Validation Issues" in report_text
        assert "Value 50000 outside range" in report_text

    def test_multiple_templates(self):
        """Test reporting with multiple templates."""
        reporter = CoverageReporter()
        
        # Add results from different templates
        nlp_template = DefaultTemplates.nlp_training_template()
        cv_template = DefaultTemplates.cv_training_template()
        
        nlp_result = {
            "template_id": "nlp_training_v1",
            "extracted_fields": {
                ExtractionField.GPU_TYPE: "A100",
                ExtractionField.TRAINING_TIME_HOURS: 168.0,
                ExtractionField.PARAMETERS_COUNT: 1300.0,
                ExtractionField.DATASET_SIZE_GB: 500.0
            },
            "validation_results": {"passed": True, "errors": [], "warnings": []},
            "confidence_scores": {},
            "completeness": 1.0
        }
        
        cv_result = {
            "template_id": "cv_training_v1",
            "extracted_fields": {
                ExtractionField.GPU_TYPE: "V100",
                ExtractionField.TRAINING_TIME_HOURS: 48.0,
                ExtractionField.DATASET_SIZE_GB: 150.0
            },
            "validation_results": {"passed": True, "errors": [], "warnings": []},
            "confidence_scores": {},
            "completeness": 1.0
        }
        
        reporter.add_extraction_result(nlp_result, nlp_template)
        reporter.add_extraction_result(cv_result, cv_template)
        
        assert len(reporter.template_reports) == 2
        assert "nlp_training_v1" in reporter.template_reports
        assert "cv_training_v1" in reporter.template_reports
        
        # Check field insights across templates
        insights = reporter.get_field_insights(ExtractionField.GPU_TYPE)
        assert len(insights["usage_by_template"]) == 2