"""Integration tests for default configuration with quality checks."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from compute_forecast.quality.core.config import (
    get_default_quality_config, 
    create_quality_config,
    QualityThresholds,
    QualityConfigModel,
)
from compute_forecast.quality.core.hooks import run_post_command_quality_check


class TestConfigIntegration:
    """Test default configuration integration with quality system."""
    
    def test_default_config_loading(self):
        """Test default configuration loading."""
        config = get_default_quality_config("collection")
        
        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.8
        assert config.thresholds["min_coverage"] == 0.7
        assert config.thresholds["min_consistency"] == 0.9
        assert config.thresholds["min_accuracy"] == 0.85
        assert config.output_format == "text"
        assert config.verbose is False
        assert config.skip_checks == []
    
    def test_custom_config_creation(self):
        """Test custom configuration creation with overrides."""
        custom_thresholds = {
            "min_completeness": 0.9,
            "min_coverage": 0.85
        }
        
        config = create_quality_config(
            stage="collection",
            thresholds=custom_thresholds,
            skip_checks=["url_validation", "abstract_check"],
            output_format="json",
            verbose=True
        )
        
        assert config.thresholds["min_completeness"] == 0.9
        assert config.thresholds["min_coverage"] == 0.85
        assert config.thresholds["min_consistency"] == 0.9  # Should keep default
        assert "url_validation" in config.skip_checks
        assert "abstract_check" in config.skip_checks
        assert config.verbose is True
        assert config.output_format == "json"
    
    def test_config_validation(self):
        """Test Pydantic validation of configuration."""
        from pydantic import ValidationError
        
        # Test invalid threshold values
        with pytest.raises(ValidationError):
            create_quality_config(
                stage="collection",
                thresholds={"min_completeness": 1.5}  # > 1.0
            )
        
        with pytest.raises(ValidationError):
            create_quality_config(
                stage="collection",
                thresholds={"min_coverage": -0.1}  # < 0.0
            )
        
        # Test invalid output format
        with pytest.raises(ValidationError):
            create_quality_config(
                stage="collection",
                output_format="invalid_format"
            )
        
        # Test empty stage name
        with pytest.raises(ValidationError):
            create_quality_config(stage="")
    
    def test_stage_defaults(self):
        """Test different stage-specific defaults."""
        collection_config = get_default_quality_config("collection")
        consolidation_config = get_default_quality_config("consolidation")
        extraction_config = get_default_quality_config("extraction")
        
        # Collection defaults
        assert collection_config.thresholds["min_completeness"] == 0.8
        
        # Consolidation has higher standards
        assert consolidation_config.thresholds["min_completeness"] == 0.85
        
        # Extraction has highest standards
        assert extraction_config.thresholds["min_completeness"] == 0.9
        assert extraction_config.thresholds["min_consistency"] == 0.95
    
    def test_post_command_hook_with_default_config(self):
        """Test post-command hook uses default configuration."""
        with TemporaryDirectory() as tmp_dir:
            # Create test data
            test_data = {
                "collection_metadata": {
                    "total_papers": 2,
                    "venues": ["Test Venue"],
                    "years": [2024]
                },
                "papers": [
                    {
                        "title": "Test Paper 1",
                        "authors": ["Dr. Test Author"],
                        "venue": "Test Venue",
                        "year": 2024,
                        "abstract": "Test abstract",
                        "paper_id": "test_1"
                    },
                    {
                        "title": "Test Paper 2",
                        "authors": ["Dr. Another Author"],
                        "venue": "Test Venue",
                        "year": 2024,
                        "abstract": "Another test abstract",
                        "paper_id": "test_2"
                    }
                ]
            }
            
            data_file = Path(tmp_dir) / "test_data.json"
            import json
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
            
            # Test with default config
            report = run_post_command_quality_check(
                stage="collection",
                output_path=data_file,
                context={"total_papers": 2},
                show_summary=False
            )
            
            assert report is not None
            assert report.stage == "collection"
    
    def test_post_command_hook_with_custom_config(self):
        """Test post-command hook with custom configuration."""
        with TemporaryDirectory() as tmp_dir:
            # Create test data
            test_data = {
                "collection_metadata": {
                    "total_papers": 1,
                    "venues": ["Test Venue"],
                    "years": [2024]
                },
                "papers": [
                    {
                        "title": "Test Paper",
                        "authors": ["Dr. Test Author"],
                        "venue": "Test Venue",
                        "year": 2024,
                        "abstract": "Test abstract",
                        "paper_id": "test_1"
                    }
                ]
            }
            
            data_file = Path(tmp_dir) / "test_data.json"
            import json
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
            
            # Test with custom config
            custom_config = create_quality_config(
                stage="collection",
                thresholds={"min_completeness": 0.9},
                verbose=True
            )
            
            report = run_post_command_quality_check(
                stage="collection",
                output_path=data_file,
                context={"total_papers": 1},
                config=custom_config,
                show_summary=False
            )
            
            assert report is not None
            assert report.stage == "collection"
    
    def test_config_model_serialization(self):
        """Test Pydantic model serialization and deserialization."""
        # Create a config model
        model = QualityConfigModel(
            stage="collection",
            thresholds=QualityThresholds(min_completeness=0.95),
            skip_checks=["test_check"],
            output_format="json",
            verbose=True
        )
        
        # Serialize to dict
        data = model.model_dump()
        
        assert data["stage"] == "collection"
        assert data["thresholds"]["min_completeness"] == 0.95
        assert data["skip_checks"] == ["test_check"]
        
        # Deserialize back
        restored_model = QualityConfigModel(**data)
        assert restored_model.stage == model.stage
        assert restored_model.thresholds.min_completeness == 0.95
    
    def test_config_usage_in_quality_command(self):
        """Test configuration usage simulating quality command flow."""
        # Simulate command line arguments
        stage = "collection"
        min_completeness = 0.95
        output_format = "json"
        
        # Create config as the command would
        config = create_quality_config(
            stage=stage,
            thresholds={"min_completeness": min_completeness} if min_completeness else None,
            output_format=output_format
        )
        
        assert config.stage == "collection"
        assert config.thresholds["min_completeness"] == 0.95
        assert config.output_format == "json"
        
        # Defaults should be preserved for unspecified thresholds
        assert config.thresholds["min_coverage"] == 0.7
        assert config.thresholds["min_consistency"] == 0.9