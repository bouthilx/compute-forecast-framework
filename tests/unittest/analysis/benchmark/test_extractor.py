"""Tests for academic benchmark extractor."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.analysis.benchmark.extractor import AcademicBenchmarkExtractor
from compute_forecast.analysis.benchmark.models import (
    BenchmarkDomain,
    BenchmarkPaper,
    ExtractionBatch,
)
from compute_forecast.data.models import Paper, ComputationalAnalysis, Author


class TestAcademicBenchmarkExtractor:
    """Test the main benchmark extraction functionality."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock computational analyzer."""
        analyzer = Mock()
        analyzer.analyze_paper = Mock()
        analyzer.analyze_paper.return_value = ComputationalAnalysis(
            computational_richness=0.85,
            keyword_matches={"gpu": 5, "training": 3, "deep learning": 2},
            resource_metrics={
                "gpu_hours": 100.0,
                "gpu_type": "V100",
                "gpu_count": 4,
                "training_time_days": 2.0,
                "parameters": 350_000_000,
            },
            experimental_indicators={"has_experiments": True, "has_results": True},
            confidence_score=0.85,
        )
        return analyzer

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        papers = []
        for i in range(5):
            paper = Paper(
                paper_id=f"paper_{i}",
                title=f"Deep Learning Paper {i}",
                year=2023,
                venue="NeurIPS",
                authors=[Author(name=f"Author {i}")],
                citations=10 + i * 5,
                abstract="Training neural networks on large datasets...",
            )
            papers.append(paper)
        return papers

    @pytest.fixture
    def extractor(self, mock_analyzer):
        """Create an extractor instance with mocked analyzer."""
        with patch(
            "compute_forecast.analysis.benchmark.extractor.ComputationalAnalyzer"
        ) as mock_cls:
            mock_cls.return_value = mock_analyzer
            return AcademicBenchmarkExtractor()

    def test_extractor_initialization(self, extractor):
        """Test extractor initializes with correct defaults."""
        assert extractor.min_papers_per_domain_year == 20
        assert extractor.max_papers_per_domain_year == 40
        assert extractor.confidence_threshold == 0.7
        assert extractor.analyzer is not None

    def test_extract_benchmark_batch(self, extractor, sample_papers):
        """Test extracting a batch of papers."""
        batch = extractor.extract_benchmark_batch(sample_papers, BenchmarkDomain.NLP)

        assert isinstance(batch, ExtractionBatch)
        assert batch.domain == BenchmarkDomain.NLP
        assert batch.total_extracted == 5
        assert len(batch.papers) == 5
        assert all(isinstance(p, BenchmarkPaper) for p in batch.papers)

    def test_identify_sota_papers(self, extractor, sample_papers):
        """Test identifying state-of-the-art papers."""
        # Add SOTA indicators to some papers
        sample_papers[0].title = "BERT: Pre-training of Deep Bidirectional Transformers"
        sample_papers[1].abstract = "We achieve new state-of-the-art results on GLUE"
        sample_papers[2].title = "Achieving SOTA Performance on ImageNet"

        sota_ids = extractor.identify_sota_papers(sample_papers)

        assert len(sota_ids) >= 2
        assert "paper_0" in sota_ids
        assert "paper_1" in sota_ids

    def test_extract_computational_details(self, extractor, sample_papers):
        """Test extracting computational details from a paper."""
        paper = sample_papers[0]
        paper.full_text = """
        We trained our model on 8 V100 GPUs for 14 days.
        The model has 350M parameters and was trained on 1TB of text data.
        Training used a batch size of 512 and required 32GB of memory per GPU.
        We used PyTorch and Transformers library for implementation.
        """

        details = extractor.extract_computational_details(paper)

        assert "gpu_hours" in details
        assert "gpu_type" in details
        assert "gpu_count" in details
        assert "training_time_days" in details
        assert "parameters" in details
        assert "memory_gb" in details
        assert "frameworks" in details

    def test_validate_extraction(self, extractor, sample_papers):
        """Test validation of extracted computational details."""
        paper = sample_papers[0]
        paper.year = 2020

        # Valid extraction
        valid_extraction = {
            "gpu_hours": 1000.0,
            "gpu_type": "V100",
            "gpu_count": 8,
            "parameters": 350_000_000,
        }
        score = extractor.validate_extraction(valid_extraction, paper)
        assert score > 0.7

        # Invalid extraction (too many resources for 2020)
        invalid_extraction = {
            "gpu_hours": 1_000_000.0,  # Unrealistic
            "gpu_type": "H100",  # Didn't exist in 2020
            "gpu_count": 1000,  # Too many
            "parameters": 1_000_000_000_000,  # 1 trillion params in 2020
        }
        score = extractor.validate_extraction(invalid_extraction, paper)
        assert score < 0.5

    def test_batch_high_confidence_count(self, extractor, sample_papers):
        """Test counting high confidence extractions."""
        # Mock different confidence scores
        confidence_scores = [0.9, 0.8, 0.6, 0.75, 0.5]

        with patch.object(extractor.analyzer, "analyze_paper") as mock_analyze:
            # Create side_effect list for sequential calls
            mock_analyze.side_effect = [
                ComputationalAnalysis(
                    computational_richness=conf,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": 100.0},
                    experimental_indicators={},
                    confidence_score=conf,
                )
                for conf in confidence_scores
            ]

            batch = extractor.extract_benchmark_batch(sample_papers, BenchmarkDomain.CV)

        # Papers with confidence >= 0.7
        assert batch.high_confidence_count == 3

    def test_manual_review_identification(self, extractor, sample_papers):
        """Test identifying papers that need manual review."""
        # Mock low confidence extractions
        with patch.object(extractor.analyzer, "analyze_paper") as mock_analyze:
            mock_analyze.side_effect = [
                ComputationalAnalysis(
                    computational_richness=0.9,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": 100.0},
                    experimental_indicators={},
                    confidence_score=0.9,
                ),
                ComputationalAnalysis(
                    computational_richness=0.4,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": None},
                    experimental_indicators={},
                    confidence_score=0.4,
                ),  # Low confidence
                ComputationalAnalysis(
                    computational_richness=0.6,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": 50.0},
                    experimental_indicators={},
                    confidence_score=0.6,
                ),  # Below threshold
                ComputationalAnalysis(
                    computational_richness=0.8,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": 200.0},
                    experimental_indicators={},
                    confidence_score=0.8,
                ),
                ComputationalAnalysis(
                    computational_richness=0.3,
                    keyword_matches={},
                    resource_metrics={"gpu_hours": None},
                    experimental_indicators={},
                    confidence_score=0.3,
                ),  # Very low
            ]

            batch = extractor.extract_benchmark_batch(sample_papers, BenchmarkDomain.RL)

        assert len(batch.requires_manual_review) == 3
        assert "paper_1" in batch.requires_manual_review
        assert "paper_2" in batch.requires_manual_review
        assert "paper_4" in batch.requires_manual_review

    def test_extract_with_missing_computational_data(self, extractor):
        """Test extraction when computational data is missing."""
        paper = Paper(
            paper_id="minimal_paper",
            title="Theoretical Analysis of Neural Networks",
            year=2022,
            venue="COLT",
            authors=[Author(name="Theorist")],
            citations=5,
            abstract="We provide theoretical bounds for neural network convergence.",
        )

        with patch.object(extractor.analyzer, "analyze_paper") as mock_analyze:
            mock_analyze.return_value = ComputationalAnalysis(
                computational_richness=0.2,
                keyword_matches={},
                resource_metrics={"gpu_hours": None, "gpu_type": None},
                experimental_indicators={},
                confidence_score=0.2,
            )

            batch = extractor.extract_benchmark_batch([paper], BenchmarkDomain.GENERAL)

        assert batch.total_extracted == 1
        assert batch.high_confidence_count == 0
        assert "minimal_paper" in batch.requires_manual_review
