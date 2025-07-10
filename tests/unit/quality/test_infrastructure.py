"""Test basic quality infrastructure setup."""

from pathlib import Path

from compute_forecast.quality import (
    QualityRunner,
    StageQualityChecker,
    register_stage_checker,
    QualityCheckResult,
    QualityCheckType,
    QualityConfig,
    QualityIssue,
    QualityIssueLevel,
    get_registry,
)


class DummyChecker(StageQualityChecker):
    """Dummy checker for testing infrastructure."""
    
    def get_stage_name(self):
        return "dummy"
    
    def load_data(self, data_path):
        return {"test": "data", "path": str(data_path)}
    
    def _register_checks(self):
        return {
            "dummy_check": self._dummy_check,
            "another_check": self._another_check,
        }
    
    def _dummy_check(self, data, config):
        return QualityCheckResult(
            check_name="dummy_check",
            check_type=QualityCheckType.COMPLETENESS,
            passed=True,
            score=1.0,
            issues=[]
        )
    
    def _another_check(self, data, config):
        return QualityCheckResult(
            check_name="another_check",
            check_type=QualityCheckType.ACCURACY,
            passed=False,
            score=0.8,
            issues=[
                QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.WARNING,
                    field="test_field",
                    message="Test warning",
                    suggested_action="Fix the test"
                )
            ]
        )


class TestQualityInfrastructure:
    """Test the basic quality infrastructure."""
    
    def test_stage_registration(self):
        """Test that we can register a stage checker."""
        # Register our dummy checker
        register_stage_checker("dummy", DummyChecker)
        
        # Verify it's registered
        registry = get_registry()
        assert "dummy" in registry.list_stages()
        
        # Get the checker
        checker = registry.get_checker("dummy")
        assert checker is not None
        assert isinstance(checker, DummyChecker)
    
    def test_runner_basic_functionality(self):
        """Test the quality runner can run checks."""
        # Register dummy checker
        register_stage_checker("dummy", DummyChecker)
        
        # Create runner
        runner = QualityRunner()
        
        # Run checks
        config = QualityConfig(
            stage="dummy",
            thresholds={},
            skip_checks=[],
            output_format="text",
            verbose=False
        )
        
        report = runner.run_checks("dummy", Path("test.json"), config)
        
        # Verify report
        assert report.stage == "dummy"
        assert report.data_path == Path("test.json")
        assert len(report.check_results) == 2
        assert report.overall_score == 0.9  # (1.0 + 0.8) / 2
        
        # Check individual results
        assert report.check_results[0].check_name == "dummy_check"
        assert report.check_results[0].passed is True
        assert report.check_results[1].check_name == "another_check"
        assert report.check_results[1].passed is False
        
        # Check issues
        assert len(report.critical_issues) == 0
        assert len(report.warnings) == 1
        assert report.warnings[0].message == "Test warning"
    
    def test_skip_checks(self):
        """Test that we can skip specific checks."""
        # Register dummy checker
        register_stage_checker("dummy", DummyChecker)
        
        runner = QualityRunner()
        
        # Skip one check
        config = QualityConfig(
            stage="dummy",
            thresholds={},
            skip_checks=["another_check"],
            output_format="text",
            verbose=False
        )
        
        report = runner.run_checks("dummy", Path("test.json"), config)
        
        # Should only have one check result
        assert len(report.check_results) == 1
        assert report.check_results[0].check_name == "dummy_check"
        assert report.overall_score == 1.0
    
    def test_available_checks_listing(self):
        """Test that we can list available checks for a stage."""
        # Register dummy checker
        register_stage_checker("dummy", DummyChecker)
        
        registry = get_registry()
        checks = registry.list_checks_for_stage("dummy")
        
        assert checks is not None
        assert len(checks) == 2
        assert "dummy_check" in checks
        assert "another_check" in checks
    
    def test_score_by_type(self):
        """Test getting scores by check type."""
        # Register dummy checker
        register_stage_checker("dummy", DummyChecker)
        
        runner = QualityRunner()
        config = QualityConfig(stage="dummy")
        report = runner.run_checks("dummy", Path("test.json"), config)
        
        # Test score by type
        completeness_score = report.get_score_by_type(QualityCheckType.COMPLETENESS)
        accuracy_score = report.get_score_by_type(QualityCheckType.ACCURACY)
        
        assert completeness_score == 1.0
        assert accuracy_score == 0.8