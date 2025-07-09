"""Unit tests for CitationAnalyzer."""

import pytest
from datetime import datetime
from unittest.mock import patch
import numpy as np

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.metadata_collection.collectors.state_structures import (
    VenueConfig,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_analyzer import (
    CitationAnalyzer,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_statistics import (
    CitationAnalysisReport,
    CitationFilterResult,
    FilteringQualityReport,
    BreakthroughPaper,
)


class TestCitationAnalyzer:
    """Test citation analysis functionality."""

    @pytest.fixture
    def venue_configs(self):
        """Create venue configurations."""
        return [
            VenueConfig(
                venue_name="NeurIPS",
                target_years=[2021, 2022, 2023],
                max_papers_per_year=100,
                priority=1,
            ),
            VenueConfig(
                venue_name="ICML",
                target_years=[2021, 2022, 2023],
                max_papers_per_year=100,
                priority=1,
            ),
            VenueConfig(
                venue_name="CVPR",
                target_years=[2021, 2022, 2023],
                max_papers_per_year=80,
                priority=2,
            ),
        ]

    @pytest.fixture
    def analyzer(self, venue_configs):
        """Create analyzer instance."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.Path.exists",
            return_value=False,
        ):
            return CitationAnalyzer(venue_configs)

    @pytest.fixture
    def sample_papers(self):
        """Create diverse sample papers for testing."""
        papers = []

        # High-impact NeurIPS papers
        for i in range(5):
            papers.append(
                Paper(
                    paper_id=f"neurips_high_{i}",
                    title=f"High Impact NeurIPS Paper {i}",
                    venue="NeurIPS",
                    normalized_venue="NeurIPS",
                    year=2023,
                    citations=100 + i * 20,
                    authors=[Author(name=f"Author {i}")],
                )
            )

        # Medium-impact ICML papers
        for i in range(5):
            papers.append(
                Paper(
                    paper_id=f"icml_med_{i}",
                    title=f"Medium Impact ICML Paper {i}",
                    venue="ICML",
                    normalized_venue="ICML",
                    year=2022,
                    citations=30 + i * 5,
                    authors=[Author(name=f"Author {i + 5}")],
                )
            )

        # Low-impact CVPR papers
        for i in range(5):
            papers.append(
                Paper(
                    paper_id=f"cvpr_low_{i}",
                    title=f"Low Impact CVPR Paper {i}",
                    venue="CVPR",
                    normalized_venue="CVPR",
                    year=2021,
                    citations=i * 2,
                    authors=[Author(name=f"Author {i + 10}")],
                )
            )

        # Zero citation papers
        for i in range(3):
            papers.append(
                Paper(
                    paper_id=f"zero_{i}",
                    title=f"Zero Citation Paper {i}",
                    venue="Workshop",
                    normalized_venue="Workshop",
                    year=2023,
                    citations=0,
                    authors=[Author(name=f"Author {i + 15}")],
                )
            )

        return papers

    def test_analyze_citation_distributions(self, analyzer, sample_papers):
        """Test comprehensive citation distribution analysis."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.citation_analyzer.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            analyzer.current_year = 2024

            report = analyzer.analyze_citation_distributions(sample_papers)

            assert isinstance(report, CitationAnalysisReport)
            assert report.papers_analyzed == len(sample_papers)
            assert len(report.venue_analysis) > 0
            assert len(report.year_analysis) > 0
            assert len(report.overall_percentiles) > 0
            # Check papers with zero citations (papers that have citations field == 0)
            zero_citation_count = len([p for p in sample_papers if p.citations == 0])
            assert len(report.zero_citation_papers) == zero_citation_count
            assert len(report.high_citation_outliers) > 0
            assert len(report.suggested_thresholds) > 0
            assert len(report.quality_indicators) > 0
            assert len(report.filtering_recommendations) > 0

    def test_filter_papers_by_citations_with_breakthrough(
        self, analyzer, sample_papers
    ):
        """Test citation filtering with breakthrough preservation."""
        # Mock breakthrough detection
        mock_breakthrough = BreakthroughPaper(
            paper=sample_papers[-1],  # Zero citation paper
            breakthrough_score=0.8,
            breakthrough_indicators=["Test indicator"],
            citation_velocity_score=0.1,
            keyword_score=0.9,
            author_reputation_score=0.5,
            venue_prestige_score=0.4,
            recency_bonus=1.0,
            matched_keywords=["breakthrough"],
            high_impact_authors=[],
            citation_velocity=0.0,
        )

        with patch.object(
            analyzer.breakthrough_detector,
            "detect_breakthrough_papers",
            return_value=[mock_breakthrough],
        ):
            result = analyzer.filter_papers_by_citations(
                sample_papers, preserve_breakthroughs=True
            )

            assert isinstance(result, CitationFilterResult)
            assert result.original_count == len(sample_papers)
            assert result.filtered_count > 0
            assert len(result.papers_above_threshold) > 0
            assert len(result.papers_below_threshold) > 0
            assert len(result.breakthrough_papers_preserved) == 1
            assert result.breakthrough_preservation_rate == 1.0
            assert result.estimated_precision > 0
            assert result.estimated_coverage > 0

    def test_filter_papers_by_citations_without_breakthrough(
        self, analyzer, sample_papers
    ):
        """Test citation filtering without breakthrough preservation."""
        result = analyzer.filter_papers_by_citations(
            sample_papers, preserve_breakthroughs=False
        )

        assert isinstance(result, CitationFilterResult)
        assert len(result.breakthrough_papers_preserved) == 0
        assert result.filtered_count < result.original_count
        # Papers should meet their venue/year-specific threshold (which may be 0 in edge cases)
        assert all(
            p in result.papers_above_threshold or p in result.papers_below_threshold
            for p in sample_papers
        )

    def test_detect_breakthrough_papers(self, analyzer, sample_papers):
        """Test breakthrough paper detection."""
        # Add a potential breakthrough paper
        breakthrough_paper = Paper(
            paper_id="breakthrough1",
            title="Transformer: A Novel Architecture",
            abstract="We present a breakthrough method",
            venue="NeurIPS",
            normalized_venue="NeurIPS",
            year=2023,
            citations=200,
            authors=[Author(name="Geoffrey Hinton")],
        )
        papers = sample_papers + [breakthrough_paper]

        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            analyzer.breakthrough_detector.current_year = 2024

            breakthrough_papers = analyzer.detect_breakthrough_papers(papers)

            assert len(breakthrough_papers) > 0
            assert any(
                bp.paper.paper_id == "breakthrough1" for bp in breakthrough_papers
            )

    def test_calculate_adaptive_threshold(self, analyzer, sample_papers):
        """Test adaptive threshold calculation."""
        neurips_papers = [p for p in sample_papers if p.venue == "NeurIPS"]

        threshold = analyzer.calculate_adaptive_threshold(
            "NeurIPS", 2023, neurips_papers
        )

        assert threshold.venue == "NeurIPS"
        assert threshold.year == 2023
        assert threshold.threshold > 0
        assert threshold.confidence > 0
        assert threshold.base_threshold > 0
        assert threshold.papers_analyzed == len(neurips_papers)
        assert "50th_percentile" in threshold.alternative_thresholds

    def test_validate_filtering_quality(self, analyzer, sample_papers):
        """Test filtering quality validation."""
        # Filter to keep only high-citation papers
        filtered_papers = [p for p in sample_papers if p.citations and p.citations > 50]

        report = analyzer.validate_filtering_quality(sample_papers, filtered_papers)

        assert isinstance(report, FilteringQualityReport)
        assert report.total_papers_original == len(sample_papers)
        assert report.total_papers_filtered == len(filtered_papers)
        assert report.venue_coverage_rate > 0
        assert report.impact_preservation_rate > 0
        assert report.breakthrough_preservation_rate >= 0
        assert report.citation_improvement_ratio > 1.0  # Should improve average
        assert len(report.warnings) > 0  # Should warn about aggressive filtering
        assert len(report.recommendations) > 0

    def test_venue_tier_assignment(self, analyzer):
        """Test venue tier assignment."""
        assert analyzer._get_venue_tier("NeurIPS") == "tier1"
        assert analyzer._get_venue_tier("ICML") == "tier1"
        assert analyzer._get_venue_tier("CVPR") == "tier2"
        assert analyzer._get_venue_tier("UAI") == "tier3"
        assert analyzer._get_venue_tier("Unknown") == "tier4"

    def test_percentile_calculation(self, analyzer):
        """Test percentile calculation."""
        citations = list(range(0, 101, 10))  # 0, 10, 20, ..., 100

        percentiles = analyzer._calculate_percentiles(citations)

        assert percentiles[50] == 50.0  # Median
        assert percentiles[25] == 25.0
        assert percentiles[75] == 75.0
        assert percentiles[90] == 90.0
        assert len(percentiles) == 8  # Should calculate 8 different percentiles

    def test_empty_paper_list(self, analyzer):
        """Test handling empty paper list."""
        report = analyzer.analyze_citation_distributions([])

        assert report.papers_analyzed == 0
        assert len(report.venue_analysis) == 0
        assert len(report.year_analysis) == 0
        assert len(report.breakthrough_candidates) == 0

    def test_papers_without_citations(self, analyzer):
        """Test handling papers without citation data."""
        papers = [
            Paper(
                paper_id=str(i),
                title=f"Paper {i}",
                venue="Test",
                year=2023,
                citations=None,
                authors=[Author(name="Test")],
            )
            for i in range(5)
        ]

        report = analyzer.analyze_citation_distributions(papers)

        assert report.papers_analyzed == 5
        assert len(report.zero_citation_papers) == 0  # None is different from 0

    def test_performance_large_dataset(self, analyzer):
        """Test performance with large dataset (50,000+ papers)."""
        # Create large dataset
        large_papers = []
        for i in range(50000):
            large_papers.append(
                Paper(
                    paper_id=str(i),
                    title=f"Paper {i}",
                    venue="NeurIPS" if i % 3 == 0 else "ICML" if i % 3 == 1 else "CVPR",
                    normalized_venue="NeurIPS"
                    if i % 3 == 0
                    else "ICML"
                    if i % 3 == 1
                    else "CVPR",
                    year=2020 + (i % 4),
                    citations=np.random.poisson(20),  # Poisson distribution
                    authors=[Author(name=f"Author {i % 100}")],
                )
            )

        import time

        start_time = time.time()

        report = analyzer.analyze_citation_distributions(large_papers)

        end_time = time.time()
        duration = end_time - start_time

        # Should process 50,000+ papers within 2 minutes (120 seconds)
        assert duration < 120
        assert report.papers_analyzed == 50000

    def test_venue_analysis_statistics(self, analyzer, sample_papers):
        """Test venue-specific statistics calculation."""
        report = analyzer.analyze_citation_distributions(sample_papers)

        neurips_stats = report.venue_analysis.get("NeurIPS")
        assert neurips_stats is not None
        assert neurips_stats.venue_name == "NeurIPS"
        assert neurips_stats.venue_tier == "tier1"
        assert neurips_stats.total_papers == 5
        assert neurips_stats.mean_citations > 0
        assert neurips_stats.median_citations > 0
        assert len(neurips_stats.citation_percentiles) > 0
        assert len(neurips_stats.high_impact_papers) > 0
        assert neurips_stats.recommended_threshold > 0

    def test_filtering_statistics(self, analyzer, sample_papers):
        """Test filtering statistics generation."""
        result = analyzer.filter_papers_by_citations(sample_papers)

        assert "above_threshold" in result.filtering_statistics
        assert "below_threshold" in result.filtering_statistics
        assert sum(result.filtering_statistics.values()) == len(sample_papers)
        assert len(result.venue_representation) > 0
        assert len(result.threshold_compliance) > 0

    def test_quality_indicators(self, analyzer, sample_papers):
        """Test quality indicator calculation."""
        report = analyzer.analyze_citation_distributions(sample_papers)

        indicators = report.quality_indicators
        assert "mean_citations" in indicators
        assert "median_citations" in indicators
        assert "citation_variance" in indicators
        assert "zero_citation_rate" in indicators
        assert "venue_count" in indicators
        assert "papers_per_venue" in indicators
        assert "breakthrough_rate" in indicators
        assert "recent_paper_rate" in indicators

    def test_filtering_recommendations(self, analyzer, sample_papers):
        """Test filtering recommendation generation."""
        report = analyzer.analyze_citation_distributions(sample_papers)

        recommendations = report.filtering_recommendations
        assert len(recommendations) > 0
        assert any("venue-specific" in rec for rec in recommendations)
        assert any("Validate" in rec for rec in recommendations)
