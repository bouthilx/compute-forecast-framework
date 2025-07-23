# Quality Command Phase 3: Integration Implementation Plan (Updated)

**Date**: 2025-01-10
**Time**: 18:30
**Task**: Updated implementation plan for Phase 3 - Integration (1 hour)

## Current State Analysis

### Already Completed Hook Work ✅

1. **`compute_forecast/quality/core/hooks.py`** - FULLY IMPLEMENTED
   - `run_post_command_quality_check()` function complete
   - Quality summary display with Rich panels
   - Error handling that doesn't break main commands
   - Grade calculation and color coding
   - Context integration for showing collection details

2. **`compute_forecast/cli/commands/collect.py`** - FULLY INTEGRATED
   - `--skip-quality-check` option implemented
   - Import of quality hooks already in place
   - Quality check integration at end of collection
   - Proper context passing with total papers, venues, years
   - Error handling that doesn't fail collection command

### What's Missing

1. **Configuration object with defaults** - NOT IMPLEMENTED
2. **End-to-end integration tests** - NOT IMPLEMENTED
3. **Quality check config loading with defaults** - NOT IMPLEMENTED

## Revised Phase 3 Tasks (1 hour total)

### Task 1: Simple Configuration System with Defaults (30 minutes)

**File**: `compute_forecast/quality/core/config.py`

Create a Pydantic-based configuration system with sensible defaults:

```python
"""Configuration management for quality checks with defaults using Pydantic."""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator

from .interfaces import QualityConfig


class QualityThresholds(BaseModel):
    """Quality thresholds configuration."""

    min_completeness: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum completeness score")
    min_coverage: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum coverage score")
    min_consistency: float = Field(default=0.9, ge=0.0, le=1.0, description="Minimum consistency score")
    min_accuracy: float = Field(default=0.85, ge=0.0, le=1.0, description="Minimum accuracy score")


class QualityConfigModel(BaseModel):
    """Pydantic model for quality configuration."""

    stage: str = Field(..., description="Pipeline stage name")
    thresholds: QualityThresholds = Field(default_factory=QualityThresholds, description="Quality thresholds")
    skip_checks: List[str] = Field(default_factory=list, description="List of checks to skip")
    output_format: Literal["text", "json", "markdown"] = Field(default="text", description="Output format")
    verbose: bool = Field(default=False, description="Enable verbose output")

    @validator("stage")
    def validate_stage(cls, v):
        """Validate stage name."""
        if not v or not v.strip():
            raise ValueError("Stage name cannot be empty")
        return v.strip().lower()

    @validator("skip_checks")
    def validate_skip_checks(cls, v):
        """Validate skip checks list."""
        return [check.strip() for check in v if check.strip()]

    def to_quality_config(self) -> QualityConfig:
        """Convert to QualityConfig dataclass."""
        return QualityConfig(
            stage=self.stage,
            thresholds=self.thresholds.dict(),
            skip_checks=self.skip_checks,
            output_format=self.output_format,
            verbose=self.verbose
        )


# Stage-specific default configurations
STAGE_DEFAULTS = {
    "collection": QualityConfigModel(
        stage="collection",
        thresholds=QualityThresholds(
            min_completeness=0.8,
            min_coverage=0.7,
            min_consistency=0.9,
            min_accuracy=0.85
        )
    ),
    "consolidation": QualityConfigModel(
        stage="consolidation",
        thresholds=QualityThresholds(
            min_completeness=0.85,
            min_coverage=0.8,
            min_consistency=0.9,
            min_accuracy=0.85
        )
    ),
    "extraction": QualityConfigModel(
        stage="extraction",
        thresholds=QualityThresholds(
            min_completeness=0.9,
            min_coverage=0.8,
            min_consistency=0.95,
            min_accuracy=0.9
        )
    ),
}


def get_default_quality_config(stage: str) -> QualityConfig:
    """Get default quality configuration for a stage.

    Args:
        stage: Pipeline stage name (e.g., "collection")

    Returns:
        QualityConfig with stage-appropriate defaults
    """
    stage_key = stage.lower().strip()

    # Use stage-specific defaults or fall back to collection defaults
    if stage_key in STAGE_DEFAULTS:
        config_model = STAGE_DEFAULTS[stage_key]
    else:
        # Create default config for unknown stage
        config_model = QualityConfigModel(
            stage=stage_key,
            thresholds=QualityThresholds()  # Use default thresholds
        )

    return config_model.to_quality_config()


def create_quality_config(
    stage: str,
    thresholds: Optional[Dict[str, float]] = None,
    skip_checks: Optional[List[str]] = None,
    output_format: str = "text",
    verbose: bool = False
) -> QualityConfig:
    """Create quality configuration with custom overrides.

    Args:
        stage: Pipeline stage name
        thresholds: Custom threshold overrides
        skip_checks: List of check names to skip
        output_format: Output format ("text", "json", "markdown")
        verbose: Enable verbose output

    Returns:
        QualityConfig with custom settings

    Raises:
        ValidationError: If configuration parameters are invalid
    """
    # Start with default thresholds
    default_thresholds = QualityThresholds()

    # Apply threshold overrides
    if thresholds:
        threshold_dict = default_thresholds.dict()
        threshold_dict.update(thresholds)
        custom_thresholds = QualityThresholds(**threshold_dict)
    else:
        custom_thresholds = default_thresholds

    # Create configuration model with validation
    config_model = QualityConfigModel(
        stage=stage,
        thresholds=custom_thresholds,
        skip_checks=skip_checks or [],
        output_format=output_format,
        verbose=verbose
    )

    return config_model.to_quality_config()


def validate_quality_config(config_dict: Dict[str, Any]) -> QualityConfig:
    """Validate and create quality configuration from dictionary.

    Args:
        config_dict: Dictionary containing configuration parameters

    Returns:
        Validated QualityConfig

    Raises:
        ValidationError: If configuration is invalid
    """
    config_model = QualityConfigModel(**config_dict)
    return config_model.to_quality_config()
```

### Task 2: Update Hook Integration to Use Default Config (30 minutes)

**File**: `compute_forecast/quality/core/hooks.py` (modifications)

Update the existing hook to use the default configuration system:

```python
# Add import at top
from .config import get_default_quality_config

# Update the run_post_command_quality_check function
def run_post_command_quality_check(
    stage: str,
    output_path: Path,
    context: Optional[Dict[str, Any]] = None,
    config: Optional[QualityConfig] = None,
    show_summary: bool = True
) -> Optional[QualityReport]:
    """Run quality checks after a command completes."""
    try:
        runner = QualityRunner()

        # Use provided config or get defaults
        if config is None:
            config = get_default_quality_config(stage)
            config.verbose = False  # Keep integrated checks concise

        # Rest of function remains the same...
        # Run the quality checks
        report = runner.run_checks(stage, output_path, config)

        if show_summary:
            _show_quality_summary(report, context)

        # Handle critical issues
        if report.has_critical_issues():
            console.print("\n[red]⚠️  Critical quality issues detected![/red]")
            console.print("Run [cyan]cf quality --stage collection --verbose[/cyan] for details.")

        return report

    except Exception as e:
        console.print(f"\n[yellow]Warning: Quality checks failed: {e}[/yellow]")
        return None
```

### Task 3: End-to-End Integration Tests (30 minutes)

**File**: `tests/integration/quality/test_config_integration.py`

Create integration tests for default configuration:

```python
"""Integration tests for default configuration with quality checks."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from compute_forecast.quality.core.config import get_default_quality_config, create_quality_config
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
```

## Implementation Dependencies

### Required Python Packages

Pydantic should already be available in the project. If not, add to `pyproject.toml`:
```toml
[dependency-groups]
quality = [
    "pydantic>=2.0.0",  # For configuration validation
    # ... existing dependencies
]
```

## Testing Plan

### Manual Testing Commands

```bash
# Test default configuration
cf collect --venue neurips --year 2024 --max-papers 10

# Test skip quality checks
cf collect --venue neurips --year 2024 --max-papers 10 --skip-quality-check

# Test manual quality command with default config
cf quality --stage collection data/collected_papers/papers_*.json

# Test CLI overrides of default config
cf quality --stage collection --min-completeness 0.95 --verbose data/papers.json
```

## Success Criteria

### Phase 3 Complete When:

1. **✅ Default Configuration System Working**
   - Quality configs loaded with sensible defaults
   - Stage-specific thresholds supported
   - Custom configuration overrides working
   - Clean API for configuration management

2. **✅ Hook Integration Updated**
   - Post-command hooks use default configuration
   - Integration with collect command maintained
   - Error handling preserved

3. **✅ Integration Tests Passing**
   - Default configuration loading tested
   - Hook integration with default config tested
   - End-to-end workflow validated

## Files Modified

### New Files:
- `compute_forecast/quality/core/config.py` - Default configuration management
- `tests/integration/quality/test_config_integration.py` - Integration tests

### Modified Files:
- `compute_forecast/quality/core/hooks.py` - Use default config

## Time Estimate: 1 hour

This simplified plan focuses on creating a clean configuration system with defaults, avoiding the complexity of .env file loading for now. The substantial hook integration work that's already complete will be leveraged with minimal changes.
