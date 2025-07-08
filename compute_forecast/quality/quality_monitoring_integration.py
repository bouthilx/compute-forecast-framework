"""
Quality Monitoring Integration for Issue #13.
Integrates adaptive quality thresholds with the monitoring and alerting system.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .adaptive_thresholds import AdaptiveThresholdEngine
from .quality_analyzer import QualityAnalyzer
from .quality_filter import QualityFilter
from .quality_structures import (
    QualityMetrics,
    QualityThresholds,
    AdaptationConfig,
    QualityPerformanceMetrics,
    AdaptationStrategy,
)

logger = logging.getLogger(__name__)


class QualityMonitoringIntegration:
    """
    Integration layer between quality assessment system and monitoring/alerting.

    Features:
    - Quality metrics integration with dashboard
    - Alert rules for quality threshold performance
    - Real-time quality monitoring and adaptation
    - Performance analytics for quality system
    """

    def __init__(
        self,
        adaptation_config: Optional[AdaptationConfig] = None,
        enable_monitoring: bool = True,
    ):
        self.adaptation_config = adaptation_config or AdaptationConfig()
        self.enable_monitoring = enable_monitoring

        # Quality system components
        self.threshold_engine = AdaptiveThresholdEngine(self.adaptation_config)
        self.quality_analyzer = QualityAnalyzer()
        self.quality_filters: Dict[str, QualityFilter] = {}

        # Monitoring integration
        self.quality_metrics_history: List[Dict[str, Any]] = []
        self.performance_tracker = QualityPerformanceTracker()

        # Alert integration
        self.quality_alert_rules = {
            "quality_threshold_performance_degradation": {
                "condition": lambda metrics: metrics.get("collection_efficiency", 1.0)
                < 0.7,
                "severity": "WARNING",
                "message": "Quality threshold collection efficiency below 70%",
            },
            "adaptation_failure": {
                "condition": lambda metrics: metrics.get("adaptation_failures", 0) > 3,
                "severity": "CRITICAL",
                "message": "Multiple quality threshold adaptation failures detected",
            },
            "quality_trend_declining": {
                "condition": lambda metrics: metrics.get("quality_trend_direction")
                == "declining",
                "severity": "WARNING",
                "message": "Paper quality trend is declining",
            },
        }

        logger.info("QualityMonitoringIntegration initialized")

    def integrate_with_monitoring_system(self, monitoring_system) -> None:
        """
        Integrate quality system with existing monitoring infrastructure.
        """
        try:
            # Add quality metrics to monitoring system
            if hasattr(monitoring_system, "add_custom_metrics_collector"):
                monitoring_system.add_custom_metrics_collector(
                    "quality_metrics", self._collect_quality_metrics
                )

            # Add quality alert rules to alerting system
            if hasattr(monitoring_system, "alert_system"):
                self._setup_quality_alert_rules(monitoring_system.alert_system)

            logger.info("Quality system integrated with monitoring")

        except Exception as e:
            logger.error(f"Error integrating with monitoring system: {e}")

    def integrate_with_collection_pipeline(self, collection_system) -> None:
        """
        Integrate quality filtering with paper collection pipeline.
        """
        try:
            # Wrap collection methods to include quality assessment
            original_collect_paper = getattr(collection_system, "collect_paper", None)

            if original_collect_paper:

                def quality_aware_collect_paper(paper_data):
                    # Assess paper quality
                    quality_metrics = self.quality_analyzer.assess_paper_quality(
                        paper_data
                    )

                    # Get venue-specific thresholds
                    venue = paper_data.get("venue", "unknown")
                    year = paper_data.get("year")
                    thresholds = self.threshold_engine.get_thresholds(venue, year)

                    # Filter based on quality
                    filter_obj = self._get_quality_filter(venue, year, thresholds)
                    passes, reasons = filter_obj.evaluate_paper(quality_metrics)

                    if passes:
                        # Collect the paper
                        result = original_collect_paper(paper_data)
                        self._record_quality_success(quality_metrics, venue, year)
                        return result
                    else:
                        # Reject the paper
                        self._record_quality_rejection(
                            quality_metrics, reasons, venue, year
                        )
                        logger.debug(
                            f"Paper {paper_data.get('paper_id', 'unknown')} rejected: {reasons}"
                        )
                        return None

                # Replace the collection method
                setattr(collection_system, "collect_paper", quality_aware_collect_paper)

            logger.info("Quality system integrated with collection pipeline")

        except Exception as e:
            logger.error(f"Error integrating with collection pipeline: {e}")

    def update_quality_performance(
        self, venue: str, year: Optional[int] = None
    ) -> None:
        """
        Update quality performance metrics and adapt thresholds if needed.
        """
        try:
            # Calculate performance metrics
            performance_data = self.performance_tracker.calculate_performance_metrics(
                venue, year
            )

            if performance_data:
                # Update thresholds based on performance
                self.threshold_engine.update_thresholds(venue, year, performance_data)

                # Update quality filter with new thresholds
                thresholds = self.threshold_engine.get_thresholds(venue, year)
                filter_key = f"{venue}_{year}" if year else venue
                if filter_key in self.quality_filters:
                    self.quality_filters[filter_key].update_thresholds(thresholds)

                # Record performance update
                self._record_performance_update(venue, year, performance_data)

                logger.debug(f"Updated quality performance for {venue} ({year})")

        except Exception as e:
            logger.error(f"Error updating quality performance for {venue}: {e}")

    def get_quality_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get quality metrics formatted for dashboard display.
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "active_venues": len(self.quality_filters),
            "total_adaptations": 0,
            "average_collection_efficiency": 0.0,
            "quality_trends": {},
            "recent_adaptations": [],
        }

        try:
            # Calculate aggregate metrics
            venue_efficiencies = []
            total_adaptations = 0

            for venue_key, filter_obj in self.quality_filters.items():
                stats = filter_obj.get_filter_statistics()
                venue_efficiencies.append(stats.get("pass_rate", 0.0))

                # Get adaptation count for this venue
                venue_name = venue_key.split("_")[0]
                thresholds = self.threshold_engine.get_thresholds(venue_name)
                total_adaptations += thresholds.adaptation_count

            metrics["total_adaptations"] = total_adaptations
            metrics["average_collection_efficiency"] = (
                sum(venue_efficiencies) / len(venue_efficiencies)
                if venue_efficiencies
                else 0.0
            )

            # Get recent adaptations
            adaptation_stats = self.threshold_engine.get_adaptation_statistics()
            metrics["recent_adaptations"] = adaptation_stats

        except Exception as e:
            logger.error(f"Error getting quality dashboard metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    def _collect_quality_metrics(self) -> Dict[str, Any]:
        """Collect quality metrics for monitoring system."""
        return self.get_quality_dashboard_metrics()

    def _setup_quality_alert_rules(self, alert_system) -> None:
        """Setup quality-specific alert rules."""
        try:
            for rule_name, rule_config in self.quality_alert_rules.items():
                if hasattr(alert_system, "add_alert_rule"):
                    alert_system.add_alert_rule(
                        rule_name,
                        rule_config["condition"],
                        rule_config["severity"],
                        rule_config["message"],
                    )

            logger.info(f"Added {len(self.quality_alert_rules)} quality alert rules")

        except Exception as e:
            logger.error(f"Error setting up quality alert rules: {e}")

    def _get_quality_filter(
        self, venue: str, year: Optional[int], thresholds: QualityThresholds
    ) -> QualityFilter:
        """Get or create quality filter for venue."""
        filter_key = f"{venue}_{year}" if year else venue

        if filter_key not in self.quality_filters:
            self.quality_filters[filter_key] = QualityFilter(thresholds)

        return self.quality_filters[filter_key]

    def _record_quality_success(
        self, metrics: QualityMetrics, venue: str, year: Optional[int]
    ) -> None:
        """Record successful quality assessment."""
        self.performance_tracker.record_success(metrics, venue, year)

    def _record_quality_rejection(
        self,
        metrics: QualityMetrics,
        reasons: List[str],
        venue: str,
        year: Optional[int],
    ) -> None:
        """Record quality rejection."""
        self.performance_tracker.record_rejection(metrics, reasons, venue, year)

    def _record_performance_update(
        self,
        venue: str,
        year: Optional[int],
        performance_data: QualityPerformanceMetrics,
    ) -> None:
        """Record performance update event."""
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "venue": venue,
            "year": year,
            "performance": performance_data.to_dict(),
            "event_type": "performance_update",
        }

        self.quality_metrics_history.append(update_record)

        # Limit history size
        if len(self.quality_metrics_history) > 1000:
            self.quality_metrics_history = self.quality_metrics_history[-500:]


class QualityPerformanceTracker:
    """
    Tracks quality assessment performance for threshold optimization.
    """

    def __init__(self):
        self.venue_performance: Dict[str, List[Dict[str, Any]]] = {}
        self.performance_window_hours = 24

    def record_success(
        self, metrics: QualityMetrics, venue: str, year: Optional[int]
    ) -> None:
        """Record successful quality assessment."""
        venue_key = f"{venue}_{year}" if year else venue

        record = {
            "timestamp": datetime.now(),
            "result": "success",
            "quality_score": metrics.combined_quality_score,
            "confidence": metrics.confidence_level,
            "metrics": metrics.to_dict(),
        }

        if venue_key not in self.venue_performance:
            self.venue_performance[venue_key] = []

        self.venue_performance[venue_key].append(record)
        self._cleanup_old_records(venue_key)

    def record_rejection(
        self,
        metrics: QualityMetrics,
        reasons: List[str],
        venue: str,
        year: Optional[int],
    ) -> None:
        """Record quality rejection."""
        venue_key = f"{venue}_{year}" if year else venue

        record = {
            "timestamp": datetime.now(),
            "result": "rejection",
            "quality_score": metrics.combined_quality_score,
            "confidence": metrics.confidence_level,
            "rejection_reasons": reasons,
            "metrics": metrics.to_dict(),
        }

        if venue_key not in self.venue_performance:
            self.venue_performance[venue_key] = []

        self.venue_performance[venue_key].append(record)
        self._cleanup_old_records(venue_key)

    def calculate_performance_metrics(
        self, venue: str, year: Optional[int]
    ) -> Optional[QualityPerformanceMetrics]:
        """Calculate performance metrics for venue."""
        venue_key = f"{venue}_{year}" if year else venue

        if venue_key not in self.venue_performance:
            return None

        records = self.venue_performance[venue_key]
        if len(records) < 10:  # Need minimum samples
            return None

        # Count results
        successes = [r for r in records if r["result"] == "success"]
        rejections = [r for r in records if r["result"] == "rejection"]

        papers_evaluated = len(records)
        papers_collected = len(successes)
        papers_rejected = len(rejections)

        if papers_evaluated == 0:
            return None

        collection_efficiency = papers_collected / papers_evaluated

        # Calculate quality scores
        quality_scores = [r["quality_score"] for r in records]
        average_quality_score = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        # Create performance metrics
        performance_data = QualityPerformanceMetrics(
            venue=venue,
            evaluation_period_hours=self.performance_window_hours,
            papers_evaluated=papers_evaluated,
            papers_collected=papers_collected,
            papers_rejected=papers_rejected,
            collection_efficiency=collection_efficiency,
            average_quality_score=average_quality_score,
            threshold_hit_rate=collection_efficiency,  # Simplification
        )

        # Calculate precision, recall, etc. (simplified - would need ground truth)
        # For now, use collection efficiency as proxy
        performance_data.precision = collection_efficiency
        performance_data.recall = min(1.0, collection_efficiency * 1.2)  # Estimate
        performance_data.calculate_derived_metrics()

        return performance_data

    def _cleanup_old_records(self, venue_key: str) -> None:
        """Remove old performance records outside the time window."""
        cutoff_time = datetime.now() - timedelta(hours=self.performance_window_hours)

        self.venue_performance[venue_key] = [
            record
            for record in self.venue_performance[venue_key]
            if record["timestamp"] > cutoff_time
        ]

        # Limit total records per venue
        if len(self.venue_performance[venue_key]) > 1000:
            self.venue_performance[venue_key] = self.venue_performance[venue_key][-500:]


# Factory function for easy integration
def create_quality_monitoring_integration(
    adaptation_strategy: AdaptationStrategy = AdaptationStrategy.BALANCED,
    target_collection_efficiency: float = 0.85,
    target_precision: float = 0.80,
    target_recall: float = 0.95,
) -> QualityMonitoringIntegration:
    """
    Create a pre-configured quality monitoring integration.
    """
    config = AdaptationConfig(
        strategy=adaptation_strategy,
        target_collection_efficiency=target_collection_efficiency,
        target_precision=target_precision,
        target_recall=target_recall,
    )

    return QualityMonitoringIntegration(config)
