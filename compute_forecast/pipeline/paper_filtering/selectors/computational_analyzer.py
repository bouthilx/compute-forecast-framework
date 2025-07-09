"""
Computational Richness Analyzer for Issue #8.
Detects and scores computational content in research papers.
"""

import re
import logging
from typing import Dict, List, Any

from ...metadata_collection.models import Paper, ComputationalAnalysis

logger = logging.getLogger(__name__)


class ComputationalAnalyzer:
    """
    Analyzes papers for computational richness using keyword analysis,
    resource metrics, and experimental indicators.
    """

    def __init__(self):
        # Computational keywords grouped by category
        self.computational_keywords = {
            "algorithms": {
                "algorithm",
                "optimization",
                "heuristic",
                "solver",
                "search",
                "greedy",
                "dynamic programming",
                "branch and bound",
                "approximation",
                "randomized",
                "online algorithm",
                "streaming",
                "parallel algorithm",
                "distributed algorithm",
                "quantum algorithm",
                "genetic algorithm",
                "evolutionary",
                "metaheuristic",
                "local search",
                "simulated annealing",
            },
            "complexity": {
                "complexity",
                "np-hard",
                "np-complete",
                "pspace",
                "polynomial",
                "exponential",
                "logarithmic",
                "linear time",
                "quadratic",
                "cubic",
                "big-o",
                "omega",
                "theta",
                "amortized",
                "worst-case",
                "average-case",
                "approximation ratio",
                "competitive ratio",
                "hardness",
                "reduction",
            },
            "machine_learning": {
                "neural network",
                "deep learning",
                "machine learning",
                "training",
                "dataset",
                "model",
                "accuracy",
                "precision",
                "recall",
                "f1-score",
                "loss function",
                "gradient",
                "backpropagation",
                "optimizer",
                "epoch",
                "batch",
                "validation",
                "test set",
                "cross-validation",
                "overfitting",
                "regularization",
                "dropout",
                "convolution",
                "transformer",
                "attention",
                "bert",
                "gpt",
                "gan",
                "vae",
                "reinforcement learning",
                "supervised",
                "unsupervised",
                "semi-supervised",
                "transfer learning",
                "fine-tuning",
            },
            "systems": {
                "implementation",
                "system",
                "architecture",
                "performance",
                "scalability",
                "throughput",
                "latency",
                "bandwidth",
                "memory",
                "cache",
                "distributed",
                "parallel",
                "concurrent",
                "thread",
                "process",
                "synchronization",
                "load balancing",
                "fault tolerance",
                "reliability",
                "availability",
                "consistency",
                "partition",
                "replication",
                "consensus",
                "database",
            },
            "experimental": {
                "experiment",
                "evaluation",
                "benchmark",
                "dataset",
                "baseline",
                "comparison",
                "results",
                "performance",
                "metrics",
                "measurement",
                "empirical",
                "simulation",
                "prototype",
                "implementation",
                "case study",
                "ablation",
                "analysis",
                "statistical significance",
                "confidence interval",
                "standard deviation",
                "variance",
                "correlation",
                "hypothesis test",
            },
            "computation_resources": {
                "gpu",
                "cpu",
                "memory",
                "ram",
                "storage",
                "compute",
                "cluster",
                "cloud",
                "aws",
                "azure",
                "gcp",
                "hpc",
                "supercomputer",
                "fpga",
                "asic",
                "tpu",
                "quantum computer",
                "edge device",
                "iot",
                "embedded",
            },
            "data_structures": {
                "array",
                "list",
                "tree",
                "graph",
                "hash",
                "map",
                "set",
                "queue",
                "stack",
                "heap",
                "trie",
                "suffix tree",
                "segment tree",
                "fenwick tree",
                "union-find",
                "bloom filter",
                "skip list",
                "b-tree",
                "red-black tree",
                "avl tree",
                "splay tree",
                "treap",
                "kd-tree",
                "quadtree",
                "octree",
            },
        }

        # Patterns indicating computational resources or experiments
        self.resource_patterns = [
            (
                r"\d+\s*(?:GB|TB|PB)\s*(?:of\s*)?(?:memory|RAM|storage|data)",
                "memory_size",
            ),
            (
                r"\d+\s*(?:hours?|days?|weeks?)\s*(?:of\s*)?(?:compute|computation|training)",
                "compute_time",
            ),
            (r"\d+\s*(?:CPU|GPU|TPU)s?\s*(?:cores?|units?)?", "compute_units"),
            (
                r"(?:trained|ran|executed)\s*(?:on|using)\s*\d+\s*(?:nodes?|machines?|servers?)",
                "distributed_scale",
            ),
            (
                r"\d+(?:\.\d+)?\s*(?:million|billion|M|B)\s*(?:parameters|samples|examples)",
                "scale_metric",
            ),
            (
                r"(?:dataset|corpus)\s*(?:of|with|containing)\s*\d+\s*(?:samples|examples|instances)",
                "dataset_size",
            ),
        ]

        # Experimental indicators
        self.experimental_indicators = {
            "strong": {
                "we implement",
                "we develop",
                "we build",
                "we design",
                "we propose and implement",
                "our implementation",
                "our system",
                "our algorithm",
                "we evaluate",
                "experimental results",
                "empirical evaluation",
                "extensive experiments",
                "real-world experiments",
                "experimental setup",
                "experimental validation",
            },
            "medium": {
                "we test",
                "we measure",
                "we compare",
                "we analyze",
                "we benchmark",
                "performance evaluation",
                "experimental study",
                "case study",
                "simulation results",
                "synthetic experiments",
                "controlled experiments",
            },
            "weak": {
                "we propose",
                "we present",
                "we introduce",
                "theoretical analysis",
                "we prove",
                "we show",
                "formal analysis",
                "mathematical framework",
            },
        }

        logger.info("ComputationalAnalyzer initialized with comprehensive keyword sets")

    def analyze_computational_content(self, paper: Paper) -> ComputationalAnalysis:
        """
        Analyze a paper for computational content and richness.

        Args:
            paper: Paper object to analyze

        Returns:
            ComputationalAnalysis object with scores and metrics
        """
        # Combine title and abstract for analysis
        text = f"{paper.title} {paper.abstract}".lower()

        # Analyze keywords
        keyword_matches = self._analyze_keywords(text)

        # Analyze resource metrics
        resource_metrics = self._analyze_resources(text)

        # Analyze experimental indicators
        experimental_indicators = self._analyze_experimental_indicators(text)

        # Calculate computational richness score
        computational_richness = self._calculate_richness_score(
            keyword_matches, resource_metrics, experimental_indicators
        )

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            text, keyword_matches, resource_metrics, experimental_indicators
        )

        return ComputationalAnalysis(
            computational_richness=computational_richness,
            keyword_matches=keyword_matches,
            resource_metrics=resource_metrics,
            experimental_indicators=experimental_indicators,
            confidence_score=confidence_score,
        )

    def _analyze_keywords(self, text: str) -> Dict[str, int]:
        """Analyze keyword matches by category."""
        keyword_matches = {}

        for category, keywords in self.computational_keywords.items():
            matches = 0
            for keyword in keywords:
                # Use word boundaries for accurate matching
                pattern = r"\b" + re.escape(keyword) + r"\b"
                matches += len(re.findall(pattern, text, re.IGNORECASE))

            if matches > 0:
                keyword_matches[category] = matches

        return keyword_matches

    def _analyze_resources(self, text: str) -> Dict[str, Any]:
        """Extract computational resource metrics from text."""
        resource_metrics = {}

        for pattern, metric_type in self.resource_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                resource_metrics[metric_type] = {
                    "count": len(matches),
                    "values": matches[:5],  # Store up to 5 examples
                }

        return resource_metrics

    def _analyze_experimental_indicators(self, text: str) -> Dict[str, Any]:
        """Analyze experimental vs theoretical indicators."""
        indicators = {
            "strong_experimental": 0,
            "medium_experimental": 0,
            "weak_experimental": 0,
            "implementation_mentioned": False,
            "evaluation_mentioned": False,
            "theoretical_focus": False,
        }

        # Count indicator matches
        for level, phrases in self.experimental_indicators.items():
            count = 0
            for phrase in phrases:
                if phrase in text:
                    count += 1
            indicators[f"{level}_experimental"] = count

        # Check specific flags
        indicators["implementation_mentioned"] = any(
            term in text
            for term in ["implement", "implementation", "prototype", "system"]
        )
        indicators["evaluation_mentioned"] = any(
            term in text
            for term in ["evaluat", "experiment", "benchmark", "test", "measur"]
        )
        indicators["theoretical_focus"] = any(
            term in text
            for term in ["theorem", "proof", "lemma", "corollary", "formal"]
        )

        return indicators

    def _calculate_richness_score(
        self,
        keyword_matches: Dict[str, int],
        resource_metrics: Dict[str, Any],
        experimental_indicators: Dict[str, Any],
    ) -> float:
        """
        Calculate overall computational richness score (0-1).

        Higher scores indicate more computational content.
        """
        score = 0.0

        # Keyword contribution (40% weight)
        keyword_score = 0.0
        if keyword_matches:
            # Weight different categories
            weights = {
                "algorithms": 1.5,
                "machine_learning": 1.5,
                "systems": 1.3,
                "complexity": 1.2,
                "experimental": 1.2,
                "computation_resources": 1.1,
                "data_structures": 1.0,
            }

            total_weighted_matches = sum(
                keyword_matches.get(cat, 0) * weights.get(cat, 1.0) for cat in weights
            )

            # Normalize to 0-1 range (50 weighted matches = 1.0)
            keyword_score = min(1.0, total_weighted_matches / 50.0)

        score += keyword_score * 0.4

        # Resource metrics contribution (30% weight)
        resource_score = 0.0
        if resource_metrics:
            # Each type of resource mentioned adds to score
            resource_types = len(resource_metrics)
            resource_score = min(1.0, resource_types / 4.0)

        score += resource_score * 0.3

        # Experimental indicators contribution (30% weight)
        experimental_score = 0.0
        if experimental_indicators:
            strong = experimental_indicators.get("strong_experimental", 0)
            medium = experimental_indicators.get("medium_experimental", 0)
            weak = experimental_indicators.get("weak_experimental", 0)

            # Weight strong indicators more heavily
            weighted_indicators = strong * 3 + medium * 2 + weak * 1
            experimental_score = min(1.0, weighted_indicators / 10.0)

            # Bonus for implementation and evaluation
            if experimental_indicators.get("implementation_mentioned"):
                experimental_score = min(1.0, experimental_score + 0.2)
            if experimental_indicators.get("evaluation_mentioned"):
                experimental_score = min(1.0, experimental_score + 0.1)

            # Penalty for purely theoretical
            if experimental_indicators.get("theoretical_focus") and strong == 0:
                experimental_score *= 0.7

        score += experimental_score * 0.3

        return float(score)

    def _calculate_confidence_score(
        self,
        text: str,
        keyword_matches: Dict[str, int],
        resource_metrics: Dict[str, Any],
        experimental_indicators: Dict[str, Any],
    ) -> float:
        """
        Calculate confidence in the computational richness assessment.

        Based on text length and evidence strength.
        """
        confidence = 0.0

        # Text length factor (longer abstracts provide more evidence)
        text_length = len(text.split())
        length_factor = min(1.0, text_length / 200.0)  # 200 words = full confidence
        confidence += length_factor * 0.3

        # Keyword evidence factor
        total_keywords = sum(keyword_matches.values())
        keyword_factor = min(
            1.0, total_keywords / 20.0
        )  # 20 keywords = full confidence
        confidence += keyword_factor * 0.3

        # Resource evidence factor
        resource_factor = min(1.0, len(resource_metrics) / 3.0)
        confidence += resource_factor * 0.2

        # Experimental evidence factor
        experimental_evidence = experimental_indicators.get(
            "strong_experimental", 0
        ) + experimental_indicators.get("medium_experimental", 0)
        experimental_factor = min(1.0, experimental_evidence / 5.0)
        confidence += experimental_factor * 0.2

        return float(confidence)

    def batch_analyze(self, papers: List[Paper]) -> List[ComputationalAnalysis]:
        """Analyze multiple papers efficiently."""
        results = []

        for paper in papers:
            try:
                analysis = self.analyze_computational_content(paper)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing paper '{paper.title}': {e}")
                # Return minimal analysis on error
                results.append(
                    ComputationalAnalysis(
                        computational_richness=0.0,
                        keyword_matches={},
                        resource_metrics={},
                        experimental_indicators={},
                        confidence_score=0.0,
                    )
                )

        return results
