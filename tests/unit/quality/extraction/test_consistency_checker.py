"""
Tests for ExtractionConsistencyChecker.
"""

import numpy as np
from datetime import datetime

from compute_forecast.pipeline.content_extraction.quality.consistency_checker import (
    ExtractionConsistencyChecker,
    ConsistencyCheck,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from .test_helpers import MockComputationalAnalysis as ComputationalAnalysis


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


class TestExtractionConsistencyChecker:
    """Test extraction consistency checking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = ExtractionConsistencyChecker()

        # Create test papers with increasing computational requirements
        self.papers = []
        for i, year in enumerate([2019, 2020, 2021, 2022, 2023]):
            paper = create_test_paper(
                paper_id=f"paper_{year}",
                title=f"Model Training {year}",
                year=year,
                authors=[],
                venue="",
                citation_count=0,
            )
            # Exponentially increasing requirements
            paper.computational_analysis = ComputationalAnalysis(
                gpu_hours=100 * (2**i),  # 100, 200, 400, 800, 1600
                parameters=1e8 * (3**i),  # 1e8, 3e8, 9e8, 27e8, 81e8
                training_time=24 * (1.5**i),  # 24, 36, 54, 81, 121.5
            )
            self.papers.append(paper)

    def test_temporal_consistency_increasing_trend(self):
        """Test temporal consistency with increasing trend."""
        # Test GPU hours (should show increasing trend)
        result = self.checker.check_temporal_consistency(self.papers, "gpu_hours")

        assert isinstance(result, ConsistencyCheck)
        assert result.check_type == "temporal"
        assert result.passed is True
        assert result.confidence >= 0.7
        assert "growth_rate" in result.details
        assert result.details["growth_rate"] > 0  # Positive growth

    def test_temporal_consistency_insufficient_data(self):
        """Test temporal consistency with insufficient data."""
        result = self.checker.check_temporal_consistency(self.papers[:2], "gpu_hours")

        assert result.passed is True
        assert result.confidence == 0.5
        assert result.details["reason"] == "insufficient_data"

    def test_temporal_consistency_with_outlier(self):
        """Test temporal consistency with outlier."""
        # Add outlier paper
        outlier_paper = create_test_paper(
            paper_id="outlier",
            title="Outlier",
            year=2022,
            authors=[],
            venue="",
            citation_count=0,
        )
        outlier_paper.computational_analysis = ComputationalAnalysis(
            gpu_hours=1000000  # Way too high
        )
        papers_with_outlier = self.papers[:4] + [outlier_paper]

        result = self.checker.check_temporal_consistency(
            papers_with_outlier, "gpu_hours"
        )

        # May still pass but with lower confidence
        assert result.confidence < 0.9

    def test_cross_paper_consistency_similar_values(self):
        """Test cross-paper consistency with similar values."""
        # Create similar papers
        similar_papers = []
        for i in range(5):
            paper = create_test_paper(
                paper_id=f"similar_{i}",
                title=f"Similar Model {i}",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            )
            paper.computational_analysis = ComputationalAnalysis(
                gpu_hours=1000 + np.random.normal(0, 50)  # Small variation
            )
            similar_papers.append(paper)

        result = self.checker.check_cross_paper_consistency(similar_papers, "gpu_hours")

        assert result.check_type == "cross_paper"
        assert result.passed is True
        assert result.confidence > 0.8
        assert result.details["consistent"] is True

    def test_cross_paper_consistency_high_variation(self):
        """Test cross-paper consistency with high variation."""
        # Create papers with high variation
        varied_papers = []
        # Use 10 papers where 3 are outliers (> 20% outliers)
        values = [100, 100, 100, 100, 100, 100, 100, 100000, 100000, 100000]
        for i, val in enumerate(values):
            paper = create_test_paper(
                paper_id=f"varied_{i}",
                title=f"Varied Model {i}",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            )
            paper.computational_analysis = ComputationalAnalysis(gpu_hours=val)
            varied_papers.append(paper)

        result = self.checker.check_cross_paper_consistency(varied_papers, "gpu_hours")

        assert result.passed is False
        assert result.confidence < 0.7  # Adjust expected confidence
        assert result.details["issue"] in ["high_variation", "too_many_outliers"]

    def test_domain_consistency_nlp(self):
        """Test domain-specific consistency for NLP."""
        nlp_paper = create_test_paper(
            paper_id="nlp_1",
            title="Transformer Language Model Training",
            year=2023,
            authors=[],
            venue="",
            citation_count=0,
        )

        # Valid NLP extraction
        valid_extraction = {
            "parameters": 1e9,  # Within NLP range
            "gpu_hours": 10000,  # Within NLP range
            "batch_size": 128,  # Within NLP range
        }
        result = self.checker.check_domain_consistency(nlp_paper, valid_extraction)

        assert result.check_type == "domain_specific"
        assert result.passed is True
        assert result.confidence > 0.7
        assert result.details["domain"] == "nlp"

    def test_domain_consistency_cv(self):
        """Test domain-specific consistency for computer vision."""
        cv_paper = create_test_paper(
            paper_id="cv_1",
            title="Image Classification with Deep CNNs",
            year=2023,
            authors=[],
            venue="",
            citation_count=0,
        )

        # CV extraction with some violations
        extraction = {
            "parameters": 1e13,  # Too large for CV
            "gpu_hours": 5000,  # OK for CV
            "batch_size": 256,  # OK for CV
        }
        result = self.checker.check_domain_consistency(cv_paper, extraction)

        assert result.details["domain"] == "cv"
        assert len(result.details["violations"]) > 0
        # Should have violation for parameters
        param_violation = next(
            v for v in result.details["violations"] if v["field"] == "parameters"
        )
        assert param_violation["severity"] == "high"

    def test_identify_outliers(self):
        """Test outlier identification."""
        # Normal distribution with outliers
        values = [10, 12, 11, 13, 10, 11, 12, 100, 11, 10]  # 100 is outlier

        outliers = self.checker.identify_outliers(values, {"field": "test"})

        assert len(outliers) > 0
        assert 7 in outliers  # Index of value 100

    def test_identify_outliers_insufficient_data(self):
        """Test outlier identification with insufficient data."""
        values = [10, 20]
        outliers = self.checker.identify_outliers(values, {"field": "test"})
        assert len(outliers) == 0

    def test_scaling_consistency_valid(self):
        """Test scaling law consistency with valid values."""
        # GPU hours ~ parameters^0.7
        parameters = 1e9
        expected_gpu_hours = (parameters**0.7) / 1e6
        gpu_hours = expected_gpu_hours * 1.2  # 20% deviation

        result = self.checker.check_scaling_consistency(gpu_hours, parameters)

        assert result.check_type == "scaling_law"
        assert result.passed is True
        assert result.confidence > 0.7

    def test_scaling_consistency_violation(self):
        """Test scaling law consistency with violation."""
        parameters = 1e9
        gpu_hours = 10  # Way too low

        result = self.checker.check_scaling_consistency(gpu_hours, parameters)

        assert result.passed is False
        assert result.confidence < 0.5
        assert result.details["issue"] == "scaling_law_violation"

    def test_determine_domain(self):
        """Test domain determination from paper title."""
        # NLP papers
        nlp_papers = [
            create_test_paper(
                paper_id="1",
                title="Transformer Language Model",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="2",
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="3",
                title="GPT-3: Language Models are Few-Shot Learners",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
        ]
        for paper in nlp_papers:
            assert self.checker._determine_domain(paper) == "nlp"

        # CV papers
        cv_papers = [
            create_test_paper(
                paper_id="4",
                title="Deep Residual Learning for Image Recognition",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="5",
                title="YOLO: Real-Time Object Detection",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="6",
                title="Vision Transformer for Image Classification",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
        ]
        for paper in cv_papers:
            assert self.checker._determine_domain(paper) == "cv"

        # RL papers
        rl_papers = [
            create_test_paper(
                paper_id="7",
                title="Deep Reinforcement Learning with Policy Gradients",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="8",
                title="PPO: Proximal Policy Optimization",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
            create_test_paper(
                paper_id="9",
                title="Multi-Agent Reinforcement Learning",
                year=2023,
                authors=[],
                venue="",
                citation_count=0,
            ),
        ]
        for paper in rl_papers:
            assert self.checker._determine_domain(paper) == "rl"

        # General papers
        general_paper = create_test_paper(
            paper_id="10",
            title="A Study of Machine Learning Algorithms",
            year=2023,
            authors=[],
            venue="",
            citation_count=0,
        )
        assert self.checker._determine_domain(general_paper) == "general"
