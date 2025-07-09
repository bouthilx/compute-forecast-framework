"""
Main Computational Research Filter for Issue #8.
Integrates all filtering components for real-time paper filtering.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ...metadata_collection.models import (
    Paper,
    ComputationalAnalysis,
    AuthorshipAnalysis,
    VenueAnalysis,
)
from .computational_analyzer import ComputationalAnalyzer
from .authorship_classifier import AuthorshipClassifier
from .venue_relevance_scorer import VenueRelevanceScorer

logger = logging.getLogger(__name__)


@dataclass
class FilteringResult:
    """Result of computational filtering for a paper."""

    paper: Paper
    passed: bool
    score: float
    computational_analysis: Optional[ComputationalAnalysis]
    authorship_analysis: Optional[AuthorshipAnalysis]
    venue_analysis: Optional[VenueAnalysis]
    reasons: List[str]
    confidence: float


@dataclass
class FilteringConfig:
    """Configuration for computational filtering thresholds."""

    # Computational richness thresholds
    min_computational_richness: float = 0.3
    min_computational_confidence: float = 0.5

    # Author affiliation settings
    require_academic_eligible: bool = False
    allow_industry_collaboration: bool = True
    min_authorship_confidence: float = 0.6

    # Venue relevance thresholds
    min_venue_score: float = 0.4
    min_domain_relevance: float = 0.5
    max_venue_importance_ranking: int = 4

    # Overall filtering
    min_combined_score: float = 0.5
    strict_mode: bool = False  # If True, all criteria must be met


class ComputationalResearchFilter:
    """
    Real-time filter for computational research papers.
    Combines computational richness, author affiliations, and venue relevance.
    """

    def __init__(self, config: Optional[FilteringConfig] = None):
        self.config = config or FilteringConfig()

        # Initialize component analyzers
        self.computational_analyzer = ComputationalAnalyzer()
        self.authorship_classifier = AuthorshipClassifier()
        self.venue_scorer = VenueRelevanceScorer()

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_processed": 0,
            "total_passed": 0,
            "computational_filtered": 0,
            "authorship_filtered": 0,
            "venue_filtered": 0,
            "combined_filtered": 0,
            "pass_rate": 0.0,
            "computational_filter_rate": 0.0,
            "authorship_filter_rate": 0.0,
            "venue_filter_rate": 0.0,
            "combined_filter_rate": 0.0,
        }

        logger.info("ComputationalResearchFilter initialized")

    def filter_paper(self, paper: Paper) -> FilteringResult:
        """
        Apply computational research filtering to a single paper.

        Args:
            paper: Paper to filter

        Returns:
            FilteringResult with pass/fail status and detailed analysis
        """
        self.stats["total_processed"] += 1

        # Perform analyses
        computational_analysis = (
            self.computational_analyzer.analyze_computational_content(paper)
        )
        authorship_analysis = self.authorship_classifier.classify_authors(paper.authors)
        venue_analysis = self.venue_scorer.score_venue(paper.venue)

        # Check individual criteria
        comp_passed, comp_reasons = self._check_computational_criteria(
            computational_analysis
        )
        auth_passed, auth_reasons = self._check_authorship_criteria(authorship_analysis)
        venue_passed, venue_reasons = self._check_venue_criteria(venue_analysis)

        # Calculate combined score
        combined_score = self._calculate_combined_score(
            computational_analysis, authorship_analysis, venue_analysis
        )

        # Determine overall pass/fail
        if self.config.strict_mode:
            # All criteria must pass
            passed = comp_passed and auth_passed and venue_passed
        else:
            # Use combined score threshold
            passed = combined_score >= self.config.min_combined_score

            # Override if any critical failure
            if computational_analysis.computational_richness < 0.1:
                passed = False
            if venue_analysis.importance_ranking > 5:
                passed = False

        # Compile reasons
        all_reasons = []
        if not comp_passed:
            all_reasons.extend(comp_reasons)
            self.stats["computational_filtered"] += 1
        if not auth_passed:
            all_reasons.extend(auth_reasons)
            self.stats["authorship_filtered"] += 1
        if not venue_passed:
            all_reasons.extend(venue_reasons)
            self.stats["venue_filtered"] += 1

        if not passed and not all_reasons:
            all_reasons.append(
                f"Combined score {combined_score:.2f} below threshold {self.config.min_combined_score}"
            )
            self.stats["combined_filtered"] += 1

        if passed:
            self.stats["total_passed"] += 1
            all_reasons.append("Paper meets computational research criteria")

        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            computational_analysis, authorship_analysis, venue_analysis
        )

        return FilteringResult(
            paper=paper,
            passed=passed,
            score=combined_score,
            computational_analysis=computational_analysis,
            authorship_analysis=authorship_analysis,
            venue_analysis=venue_analysis,
            reasons=all_reasons,
            confidence=confidence,
        )

    def _check_computational_criteria(
        self, analysis: ComputationalAnalysis
    ) -> Tuple[bool, List[str]]:
        """Check if computational criteria are met."""
        reasons = []
        passed = True

        if analysis.computational_richness < self.config.min_computational_richness:
            passed = False
            reasons.append(
                f"Computational richness {analysis.computational_richness:.2f} "
                f"below threshold {self.config.min_computational_richness}"
            )

        if analysis.confidence_score < self.config.min_computational_confidence:
            passed = False
            reasons.append(
                f"Computational confidence {analysis.confidence_score:.2f} "
                f"below threshold {self.config.min_computational_confidence}"
            )

        return passed, reasons

    def _check_authorship_criteria(
        self, analysis: AuthorshipAnalysis
    ) -> Tuple[bool, List[str]]:
        """Check if authorship criteria are met."""
        reasons = []
        passed = True

        if self.config.require_academic_eligible:
            if analysis.category != "academic_eligible":
                passed = False
                reasons.append(
                    f"Paper not academic eligible (category: {analysis.category})"
                )

        if not self.config.allow_industry_collaboration:
            if analysis.industry_count > 0:
                passed = False
                reasons.append(
                    f"Industry collaboration not allowed ({analysis.industry_count} industry authors)"
                )

        if analysis.confidence < self.config.min_authorship_confidence:
            passed = False
            reasons.append(
                f"Authorship confidence {analysis.confidence:.2f} "
                f"below threshold {self.config.min_authorship_confidence}"
            )

        return passed, reasons

    def _check_venue_criteria(self, analysis: VenueAnalysis) -> Tuple[bool, List[str]]:
        """Check if venue criteria are met."""
        reasons = []
        passed = True

        if analysis.venue_score < self.config.min_venue_score:
            passed = False
            reasons.append(
                f"Venue score {analysis.venue_score:.2f} "
                f"below threshold {self.config.min_venue_score}"
            )

        if analysis.domain_relevance < self.config.min_domain_relevance:
            passed = False
            reasons.append(
                f"Domain relevance {analysis.domain_relevance:.2f} "
                f"below threshold {self.config.min_domain_relevance}"
            )

        if analysis.importance_ranking > self.config.max_venue_importance_ranking:
            passed = False
            reasons.append(
                f"Venue importance ranking {analysis.importance_ranking} "
                f"exceeds maximum {self.config.max_venue_importance_ranking}"
            )

        return passed, reasons

    def _calculate_combined_score(
        self,
        comp: ComputationalAnalysis,
        auth: AuthorshipAnalysis,
        venue: VenueAnalysis,
    ) -> float:
        """Calculate combined filtering score."""
        # Weight components
        comp_weight = 0.4
        auth_weight = 0.2
        venue_weight = 0.4

        # Computational component
        comp_score = comp.computational_richness * comp.confidence_score

        # Authorship component
        if auth.category == "academic_eligible":
            auth_score = 1.0
        elif auth.category == "industry_eligible":
            auth_score = 0.8
        else:
            auth_score = 0.3
        auth_score *= auth.confidence

        # Venue component
        venue_score = venue.venue_score

        # Combined weighted score
        combined = (
            comp_score * comp_weight
            + auth_score * auth_weight
            + venue_score * venue_weight
        )

        return float(combined)

    def _calculate_overall_confidence(
        self,
        comp: ComputationalAnalysis,
        auth: AuthorshipAnalysis,
        venue: VenueAnalysis,
    ) -> float:
        """Calculate overall confidence in the filtering decision."""
        # Average the component confidences
        comp_conf = comp.confidence_score
        auth_conf = auth.confidence

        # Venue confidence based on ranking (better venues = higher confidence)
        venue_conf = 1.0 - (venue.importance_ranking - 1) * 0.2
        venue_conf = max(0.2, venue_conf)

        overall_conf = (comp_conf + auth_conf + venue_conf) / 3.0

        return float(overall_conf)

    def batch_filter(
        self, papers: List[Paper], return_all: bool = False
    ) -> List[FilteringResult]:
        """
        Filter multiple papers efficiently.

        Args:
            papers: List of papers to filter
            return_all: If True, return results for all papers. If False, only passed papers.

        Returns:
            List of FilteringResult objects
        """
        results = []

        for paper in papers:
            try:
                result = self.filter_paper(paper)
                if return_all or result.passed:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error filtering paper '{paper.title}': {e}")
                if return_all:
                    # Create failed result
                    results.append(
                        FilteringResult(
                            paper=paper,
                            passed=False,
                            score=0.0,
                            computational_analysis=ComputationalAnalysis(
                                computational_richness=0.0,
                                keyword_matches={},
                                resource_metrics={},
                                experimental_indicators={},
                                confidence_score=0.0,
                            ),
                            authorship_analysis=AuthorshipAnalysis(
                                category="needs_manual_review",
                                academic_count=0,
                                industry_count=0,
                                unknown_count=len(paper.authors),
                                confidence=0.0,
                                author_details=[],
                            ),
                            venue_analysis=VenueAnalysis(
                                venue_score=0.0,
                                domain_relevance=0.0,
                                computational_focus=0.0,
                                importance_ranking=5,
                            ),
                            reasons=[f"Error during filtering: {str(e)}"],
                            confidence=0.0,
                        )
                    )

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics."""
        stats = self.stats.copy()

        # Calculate rates
        if stats["total_processed"] > 0:
            stats["pass_rate"] = float(stats["total_passed"] / stats["total_processed"])
            stats["computational_filter_rate"] = float(
                stats["computational_filtered"] / stats["total_processed"]
            )
            stats["authorship_filter_rate"] = float(
                stats["authorship_filtered"] / stats["total_processed"]
            )
            stats["venue_filter_rate"] = float(
                stats["venue_filtered"] / stats["total_processed"]
            )
            stats["combined_filter_rate"] = float(
                stats["combined_filtered"] / stats["total_processed"]
            )
        else:
            stats["pass_rate"] = 0.0
            stats["computational_filter_rate"] = 0.0
            stats["authorship_filter_rate"] = 0.0
            stats["venue_filter_rate"] = 0.0
            stats["combined_filter_rate"] = 0.0

        return stats

    def reset_statistics(self) -> None:
        """Reset filtering statistics."""
        self.stats = {
            "total_processed": 0,
            "total_passed": 0,
            "computational_filtered": 0,
            "authorship_filtered": 0,
            "venue_filtered": 0,
            "combined_filtered": 0,
            "pass_rate": 0.0,
            "computational_filter_rate": 0.0,
            "authorship_filter_rate": 0.0,
            "venue_filter_rate": 0.0,
            "combined_filter_rate": 0.0,
        }

    def update_config(self, new_config: FilteringConfig) -> None:
        """Update filtering configuration."""
        self.config = new_config
        logger.info("Filtering configuration updated")
