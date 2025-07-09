"""Tests for extraction workflow manager."""

import pytest
from unittest.mock import patch
import pandas as pd

from compute_forecast.pipeline.analysis.benchmark.workflow_manager import (
    ExtractionWorkflowManager,
)
from compute_forecast.pipeline.analysis.benchmark.models import (
    BenchmarkDomain,
    ExtractionBatch,
    BenchmarkPaper,
)
from compute_forecast.pipeline.analysis.benchmark.extractor import (
    AcademicBenchmarkExtractor,
)
from compute_forecast.pipeline.analysis.benchmark.domain_extractors import (
    NLPBenchmarkExtractor,
)
from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    Author,
)


class TestExtractionWorkflowManager:
    """Test the extraction workflow manager."""

    @pytest.fixture
    def sample_papers(self):
        """Create a diverse set of sample papers."""
        papers = []
        domains = ["NLP", "Computer Vision", "Reinforcement Learning"]
        years = [2019, 2020, 2021, 2022, 2023, 2024]

        paper_id = 0
        for year in years:
            for domain in domains:
                for i in range(3):  # 3 papers per domain per year
                    paper = Paper(
                        paper_id=f"paper_{paper_id}",
                        title=f"{domain} Paper {i} - {year}",
                        year=year,
                        venue="NeurIPS" if domain == "NLP" else "ICML",
                        authors=[Author(name=f"Author {paper_id}")],
                        citations=i * 50,  # Add required citations field
                        abstract=f"Research in {domain} using deep learning",
                    )
                    papers.append(paper)
                    paper_id += 1

        return papers

    @pytest.fixture
    def workflow_manager(self):
        """Create a workflow manager instance."""
        return ExtractionWorkflowManager()

    def test_workflow_manager_initialization(self, workflow_manager):
        """Test workflow manager initializes correctly."""
        assert workflow_manager.domains == [
            BenchmarkDomain.NLP,
            BenchmarkDomain.CV,
            BenchmarkDomain.RL,
        ]
        assert workflow_manager.years == [2019, 2020, 2021, 2022, 2023, 2024]
        assert len(workflow_manager.extractors) == 3
        assert isinstance(
            workflow_manager.extractors[BenchmarkDomain.NLP], NLPBenchmarkExtractor
        )

    def test_plan_extraction(self, workflow_manager, sample_papers):
        """Test planning extraction batches."""
        batches = workflow_manager.plan_extraction(sample_papers)

        # Should have batches for each domain-year combination
        assert len(batches) > 0

        # Check batch keys follow expected format
        for key in batches:
            assert "_" in key  # Format: "domain_year"
            # Split from the right to handle multi-word domains
            parts = key.rsplit("_", 1)
            assert len(parts) == 2
            domain_str, year_str = parts
            assert domain_str in ["nlp", "computer_vision", "reinforcement_learning"]
            assert int(year_str) in workflow_manager.years

        # Check papers are properly distributed
        total_papers_in_batches = sum(len(papers) for papers in batches.values())
        assert total_papers_in_batches == len(sample_papers)

    def test_execute_parallel_extraction(self, workflow_manager, sample_papers):
        """Test parallel extraction execution."""
        batches = workflow_manager.plan_extraction(sample_papers)

        # Mock the base extractor to return test results
        with patch.object(
            AcademicBenchmarkExtractor, "extract_benchmark_batch"
        ) as mock_extract:

            def create_mock_batch(papers, domain):
                return ExtractionBatch(
                    domain=domain,
                    year=papers[0].year if papers else 2023,
                    papers=[
                        BenchmarkPaper(
                            paper=p,
                            domain=domain,
                            is_sota=False,
                            benchmark_datasets=["Test"],
                            computational_requirements=ComputationalAnalysis(
                                computational_richness=0.8,
                                keyword_matches={"gpu": 1},
                                resource_metrics={"gpu_hours": 100.0},
                                experimental_indicators={"has_ablation": True},
                                confidence_score=0.8,
                            ),
                            extraction_confidence=0.8,
                        )
                        for p in papers
                    ],
                    total_extracted=len(papers),
                    high_confidence_count=len(papers) - 1,
                    requires_manual_review=[],
                )

            mock_extract.side_effect = create_mock_batch

            results = workflow_manager.execute_parallel_extraction(batches)

        assert len(results) == len(batches)
        assert all(isinstance(r, ExtractionBatch) for r in results)

    def test_generate_extraction_report(self, workflow_manager):
        """Test generating extraction summary report."""
        # Create mock extraction results
        results = []
        for domain in workflow_manager.domains:
            for year in [2023, 2024]:
                batch = ExtractionBatch(
                    domain=domain,
                    year=year,
                    papers=[],  # Empty for this test
                    total_extracted=20,
                    high_confidence_count=15,
                    requires_manual_review=["paper_1", "paper_2"],
                )
                results.append(batch)

        report_df = workflow_manager.generate_extraction_report(results)

        assert isinstance(report_df, pd.DataFrame)
        assert len(report_df) == 6  # 3 domains × 2 years
        assert "domain" in report_df.columns
        assert "year" in report_df.columns
        assert "total_extracted" in report_df.columns
        assert "high_confidence_count" in report_df.columns
        assert "manual_review_count" in report_df.columns

    def test_identify_manual_review_candidates(self, workflow_manager):
        """Test identifying papers requiring manual review."""
        # Create mock papers and batches
        papers_needing_review = []
        results = []

        for i in range(3):
            paper = Paper(
                paper_id=f"review_{i}",
                title=f"Paper needing review {i}",
                year=2023,
                venue="ICML",
                authors=[Author(name=f"Author {i}")],
                citations=10,
            )
            papers_needing_review.append(paper)

            batch_papers = [
                BenchmarkPaper(
                    paper=paper,
                    domain=BenchmarkDomain.NLP,
                    is_sota=False,
                    benchmark_datasets=[],
                    computational_requirements=ComputationalAnalysis(
                        computational_richness=0.4,
                        keyword_matches={},
                        resource_metrics={},
                        experimental_indicators={},
                        confidence_score=0.4,
                    ),
                    extraction_confidence=0.4,
                )
            ]

            batch = ExtractionBatch(
                domain=BenchmarkDomain.NLP,
                year=2023,
                papers=batch_papers,
                total_extracted=1,
                high_confidence_count=0,
                requires_manual_review=[paper.paper_id],
            )
            results.append(batch)

        candidates = workflow_manager.identify_manual_review_candidates(results)

        assert len(candidates) == 3
        assert all(p.paper_id.startswith("review_") for p in candidates)

    def test_parallel_extraction_error_handling(self, workflow_manager):
        """Test error handling in parallel extraction."""
        batches = {
            "nlp_2023": [
                Paper(
                    paper_id="1",
                    title="Test",
                    year=2023,
                    venue="ACL",
                    authors=[Author(name="A")],
                    citations=10,
                )
            ],
            "computer_vision_2023": [
                Paper(
                    paper_id="2",
                    title="Test2",
                    year=2023,
                    venue="CVPR",
                    authors=[Author(name="B")],
                    citations=10,
                )
            ],
        }

        with patch.object(
            AcademicBenchmarkExtractor, "extract_benchmark_batch"
        ) as mock_extract:
            # Make one extraction fail
            def side_effect(papers, domain):
                if domain == BenchmarkDomain.NLP:
                    raise Exception("Extraction failed")
                return ExtractionBatch(
                    domain=domain,
                    year=2023,
                    papers=[],
                    total_extracted=1,
                    high_confidence_count=1,
                    requires_manual_review=[],
                )

            mock_extract.side_effect = side_effect

            results = workflow_manager.execute_parallel_extraction(batches)

        # Should still get results for successful extractions
        assert len(results) >= 1
        assert any(r.domain == BenchmarkDomain.CV for r in results)

    def test_domain_detection_from_paper(self, workflow_manager):
        """Test detecting domain from paper content."""
        nlp_paper = Paper(
            paper_id="nlp_test",
            title="BERT for Natural Language Understanding",
            year=2023,
            venue="ACL",
            authors=[Author(name="NLP Researcher")],
            citations=100,
            abstract="We present improvements to transformer models for NLP tasks.",
        )

        cv_paper = Paper(
            paper_id="cv_test",
            title="Vision Transformer for Image Classification",
            year=2023,
            venue="CVPR",
            authors=[Author(name="CV Researcher")],
            citations=150,
            abstract="We apply transformers to computer vision and image recognition.",
        )

        rl_paper = Paper(
            paper_id="rl_test",
            title="Deep Reinforcement Learning for Atari Games",
            year=2023,
            venue="ICML",
            authors=[Author(name="RL Researcher")],
            citations=80,
            abstract="We train agents using reinforcement learning on Atari environments.",
        )

        nlp_domain = workflow_manager.detect_domain(nlp_paper)
        cv_domain = workflow_manager.detect_domain(cv_paper)
        rl_domain = workflow_manager.detect_domain(rl_paper)

        assert nlp_domain == BenchmarkDomain.NLP
        assert cv_domain == BenchmarkDomain.CV
        assert rl_domain == BenchmarkDomain.RL

    def test_extraction_report_aggregation(self, workflow_manager):
        """Test that extraction report properly aggregates statistics."""
        results = []

        # Create multiple batches for same domain/year
        for i in range(3):
            batch = ExtractionBatch(
                domain=BenchmarkDomain.NLP,
                year=2023,
                papers=[],
                total_extracted=10,
                high_confidence_count=8,
                requires_manual_review=["p1", "p2"],
            )
            results.append(batch)

        report_df = workflow_manager.generate_extraction_report(results)

        # Should aggregate the 3 batches into one row
        nlp_2023 = report_df[
            (report_df["domain"] == "nlp") & (report_df["year"] == 2023)
        ]
        assert len(nlp_2023) == 1
        assert nlp_2023.iloc[0]["total_extracted"] == 30  # 3 × 10
        assert nlp_2023.iloc[0]["high_confidence_count"] == 24  # 3 × 8
