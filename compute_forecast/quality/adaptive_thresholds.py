"""
Adaptive Threshold Engine for Issue #13.
Manages dynamic threshold adjustment based on collection performance and quality trends.
"""

import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

from .quality_structures import (
    QualityThresholds,
    AdaptationConfig,
    QualityTrend,
    QualityPerformanceMetrics,
    AdaptationStrategy,
    QualityTrendDirection,
    DEFAULT_QUALITY_THRESHOLDS,
)

logger = logging.getLogger(__name__)


class AdaptiveThresholdEngine:
    """
    Engine for managing adaptive quality thresholds.

    Features:
    - Dynamic threshold adjustment based on performance feedback
    - Venue-specific threshold management
    - Multiple adaptation strategies (conservative, aggressive, balanced, static)
    - Safety limits to prevent extreme threshold changes
    - Statistical trend analysis for threshold optimization
    """

    def __init__(self, config: AdaptationConfig):
        self.config = config
        self.venue_thresholds: Dict[str, QualityThresholds] = {}
        self.quality_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.adaptation_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        logger.info("AdaptiveThresholdEngine initialized")

    def get_thresholds(
        self, venue: str, year: Optional[int] = None
    ) -> QualityThresholds:
        """
        Get quality thresholds for specific venue and year.
        Creates default thresholds if none exist.
        """
        key = f"{venue}_{year}" if year else venue

        if key not in self.venue_thresholds:
            # Create default thresholds
            self.venue_thresholds[key] = QualityThresholds(
                venue=venue,
                year=year,
                min_citation_count=int(
                    DEFAULT_QUALITY_THRESHOLDS["min_citation_count"]
                ),
                min_paper_quality_score=float(
                    DEFAULT_QUALITY_THRESHOLDS["min_paper_quality_score"]
                ),
                min_combined_quality_score=float(
                    DEFAULT_QUALITY_THRESHOLDS["min_combined_quality_score"]
                ),
                min_venue_quality_score=float(
                    DEFAULT_QUALITY_THRESHOLDS["min_venue_quality_score"]
                ),
                min_venue_impact_factor=float(
                    DEFAULT_QUALITY_THRESHOLDS["min_venue_impact_factor"]
                ),
            )
            logger.info(f"Created default thresholds for {key}")

        return self.venue_thresholds[key]

    def update_thresholds(
        self,
        venue: str,
        year: Optional[int],
        performance_data: QualityPerformanceMetrics,
    ) -> None:
        """
        Update thresholds based on performance feedback.
        """
        if self.config.strategy == AdaptationStrategy.STATIC:
            logger.debug(f"Static strategy - no threshold updates for {venue}")
            return

        key = f"{venue}_{year}" if year else venue
        current_thresholds = self.get_thresholds(venue, year)

        # Calculate threshold adjustments
        adjustments = self._calculate_threshold_adjustments(
            current_thresholds, performance_data
        )

        if not adjustments:
            logger.debug(f"No threshold adjustments needed for {venue}")
            return

        # Apply safety limits
        adjustments = self._apply_safety_limits(adjustments)

        # Update thresholds
        current_thresholds.update_thresholds(adjustments)

        # Record adaptation history
        self._record_adaptation(key, adjustments, performance_data)

        logger.info(f"Updated thresholds for {venue}: {adjustments}")

    def analyze_quality_trends(
        self,
        venue: str,
        metric_name: str,
        quality_history: List[Tuple[datetime, float]],
    ) -> QualityTrend:
        """
        Analyze quality trends for specified venue and metric.
        """
        if len(quality_history) < 3:
            return QualityTrend(
                venue=venue,
                metric_name=metric_name,
                time_window_hours=24,
                trend_direction=QualityTrendDirection.UNKNOWN,
                trend_strength=0.0,
                trend_confidence=0.0,
                slope=0.0,
                r_squared=0.0,
                p_value=1.0,
                sample_count=len(quality_history),
            )

        # Convert to numpy arrays for analysis
        timestamps = np.array([t.timestamp() for t, v in quality_history])
        values = np.array([v for t, v in quality_history])

        # Normalize timestamps to hours from start
        time_hours = (timestamps - timestamps[0]) / 3600

        # Linear regression for trend analysis
        from scipy import stats

        slope, intercept, r_value, p_value, std_err = stats.linregress(
            time_hours, values
        )

        r_squared = r_value**2

        # Determine trend direction and strength
        if abs(slope) < std_err:
            trend_direction = QualityTrendDirection.STABLE
            trend_strength = 1.0 - abs(slope) / (abs(slope) + std_err)
        elif slope > 0:
            trend_direction = QualityTrendDirection.IMPROVING
            trend_strength = min(
                1.0, abs(slope) / values.std() if values.std() > 0 else 0.5
            )
        else:
            trend_direction = QualityTrendDirection.DECLINING
            trend_strength = min(
                1.0, abs(slope) / values.std() if values.std() > 0 else 0.5
            )

        # Calculate prediction for next value
        next_time = time_hours[-1] + 1
        predicted_next_value = slope * next_time + intercept

        return QualityTrend(
            venue=venue,
            metric_name=metric_name,
            time_window_hours=int((timestamps[-1] - timestamps[0]) / 3600),
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            trend_confidence=r_squared,
            slope=slope,
            r_squared=r_squared,
            p_value=p_value,
            sample_count=len(quality_history),
            time_series_data=quality_history,
            predicted_next_value=predicted_next_value,
            prediction_confidence=r_squared,
        )

    def _calculate_threshold_adjustments(
        self,
        current_thresholds: QualityThresholds,
        performance_data: QualityPerformanceMetrics,
    ) -> Dict[str, Any]:
        """
        Calculate threshold adjustments based on performance data.
        """
        adjustments = {}

        # Calculate current performance vs targets
        precision_gap = self.config.target_precision - performance_data.precision
        recall_gap = self.config.target_recall - performance_data.recall
        efficiency_gap = (
            self.config.target_collection_efficiency
            - performance_data.collection_efficiency
        )

        # Determine adjustment direction and magnitude
        learning_rate = self._get_strategy_learning_rate()

        # Adjust paper quality score threshold
        if precision_gap > 0.05:  # Precision too low - increase thresholds
            adjustment = learning_rate * precision_gap
            new_value = current_thresholds.min_paper_quality_score + adjustment
            adjustments["min_paper_quality_score"] = min(1.0, new_value)
        elif recall_gap > 0.05:  # Recall too low - decrease thresholds
            adjustment = learning_rate * recall_gap
            new_value = current_thresholds.min_paper_quality_score - adjustment
            adjustments["min_paper_quality_score"] = max(0.0, new_value)

        # Adjust combined quality score threshold
        if efficiency_gap > 0.05:  # Efficiency too low - adjust based on primary gap
            if precision_gap > recall_gap:
                adjustment = learning_rate * efficiency_gap
                new_value = current_thresholds.min_combined_quality_score + adjustment
            else:
                adjustment = learning_rate * efficiency_gap
                new_value = current_thresholds.min_combined_quality_score - adjustment
            adjustments["min_combined_quality_score"] = np.clip(new_value, 0.0, 1.0)

        # Limit maximum change per update
        max_change = self.config.max_threshold_adjustment_per_step
        for key, value in adjustments.items():
            current_value = getattr(current_thresholds, key)
            change = abs(value - current_value)
            if change > max_change:
                direction = 1 if value > current_value else -1
                adjustments[key] = current_value + (direction * max_change)

        return adjustments

    def _get_strategy_learning_rate(self) -> float:
        """Get learning rate based on adaptation strategy."""
        base_rate = self.config.learning_rate

        if self.config.strategy == AdaptationStrategy.CONSERVATIVE:
            return base_rate * 0.5
        elif self.config.strategy == AdaptationStrategy.AGGRESSIVE:
            return base_rate * 2.0
        else:  # BALANCED
            return base_rate

    def _apply_safety_limits(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """Apply safety limits to threshold adjustments."""
        safe_adjustments = {}

        for key, value in adjustments.items():
            # Apply absolute minimum limits
            if key in self.config.absolute_minimum_thresholds:
                value = max(value, self.config.absolute_minimum_thresholds[key])

            # Apply absolute maximum limits
            if key in self.config.absolute_maximum_thresholds:
                value = min(value, self.config.absolute_maximum_thresholds[key])

            safe_adjustments[key] = value

        return safe_adjustments

    def _record_adaptation(
        self,
        venue_key: str,
        adjustments: Dict[str, Any],
        performance_data: QualityPerformanceMetrics,
    ) -> None:
        """Record adaptation history for analysis."""
        adaptation_record = {
            "timestamp": datetime.now().isoformat(),
            "adjustments": adjustments,
            "performance": {
                "precision": performance_data.precision,
                "recall": performance_data.recall,
                "f1_score": performance_data.f1_score,
                "collection_efficiency": performance_data.collection_efficiency,
            },
            "strategy": self.config.strategy.value,
        }

        self.adaptation_history[venue_key].append(adaptation_record)

        # Limit history size
        if len(self.adaptation_history[venue_key]) > 100:
            self.adaptation_history[venue_key] = self.adaptation_history[venue_key][
                -50:
            ]

    def get_adaptation_history(
        self, venue: str, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get adaptation history for venue."""
        key = f"{venue}_{year}" if year else venue
        return self.adaptation_history.get(key, [])

    def get_adaptation_statistics(self) -> Dict[str, Any]:
        """Get overall adaptation statistics."""
        total_adaptations = sum(
            len(history) for history in self.adaptation_history.values()
        )
        active_venues = len(self.venue_thresholds)

        # Calculate average performance improvement
        performance_improvements = []
        for history in self.adaptation_history.values():
            if len(history) >= 2:
                recent = history[-1]["performance"]
                older = history[-2]["performance"]
                improvement = recent["f1_score"] - older["f1_score"]
                performance_improvements.append(improvement)

        avg_improvement = (
            np.mean(performance_improvements) if performance_improvements else 0.0
        )

        return {
            "total_adaptations": total_adaptations,
            "active_venues": active_venues,
            "average_performance_improvement": avg_improvement,
            "adaptation_strategies": {
                venue: self.config.strategy.value
                for venue in self.venue_thresholds.keys()
            },
        }
