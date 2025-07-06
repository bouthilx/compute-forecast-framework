"""
Quality Assessment Data Structures for Issue #13.
Defines data structures for quality metrics, thresholds, and adaptation configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class QualityTrendDirection(Enum):
    """Quality trend direction enumeration"""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNKNOWN = "unknown"


class AdaptationStrategy(Enum):
    """Threshold adaptation strategy"""

    CONSERVATIVE = "conservative"  # Slower adaptation
    AGGRESSIVE = "aggressive"  # Faster adaptation
    BALANCED = "balanced"  # Default strategy
    STATIC = "static"  # No adaptation


@dataclass
class QualityMetrics:
    """Quality metrics for papers and venues"""

    paper_id: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None

    # Paper quality indicators
    citation_count: int = 0
    author_count: int = 0
    page_count: int = 0
    reference_count: int = 0

    # Venue quality indicators
    venue_impact_factor: float = 0.0
    venue_acceptance_rate: float = 0.0
    venue_h_index: float = 0.0

    # Calculated quality scores
    paper_quality_score: float = 0.0
    venue_quality_score: float = 0.0
    combined_quality_score: float = 0.0

    # Quality confidence
    confidence_level: float = 0.0  # 0.0 to 1.0

    # Metadata
    assessment_timestamp: datetime = field(default_factory=datetime.now)
    calculation_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "paper_id": self.paper_id,
            "venue": self.venue,
            "year": self.year,
            "citation_count": self.citation_count,
            "author_count": self.author_count,
            "page_count": self.page_count,
            "reference_count": self.reference_count,
            "venue_impact_factor": self.venue_impact_factor,
            "venue_acceptance_rate": self.venue_acceptance_rate,
            "venue_h_index": self.venue_h_index,
            "paper_quality_score": self.paper_quality_score,
            "venue_quality_score": self.venue_quality_score,
            "combined_quality_score": self.combined_quality_score,
            "confidence_level": self.confidence_level,
            "assessment_timestamp": self.assessment_timestamp.isoformat(),
            "calculation_version": self.calculation_version,
        }


@dataclass
class QualityThresholds:
    """Quality thresholds for filtering and collection decisions"""

    venue: str
    year: Optional[int] = None

    # Paper quality thresholds
    min_citation_count: int = 0
    min_paper_quality_score: float = 0.0
    min_combined_quality_score: float = 0.0

    # Venue quality thresholds
    min_venue_quality_score: float = 0.0
    min_venue_impact_factor: float = 0.0

    # Adaptive parameters
    adaptation_sensitivity: float = 0.5  # 0.0 to 1.0
    min_samples_for_adaptation: int = 50
    max_threshold_change_per_update: float = 0.1

    # Threshold metadata
    last_updated: datetime = field(default_factory=datetime.now)
    adaptation_count: int = 0
    performance_score: float = 0.0  # How well these thresholds perform

    # Historical tracking
    threshold_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "venue": self.venue,
            "year": self.year,
            "min_citation_count": self.min_citation_count,
            "min_paper_quality_score": self.min_paper_quality_score,
            "min_combined_quality_score": self.min_combined_quality_score,
            "min_venue_quality_score": self.min_venue_quality_score,
            "min_venue_impact_factor": self.min_venue_impact_factor,
            "adaptation_sensitivity": self.adaptation_sensitivity,
            "min_samples_for_adaptation": self.min_samples_for_adaptation,
            "max_threshold_change_per_update": self.max_threshold_change_per_update,
            "last_updated": self.last_updated.isoformat(),
            "adaptation_count": self.adaptation_count,
            "performance_score": self.performance_score,
            "threshold_history": self.threshold_history,
        }

    def update_thresholds(self, new_values: Dict[str, Any]) -> None:
        """Update thresholds and track history"""
        # Save current values to history
        current_values = {
            "timestamp": self.last_updated.isoformat(),
            "min_citation_count": self.min_citation_count,
            "min_paper_quality_score": self.min_paper_quality_score,
            "min_combined_quality_score": self.min_combined_quality_score,
            "min_venue_quality_score": self.min_venue_quality_score,
            "min_venue_impact_factor": self.min_venue_impact_factor,
            "performance_score": self.performance_score,
        }
        self.threshold_history.append(current_values)

        # Limit history size
        if len(self.threshold_history) > 100:
            self.threshold_history = self.threshold_history[-50:]

        # Update thresholds
        for key, value in new_values.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Update metadata
        self.last_updated = datetime.now()
        self.adaptation_count += 1


@dataclass
class AdaptationConfig:
    """Configuration for adaptive threshold behavior"""

    strategy: AdaptationStrategy = AdaptationStrategy.BALANCED

    # Learning parameters
    learning_rate: float = 0.1
    momentum: float = 0.9
    adaptation_window_hours: int = 24

    # Quality targets
    target_collection_efficiency: float = 0.85  # Target % of quality papers
    target_recall: float = 0.95  # Don't miss high-quality papers
    target_precision: float = 0.80  # Minimize low-quality papers

    # Adaptation constraints
    min_adaptation_interval_hours: int = 1
    max_threshold_adjustment_per_step: float = 0.15
    require_statistical_significance: bool = True

    # Performance tracking
    adaptation_performance_window: int = 1000  # Number of papers to evaluate
    enable_feedback_learning: bool = True

    # Safety limits
    absolute_minimum_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "min_citation_count": 0,
            "min_paper_quality_score": 0.0,
            "min_combined_quality_score": 0.0,
        }
    )

    absolute_maximum_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "min_citation_count": 1000,
            "min_paper_quality_score": 1.0,
            "min_combined_quality_score": 1.0,
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "strategy": self.strategy.value,
            "learning_rate": self.learning_rate,
            "momentum": self.momentum,
            "adaptation_window_hours": self.adaptation_window_hours,
            "target_collection_efficiency": self.target_collection_efficiency,
            "target_recall": self.target_recall,
            "target_precision": self.target_precision,
            "min_adaptation_interval_hours": self.min_adaptation_interval_hours,
            "max_threshold_adjustment_per_step": self.max_threshold_adjustment_per_step,
            "require_statistical_significance": self.require_statistical_significance,
            "adaptation_performance_window": self.adaptation_performance_window,
            "enable_feedback_learning": self.enable_feedback_learning,
            "absolute_minimum_thresholds": self.absolute_minimum_thresholds,
            "absolute_maximum_thresholds": self.absolute_maximum_thresholds,
        }


@dataclass
class QualityTrend:
    """Quality trend analysis results"""

    venue: str
    metric_name: str
    time_window_hours: int

    # Trend analysis
    trend_direction: QualityTrendDirection
    trend_strength: float  # 0.0 to 1.0
    trend_confidence: float  # 0.0 to 1.0

    # Statistical measures
    slope: float
    r_squared: float
    p_value: float

    # Trend data
    sample_count: int
    time_series_data: List[Tuple[datetime, float]] = field(default_factory=list)

    # Predictions
    predicted_next_value: Optional[float] = None
    prediction_confidence: Optional[float] = None

    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "venue": self.venue,
            "metric_name": self.metric_name,
            "time_window_hours": self.time_window_hours,
            "trend_direction": self.trend_direction.value,
            "trend_strength": self.trend_strength,
            "trend_confidence": self.trend_confidence,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "p_value": self.p_value,
            "sample_count": self.sample_count,
            "time_series_data": [(t.isoformat(), v) for t, v in self.time_series_data],
            "predicted_next_value": self.predicted_next_value,
            "prediction_confidence": self.prediction_confidence,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class QualityPerformanceMetrics:
    """Performance metrics for quality assessment and filtering"""

    venue: str
    evaluation_period_hours: int

    # Collection performance
    papers_evaluated: int
    papers_collected: int
    papers_rejected: int
    collection_efficiency: float  # % of papers that met quality thresholds

    # Quality performance
    true_positives: int = 0  # High-quality papers correctly collected
    false_positives: int = 0  # Low-quality papers incorrectly collected
    true_negatives: int = 0  # Low-quality papers correctly rejected
    false_negatives: int = 0  # High-quality papers incorrectly rejected

    # Calculated metrics
    precision: float = 0.0  # TP / (TP + FP)
    recall: float = 0.0  # TP / (TP + FN)
    f1_score: float = 0.0  # 2 * (precision * recall) / (precision + recall)
    accuracy: float = 0.0  # (TP + TN) / (TP + TN + FP + FN)

    # Threshold performance
    average_quality_score: float = 0.0
    threshold_hit_rate: float = 0.0  # % of papers that exceeded thresholds

    # Metadata
    evaluation_timestamp: datetime = field(default_factory=datetime.now)
    threshold_version: str = "1.0"

    def calculate_derived_metrics(self) -> None:
        """Calculate precision, recall, F1, and accuracy"""
        total = (
            self.true_positives
            + self.false_positives
            + self.true_negatives
            + self.false_negatives
        )

        if total == 0:
            return

        # Precision
        if (self.true_positives + self.false_positives) > 0:
            self.precision = self.true_positives / (
                self.true_positives + self.false_positives
            )

        # Recall
        if (self.true_positives + self.false_negatives) > 0:
            self.recall = self.true_positives / (
                self.true_positives + self.false_negatives
            )

        # F1 Score
        if (self.precision + self.recall) > 0:
            self.f1_score = (
                2 * (self.precision * self.recall) / (self.precision + self.recall)
            )

        # Accuracy
        self.accuracy = (self.true_positives + self.true_negatives) / total

        # Collection efficiency
        if self.papers_evaluated > 0:
            self.collection_efficiency = self.papers_collected / self.papers_evaluated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "venue": self.venue,
            "evaluation_period_hours": self.evaluation_period_hours,
            "papers_evaluated": self.papers_evaluated,
            "papers_collected": self.papers_collected,
            "papers_rejected": self.papers_rejected,
            "collection_efficiency": self.collection_efficiency,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "average_quality_score": self.average_quality_score,
            "threshold_hit_rate": self.threshold_hit_rate,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat(),
            "threshold_version": self.threshold_version,
        }


# Configuration constants
DEFAULT_QUALITY_THRESHOLDS = {
    "min_citation_count": 5,
    "min_paper_quality_score": 0.3,
    "min_combined_quality_score": 0.4,
    "min_venue_quality_score": 0.5,
    "min_venue_impact_factor": 1.0,
}

DEFAULT_ADAPTATION_CONFIG = AdaptationConfig()

# Quality scoring weights
QUALITY_SCORING_WEIGHTS = {
    "citation_count": 0.3,
    "venue_impact_factor": 0.25,
    "author_count": 0.1,
    "page_count": 0.05,
    "reference_count": 0.1,
    "venue_h_index": 0.2,
}
