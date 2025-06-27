"""
Quality Assessment and Adaptive Thresholds Module

This module provides quality assessment, adaptive threshold management,
and quality-based filtering for the paper collection system.
"""

from .adaptive_thresholds import AdaptiveThresholdEngine
from .quality_analyzer import QualityAnalyzer
from .threshold_optimizer import ThresholdOptimizer
from .quality_filter import QualityFilter
from .quality_monitoring_integration import (
    QualityMonitoringIntegration,
    QualityPerformanceTracker,
    create_quality_monitoring_integration
)
from .quality_structures import (
    QualityMetrics,
    QualityThresholds,
    AdaptationConfig,
    QualityTrend,
    QualityPerformanceMetrics,
    AdaptationStrategy,
    QualityTrendDirection,
    DEFAULT_QUALITY_THRESHOLDS,
    DEFAULT_ADAPTATION_CONFIG,
    QUALITY_SCORING_WEIGHTS
)

__all__ = [
    'AdaptiveThresholdEngine',
    'QualityAnalyzer', 
    'ThresholdOptimizer',
    'QualityFilter',
    'QualityMonitoringIntegration',
    'QualityPerformanceTracker',
    'create_quality_monitoring_integration',
    'QualityMetrics',
    'QualityThresholds',
    'AdaptationConfig',
    'QualityTrend',
    'QualityPerformanceMetrics',
    'AdaptationStrategy',
    'QualityTrendDirection',
    'DEFAULT_QUALITY_THRESHOLDS',
    'DEFAULT_ADAPTATION_CONFIG',
    'QUALITY_SCORING_WEIGHTS'
]
