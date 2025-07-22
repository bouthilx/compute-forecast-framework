"""Domain-specific benchmark extractors for NLP, CV, and RL."""

import re
from typing import Dict, Any, List

from compute_forecast.pipeline.metadata_collection.models import Paper


class NLPBenchmarkExtractor:
    """NLP-specific extraction logic."""

    def __init__(self):
        self.benchmark_datasets = [
            "GLUE",
            "SuperGLUE",
            "SQuAD",
            "WMT",
            "CommonCrawl",
            "BERT",
            "RoBERTa",
            "GPT",
            "T5",
            "MMLU",
            "HellaSwag",
            "ARC",
            "BoolQ",
            "CoQA",
            "RACE",
            "SWAG",
            "Winograd",
        ]

        # NLP-specific patterns
        self.token_patterns = [
            r"(\d+\.?\d*)\s*billion\s+(?:tokens?|words?)",
            r"(\d+\.?\d*)\s*([BMK])\s*(?:tokens?|words?)",
            r"trained\s+on\s+(\d+\.?\d*)\s*([BMK])?\s*(?:tokens?|words?)",
        ]

        self.vocab_patterns = [
            r"vocabulary\s+(?:size\s+)?(?:of\s+)?(\d+(?:,\d+)*)",
            r"(\d+(?:,\d+)*)[- ]?(?:word)?pieces?",
            r"vocab(?:ulary)?\s+(?:of\s+)?(\d+(?:,\d+)*)",
        ]

        self.sequence_patterns = [
            r"(?:max(?:imum)?\s+)?sequence\s+length\s+(?:was\s+)?(?:set\s+to\s+)?(\d+)",
            r"(\d+)\s+tokens?\s+(?:sequence|context)",
            r"context\s+(?:window|length)\s+(?:of\s+)?(\d+)",
        ]

    def extract_nlp_specific_metrics(self, paper: Paper) -> Dict[str, Any]:
        """Extract NLP-specific computational metrics."""
        metrics: Dict[str, Any] = {
            "token_count": None,
            "vocabulary_size": None,
            "sequence_length": None,
            "pre_training": False,
            "fine_tuning": False,
        }

        text = getattr(paper, "full_text", "") or paper.get_best_abstract()

        # Extract token count
        for pattern in self.token_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2) if len(match.groups()) > 1 else None

                if "billion" in match.group(0).lower():
                    value *= 1_000_000_000
                elif unit:
                    if unit.upper() == "B":
                        value *= 1_000_000_000
                    elif unit.upper() == "M":
                        value *= 1_000_000
                    elif unit.upper() == "K":
                        value *= 1_000

                metrics["token_count"] = int(value)
                break

        # Extract vocabulary size
        for pattern in self.vocab_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Remove commas from number
                value_str = match.group(1).replace(",", "")
                metrics["vocabulary_size"] = int(value_str)
                break

        # Extract sequence length
        for pattern in self.sequence_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["sequence_length"] = int(match.group(1))
                break

        # Check for pre-training and fine-tuning
        if re.search(r"pre[- ]?train", text, re.IGNORECASE):
            metrics["pre_training"] = True
        if re.search(r"fine[- ]?tun", text, re.IGNORECASE):
            metrics["fine_tuning"] = True

        return metrics

    def normalize_nlp_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize to standard units (e.g., tokens to words)."""
        normalized = metrics.copy()

        # Estimate words from tokens (roughly 0.75 words per token)
        if metrics.get("token_count") and not metrics.get("word_count_estimate"):
            normalized["word_count_estimate"] = int(metrics["token_count"] * 0.75)

        return normalized

    def identify_benchmarks(self, paper: Paper) -> List[str]:
        """Identify NLP benchmark datasets mentioned in the paper."""
        benchmarks = []
        # Include full_text if available
        full_text = getattr(paper, "full_text", "")
        text = f"{paper.title} {paper.get_best_abstract()} {full_text}".lower()

        for dataset in self.benchmark_datasets:
            # Handle special cases
            if dataset in ["BERT", "GPT", "T5"] and dataset.lower() in text:
                # Only count as benchmark if used for evaluation, not just mentioned
                if re.search(
                    f"evaluated?\\s+on\\s+.*{dataset.lower()}", text
                ) or re.search(f"{dataset.lower()}\\s+benchmark", text):
                    benchmarks.append(dataset)
            elif dataset.lower() in text:
                benchmarks.append(dataset)

        return list(set(benchmarks))  # Remove duplicates


class CVBenchmarkExtractor:
    """Computer Vision specific extraction."""

    def __init__(self):
        self.benchmark_datasets = [
            "ImageNet",
            "COCO",
            "CIFAR",
            "CIFAR-10",
            "CIFAR-100",
            "ADE20K",
            "Kinetics",
            "Pascal VOC",
            "CityScapes",
            "Open Images",
            "KITTI",
            "ModelNet",
            "ShapeNet",
        ]

        # Resolution patterns
        self.resolution_patterns = [
            r"(\d+)\s*[x×]\s*(\d+)(?:\s*(?:px|pixels?))?",
            r"resolution\s+(?:of\s+)?(\d+)\s*[x×]\s*(\d+)",
            r"(\d+)p\s+(?:images?|frames?)",  # e.g., "1080p"
        ]

        # Throughput patterns
        self.throughput_patterns = [
            r"(\d+\.?\d*)\s*(?:images?|frames?)\s*(?:per\s*|/)\s*(?:second|sec|s)",
            r"(\d+\.?\d*)\s*fps",
            r"throughput\s+(?:of\s+)?(\d+\.?\d*)",
        ]

    def extract_cv_specific_metrics(self, paper: Paper) -> Dict[str, Any]:
        """Extract CV-specific computational metrics."""
        metrics: Dict[str, Any] = {
            "image_resolution": None,
            "throughput_fps": None,
            "augmentation_compute": False,
            "multi_scale_training": False,
        }

        text = getattr(paper, "full_text", "") or paper.get_best_abstract()

        # Extract image resolution
        for pattern in self.resolution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if "p" in match.group(0):  # e.g., "1080p"
                    height = int(match.group(1))
                    width = int(height * 16 / 9)  # Assume 16:9 aspect ratio
                    metrics["image_resolution"] = (width, height)
                else:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    metrics["image_resolution"] = (width, height)
                break

        # Extract throughput
        for pattern in self.throughput_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["throughput_fps"] = float(match.group(1))
                break

        # Check for augmentation and multi-scale
        augmentation_terms = [
            "augment",
            "randaugment",
            "autoaugment",
            "cutmix",
            "mixup",
        ]
        for term in augmentation_terms:
            if term in text.lower():
                metrics["augmentation_compute"] = True
                break

        if re.search(r"multi[- ]?scale", text, re.IGNORECASE):
            metrics["multi_scale_training"] = True

        return metrics

    def calculate_compute_overhead(self, metrics: Dict[str, Any]) -> float:
        """Calculate compute overhead for CV tasks."""
        overhead = 1.0

        # Higher resolution increases compute quadratically
        if metrics.get("image_resolution"):
            width, height = metrics["image_resolution"]
            base_resolution = 224 * 224
            actual_resolution = width * height
            resolution_factor = actual_resolution / base_resolution
            overhead *= resolution_factor

        # Multi-scale training adds overhead
        if metrics.get("multi_scale_training"):
            overhead *= 1.5

        # Augmentation adds overhead
        if metrics.get("augmentation_compute"):
            overhead *= 1.2

        return min(overhead, 3.0)  # Cap at 3x overhead

    def identify_benchmarks(self, paper: Paper) -> List[str]:
        """Identify CV benchmark datasets mentioned in the paper."""
        benchmarks = []
        full_text = getattr(paper, "full_text", "")
        text = f"{paper.title} {paper.get_best_abstract()} {full_text}".lower()

        for dataset in self.benchmark_datasets:
            # Handle special cases like CIFAR-10 vs CIFAR-100
            if dataset == "CIFAR":
                if "cifar-10" in text or "cifar10" in text:
                    benchmarks.append("CIFAR-10")
                if "cifar-100" in text or "cifar100" in text:
                    benchmarks.append("CIFAR-100")
            elif dataset.lower() in text:
                benchmarks.append(dataset)

        return list(set(benchmarks))


class RLBenchmarkExtractor:
    """Reinforcement Learning specific extraction."""

    def __init__(self):
        self.benchmark_environments = [
            "Atari",
            "MuJoCo",
            "OpenAI Gym",
            "Gym",
            "StarCraft",
            "Dota",
            "Go",
            "Chess",
            "Shogi",
            "Hex",
            "Hanabi",
            "DeepMind Control",
            "DMC",
            "Minecraft",
            "NetHack",
        ]

        # Environment step patterns
        self.step_patterns = [
            r"(\d+\.?\d*)\s*([BMK])?\s*(?:environment\s+)?steps?",
            r"(\d+\.?\d*)\s*([BMK])?\s*(?:training\s+)?frames?",
            r"trained?\s+(?:for\s+)?(\d+\.?\d*)\s*([BMK])?\s*episodes?",
        ]

        # Simulation time patterns
        self.sim_time_patterns = [
            r"(?:total\s+)?simulation\s+time(?:\s*[:])\s*(\d+\.?\d*)\s*days?",
            r"(\d+\.?\d*)\s*days?\s+(?:of\s+)?(?:simulation|training)",
            r"(\d+\.?\d*)\s*(?:gpu|cpu)\s*days?",
        ]

    def extract_rl_specific_metrics(self, paper: Paper) -> Dict[str, Any]:
        """Extract RL-specific computational metrics."""
        metrics: Dict[str, Any] = {
            "environment_steps": None,
            "simulation_time_days": None,
            "parallel_environments": None,
            "experience_replay_size": None,
        }

        text = getattr(paper, "full_text", "") or paper.get_best_abstract()

        # Extract environment steps
        for pattern in self.step_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2) if len(match.groups()) > 1 else None

                if unit:
                    if unit.upper() == "B":
                        value *= 1_000_000_000
                    elif unit.upper() == "M":
                        value *= 1_000_000
                    elif unit.upper() == "K":
                        value *= 1_000

                metrics["environment_steps"] = int(value)
                break

        # Extract simulation time
        for pattern in self.sim_time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["simulation_time_days"] = float(match.group(1))
                break

        # Extract parallel environments
        parallel_match = re.search(
            r"(\d+)\s*parallel\s+(?:environments?|workers?|actors?)",
            text,
            re.IGNORECASE,
        )
        if parallel_match:
            metrics["parallel_environments"] = int(parallel_match.group(1))

        # Extract replay buffer size
        replay_match = re.search(
            r"(?:replay\s+)?buffer\s+(?:size\s*[:])\s*(\d+\.?\d*)\s*([BMK])?\s*(?:transitions?)?",
            text,
            re.IGNORECASE,
        )
        if not replay_match:
            replay_match = re.search(
                r"(\d+\.?\d*)\s*([BMK])\s*transitions?", text, re.IGNORECASE
            )
        if replay_match:
            value = float(replay_match.group(1))
            unit = replay_match.group(2)
            if unit:
                if unit.upper() == "M":
                    value *= 1_000_000
                elif unit.upper() == "K":
                    value *= 1_000
            metrics["experience_replay_size"] = int(value)

        return metrics

    def estimate_compute_hours(self, metrics: Dict[str, Any]) -> float:
        """Estimate total compute hours for RL training."""
        if metrics.get("simulation_time_days"):
            # Assume 1 GPU per environment if not specified
            gpu_count = metrics.get("parallel_environments", 1)
            return float(metrics["simulation_time_days"] * 24 * gpu_count)

        return 0.0

    def identify_benchmarks(self, paper: Paper) -> List[str]:
        """Identify RL benchmark environments mentioned in the paper."""
        benchmarks = []
        full_text = getattr(paper, "full_text", "")
        text = f"{paper.title} {paper.get_best_abstract()} {full_text}".lower()

        for env in self.benchmark_environments:
            # Handle special cases
            if env == "OpenAI Gym" and ("gym" in text or "openai gym" in text):
                benchmarks.append("OpenAI Gym")
            elif env == "DeepMind Control" and (
                "dmc" in text or "deepmind control" in text
            ):
                benchmarks.append("DeepMind Control")
            elif env.lower() in text:
                benchmarks.append(env)

        return list(set(benchmarks))
