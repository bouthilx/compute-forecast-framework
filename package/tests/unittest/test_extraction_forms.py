"""
Unit tests for extraction forms module.

Tests YAML templates and form validation for computational resource extraction.
"""

import pytest
import yaml
from datetime import datetime

from src.analysis.computational.extraction_forms import (
    ExtractionForm,
    FormValidator,
    FormField,
    FieldType,
    FormTemplate
)


@pytest.fixture
def basic_form_data():
    """Basic valid form data for testing."""
    return {
        "metadata": {
            "paper_id": "test_001",
            "extraction_date": "2024-01-01",
            "analyst": "test_analyst"
        },
        "hardware": {
            "gpu_type": "V100",
            "gpu_count": 8,
            "gpu_memory_gb": 16.0
        },
        "training": {
            "total_time_hours": 120.0,
            "time_unit_original": "hours"
        }
    }


@pytest.fixture
def form_validator():
    """Create form validator instance."""
    return FormValidator()


@pytest.fixture
def extraction_form():
    """Create extraction form instance."""
    return ExtractionForm()


class TestFormField:
    """Test FormField dataclass."""
    
    def test_field_creation(self):
        """Test creating form field."""
        field = FormField(
            name="gpu_type",
            field_type=FieldType.TEXT,
            required=True,
            description="Type of GPU used"
        )
        
        assert field.name == "gpu_type"
        assert field.field_type == FieldType.TEXT
        assert field.required is True
        assert field.description == "Type of GPU used"
        assert field.default is None
        assert field.options is None
    
    def test_field_with_options(self):
        """Test field with predefined options."""
        field = FormField(
            name="confidence_level",
            field_type=FieldType.ENUM,
            options=["LOW", "MEDIUM", "HIGH"],
            default="LOW"
        )
        
        assert field.options == ["LOW", "MEDIUM", "HIGH"]
        assert field.default == "LOW"
    
    def test_field_types(self):
        """Test different field types."""
        text_field = FormField("text", FieldType.TEXT)
        assert text_field.field_type == FieldType.TEXT
        
        number_field = FormField("number", FieldType.NUMBER)
        assert number_field.field_type == FieldType.NUMBER
        
        date_field = FormField("date", FieldType.DATE)
        assert date_field.field_type == FieldType.DATE


class TestFormTemplate:
    """Test FormTemplate class."""
    
    def test_template_creation(self):
        """Test creating form template."""
        fields = [
            FormField("gpu_type", FieldType.TEXT, required=True),
            FormField("gpu_count", FieldType.INTEGER, required=True)
        ]
        
        template = FormTemplate(
            name="hardware_specs",
            version="1.0",
            fields=fields
        )
        
        assert template.name == "hardware_specs"
        assert template.version == "1.0"
        assert len(template.fields) == 2
        assert template.description is None
    
    def test_template_to_yaml(self):
        """Test converting template to YAML."""
        fields = [
            FormField("gpu_type", FieldType.TEXT, required=True, description="GPU model"),
            FormField("gpu_count", FieldType.INTEGER, required=True, default=1)
        ]
        
        template = FormTemplate(
            name="hardware_specs",
            version="1.0",
            fields=fields,
            description="Hardware specifications template"
        )
        
        yaml_str = template.to_yaml()
        data = yaml.safe_load(yaml_str)
        
        assert data["name"] == "hardware_specs"
        assert data["version"] == "1.0"
        assert data["description"] == "Hardware specifications template"
        assert len(data["fields"]) == 2
        assert data["fields"][0]["name"] == "gpu_type"
        assert data["fields"][0]["required"] is True


class TestExtractionForm:
    """Test ExtractionForm main class."""
    
    def test_form_initialization(self, extraction_form):
        """Test form initialization."""
        assert extraction_form.metadata_template is not None
        assert extraction_form.hardware_template is not None
        assert extraction_form.training_template is not None
        assert extraction_form.model_template is not None
        assert extraction_form.dataset_template is not None
        assert extraction_form.computation_template is not None
    
    def test_create_empty_form(self, extraction_form):
        """Test creating empty form structure."""
        empty_form = extraction_form.create_empty_form()
        
        # Check main sections exist
        assert "metadata" in empty_form
        assert "hardware" in empty_form
        assert "training" in empty_form
        assert "model" in empty_form
        assert "dataset" in empty_form
        assert "computation" in empty_form
        assert "validation" in empty_form
        assert "notes" in empty_form
        
        # Check metadata has required fields
        assert "paper_id" in empty_form["metadata"]
        assert "extraction_date" in empty_form["metadata"]
        assert "analyst" in empty_form["metadata"]
    
    def test_validate_form_valid(self, extraction_form, basic_form_data):
        """Test validating a valid form."""
        errors = extraction_form.validate_form(basic_form_data)
        assert len(errors) == 0
    
    def test_validate_form_missing_required(self, extraction_form):
        """Test validating form with missing required fields."""
        incomplete_data = {
            "metadata": {
                "paper_id": "test_001",
                # Missing extraction_date and analyst
            },
            "hardware": {
                "gpu_type": "V100"
                # Missing gpu_count
            }
        }
        
        errors = extraction_form.validate_form(incomplete_data)
        assert len(errors) > 0
        assert any("extraction_date" in str(error) for error in errors)
        assert any("analyst" in str(error) for error in errors)
    
    def test_validate_form_invalid_types(self, extraction_form):
        """Test validating form with invalid field types."""
        invalid_data = {
            "metadata": {
                "paper_id": "test_001",
                "extraction_date": "2024-01-01",
                "analyst": "test_analyst"
            },
            "hardware": {
                "gpu_count": "eight",  # Should be integer
                "gpu_memory_gb": "16GB"  # Should be number
            }
        }
        
        errors = extraction_form.validate_form(invalid_data)
        assert len(errors) > 0
        assert any("gpu_count" in str(error) for error in errors)
        assert any("gpu_memory_gb" in str(error) for error in errors)
    
    def test_to_yaml(self, extraction_form, basic_form_data):
        """Test converting form to YAML."""
        yaml_str = extraction_form.to_yaml(basic_form_data)
        
        # Check it's valid YAML
        parsed = yaml.safe_load(yaml_str)
        assert parsed is not None
        
        # Check structure is preserved
        assert parsed["metadata"]["paper_id"] == "test_001"
        assert parsed["hardware"]["gpu_type"] == "V100"
        assert parsed["training"]["total_time_hours"] == 120.0
    
    def test_from_yaml(self, extraction_form, basic_form_data):
        """Test loading form from YAML."""
        yaml_str = extraction_form.to_yaml(basic_form_data)
        loaded_data = extraction_form.from_yaml(yaml_str)
        
        # Check data is loaded correctly
        assert loaded_data["metadata"]["paper_id"] == basic_form_data["metadata"]["paper_id"]
        assert loaded_data["hardware"]["gpu_type"] == basic_form_data["hardware"]["gpu_type"]
        assert loaded_data["training"]["total_time_hours"] == basic_form_data["training"]["total_time_hours"]
    
    def test_save_and_load_form(self, extraction_form, basic_form_data, tmp_path):
        """Test saving and loading form to/from file."""
        file_path = tmp_path / "test_form.yaml"
        
        # Save form
        extraction_form.save_form(basic_form_data, file_path)
        assert file_path.exists()
        
        # Load form
        loaded_data = extraction_form.load_form(file_path)
        assert loaded_data["metadata"]["paper_id"] == basic_form_data["metadata"]["paper_id"]
    
    def test_get_all_templates(self, extraction_form):
        """Test getting all form templates."""
        templates = extraction_form.get_all_templates()
        
        assert "metadata" in templates
        assert "hardware" in templates
        assert "training" in templates
        assert "model" in templates
        assert "dataset" in templates
        assert "computation" in templates
        
        # Check each template is a FormTemplate instance
        for template in templates.values():
            assert isinstance(template, FormTemplate)
    
    def test_export_template_schema(self, extraction_form, tmp_path):
        """Test exporting template schema."""
        schema_file = tmp_path / "schema.yaml"
        extraction_form.export_template_schema(schema_file)
        
        assert schema_file.exists()
        
        # Load and check schema
        with open(schema_file) as f:
            schema = yaml.safe_load(f)
        
        assert "metadata" in schema
        assert "hardware" in schema
        assert schema["metadata"]["fields"] is not None


class TestFormValidator:
    """Test FormValidator class."""
    
    def test_validate_required_field(self, form_validator):
        """Test validating required fields."""
        field = FormField("test_field", FieldType.TEXT, required=True)
        
        # Valid case
        errors = form_validator.validate_field(field, "value")
        assert len(errors) == 0
        
        # Missing required field
        errors = form_validator.validate_field(field, None)
        assert len(errors) == 1
        assert "required" in errors[0].lower()
    
    def test_validate_field_type_text(self, form_validator):
        """Test validating text field type."""
        field = FormField("text_field", FieldType.TEXT)
        
        # Valid text
        errors = form_validator.validate_field(field, "valid text")
        assert len(errors) == 0
        
        # Non-string value
        errors = form_validator.validate_field(field, 123)
        assert len(errors) == 1
        assert "must be text" in errors[0].lower()
    
    def test_validate_field_type_integer(self, form_validator):
        """Test validating integer field type."""
        field = FormField("int_field", FieldType.INTEGER)
        
        # Valid integer
        errors = form_validator.validate_field(field, 42)
        assert len(errors) == 0
        
        # Float value
        errors = form_validator.validate_field(field, 42.5)
        assert len(errors) == 1
        assert "must be integer" in errors[0].lower()
        
        # String value
        errors = form_validator.validate_field(field, "42")
        assert len(errors) == 1
    
    def test_validate_field_type_number(self, form_validator):
        """Test validating number field type."""
        field = FormField("num_field", FieldType.NUMBER)
        
        # Valid integer
        errors = form_validator.validate_field(field, 42)
        assert len(errors) == 0
        
        # Valid float
        errors = form_validator.validate_field(field, 42.5)
        assert len(errors) == 0
        
        # String value
        errors = form_validator.validate_field(field, "42.5")
        assert len(errors) == 1
        assert "must be number" in errors[0].lower()
    
    def test_validate_field_type_enum(self, form_validator):
        """Test validating enum field type."""
        field = FormField(
            "enum_field", 
            FieldType.ENUM, 
            options=["LOW", "MEDIUM", "HIGH"]
        )
        
        # Valid option
        errors = form_validator.validate_field(field, "HIGH")
        assert len(errors) == 0
        
        # Invalid option
        errors = form_validator.validate_field(field, "VERY_HIGH")
        assert len(errors) == 1
        assert "must be one of" in errors[0].lower()
    
    def test_validate_field_type_date(self, form_validator):
        """Test validating date field type."""
        field = FormField("date_field", FieldType.DATE)
        
        # Valid ISO date string
        errors = form_validator.validate_field(field, "2024-01-01")
        assert len(errors) == 0
        
        # Valid datetime object
        errors = form_validator.validate_field(field, datetime.now())
        assert len(errors) == 0
        
        # Invalid date string
        errors = form_validator.validate_field(field, "January 1, 2024")
        assert len(errors) == 1
        assert "must be date" in errors[0].lower()
    
    def test_validate_section(self, form_validator):
        """Test validating entire section."""
        template = FormTemplate(
            name="test_section",
            version="1.0",
            fields=[
                FormField("field1", FieldType.TEXT, required=True),
                FormField("field2", FieldType.INTEGER, required=True),
                FormField("field3", FieldType.TEXT, required=False)
            ]
        )
        
        # Valid section
        data = {
            "field1": "value",
            "field2": 42,
            "field3": "optional"
        }
        errors = form_validator.validate_section(template, data)
        assert len(errors) == 0
        
        # Missing required field
        data = {
            "field1": "value"
            # Missing field2
        }
        errors = form_validator.validate_section(template, data)
        assert len(errors) == 1
        assert "field2" in errors[0]
    
    def test_validate_complete_form(self, form_validator, extraction_form, basic_form_data):
        """Test validating complete form."""
        errors = form_validator.validate_complete_form(
            extraction_form.get_all_templates(),
            basic_form_data
        )
        
        # Basic form data should be valid
        assert len(errors) == 0
    
    def test_custom_validation_rules(self, form_validator):
        """Test custom validation rules."""
        # Test GPU count validation
        field = FormField("gpu_count", FieldType.INTEGER)
        
        # Valid GPU count
        errors = form_validator.validate_field(field, 8)
        assert len(errors) == 0
        
        # Extremely high GPU count (should trigger warning)
        errors = form_validator.validate_field(field, 10000)
        # Validator might add warnings for unusual values
        # This depends on implementation
    
    def test_cross_field_validation(self, form_validator):
        """Test validation across multiple fields."""
        
        # This would be caught by consistency checks in the protocol
        # FormValidator focuses on individual field validation


class TestExtractionFormEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_form_validation(self, extraction_form):
        """Test validating completely empty form."""
        errors = extraction_form.validate_form({})
        assert len(errors) > 0
    
    def test_malformed_yaml_loading(self, extraction_form):
        """Test loading malformed YAML."""
        malformed_yaml = "invalid: yaml: content: :"
        
        with pytest.raises(yaml.YAMLError):
            extraction_form.from_yaml(malformed_yaml)
    
    def test_save_form_invalid_path(self, extraction_form, basic_form_data):
        """Test saving form to invalid path."""
        invalid_path = "/nonexistent/directory/form.yaml"
        
        with pytest.raises(Exception):
            extraction_form.save_form(basic_form_data, invalid_path)
    
    def test_load_nonexistent_form(self, extraction_form):
        """Test loading non-existent form file."""
        with pytest.raises(FileNotFoundError):
            extraction_form.load_form("nonexistent.yaml")
    
    def test_field_with_validator_function(self):
        """Test field with custom validator function."""
        def gpu_type_validator(value):
            valid_gpus = ["V100", "A100", "H100", "T4", "P100"]
            if value not in valid_gpus:
                return f"GPU type must be one of: {', '.join(valid_gpus)}"
            return None
        
        FormField(
            "gpu_type",
            FieldType.TEXT,
            validator=gpu_type_validator
        )
        
        # Test would verify validator is called correctly
        # This depends on implementation supporting custom validators