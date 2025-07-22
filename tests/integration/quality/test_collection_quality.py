"""Integration tests for collection quality checker."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from compute_forecast.quality.core.interfaces import QualityConfig
from compute_forecast.quality.core.runner import QualityRunner
from compute_forecast.quality.core.registry import get_registry
from compute_forecast.quality.stages.collection import CollectionQualityChecker


class TestCollectionQualityIntegration:
    """Integration tests for collection quality checking."""

    def test_collection_checker_registration(self):
        """Test that collection checker is properly registered."""
        registry = get_registry()
        assert "collection" in registry.list_stages()

        checker = registry.get_checker("collection")
        assert checker is not None
        assert isinstance(checker, CollectionQualityChecker)

    def test_collection_checker_available_checks(self):
        """Test that collection checker has expected checks."""
        registry = get_registry()
        checks = registry.list_checks_for_stage("collection")

        assert checks is not None
        assert len(checks) == 4
        assert "completeness" in checks
        assert "consistency" in checks
        assert "accuracy" in checks
        assert "coverage" in checks

    def test_quality_runner_with_collection_data(self):
        """Test running quality checks on collection data."""
        with TemporaryDirectory() as tmp_dir:
            # Create test data
            test_data = self._create_test_collection_data()
            data_file = Path(tmp_dir) / "test_collection.json"

            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(
                stage="collection",
                thresholds={},
                skip_checks=[],
                output_format="text",
                verbose=False,
            )

            report = runner.run_checks("collection", data_file, config)

            # Verify report structure
            assert report.stage == "collection"
            assert report.data_path == data_file
            assert report.overall_score >= 0.0
            assert report.overall_score <= 1.0
            assert len(report.check_results) == 4

            # Check that all expected checks ran
            check_names = [result.check_name for result in report.check_results]
            assert "completeness_check" in check_names
            assert "consistency_check" in check_names
            assert "accuracy_check" in check_names
            assert "coverage_check" in check_names

    def test_quality_checks_with_good_data(self):
        """Test quality checks with high-quality data."""
        with TemporaryDirectory() as tmp_dir:
            # Create high-quality test data
            test_data = self._create_high_quality_collection_data()
            data_file = Path(tmp_dir) / "good_collection.json"

            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(stage="collection")
            report = runner.run_checks("collection", data_file, config)

            # Should have high overall score
            assert report.overall_score >= 0.8

            # Most checks should pass
            passed_checks = [r for r in report.check_results if r.passed]
            assert len(passed_checks) >= 3

            # Should have few critical issues
            assert len(report.critical_issues) <= 1

    def test_quality_checks_with_poor_data(self):
        """Test quality checks with low-quality data."""
        with TemporaryDirectory() as tmp_dir:
            # Create poor-quality test data
            test_data = self._create_poor_quality_collection_data()
            data_file = Path(tmp_dir) / "poor_collection.json"

            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(stage="collection")
            report = runner.run_checks("collection", data_file, config)

            # Should have low overall score
            assert report.overall_score < 0.7

            # Should have issues
            assert len(report.critical_issues) > 0 or len(report.warnings) > 0

    def test_quality_checks_with_empty_data(self):
        """Test quality checks with empty data."""
        with TemporaryDirectory() as tmp_dir:
            # Create empty data file
            data_file = Path(tmp_dir) / "empty_collection.json"

            with open(data_file, "w") as f:
                json.dump([], f)

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(stage="collection")
            report = runner.run_checks("collection", data_file, config)

            # Should have very low score
            assert report.overall_score <= 0.5

            # Should have critical issues
            assert len(report.critical_issues) > 0

    def test_quality_checks_with_directory_data(self):
        """Test quality checks with directory containing multiple files."""
        with TemporaryDirectory() as tmp_dir:
            # Create multiple data files
            data_dir = Path(tmp_dir) / "collection_data"
            data_dir.mkdir()

            # File 1
            data1 = self._create_test_collection_data()[:3]
            with open(data_dir / "papers1.json", "w") as f:
                json.dump(data1, f)

            # File 2
            data2 = self._create_test_collection_data()[3:]
            with open(data_dir / "papers2.json", "w") as f:
                json.dump(data2, f)

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(stage="collection")
            report = runner.run_checks("collection", data_dir, config)

            # Should successfully process all files
            assert report.overall_score >= 0.0
            assert len(report.check_results) == 4

    def test_skip_checks_functionality(self):
        """Test skipping specific checks."""
        with TemporaryDirectory() as tmp_dir:
            # Create test data
            test_data = self._create_test_collection_data()
            data_file = Path(tmp_dir) / "test_collection.json"

            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Skip accuracy check
            runner = QualityRunner()
            config = QualityConfig(stage="collection", skip_checks=["accuracy"])
            report = runner.run_checks("collection", data_file, config)

            # Should only have 3 checks
            assert len(report.check_results) == 3
            check_names = [result.check_name for result in report.check_results]
            assert "accuracy_check" not in check_names
            assert "completeness_check" in check_names
            assert "consistency_check" in check_names
            assert "coverage_check" in check_names

    def test_invalid_data_file(self):
        """Test handling of invalid data files."""
        with TemporaryDirectory() as tmp_dir:
            # Create invalid JSON file
            data_file = Path(tmp_dir) / "invalid.json"

            with open(data_file, "w") as f:
                f.write("invalid json content")

            # Run quality checks
            runner = QualityRunner()
            config = QualityConfig(stage="collection")

            # Should raise ValueError
            with pytest.raises(ValueError, match="Invalid JSON"):
                runner.run_checks("collection", data_file, config)

    def test_nonexistent_data_file(self):
        """Test handling of nonexistent data files."""
        runner = QualityRunner()
        config = QualityConfig(stage="collection")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Data path does not exist"):
            runner.run_checks("collection", Path("/nonexistent/path"), config)

    def test_completeness_validator_individually(self):
        """Test completeness validator with specific scenarios."""
        with TemporaryDirectory() as tmp_dir:
            # Test data with missing required fields
            test_data = [
                {
                    "title": "Complete Paper",
                    "authors": ["Author One", "Author Two"],
                    "venue": "Test Conference",
                    "year": 2023,
                    "abstract": "This is a complete paper.",
                    "pdf_url": "https://example.com/paper.pdf",
                },
                {
                    "title": "Incomplete Paper",
                    "authors": ["Author Three"],
                    # Missing venue and year
                    "abstract": "This paper is missing fields.",
                },
            ]

            data_file = Path(tmp_dir) / "completeness_test.json"
            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run only completeness check
            runner = QualityRunner()
            config = QualityConfig(
                stage="collection", skip_checks=["consistency", "accuracy", "coverage"]
            )
            report = runner.run_checks("collection", data_file, config)

            # Should have issues for missing fields
            completeness_result = report.check_results[0]
            assert completeness_result.check_name == "completeness_check"
            assert len(completeness_result.issues) > 0

            # Should have critical issues for missing required fields
            critical_issues = [
                i for i in completeness_result.issues if i.level.name == "CRITICAL"
            ]
            assert len(critical_issues) > 0

    def test_consistency_validator_individually(self):
        """Test consistency validator with specific scenarios."""
        with TemporaryDirectory() as tmp_dir:
            # Test data with duplicates and inconsistencies
            test_data = [
                {
                    "title": "Unique Paper",
                    "authors": ["Author One"],
                    "venue": "Conference A",
                    "year": 2023,
                },
                {
                    "title": "Duplicate Paper",
                    "authors": ["Author Two"],
                    "venue": "Conference B",
                    "year": 2023,
                },
                {
                    "title": "Duplicate Paper",  # Same title
                    "authors": ["Author Three"],
                    "venue": "Conference C",
                    "year": 2023,
                },
                {
                    "title": "Year Issue",
                    "authors": ["Author Four"],
                    "venue": "Conference D",
                    "year": "invalid_year",  # Invalid year
                },
            ]

            data_file = Path(tmp_dir) / "consistency_test.json"
            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run only consistency check
            runner = QualityRunner()
            config = QualityConfig(
                stage="collection", skip_checks=["completeness", "accuracy", "coverage"]
            )
            report = runner.run_checks("collection", data_file, config)

            # Should have issues for duplicates and invalid years
            consistency_result = report.check_results[0]
            assert consistency_result.check_name == "consistency_check"
            assert len(consistency_result.issues) > 0

    def test_accuracy_validator_individually(self):
        """Test accuracy validator with specific scenarios."""
        with TemporaryDirectory() as tmp_dir:
            # Test data with accuracy issues
            test_data = [
                {
                    "title": "Good Paper",
                    "authors": ["John Doe", "Jane Smith"],
                    "venue": "Good Conference",
                    "year": 2023,
                    "pdf_url": "https://example.com/good.pdf",
                    "doi": "10.1234/good.paper",
                },
                {
                    "title": "Bad Paper",
                    "authors": ["X", "123", ""],  # Bad author names
                    "venue": "Bad Conference",
                    "year": 2023,
                    "pdf_url": "not_a_url",  # Invalid URL
                    "doi": "invalid_doi",  # Invalid DOI
                },
            ]

            data_file = Path(tmp_dir) / "accuracy_test.json"
            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run only accuracy check
            runner = QualityRunner()
            config = QualityConfig(
                stage="collection",
                skip_checks=["completeness", "consistency", "coverage"],
            )
            report = runner.run_checks("collection", data_file, config)

            # Should have issues for invalid data
            accuracy_result = report.check_results[0]
            assert accuracy_result.check_name == "accuracy_check"
            assert len(accuracy_result.issues) > 0

    def test_coverage_validator_individually(self):
        """Test coverage validator with specific scenarios."""
        with TemporaryDirectory() as tmp_dir:
            # Test data with coverage issues
            test_data = [
                {
                    "title": "Paper 1",
                    "authors": ["Author One"],
                    "venue": "Venue A",
                    "year": 2023,
                    "scraper_source": "scraper1",
                },
                {
                    "title": "Paper 2",
                    "authors": ["Author Two"],
                    "venue": "Venue A",  # Same venue
                    "year": 2023,
                    "scraper_source": "scraper1",  # Same scraper
                },
                {
                    "title": "Paper 3",
                    "authors": ["Author Three"],
                    "venue": "Unknown",  # Unknown venue
                    "year": 2023,
                    # No scraper_source
                },
            ]

            data_file = Path(tmp_dir) / "coverage_test.json"
            with open(data_file, "w") as f:
                json.dump(test_data, f)

            # Run only coverage check
            runner = QualityRunner()
            config = QualityConfig(
                stage="collection",
                skip_checks=["completeness", "consistency", "accuracy"],
            )
            report = runner.run_checks("collection", data_file, config)

            # Should have issues for coverage limitations
            coverage_result = report.check_results[0]
            assert coverage_result.check_name == "coverage_check"
            # May have warnings about venue distribution or scraper diversity

    def _create_test_collection_data(self):
        """Create basic test collection data."""
        return [
            {
                "title": "Paper 1: Machine Learning Advances",
                "authors": ["John Smith", "Jane Doe"],
                "venue": "NeurIPS",
                "year": 2023,
                "abstract": "This paper presents advances in machine learning.",
                "pdf_url": "https://example.com/paper1.pdf",
                "doi": "10.1234/paper1",
                "scraper_source": "neurips_scraper",
            },
            {
                "title": "Paper 2: Deep Learning Research",
                "authors": ["Alice Johnson", "Bob Wilson"],
                "venue": "ICML",
                "year": 2023,
                "abstract": "This paper explores deep learning techniques.",
                "pdf_url": "https://example.com/paper2.pdf",
                "doi": "10.1234/paper2",
                "scraper_source": "icml_scraper",
            },
            {
                "title": "Paper 3: AI Applications",
                "authors": ["Charlie Brown", "Diana Prince"],
                "venue": "ICLR",
                "year": 2022,
                "abstract": "This paper discusses AI applications.",
                "pdf_url": "https://example.com/paper3.pdf",
                "doi": "10.1234/paper3",
                "scraper_source": "iclr_scraper",
            },
            {
                "title": "Paper 4: Neural Networks",
                "authors": ["Eve Davis", "Frank Miller"],
                "venue": "AAAI",
                "year": 2022,
                "abstract": "This paper analyzes neural networks.",
                "pdf_url": "https://example.com/paper4.pdf",
                "doi": "10.1234/paper4",
                "scraper_source": "aaai_scraper",
            },
        ]

    def _create_high_quality_collection_data(self):
        """Create high-quality test collection data."""
        return [
            {
                "title": "High Quality Paper 1: Advanced Machine Learning",
                "authors": ["Dr. John Smith", "Prof. Jane Doe"],
                "venue": "NeurIPS",
                "year": 2023,
                "abstract": "This paper presents significant advances in machine learning with comprehensive experiments.",
                "pdf_url": "https://proceedings.neurips.cc/paper1.pdf",
                "doi": "10.5555/neurips.2023.paper1",
                "keywords": ["machine learning", "neural networks"],
                "scraper_source": "neurips_scraper",
            },
            {
                "title": "High Quality Paper 2: Deep Learning Innovations",
                "authors": ["Dr. Alice Johnson", "Prof. Bob Wilson"],
                "venue": "ICML",
                "year": 2023,
                "abstract": "This paper explores innovative deep learning techniques with thorough analysis.",
                "pdf_url": "https://proceedings.icml.cc/paper2.pdf",
                "doi": "10.5555/icml.2023.paper2",
                "keywords": ["deep learning", "optimization"],
                "scraper_source": "icml_scraper",
            },
            {
                "title": "High Quality Paper 3: AI Research Breakthroughs",
                "authors": ["Dr. Charlie Brown", "Prof. Diana Prince"],
                "venue": "ICLR",
                "year": 2023,
                "abstract": "This paper discusses breakthrough AI research with extensive validation.",
                "pdf_url": "https://openreview.net/paper3.pdf",
                "doi": "10.5555/iclr.2023.paper3",
                "keywords": ["artificial intelligence", "research"],
                "scraper_source": "iclr_scraper",
            },
        ]

    def _create_poor_quality_collection_data(self):
        """Create poor-quality test collection data."""
        return [
            {
                "title": "Poor Paper 1",
                "authors": ["X", "Y"],  # Poor author names
                "venue": "Unknown",
                "year": 1800,  # Invalid year
                "abstract": "",  # Empty abstract
                "pdf_url": "not_a_url",  # Invalid URL
                "doi": "bad_doi",  # Invalid DOI
            },
            {
                "title": "Poor Paper 2",
                "authors": [],  # No authors
                "venue": "",  # Empty venue
                "year": "invalid",  # Invalid year format
                "pdf_url": "http://",  # Incomplete URL
                "doi": "",  # Empty DOI
            },
            {
                "title": "Poor Paper 1",  # Duplicate title
                "authors": ["Same Author"],
                "venue": "Same Venue",
                "year": 2023,
                # Missing many fields
            },
        ]
