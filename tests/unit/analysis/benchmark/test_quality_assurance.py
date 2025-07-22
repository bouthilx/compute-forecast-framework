"""Tests for extraction quality assurance."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from compute_forecast.pipeline.analysis.benchmark.quality_assurance import (
    ExtractionQualityAssurance,
)
from compute_forecast.pipeline.analysis.benchmark.models import (
    BenchmarkDomain,
    ExtractionBatch,
    BenchmarkPaper,
    ExtractionQA,
)
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    Author,
)


def create_mock_paper(extraction_confidence=0.8):
    """Create a mock paper with extraction_confidence attribute."""
    mock = Mock()
    mock.extraction_confidence = extraction_confidence
    return mock


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestExtractionQualityAssurance:
    """Test the extraction quality assurance system."""

    @pytest.fixture
    def qa_system(self):
        """Create a quality assurance system instance."""
        return ExtractionQualityAssurance()

    @pytest.fixture
    def sample_extraction_results(self):
        """Create sample extraction results for testing."""
        results = []

        # Create balanced results across domains and years
        for domain in [BenchmarkDomain.NLP, BenchmarkDomain.CV, BenchmarkDomain.RL]:
            for year in [2022, 2023, 2024]:
                papers = []
                for i in range(40):  # 40 papers per domain-year
                    confidence = 0.9 - (i * 0.02)  # Gradually decreasing confidence
                    paper = create_test_paper(
                        paper_id=f"{domain.value}_{year}_{i}",
                        title=f"Paper {i}",
                        year=year,
                        venue="Test",
                        authors=[Author(name="Author")],
                        citation_count=i * 10,  # Add required citations field
                    )

                    benchmark_paper = BenchmarkPaper(
                        paper=paper,
                        domain=domain,
                        is_sota=(i < 5),  # First 5 are SOTA
                        benchmark_datasets=["Dataset1"],
                        computational_requirements=ComputationalAnalysis(
                            computational_richness=confidence,
                            keyword_matches={"gpu": 1} if confidence > 0.5 else {},
                            resource_metrics={"gpu_hours": 100.0}
                            if confidence > 0.5
                            else {},
                            experimental_indicators={"has_ablation": confidence > 0.7},
                            confidence_score=confidence,
                        ),
                        extraction_confidence=confidence,
                    )
                    papers.append(benchmark_paper)

                # Determine counts based on confidence thresholds
                high_conf = sum(1 for p in papers if p.extraction_confidence >= 0.7)
                manual_review = [
                    p.paper.paper_id for p in papers if p.extraction_confidence < 0.7
                ]

                batch = ExtractionBatch(
                    domain=domain,
                    year=year,
                    papers=papers,
                    total_extracted=len(papers),
                    high_confidence_count=high_conf,
                    requires_manual_review=manual_review,
                )
                results.append(batch)

        return results

    def test_qa_system_initialization(self, qa_system):
        """Test QA system initializes with correct thresholds."""
        assert qa_system.min_extraction_rate == 0.8
        assert qa_system.min_high_confidence_rate == 0.6

    def test_validate_coverage(self, qa_system, sample_extraction_results):
        """Test coverage validation across domains and years."""
        is_valid = qa_system.validate_coverage(sample_extraction_results)

        assert is_valid is True

        # Test with insufficient coverage
        poor_results = sample_extraction_results[:2]  # Only 2 batches
        is_valid = qa_system.validate_coverage(poor_results)

        assert is_valid is False

    def test_validate_distribution(self, qa_system, sample_extraction_results):
        """Test distribution validation is balanced."""
        distribution = qa_system.validate_distribution(sample_extraction_results)

        assert "domains" in distribution
        assert "years" in distribution
        assert "is_balanced" in distribution

        # Check domain distribution
        assert len(distribution["domains"]) == 3
        assert all(
            count == 120 for count in distribution["domains"].values()
        )  # 40 × 3 years

        # Check year distribution
        assert len(distribution["years"]) == 3
        assert all(
            count == 120 for count in distribution["years"].values()
        )  # 40 × 3 domains

        assert distribution["is_balanced"] is True

    def test_generate_qa_report(self, qa_system, sample_extraction_results):
        """Test generating comprehensive QA report."""
        qa_report = qa_system.generate_qa_report(sample_extraction_results)

        assert isinstance(qa_report, ExtractionQA)
        assert qa_report.total_papers == 360  # 40 × 3 domains × 3 years
        assert qa_report.successfully_extracted == 360

        # Check confidence distribution
        assert qa_report.high_confidence > 0
        assert qa_report.medium_confidence > 0
        assert qa_report.low_confidence >= 0
        assert (
            qa_report.high_confidence
            + qa_report.medium_confidence
            + qa_report.low_confidence
            == qa_report.successfully_extracted
        )

        # Check domain distribution
        assert sum(qa_report.domain_distribution.values()) == qa_report.total_papers
        assert all(count == 120 for count in qa_report.domain_distribution.values())

        # Check year distribution
        assert sum(qa_report.year_distribution.values()) == qa_report.total_papers

    def test_extraction_rate_validation(self, qa_system):
        """Test validation of extraction success rate."""
        # Good extraction rate
        good_results = [
            ExtractionBatch(
                domain=BenchmarkDomain.NLP,
                year=2023,
                papers=[create_mock_paper() for _ in range(100)],
                total_extracted=85,  # 85% extraction rate
                high_confidence_count=60,
                requires_manual_review=[],
            )
        ]

        stats = qa_system.calculate_extraction_stats(good_results)
        assert stats["extraction_rate"] >= qa_system.min_extraction_rate

        # Poor extraction rate
        poor_results = [
            ExtractionBatch(
                domain=BenchmarkDomain.CV,
                year=2023,
                papers=[create_mock_paper() for _ in range(100)],
                total_extracted=50,  # 50% extraction rate
                high_confidence_count=30,
                requires_manual_review=list(range(50)),
            )
        ]

        stats = qa_system.calculate_extraction_stats(poor_results)
        assert stats["extraction_rate"] < qa_system.min_extraction_rate

    def test_high_confidence_rate_validation(self, qa_system):
        """Test validation of high confidence extraction rate."""
        results = [
            ExtractionBatch(
                domain=BenchmarkDomain.RL,
                year=2023,
                papers=[create_mock_paper() for _ in range(100)],
                total_extracted=100,
                high_confidence_count=65,  # 65% high confidence
                requires_manual_review=list(range(35)),
            )
        ]

        stats = qa_system.calculate_extraction_stats(results)
        assert stats["high_confidence_rate"] >= qa_system.min_high_confidence_rate

    def test_unbalanced_distribution_detection(self, qa_system):
        """Test detection of unbalanced extraction distribution."""
        # Create unbalanced results - too many NLP, too few RL
        unbalanced_results = []

        # Add many NLP papers
        for year in [2022, 2023]:
            batch = ExtractionBatch(
                domain=BenchmarkDomain.NLP,
                year=year,
                papers=[create_mock_paper() for _ in range(100)],
                total_extracted=100,
                high_confidence_count=80,
                requires_manual_review=[],
            )
            unbalanced_results.append(batch)

        # Add few RL papers
        batch = ExtractionBatch(
            domain=BenchmarkDomain.RL,
            year=2023,
            papers=[create_mock_paper() for _ in range(10)],
            total_extracted=10,
            high_confidence_count=8,
            requires_manual_review=[],
        )
        unbalanced_results.append(batch)

        distribution = qa_system.validate_distribution(unbalanced_results)
        assert distribution["is_balanced"] is False

    def test_missing_year_coverage(self, qa_system):
        """Test detection of missing year coverage."""
        # Results missing years 2019-2021
        partial_results = []

        for domain in [BenchmarkDomain.NLP, BenchmarkDomain.CV, BenchmarkDomain.RL]:
            for year in [2022, 2023, 2024]:  # Missing 2019-2021
                batch = ExtractionBatch(
                    domain=domain,
                    year=year,
                    papers=[create_mock_paper() for _ in range(30)],
                    total_extracted=30,
                    high_confidence_count=20,
                    requires_manual_review=[],
                )
                partial_results.append(batch)

        qa_system.validate_coverage(partial_results)
        qa_report = qa_system.generate_qa_report(partial_results)

        # Should detect missing years
        assert 2019 not in qa_report.year_distribution
        assert 2020 not in qa_report.year_distribution
        assert 2021 not in qa_report.year_distribution

    def test_quality_metrics_calculation(self, qa_system, sample_extraction_results):
        """Test calculation of various quality metrics."""
        metrics = qa_system.calculate_quality_metrics(sample_extraction_results)

        assert "extraction_rate" in metrics
        assert "high_confidence_rate" in metrics
        assert "manual_review_rate" in metrics
        assert "sota_paper_count" in metrics
        assert "avg_confidence_score" in metrics

        assert 0 <= metrics["extraction_rate"] <= 1
        assert 0 <= metrics["high_confidence_rate"] <= 1
        assert 0 <= metrics["manual_review_rate"] <= 1
        assert metrics["sota_paper_count"] > 0
        assert 0 <= metrics["avg_confidence_score"] <= 1
