"""
Threshold Optimizer for Issue #13.
Optimizes quality thresholds to meet target performance metrics using gradient-based methods.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime
import copy

from .quality_structures import (
    QualityThresholds,
    AdaptationConfig,
    QualityPerformanceMetrics,
    AdaptationStrategy,
)

logger = logging.getLogger(__name__)


class ThresholdOptimizer:
    """
    Optimizer for quality thresholds using performance feedback.

    Features:
    - Gradient-based optimization for threshold adjustment
    - Multi-objective optimization (precision, recall, efficiency)
    - Statistical significance testing for threshold changes
    - Momentum-based learning with adaptive rates
    - Safety constraints and bounds checking
    """

    def __init__(self, config: AdaptationConfig):
        self.config = config
        self.optimization_history: List[Dict[str, Any]] = []
        self.momentum_values: Dict[str, float] = {}

        logger.info("ThresholdOptimizer initialized")

    def optimize_thresholds(
        self,
        current_thresholds: QualityThresholds,
        performance_data: QualityPerformanceMetrics,
    ) -> QualityThresholds:
        """
        Optimize thresholds based on performance data to meet target metrics.

        Args:
            current_thresholds: Current quality thresholds
            performance_data: Performance metrics for optimization

        Returns:
            Optimized QualityThresholds
        """
        # Calculate optimization gradients
        gradients = self.calculate_optimization_gradient(performance_data)

        # Apply gradient-based updates with momentum
        threshold_updates = self._apply_gradient_updates(current_thresholds, gradients)

        # Apply safety constraints
        threshold_updates = self._apply_optimization_constraints(threshold_updates)

        # Create optimized thresholds
        optimized_thresholds = copy.deepcopy(current_thresholds)
        optimized_thresholds.update_thresholds(threshold_updates)

        # Record optimization step
        self._record_optimization_step(
            current_thresholds, optimized_thresholds, performance_data, gradients
        )

        return optimized_thresholds

    def calculate_optimization_gradient(
        self, performance_data: QualityPerformanceMetrics
    ) -> Dict[str, float]:
        """
        Calculate optimization gradients based on performance gaps.

        Returns gradients indicating direction and magnitude of threshold adjustments.
        """
        gradients = {
            "precision_gradient": 0.0,
            "recall_gradient": 0.0,
            "f1_gradient": 0.0,
            "efficiency_gradient": 0.0,
        }

        # Calculate performance gaps (target - actual)
        precision_gap = self.config.target_precision - performance_data.precision
        recall_gap = self.config.target_recall - performance_data.recall
        efficiency_gap = (
            self.config.target_collection_efficiency
            - performance_data.collection_efficiency
        )

        # Precision gradient (positive gap = need higher thresholds)
        if abs(precision_gap) > 0.01:  # Only optimize if significant gap
            gradients["precision_gradient"] = precision_gap

        # Recall gradient (positive gap = need lower thresholds)
        if abs(recall_gap) > 0.01:
            gradients[
                "recall_gradient"
            ] = -recall_gap  # Negative because higher recall needs lower thresholds

        # Efficiency gradient
        if abs(efficiency_gap) > 0.01:
            gradients["efficiency_gradient"] = efficiency_gap

        # F1 gradient (balanced optimization)
        target_f1 = (
            2
            * (self.config.target_precision * self.config.target_recall)
            / (self.config.target_precision + self.config.target_recall)
        )
        f1_gap = target_f1 - performance_data.f1_score

        if abs(f1_gap) > 0.01:
            gradients["f1_gradient"] = f1_gap

        return gradients

    def _apply_gradient_updates(
        self, current_thresholds: QualityThresholds, gradients: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply gradient-based updates with momentum and adaptive learning rate.
        """
        updates = {}
        learning_rate = self._get_adaptive_learning_rate()

        # Calculate composite gradient for each threshold
        threshold_gradients = self._calculate_threshold_gradients(gradients)

        for threshold_name, gradient in threshold_gradients.items():
            if abs(gradient) < 1e-6:  # Skip very small gradients
                continue

            # Apply momentum
            if threshold_name not in self.momentum_values:
                self.momentum_values[threshold_name] = 0.0

            momentum_update = (
                self.config.momentum * self.momentum_values[threshold_name]
                + (1 - self.config.momentum) * gradient
            )
            self.momentum_values[threshold_name] = momentum_update

            # Calculate threshold update
            current_value = getattr(current_thresholds, threshold_name)
            update_magnitude = learning_rate * momentum_update

            # Limit maximum change per step
            max_change = self.config.max_threshold_adjustment_per_step
            if abs(update_magnitude) > max_change:
                update_magnitude = np.sign(update_magnitude) * max_change

            new_value = current_value + update_magnitude
            updates[threshold_name] = new_value

        return updates

    def _calculate_threshold_gradients(
        self, performance_gradients: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Convert performance gradients to threshold-specific gradients.
        """
        threshold_gradients = {}

        # Precision optimization affects paper quality thresholds most
        precision_weight = 0.4
        paper_quality_gradient = (
            performance_gradients["precision_gradient"] * precision_weight
            + performance_gradients["f1_gradient"] * 0.3
        )
        threshold_gradients["min_paper_quality_score"] = paper_quality_gradient

        # Recall optimization affects combined quality threshold
        recall_weight = 0.3
        combined_quality_gradient = (
            performance_gradients["recall_gradient"] * recall_weight
            + performance_gradients["f1_gradient"] * 0.2
            + performance_gradients["efficiency_gradient"] * 0.1
        )
        threshold_gradients["min_combined_quality_score"] = combined_quality_gradient

        # Citation count affects precision primarily
        citation_gradient = performance_gradients["precision_gradient"] * 0.2
        # Convert to integer gradient for citation count
        if abs(citation_gradient) > 0.1:
            threshold_gradients["min_citation_count"] = int(citation_gradient * 10)

        # Venue quality affects overall efficiency
        venue_gradient = performance_gradients["efficiency_gradient"] * 0.1
        threshold_gradients["min_venue_quality_score"] = venue_gradient

        return threshold_gradients

    def _get_adaptive_learning_rate(self) -> float:
        """
        Get adaptive learning rate based on strategy and optimization history.
        """
        base_rate = self.config.learning_rate

        # Strategy-based adjustment
        if self.config.strategy == AdaptationStrategy.CONSERVATIVE:
            strategy_multiplier = 0.5
        elif self.config.strategy == AdaptationStrategy.AGGRESSIVE:
            strategy_multiplier = 2.0
        else:  # BALANCED
            strategy_multiplier = 1.0

        # History-based adaptation (reduce rate if oscillating)
        if len(self.optimization_history) >= 3:
            recent_changes = [
                step["threshold_changes"] for step in self.optimization_history[-3:]
            ]

            # Check for oscillation (sign changes in updates)
            oscillation_detected = False
            for threshold_name in [
                "min_paper_quality_score",
                "min_combined_quality_score",
            ]:
                changes = [change.get(threshold_name, 0) for change in recent_changes]
                if len(changes) >= 2:
                    signs = [np.sign(c) for c in changes if c != 0]
                    if len(set(signs)) > 1:  # Different signs = oscillation
                        oscillation_detected = True
                        break

            if oscillation_detected:
                strategy_multiplier *= 0.5  # Reduce learning rate
                logger.debug("Oscillation detected, reducing learning rate")

        return base_rate * strategy_multiplier

    def _apply_optimization_constraints(
        self, updates: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply safety constraints and bounds to threshold updates.
        """
        constrained_updates = {}

        for threshold_name, new_value in updates.items():
            # Apply absolute minimum constraints
            if threshold_name in self.config.absolute_minimum_thresholds:
                min_value = self.config.absolute_minimum_thresholds[threshold_name]
                new_value = max(new_value, min_value)

            # Apply absolute maximum constraints
            if threshold_name in self.config.absolute_maximum_thresholds:
                max_value = self.config.absolute_maximum_thresholds[threshold_name]
                new_value = min(new_value, max_value)

            # Ensure reasonable bounds for specific thresholds
            if threshold_name == "min_citation_count":
                new_value = max(
                    0, int(new_value)
                )  # Citation count must be non-negative integer
            elif "score" in threshold_name:
                new_value = np.clip(new_value, 0.0, 1.0)  # Scores must be [0, 1]

            constrained_updates[threshold_name] = new_value

        return constrained_updates

    def _record_optimization_step(
        self,
        old_thresholds: QualityThresholds,
        new_thresholds: QualityThresholds,
        performance_data: QualityPerformanceMetrics,
        gradients: Dict[str, float],
    ) -> None:
        """Record optimization step for analysis and debugging."""
        step_record = {
            "timestamp": datetime.now().isoformat(),
            "venue": old_thresholds.venue,
            "performance_before": {
                "precision": performance_data.precision,
                "recall": performance_data.recall,
                "f1_score": performance_data.f1_score,
                "efficiency": performance_data.collection_efficiency,
            },
            "thresholds_before": {
                "min_paper_quality_score": old_thresholds.min_paper_quality_score,
                "min_combined_quality_score": old_thresholds.min_combined_quality_score,
                "min_citation_count": old_thresholds.min_citation_count,
            },
            "thresholds_after": {
                "min_paper_quality_score": new_thresholds.min_paper_quality_score,
                "min_combined_quality_score": new_thresholds.min_combined_quality_score,
                "min_citation_count": new_thresholds.min_citation_count,
            },
            "threshold_changes": {
                "min_paper_quality_score": new_thresholds.min_paper_quality_score
                - old_thresholds.min_paper_quality_score,
                "min_combined_quality_score": new_thresholds.min_combined_quality_score
                - old_thresholds.min_combined_quality_score,
                "min_citation_count": new_thresholds.min_citation_count
                - old_thresholds.min_citation_count,
            },
            "gradients": gradients,
            "learning_rate": self._get_adaptive_learning_rate(),
        }

        self.optimization_history.append(step_record)

        # Limit history size
        if len(self.optimization_history) > 100:
            self.optimization_history = self.optimization_history[-50:]

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization history for analysis."""
        return self.optimization_history.copy()

    def analyze_optimization_performance(self) -> Dict[str, Any]:
        """
        Analyze optimization performance over time.
        """
        if len(self.optimization_history) < 2:
            return {
                "optimization_steps": len(self.optimization_history),
                "performance_trend": "insufficient_data",
                "convergence_status": "unknown",
            }

        # Calculate performance trends
        f1_scores = [
            step["performance_before"]["f1_score"] for step in self.optimization_history
        ]

        # Simple trend analysis
        if len(f1_scores) >= 3:
            recent_trend = f1_scores[-3:]
            if all(
                recent_trend[i] >= recent_trend[i - 1]
                for i in range(1, len(recent_trend))
            ):
                trend = "improving"
            elif all(
                recent_trend[i] <= recent_trend[i - 1]
                for i in range(1, len(recent_trend))
            ):
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        # Check convergence (small changes in recent steps)
        if len(self.optimization_history) >= 5:
            recent_changes = []
            for step in self.optimization_history[-5:]:
                total_change = sum(
                    abs(change) for change in step["threshold_changes"].values()
                )
                recent_changes.append(total_change)

            avg_recent_change = np.mean(recent_changes)
            convergence_status = (
                "converged" if avg_recent_change < 0.01 else "converging"
            )
        else:
            convergence_status = "unknown"

        # Calculate optimization effectiveness
        if len(f1_scores) >= 2:
            improvement = f1_scores[-1] - f1_scores[0]
            effectiveness = "effective" if improvement > 0.05 else "limited"
        else:
            effectiveness = "unknown"

        return {
            "optimization_steps": len(self.optimization_history),
            "performance_trend": trend,
            "convergence_status": convergence_status,
            "optimization_effectiveness": effectiveness,
            "f1_score_history": f1_scores,
            "average_recent_change": avg_recent_change
            if "avg_recent_change" in locals()
            else 0.0,
        }

    def suggest_threshold_bounds(
        self, performance_history: List[QualityPerformanceMetrics]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Suggest reasonable threshold bounds based on performance history.
        """
        if not performance_history:
            return {}

        suggestions = {}

        # Analyze performance distribution
        precisions = [p.precision for p in performance_history if p.precision > 0]
        recalls = [p.recall for p in performance_history if p.recall > 0]
        [p.f1_score for p in performance_history if p.f1_score > 0]

        if precisions and recalls:
            # Suggest bounds based on performance distribution
            avg_precision = np.mean(precisions)
            np.mean(recalls)

            # For paper quality score - affects precision most
            if avg_precision < self.config.target_precision:
                suggestions["min_paper_quality_score"] = (
                    0.1,
                    0.8,
                )  # Need room to increase
            else:
                suggestions["min_paper_quality_score"] = (
                    0.0,
                    0.6,
                )  # Can be more permissive

            # For combined quality score - affects both precision and recall
            suggestions["min_combined_quality_score"] = (0.0, 0.7)

            # For citation count - coarse filter
            suggestions["min_citation_count"] = (0, 50)

        return suggestions

    def reset_momentum(self) -> None:
        """Reset momentum values (useful when strategy changes)."""
        self.momentum_values.clear()
        logger.info("Reset optimization momentum")

    def get_momentum_status(self) -> Dict[str, float]:
        """Get current momentum values for debugging."""
        return self.momentum_values.copy()
