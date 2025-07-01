"""Tests for validation rules engine."""

import pytest

from src.extraction.validation_rules import ValidationRulesEngine, ValidationRule
from src.extraction.template_engine import ExtractionField


class TestValidationRule:
    """Test ValidationRule dataclass."""

    def test_validation_rule_creation(self):
        """Test creating a validation rule."""
        rule = ValidationRule(
            field=ExtractionField.GPU_COUNT,
            rule_type="range",
            parameters={"min": 1, "max": 10000},
            severity="error"
        )
        
        assert rule.field == ExtractionField.GPU_COUNT
        assert rule.rule_type == "range"
        assert rule.parameters["min"] == 1
        assert rule.parameters["max"] == 10000
        assert rule.severity == "error"


class TestValidationRulesEngine:
    """Test ValidationRulesEngine functionality."""

    def test_engine_initialization(self):
        """Test that validation engine initializes properly."""
        engine = ValidationRulesEngine()
        assert hasattr(engine, 'rules')
        assert isinstance(engine.rules, dict)

    def test_validate_range(self):
        """Test range validation."""
        engine = ValidationRulesEngine()
        
        # Test within range
        assert engine.validate_range(50, 1, 100) is True
        assert engine.validate_range(1, 1, 100) is True
        assert engine.validate_range(100, 1, 100) is True
        
        # Test outside range
        assert engine.validate_range(0, 1, 100) is False
        assert engine.validate_range(101, 1, 100) is False
        assert engine.validate_range(-10, 1, 100) is False

    def test_validate_enum(self):
        """Test enum validation."""
        engine = ValidationRulesEngine()
        
        allowed_gpus = ["V100", "A100", "H100", "RTX 3090", "RTX 4090"]
        
        # Test valid values
        assert engine.validate_enum("A100", allowed_gpus) is True
        assert engine.validate_enum("V100", allowed_gpus) is True
        
        # Test invalid values
        assert engine.validate_enum("GTX 1080", allowed_gpus) is False
        assert engine.validate_enum("A200", allowed_gpus) is False
        assert engine.validate_enum("", allowed_gpus) is False

    def test_validate_gpu_configuration(self):
        """Test GPU configuration validation."""
        engine = ValidationRulesEngine()
        
        # Test realistic configurations
        result = engine.validate_gpu_configuration("A100", 8)
        assert result["valid"] is True
        assert len(result["warnings"]) == 0
        
        result = engine.validate_gpu_configuration("V100", 64)
        assert result["valid"] is True
        assert len(result["warnings"]) == 0
        
        # Test unrealistic configurations
        result = engine.validate_gpu_configuration("RTX 3090", 10000)
        assert result["valid"] is False
        assert "unrealistic" in result["errors"][0].lower()
        
        result = engine.validate_gpu_configuration("A100", 100000)
        assert result["valid"] is False
        assert "unrealistic" in result["errors"][0].lower()

    def test_validate_scaling_laws(self):
        """Test scaling law validation."""
        engine = ValidationRulesEngine()
        
        # Test reasonable scaling
        result = engine.validate_scaling_laws(
            parameters=1e9,  # 1B parameters
            training_time=168,  # 7 days
            dataset_size=100  # 100GB
        )
        assert result["valid"] is True
        
        # Test unreasonable scaling (too little time for model size)
        result = engine.validate_scaling_laws(
            parameters=175e9,  # 175B parameters
            training_time=1,  # 1 hour - way too little
            dataset_size=1000  # 1TB
        )
        assert result["valid"] is False
        assert "scaling" in result["warnings"][0].lower()

    def test_add_rule(self):
        """Test adding custom validation rules."""
        engine = ValidationRulesEngine()
        
        rule = ValidationRule(
            field=ExtractionField.BATCH_SIZE,
            rule_type="range",
            parameters={"min": 1, "max": 10000},
            severity="warning"
        )
        
        engine.add_rule(rule)
        
        # Verify rule was added
        assert ExtractionField.BATCH_SIZE in engine.rules
        assert rule in engine.rules[ExtractionField.BATCH_SIZE]

    def test_validate_field(self):
        """Test validating a single field value."""
        engine = ValidationRulesEngine()
        
        # Add a range rule
        rule = ValidationRule(
            field=ExtractionField.TRAINING_TIME_HOURS,
            rule_type="range",
            parameters={"min": 0.1, "max": 50000},
            severity="error"
        )
        engine.add_rule(rule)
        
        # Test valid value
        result = engine.validate_field(ExtractionField.TRAINING_TIME_HOURS, 100)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Test invalid value
        result = engine.validate_field(ExtractionField.TRAINING_TIME_HOURS, 100000)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["errors"][0]["severity"] == "error"

    def test_validate_extraction(self):
        """Test validating complete extraction results."""
        engine = ValidationRulesEngine()
        
        # Clear default rules to have clean test
        engine.rules = {}
        
        # Add some rules
        engine.add_rule(ValidationRule(
            field=ExtractionField.GPU_COUNT,
            rule_type="range",
            parameters={"min": 1, "max": 10000},
            severity="error"
        ))
        
        engine.add_rule(ValidationRule(
            field=ExtractionField.GPU_TYPE,
            rule_type="enum",
            parameters={"allowed": ["V100", "A100", "H100"]},
            severity="error"
        ))
        
        # Test valid extraction
        extraction = {
            ExtractionField.GPU_COUNT: 8,
            ExtractionField.GPU_TYPE: "A100",
            ExtractionField.TRAINING_TIME_HOURS: 168
        }
        
        result = engine.validate_extraction(extraction)
        assert result["passed"] is True
        assert len(result["errors"]) == 0
        
        # Test invalid extraction
        extraction = {
            ExtractionField.GPU_COUNT: 20000,  # Too many
            ExtractionField.GPU_TYPE: "GTX 1080",  # Not allowed
            ExtractionField.TRAINING_TIME_HOURS: 168
        }
        
        result = engine.validate_extraction(extraction)
        assert result["passed"] is False
        # Should have 3 errors: GPU count range, GPU type enum, and GPU config cross-validation
        assert len(result["errors"]) == 3

    def test_custom_validation_function(self):
        """Test using custom validation functions."""
        engine = ValidationRulesEngine()
        
        def validate_power_of_two(value):
            """Check if value is power of 2."""
            return value > 0 and (value & (value - 1)) == 0
        
        rule = ValidationRule(
            field=ExtractionField.BATCH_SIZE,
            rule_type="custom",
            parameters={"function": validate_power_of_two},
            severity="warning"
        )
        
        engine.add_rule(rule)
        
        # Test valid values (powers of 2)
        result = engine.validate_field(ExtractionField.BATCH_SIZE, 32)
        assert result["valid"] is True
        
        result = engine.validate_field(ExtractionField.BATCH_SIZE, 256)
        assert result["valid"] is True
        
        # Test invalid values
        result = engine.validate_field(ExtractionField.BATCH_SIZE, 33)
        assert result["valid"] is False
        assert result["warnings"][0]["severity"] == "warning"