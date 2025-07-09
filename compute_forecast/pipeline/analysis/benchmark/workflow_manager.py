"""Extraction workflow manager for parallel processing."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from typing import Dict, List, Tuple
from collections import defaultdict

from compute_forecast.pipeline.analysis.benchmark.models import (
    BenchmarkDomain,
    ExtractionBatch,
)
from compute_forecast.pipeline.analysis.benchmark.extractor import (
    AcademicBenchmarkExtractor,
)
from compute_forecast.pipeline.analysis.benchmark.domain_extractors import (
    NLPBenchmarkExtractor,
    CVBenchmarkExtractor,
    RLBenchmarkExtractor,
)
from compute_forecast.pipeline.metadata_collection.models import Paper


class ExtractionWorkflowManager:
    """Manage the extraction workflow for all papers."""

    def __init__(self):
        self.domains = [BenchmarkDomain.NLP, BenchmarkDomain.CV, BenchmarkDomain.RL]
        self.years = [2019, 2020, 2021, 2022, 2023, 2024]
        self.extractors = {
            BenchmarkDomain.NLP: NLPBenchmarkExtractor(),
            BenchmarkDomain.CV: CVBenchmarkExtractor(),
            BenchmarkDomain.RL: RLBenchmarkExtractor(),
        }
        self.base_extractor = AcademicBenchmarkExtractor()

    def plan_extraction(self, all_papers: List[Paper]) -> Dict[str, List[Paper]]:
        """Plan extraction batches by domain and year."""
        batches = defaultdict(list)

        for paper in all_papers:
            domain = self.detect_domain(paper)
            domain_key = domain.value
            year_key = f"{domain_key}_{paper.year}"
            batches[year_key].append(paper)

        return dict(batches)

    def detect_domain(self, paper: Paper) -> BenchmarkDomain:
        """Detect domain from paper content."""
        text = f"{paper.title} {paper.abstract}".lower()

        # NLP keywords
        nlp_keywords = [
            "natural language",
            "nlp",
            "language model",
            "bert",
            "gpt",
            "transformer",
            "text",
            "sentiment",
            "translation",
            "tokeniz",
            "word",
            "sentence",
            "corpus",
            "vocabulary",
            "semantic",
        ]

        # CV keywords
        cv_keywords = [
            "computer vision",
            "image",
            "visual",
            "convolutional",
            "cnn",
            "resnet",
            "efficientnet",
            "yolo",
            "detection",
            "segmentation",
            "classification",
            "pixel",
            "convolution",
            "imagenet",
            "coco",
        ]

        # RL keywords
        rl_keywords = [
            "reinforcement learning",
            "rl",
            "agent",
            "environment",
            "reward",
            "policy",
            "q-learning",
            "dqn",
            "actor-critic",
            "atari",
            "mujoco",
            "game",
            "simulation",
            "episode",
            "action",
            "state",
        ]

        nlp_score = sum(1 for kw in nlp_keywords if kw in text)
        cv_score = sum(1 for kw in cv_keywords if kw in text)
        rl_score = sum(1 for kw in rl_keywords if kw in text)

        if nlp_score >= cv_score and nlp_score >= rl_score:
            return BenchmarkDomain.NLP
        elif cv_score >= rl_score:
            return BenchmarkDomain.CV
        else:
            return BenchmarkDomain.RL

    def execute_parallel_extraction(
        self, batches: Dict[str, List[Paper]]
    ) -> List[ExtractionBatch]:
        """Execute extraction in parallel."""
        results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit extraction jobs
            future_to_batch = {}
            for batch_key, papers in batches.items():
                # Split from the right to handle multi-word domains
                parts = batch_key.rsplit("_", 1)
                domain_str, year_str = parts
                domain = BenchmarkDomain(domain_str)

                future = executor.submit(
                    self.base_extractor.extract_benchmark_batch, papers, domain
                )
                future_to_batch[future] = (batch_key, domain, papers)

            # Collect results
            for future in as_completed(future_to_batch):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Extraction failed for batch: {e}")
                    continue

        return results

    def generate_extraction_report(
        self, results: List[ExtractionBatch]
    ) -> pd.DataFrame:
        """Generate summary report of extractions."""
        report_data = []

        # Aggregate by domain and year
        aggregated: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(
            lambda: {
                "total_extracted": 0,
                "high_confidence_count": 0,
                "manual_review_count": 0,
            }
        )

        for batch in results:
            key = (batch.domain.value, batch.year)
            aggregated[key]["total_extracted"] += batch.total_extracted
            aggregated[key]["high_confidence_count"] += batch.high_confidence_count
            aggregated[key]["manual_review_count"] += len(batch.requires_manual_review)

        # Convert to DataFrame
        for (domain, year), data in aggregated.items():
            report_data.append({"domain": domain, "year": year, **data})

        return pd.DataFrame(report_data)

    def identify_manual_review_candidates(
        self, results: List[ExtractionBatch]
    ) -> List[Paper]:
        """Papers requiring manual review."""
        papers = []
        for batch in results:
            for paper in batch.papers:
                if paper.paper.paper_id in batch.requires_manual_review:
                    papers.append(paper.paper)
        return papers
