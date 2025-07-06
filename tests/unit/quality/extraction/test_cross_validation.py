"""
Tests for CrossValidationFramework.
"""

from compute_forecast.quality.extraction.cross_validation import (
    CrossValidationFramework,
)
from compute_forecast.data.models import Paper


class TestCrossValidationFramework:
    """Test cross-validation framework."""

    def setup_method(self):
        """Set up test fixtures."""
        self.framework = CrossValidationFramework()

        # Create test papers
        self.papers = []
        for year in [2019, 2020, 2021, 2022, 2023]:
            for i in range(30):  # 30 papers per year
                paper = Paper(
                    paper_id=f"paper_{year}_{i}",
                    title=f"Model {i} Research {year}",
                    year=year,
                    venue=f"Conference{i % 3}",  # 3 different venues
                    authors=[],
                    citations=0,
                )
                self.papers.append(paper)

    def test_select_validation_sample_random(self):
        """Test random sampling."""
        sample = self.framework.select_validation_sample(
            self.papers, stratify_by="none"
        )

        assert len(sample) == self.framework.manual_sample_size
        assert all(p in self.papers for p in sample)
        assert len(set(p.paper_id for p in sample)) == len(sample)  # No duplicates

    def test_select_validation_sample_by_year(self):
        """Test stratified sampling by year."""
        sample = self.framework.select_validation_sample(
            self.papers, stratify_by="year"
        )

        assert len(sample) == self.framework.manual_sample_size

        # Check year distribution
        years_in_sample = [p.year for p in sample]
        for year in [2019, 2020, 2021, 2022, 2023]:
            year_count = years_in_sample.count(year)
            # Each year should have roughly 20 papers (100/5)
            assert 15 < year_count < 25

    def test_select_validation_sample_small_dataset(self):
        """Test sampling with dataset smaller than sample size."""
        small_papers = self.papers[:50]
        sample = self.framework.select_validation_sample(small_papers)

        assert len(sample) == len(small_papers)
        assert all(p in small_papers for p in sample)

    def test_compare_extractions_perfect_match(self):
        """Test comparison with perfect match."""
        manual = {
            "paper_1": {"gpu_hours": 1000, "parameters": 1e9, "batch_size": 256},
            "paper_2": {"gpu_hours": 2000, "parameters": 2e9, "batch_size": 512},
        }
        automated = manual.copy()

        accuracies = self.framework.compare_extractions(manual, automated)

        assert accuracies["gpu_hours"] == 1.0
        assert accuracies["parameters"] == 1.0
        assert accuracies["batch_size"] == 1.0

    def test_compare_extractions_within_tolerance(self):
        """Test comparison with values within tolerance."""
        manual = {"paper_1": {"gpu_hours": 1000, "parameters": 1e9}}
        automated = {
            "paper_1": {
                "gpu_hours": 1100,
                "parameters": 1.05e9,
            }  # 10% and 5% difference
        }

        accuracies = self.framework.compare_extractions(manual, automated)

        # Should be within tolerance
        assert accuracies["gpu_hours"] > 0.8  # 15% tolerance
        assert accuracies["parameters"] > 0.9  # 10% tolerance

    def test_compare_extractions_outside_tolerance(self):
        """Test comparison with values outside tolerance."""
        manual = {"paper_1": {"gpu_hours": 1000, "batch_size": 256}}
        automated = {
            "paper_1": {"gpu_hours": 2000, "batch_size": 512}  # 100% difference
        }

        accuracies = self.framework.compare_extractions(manual, automated)

        assert accuracies["gpu_hours"] < 0.5
        assert accuracies["batch_size"] < 0.5  # Exact match required

    def test_calculate_field_agreement_numeric(self):
        """Test field agreement calculation for numeric values."""
        # Exact match
        agreement, accuracy = self.framework._calculate_field_agreement(
            "gpu_count", 8, 8
        )
        assert agreement is True
        assert accuracy == 1.0

        # Within tolerance
        agreement, accuracy = self.framework._calculate_field_agreement(
            "gpu_hours",
            1000,
            1100,  # 10% difference
        )
        assert agreement is True
        assert accuracy > 0.8

        # Outside tolerance
        agreement, accuracy = self.framework._calculate_field_agreement(
            "gpu_hours",
            1000,
            2000,  # 100% difference
        )
        assert agreement is False
        assert accuracy < 0.5

    def test_calculate_field_agreement_string(self):
        """Test field agreement calculation for string values."""
        # Exact match
        agreement, accuracy = self.framework._calculate_field_agreement(
            "framework",
            "pytorch",
            "PyTorch",  # Case insensitive
        )
        assert agreement is True
        assert accuracy == 1.0

        # Different strings
        agreement, accuracy = self.framework._calculate_field_agreement(
            "framework", "pytorch", "tensorflow"
        )
        assert agreement is False
        assert accuracy == 0.0

    def test_generate_calibration_model(self):
        """Test calibration model generation."""
        comparisons = [
            {
                "gpu_hours": [
                    {"manual": 1000, "automated": 900},
                    {"manual": 2000, "automated": 1850},
                    {"manual": 500, "automated": 450},
                    {"manual": 1500, "automated": 1400},
                    {"manual": 3000, "automated": 2800},
                ]
            }
        ]

        calibration_params = self.framework.generate_calibration_model(comparisons)

        assert "gpu_hours" in calibration_params
        gpu_hours_params = calibration_params["gpu_hours"]

        # Should find systematic bias (automated values are ~10% lower)
        assert gpu_hours_params["slope"] > 1.0
        assert gpu_hours_params["r_squared"] > 0.9
        assert gpu_hours_params["reliable"] is True

    def test_apply_calibration(self):
        """Test calibration application."""
        # Set up calibration model
        self.framework.calibration_models = {
            "gpu_hours": {"slope": 1.1, "intercept": 50, "reliable": True}
        }

        # Apply calibration
        calibrated, is_calibrated = self.framework.apply_calibration("gpu_hours", 1000)

        assert is_calibrated is True
        assert calibrated == 1150  # 1.1 * 1000 + 50

        # Test uncalibrated field
        original, is_calibrated = self.framework.apply_calibration("parameters", 1000)

        assert is_calibrated is False
        assert original == 1000

    def test_validate_extraction_quality(self):
        """Test comprehensive extraction quality validation."""
        manual_sample = {
            "paper_1": {"gpu_hours": 1000, "parameters": 1e9},
            "paper_2": {"gpu_hours": 2000, "parameters": 2e9},
        }

        automated_full = {
            "paper_1": {"gpu_hours": 1100, "parameters": 1.05e9},
            "paper_2": {"gpu_hours": 2200, "parameters": 2.1e9},
            "paper_3": {"gpu_hours": 3000, "parameters": 3e9},
        }

        report = self.framework.validate_extraction_quality(
            manual_sample, automated_full
        )

        assert "overall_accuracy" in report
        assert "field_accuracies" in report
        assert "problematic_fields" in report
        assert "recommendations" in report

        # Should have good accuracy
        assert report["overall_accuracy"] > 0.8
        assert len(report["problematic_fields"]) == 0

    def test_stratified_sample_by_domain(self):
        """Test stratified sampling by domain."""
        # Add domain-specific titles
        for i, paper in enumerate(self.papers):
            if i % 3 == 0:
                paper.title = f"Transformer NLP Model {i}"
            elif i % 3 == 1:
                paper.title = f"CNN Image Classification {i}"
            else:
                paper.title = f"RL Agent Training {i}"

        sample = self.framework.select_validation_sample(
            self.papers, stratify_by="domain"
        )

        assert len(sample) == self.framework.manual_sample_size

        # Check domain distribution
        nlp_count = sum(1 for p in sample if "nlp" in p.title.lower())
        cv_count = sum(
            1 for p in sample if "cnn" in p.title.lower() or "image" in p.title.lower()
        )
        rl_count = sum(1 for p in sample if "rl" in p.title.lower())

        # Should have representation from all domains
        assert nlp_count > 20
        assert cv_count > 20
        assert rl_count > 20
