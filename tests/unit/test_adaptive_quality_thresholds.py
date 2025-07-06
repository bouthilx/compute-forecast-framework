"""
Test cases for Adaptive Quality Thresholds (Issue #13).
Testing TDD approach: write failing tests first, then implement minimal code.
"""

import pytest
from datetime import datetime, timedelta

from compute_forecast.quality.quality_structures import (
    QualityMetrics,
    QualityThresholds,
    AdaptationConfig,
    QualityTrend,
    QualityPerformanceMetrics,
    AdaptationStrategy,
    QualityTrendDirection,
)

# Import components to test (these will fail initially)
from compute_forecast.quality.adaptive_thresholds import AdaptiveThresholdEngine
from compute_forecast.quality.quality_analyzer import QualityAnalyzer
from compute_forecast.quality.threshold_optimizer import ThresholdOptimizer
from compute_forecast.quality.quality_filter import QualityFilter


class TestQualityAnalyzer:
    """Test QualityAnalyzer component"""

    def test_quality_analyzer_initialization(self):
        """Test QualityAnalyzer can be initialized"""
        analyzer = QualityAnalyzer()
        assert analyzer is not None

    def test_calculate_paper_quality_score(self):
        """Test paper quality score calculation using weighted formula"""
        analyzer = QualityAnalyzer()

        paper_data = {
            "citation_count": 10,
            "author_count": 3,
            "page_count": 12,
            "reference_count": 25,
            "venue_impact_factor": 2.5,
            "venue_h_index": 50.0,
        }

        # Should calculate weighted score based on QUALITY_SCORING_WEIGHTS
        score = analyzer.calculate_paper_quality_score(paper_data)

        # Expected calculation:
        # citation_count(10) * 0.3 + venue_impact_factor(2.5) * 0.25 +
        # author_count(3) * 0.1 + page_count(12) * 0.05 +
        # reference_count(25) * 0.1 + venue_h_index(50) * 0.2
        expected = (
            (10 * 0.3)
            + (2.5 * 0.25)
            + (3 * 0.1)
            + (12 * 0.05)
            + (25 * 0.1)
            + (50 * 0.2)
        )

        assert abs(score - expected) < 0.01
        assert isinstance(score, float)

    def test_assess_paper_quality(self):
        """Test complete paper quality assessment"""
        analyzer = QualityAnalyzer()

        paper_data = {
            "paper_id": "test_paper_123",
            "venue": "ICML",
            "year": 2024,
            "citation_count": 15,
            "author_count": 4,
            "page_count": 10,
            "reference_count": 30,
            "venue_impact_factor": 3.2,
            "venue_acceptance_rate": 0.22,
            "venue_h_index": 75.0,
        }

        metrics = analyzer.assess_paper_quality(paper_data)

        assert isinstance(metrics, QualityMetrics)
        assert metrics.paper_id == "test_paper_123"
        assert metrics.venue == "ICML"
        assert metrics.year == 2024
        assert metrics.citation_count == 15
        assert metrics.paper_quality_score > 0
        assert metrics.venue_quality_score > 0
        assert metrics.combined_quality_score > 0
        assert 0.0 <= metrics.confidence_level <= 1.0

    def test_calculate_venue_quality_score(self):
        """Test venue quality score calculation"""
        analyzer = QualityAnalyzer()

        venue_data = {
            "venue_impact_factor": 2.8,
            "venue_acceptance_rate": 0.18,
            "venue_h_index": 85.0,
        }

        score = analyzer.calculate_venue_quality_score(venue_data)

        assert isinstance(score, float)
        assert score > 0
        # Higher impact factor and h-index, lower acceptance rate = higher quality
        assert score > 0.5  # Should be reasonably high for good venue


class TestQualityFilter:
    """Test QualityFilter component"""

    def test_quality_filter_initialization(self):
        """Test QualityFilter can be initialized with thresholds"""
        thresholds = QualityThresholds(venue="ICML", year=2024)
        filter_obj = QualityFilter(thresholds)

        assert filter_obj is not None
        assert filter_obj.thresholds == thresholds

    def test_filter_paper_passes_quality(self):
        """Test filtering paper that meets quality thresholds"""
        thresholds = QualityThresholds(
            venue="ICML",
            min_citation_count=5,
            min_paper_quality_score=0.3,
            min_combined_quality_score=0.4,
        )
        filter_obj = QualityFilter(thresholds)

        # High quality paper
        metrics = QualityMetrics(
            paper_id="high_quality_paper",
            citation_count=10,
            paper_quality_score=0.7,
            combined_quality_score=0.8,
            confidence_level=0.9,
        )

        passes, reasons = filter_obj.evaluate_paper(metrics)

        assert passes is True
        assert isinstance(reasons, list)

    def test_filter_paper_fails_quality(self):
        """Test filtering paper that fails quality thresholds"""
        thresholds = QualityThresholds(
            venue="ICML",
            min_citation_count=10,
            min_paper_quality_score=0.5,
            min_combined_quality_score=0.6,
        )
        filter_obj = QualityFilter(thresholds)

        # Low quality paper
        metrics = QualityMetrics(
            paper_id="low_quality_paper",
            citation_count=2,
            paper_quality_score=0.3,
            combined_quality_score=0.4,
            confidence_level=0.5,
        )

        passes, reasons = filter_obj.evaluate_paper(metrics)

        assert passes is False
        assert isinstance(reasons, list)
        assert len(reasons) > 0  # Should have failure reasons

    def test_batch_filter_papers(self):
        """Test batch filtering of multiple papers"""
        thresholds = QualityThresholds(venue="ICML", min_citation_count=5)
        filter_obj = QualityFilter(thresholds)

        papers = [
            QualityMetrics(paper_id="paper1", citation_count=10),
            QualityMetrics(paper_id="paper2", citation_count=3),
            QualityMetrics(paper_id="paper3", citation_count=8),
        ]

        results = filter_obj.filter_papers(papers)

        assert isinstance(results, dict)
        assert "passed" in results
        assert "failed" in results
        assert len(results["passed"]) == 2  # paper1 and paper3
        assert len(results["failed"]) == 1  # paper2


class TestThresholdOptimizer:
    """Test ThresholdOptimizer component"""

    def test_threshold_optimizer_initialization(self):
        """Test ThresholdOptimizer can be initialized"""
        config = AdaptationConfig()
        optimizer = ThresholdOptimizer(config)

        assert optimizer is not None
        assert optimizer.config == config

    def test_optimize_thresholds_for_target_precision(self):
        """Test threshold optimization to meet target precision"""
        config = AdaptationConfig(target_precision=0.8, target_recall=0.9)
        optimizer = ThresholdOptimizer(config)

        current_thresholds = QualityThresholds(venue="ICML")

        # Mock performance data showing poor precision
        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=80,
            papers_rejected=20,
            collection_efficiency=0.8,
            true_positives=60,
            false_positives=20,  # High false positives = low precision
            true_negatives=15,
            false_negatives=5,
        )
        performance_data.calculate_derived_metrics()

        new_thresholds = optimizer.optimize_thresholds(
            current_thresholds, performance_data
        )

        assert isinstance(new_thresholds, QualityThresholds)
        # Should increase thresholds to reduce false positives
        assert (
            new_thresholds.min_paper_quality_score
            >= current_thresholds.min_paper_quality_score
        )

    def test_optimize_thresholds_for_target_recall(self):
        """Test threshold optimization to meet target recall"""
        config = AdaptationConfig(target_precision=0.8, target_recall=0.9)
        optimizer = ThresholdOptimizer(config)

        current_thresholds = QualityThresholds(
            venue="ICML", min_citation_count=10, min_paper_quality_score=0.7
        )

        # Mock performance data showing poor recall
        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=60,
            papers_rejected=40,
            collection_efficiency=0.6,
            true_positives=50,
            false_positives=10,
            true_negatives=30,
            false_negatives=10,  # High false negatives = low recall
        )
        performance_data.calculate_derived_metrics()

        new_thresholds = optimizer.optimize_thresholds(
            current_thresholds, performance_data
        )

        assert isinstance(new_thresholds, QualityThresholds)
        # Should decrease thresholds to reduce false negatives
        assert (
            new_thresholds.min_paper_quality_score
            <= current_thresholds.min_paper_quality_score
        )

    def test_calculate_gradient_for_threshold_adjustment(self):
        """Test gradient calculation for threshold optimization"""
        config = AdaptationConfig()
        optimizer = ThresholdOptimizer(config)

        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=80,
            papers_rejected=20,
            collection_efficiency=0.8,
            precision=0.7,
            recall=0.85,
            f1_score=0.75,
        )

        gradient = optimizer.calculate_optimization_gradient(performance_data)

        assert isinstance(gradient, dict)
        assert "precision_gradient" in gradient
        assert "recall_gradient" in gradient
        assert "f1_gradient" in gradient


class TestAdaptiveThresholdEngine:
    """Test AdaptiveThresholdEngine component"""

    def test_adaptive_threshold_engine_initialization(self):
        """Test AdaptiveThresholdEngine can be initialized"""
        config = AdaptationConfig()
        engine = AdaptiveThresholdEngine(config)

        assert engine is not None
        assert engine.config == config
        assert isinstance(engine.venue_thresholds, dict)

    def test_get_thresholds_for_venue(self):
        """Test getting thresholds for specific venue"""
        engine = AdaptiveThresholdEngine(AdaptationConfig())

        thresholds = engine.get_thresholds("ICML", 2024)

        assert isinstance(thresholds, QualityThresholds)
        assert thresholds.venue == "ICML"
        assert thresholds.year == 2024

    def test_update_thresholds_based_on_performance(self):
        """Test threshold updates based on performance feedback"""
        config = AdaptationConfig(strategy=AdaptationStrategy.BALANCED)
        engine = AdaptiveThresholdEngine(config)

        # Get initial thresholds
        initial_thresholds = engine.get_thresholds("ICML", 2024)
        initial_score = initial_thresholds.min_paper_quality_score
        initial_adaptation_count = initial_thresholds.adaptation_count

        # Create performance data indicating poor precision
        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=90,
            papers_rejected=10,
            collection_efficiency=0.9,
            precision=0.5,  # Below target of 0.8
            recall=0.95,
            f1_score=0.65,
        )

        # Update thresholds
        engine.update_thresholds("ICML", 2024, performance_data)

        # Get updated thresholds
        updated_thresholds = engine.get_thresholds("ICML", 2024)

        # Should have increased thresholds to improve precision
        assert updated_thresholds.min_paper_quality_score > initial_score
        assert updated_thresholds.adaptation_count > initial_adaptation_count

    def test_adaptation_respects_safety_limits(self):
        """Test that adaptation respects absolute minimum/maximum limits"""
        config = AdaptationConfig()
        config.absolute_maximum_thresholds["min_paper_quality_score"] = 0.5

        engine = AdaptiveThresholdEngine(config)

        # Try to force thresholds beyond safety limits
        extreme_performance = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=100,
            papers_rejected=0,
            collection_efficiency=1.0,
            precision=0.1,  # Very poor precision
            recall=1.0,
            f1_score=0.18,
        )

        # Multiple updates to try to exceed limits
        for _ in range(10):
            engine.update_thresholds("ICML", 2024, extreme_performance)

        thresholds = engine.get_thresholds("ICML", 2024)

        # Should not exceed safety limits
        assert thresholds.min_paper_quality_score <= 0.5

    def test_conservative_adaptation_strategy(self):
        """Test conservative adaptation strategy makes smaller changes"""
        conservative_config = AdaptationConfig(
            strategy=AdaptationStrategy.CONSERVATIVE, learning_rate=0.05
        )
        aggressive_config = AdaptationConfig(
            strategy=AdaptationStrategy.AGGRESSIVE, learning_rate=0.2
        )

        conservative_engine = AdaptiveThresholdEngine(conservative_config)
        aggressive_engine = AdaptiveThresholdEngine(aggressive_config)

        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=80,
            papers_rejected=20,
            collection_efficiency=0.8,
            precision=0.6,  # Below target
            recall=0.9,
            f1_score=0.72,
        )

        # Get initial thresholds (should be same for both)
        conservative_initial = conservative_engine.get_thresholds("ICML", 2024)
        aggressive_initial = aggressive_engine.get_thresholds("ICML", 2024)

        initial_score = conservative_initial.min_paper_quality_score

        # Update both engines
        conservative_engine.update_thresholds("ICML", 2024, performance_data)
        aggressive_engine.update_thresholds("ICML", 2024, performance_data)

        conservative_updated = conservative_engine.get_thresholds("ICML", 2024)
        aggressive_updated = aggressive_engine.get_thresholds("ICML", 2024)

        conservative_change = abs(
            conservative_updated.min_paper_quality_score - initial_score
        )
        aggressive_change = abs(
            aggressive_updated.min_paper_quality_score - initial_score
        )

        # Conservative should make smaller changes
        assert conservative_change < aggressive_change

    def test_static_strategy_prevents_adaptation(self):
        """Test static strategy prevents threshold adaptation"""
        config = AdaptationConfig(strategy=AdaptationStrategy.STATIC)
        engine = AdaptiveThresholdEngine(config)

        initial_thresholds = engine.get_thresholds("ICML", 2024)
        initial_score = initial_thresholds.min_paper_quality_score

        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=50,
            papers_rejected=50,
            collection_efficiency=0.5,
            precision=0.3,  # Very poor
            recall=0.5,  # Very poor
            f1_score=0.37,
        )

        # Try to update thresholds
        engine.update_thresholds("ICML", 2024, performance_data)

        updated_thresholds = engine.get_thresholds("ICML", 2024)

        # Thresholds should not change with static strategy
        assert updated_thresholds.min_paper_quality_score == initial_score

    def test_analyze_quality_trends(self):
        """Test quality trend analysis"""
        engine = AdaptiveThresholdEngine(AdaptationConfig())

        # Add historical quality data
        quality_history = []
        base_time = datetime.now() - timedelta(hours=24)

        for i in range(24):
            timestamp = base_time + timedelta(hours=i)
            quality_score = 0.5 + (i * 0.01)  # Increasing trend
            quality_history.append((timestamp, quality_score))

        trend = engine.analyze_quality_trends(
            "ICML", "paper_quality_score", quality_history
        )

        assert isinstance(trend, QualityTrend)
        assert trend.venue == "ICML"
        assert trend.metric_name == "paper_quality_score"
        assert trend.trend_direction == QualityTrendDirection.IMPROVING
        assert trend.trend_strength > 0
        assert trend.trend_confidence > 0


class TestIntegrationScenarios:
    """Integration tests for complete quality assessment workflow"""

    def test_complete_quality_assessment_workflow(self):
        """Test complete workflow: analyze -> filter -> optimize -> adapt"""
        # Initialize components
        analyzer = QualityAnalyzer()
        config = AdaptationConfig()
        engine = AdaptiveThresholdEngine(config)
        optimizer = ThresholdOptimizer(config)

        # Paper data
        paper_data = {
            "paper_id": "workflow_test_paper",
            "venue": "ICML",
            "year": 2024,
            "citation_count": 8,
            "author_count": 3,
            "page_count": 10,
            "reference_count": 20,
            "venue_impact_factor": 2.1,
            "venue_acceptance_rate": 0.25,
            "venue_h_index": 60.0,
        }

        # Step 1: Analyze paper quality
        metrics = analyzer.assess_paper_quality(paper_data)
        assert isinstance(metrics, QualityMetrics)

        # Step 2: Get thresholds and filter
        thresholds = engine.get_thresholds("ICML", 2024)
        filter_obj = QualityFilter(thresholds)
        passes, reasons = filter_obj.evaluate_paper(metrics)

        # Step 3: Create performance feedback
        performance_data = QualityPerformanceMetrics(
            venue="ICML",
            evaluation_period_hours=24,
            papers_evaluated=100,
            papers_collected=75,
            papers_rejected=25,
            collection_efficiency=0.75,
            precision=0.75,
            recall=0.85,
            f1_score=0.79,
        )

        # Step 4: Optimize and adapt thresholds
        optimized_thresholds = optimizer.optimize_thresholds(
            thresholds, performance_data
        )
        engine.update_thresholds("ICML", 2024, performance_data)

        # Verify workflow completed successfully
        assert isinstance(optimized_thresholds, QualityThresholds)
        updated_thresholds = engine.get_thresholds("ICML", 2024)
        assert updated_thresholds.adaptation_count > 0

    def test_real_time_quality_filtering_performance(self):
        """Test performance requirements for real-time filtering"""
        import time

        analyzer = QualityAnalyzer()
        thresholds = QualityThresholds(venue="ICML")
        filter_obj = QualityFilter(thresholds)

        # Generate test papers
        papers = []
        for i in range(100):
            paper_data = {
                "paper_id": f"perf_test_{i}",
                "venue": "ICML",
                "year": 2024,
                "citation_count": i % 20,
                "author_count": (i % 5) + 1,
                "page_count": 8 + (i % 10),
                "reference_count": 15 + (i % 25),
                "venue_impact_factor": 1.5 + (i % 3),
                "venue_h_index": 40 + (i % 40),
            }
            metrics = analyzer.assess_paper_quality(paper_data)
            papers.append(metrics)

        # Time the filtering operation
        start_time = time.time()
        results = filter_obj.filter_papers(papers)
        end_time = time.time()

        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds

        # Should complete within milliseconds (requirement from research)
        assert processing_time < 100  # Less than 100ms for 100 papers
        assert "passed" in results
        assert "failed" in results
        assert len(results["passed"]) + len(results["failed"]) == 100


# Test fixtures for common test data
@pytest.fixture
def sample_paper_data():
    """Sample paper data for testing"""
    return {
        "paper_id": "test_paper_123",
        "venue": "ICML",
        "year": 2024,
        "citation_count": 12,
        "author_count": 4,
        "page_count": 9,
        "reference_count": 28,
        "venue_impact_factor": 2.8,
        "venue_acceptance_rate": 0.20,
        "venue_h_index": 70.0,
    }


@pytest.fixture
def sample_quality_thresholds():
    """Sample quality thresholds for testing"""
    return QualityThresholds(
        venue="ICML",
        year=2024,
        min_citation_count=5,
        min_paper_quality_score=0.3,
        min_combined_quality_score=0.4,
        min_venue_quality_score=0.5,
    )


@pytest.fixture
def sample_adaptation_config():
    """Sample adaptation configuration for testing"""
    return AdaptationConfig(
        strategy=AdaptationStrategy.BALANCED,
        learning_rate=0.1,
        target_collection_efficiency=0.85,
        target_recall=0.95,
        target_precision=0.80,
    )
