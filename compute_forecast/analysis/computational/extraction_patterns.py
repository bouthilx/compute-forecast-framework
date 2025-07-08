"""
Common extraction patterns and edge case handling for computational requirements.

This module documents common patterns found in papers and provides systematic
approaches for handling edge cases and ambiguous information.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import re
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of extraction patterns."""

    EXPLICIT_RESOURCE = "explicit_resource"
    DISTRIBUTED_TRAINING = "distributed_training"
    MULTIPLE_PHASES = "multiple_phases"
    IMPLICIT_INFORMATION = "implicit_information"
    CLOUD_CREDITS = "cloud_credits"
    RELATIVE_REFERENCE = "relative_reference"


@dataclass
class ExtractionPattern:
    """Represents a common extraction pattern."""

    pattern_type: PatternType
    description: str
    example_text: str
    extraction_approach: str
    expected_fields: List[str]
    confidence_level: str
    notes: str


class CommonPatterns:
    """Database of common extraction patterns found in computational papers."""

    PATTERNS = [
        ExtractionPattern(
            pattern_type=PatternType.EXPLICIT_RESOURCE,
            description="Direct statement of computational resources",
            example_text="We trained our model on 8 V100 GPUs for 5 days",
            extraction_approach="Direct extraction of GPU type, count, and time",
            expected_fields=["gpu_type", "gpu_count", "training_time"],
            confidence_level="high",
            notes="Calculate: 8 GPUs × 120 hours = 960 GPU-hours",
        ),
        ExtractionPattern(
            pattern_type=PatternType.DISTRIBUTED_TRAINING,
            description="Multi-node distributed training setup",
            example_text="32 nodes with 8 GPUs each for 36 hours",
            extraction_approach="Calculate total GPUs: nodes × GPUs per node",
            expected_fields=[
                "nodes",
                "gpus_per_node",
                "training_time",
                "total_gpu_hours",
            ],
            confidence_level="high",
            notes="Total: 32 × 8 = 256 GPUs, 256 × 36 = 9,216 GPU-hours",
        ),
        ExtractionPattern(
            pattern_type=PatternType.MULTIPLE_PHASES,
            description="Training with distinct phases (pre-training, fine-tuning)",
            example_text="Pre-training: 128 TPU cores for 2 weeks, Fine-tuning: 8 V100s for 3 days",
            extraction_approach="Extract each phase separately, sum for total",
            expected_fields=["pre_training_time", "fine_tuning_time", "total_time"],
            confidence_level="medium",
            notes="Record phases separately and calculate total computational cost",
        ),
        ExtractionPattern(
            pattern_type=PatternType.IMPLICIT_INFORMATION,
            description="Reference to known configurations",
            example_text="Following BERT-large configuration with standard training",
            extraction_approach="Use known specifications for referenced models",
            expected_fields=["parameters_count", "architecture"],
            confidence_level="medium",
            notes="BERT-large: 340M parameters, estimate training time from similar papers",
        ),
        ExtractionPattern(
            pattern_type=PatternType.CLOUD_CREDITS,
            description="Cost-based resource specification",
            example_text="Used $50,000 in cloud credits on Google Cloud",
            extraction_approach="Estimate GPU-hours based on cloud pricing",
            expected_fields=["estimated_cost", "cloud_provider"],
            confidence_level="low",
            notes="Estimate using typical cloud GPU pricing ($2-4/GPU-hour)",
        ),
        ExtractionPattern(
            pattern_type=PatternType.RELATIVE_REFERENCE,
            description="Resources described relative to other work",
            example_text="10x more compute than GPT-2 training",
            extraction_approach="Calculate based on known baseline computational costs",
            expected_fields=["relative_multiplier", "baseline_model"],
            confidence_level="low",
            notes="Requires knowledge of baseline model's computational requirements",
        ),
    ]

    @classmethod
    def get_pattern(cls, pattern_type: PatternType) -> Optional[ExtractionPattern]:
        """Get pattern by type."""
        for pattern in cls.PATTERNS:
            if pattern.pattern_type == pattern_type:
                return pattern
        return None

    @classmethod
    def get_patterns_by_confidence(cls, confidence: str) -> List[ExtractionPattern]:
        """Get patterns by confidence level."""
        return [p for p in cls.PATTERNS if p.confidence_level == confidence]


class ExtractionRegexPatterns:
    """Regular expression patterns for extracting specific information."""

    # GPU patterns
    GPU_COUNT_PATTERNS = [
        r"(\d+)\s*(?:×|x|\*)\s*([A-Z]\d+|V100|A100|K80|P100|T4)",  # "8 × V100"
        r"(\d+)\s+(V100|A100|K80|P100|T4)\s*GPUs?",  # "8 V100 GPUs"
        r"(\d+)\s+([A-Z]\d+)\s*graphics?\s*cards?",  # "8 V100 graphics cards"
        r"trained\s+on\s+(\d+)\s+(V100|A100|K80|P100|T4)",  # "trained on 8 V100"
    ]

    # Training time patterns
    TIME_PATTERNS = [
        r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b",  # "5.5 hours"
        r"(\d+(?:\.\d+)?)\s*(days?|d)\b",  # "3 days"
        r"(\d+(?:\.\d+)?)\s*(weeks?|w)\b",  # "2 weeks"
        r"for\s+(\d+(?:\.\d+)?)\s*(hours?|days?|weeks?)",  # "for 5 days"
        r"(\d+(?:\.\d+)?)\s*-?\s*(hour|day|week)\s*training",  # "5-day training"
    ]

    # Parameter count patterns
    PARAMETER_PATTERNS = [
        r"(\d+(?:\.\d+)?)\s*([BMK])\s*parameters?",  # "340M parameters"
        r"(\d+(?:\.\d+)?)\s*(billion|million|thousand)\s*parameters?",  # "1.5 billion parameters"
        r"(\d+(?:\.\d+)?)\s*([BMK])\s*params",  # "340M params"
        r"model\s+size:?\s*(\d+(?:\.\d+)?)\s*([BMK])",  # "model size: 340M"
    ]

    # Cost patterns
    COST_PATTERNS = [
        r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)",  # "$50,000.00"
        r"(\d+(?:,\d{3})*)\s*dollars?",  # "50000 dollars"
        r"cost:?\s*\$?(\d+(?:,\d{3})*)",  # "cost: $50000"
        r"(\d+(?:,\d{3})*)\s*USD",  # "50000 USD"
    ]

    # GPU-hours patterns
    GPU_HOURS_PATTERNS = [
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*GPU-?hours?",  # "1,000 GPU-hours"
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*GPU\s*hrs?",  # "1000 GPU hrs"
        r"total:?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*GPU-?hours?",  # "total: 1000 GPU-hours"
    ]

    @staticmethod
    def extract_gpu_info(text: str) -> List[Tuple[int, str]]:
        """Extract GPU count and type from text."""
        results = []
        text.lower()

        for pattern in ExtractionRegexPatterns.GPU_COUNT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                count = int(match.group(1))
                gpu_type = match.group(2).upper()
                results.append((count, gpu_type))

        return results

    @staticmethod
    def extract_training_time(text: str) -> List[Tuple[float, str]]:
        """Extract training time values from text."""
        results = []

        for pattern in ExtractionRegexPatterns.TIME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                unit = match.group(2).lower()
                results.append((value, unit))

        return results

    @staticmethod
    def extract_parameters(text: str) -> List[Tuple[float, str]]:
        """Extract parameter counts from text."""
        results = []

        for pattern in ExtractionRegexPatterns.PARAMETER_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                unit = match.group(2).upper() if len(match.groups()) > 1 else "M"
                results.append((value, unit))

        return results

    @staticmethod
    def normalize_time_to_hours(value: float, unit: str) -> float:
        """Normalize time values to hours."""
        unit_lower = unit.lower()

        if unit_lower in ["h", "hour", "hours", "hr", "hrs"]:
            return value
        elif unit_lower in ["d", "day", "days"]:
            return value * 24
        elif unit_lower in ["w", "week", "weeks"]:
            return value * 24 * 7
        else:
            logger.warning(f"Unknown time unit: {unit}")
            return value

    @staticmethod
    def normalize_parameters_to_millions(value: float, unit: str) -> float:
        """Normalize parameter counts to millions."""
        unit_upper = unit.upper()

        if unit_upper == "M":
            return value
        elif unit_upper == "B":
            return value * 1000
        elif unit_upper == "K":
            return value / 1000
        else:
            logger.warning(f"Unknown parameter unit: {unit}")
            return value


class EdgeCaseHandler:
    """Handles edge cases and ambiguous extraction scenarios."""

    # Known model configurations for implicit references
    KNOWN_MODELS = {
        "BERT-base": {
            "parameters_millions": 110,
            "architecture": "Transformer",
            "layers": 12,
            "hidden_size": 768,
        },
        "BERT-large": {
            "parameters_millions": 340,
            "architecture": "Transformer",
            "layers": 24,
            "hidden_size": 1024,
        },
        "GPT-2": {
            "parameters_millions": 117,
            "architecture": "Transformer",
            "layers": 12,
            "hidden_size": 768,
        },
        "GPT-3": {
            "parameters_millions": 175000,
            "architecture": "Transformer",
            "layers": 96,
            "hidden_size": 12288,
        },
        "T5-base": {
            "parameters_millions": 220,
            "architecture": "Transformer",
            "layers": 12,
            "hidden_size": 768,
        },
    }

    # Cloud pricing estimates (USD per GPU-hour)
    CLOUD_PRICING = {
        "aws": {"V100": 3.06, "A100": 4.10, "K80": 0.90},
        "gcp": {"V100": 2.48, "A100": 3.77, "K80": 0.45},
        "azure": {"V100": 3.60, "A100": 4.90, "K80": 0.90},
    }

    @classmethod
    def handle_missing_gpu_type(cls, text: str, year: Optional[int] = None) -> str:
        """Handle cases where GPU type is not explicitly mentioned."""
        text_lower = text.lower()

        # Look for generation hints
        if "latest nvidia" in text_lower or "state-of-the-art gpu" in text_lower:
            if year and year >= 2020:
                return "A100 (inferred)"
            elif year and year >= 2017:
                return "V100 (inferred)"
            else:
                return "GPU (generation unknown)"

        # Look for memory hints
        if "32gb" in text_lower or "40gb" in text_lower:
            return "A100 (inferred from memory)"
        elif "16gb" in text_lower:
            return "V100 or T4 (inferred from memory)"

        # Default based on year
        if year and year >= 2021:
            return "A100 (assumed based on year)"
        elif year and year >= 2018:
            return "V100 (assumed based on year)"
        else:
            return "GPU (type unknown)"

    @classmethod
    def handle_vague_time(cls, text: str) -> Tuple[float, float]:
        """Handle vague time expressions like 'several days'."""
        text_lower = text.lower()

        if "several days" in text_lower:
            return (3.0 * 24, 5.0 * 24)  # 3-5 days in hours
        elif "few hours" in text_lower:
            return (2.0, 4.0)  # 2-4 hours
        elif "many hours" in text_lower:
            return (12.0, 48.0)  # 12-48 hours
        elif "overnight" in text_lower:
            return (8.0, 12.0)  # 8-12 hours
        elif "weekend" in text_lower:
            return (48.0, 72.0)  # 2-3 days
        else:
            logger.warning(f"Unknown vague time expression: {text}")
            return (1.0, 24.0)  # Default 1-24 hours

    @classmethod
    def estimate_from_cost(
        cls, cost_usd: float, provider: str = "aws", gpu_type: str = "V100"
    ) -> float:
        """Estimate GPU-hours from cost information."""
        if provider not in cls.CLOUD_PRICING:
            provider = "aws"  # Default to AWS pricing

        if gpu_type not in cls.CLOUD_PRICING[provider]:
            gpu_type = "V100"  # Default to V100

        cost_per_hour = cls.CLOUD_PRICING[provider][gpu_type]
        estimated_gpu_hours = cost_usd / cost_per_hour

        logger.info(
            f"Estimated {estimated_gpu_hours:.0f} GPU-hours from ${cost_usd} "
            f"using {provider} {gpu_type} pricing"
        )

        return estimated_gpu_hours

    @classmethod
    def resolve_model_reference(cls, model_name: str) -> Dict[str, Any]:
        """Resolve implicit model references to known configurations."""
        model_name_clean = model_name.upper().replace("-", "").replace("_", "")

        # Try exact match first
        for known_model, config in cls.KNOWN_MODELS.items():
            if known_model.upper().replace("-", "") == model_name_clean:
                logger.info(f"Resolved {model_name} to known configuration")
                return config.copy()

        # Try partial match
        for known_model, config in cls.KNOWN_MODELS.items():
            if known_model.upper().replace("-", "") in model_name_clean:
                logger.info(
                    f"Partially resolved {model_name} to {known_model} configuration"
                )
                return config.copy()

        logger.warning(f"Could not resolve model reference: {model_name}")
        return {}

    @classmethod
    def handle_distributed_training(cls, text: str) -> Dict[str, Any]:
        """Extract distributed training configuration."""
        text_lower = text.lower()
        result = {}

        # Look for node patterns
        node_patterns = [
            r"(\d+)\s*nodes?",
            r"(\d+)-node\s*cluster",
            r"distributed\s*across\s*(\d+)\s*machines?",
        ]

        for pattern in node_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["nodes"] = int(match.group(1))
                break

        # Look for GPUs per node
        gpu_per_node_patterns = [
            r"(\d+)\s*gpus?\s*per\s*node",
            r"(\d+)\s*gpus?\s*each",
            r"each\s*with\s*(\d+)\s*gpus?",
        ]

        for pattern in gpu_per_node_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["gpus_per_node"] = int(match.group(1))
                break

        # Calculate total GPUs if both found
        if "nodes" in result and "gpus_per_node" in result:
            result["total_gpus"] = result["nodes"] * result["gpus_per_node"]

        return result

    @classmethod
    def handle_multiple_experiments(cls, text: str) -> Dict[str, Any]:
        """Handle cases with multiple experimental runs."""
        text_lower = text.lower()
        result = {}

        # Look for number of runs
        run_patterns = [
            r"(\d+)\s*(?:independent\s*)?runs?",
            r"(\d+)\s*trials?",
            r"(\d+)\s*experiments?",
            r"repeated\s*(\d+)\s*times?",
        ]

        for pattern in run_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["number_of_runs"] = int(match.group(1))
                break

        # Look for statistical significance indicators
        if any(
            term in text_lower
            for term in [
                "statistical significance",
                "confidence interval",
                "standard deviation",
            ]
        ):
            result["statistical_analysis"] = True

        return result


class PatternMatcher:
    """Matches text against known extraction patterns."""

    def __init__(self):
        """Initialize pattern matcher."""
        self.regex_patterns = ExtractionRegexPatterns()
        self.edge_case_handler = EdgeCaseHandler()

    def identify_pattern_type(self, text: str) -> List[PatternType]:
        """Identify which extraction patterns apply to the given text."""
        text_lower = text.lower()
        patterns = []

        # Check for explicit resource statements
        if any(gpu in text_lower for gpu in ["v100", "a100", "k80", "p100", "t4"]):
            patterns.append(PatternType.EXPLICIT_RESOURCE)

        # Check for distributed training
        if any(term in text_lower for term in ["nodes", "cluster", "distributed"]):
            patterns.append(PatternType.DISTRIBUTED_TRAINING)

        # Check for multiple phases
        if any(
            term in text_lower
            for term in ["pre-training", "fine-tuning", "pretraining", "finetuning"]
        ):
            patterns.append(PatternType.MULTIPLE_PHASES)

        # Check for model references
        if any(model in text_lower for model in ["bert", "gpt", "t5", "transformer"]):
            patterns.append(PatternType.IMPLICIT_INFORMATION)

        # Check for cost information
        if any(
            term in text_lower for term in ["$", "dollar", "cost", "credit", "cloud"]
        ):
            patterns.append(PatternType.CLOUD_CREDITS)

        # Check for relative references
        if any(
            term in text_lower
            for term in ["more than", "times", "compared to", "relative to"]
        ):
            patterns.append(PatternType.RELATIVE_REFERENCE)

        return patterns

    def extract_all_patterns(self, text: str) -> Dict[PatternType, Dict[str, Any]]:
        """Extract information using all applicable patterns."""
        results = {}
        pattern_types = self.identify_pattern_type(text)

        for pattern_type in pattern_types:
            if pattern_type == PatternType.EXPLICIT_RESOURCE:
                results[pattern_type] = self._extract_explicit_resources(text)
            elif pattern_type == PatternType.DISTRIBUTED_TRAINING:
                results[pattern_type] = (
                    self.edge_case_handler.handle_distributed_training(text)
                )
            elif pattern_type == PatternType.MULTIPLE_PHASES:
                results[pattern_type] = self._extract_multiple_phases(text)
            elif pattern_type == PatternType.IMPLICIT_INFORMATION:
                results[pattern_type] = self._extract_implicit_info(text)
            elif pattern_type == PatternType.CLOUD_CREDITS:
                results[pattern_type] = self._extract_cost_info(text)
            elif pattern_type == PatternType.RELATIVE_REFERENCE:
                results[pattern_type] = self._extract_relative_info(text)

        return results

    def _extract_explicit_resources(self, text: str) -> Dict[str, Any]:
        """Extract explicit resource information."""
        result = {}

        # Extract GPU info
        gpu_info = self.regex_patterns.extract_gpu_info(text)
        if gpu_info:
            result["gpu_count"] = gpu_info[0][0]
            result["gpu_type"] = gpu_info[0][1]

        # Extract training time
        time_info = self.regex_patterns.extract_training_time(text)
        if time_info:
            value, unit = time_info[0]
            result["training_time_hours"] = self.regex_patterns.normalize_time_to_hours(
                value, unit
            )
            result["training_time_original"] = f"{value} {unit}"

        # Extract parameters
        param_info = self.regex_patterns.extract_parameters(text)
        if param_info:
            value, unit = param_info[0]
            result["parameters_millions"] = (
                self.regex_patterns.normalize_parameters_to_millions(value, unit)
            )
            result["parameters_original"] = f"{value}{unit}"

        return result

    def _extract_multiple_phases(self, text: str) -> Dict[str, Any]:
        """Extract multiple training phases."""
        result = {}
        text_lower = text.lower()

        # Look for pre-training
        if "pre-training" in text_lower or "pretraining" in text_lower:
            # Extract time for pre-training phase
            result["has_pretraining"] = True

        # Look for fine-tuning
        if "fine-tuning" in text_lower or "finetuning" in text_lower:
            result["has_finetuning"] = True

        return result

    def _extract_implicit_info(self, text: str) -> Dict[str, Any]:
        """Extract implicit model information."""
        result = {}
        text_lower = text.lower()

        # Look for model references
        for model_name in self.edge_case_handler.KNOWN_MODELS.keys():
            if model_name.lower() in text_lower:
                config = self.edge_case_handler.resolve_model_reference(model_name)
                result.update(config)
                result["referenced_model"] = model_name
                break

        return result

    def _extract_cost_info(self, text: str) -> Dict[str, Any]:
        """Extract cost information."""
        result = {}

        # Extract cost values
        for pattern in ExtractionRegexPatterns.COST_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cost_str = match.group(1).replace(",", "")
                result["cost_usd"] = float(cost_str)
                break

        # Identify cloud provider
        text_lower = text.lower()
        if "aws" in text_lower or "amazon" in text_lower:
            result["cloud_provider"] = "aws"
        elif "gcp" in text_lower or "google" in text_lower:
            result["cloud_provider"] = "gcp"
        elif "azure" in text_lower or "microsoft" in text_lower:
            result["cloud_provider"] = "azure"

        return result

    def _extract_relative_info(self, text: str) -> Dict[str, Any]:
        """Extract relative reference information."""
        result = {}
        text_lower = text.lower()

        # Look for multiplier patterns
        multiplier_patterns = [
            r"(\d+(?:\.\d+)?)\s*[x×]\s*more",
            r"(\d+(?:\.\d+)?)\s*times\s*(?:more|larger|bigger)",
            r"(\d+(?:\.\d+)?)\s*times\s*the\s*compute",
        ]

        for pattern in multiplier_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["multiplier"] = float(match.group(1))
                break

        # Look for baseline model references
        for model_name in self.edge_case_handler.KNOWN_MODELS.keys():
            if model_name.lower() in text_lower:
                result["baseline_model"] = model_name
                break

        return result
