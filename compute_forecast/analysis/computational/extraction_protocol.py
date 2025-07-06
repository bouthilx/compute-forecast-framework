"""
Systematic and reproducible extraction methodology for computational requirements from papers.

This module implements the M2-4 extraction process design with structured phases,
quality control, and validation for ensuring reproducible computational requirement extraction.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml
import logging

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for extracted information."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExtractionPhase(Enum):
    """Phases of the extraction protocol."""

    PREPARATION = "preparation"
    AUTOMATED = "automated"
    MANUAL = "manual"
    VALIDATION = "validation"
    DOCUMENTATION = "documentation"


@dataclass
class ExtractionMetadata:
    """Metadata for an extraction session."""

    paper_id: str
    title: str
    extraction_date: datetime
    analyst: str
    time_spent_minutes: int = 0
    phase_completed: Optional[ExtractionPhase] = None


@dataclass
class HardwareSpecs:
    """Hardware specifications extracted from paper."""

    gpu_type: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_memory_gb: Optional[float] = None
    tpu_version: Optional[str] = None
    tpu_cores: Optional[int] = None
    nodes_used: Optional[int] = None
    special_hardware: Optional[str] = None


@dataclass
class TrainingSpecs:
    """Training specifications extracted from paper."""

    total_time_hours: Optional[float] = None
    time_unit_original: Optional[str] = None
    pre_training_hours: Optional[float] = None
    fine_tuning_hours: Optional[float] = None
    number_of_runs: int = 1
    wall_clock_time: Optional[float] = None


@dataclass
class ModelSpecs:
    """Model specifications extracted from paper."""

    parameters_count: Optional[float] = None
    parameters_unit: str = "millions"
    architecture: Optional[str] = None
    layers: Optional[int] = None
    hidden_size: Optional[int] = None
    model_size_gb: Optional[float] = None


@dataclass
class DatasetSpecs:
    """Dataset specifications extracted from paper."""

    name: Optional[str] = None
    size_gb: Optional[float] = None
    samples_count: Optional[int] = None
    tokens_count: Optional[int] = None
    batch_size: Optional[int] = None
    sequence_length: Optional[int] = None


@dataclass
class ComputationSpecs:
    """Computational cost specifications."""

    total_gpu_hours: Optional[float] = None
    calculation_method: Optional[str] = None
    estimated_cost_usd: Optional[float] = None
    flops_estimate: Optional[float] = None


@dataclass
class ValidationResults:
    """Validation results for extracted data."""

    confidence_hardware: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_training: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_model: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_overall: ConfidenceLevel = ConfidenceLevel.LOW
    consistency_checks_passed: bool = False
    outliers_flagged: List[str] = field(default_factory=list)


@dataclass
class ExtractionNotes:
    """Notes and observations from extraction process."""

    ambiguities: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    follow_up_needed: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Complete extraction result with all components."""

    metadata: ExtractionMetadata
    automated_extraction: Dict[str, Any] = field(default_factory=dict)
    hardware: HardwareSpecs = field(default_factory=HardwareSpecs)
    training: TrainingSpecs = field(default_factory=TrainingSpecs)
    model: ModelSpecs = field(default_factory=ModelSpecs)
    dataset: DatasetSpecs = field(default_factory=DatasetSpecs)
    computation: ComputationSpecs = field(default_factory=ComputationSpecs)
    validation: ValidationResults = field(default_factory=ValidationResults)
    notes: ExtractionNotes = field(default_factory=ExtractionNotes)


class ExtractionDecisionTree:
    """Decision tree for systematic extraction navigation."""

    DECISION_TREE = {
        "start": {
            "question": "Is computational info in abstract?",
            "yes": "extract_abstract",
            "no": "check_experimental_section",
        },
        "extract_abstract": {
            "question": "Is abstract info sufficient?",
            "yes": "verify_main_text",
            "no": "check_experimental_section",
        },
        "verify_main_text": {
            "question": "Main text confirms abstract claims?",
            "yes": "extract_main_text",
            "no": "flag_inconsistency",
        },
        "check_experimental_section": {
            "question": "Found implementation details in experimental section?",
            "yes": "extract_experimental",
            "no": "check_appendix",
        },
        "extract_experimental": {
            "question": "All required metrics found?",
            "yes": "proceed_validation",
            "no": "check_appendix",
        },
        "check_appendix": {
            "question": "Computational details in appendix?",
            "yes": "extract_appendix",
            "no": "check_github",
        },
        "extract_appendix": {
            "question": "Comprehensive details found?",
            "yes": "proceed_validation",
            "no": "check_github",
        },
        "check_github": {
            "question": "Repository with config files exists?",
            "yes": "extract_github",
            "no": "limited_extraction",
        },
        "extract_github": {
            "question": "Config files provide missing details?",
            "yes": "proceed_validation",
            "no": "limited_extraction",
        },
        "limited_extraction": {
            "action": "Document limited availability",
            "next": "proceed_validation",
        },
        "flag_inconsistency": {
            "action": "Document inconsistency",
            "next": "check_experimental_section",
        },
        "proceed_validation": {"action": "Move to validation phase"},
    }

    @classmethod
    def get_next_step(cls, current_step: str, answer: str) -> str:
        """Get next step in decision tree based on current step and answer."""
        step_info = cls.DECISION_TREE.get(current_step, {})

        if answer.lower() in ["yes", "y"]:
            return step_info.get("yes", "proceed_validation")
        elif answer.lower() in ["no", "n"]:
            return step_info.get("no", "proceed_validation")
        else:
            return step_info.get("next", "proceed_validation")

    @classmethod
    def get_step_info(cls, step: str) -> Dict[str, str]:
        """Get information about a specific step."""
        return cls.DECISION_TREE.get(step, {})


class ExtractionProtocol:
    """Main extraction protocol implementation."""

    # Phase 1: Paper Preparation Keywords
    PREPARATION_KEYWORDS = [
        "computational",
        "gpu",
        "tpu",
        "training",
        "parameters",
        "dataset",
        "experiments",
        "implementation",
        "resources",
    ]

    # Phase 2: Quick scan locations (in priority order)
    SCAN_LOCATIONS = [
        "abstract",
        "experimental_setup",
        "implementation_details",
        "appendix",
        "supplementary_materials",
        "tables",
        "github_repository",
    ]

    # Phase 3: Manual extraction keywords by category
    MANUAL_KEYWORDS = {
        "hardware": ["gpu", "tpu", "cpu", "cluster", "node", "memory", "v100", "a100"],
        "training_time": [
            "hours",
            "days",
            "weeks",
            "training time",
            "wall clock",
            "runtime",
        ],
        "model_scale": [
            "parameters",
            "layers",
            "dimensions",
            "model size",
            "architecture",
        ],
        "dataset": [
            "dataset",
            "samples",
            "tokens",
            "size",
            "batch size",
            "sequence length",
        ],
        "cost": ["gpu-hours", "cost", "credits", "compute", "flops"],
    }

    def __init__(self, paper_content: str, paper_id: str, analyst: str):
        """Initialize extraction protocol for a specific paper."""
        self.paper_content = paper_content
        self.paper_id = paper_id
        self.analyst = analyst
        self.extraction_result = ExtractionResult(
            metadata=ExtractionMetadata(
                paper_id=paper_id,
                title="",  # To be extracted
                extraction_date=datetime.now(),
                analyst=analyst,
            )
        )
        self.decision_tree = ExtractionDecisionTree()

    def phase1_preparation(self) -> Dict[str, Any]:
        """Phase 1: Paper Preparation (15 minutes)."""
        logger.info(f"Starting Phase 1: Paper Preparation for {self.paper_id}")

        phase_start = datetime.now()
        preparation_results = {
            "has_computational_experiments": False,
            "pdf_quality": "unknown",
            "structure_notes": [],
            "quick_scan_results": {},
        }

        # 1.1 Initial Assessment
        computational_indicators = sum(
            1
            for keyword in self.PREPARATION_KEYWORDS
            if keyword.lower() in self.paper_content.lower()
        )
        preparation_results["has_computational_experiments"] = (
            computational_indicators >= 3
        )

        # 1.2 Quick Scan Locations
        for location in self.SCAN_LOCATIONS:
            section_content = self._find_section_content(location)
            if section_content:
                preparation_results["quick_scan_results"][location] = len(
                    section_content
                )
                preparation_results["structure_notes"].append(
                    f"Found {location} section"
                )

        # Update metadata
        phase_duration = (datetime.now() - phase_start).total_seconds() / 60
        self.extraction_result.metadata.time_spent_minutes += int(phase_duration)
        self.extraction_result.metadata.phase_completed = ExtractionPhase.PREPARATION

        logger.info(f"Phase 1 completed in {phase_duration:.1f} minutes")
        return preparation_results

    def phase2_automated_extraction(self, analyzer) -> Dict[str, Any]:
        """Phase 2: Automated Extraction (10 minutes)."""
        logger.info(f"Starting Phase 2: Automated Extraction for {self.paper_id}")

        phase_start = datetime.now()

        # Run automated analyzer
        automated_results = analyzer.analyze(self.paper_content)

        # Store results
        self.extraction_result.automated_extraction = {
            "confidence_score": getattr(automated_results, "confidence", 0.0),
            "fields_found": list(automated_results.__dict__.keys())
            if hasattr(automated_results, "__dict__")
            else [],
            "fields_missing": [],
            "raw_results": automated_results,
        }

        # Update timing
        phase_duration = (datetime.now() - phase_start).total_seconds() / 60
        self.extraction_result.metadata.time_spent_minutes += int(phase_duration)
        self.extraction_result.metadata.phase_completed = ExtractionPhase.AUTOMATED

        logger.info(f"Phase 2 completed in {phase_duration:.1f} minutes")
        return self.extraction_result.automated_extraction

    def phase3_manual_extraction(self) -> Dict[str, Any]:
        """Phase 3: Manual Extraction (20-40 minutes)."""
        logger.info(f"Starting Phase 3: Manual Extraction for {self.paper_id}")

        phase_start = datetime.now()
        manual_results = {}

        # 3.1 Hardware Specifications
        hardware_info = self._extract_hardware_specs()
        self.extraction_result.hardware = HardwareSpecs(**hardware_info)
        manual_results["hardware"] = hardware_info

        # 3.2 Training Time
        training_info = self._extract_training_specs()
        self.extraction_result.training = TrainingSpecs(**training_info)
        manual_results["training"] = training_info

        # 3.3 Model Scale
        model_info = self._extract_model_specs()
        self.extraction_result.model = ModelSpecs(**model_info)
        manual_results["model"] = model_info

        # 3.4 Dataset Information
        dataset_info = self._extract_dataset_specs()
        self.extraction_result.dataset = DatasetSpecs(**dataset_info)
        manual_results["dataset"] = dataset_info

        # 3.5 Computational Cost
        computation_info = self._extract_computation_specs()
        self.extraction_result.computation = ComputationSpecs(**computation_info)
        manual_results["computation"] = computation_info

        # Update timing
        phase_duration = (datetime.now() - phase_start).total_seconds() / 60
        self.extraction_result.metadata.time_spent_minutes += int(phase_duration)
        self.extraction_result.metadata.phase_completed = ExtractionPhase.MANUAL

        logger.info(f"Phase 3 completed in {phase_duration:.1f} minutes")
        return manual_results

    def phase4_validation(self) -> ValidationResults:
        """Phase 4: Validation (10 minutes)."""
        logger.info(f"Starting Phase 4: Validation for {self.paper_id}")

        phase_start = datetime.now()
        validation = ValidationResults()

        # 4.1 Consistency Checks
        consistency_issues = self._run_consistency_checks()
        validation.consistency_checks_passed = len(consistency_issues) == 0

        if consistency_issues:
            self.extraction_result.notes.quality_issues.extend(consistency_issues)

        # 4.2 Uncertainty Assessment
        validation.confidence_hardware = self._assess_confidence("hardware")
        validation.confidence_training = self._assess_confidence("training")
        validation.confidence_model = self._assess_confidence("model")
        validation.confidence_overall = self._assess_overall_confidence(validation)

        # 4.3 Outlier Detection
        outliers = self._detect_outliers()
        validation.outliers_flagged = outliers

        self.extraction_result.validation = validation

        # Update timing
        phase_duration = (datetime.now() - phase_start).total_seconds() / 60
        self.extraction_result.metadata.time_spent_minutes += int(phase_duration)
        self.extraction_result.metadata.phase_completed = ExtractionPhase.VALIDATION

        logger.info(f"Phase 4 completed in {phase_duration:.1f} minutes")
        return validation

    def phase5_documentation(self) -> Dict[str, Any]:
        """Phase 5: Documentation (5 minutes)."""
        logger.info(f"Starting Phase 5: Documentation for {self.paper_id}")

        phase_start = datetime.now()

        # Generate extraction summary
        documentation = {
            "extraction_summary": self._generate_extraction_summary(),
            "yaml_export": self.to_yaml(),
            "completeness_score": self._calculate_completeness_score(),
            "quality_score": self._calculate_quality_score(),
        }

        # Update timing
        phase_duration = (datetime.now() - phase_start).total_seconds() / 60
        self.extraction_result.metadata.time_spent_minutes += int(phase_duration)
        self.extraction_result.metadata.phase_completed = ExtractionPhase.DOCUMENTATION

        logger.info(f"Phase 5 completed in {phase_duration:.1f} minutes")
        logger.info(
            f"Total extraction time: {self.extraction_result.metadata.time_spent_minutes} minutes"
        )

        return documentation

    def _find_section_content(self, section_name: str) -> str:
        """Find content in specific paper sections."""
        # Simple implementation - can be enhanced with more sophisticated parsing
        content_lower = self.paper_content.lower()

        section_patterns = {
            "abstract": ["abstract", "summary"],
            "experimental_setup": ["experimental setup", "experiments", "methodology"],
            "implementation_details": ["implementation", "details", "setup"],
            "appendix": ["appendix", "supplementary"],
            "tables": ["table", "tab."],
            "github_repository": ["github", "repository", "code"],
        }

        patterns = section_patterns.get(section_name, [section_name])
        for pattern in patterns:
            if pattern in content_lower:
                # Extract content around the pattern (simplified)
                start_idx = content_lower.find(pattern)
                return self.paper_content[
                    start_idx : start_idx + 1000
                ]  # Return up to 1000 chars

        return ""

    def _extract_hardware_specs(self) -> Dict[str, Any]:
        """Extract hardware specifications from paper content."""
        hardware_info = {}
        content_lower = self.paper_content.lower()

        # Look for GPU information
        if "v100" in content_lower:
            hardware_info["gpu_type"] = "V100"
        elif "a100" in content_lower:
            hardware_info["gpu_type"] = "A100"
        elif "gpu" in content_lower:
            hardware_info["gpu_type"] = "GPU (type not specified)"

        # Look for TPU information
        if "tpu" in content_lower:
            hardware_info["tpu_version"] = "TPU (version not specified)"

        # This is a simplified implementation - in practice, would use regex patterns
        # from the existing keywords.py module

        return hardware_info

    def _extract_training_specs(self) -> Dict[str, Any]:
        """Extract training specifications from paper content."""
        training_info = {}
        content_lower = self.paper_content.lower()

        # Look for time indicators
        if "hours" in content_lower:
            training_info["time_unit_original"] = "hours"
        elif "days" in content_lower:
            training_info["time_unit_original"] = "days"
        elif "weeks" in content_lower:
            training_info["time_unit_original"] = "weeks"

        return training_info

    def _extract_model_specs(self) -> Dict[str, Any]:
        """Extract model specifications from paper content."""
        model_info = {}
        content_lower = self.paper_content.lower()

        # Look for parameter counts
        if "parameters" in content_lower or "params" in content_lower:
            model_info["parameters_unit"] = "millions"  # Default assumption

        # Look for architecture information
        if "transformer" in content_lower:
            model_info["architecture"] = "Transformer"
        elif "bert" in content_lower:
            model_info["architecture"] = "BERT"
        elif "gpt" in content_lower:
            model_info["architecture"] = "GPT"

        return model_info

    def _extract_dataset_specs(self) -> Dict[str, Any]:
        """Extract dataset specifications from paper content."""
        dataset_info = {}
        content_lower = self.paper_content.lower()

        # Look for common datasets
        dataset_names = ["imagenet", "coco", "wikipedia", "bookcorpus", "glue", "squad"]
        for name in dataset_names:
            if name in content_lower:
                dataset_info["name"] = name.upper()
                break

        return dataset_info

    def _extract_computation_specs(self) -> Dict[str, Any]:
        """Extract computational cost specifications."""
        computation_info = {}
        content_lower = self.paper_content.lower()

        # Look for GPU-hours or cost information
        if "gpu-hours" in content_lower or "gpu hours" in content_lower:
            computation_info["calculation_method"] = "explicit_gpu_hours"
        elif "cost" in content_lower and (
            "$" in self.paper_content or "dollar" in content_lower
        ):
            computation_info["calculation_method"] = "cost_estimate"

        return computation_info

    def _run_consistency_checks(self) -> List[str]:
        """Run consistency checks on extracted data."""
        issues = []

        # Check GPU-hours calculation
        if (
            self.extraction_result.hardware.gpu_count
            and self.extraction_result.training.total_time_hours
        ):
            calculated_gpu_hours = (
                self.extraction_result.hardware.gpu_count
                * self.extraction_result.training.total_time_hours
            )
            if (
                self.extraction_result.computation.total_gpu_hours
                and abs(
                    calculated_gpu_hours
                    - self.extraction_result.computation.total_gpu_hours
                )
                > calculated_gpu_hours * 0.1
            ):  # 10% tolerance
                issues.append("GPU-hours calculation inconsistent")

        # Check model size plausibility
        if self.extraction_result.model.parameters_count:
            if (
                self.extraction_result.model.parameters_count > 1000000
            ):  # > 1T parameters
                issues.append("Model size unusually large")

        return issues

    def _assess_confidence(self, category: str) -> ConfidenceLevel:
        """Assess confidence level for a specific category."""
        # Simplified confidence assessment based on data completeness
        category_data = getattr(self.extraction_result, category)
        if not category_data:
            return ConfidenceLevel.LOW

        # Count non-None fields
        non_none_fields = sum(
            1 for value in category_data.__dict__.values() if value is not None
        )
        total_fields = len(category_data.__dict__)

        completeness_ratio = non_none_fields / total_fields

        if completeness_ratio >= 0.7:
            return ConfidenceLevel.HIGH
        elif completeness_ratio >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _assess_overall_confidence(
        self, validation: ValidationResults
    ) -> ConfidenceLevel:
        """Assess overall confidence based on individual category confidences."""
        confidence_scores = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1,
        }

        total_score = (
            confidence_scores[validation.confidence_hardware]
            + confidence_scores[validation.confidence_training]
            + confidence_scores[validation.confidence_model]
        )

        avg_score = total_score / 3

        if avg_score >= 2.5:
            return ConfidenceLevel.HIGH
        elif avg_score >= 1.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _detect_outliers(self) -> List[str]:
        """Detect potential outliers in extracted data."""
        outliers = []

        # Check for unusually high values
        if (
            self.extraction_result.training.total_time_hours
            and self.extraction_result.training.total_time_hours > 8760
        ):  # > 1 year
            outliers.append("Training time exceeds 1 year")

        if (
            self.extraction_result.computation.total_gpu_hours
            and self.extraction_result.computation.total_gpu_hours > 1000000
        ):  # > 1M GPU-hours
            outliers.append("GPU-hours unusually high")

        return outliers

    def _generate_extraction_summary(self) -> str:
        """Generate a human-readable extraction summary."""
        summary_parts = []

        if self.extraction_result.hardware.gpu_type:
            summary_parts.append(
                f"Hardware: {self.extraction_result.hardware.gpu_type}"
            )

        if self.extraction_result.training.total_time_hours:
            summary_parts.append(
                f"Training: {self.extraction_result.training.total_time_hours} hours"
            )

        if self.extraction_result.model.parameters_count:
            summary_parts.append(
                f"Model: {self.extraction_result.model.parameters_count}M parameters"
            )

        if self.extraction_result.computation.total_gpu_hours:
            summary_parts.append(
                f"Compute: {self.extraction_result.computation.total_gpu_hours} GPU-hours"
            )

        return (
            " | ".join(summary_parts) if summary_parts else "Limited extraction results"
        )

    def _calculate_completeness_score(self) -> float:
        """Calculate completeness score (0-1) based on extracted fields."""
        total_fields = 0
        filled_fields = 0

        for spec_category in [
            self.extraction_result.hardware,
            self.extraction_result.training,
            self.extraction_result.model,
            self.extraction_result.dataset,
            self.extraction_result.computation,
        ]:
            for value in spec_category.__dict__.values():
                total_fields += 1
                if value is not None:
                    filled_fields += 1

        return filled_fields / total_fields if total_fields > 0 else 0.0

    def _calculate_quality_score(self) -> float:
        """Calculate quality score (0-1) based on confidence and consistency."""
        confidence_scores = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.2,
        }

        confidence_score = confidence_scores.get(
            self.extraction_result.validation.confidence_overall, 0.0
        )
        consistency_score = (
            1.0 if self.extraction_result.validation.consistency_checks_passed else 0.5
        )

        return (confidence_score + consistency_score) / 2

    def to_yaml(self) -> str:
        """Export extraction result to YAML format."""

        # Convert dataclasses to dictionaries for YAML serialization
        def dataclass_to_dict(obj):
            if hasattr(obj, "__dict__"):
                result = {}
                for key, value in obj.__dict__.items():
                    if hasattr(value, "__dict__"):
                        result[key] = dataclass_to_dict(value)
                    elif isinstance(value, Enum):
                        result[key] = value.value
                    elif isinstance(value, datetime):
                        result[key] = value.isoformat()
                    else:
                        result[key] = value
                return result
            return obj

        data = dataclass_to_dict(self.extraction_result)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def run_full_protocol(self, analyzer) -> ExtractionResult:
        """Run the complete 5-phase extraction protocol."""
        logger.info(f"Starting full extraction protocol for {self.paper_id}")

        try:
            # Phase 1: Preparation
            self.phase1_preparation()

            # Phase 2: Automated Extraction
            self.phase2_automated_extraction(analyzer)

            # Phase 3: Manual Extraction
            self.phase3_manual_extraction()

            # Phase 4: Validation
            self.phase4_validation()

            # Phase 5: Documentation
            self.phase5_documentation()

            logger.info(
                f"Extraction protocol completed successfully for {self.paper_id}"
            )
            return self.extraction_result

        except Exception as e:
            logger.error(f"Extraction protocol failed for {self.paper_id}: {str(e)}")
            self.extraction_result.notes.quality_issues.append(
                f"Protocol failed: {str(e)}"
            )
            raise
