"""Validation rules engine for extracted values."""

from dataclasses import dataclass
from typing import Dict, List, Any
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
        self.rules: Dict[str, List[ValidationRule]] = {}
        self.load_default_rules()
    
    def load_default_rules(self):
        """Load default validation rules."""
        # Placeholder - to be implemented
        pass