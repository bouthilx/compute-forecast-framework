"""
Standardized extraction forms and templates for computational requirements.

This module provides YAML-based templates and form utilities for consistent
data collection across different analysts and extraction sessions.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import yaml
from pathlib import Path
import logging
from datetime import datetime

from .extraction_protocol import ExtractionResult

logger = logging.getLogger(__name__)


class ExtractionFormTemplate:
    """Standardized extraction form template in YAML format."""

    @staticmethod
    def get_blank_template() -> Dict[str, Any]:
        """Get a blank extraction form template."""
        return {
            "metadata": {
                "paper_id": "",
                "title": "",
                "authors": [],
                "venue": "",
                "year": None,
                "extraction_date": "",
                "analyst": "",
                "time_spent_minutes": 0,
                "extraction_version": "1.0",
            },
            "automated_extraction": {
                "confidence_score": 0.0,
                "fields_found": [],
                "fields_missing": [],
                "analyzer_version": "",
                "analysis_timestamp": "",
            },
            "hardware": {
                "gpu_type": "",
                "gpu_count": None,
                "gpu_memory_gb": None,
                "tpu_version": "",
                "tpu_cores": None,
                "cpu_cores": None,
                "nodes_used": None,
                "cluster_name": "",
                "special_hardware": "",
                "hardware_notes": "",
            },
            "training": {
                "total_time_hours": None,
                "time_unit_original": "",
                "pre_training_hours": None,
                "fine_tuning_hours": None,
                "inference_time_hours": None,
                "number_of_runs": 1,
                "wall_clock_time": None,
                "distributed_training": False,
                "training_notes": "",
            },
            "model": {
                "parameters_count": None,
                "parameters_unit": "millions",
                "architecture": "",
                "layers": None,
                "hidden_size": None,
                "attention_heads": None,
                "model_size_gb": None,
                "precision": "",
                "model_notes": "",
            },
            "dataset": {
                "name": "",
                "size_gb": None,
                "samples_count": None,
                "tokens_count": None,
                "batch_size": None,
                "sequence_length": None,
                "preprocessing_time": None,
                "dataset_notes": "",
            },
            "computation": {
                "total_gpu_hours": None,
                "total_tpu_hours": None,
                "calculation_method": "",
                "estimated_cost_usd": None,
                "cost_calculation_method": "",
                "flops_estimate": None,
                "energy_consumption_kwh": None,
                "computation_notes": "",
            },
            "validation": {
                "confidence_hardware": "low",
                "confidence_training": "low",
                "confidence_model": "low",
                "confidence_dataset": "low",
                "confidence_computation": "low",
                "confidence_overall": "low",
                "consistency_checks_passed": False,
                "outliers_flagged": [],
                "validation_notes": "",
            },
            "extraction_notes": {
                "paper_sections_reviewed": [],
                "ambiguities": [],
                "assumptions": [],
                "follow_up_needed": [],
                "quality_issues": [],
                "extraction_challenges": [],
                "additional_sources": [],
            },
            "review": {
                "reviewer": "",
                "review_date": "",
                "review_status": "pending",
                "review_comments": [],
                "approved": False,
            },
        }

    @staticmethod
    def get_example_template() -> Dict[str, Any]:
        """Get an example filled extraction form for reference."""
        template = ExtractionFormTemplate.get_blank_template()

        # Fill with example data
        template.update(
            {
                "metadata": {
                    "paper_id": "arxiv_2023_1234_5678",
                    "title": "Scaling Language Models: A Computational Analysis",
                    "authors": ["Smith, J.", "Doe, A.", "Johnson, K."],
                    "venue": "NeurIPS",
                    "year": 2023,
                    "extraction_date": "2024-01-15T10:30:00",
                    "analyst": "analyst_001",
                    "time_spent_minutes": 45,
                    "extraction_version": "1.0",
                },
                "automated_extraction": {
                    "confidence_score": 0.75,
                    "fields_found": ["gpu_type", "training_time", "parameters"],
                    "fields_missing": ["dataset_size", "cost"],
                    "analyzer_version": "2.1.0",
                    "analysis_timestamp": "2024-01-15T10:00:00",
                },
                "hardware": {
                    "gpu_type": "A100",
                    "gpu_count": 64,
                    "gpu_memory_gb": 40,
                    "tpu_version": "",
                    "tpu_cores": None,
                    "cpu_cores": None,
                    "nodes_used": 8,
                    "cluster_name": "internal_cluster",
                    "special_hardware": "",
                    "hardware_notes": "8 nodes with 8 A100 GPUs each",
                },
                "training": {
                    "total_time_hours": 168,
                    "time_unit_original": "1 week",
                    "pre_training_hours": 144,
                    "fine_tuning_hours": 24,
                    "inference_time_hours": None,
                    "number_of_runs": 3,
                    "wall_clock_time": 168,
                    "distributed_training": True,
                    "training_notes": "Training included 3 full runs for statistical significance",
                },
                "model": {
                    "parameters_count": 13000,
                    "parameters_unit": "millions",
                    "architecture": "Transformer",
                    "layers": 40,
                    "hidden_size": 5120,
                    "attention_heads": 40,
                    "model_size_gb": 52,
                    "precision": "fp16",
                    "model_notes": "13B parameter model similar to GPT-3 architecture",
                },
                "dataset": {
                    "name": "Common Crawl + Books",
                    "size_gb": 500,
                    "samples_count": None,
                    "tokens_count": 300000000000,
                    "batch_size": 512,
                    "sequence_length": 2048,
                    "preprocessing_time": 48,
                    "dataset_notes": "300B tokens from web crawl and book corpus",
                },
                "computation": {
                    "total_gpu_hours": 10752,
                    "total_tpu_hours": None,
                    "calculation_method": "64 GPUs × 168 hours",
                    "estimated_cost_usd": 32256,
                    "cost_calculation_method": "$3/GPU-hour estimate",
                    "flops_estimate": 3.2e21,
                    "energy_consumption_kwh": 43008,
                    "computation_notes": "Cost estimated based on cloud pricing",
                },
                "validation": {
                    "confidence_hardware": "high",
                    "confidence_training": "high",
                    "confidence_model": "high",
                    "confidence_dataset": "medium",
                    "confidence_computation": "medium",
                    "confidence_overall": "high",
                    "consistency_checks_passed": True,
                    "outliers_flagged": [],
                    "validation_notes": "All calculations verified and consistent",
                },
                "extraction_notes": {
                    "paper_sections_reviewed": [
                        "abstract",
                        "experimental_setup",
                        "appendix_a",
                    ],
                    "ambiguities": ["Exact preprocessing time unclear"],
                    "assumptions": ["Used $3/GPU-hour for cost estimation"],
                    "follow_up_needed": [],
                    "quality_issues": [],
                    "extraction_challenges": ["Dataset size given in tokens, not GB"],
                    "additional_sources": ["GitHub repository for exact config"],
                },
                "review": {
                    "reviewer": "",
                    "review_date": "",
                    "review_status": "pending",
                    "review_comments": [],
                    "approved": False,
                },
            }
        )

        return template

    @staticmethod
    def save_template(template: Dict[str, Any], filepath: Path) -> None:
        """Save template to YAML file."""
        with open(filepath, "w") as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False, indent=2)
        logger.info(f"Template saved to {filepath}")

    @staticmethod
    def load_template(filepath: Path) -> Dict[str, Any]:
        """Load template from YAML file."""
        with open(filepath, "r") as f:
            template = yaml.safe_load(f)
        logger.info(f"Template loaded from {filepath}")
        return dict(template)


@dataclass
class FormValidationResult:
    """Result of form validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    completeness_score: float


class FormValidator:
    """Validates extraction forms for completeness and consistency."""

    REQUIRED_FIELDS = {
        "metadata": ["paper_id", "analyst", "extraction_date"],
        "hardware": [],  # No strictly required fields - depends on paper
        "training": [],
        "model": [],
        "dataset": [],
        "computation": [],
        "validation": ["confidence_overall"],
    }

    RECOMMENDED_FIELDS = {
        "hardware": ["gpu_type", "gpu_count"],
        "training": ["total_time_hours"],
        "model": ["parameters_count", "architecture"],
        "dataset": ["name"],
        "computation": ["total_gpu_hours"],
    }

    def validate_form(self, form_data: Dict[str, Any]) -> FormValidationResult:
        """Validate extraction form data."""
        errors = []
        warnings = []

        # Check required fields
        for section, fields in self.REQUIRED_FIELDS.items():
            if section not in form_data:
                errors.append(f"Missing required section: {section}")
                continue

            for field in fields:
                if field not in form_data[section] or not form_data[section][field]:
                    errors.append(f"Missing required field: {section}.{field}")

        # Check recommended fields
        total_recommended = 0
        filled_recommended = 0

        for section, fields in self.RECOMMENDED_FIELDS.items():
            if section not in form_data:
                continue

            for field in fields:
                total_recommended += 1
                if (
                    field in form_data[section]
                    and form_data[section][field] is not None
                    and form_data[section][field] != ""
                ):
                    filled_recommended += 1
                else:
                    warnings.append(f"Recommended field missing: {section}.{field}")

        # Calculate completeness score
        completeness_score = (
            filled_recommended / total_recommended if total_recommended > 0 else 1.0
        )

        # Validate confidence levels
        confidence_errors = self._validate_confidence_levels(form_data)
        errors.extend(confidence_errors)

        # Validate consistency
        consistency_warnings = self._validate_consistency(form_data)
        warnings.extend(consistency_warnings)

        return FormValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            completeness_score=completeness_score,
        )

    def _validate_confidence_levels(self, form_data: Dict[str, Any]) -> List[str]:
        """Validate confidence level values."""
        errors = []
        valid_levels = ["low", "medium", "high"]

        if "validation" in form_data:
            confidence_fields = [
                "confidence_hardware",
                "confidence_training",
                "confidence_model",
                "confidence_dataset",
                "confidence_computation",
                "confidence_overall",
            ]

            for field in confidence_fields:
                if field in form_data["validation"]:
                    value = form_data["validation"][field]
                    if value not in valid_levels:
                        errors.append(
                            f"Invalid confidence level '{value}' in {field}. Must be one of: {valid_levels}"
                        )

        return errors

    def _validate_consistency(self, form_data: Dict[str, Any]) -> List[str]:
        """Validate internal consistency of form data."""
        warnings = []

        # Check GPU-hours calculation
        if (
            "hardware" in form_data
            and "training" in form_data
            and "computation" in form_data
        ):
            gpu_count = form_data["hardware"].get("gpu_count")
            training_hours = form_data["training"].get("total_time_hours")
            total_gpu_hours = form_data["computation"].get("total_gpu_hours")

            if all(x is not None for x in [gpu_count, training_hours, total_gpu_hours]):
                calculated = gpu_count * training_hours
                if (
                    abs(calculated - total_gpu_hours) > calculated * 0.1
                ):  # 10% tolerance
                    warnings.append(
                        f"GPU-hours inconsistent: calculated {calculated}, reported {total_gpu_hours}"
                    )

        # Check parameter count vs model size
        if "model" in form_data:
            params = form_data["model"].get("parameters_count")
            size_gb = form_data["model"].get("model_size_gb")

            if params is not None and size_gb is not None:
                # Rough estimate: 4 bytes per parameter
                estimated_size = (params * 1_000_000 * 4) / (1024**3)
                if (
                    abs(estimated_size - size_gb) > estimated_size * 0.5
                ):  # 50% tolerance
                    warnings.append("Model size inconsistent with parameter count")

        return warnings


class FormManager:
    """Manages extraction forms and templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize form manager with templates directory."""
        self.templates_dir = templates_dir or Path("templates/extraction_forms")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self.validator = FormValidator()

        # Create default templates if they don't exist
        self._create_default_templates()

    def _create_default_templates(self):
        """Create default template files."""
        blank_template_path = self.templates_dir / "blank_extraction_form.yaml"
        example_template_path = self.templates_dir / "example_extraction_form.yaml"

        if not blank_template_path.exists():
            blank_template = ExtractionFormTemplate.get_blank_template()
            ExtractionFormTemplate.save_template(blank_template, blank_template_path)

        if not example_template_path.exists():
            example_template = ExtractionFormTemplate.get_example_template()
            ExtractionFormTemplate.save_template(
                example_template, example_template_path
            )

    def create_form_for_paper(
        self,
        paper_id: str,
        analyst: str,
        paper_title: str = "",
        paper_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new extraction form for a specific paper."""
        form = ExtractionFormTemplate.get_blank_template()

        # Pre-fill metadata
        form["metadata"].update(
            {
                "paper_id": paper_id,
                "title": paper_title,
                "year": paper_year,
                "extraction_date": datetime.now().isoformat(),
                "analyst": analyst,
            }
        )

        return form

    def save_form(
        self, form_data: Dict[str, Any], paper_id: str, forms_dir: Optional[Path] = None
    ) -> Path:
        """Save extraction form to file."""
        if forms_dir is None:
            forms_dir = self.templates_dir.parent / "extraction_forms"
        forms_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{paper_id}_{timestamp}.yaml"
        filepath = forms_dir / filename

        ExtractionFormTemplate.save_template(form_data, filepath)
        return filepath

    def load_form(self, filepath: Path) -> Dict[str, Any]:
        """Load extraction form from file."""
        return ExtractionFormTemplate.load_template(filepath)

    def validate_form(self, form_data: Dict[str, Any]) -> FormValidationResult:
        """Validate extraction form."""
        return self.validator.validate_form(form_data)

    def convert_extraction_result_to_form(
        self, result: ExtractionResult
    ) -> Dict[str, Any]:
        """Convert ExtractionResult to form format."""
        form = ExtractionFormTemplate.get_blank_template()

        # Convert metadata
        if result.metadata:
            form["metadata"].update(
                {
                    "paper_id": result.metadata.paper_id,
                    "title": result.metadata.title,
                    "extraction_date": result.metadata.extraction_date.isoformat(),
                    "analyst": result.metadata.analyst,
                    "time_spent_minutes": result.metadata.time_spent_minutes,
                }
            )

        # Convert automated extraction results
        if result.automated_extraction:
            form["automated_extraction"].update(result.automated_extraction)

        # Convert specifications
        if result.hardware:
            form["hardware"].update(
                {k: v for k, v in asdict(result.hardware).items() if v is not None}
            )

        if result.training:
            form["training"].update(
                {k: v for k, v in asdict(result.training).items() if v is not None}
            )

        if result.model:
            form["model"].update(
                {k: v for k, v in asdict(result.model).items() if v is not None}
            )

        if result.dataset:
            form["dataset"].update(
                {k: v for k, v in asdict(result.dataset).items() if v is not None}
            )

        if result.computation:
            form["computation"].update(
                {k: v for k, v in asdict(result.computation).items() if v is not None}
            )

        # Convert validation results
        if result.validation:
            form["validation"].update(
                {
                    "confidence_hardware": result.validation.confidence_hardware.value,
                    "confidence_training": result.validation.confidence_training.value,
                    "confidence_model": result.validation.confidence_model.value,
                    "confidence_overall": result.validation.confidence_overall.value,
                    "consistency_checks_passed": result.validation.consistency_checks_passed,
                    "outliers_flagged": result.validation.outliers_flagged,
                }
            )

        # Convert notes
        if result.notes:
            form["extraction_notes"].update(
                {
                    "ambiguities": result.notes.ambiguities,
                    "assumptions": result.notes.assumptions,
                    "follow_up_needed": result.notes.follow_up_needed,
                    "quality_issues": result.notes.quality_issues,
                }
            )

        return form

    def generate_form_summary(self, form_data: Dict[str, Any]) -> str:
        """Generate a human-readable summary of extraction form."""
        lines = []

        # Metadata summary
        metadata = form_data.get("metadata", {})
        lines.append(f"Paper: {metadata.get('title', 'Unknown')}")
        lines.append(f"ID: {metadata.get('paper_id', 'Unknown')}")
        lines.append(f"Analyst: {metadata.get('analyst', 'Unknown')}")
        lines.append(f"Date: {metadata.get('extraction_date', 'Unknown')}")
        lines.append("")

        # Hardware summary
        hardware = form_data.get("hardware", {})
        if hardware.get("gpu_type") or hardware.get("gpu_count"):
            gpu_info = (
                f"{hardware.get('gpu_count', '?')} × {hardware.get('gpu_type', 'GPU')}"
            )
            lines.append(f"Hardware: {gpu_info}")

        # Training summary
        training = form_data.get("training", {})
        if training.get("total_time_hours"):
            lines.append(f"Training: {training['total_time_hours']} hours")

        # Model summary
        model = form_data.get("model", {})
        if model.get("parameters_count"):
            params = f"{model['parameters_count']}{model.get('parameters_unit', 'M')}"
            arch = model.get("architecture", "")
            lines.append(f"Model: {params} parameters ({arch})")

        # Computation summary
        computation = form_data.get("computation", {})
        if computation.get("total_gpu_hours"):
            lines.append(f"Compute: {computation['total_gpu_hours']} GPU-hours")

        # Confidence summary
        validation = form_data.get("validation", {})
        if validation.get("confidence_overall"):
            lines.append(f"Confidence: {validation['confidence_overall']}")

        return "\n".join(lines)

    def get_template_list(self) -> List[str]:
        """Get list of available template files."""
        if not self.templates_dir.exists():
            return []

        template_files = list(self.templates_dir.glob("*.yaml"))
        return [f.name for f in template_files]

    def export_form_to_csv_row(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export form data as a flattened dictionary suitable for CSV."""
        csv_row = {}

        # Flatten nested structure
        for section_name, section_data in form_data.items():
            if isinstance(section_data, dict):
                for field_name, field_value in section_data.items():
                    csv_row[f"{section_name}_{field_name}"] = field_value
            else:
                csv_row[section_name] = section_data

        return csv_row
