"""Tests for benchmark extraction data models."""

import pytest
from dataclasses import asdict
from typing import List

# Import future models
from src.analysis.benchmark.models import (
    BenchmarkDomain,
    BenchmarkPaper,
    ExtractionBatch,
    BenchmarkExport,
    ExtractionQA,
)
from src.data.models import Paper, ComputationalAnalysis, Author


class TestBenchmarkModels:
    """Test benchmark extraction data models."""

    def test_benchmark_domain_enum(self):
        """Test BenchmarkDomain enum values."""
        assert BenchmarkDomain.NLP.value == "nlp"
        assert BenchmarkDomain.CV.value == "computer_vision"
        assert BenchmarkDomain.RL.value == "reinforcement_learning"
        assert BenchmarkDomain.GENERAL.value == "general"

    def test_benchmark_paper_creation(self):
        """Test creating a BenchmarkPaper instance."""
        paper = Paper(
            paper_id="test123",
            title="Test Paper",
            year=2023,
            venue="ICML",
            authors=[Author(name="Author 1")],
            citations=50,
        )
        comp_analysis = ComputationalAnalysis(
            computational_richness=0.85,
            keyword_matches={"gpu": 5, "training": 3},
            resource_metrics={"gpu_hours": 100.0, "gpu_type": "V100"},
            experimental_indicators={"has_experiments": True},
            confidence_score=0.85,
        )

        benchmark_paper = BenchmarkPaper(
            paper=paper,
            domain=BenchmarkDomain.NLP,
            is_sota=True,
            benchmark_datasets=["GLUE", "SuperGLUE"],
            computational_requirements=comp_analysis,
            extraction_confidence=0.85,
            manual_verification=False,
        )

        assert benchmark_paper.paper.paper_id == "test123"
        assert benchmark_paper.domain == BenchmarkDomain.NLP
        assert benchmark_paper.is_sota is True
        assert len(benchmark_paper.benchmark_datasets) == 2
        assert benchmark_paper.extraction_confidence == 0.85
        assert benchmark_paper.computational_requirements.resource_metrics["gpu_hours"] == 100.0

    def test_extraction_batch_creation(self):
        """Test creating an ExtractionBatch instance."""
        papers = []
        for i in range(3):
            paper = Paper(
                paper_id=f"paper{i}",
                title=f"Paper {i}",
                year=2023,
                venue="NeurIPS",
                authors=[Author(name=f"Author {i}")],
                citations=10,
            )
            comp_analysis = ComputationalAnalysis(
                computational_richness=0.8 - (i * 0.1),
                keyword_matches={},
                resource_metrics={"gpu_hours": 50.0 * (i + 1)},
                experimental_indicators={},
                confidence_score=0.8 - (i * 0.1),
            )
            benchmark_paper = BenchmarkPaper(
                paper=paper,
                domain=BenchmarkDomain.CV,
                is_sota=False,
                benchmark_datasets=["ImageNet"],
                computational_requirements=comp_analysis,
                extraction_confidence=0.8 - (i * 0.1),
            )
            papers.append(benchmark_paper)

        batch = ExtractionBatch(
            domain=BenchmarkDomain.CV,
            year=2023,
            papers=papers,
            total_extracted=3,
            high_confidence_count=2,
            requires_manual_review=["paper2"],
        )

        assert batch.domain == BenchmarkDomain.CV
        assert batch.year == 2023
        assert len(batch.papers) == 3
        assert batch.total_extracted == 3
        assert batch.high_confidence_count == 2
        assert "paper2" in batch.requires_manual_review

    def test_benchmark_export_creation(self):
        """Test creating a BenchmarkExport instance."""
        export = BenchmarkExport(
            paper_id="test123",
            title="Test Paper",
            year=2023,
            domain=BenchmarkDomain.RL,
            venue="ICLR",
            gpu_hours=500.0,
            gpu_type="A100",
            gpu_count=8,
            training_days=7.5,
            parameters_millions=1500.0,
            dataset_size_gb=100.0,
            extraction_confidence=0.92,
            is_sota=True,
            benchmark_datasets=["Atari", "MuJoCo"],
        )

        assert export.paper_id == "test123"
        assert export.domain == BenchmarkDomain.RL
        assert export.gpu_hours == 500.0
        assert export.parameters_millions == 1500.0

    def test_benchmark_export_to_csv_row(self):
        """Test converting BenchmarkExport to CSV row."""
        export = BenchmarkExport(
            paper_id="test123",
            title="Test Paper",
            year=2023,
            domain=BenchmarkDomain.NLP,
            venue="ACL",
            gpu_hours=200.0,
            gpu_type="V100",
            gpu_count=4,
            training_days=3.0,
            parameters_millions=350.0,
            dataset_size_gb=50.0,
            extraction_confidence=0.88,
            is_sota=False,
            benchmark_datasets=["GLUE"],
        )

        csv_row = export.to_csv_row()

        assert csv_row["paper_id"] == "test123"
        assert csv_row["domain"] == "nlp"
        assert csv_row["gpu_hours"] == 200.0
        assert csv_row["benchmark_datasets"] == "GLUE"

    def test_extraction_qa_creation(self):
        """Test creating an ExtractionQA instance."""
        qa = ExtractionQA(
            total_papers=300,
            successfully_extracted=250,
            high_confidence=180,
            medium_confidence=50,
            low_confidence=20,
            manual_review_required=30,
            domain_distribution={
                BenchmarkDomain.NLP: 100,
                BenchmarkDomain.CV: 100,
                BenchmarkDomain.RL: 100,
            },
            year_distribution={
                2019: 50,
                2020: 50,
                2021: 50,
                2022: 50,
                2023: 50,
                2024: 50,
            },
        )

        assert qa.total_papers == 300
        assert qa.successfully_extracted == 250
        assert qa.high_confidence == 180
        assert sum(qa.domain_distribution.values()) == 300
        assert sum(qa.year_distribution.values()) == 300

    def test_benchmark_export_with_none_values(self):
        """Test BenchmarkExport handles None values properly in CSV export."""
        export = BenchmarkExport(
            paper_id="test456",
            title="Minimal Paper",
            year=2022,
            domain=BenchmarkDomain.GENERAL,
            venue="arXiv",
            gpu_hours=None,
            gpu_type=None,
            gpu_count=None,
            training_days=None,
            parameters_millions=None,
            dataset_size_gb=None,
            extraction_confidence=0.5,
            is_sota=False,
            benchmark_datasets=[],
        )

        csv_row = export.to_csv_row()

        assert csv_row["paper_id"] == "test456"
        assert csv_row["gpu_hours"] == ""
        assert csv_row["gpu_type"] == ""
        assert csv_row["benchmark_datasets"] == ""