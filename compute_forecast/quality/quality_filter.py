"""
Quality Filter for Issue #13.
Filters papers based on quality thresholds with real-time performance requirements.
"""

import logging
from typing import Dict, List, Tuple, Any, cast

from .quality_structures import QualityMetrics, QualityThresholds

logger = logging.getLogger(__name__)


class QualityFilter:
    """
    Filter for quality-based paper collection decisions.

    Features:
    - Real-time quality filtering with millisecond performance
    - Configurable quality thresholds per venue
    - Detailed rejection reasons for analysis
    - Batch processing capabilities
    - Performance tracking for threshold optimization
    """

    def __init__(self, thresholds: QualityThresholds):
        self.thresholds = thresholds
        self.filter_statistics: Dict[str, Any] = {
            "papers_evaluated": 0,
            "papers_passed": 0,
            "papers_rejected": 0,
            "rejection_reasons": {},
        }

        logger.info(f"QualityFilter initialized for {thresholds.venue}")

    def evaluate_paper(self, metrics: QualityMetrics) -> Tuple[bool, List[str]]:
        """
        Evaluate if paper meets quality thresholds.

        Args:
            metrics: QualityMetrics for the paper

        Returns:
            Tuple of (passes_filter, rejection_reasons)
        """
        self.filter_statistics["papers_evaluated"] += 1
        rejection_reasons = []

        # Check citation count threshold
        if metrics.citation_count < self.thresholds.min_citation_count:
            reason = f"Citation count {metrics.citation_count} below threshold {self.thresholds.min_citation_count}"
            rejection_reasons.append(reason)
            self._track_rejection_reason("citation_count")

        # Check paper quality score threshold
        if metrics.paper_quality_score < self.thresholds.min_paper_quality_score:
            reason = f"Paper quality score {metrics.paper_quality_score:.3f} below threshold {self.thresholds.min_paper_quality_score:.3f}"
            rejection_reasons.append(reason)
            self._track_rejection_reason("paper_quality_score")

        # Check combined quality score threshold
        if metrics.combined_quality_score < self.thresholds.min_combined_quality_score:
            reason = f"Combined quality score {metrics.combined_quality_score:.3f} below threshold {self.thresholds.min_combined_quality_score:.3f}"
            rejection_reasons.append(reason)
            self._track_rejection_reason("combined_quality_score")

        # Check venue quality score threshold
        if metrics.venue_quality_score < self.thresholds.min_venue_quality_score:
            reason = f"Venue quality score {metrics.venue_quality_score:.3f} below threshold {self.thresholds.min_venue_quality_score:.3f}"
            rejection_reasons.append(reason)
            self._track_rejection_reason("venue_quality_score")

        # Check venue impact factor threshold
        if metrics.venue_impact_factor < self.thresholds.min_venue_impact_factor:
            reason = f"Venue impact factor {metrics.venue_impact_factor:.3f} below threshold {self.thresholds.min_venue_impact_factor:.3f}"
            rejection_reasons.append(reason)
            self._track_rejection_reason("venue_impact_factor")

        # Determine if paper passes
        passes = len(rejection_reasons) == 0

        # Update statistics
        if passes:
            self.filter_statistics["papers_passed"] += 1
        else:
            self.filter_statistics["papers_rejected"] += 1

        return passes, rejection_reasons

    def filter_papers(
        self, papers: List[QualityMetrics]
    ) -> Dict[str, List[QualityMetrics]]:
        """
        Filter multiple papers efficiently for batch processing.

        Args:
            papers: List of QualityMetrics to filter

        Returns:
            Dictionary with 'passed' and 'failed' lists
        """
        results: Dict[str, List[QualityMetrics]] = {"passed": [], "failed": []}

        for metrics in papers:
            passes, reasons = self.evaluate_paper(metrics)

            if passes:
                results["passed"].append(metrics)
            else:
                results["failed"].append(metrics)

        logger.debug(
            f"Filtered {len(papers)} papers: {len(results['passed'])} passed, {len(results['failed'])} failed"
        )

        return results

    def update_thresholds(self, new_thresholds: QualityThresholds) -> None:
        """Update filter thresholds."""
        old_venue = self.thresholds.venue
        self.thresholds = new_thresholds

        logger.info(f"Updated thresholds for {old_venue} -> {new_thresholds.venue}")

    def get_filter_statistics(self) -> Dict[str, Any]:
        """Get filtering performance statistics."""
        stats = self.filter_statistics.copy()

        # Calculate derived statistics
        if stats["papers_evaluated"] > 0:
            stats["pass_rate"] = stats["papers_passed"] / stats["papers_evaluated"]
            stats["rejection_rate"] = (
                stats["papers_rejected"] / stats["papers_evaluated"]
            )
        else:
            stats["pass_rate"] = 0.0
            stats["rejection_rate"] = 0.0

        # Add threshold information
        stats["current_thresholds"] = {
            "venue": self.thresholds.venue,
            "min_citation_count": self.thresholds.min_citation_count,
            "min_paper_quality_score": self.thresholds.min_paper_quality_score,
            "min_combined_quality_score": self.thresholds.min_combined_quality_score,
            "min_venue_quality_score": self.thresholds.min_venue_quality_score,
            "min_venue_impact_factor": self.thresholds.min_venue_impact_factor,
        }

        return stats

    def reset_statistics(self) -> None:
        """Reset filtering statistics."""
        self.filter_statistics = {
            "papers_evaluated": 0,
            "papers_passed": 0,
            "papers_rejected": 0,
            "rejection_reasons": {},
        }

        logger.info(f"Reset filter statistics for {self.thresholds.venue}")

    def get_rejection_analysis(self) -> Dict[str, Any]:
        """
        Get detailed analysis of rejection reasons.
        Useful for understanding which thresholds are most restrictive.
        """
        total_rejections = self.filter_statistics["papers_rejected"]

        if total_rejections == 0:
            return {
                "total_rejections": 0,
                "rejection_breakdown": {},
                "most_restrictive_threshold": None,
            }

        # Calculate rejection percentages
        rejection_breakdown = {}
        for reason, count in self.filter_statistics["rejection_reasons"].items():
            percentage = (count / total_rejections) * 100
            rejection_breakdown[reason] = {"count": count, "percentage": percentage}

        # Find most restrictive threshold
        most_restrictive = max(
            self.filter_statistics["rejection_reasons"].items(),
            key=lambda x: x[1],
            default=(None, 0),
        )

        return {
            "total_rejections": total_rejections,
            "rejection_breakdown": rejection_breakdown,
            "most_restrictive_threshold": most_restrictive[0]
            if most_restrictive[0]
            else None,
            "most_restrictive_count": most_restrictive[1],
        }

    def _track_rejection_reason(self, reason: str) -> None:
        """Track rejection reason for statistics."""
        if reason not in self.filter_statistics["rejection_reasons"]:
            self.filter_statistics["rejection_reasons"][reason] = 0
        self.filter_statistics["rejection_reasons"][reason] += 1

    def simulate_threshold_impact(
        self, papers: List[QualityMetrics], threshold_changes: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Simulate the impact of threshold changes on a set of papers.
        Useful for threshold optimization without actually changing thresholds.
        """
        # Create temporary thresholds with changes applied
        temp_thresholds = QualityThresholds(
            venue=self.thresholds.venue,
            year=self.thresholds.year,
            min_citation_count=int(
                threshold_changes.get(
                    "min_citation_count", self.thresholds.min_citation_count
                )
            ),
            min_paper_quality_score=threshold_changes.get(
                "min_paper_quality_score", self.thresholds.min_paper_quality_score
            ),
            min_combined_quality_score=threshold_changes.get(
                "min_combined_quality_score", self.thresholds.min_combined_quality_score
            ),
            min_venue_quality_score=threshold_changes.get(
                "min_venue_quality_score", self.thresholds.min_venue_quality_score
            ),
            min_venue_impact_factor=threshold_changes.get(
                "min_venue_impact_factor", self.thresholds.min_venue_impact_factor
            ),
        )

        # Create temporary filter
        temp_filter = QualityFilter(temp_thresholds)

        # Apply filtering
        results = temp_filter.filter_papers(papers)

        # Calculate impact metrics
        original_results = self.filter_papers(papers)

        impact = {
            "original_passed": len(original_results["passed"]),
            "new_passed": len(results["passed"]),
            "original_failed": len(original_results["failed"]),
            "new_failed": len(results["failed"]),
            "change_in_passed": len(results["passed"])
            - len(original_results["passed"]),
            "change_in_failed": len(results["failed"])
            - len(original_results["failed"]),
            "threshold_changes": threshold_changes,
        }

        # Calculate percentage changes
        if len(papers) > 0:
            impact["original_pass_rate"] = len(original_results["passed"]) / len(papers)
            impact["new_pass_rate"] = len(results["passed"]) / len(papers)
            impact["pass_rate_change"] = cast(float, impact["new_pass_rate"]) - cast(
                float, impact["original_pass_rate"]
            )

        return impact

    def is_paper_borderline(
        self, metrics: QualityMetrics, tolerance: float = 0.1
    ) -> Dict[str, bool]:
        """
        Check if paper is borderline (close to thresholds) for each criterion.
        Useful for identifying papers that might be affected by small threshold changes.
        """
        borderline_status = {}

        # Citation count
        citation_diff = abs(metrics.citation_count - self.thresholds.min_citation_count)
        borderline_status["citation_count"] = citation_diff <= (
            self.thresholds.min_citation_count * tolerance
        )

        # Paper quality score
        paper_score_diff = abs(
            metrics.paper_quality_score - self.thresholds.min_paper_quality_score
        )
        borderline_status["paper_quality_score"] = paper_score_diff <= tolerance

        # Combined quality score
        combined_score_diff = abs(
            metrics.combined_quality_score - self.thresholds.min_combined_quality_score
        )
        borderline_status["combined_quality_score"] = combined_score_diff <= tolerance

        # Venue quality score
        venue_score_diff = abs(
            metrics.venue_quality_score - self.thresholds.min_venue_quality_score
        )
        borderline_status["venue_quality_score"] = venue_score_diff <= tolerance

        # Venue impact factor
        impact_diff = abs(
            metrics.venue_impact_factor - self.thresholds.min_venue_impact_factor
        )
        borderline_status["venue_impact_factor"] = impact_diff <= tolerance

        # Overall borderline status
        borderline_status["is_borderline"] = any(borderline_status.values())

        return borderline_status
