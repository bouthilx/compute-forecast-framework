"""Normalization engine for extracted values."""

import re
from typing import Dict, Any, Tuple, Optional, Union

from .template_engine import ExtractionField


class NormalizationEngine:
    """Normalize extracted values to standard units."""
    
    def __init__(self):
        self.time_conversions = {
            "minutes": 1/60,
            "hours": 1,
            "days": 24,
            "weeks": 24 * 7
        }
        
        self.memory_conversions = {
            "MB": 1/1024,
            "GB": 1,
            "TB": 1024
        }
        
        self.parameter_conversions = {
            "K": 1e-3,
            "M": 1,
            "B": 1e3,
            "T": 1e6
        }
        
        # GPU name mappings
        self.gpu_mappings = {
            "V100": ["V100", "Tesla V100", "V100-SXM2", "V100-PCIE", "NVIDIA V100"],
            "A100": ["A100", "A100-SXM4", "A100-PCIE", "A100 40GB", "A100 80GB", "NVIDIA A100"],
            "H100": ["H100", "H100-SXM5", "H100-PCIE", "NVIDIA H100"],
            "RTX 3090": ["RTX 3090", "GeForce RTX 3090", "3090"],
            "RTX 4090": ["RTX 4090", "GeForce RTX 4090", "4090"]
        }
    
    def normalize_time_to_hours(self, value: float, unit: str) -> float:
        """Convert time to hours."""
        return value * self.time_conversions.get(unit, 1)
    
    def normalize_memory_to_gb(self, value: float, unit: str) -> float:
        """Convert memory to GB."""
        return value * self.memory_conversions.get(unit, 1)
    
    def normalize_parameters_to_millions(self, value: float, unit: str) -> float:
        """Convert parameters to millions."""
        return value * self.parameter_conversions.get(unit, 1)
    
    def normalize_gpu_names(self, gpu_name: str) -> str:
        """Normalize GPU naming variations."""
        gpu_name = gpu_name.strip()
        
        for canonical, variations in self.gpu_mappings.items():
            for var in variations:
                if var.lower() in gpu_name.lower():
                    return canonical
        
        return gpu_name
    
    def extract_value_and_unit(self, text: Union[str, float, int]) -> Tuple[Optional[float], Optional[str]]:
        """Extract numeric value and unit from string."""
        if isinstance(text, (int, float)):
            return float(text), None
        
        if not isinstance(text, str):
            return None, None
        
        # Pattern to match number followed by optional unit
        # Handles: "7 days", "168 hours", "32GB", "1.5TB", "340M", "1.5B parameters"
        pattern = r'(\d+\.?\d*)\s*([a-zA-Z]+)?'
        match = re.search(pattern, text)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2) if match.group(2) else None
            
            # Handle special cases
            if unit:
                unit = unit.strip()
                # Map common variations
                if unit.lower() == "billion":
                    unit = "B"
                elif unit.lower() == "million":
                    unit = "M"
                elif unit.lower() == "thousand":
                    unit = "K"
                elif unit.lower() in ["parameters", "params"]:
                    # Check if there's a scale indicator before
                    if "billion" in text.lower() or " b " in text.lower():
                        unit = "B"
                    elif "million" in text.lower() or " m " in text.lower():
                        unit = "M"
                    else:
                        unit = None
            
            return value, unit
        
        return None, None
    
    def normalize_field_value(self, field: ExtractionField, value: Any) -> Any:
        """Normalize a specific field value."""
        if value is None:
            return None
        
        # GPU type normalization
        if field == ExtractionField.GPU_TYPE:
            return self.normalize_gpu_names(str(value))
        
        # Time fields - normalize to hours
        if field == ExtractionField.TRAINING_TIME_HOURS:
            if isinstance(value, str):
                num_val, unit = self.extract_value_and_unit(value)
                if num_val is not None:
                    if unit:
                        return self.normalize_time_to_hours(num_val, unit)
                    return num_val
            return float(value)
        
        # Parameter fields - normalize to millions
        if field == ExtractionField.PARAMETERS_COUNT:
            if isinstance(value, str):
                num_val, unit = self.extract_value_and_unit(value)
                if num_val is not None:
                    if unit:
                        return self.normalize_parameters_to_millions(num_val, unit)
                    # If no unit, assume already in millions if reasonable
                    if num_val < 1000:  # Likely already in millions
                        return num_val
                    else:  # Likely in base units
                        return num_val / 1e6
            # If numeric, check magnitude to determine if conversion needed
            num_val = float(value)
            if num_val < 1000:  # Already in millions (or billions converted to millions)
                return num_val
            else:  # In base units, convert to millions
                return num_val / 1e6
        
        # Memory/dataset size fields - normalize to GB
        if field in [ExtractionField.DATASET_SIZE_GB, ExtractionField.GPU_MEMORY_GB]:
            if isinstance(value, str):
                num_val, unit = self.extract_value_and_unit(value)
                if num_val is not None:
                    if unit:
                        return self.normalize_memory_to_gb(num_val, unit)
                    return num_val
            return float(value)
        
        # Numeric fields that don't need conversion
        if isinstance(value, (int, float)):
            return value
        
        # Try to extract numeric value from string
        if isinstance(value, str):
            num_val, _ = self.extract_value_and_unit(value)
            if num_val is not None:
                return num_val
        
        # Return as-is if can't normalize
        return value
    
    def normalize_extraction(self, 
                           extraction: Dict[ExtractionField, Any]) -> Dict[ExtractionField, Any]:
        """Normalize all values in an extraction."""
        normalized = {}
        
        for field, value in extraction.items():
            normalized[field] = self.normalize_field_value(field, value)
        
        return normalized