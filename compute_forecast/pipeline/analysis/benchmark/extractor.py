"""Academic benchmark extractor for computational requirements."""

import re
from typing import Dict, List, Any, Set

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.analysis.computational.analyzer import (
    ComputationalAnalyzer,
)
from compute_forecast.pipeline.analysis.benchmark.models import (
    BenchmarkDomain,
    BenchmarkPaper,
    ExtractionBatch,
)


class AcademicBenchmarkExtractor:
    """Extract computational requirements from academic papers."""

    def __init__(self):
        self.analyzer = ComputationalAnalyzer()
        self.min_papers_per_domain_year = 20
        self.max_papers_per_domain_year = 40
        self.confidence_threshold = 0.7

        # SOTA detection patterns
        self.sota_patterns = [
            r"state[- ]of[- ]the[- ]art",
            r"sota",
            r"new\s+record",
            r"surpass(?:es|ed)?\s+previous",
            r"outperform(?:s|ed)?",
            r"best\s+performance",
            r"achieve(?:s|d)?\s+new",
            r"superior\s+to\s+existing",
            r"achieving\s+sota",
        ]

        # Landmark papers that are implicitly SOTA
        self.landmark_papers = [
            "bert",
            "gpt",
            "transformer",
            "resnet",
            "efficientnet",
            "yolo",
            "vit",
            "vision transformer",
            "alphago",
            "alphafold",
        ]

    def extract_benchmark_batch(
        self, papers: List[Paper], domain: BenchmarkDomain
    ) -> ExtractionBatch:
        """Process batch of papers for a domain."""
        extracted_papers = []
        high_confidence_count = 0
        manual_review_ids: List[str] = []

        # Identify SOTA papers
        sota_paper_ids = self.identify_sota_papers(papers)

        for paper in papers:
            # Analyze computational requirements
            comp_analysis = self.analyzer.analyze_paper(paper)

            # Extract computational details
            comp_details = self.extract_computational_details(paper)

            # Validate extraction
            validation_score = self.validate_extraction(comp_details, paper)

            # Determine confidence
            # If we have resource metrics from the analyzer, use its confidence
            # Otherwise use the validation score
            if comp_analysis.resource_metrics and any(
                comp_analysis.resource_metrics.values()
            ):
                confidence = comp_analysis.confidence_score
            else:
                confidence = min(comp_analysis.confidence_score, validation_score)

            # Create benchmark paper
            benchmark_paper = BenchmarkPaper(
                paper=paper,
                domain=domain,
                is_sota=(paper.paper_id in sota_paper_ids),
                benchmark_datasets=self._extract_benchmark_datasets(paper, domain),
                computational_requirements=comp_analysis,
                extraction_confidence=confidence,
                manual_verification=False,
            )

            extracted_papers.append(benchmark_paper)

            if confidence >= self.confidence_threshold:
                high_confidence_count += 1
            else:
                if paper.paper_id:
                    manual_review_ids.append(paper.paper_id)

        # Determine year from papers
        year = papers[0].year if papers else 2023

        return ExtractionBatch(
            domain=domain,
            year=year,
            papers=extracted_papers,
            total_extracted=len(extracted_papers),
            high_confidence_count=high_confidence_count,
            requires_manual_review=manual_review_ids,
        )

    def identify_sota_papers(self, papers: List[Paper]) -> Set[str]:
        """Identify state-of-the-art papers using citations and keywords."""
        sota_ids = set()

        for paper in papers:
            # Check title and abstract for SOTA indicators
            abstract_text = paper.get_best_abstract() if paper.abstracts else ""
            text_to_check = f"{paper.title} {abstract_text}".lower()

            # Check for explicit SOTA patterns
            for pattern in self.sota_patterns:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    if paper.paper_id:
                        sota_ids.add(paper.paper_id)
                    break

            # Check for landmark papers
            for landmark in self.landmark_papers:
                if landmark in text_to_check:
                    if paper.paper_id:
                        sota_ids.add(paper.paper_id)
                    break

            # Also check if paper has high citation count relative to year
            citations_count = paper.get_latest_citations_count()
            if citations_count > 0:
                years_since_pub = 2024 - paper.year
                if years_since_pub > 0:
                    citations_per_year = citations_count / years_since_pub
                    if citations_per_year > 50:  # Threshold for high impact
                        if paper.paper_id:
                            sota_ids.add(paper.paper_id)

        return sota_ids

    def extract_computational_details(self, paper: Paper) -> Dict[str, Any]:
        """Extract detailed computational requirements."""
        details: Dict[str, Any] = {
            "gpu_hours": None,
            "gpu_type": None,
            "gpu_count": None,
            "training_time_days": None,
            "parameters": None,
            "dataset_size": None,
            "batch_size": None,
            "memory_gb": None,
            "frameworks": [],
        }

        # Get full text to analyze
        abstract_text = paper.get_best_abstract() if paper.abstracts else ""
        text = getattr(paper, "full_text", "") or abstract_text

        # Extract GPU information
        gpu_pattern = r"(\d+)\s*(?:x\s*)?([VATH]\d{2,3}|TPU|GPU)"
        gpu_matches = re.findall(gpu_pattern, text, re.IGNORECASE)
        if gpu_matches:
            details["gpu_count"] = int(gpu_matches[0][0])
            details["gpu_type"] = gpu_matches[0][1].upper()

        # Extract training time
        time_patterns = [
            r"train(?:ed|ing)?\s+(?:for\s+)?(\d+\.?\d*)\s*days?",
            r"(\d+\.?\d*)\s*days?\s+of\s+train(?:ing)?",
            r"(\d+)\s*hours?\s+(?:of\s+)?train(?:ing)?",
        ]

        for pattern in time_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                value = float(matches.group(1))
                if "hour" in pattern:
                    details["training_time_days"] = value / 24
                else:
                    details["training_time_days"] = value
                break

        # Extract parameters
        param_pattern = r"(\d+\.?\d*)\s*([BMK])?\s*(?:parameters|params)"
        param_match = re.search(param_pattern, text, re.IGNORECASE)
        if param_match:
            value = float(param_match.group(1))
            unit = param_match.group(2)
            if unit:
                if unit.upper() == "B":
                    value *= 1_000_000_000
                elif unit.upper() == "M":
                    value *= 1_000_000
                elif unit.upper() == "K":
                    value *= 1_000
            details["parameters"] = int(value)

        # Extract memory requirements
        memory_pattern = r"(\d+)\s*GB?\s*(?:of\s+)?(?:memory|RAM|VRAM)"
        memory_match = re.search(memory_pattern, text, re.IGNORECASE)
        if memory_match:
            details["memory_gb"] = float(memory_match.group(1))

        # Extract frameworks
        frameworks = ["PyTorch", "TensorFlow", "JAX", "Transformers", "Keras", "MXNet"]
        for fw in frameworks:
            if fw.lower() in text.lower():
                details["frameworks"].append(fw)

        # Calculate GPU hours if we have the components
        if details["gpu_count"] and details["training_time_days"]:
            details["gpu_hours"] = (
                details["gpu_count"] * details["training_time_days"] * 24
            )

        return details

    def validate_extraction(self, extraction: Dict[str, Any], paper: Paper) -> float:
        """Validate extraction makes sense for paper context."""
        score = 1.0

        # Check if GPU type is reasonable for the year
        if extraction.get("gpu_type") and paper.year:
            gpu_year_map = {
                "V100": 2017,
                "A100": 2020,
                "H100": 2022,
                "TPU": 2016,
            }

            gpu_type = extraction["gpu_type"]
            for gpu, intro_year in gpu_year_map.items():
                if gpu in gpu_type and paper.year < intro_year:
                    score *= 0.3  # Heavily penalize anachronistic GPUs

        # Check if parameters are reasonable
        if extraction.get("parameters"):
            params = extraction["parameters"]

            # Year-based reasonable parameter counts
            if paper.year <= 2018 and params > 1_000_000_000:  # 1B
                score *= 0.7
            elif paper.year <= 2020 and params > 10_000_000_000:  # 10B
                score *= 0.6
            elif paper.year <= 2022 and params > 100_000_000_000:  # 100B
                score *= 0.7
            elif params > 1_000_000_000_000:  # 1T
                score *= 0.8

        # Check if GPU hours are reasonable
        if extraction.get("gpu_hours"):
            hours = extraction["gpu_hours"]

            # Extremely high GPU hours are suspicious
            if hours > 1_000_000:  # 1M GPU hours
                score *= 0.5
            elif hours > 100_000:  # 100K GPU hours
                score *= 0.8

        # Check if we have at least some computational information
        has_compute_info = any(
            [
                extraction.get("gpu_hours"),
                extraction.get("gpu_count"),
                extraction.get("training_time_days"),
                extraction.get("parameters"),
            ]
        )

        if not has_compute_info:
            score *= 0.3

        return min(max(score, 0.0), 1.0)

    def _extract_benchmark_datasets(
        self, paper: Paper, domain: BenchmarkDomain
    ) -> List[str]:
        """Extract benchmark datasets mentioned in the paper."""
        datasets = []
        abstract_text = paper.get_best_abstract() if paper.abstracts else ""
        text = f"{paper.title} {abstract_text}".lower()

        # Domain-specific dataset patterns
        domain_datasets = {
            BenchmarkDomain.NLP: ["glue", "superglue", "squad", "wmt", "commoncrawl"],
            BenchmarkDomain.CV: ["imagenet", "coco", "cifar", "ade20k", "kinetics"],
            BenchmarkDomain.RL: ["atari", "mujoco", "openai gym", "starcraft", "dota"],
            BenchmarkDomain.GENERAL: [],
        }

        # Check for dataset mentions
        if domain in domain_datasets:
            for dataset in domain_datasets[domain]:
                if dataset in text:
                    datasets.append(
                        dataset.upper() if len(dataset) <= 4 else dataset.title()
                    )

        return datasets
