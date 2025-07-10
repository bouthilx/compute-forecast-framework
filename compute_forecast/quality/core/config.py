"""Configuration management for quality checks with defaults using Pydantic."""

from typing import Dict, List, Optional, Literal, Any
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
            thresholds=self.thresholds.model_dump(),
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
        threshold_dict = default_thresholds.model_dump()
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