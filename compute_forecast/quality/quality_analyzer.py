"""
Quality Analyzer for Issue #13.
Analyzes paper and venue quality using weighted scoring algorithms.
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

from .quality_structures import QualityMetrics, QUALITY_SCORING_WEIGHTS

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """
    Analyzer for paper and venue quality assessment.

    Features:
    - Weighted quality score calculation using configurable weights
    - Paper quality assessment based on citations, authors, pages, references
    - Venue quality assessment based on impact factor, acceptance rate, h-index
    - Combined quality scores with confidence levels
    - Fast real-time assessment for collection pipeline
    """

    def __init__(self, scoring_weights: Optional[Dict[str, float]] = None):
        self.scoring_weights = scoring_weights or QUALITY_SCORING_WEIGHTS
        self._validate_scoring_weights()

        logger.info("QualityAnalyzer initialized")

    def assess_paper_quality(self, paper_data: Dict[str, Any]) -> QualityMetrics:
        """
        Perform complete quality assessment for a paper.

        Args:
            paper_data: Dictionary containing paper and venue information

        Returns:
            QualityMetrics object with calculated scores and confidence
        """
        # Calculate individual quality scores
        paper_quality_score = self.calculate_paper_quality_score(paper_data)
        venue_quality_score = self.calculate_venue_quality_score(paper_data)

        # Calculate combined quality score
        combined_quality_score = self._calculate_combined_quality_score(
            paper_quality_score, venue_quality_score
        )

        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(paper_data)

        # Create QualityMetrics object
        metrics = QualityMetrics(
            paper_id=paper_data.get("paper_id"),
            venue=paper_data.get("venue"),
            year=paper_data.get("year"),
            # Paper quality indicators
            citation_count=paper_data.get("citation_count", 0),
            author_count=paper_data.get("author_count", 0),
            page_count=paper_data.get("page_count", 0),
            reference_count=paper_data.get("reference_count", 0),
            # Venue quality indicators
            venue_impact_factor=paper_data.get("venue_impact_factor", 0.0),
            venue_acceptance_rate=paper_data.get("venue_acceptance_rate", 0.0),
            venue_h_index=paper_data.get("venue_h_index", 0.0),
            # Calculated quality scores
            paper_quality_score=paper_quality_score,
            venue_quality_score=venue_quality_score,
            combined_quality_score=combined_quality_score,
            # Quality confidence
            confidence_level=confidence_level,
            # Metadata
            assessment_timestamp=datetime.now(),
            calculation_version="1.0",
        )

        return metrics

    def calculate_paper_quality_score(self, paper_data: Dict[str, Any]) -> float:
        """
        Calculate paper quality score using weighted formula.

        Uses QUALITY_SCORING_WEIGHTS to compute weighted sum of:
        - citation_count * weight
        - venue_impact_factor * weight
        - author_count * weight
        - page_count * weight
        - reference_count * weight
        - venue_h_index * weight
        """
        score = 0.0

        # Citation count contribution
        citation_count = paper_data.get("citation_count", 0)
        score += citation_count * self.scoring_weights.get("citation_count", 0)

        # Venue impact factor contribution
        venue_impact_factor = paper_data.get("venue_impact_factor", 0.0)
        score += venue_impact_factor * self.scoring_weights.get(
            "venue_impact_factor", 0
        )

        # Author count contribution (normalized)
        author_count = paper_data.get("author_count", 0)
        score += author_count * self.scoring_weights.get("author_count", 0)

        # Page count contribution (normalized)
        page_count = paper_data.get("page_count", 0)
        score += page_count * self.scoring_weights.get("page_count", 0)

        # Reference count contribution (normalized)
        reference_count = paper_data.get("reference_count", 0)
        score += reference_count * self.scoring_weights.get("reference_count", 0)

        # Venue h-index contribution (normalized)
        venue_h_index = paper_data.get("venue_h_index", 0.0)
        score += venue_h_index * self.scoring_weights.get("venue_h_index", 0)

        return float(score)

    def calculate_venue_quality_score(self, venue_data: Dict[str, Any]) -> float:
        """
        Calculate venue quality score based on venue metrics.

        Factors:
        - Higher impact factor = higher quality
        - Lower acceptance rate = higher quality (more selective)
        - Higher h-index = higher quality
        """
        impact_factor = venue_data.get("venue_impact_factor", 0.0)
        acceptance_rate = venue_data.get("venue_acceptance_rate", 1.0)
        h_index = venue_data.get("venue_h_index", 0.0)

        # Normalize impact factor (typically 0-10 range)
        impact_score = min(impact_factor / 5.0, 1.0)

        # Invert acceptance rate (lower is better) and normalize
        # Typical range 0.1-0.5, so invert and scale
        acceptance_score = (
            max(0.0, (0.5 - acceptance_rate) / 0.4) if acceptance_rate > 0 else 0.5
        )

        # Normalize h-index (typically 0-200 range)
        h_index_score = min(h_index / 100.0, 1.0)

        # Weighted combination
        venue_score = impact_score * 0.4 + acceptance_score * 0.3 + h_index_score * 0.3

        return float(venue_score)

    def _calculate_combined_quality_score(
        self, paper_score: float, venue_score: float
    ) -> float:
        """Calculate combined quality score from paper and venue scores."""
        # Weighted combination favoring paper quality slightly
        combined_score = (paper_score * 0.6) + (venue_score * 0.4)

        # Normalize to 0-1 range (paper_score can exceed 1.0)
        max_possible_paper_score = (
            sum(self.scoring_weights.values()) * 100
        )  # Rough estimate
        normalized_paper_component = (
            min(paper_score / max_possible_paper_score, 1.0) * 0.6
        )
        venue_component = venue_score * 0.4

        return float(normalized_paper_component + venue_component)

    def _calculate_confidence_level(self, paper_data: Dict[str, Any]) -> float:
        """
        Calculate confidence level based on data completeness and reliability.
        """
        confidence_factors = []

        # Citation count reliability (more citations = higher confidence)
        citation_count = paper_data.get("citation_count", 0)
        citation_confidence = min(
            citation_count / 50.0, 1.0
        )  # Max confidence at 50+ citations
        confidence_factors.append(citation_confidence)

        # Venue data completeness
        venue_data_fields = [
            "venue_impact_factor",
            "venue_acceptance_rate",
            "venue_h_index",
        ]
        venue_completeness = sum(
            1 for field in venue_data_fields if paper_data.get(field, 0) > 0
        ) / len(venue_data_fields)
        confidence_factors.append(venue_completeness)

        # Paper metadata completeness
        paper_fields = ["author_count", "page_count", "reference_count"]
        paper_completeness = sum(
            1 for field in paper_fields if paper_data.get(field, 0) > 0
        ) / len(paper_fields)
        confidence_factors.append(paper_completeness)

        # Overall confidence is average of factors
        confidence = np.mean(confidence_factors)

        return float(confidence)

    def _validate_scoring_weights(self) -> None:
        """Validate that scoring weights are properly configured."""
        required_weights = [
            "citation_count",
            "venue_impact_factor",
            "author_count",
            "page_count",
            "reference_count",
            "venue_h_index",
        ]

        for weight in required_weights:
            if weight not in self.scoring_weights:
                logger.warning(f"Missing scoring weight for {weight}, using 0.0")
                self.scoring_weights[weight] = 0.0

        # Check that weights are reasonable
        total_weight = sum(self.scoring_weights.values())
        if total_weight == 0:
            logger.error(
                "Total scoring weights sum to zero - quality assessment will not work"
            )

        logger.info(f"Scoring weights validated. Total weight: {total_weight}")

    def get_quality_score_breakdown(
        self, paper_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Get detailed breakdown of quality score components.
        Useful for debugging and understanding quality assessments.
        """
        breakdown = {}

        # Individual component scores
        citation_contribution = paper_data.get(
            "citation_count", 0
        ) * self.scoring_weights.get("citation_count", 0)
        breakdown["citation_contribution"] = citation_contribution

        venue_impact_contribution = paper_data.get(
            "venue_impact_factor", 0.0
        ) * self.scoring_weights.get("venue_impact_factor", 0)
        breakdown["venue_impact_contribution"] = venue_impact_contribution

        author_contribution = paper_data.get(
            "author_count", 0
        ) * self.scoring_weights.get("author_count", 0)
        breakdown["author_contribution"] = author_contribution

        page_contribution = paper_data.get("page_count", 0) * self.scoring_weights.get(
            "page_count", 0
        )
        breakdown["page_contribution"] = page_contribution

        reference_contribution = paper_data.get(
            "reference_count", 0
        ) * self.scoring_weights.get("reference_count", 0)
        breakdown["reference_contribution"] = reference_contribution

        h_index_contribution = paper_data.get(
            "venue_h_index", 0.0
        ) * self.scoring_weights.get("venue_h_index", 0)
        breakdown["h_index_contribution"] = h_index_contribution

        # Total scores
        breakdown["total_paper_score"] = self.calculate_paper_quality_score(paper_data)
        breakdown["total_venue_score"] = self.calculate_venue_quality_score(paper_data)

        return breakdown

    def batch_assess_quality(
        self, papers: List[Dict[str, Any]]
    ) -> List[QualityMetrics]:
        """
        Assess quality for multiple papers efficiently.
        """
        results = []

        for paper_data in papers:
            try:
                metrics = self.assess_paper_quality(paper_data)
                results.append(metrics)
            except Exception as e:
                logger.error(
                    f"Error assessing quality for paper {paper_data.get('paper_id', 'unknown')}: {e}"
                )
                # Create minimal metrics for failed assessment
                failed_metrics = QualityMetrics(
                    paper_id=paper_data.get("paper_id"),
                    venue=paper_data.get("venue"),
                    year=paper_data.get("year"),
                    paper_quality_score=0.0,
                    venue_quality_score=0.0,
                    combined_quality_score=0.0,
                    confidence_level=0.0,
                )
                results.append(failed_metrics)

        return results
