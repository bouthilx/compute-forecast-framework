"""
Extraction validation framework extending the quality system.

This module provides comprehensive validation for computational extraction results,
including confidence scoring, cross-validation, consistency checking, and outlier detection.
"""

from compute_forecast.pipeline.content_extraction.quality.extraction_validator import (
    ExtractionQualityValidator,
    ExtractionValidation,
    ExtractionQuality,
)
from compute_forecast.pipeline.content_extraction.quality.consistency_checker import (
    ExtractionConsistencyChecker,
    ConsistencyCheck,
)
from compute_forecast.pipeline.content_extraction.quality.cross_validation import (
    CrossValidationFramework,
)
from compute_forecast.pipeline.content_extraction.quality.outlier_detection import (
    OutlierDetector,
)
from compute_forecast.pipeline.content_extraction.quality.integrated_validator import (
    IntegratedExtractionValidator,
    IntegratedValidationResult,
)

__all__ = [
    "ExtractionQualityValidator",
    "ExtractionValidation",
    "ExtractionQuality",
    "ExtractionConsistencyChecker",
    "ConsistencyCheck",
    "CrossValidationFramework",
    "OutlierDetector",
    "IntegratedExtractionValidator",
    "IntegratedValidationResult",
]
