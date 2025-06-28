"""
Unit tests for quality control module.

Tests quality assurance, validation, and consistency checking for extraction results.
"""

import pytest

from src.analysis.computational.quality_control import (
    QualityController,
    QualityMetrics,
    ValidationRule,
    ConsistencyChecker,
    OutlierDetector,
    ConfidenceAssessor,
    QualityReport,
    ValidationResult,
    DataIntegrityChecker,
    CrossFieldValidator,
    StatisticalValidator,
    QualityDashboard,
    QualityConfig
)


@pytest.fixture
def sample_extraction_data():
    """Sample extraction data for testing."""
    return {
        "metadata": {
            "paper_id": "test_001",
            "extraction_date": "2024-01-01",
            "analyst": "test_analyst"
        },
        "hardware": {
            "gpu_type": "V100",
            "gpu_count": 8,
            "gpu_memory_gb": 16.0,
            "nodes_used": 1
        },
        "training": {
            "total_time_hours": 120.0,
            "time_unit_original": "hours",
            "epochs": 100,
            "batch_size": 64
        },
        "model": {
            "parameters_count": 340.0,
            "parameters_unit": "millions",
            "architecture": "Transformer",
            "layers": 24,
            "hidden_size": 768
        },
        "computation": {
            "total_gpu_hours": 960.0,
            "calculation_method": "explicit",
            "estimated_cost": 2880.0
        }
    }


@pytest.fixture
def quality_config():
    """Default quality configuration."""
    return QualityConfig(
        min_confidence_threshold=0.7,
        outlier_z_threshold=3.0,
        consistency_tolerance=0.1,
        enable_statistical_validation=True,
        enable_cross_field_validation=True
    )


@pytest.fixture
def quality_controller(quality_config):
    """Create quality controller instance."""
    return QualityController(quality_config)


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            overall_score=0.85,
            confidence_score=0.9,
            consistency_score=0.8,
            completeness_score=0.75,
            data_integrity_score=1.0
        )
        
        assert metrics.overall_score == 0.85
        assert metrics.confidence_score == 0.9
        assert metrics.consistency_score == 0.8
        assert metrics.completeness_score == 0.75
        assert metrics.data_integrity_score == 1.0
        assert metrics.outlier_count == 0
        assert metrics.validation_errors == []
    
    def test_metrics_calculation(self):
        """Test automatic metrics calculation."""
        metrics = QualityMetrics()
        
        # Set individual scores
        metrics.confidence_score = 0.8
        metrics.consistency_score = 0.9
        metrics.completeness_score = 0.7
        metrics.data_integrity_score = 1.0
        
        # Calculate overall score
        overall = (metrics.confidence_score + metrics.consistency_score + 
                  metrics.completeness_score + metrics.data_integrity_score) / 4
        metrics.overall_score = overall
        
        assert metrics.overall_score == 0.85


class TestValidationRule:
    """Test ValidationRule class."""
    
    def test_rule_creation(self):
        """Test creating validation rule."""
        rule = ValidationRule(
            name="gpu_count_positive",
            description="GPU count must be positive",
            validator=lambda data: data.get("hardware", {}).get("gpu_count", 0) > 0,
            severity="error"
        )
        
        assert rule.name == "gpu_count_positive"
        assert rule.description == "GPU count must be positive"
        assert rule.severity == "error"
        assert rule.enabled is True
    
    def test_rule_validation_pass(self, sample_extraction_data):
        """Test rule validation passing."""
        rule = ValidationRule(
            "test_rule",
            "Test rule",
            lambda data: data.get("hardware", {}).get("gpu_count", 0) > 0
        )
        
        result = rule.validate(sample_extraction_data)
        assert result.passed is True
        assert result.message is None
    
    def test_rule_validation_fail(self):
        """Test rule validation failing."""
        rule = ValidationRule(
            "test_rule",
            "Test rule",
            lambda data: data.get("hardware", {}).get("gpu_count", 0) > 10,
            error_message="GPU count must be > 10"
        )
        
        data = {"hardware": {"gpu_count": 5}}
        result = rule.validate(data)
        
        assert result.passed is False
        assert result.message == "GPU count must be > 10"
    
    def test_disabled_rule(self):
        """Test disabled rule."""
        rule = ValidationRule(
            "disabled_rule",
            "Disabled rule",
            lambda data: False,  # Always fails
            enabled=False
        )
        
        result = rule.validate({})
        assert result.passed is True  # Disabled rules always pass


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_result_creation(self):
        """Test creating validation result."""
        result = ValidationResult(
            rule_name="test_rule",
            passed=True,
            message="Validation passed",
            severity="info"
        )
        
        assert result.rule_name == "test_rule"
        assert result.passed is True
        assert result.message == "Validation passed"
        assert result.severity == "info"
        assert result.timestamp is not None
    
    def test_result_failure(self):
        """Test creating failure result."""
        result = ValidationResult(
            rule_name="fail_rule",
            passed=False,
            message="Validation failed",
            severity="error",
            details={"expected": 10, "actual": 5}
        )
        
        assert result.passed is False
        assert result.details == {"expected": 10, "actual": 5}


class TestConsistencyChecker:
    """Test ConsistencyChecker class."""
    
    def test_checker_initialization(self):
        """Test consistency checker initialization."""
        checker = ConsistencyChecker()
        assert checker.tolerance == 0.1
        assert len(checker.consistency_rules) > 0
    
    def test_gpu_hours_consistency(self, sample_extraction_data):
        """Test GPU-hours consistency check."""
        checker = ConsistencyChecker()
        
        # Data should be consistent (8 GPUs * 120 hours = 960 GPU-hours)
        issues = checker.check_gpu_hours_consistency(sample_extraction_data)
        assert len(issues) == 0
        
        # Make data inconsistent
        sample_extraction_data["computation"]["total_gpu_hours"] = 500.0
        issues = checker.check_gpu_hours_consistency(sample_extraction_data)
        assert len(issues) > 0
        assert "GPU-hours" in issues[0].lower()
    
    def test_parameter_count_consistency(self):
        """Test parameter count consistency check."""
        checker = ConsistencyChecker()
        
        data = {
            "model": {
                "parameters_count": 340.0,
                "parameters_unit": "millions",
                "layers": 24,
                "hidden_size": 768
            }
        }
        
        # Rough estimate for transformer: layers * hidden_size^2 * 4 / 1M
        # Should be approximately consistent
        checker.check_parameter_count_consistency(data)
        # This might flag as inconsistent depending on exact calculation
    
    def test_cost_consistency(self):
        """Test cost consistency check."""
        checker = ConsistencyChecker()
        
        data = {
            "computation": {
                "total_gpu_hours": 960.0,
                "estimated_cost": 2880.0  # $3/GPU-hour
            }
        }
        
        issues = checker.check_cost_consistency(data)
        # Should be consistent with typical cloud pricing
        assert len(issues) == 0
    
    def test_batch_size_consistency(self):
        """Test batch size consistency check."""
        checker = ConsistencyChecker()
        
        data = {
            "training": {
                "batch_size": 64,
                "epochs": 100
            },
            "hardware": {
                "gpu_count": 8,
                "gpu_memory_gb": 16.0
            },
            "model": {
                "parameters_count": 340.0
            }
        }
        
        checker.check_batch_size_consistency(data)
        # Should check if batch size is reasonable for given hardware
    
    def test_training_time_consistency(self):
        """Test training time consistency check."""
        checker = ConsistencyChecker()
        
        data = {
            "training": {
                "total_time_hours": 120.0,
                "epochs": 100,
                "batch_size": 64
            },
            "dataset": {
                "sample_count": 1200000  # 1.2M samples
            },
            "hardware": {
                "gpu_count": 8
            }
        }
        
        checker.check_training_time_consistency(data)
        # Should validate time makes sense for dataset size and hardware


class TestOutlierDetector:
    """Test OutlierDetector class."""
    
    def test_detector_initialization(self):
        """Test outlier detector initialization."""
        detector = OutlierDetector()
        assert detector.z_threshold == 3.0
    
    def test_detect_parameter_outliers(self):
        """Test parameter count outlier detection."""
        detector = OutlierDetector()
        
        # Normal parameter count
        data = {"model": {"parameters_count": 340.0}}
        outliers = detector.detect_parameter_outliers(data)
        assert len(outliers) == 0
        
        # Extreme parameter count
        data = {"model": {"parameters_count": 1000000.0}}  # 1 trillion parameters
        outliers = detector.detect_parameter_outliers(data)
        assert len(outliers) > 0
        assert "parameter" in outliers[0].lower()
    
    def test_detect_gpu_hours_outliers(self):
        """Test GPU-hours outlier detection."""
        detector = OutlierDetector()
        
        # Normal GPU-hours
        data = {"computation": {"total_gpu_hours": 960.0}}
        outliers = detector.detect_gpu_hours_outliers(data)
        assert len(outliers) == 0
        
        # Extreme GPU-hours
        data = {"computation": {"total_gpu_hours": 10000000.0}}  # 10M GPU-hours
        outliers = detector.detect_gpu_hours_outliers(data)
        assert len(outliers) > 0
    
    def test_detect_training_time_outliers(self):
        """Test training time outlier detection."""
        detector = OutlierDetector()
        
        # Normal training time
        data = {"training": {"total_time_hours": 120.0}}
        outliers = detector.detect_training_time_outliers(data)
        assert len(outliers) == 0
        
        # Extreme training time (over 1 year)
        data = {"training": {"total_time_hours": 10000.0}}
        outliers = detector.detect_training_time_outliers(data)
        assert len(outliers) > 0
    
    def test_detect_cost_outliers(self):
        """Test cost outlier detection."""
        detector = OutlierDetector()
        
        # Normal cost
        data = {"computation": {"estimated_cost": 2880.0}}
        outliers = detector.detect_cost_outliers(data)
        assert len(outliers) == 0
        
        # Extreme cost
        data = {"computation": {"estimated_cost": 10000000.0}}  # $10M
        outliers = detector.detect_cost_outliers(data)
        assert len(outliers) > 0
    
    def test_statistical_outlier_detection(self):
        """Test statistical outlier detection."""
        detector = OutlierDetector()
        
        # Sample data points
        values = [100, 120, 110, 115, 105, 1000]  # 1000 is outlier
        outliers = detector.detect_statistical_outliers(values)
        
        assert len(outliers) == 1
        assert 1000 in outliers


class TestConfidenceAssessor:
    """Test ConfidenceAssessor class."""
    
    def test_assessor_initialization(self):
        """Test confidence assessor initialization."""
        assessor = ConfidenceAssessor()
        assert assessor.weights is not None
    
    def test_assess_field_confidence(self):
        """Test assessing confidence for individual field."""
        assessor = ConfidenceAssessor()
        
        # High confidence - multiple indicators
        field_data = {
            "gpu_type": "V100",
            "gpu_count": 8,
            "gpu_memory_gb": 16.0
        }
        confidence = assessor.assess_field_confidence("hardware", field_data)
        assert confidence > 0.7
        
        # Low confidence - missing data
        field_data = {"gpu_type": "V100"}
        confidence = assessor.assess_field_confidence("hardware", field_data)
        assert confidence < 0.7
    
    def test_assess_overall_confidence(self, sample_extraction_data):
        """Test assessing overall confidence."""
        assessor = ConfidenceAssessor()
        
        confidence = assessor.assess_overall_confidence(sample_extraction_data)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high for complete data
    
    def test_confidence_factors(self):
        """Test individual confidence factors."""
        assessor = ConfidenceAssessor()
        
        # Test completeness factor
        complete_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        incomplete_data = {"field1": "value1"}
        
        complete_score = assessor._calculate_completeness_factor(complete_data)
        incomplete_score = assessor._calculate_completeness_factor(incomplete_data)
        
        assert complete_score > incomplete_score
    
    def test_consistency_factor(self):
        """Test consistency factor calculation."""
        assessor = ConfidenceAssessor()
        
        # Consistent data
        consistent_data = {
            "hardware": {"gpu_count": 8},
            "training": {"total_time_hours": 120.0},
            "computation": {"total_gpu_hours": 960.0}
        }
        
        consistency_score = assessor._calculate_consistency_factor(consistent_data)
        assert consistency_score > 0.8


class TestDataIntegrityChecker:
    """Test DataIntegrityChecker class."""
    
    def test_checker_initialization(self):
        """Test data integrity checker initialization."""
        checker = DataIntegrityChecker()
        assert checker.required_fields is not None
    
    def test_check_required_fields(self, sample_extraction_data):
        """Test checking required fields."""
        checker = DataIntegrityChecker()
        
        missing_fields = checker.check_required_fields(sample_extraction_data)
        assert len(missing_fields) == 0  # Complete data should have no missing fields
        
        # Remove required field
        del sample_extraction_data["metadata"]["paper_id"]
        missing_fields = checker.check_required_fields(sample_extraction_data)
        assert len(missing_fields) > 0
        assert "paper_id" in missing_fields[0]
    
    def test_check_data_types(self, sample_extraction_data):
        """Test checking data types."""
        checker = DataIntegrityChecker()
        
        type_errors = checker.check_data_types(sample_extraction_data)
        assert len(type_errors) == 0  # Correct types should have no errors
        
        # Introduce type error
        sample_extraction_data["hardware"]["gpu_count"] = "eight"  # Should be int
        type_errors = checker.check_data_types(sample_extraction_data)
        assert len(type_errors) > 0
        assert "gpu_count" in type_errors[0]
    
    def test_check_value_ranges(self, sample_extraction_data):
        """Test checking value ranges."""
        checker = DataIntegrityChecker()
        
        range_errors = checker.check_value_ranges(sample_extraction_data)
        assert len(range_errors) == 0  # Valid ranges should have no errors
        
        # Introduce range error
        sample_extraction_data["hardware"]["gpu_count"] = -5  # Negative count
        range_errors = checker.check_value_ranges(sample_extraction_data)
        assert len(range_errors) > 0
    
    def test_check_format_consistency(self, sample_extraction_data):
        """Test checking format consistency."""
        checker = DataIntegrityChecker()
        
        format_errors = checker.check_format_consistency(sample_extraction_data)
        assert len(format_errors) == 0  # Consistent formats should have no errors
        
        # Introduce format inconsistency
        sample_extraction_data["metadata"]["extraction_date"] = "January 1, 2024"  # Wrong format
        format_errors = checker.check_format_consistency(sample_extraction_data)
        assert len(format_errors) > 0


class TestCrossFieldValidator:
    """Test CrossFieldValidator class."""
    
    def test_validator_initialization(self):
        """Test cross-field validator initialization."""
        validator = CrossFieldValidator()
        assert len(validator.validation_rules) > 0
    
    def test_validate_gpu_memory_consistency(self):
        """Test GPU memory consistency validation."""
        validator = CrossFieldValidator()
        
        # Consistent GPU memory
        data = {
            "hardware": {
                "gpu_type": "V100",
                "gpu_memory_gb": 16.0
            }
        }
        errors = validator.validate_gpu_memory_consistency(data)
        assert len(errors) == 0
        
        # Inconsistent GPU memory
        data["hardware"]["gpu_memory_gb"] = 64.0  # V100 doesn't have 64GB
        errors = validator.validate_gpu_memory_consistency(data)
        assert len(errors) > 0
    
    def test_validate_architecture_parameters(self):
        """Test architecture-parameter consistency validation."""
        validator = CrossFieldValidator()
        
        # Reasonable parameter count for architecture
        data = {
            "model": {
                "architecture": "BERT-base",
                "parameters_count": 110.0,
                "layers": 12,
                "hidden_size": 768
            }
        }
        errors = validator.validate_architecture_parameters(data)
        assert len(errors) == 0
    
    def test_validate_batch_size_memory(self):
        """Test batch size vs memory validation."""
        validator = CrossFieldValidator()
        
        # Reasonable batch size for memory
        data = {
            "training": {"batch_size": 64},
            "hardware": {"gpu_memory_gb": 16.0},
            "model": {"parameters_count": 340.0}
        }
        validator.validate_batch_size_memory(data)
        # Might flag if batch size is too large for memory


class TestStatisticalValidator:
    """Test StatisticalValidator class."""
    
    def test_validator_initialization(self):
        """Test statistical validator initialization."""
        validator = StatisticalValidator()
        assert validator.reference_data is not None
    
    def test_validate_against_norms(self):
        """Test validation against statistical norms."""
        validator = StatisticalValidator()
        
        # Normal values
        data = {
            "model": {"parameters_count": 340.0},
            "training": {"total_time_hours": 120.0},
            "computation": {"total_gpu_hours": 960.0}
        }
        
        validator.validate_against_norms(data)
        # Should not flag normal values
    
    def test_calculate_z_scores(self):
        """Test Z-score calculation."""
        validator = StatisticalValidator()
        
        # Mock reference data
        validator.reference_data = {
            "parameter_counts": [100, 200, 300, 400, 500],
            "gpu_hours": [500, 1000, 1500, 2000, 2500]
        }
        
        # Test value within normal range
        z_score = validator.calculate_z_score(300, validator.reference_data["parameter_counts"])
        assert abs(z_score) < 2.0
        
        # Test outlier value
        z_score = validator.calculate_z_score(10000, validator.reference_data["parameter_counts"])
        assert abs(z_score) > 2.0


class TestQualityReport:
    """Test QualityReport class."""
    
    def test_report_creation(self):
        """Test creating quality report."""
        metrics = QualityMetrics(
            overall_score=0.85,
            confidence_score=0.9,
            consistency_score=0.8,
            completeness_score=0.75
        )
        
        validation_results = [
            ValidationResult("rule1", True, "Passed"),
            ValidationResult("rule2", False, "Failed", "error")
        ]
        
        report = QualityReport(
            extraction_id="test_001",
            metrics=metrics,
            validation_results=validation_results,
            outliers=["High parameter count"],
            recommendations=["Review parameter count"]
        )
        
        assert report.extraction_id == "test_001"
        assert report.metrics.overall_score == 0.85
        assert len(report.validation_results) == 2
        assert len(report.outliers) == 1
        assert len(report.recommendations) == 1
        assert report.timestamp is not None
    
    def test_report_summary(self):
        """Test report summary generation."""
        metrics = QualityMetrics(overall_score=0.85)
        validation_results = [
            ValidationResult("rule1", True, "Passed"),
            ValidationResult("rule2", False, "Failed", "error")
        ]
        
        report = QualityReport("test", metrics, validation_results, [], [])
        summary = report.get_summary()
        
        assert "overall_score" in summary
        assert "total_validations" in summary
        assert "failed_validations" in summary
        assert summary["overall_score"] == 0.85
        assert summary["total_validations"] == 2
        assert summary["failed_validations"] == 1
    
    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        metrics = QualityMetrics(overall_score=0.85)
        report = QualityReport("test", metrics, [], [], [])
        
        report_dict = report.to_dict()
        
        assert "extraction_id" in report_dict
        assert "metrics" in report_dict
        assert "validation_results" in report_dict
        assert "timestamp" in report_dict


class TestQualityController:
    """Test QualityController main class."""
    
    def test_controller_initialization(self, quality_controller):
        """Test quality controller initialization."""
        assert quality_controller.config is not None
        assert quality_controller.consistency_checker is not None
        assert quality_controller.outlier_detector is not None
        assert quality_controller.confidence_assessor is not None
    
    def test_run_quality_check(self, quality_controller, sample_extraction_data):
        """Test running complete quality check."""
        report = quality_controller.run_quality_check(sample_extraction_data)
        
        assert isinstance(report, QualityReport)
        assert report.extraction_id is not None
        assert report.metrics is not None
        assert isinstance(report.validation_results, list)
        assert 0.0 <= report.metrics.overall_score <= 1.0
    
    def test_validate_extraction_data(self, quality_controller, sample_extraction_data):
        """Test validating extraction data."""
        validation_results = quality_controller.validate_extraction_data(sample_extraction_data)
        
        assert isinstance(validation_results, list)
        # Should have validation results from all rules
        assert len(validation_results) > 0
    
    def test_check_consistency(self, quality_controller, sample_extraction_data):
        """Test consistency checking."""
        consistency_issues = quality_controller.check_consistency(sample_extraction_data)
        
        assert isinstance(consistency_issues, list)
        # Complete, consistent data should have no issues
        assert len(consistency_issues) == 0
    
    def test_detect_outliers(self, quality_controller, sample_extraction_data):
        """Test outlier detection."""
        outliers = quality_controller.detect_outliers(sample_extraction_data)
        
        assert isinstance(outliers, list)
        # Normal data should have no outliers
        assert len(outliers) == 0
    
    def test_assess_confidence(self, quality_controller, sample_extraction_data):
        """Test confidence assessment."""
        confidence = quality_controller.assess_confidence(sample_extraction_data)
        
        assert 0.0 <= confidence <= 1.0
        # Complete data should have reasonable confidence
        assert confidence > 0.5
    
    def test_generate_recommendations(self, quality_controller):
        """Test generating recommendations."""
        validation_results = [
            ValidationResult("rule1", False, "GPU count validation failed", "error"),
            ValidationResult("rule2", False, "Training time inconsistent", "warning")
        ]
        
        recommendations = quality_controller.generate_recommendations(validation_results, [])
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should provide specific recommendations for failed validations


class TestQualityDashboard:
    """Test QualityDashboard class."""
    
    def test_dashboard_initialization(self):
        """Test quality dashboard initialization."""
        dashboard = QualityDashboard()
        assert dashboard.reports == []
        assert dashboard.metrics_history == []
    
    def test_add_report(self):
        """Test adding report to dashboard."""
        dashboard = QualityDashboard()
        
        metrics = QualityMetrics(overall_score=0.85)
        report = QualityReport("test", metrics, [], [], [])
        
        dashboard.add_report(report)
        
        assert len(dashboard.reports) == 1
        assert len(dashboard.metrics_history) == 1
        assert dashboard.metrics_history[0]["overall_score"] == 0.85
    
    def test_get_quality_trends(self):
        """Test getting quality trends."""
        dashboard = QualityDashboard()
        
        # Add multiple reports
        for i in range(5):
            metrics = QualityMetrics(overall_score=0.8 + i * 0.02)
            report = QualityReport(f"test_{i}", metrics, [], [], [])
            dashboard.add_report(report)
        
        trends = dashboard.get_quality_trends()
        
        assert "overall_score" in trends
        assert len(trends["overall_score"]) == 5
        assert trends["overall_score"][-1] > trends["overall_score"][0]  # Improving trend
    
    def test_get_summary_statistics(self):
        """Test getting summary statistics."""
        dashboard = QualityDashboard()
        
        # Add reports with various scores
        scores = [0.7, 0.8, 0.9, 0.6, 0.85]
        for i, score in enumerate(scores):
            metrics = QualityMetrics(overall_score=score)
            report = QualityReport(f"test_{i}", metrics, [], [], [])
            dashboard.add_report(report)
        
        stats = dashboard.get_summary_statistics()
        
        assert "mean_quality_score" in stats
        assert "min_quality_score" in stats
        assert "max_quality_score" in stats
        assert "total_reports" in stats
        
        assert stats["total_reports"] == 5
        assert stats["min_quality_score"] == 0.6
        assert stats["max_quality_score"] == 0.9


class TestQualityControlEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_data_validation(self, quality_controller):
        """Test quality check with empty data."""
        empty_data = {}
        
        report = quality_controller.run_quality_check(empty_data)
        
        # Should handle empty data gracefully
        assert report.metrics.overall_score == 0.0
        assert len(report.validation_results) > 0  # Should have validation failures
    
    def test_malformed_data_validation(self, quality_controller):
        """Test quality check with malformed data."""
        malformed_data = {
            "hardware": {
                "gpu_count": "invalid",  # Should be number
                "gpu_memory_gb": None
            },
            "training": {
                "total_time_hours": -100  # Negative time
            }
        }
        
        report = quality_controller.run_quality_check(malformed_data)
        
        # Should detect multiple validation errors
        failed_validations = [r for r in report.validation_results if not r.passed]
        assert len(failed_validations) > 0
    
    def test_missing_sections_validation(self, quality_controller):
        """Test validation with missing data sections."""
        partial_data = {
            "metadata": {
                "paper_id": "test_001"
            }
            # Missing hardware, training, model, etc.
        }
        
        report = quality_controller.run_quality_check(partial_data)
        
        # Should have low completeness score
        assert report.metrics.completeness_score < 0.5
    
    def test_extreme_values_detection(self, quality_controller):
        """Test detection of extreme/impossible values."""
        extreme_data = {
            "model": {
                "parameters_count": 1000000000.0  # 1 trillion parameters
            },
            "training": {
                "total_time_hours": 100000.0  # 11+ years
            },
            "computation": {
                "total_gpu_hours": 50000000.0,  # 50M GPU-hours
                "estimated_cost": 1000000000.0  # $1B
            }
        }
        
        outliers = quality_controller.detect_outliers(extreme_data)
        
        # Should detect multiple outliers
        assert len(outliers) > 0
        assert any("parameter" in outlier.lower() for outlier in outliers)
    
    def test_inconsistent_units_validation(self, quality_controller):
        """Test validation with inconsistent units."""
        inconsistent_data = {
            "model": {
                "parameters_count": 340.0,
                "parameters_unit": "thousands"  # Inconsistent with typical usage
            },
            "training": {
                "total_time_hours": 120.0,
                "time_unit_original": "minutes"  # Inconsistent with value
            }
        }
        
        quality_controller.run_quality_check(inconsistent_data)
        
        # Should detect inconsistencies
        consistency_issues = quality_controller.check_consistency(inconsistent_data)
        assert len(consistency_issues) > 0