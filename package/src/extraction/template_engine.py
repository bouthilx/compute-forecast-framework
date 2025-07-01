"""
Template engine for standardized extraction of computational requirements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from src.analysis.computational.analyzer import ComputationalAnalyzer
from src.data.models import Paper, ComputationalAnalysis


class ExtractionField(Enum):
    """Standardized fields for computational requirement extraction."""
    
    # Hardware specifications
    GPU_COUNT = "gpu_count"
    GPU_TYPE = "gpu_type"
    GPU_MEMORY_GB = "gpu_memory_gb"
    TPU_VERSION = "tpu_version"
    TPU_CORES = "tpu_cores"
    
    # Training metrics
    TRAINING_TIME_HOURS = "training_time_hours"
    TRAINING_STEPS = "training_steps"
    BATCH_SIZE = "batch_size"
    GRADIENT_ACCUMULATION = "gradient_accumulation"
    
    # Model specifications
    PARAMETERS_COUNT = "parameters_count"
    LAYERS_COUNT = "layers_count"
    ATTENTION_HEADS = "attention_heads"
    HIDDEN_SIZE = "hidden_size"
    
    # Dataset specifications
    DATASET_SIZE_GB = "dataset_size_gb"
    DATASET_SAMPLES = "dataset_samples"
    SEQUENCE_LENGTH = "sequence_length"
    
    # Computational cost
    TOTAL_COMPUTE_HOURS = "total_compute_hours"
    ESTIMATED_COST_USD = "estimated_cost_usd"
    CARBON_FOOTPRINT_KG = "carbon_footprint_kg"


@dataclass(frozen=True)
class ExtractionTemplate:
    """Standardized template for computational requirement extraction."""
    
    template_id: str
    template_name: str
    version: str
    
    # Required fields for this template
    required_fields: List[ExtractionField]
    optional_fields: List[ExtractionField]
    
    # Validation rules
    validation_rules: Dict[ExtractionField, Dict[str, Any]] = field(default_factory=dict)
    
    # Normalization rules
    normalization_rules: Dict[ExtractionField, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate field types."""
        for field_list in [self.required_fields, self.optional_fields]:
            for field_item in field_list:
                if not isinstance(field_item, ExtractionField):
                    raise TypeError(f"Field must be ExtractionField enum, got {type(field_item)}")
    
    def calculate_completeness(self, extracted_fields: Dict[ExtractionField, Any]) -> float:
        """Calculate completeness score based on required fields."""
        if not self.required_fields:
            return 1.0
        
        present_required = sum(
            1 for field in self.required_fields 
            if field in extracted_fields
        )
        
        return present_required / len(self.required_fields)


class ExtractionTemplateEngine:
    """Engine for standardized extraction using templates."""
    
    def __init__(self):
        self.analyzer = ComputationalAnalyzer()
        self.templates: Dict[str, ExtractionTemplate] = {}
        self.load_default_templates()
    
    def load_default_templates(self):
        """Load default extraction templates."""
        # Will be implemented with DefaultTemplates class
        pass
    
    def register_template(self, template: ExtractionTemplate):
        """Register a new extraction template."""
        self.templates[template.template_id] = template
    
    def extract_to_template(self, 
                          paper: Paper, 
                          template_id: str) -> Dict[str, Any]:
        """Extract paper data according to template."""
        if template_id not in self.templates:
            raise ValueError(f"Template '{template_id}' not found")
        
        # 1. Run computational analyzer
        raw_analysis = self.analyzer.analyze(paper)
        
        # 2. Map to template fields
        template = self.templates[template_id]
        extracted = self.map_to_template(raw_analysis, template)
        
        # 3. Validate against rules
        validation_results = self.validate_extraction(extracted, template)
        
        # 4. Normalize values
        normalized = self.normalize_values(extracted, template)
        
        return {
            "template_id": template_id,
            "extracted_fields": normalized,
            "validation_results": validation_results,
            "confidence_scores": self.calculate_field_confidence(normalized, raw_analysis),
            "completeness": template.calculate_completeness(normalized)
        }
    
    def map_to_template(self, 
                       analysis: Dict[str, Any], 
                       template: ExtractionTemplate) -> Dict[ExtractionField, Any]:
        """Map analyzer output to template fields."""
        extracted = {}
        
        # Extract resource metrics that match template fields
        resource_metrics = analysis.get('resource_metrics', {})
        
        # Map common fields
        field_mappings = {
            ExtractionField.GPU_COUNT: resource_metrics.get('gpu_count'),
            ExtractionField.GPU_TYPE: resource_metrics.get('gpu_type'),
            ExtractionField.TRAINING_TIME_HOURS: resource_metrics.get('training_time'),
            ExtractionField.PARAMETERS_COUNT: resource_metrics.get('model_parameters'),
            ExtractionField.BATCH_SIZE: resource_metrics.get('batch_size'),
            ExtractionField.DATASET_SIZE_GB: resource_metrics.get('dataset_size'),
            ExtractionField.SEQUENCE_LENGTH: resource_metrics.get('sequence_length'),
            ExtractionField.GPU_MEMORY_GB: resource_metrics.get('gpu_memory'),
            ExtractionField.TRAINING_STEPS: resource_metrics.get('training_steps'),
        }
        
        # Only include fields that are in the template
        all_template_fields = set(template.required_fields + template.optional_fields)
        for field, value in field_mappings.items():
            if field in all_template_fields and value is not None:
                extracted[field] = value
        
        return extracted
    
    def validate_extraction(self, 
                          extracted: Dict[ExtractionField, Any], 
                          template: ExtractionTemplate) -> Dict[str, Any]:
        """Validate extracted values against template rules."""
        # Placeholder - will be implemented with ValidationRulesEngine
        return {
            "passed": True,
            "warnings": [],
            "errors": []
        }
    
    def normalize_values(self, 
                        extracted: Dict[ExtractionField, Any], 
                        template: ExtractionTemplate) -> Dict[ExtractionField, Any]:
        """Normalize values to standard units."""
        # Placeholder - will be implemented with NormalizationEngine
        return extracted
    
    def calculate_field_confidence(self, 
                                 extracted: Dict[ExtractionField, Any],
                                 raw_analysis: Dict[str, Any]) -> Dict[ExtractionField, float]:
        """Calculate confidence scores for each extracted field."""
        confidence_scores = {}
        
        # Base confidence from analyzer
        base_confidence = self.analyzer.get_confidence_score(raw_analysis)
        
        # Simple heuristic: assign base confidence to all fields
        # Can be enhanced with field-specific logic
        for field in extracted:
            confidence_scores[field] = base_confidence
        
        return confidence_scores