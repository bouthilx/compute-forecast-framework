"""
Extraction validation framework extending the quality system.

This module provides comprehensive validation for computational extraction results,
including confidence scoring, cross-validation, consistency checking, and outlier detection.
"""

from .extraction_validator import ExtractionQualityValidator, ExtractionValidation, ExtractionQuality
from .consistency_checker import ExtractionConsistencyChecker, ConsistencyCheck
from .cross_validation import CrossValidationFramework
from .outlier_detection import OutlierDetector

__all__ = [
    'ExtractionQualityValidator',
    'ExtractionValidation',
    'ExtractionQuality',
    'ExtractionConsistencyChecker',
    'ConsistencyCheck',
    'CrossValidationFramework',
    'OutlierDetector'
]