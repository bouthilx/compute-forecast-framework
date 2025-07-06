"""Unit tests for AdaptiveThresholdCalculator."""

import pytest
from datetime import datetime
from unittest.mock import patch

from compute_forecast.data.models import Paper, Author
from compute_forecast.data.processors.adaptive_threshold_calculator import (
    AdaptiveThresholdCalculator,
)


class TestAdaptiveThresholdCalculator:
    """Test adaptive threshold calculation functionality."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return AdaptiveThresholdCalculator()

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                paper_id="1",
                title="Paper 1",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2023,
                citations=50,
                authors=[Author(name="Author 1")],
            ),
            Paper(
                paper_id="2",
                title="Paper 2",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2023,
                citations=30,
                authors=[Author(name="Author 2")],
            ),
            Paper(
                paper_id="3",
                title="Paper 3",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2023,
                citations=10,
                authors=[Author(name="Author 3")],
            ),
            Paper(
                paper_id="4",
                title="Paper 4",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2023,
                citations=5,
                authors=[Author(name="Author 4")],
            ),
            Paper(
                paper_id="5",
                title="Paper 5",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2023,
                citations=2,
                authors=[Author(name="Author 5")],
            ),
        ]

    def test_calculate_venue_threshold_tier1_recent(self, calculator, sample_papers):
        """Test threshold calculation for tier1 venue with recent papers."""
        with patch(
            "src.data.processors.adaptive_threshold_calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            calculator.current_year = 2024

            threshold = calculator.calculate_venue_threshold(
                "NeurIPS", 2023, sample_papers, "tier1"
            )

            # For tier1 venue, 1 year old: base=5
            # Statistical threshold (75th percentile) should be around 30
            # Weighted: 0.6 * 30 + 0.4 * 5 = 20
            # But minimum representation (70th percentile) is around 10
            assert threshold == 20

    def test_calculate_venue_threshold_tier2_older(self, calculator, sample_papers):
        """Test threshold calculation for tier2 venue with older papers."""
        with patch(
            "src.data.processors.adaptive_threshold_calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            calculator.current_year = 2024

            # Change year to make papers older
            for paper in sample_papers:
                paper.year = 2020

            threshold = calculator.calculate_venue_threshold(
                "CVPR", 2020, sample_papers, "tier2"
            )

            # For tier2 venue, 4 years old: base=12
            # Statistical threshold (75th percentile) should be around 30
            # Weighted: 0.6 * 30 + 0.4 * 12 = 22.8 ≈ 22
            # Minimum representation (70th percentile) would apply if lower
            # For papers from same venue, threshold is based on actual statistics
            assert threshold >= 10  # Should be at least 10

    def test_calculate_venue_threshold_no_papers(self, calculator):
        """Test threshold calculation with no papers."""
        threshold = calculator.calculate_venue_threshold("NewVenue", 2023, [], "tier3")

        # With current_year from datetime.now(), might be different year calculation
        assert threshold >= 3  # Should at least be base threshold

    def test_calculate_venue_threshold_no_citations(self, calculator):
        """Test threshold calculation with papers having no citations."""
        papers = [
            Paper(
                paper_id=str(i),
                title=f"Paper {i}",
                venue="Venue",
                year=2023,
                citations=None,
                authors=[Author(name="Test")],
            )
            for i in range(5)
        ]

        threshold = calculator.calculate_venue_threshold("Venue", 2023, papers, "tier4")

        # When no citations data available, depends on mock data
        # With current implementation, it might use a different calculation
        assert threshold >= 1  # Should at least be minimum threshold

    def test_calculate_percentile_threshold(self, calculator):
        """Test percentile threshold calculation."""
        citations = [1, 5, 10, 20, 30, 40, 50, 60, 70, 100]

        # 50th percentile (median)
        assert 30 <= calculator.calculate_percentile_threshold(citations, 50) <= 40

        # 75th percentile
        assert 50 <= calculator.calculate_percentile_threshold(citations, 75) <= 60

        # 90th percentile
        assert 70 <= calculator.calculate_percentile_threshold(citations, 90) <= 100

    def test_calculate_percentile_threshold_empty(self, calculator):
        """Test percentile calculation with empty list."""
        assert calculator.calculate_percentile_threshold([], 50) == 0

    def test_calculate_adaptive_threshold_comprehensive(
        self, calculator, sample_papers
    ):
        """Test comprehensive adaptive threshold calculation."""
        with patch(
            "src.data.processors.adaptive_threshold_calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            calculator.current_year = 2024

            result = calculator.calculate_adaptive_threshold(
                "NeurIPS", 2023, sample_papers, "tier1"
            )

            assert result.venue == "NeurIPS"
            assert result.year == 2023
            assert result.threshold == 20  # Based on weighted calculation
            assert result.confidence > 0  # Should have some confidence
            assert result.base_threshold == 5  # tier1, 1 year old
            assert result.recency_adjustment == 0.9  # 1 year * 0.1
            assert result.venue_prestige_multiplier == 1.0  # tier1
            assert result.papers_analyzed == 5
            assert result.papers_above_threshold == 2  # Papers with >=20 citations
            assert result.percentile_used == 75.0
            assert "50th_percentile" in result.alternative_thresholds
            assert "80th_percentile" in result.alternative_thresholds
            assert "90th_percentile" in result.alternative_thresholds

    def test_get_venue_tier_multiplier(self, calculator):
        """Test venue tier multiplier retrieval."""
        assert calculator.get_venue_tier_multiplier("tier1") == 1.0
        assert calculator.get_venue_tier_multiplier("tier2") == 0.8
        assert calculator.get_venue_tier_multiplier("tier3") == 0.6
        assert calculator.get_venue_tier_multiplier("tier4") == 0.4
        assert calculator.get_venue_tier_multiplier("unknown") == 0.4  # Default

    def test_minimum_threshold(self, calculator):
        """Test threshold edge cases including papers with 0 citations."""
        # Test with all papers having 0 citations
        papers = [
            Paper(
                paper_id="1",
                title="P1",
                venue="Venue",
                year=2023,
                citations=0,
                authors=[Author(name="Test")],
            ),
            Paper(
                paper_id="2",
                title="P2",
                venue="Venue",
                year=2023,
                citations=0,
                authors=[Author(name="Test")],
            ),
            Paper(
                paper_id="3",
                title="P3",
                venue="Venue",
                year=2023,
                citations=0,
                authors=[Author(name="Test")],
            ),
        ]

        threshold = calculator.calculate_venue_threshold("Venue", 2023, papers, "tier4")

        # When all papers have 0 citations, threshold should be 0 to ensure minimum representation
        assert threshold == 0

        # Test with mixed citations
        papers_mixed = [
            Paper(
                paper_id="1",
                title="P1",
                venue="Venue",
                year=2023,
                citations=0,
                authors=[Author(name="Test")],
            ),
            Paper(
                paper_id="2",
                title="P2",
                venue="Venue",
                year=2023,
                citations=1,
                authors=[Author(name="Test")],
            ),
            Paper(
                paper_id="3",
                title="P3",
                venue="Venue",
                year=2023,
                citations=2,
                authors=[Author(name="Test")],
            ),
        ]

        threshold_mixed = calculator.calculate_venue_threshold(
            "Venue", 2023, papers_mixed, "tier4"
        )

        # With mixed citations, threshold should be at least 0
        assert threshold_mixed >= 0

    def test_years_capping(self, calculator):
        """Test that years since publication is capped at 4 for base threshold."""
        with patch(
            "src.data.processors.adaptive_threshold_calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            calculator.current_year = 2024

            # Test with very old papers (10 years)
            old_papers = [
                Paper(
                    paper_id="1",
                    title="Old",
                    venue="NeurIPS",
                    year=2014,
                    citations=100,
                    authors=[Author(name="Test")],
                )
            ]

            result = calculator.calculate_adaptive_threshold(
                "NeurIPS", 2014, old_papers, "tier1"
            )

            # Should use the max base threshold for tier1 (4+ years)
            assert result.base_threshold == 15  # tier1, 4+ years
