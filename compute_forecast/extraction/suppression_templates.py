"""Extraction templates with suppression indicators for computational demand analysis."""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Pattern

from .template_engine import ExtractionTemplate
from .default_templates import DefaultTemplates


class SuppressionField(str, Enum):
    """Suppression indicator fields."""

    # Experimental scope
    NUM_ABLATIONS = "num_ablations"
    NUM_SEEDS = "num_seeds"
    NUM_BASELINES = "num_baselines"
    NUM_MODEL_VARIANTS = "num_model_variants"
    MISSING_EXPERIMENTS = "missing_experiments"

    # Scale analysis
    MODEL_SIZE_PERCENTILE = "model_size_percentile"
    TRAINING_TRUNCATED = "training_truncated"
    CONVERGENCE_ACHIEVED = "convergence_achieved"
    DATASET_SUBSAMPLED = "dataset_subsampled"
    SUBSAMPLE_RATIO = "subsample_ratio"

    # Method classification
    EFFICIENCY_FOCUSED = "efficiency_focused"
    COMPUTE_SAVING_TECHNIQUES = "compute_saving_techniques"
    METHOD_TYPE = "method_type"

    # Explicit constraints
    CONSTRAINTS_MENTIONED = "constraints_mentioned"
    CONSTRAINT_QUOTES = "constraint_quotes"
    WORKAROUNDS_DESCRIBED = "workarounds_described"


@dataclass
class SuppressionTemplate:
    """Wrapper for extraction template with suppression indicators."""

    base_template: ExtractionTemplate
    suppression_fields: List[SuppressionField] = field(default_factory=list)
    suppression_patterns: Dict[str, Pattern] = field(default_factory=dict)

    @property
    def template_id(self):
        return self.base_template.template_id

    @property
    def template_name(self):
        return self.base_template.template_name


@dataclass
class SuppressionIndicators:
    """Container for suppression indicators."""

    experimental_scope: Dict = field(
        default_factory=lambda: {
            "num_ablations": None,
            "num_seeds": None,
            "num_baselines": None,
            "num_model_variants": None,
            "standard_experiments_missing": [],
        }
    )

    scale_analysis: Dict = field(
        default_factory=lambda: {
            "parameter_percentile": None,
            "training_duration": None,
            "dataset_usage": None,
            "convergence_achieved": None,
            "subsample_ratio": None,
        }
    )

    method_classification: Dict = field(
        default_factory=lambda: {
            "efficiency_focused": False,
            "compute_saving_techniques": [],
            "method_type": None,  # "compute_intensive" or "compute_efficient"
        }
    )

    explicit_constraints: Dict = field(
        default_factory=lambda: {
            "mentions_constraints": False,
            "constraint_quotes": [],
            "workarounds_described": [],
        }
    )


class SuppressionTemplates:
    """Templates with suppression indicators for computational demand analysis."""

    # Regex patterns for suppression indicators
    SUPPRESSION_PATTERNS = {
        "ablation_count": re.compile(
            r"\b(\d+)\s*ablation(?:s)?\s*(?:stud(?:y|ies)|experiment)", re.IGNORECASE
        ),
        "seed_count": re.compile(
            r"(?:averaged?\s*over|using|with)\s*(\d+)\s*(?:random\s*)?seeds?|"
            r"(\d+)\s*(?:random\s*)?seeds?\s*(?:were|was)\s*used",
            re.IGNORECASE,
        ),
        "baseline_count": re.compile(
            r"(?:compare[d]?\s*(?:to|with|against)|versus)\s*(\d+)\s*baseline",
            re.IGNORECASE,
        ),
        "model_variants": re.compile(
            r"(\d+)\s*(?:model\s*)?(?:variant|size|scale)s?\s*(?:were|was)\s*(?:tested|evaluated|trained)",
            re.IGNORECASE,
        ),
        "constraint_mentions": re.compile(
            r"(?:due\s*to|because\s*of|limited\s*by)\s*(?:computational?|resource|memory|time)\s*"
            r"(?:constraint|limit|restriction)|computational?\s*constraint",
            re.IGNORECASE,
        ),
        "early_stopping": re.compile(
            r"(?:stopped?|terminated?|ended?)\s*(?:early|before|prior)", re.IGNORECASE
        ),
        "subsampling": re.compile(
            r"(?:subsample[d]?|sample[d]?|use[d]?)\s*(?:only\s*)?(\d+(?:\.\d+)?)[%％]\s*(?:of\s*)?(?:the\s*)?(?:data|dataset)",
            re.IGNORECASE,
        ),
        "efficiency_techniques": re.compile(
            r"(?:knowledge\s*)?distillation|pruning|quantization|"
            r"(?:model\s*)?compression|efficient\s*(?:transformer|attention)",
            re.IGNORECASE,
        ),
        "limited_experiments": re.compile(
            r"(?:only|just|merely)\s*(?:conduct|perform|run|did)\s*(\d+)|"
            r"limit(?:ed)?\s*to\s*(\d+)\s*experiment",
            re.IGNORECASE,
        ),
        "resource_quotes": re.compile(
            r'["\']([^"\']*(?:constraint|limit|resource|computational|memory)[^"\']*)["\']',
            re.IGNORECASE,
        ),
    }

    @classmethod
    def nlp_with_suppression(cls) -> SuppressionTemplate:
        """NLP template with suppression indicators."""
        base_template = DefaultTemplates.nlp_training_template()

        # Modify base template IDs
        base_template = ExtractionTemplate(
            template_id="nlp_training_suppression_v1",
            template_name="NLP Training with Suppression Analysis",
            version="1.0",
            required_fields=base_template.required_fields,
            optional_fields=base_template.optional_fields,
            validation_rules=base_template.validation_rules,
            normalization_rules=base_template.normalization_rules,
        )

        # Create wrapper with suppression
        template = SuppressionTemplate(
            base_template=base_template,
            suppression_fields=[
                SuppressionField.NUM_ABLATIONS,
                SuppressionField.NUM_SEEDS,
                SuppressionField.NUM_BASELINES,
                SuppressionField.EFFICIENCY_FOCUSED,
                SuppressionField.CONSTRAINTS_MENTIONED,
                SuppressionField.MODEL_SIZE_PERCENTILE,
                SuppressionField.TRAINING_TRUNCATED,
            ],
            suppression_patterns=cls.SUPPRESSION_PATTERNS,
        )

        # Add extract method
        # template.extract_suppression_indicators = cls._create_extractor()  # type: ignore

        return template

    @classmethod
    def cv_with_suppression(cls) -> SuppressionTemplate:
        """Computer vision template with suppression indicators."""
        base_template = DefaultTemplates.cv_training_template()

        base_template = ExtractionTemplate(
            template_id="cv_training_suppression_v1",
            template_name="CV Training with Suppression Analysis",
            version="1.0",
            required_fields=base_template.required_fields,
            optional_fields=base_template.optional_fields,
            validation_rules=base_template.validation_rules,
            normalization_rules=base_template.normalization_rules,
        )

        template = SuppressionTemplate(
            base_template=base_template,
            suppression_fields=[
                SuppressionField.NUM_ABLATIONS,
                SuppressionField.NUM_MODEL_VARIANTS,
                SuppressionField.DATASET_SUBSAMPLED,
                SuppressionField.EFFICIENCY_FOCUSED,
                SuppressionField.CONSTRAINTS_MENTIONED,
                SuppressionField.MODEL_SIZE_PERCENTILE,
            ],
            suppression_patterns=cls.SUPPRESSION_PATTERNS,
        )

        # template.extract_suppression_indicators = cls._create_extractor()  # type: ignore

        return template

    @classmethod
    def rl_with_suppression(cls) -> SuppressionTemplate:
        """Reinforcement learning template with suppression indicators."""
        base_template = DefaultTemplates.rl_training_template()

        base_template = ExtractionTemplate(
            template_id="rl_training_suppression_v1",
            template_name="RL Training with Suppression Analysis",
            version="1.0",
            required_fields=base_template.required_fields,
            optional_fields=base_template.optional_fields,
            validation_rules=base_template.validation_rules,
            normalization_rules=base_template.normalization_rules,
        )

        template = SuppressionTemplate(
            base_template=base_template,
            suppression_fields=[
                SuppressionField.NUM_SEEDS,
                SuppressionField.NUM_BASELINES,
                SuppressionField.TRAINING_TRUNCATED,
                SuppressionField.EFFICIENCY_FOCUSED,
                SuppressionField.CONSTRAINTS_MENTIONED,
                SuppressionField.CONVERGENCE_ACHIEVED,
            ],
            suppression_patterns=cls.SUPPRESSION_PATTERNS,
        )

        # template.extract_suppression_indicators = cls._create_extractor()  # type: ignore

        return template

    @classmethod
    def _create_extractor(cls):
        """Create suppression indicator extractor function."""

        def extract_suppression_indicators(text: str) -> SuppressionIndicators:
            """Extract suppression indicators from paper text."""
            indicators = SuppressionIndicators()

            # Extract experimental scope
            ablation_match = cls.SUPPRESSION_PATTERNS["ablation_count"].search(text)
            if ablation_match:
                indicators.experimental_scope["num_ablations"] = int(
                    ablation_match.group(1)
                )

            seed_matches = cls.SUPPRESSION_PATTERNS["seed_count"].findall(text)
            if seed_matches:
                # Get the first non-empty match
                for match in seed_matches:
                    seed_count = match[0] or match[1]
                    if seed_count:
                        indicators.experimental_scope["num_seeds"] = int(seed_count)
                        break

            baseline_match = cls.SUPPRESSION_PATTERNS["baseline_count"].search(text)
            if baseline_match:
                indicators.experimental_scope["num_baselines"] = int(
                    baseline_match.group(1)
                )

            variant_match = cls.SUPPRESSION_PATTERNS["model_variants"].search(text)
            if variant_match:
                indicators.experimental_scope["num_model_variants"] = int(
                    variant_match.group(1)
                )

            # Check for limited experiments
            limited_match = cls.SUPPRESSION_PATTERNS["limited_experiments"].search(text)
            if limited_match:
                count = limited_match.group(1) or limited_match.group(2)
                if count and int(count) <= 3:
                    indicators.experimental_scope[
                        "standard_experiments_missing"
                    ].append("limited_experiment_count")

            # Extract scale analysis
            if cls.SUPPRESSION_PATTERNS["early_stopping"].search(text):
                indicators.scale_analysis["training_duration"] = "truncated"
                indicators.scale_analysis["convergence_achieved"] = False

            subsample_match = cls.SUPPRESSION_PATTERNS["subsampling"].search(text)
            if subsample_match:
                indicators.scale_analysis["dataset_usage"] = "subsampled"
                indicators.scale_analysis["subsample_ratio"] = (
                    float(subsample_match.group(1)) / 100
                )

            # Extract method classification
            efficiency_matches = cls.SUPPRESSION_PATTERNS[
                "efficiency_techniques"
            ].findall(text)
            if efficiency_matches:
                indicators.method_classification["efficiency_focused"] = True
                indicators.method_classification["compute_saving_techniques"] = list(
                    set(match.lower() for match in efficiency_matches)
                )
                indicators.method_classification["method_type"] = "compute_efficient"

            # Extract explicit constraints
            if cls.SUPPRESSION_PATTERNS["constraint_mentions"].search(text):
                indicators.explicit_constraints["mentions_constraints"] = True

            quote_matches = cls.SUPPRESSION_PATTERNS["resource_quotes"].findall(text)
            if quote_matches:
                indicators.explicit_constraints["constraint_quotes"] = quote_matches

            # Determine method type if not already set
            if not indicators.method_classification["method_type"]:
                if (
                    indicators.explicit_constraints["mentions_constraints"]
                    or indicators.method_classification["efficiency_focused"]
                ):
                    indicators.method_classification["method_type"] = (
                        "compute_efficient"
                    )
                else:
                    indicators.method_classification["method_type"] = (
                        "compute_intensive"
                    )

            return indicators

        return extract_suppression_indicators

    @staticmethod
    def calculate_suppression_score(indicators: SuppressionIndicators) -> float:
        """Calculate overall suppression score (0=no suppression, 1=high suppression)."""
        score = 0.0
        factors = 0.0

        # Experimental scope scoring
        if indicators.experimental_scope["num_ablations"] is not None:
            # Typical good practice is 5+ ablations
            ablation_score = max(
                0, 1 - (indicators.experimental_scope["num_ablations"] / 5)
            )
            score += ablation_score * 0.2
            factors += float(0.2)

        if indicators.experimental_scope["num_seeds"] is not None:
            # Typical good practice is 5+ seeds
            seed_score = max(0, 1 - (indicators.experimental_scope["num_seeds"] / 5))
            score += seed_score * 0.2
            factors += float(0.2)

        if indicators.experimental_scope["num_baselines"] is not None:
            # Typical good practice is 3+ baselines
            baseline_score = max(
                0, 1 - (indicators.experimental_scope["num_baselines"] / 3)
            )
            score += baseline_score * 0.15
            factors += float(0.15)

        # Scale analysis scoring
        if indicators.scale_analysis["parameter_percentile"] is not None:
            # Lower percentile = more suppression
            percentile_score = 1 - (
                indicators.scale_analysis["parameter_percentile"] / 100
            )
            score += percentile_score * 0.25
            factors += float(0.25)

        if indicators.scale_analysis["convergence_achieved"] is False:
            score += 0.15
            factors += float(0.15)

        if indicators.scale_analysis["dataset_usage"] == "subsampled":
            ratio = indicators.scale_analysis.get("subsample_ratio", 0.5)
            subsample_score = 1 - ratio
            score += subsample_score * 0.1
            factors += float(0.1)

        # Method classification scoring
        if indicators.method_classification["efficiency_focused"]:
            score += 0.1
            factors += float(0.1)

        # Explicit constraints scoring
        if indicators.explicit_constraints["mentions_constraints"]:
            score += 0.15
            factors += float(0.15)

        # Normalize by factors considered
        if factors > 0:
            return min(1.0, score / factors)

        return 0.0
