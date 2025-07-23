"""
Quality Assessment and Adaptive Thresholds Module

This module provides quality assessment, adaptive threshold management,
and quality-based filtering for the paper collection system.
"""

# Existing quality components
from compute_forecast.quality.adaptive_thresholds import AdaptiveThresholdEngine
from compute_forecast.quality.quality_analyzer import QualityAnalyzer
from compute_forecast.quality.threshold_optimizer import ThresholdOptimizer
from compute_forecast.quality.quality_filter import QualityFilter
from compute_forecast.quality.quality_monitoring_integration import (
    QualityMonitoringIntegration,
    QualityPerformanceTracker,
    create_quality_monitoring_integration,
)
from compute_forecast.quality.quality_structures import (
    QualityMetrics,
    QualityThresholds,
    AdaptationConfig,
    QualityTrend,
    QualityPerformanceMetrics,
    AdaptationStrategy,
    QualityTrendDirection,
    DEFAULT_QUALITY_THRESHOLDS,
    DEFAULT_ADAPTATION_CONFIG,
    QUALITY_SCORING_WEIGHTS,
)

# New quality check infrastructure
from .core.interfaces import (
    QualityCheckType,
    QualityIssueLevel,
    QualityIssue,
    QualityCheckResult,
    QualityReport,
    QualityConfig,
)
from .core.runner import QualityRunner
from .core.registry import get_registry, register_stage_checker
from .core.hooks import run_post_command_quality_check
from .stages.base import StageQualityChecker

# Register all available checkers and formatters
from .stages.collection.register import (
    register_collection_checker,
    register_collection_formatters,
)
from .core.formatters import FormatterRegistry
from .core.generic_formatters import (
    GenericTextFormatter,
    GenericJSONFormatter,
    GenericMarkdownFormatter,
)

# Register checkers
register_collection_checker()

# Register formatters
register_collection_formatters()

# Register generic formatters as fallback
FormatterRegistry.register("text", GenericTextFormatter)
FormatterRegistry.register("json", GenericJSONFormatter)
FormatterRegistry.register("markdown", GenericMarkdownFormatter)

__all__ = [
    # Existing components
    "AdaptiveThresholdEngine",
    "QualityAnalyzer",
    "ThresholdOptimizer",
    "QualityFilter",
    "QualityMonitoringIntegration",
    "QualityPerformanceTracker",
    "create_quality_monitoring_integration",
    "QualityMetrics",
    "QualityThresholds",
    "AdaptationConfig",
    "QualityTrend",
    "QualityPerformanceMetrics",
    "AdaptationStrategy",
    "QualityTrendDirection",
    "DEFAULT_QUALITY_THRESHOLDS",
    "DEFAULT_ADAPTATION_CONFIG",
    "QUALITY_SCORING_WEIGHTS",
    # New quality check components
    "QualityCheckType",
    "QualityIssueLevel",
    "QualityIssue",
    "QualityCheckResult",
    "QualityReport",
    "QualityConfig",
    "QualityRunner",
    "StageQualityChecker",
    "get_registry",
    "register_stage_checker",
    "run_post_command_quality_check",
]
