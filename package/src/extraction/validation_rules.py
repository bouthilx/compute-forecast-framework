"""Validation rules engine for extracted values."""

from dataclasses import dataclass
from typing import Dict, List, Any, Callable
from .template_engine import ExtractionField


@dataclass
class ValidationRule:
    """Represents a validation rule for a field."""
    field: ExtractionField
    rule_type: str  # "range", "enum", "regex", "custom"
    parameters: Dict[str, Any]
    severity: str  # "error", "warning", "info"


class ValidationRulesEngine:
    """Engine for validating extracted values."""
    
    def __init__(self):
        self.rules: Dict[ExtractionField, List[ValidationRule]] = {}
        self.load_default_rules()
    
    def load_default_rules(self):
        """Load default validation rules."""
        # GPU count validation
        self.add_rule(ValidationRule(
            field=ExtractionField.GPU_COUNT,
            rule_type="range",
            parameters={"min": 1, "max": 10000},
            severity="error"
        ))
        
        # Training time validation
        self.add_rule(ValidationRule(
            field=ExtractionField.TRAINING_TIME_HOURS,
            rule_type="range",
            parameters={"min": 0.1, "max": 50000},
            severity="error"
        ))
        
        # Parameters validation (in millions after normalization)
        self.add_rule(ValidationRule(
            field=ExtractionField.PARAMETERS_COUNT,
            rule_type="range",
            parameters={"min": 0.01, "max": 10000000},  # 10K to 10T parameters in millions
            severity="error"
        ))
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule."""
        if rule.field not in self.rules:
            self.rules[rule.field] = []
        self.rules[rule.field].append(rule)
    
    def validate_range(self, value: Any, min_val: float, max_val: float) -> bool:
        """Validate value is within range."""
        try:
            num_value = float(value)
            return min_val <= num_value <= max_val
        except (ValueError, TypeError):
            return False
    
    def validate_enum(self, value: str, allowed_values: List[str]) -> bool:
        """Validate value is in allowed set."""
        return value in allowed_values
    
    def validate_custom(self, value: Any, function: Callable) -> bool:
        """Validate using custom function."""
        return function(value)
    
    def validate_gpu_configuration(self, 
                                 gpu_type: str, 
                                 gpu_count: int) -> Dict[str, Any]:
        """Validate GPU configuration makes sense."""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Define realistic limits per GPU type
        gpu_limits = {
            "V100": {"typical_max": 64, "absolute_max": 512},
            "A100": {"typical_max": 128, "absolute_max": 1024},
            "H100": {"typical_max": 256, "absolute_max": 2048},
            "RTX 3090": {"typical_max": 8, "absolute_max": 32},
            "RTX 4090": {"typical_max": 8, "absolute_max": 32},
        }
        
        if gpu_type in gpu_limits:
            limits = gpu_limits[gpu_type]
            if gpu_count > limits["absolute_max"]:
                result["valid"] = False
                result["errors"].append(
                    f"Unrealistic GPU count: {gpu_count} {gpu_type}s exceeds "
                    f"reasonable limits ({limits['absolute_max']})"
                )
            elif gpu_count > limits["typical_max"]:
                result["warnings"].append(
                    f"High GPU count: {gpu_count} {gpu_type}s is unusually high"
                )
        
        # General check for extremely high counts
        if gpu_count > 10000:
            result["valid"] = False
            result["errors"].append(
                f"Unrealistic GPU count: {gpu_count} GPUs is implausible"
            )
        
        return result
    
    def validate_scaling_laws(self,
                            parameters: float,
                            training_time: float,
                            dataset_size: float) -> Dict[str, Any]:
        """Validate values follow known scaling laws."""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Simple heuristic based on Chinchilla scaling
        # Rough estimate: 1B params needs ~20-100 hours on modern hardware
        expected_min_hours = (parameters / 1e9) * 20
        expected_max_hours = (parameters / 1e9) * 500
        
        if training_time < expected_min_hours / 10:  # Way too fast
            result["valid"] = False
            result["warnings"].append(
                f"Training time ({training_time}h) seems too short for "
                f"{parameters/1e9:.1f}B parameter model based on scaling laws"
            )
        elif training_time > expected_max_hours * 10:  # Way too slow
            result["warnings"].append(
                f"Training time ({training_time}h) seems excessive for "
                f"{parameters/1e9:.1f}B parameter model"
            )
        
        return result
    
    def validate_field(self, field: ExtractionField, value: Any) -> Dict[str, Any]:
        """Validate a single field value."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        if field not in self.rules:
            return result
        
        for rule in self.rules[field]:
            rule_valid = True
            message = ""
            
            if rule.rule_type == "range":
                min_val = rule.parameters.get("min")
                max_val = rule.parameters.get("max")
                if not self.validate_range(value, min_val, max_val):
                    rule_valid = False
                    message = f"Value {value} outside range [{min_val}, {max_val}]"
            
            elif rule.rule_type == "enum":
                allowed = rule.parameters.get("allowed", [])
                if not self.validate_enum(value, allowed):
                    rule_valid = False
                    message = f"Value '{value}' not in allowed values: {allowed}"
            
            elif rule.rule_type == "custom":
                function = rule.parameters.get("function")
                if function and not self.validate_custom(value, function):
                    rule_valid = False
                    message = f"Value {value} failed custom validation"
            
            if not rule_valid:
                result["valid"] = False
                violation = {
                    "field": field.value,
                    "value": value,
                    "message": message,
                    "severity": rule.severity
                }
                
                if rule.severity == "error":
                    result["errors"].append(violation)
                elif rule.severity == "warning":
                    result["warnings"].append(violation)
                else:
                    result["info"].append(violation)
        
        return result
    
    def validate_extraction(self, 
                          extraction: Dict[ExtractionField, Any]) -> Dict[str, Any]:
        """Validate complete extraction results."""
        result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        # Validate each field
        for field, value in extraction.items():
            field_result = self.validate_field(field, value)
            
            if not field_result["valid"]:
                result["passed"] = False
            
            result["errors"].extend(field_result["errors"])
            result["warnings"].extend(field_result["warnings"])
            result["info"].extend(field_result["info"])
        
        # Additional cross-field validations
        if ExtractionField.GPU_TYPE in extraction and ExtractionField.GPU_COUNT in extraction:
            gpu_result = self.validate_gpu_configuration(
                extraction[ExtractionField.GPU_TYPE],
                extraction[ExtractionField.GPU_COUNT]
            )
            if not gpu_result["valid"]:
                result["passed"] = False
            # Convert GPU config errors to proper format
            for error in gpu_result["errors"]:
                result["errors"].append({
                    "field": "gpu_configuration",
                    "value": f"{extraction[ExtractionField.GPU_COUNT]} x {extraction[ExtractionField.GPU_TYPE]}",
                    "message": error,
                    "severity": "error"
                })
            for warning in gpu_result["warnings"]:
                result["warnings"].append({
                    "field": "gpu_configuration", 
                    "value": f"{extraction[ExtractionField.GPU_COUNT]} x {extraction[ExtractionField.GPU_TYPE]}",
                    "message": warning,
                    "severity": "warning"
                })
        
        return result