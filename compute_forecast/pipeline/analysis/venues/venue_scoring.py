"""
Venue Importance Scoring System

This module implements comprehensive venue scoring for paper collection prioritization.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from compute_forecast.pipeline.analysis.venues.venue_database import (
    VenueDatabase,
    VenueInfo,
)
from compute_forecast.pipeline.analysis.venues.venue_analyzer import MilaVenueAnalyzer

logger = logging.getLogger(__name__)


class ScoringFactor(Enum):
    """Venue scoring factors"""

    MILA_PAPER_COUNT = "mila_paper_count"
    COMPUTATIONAL_FOCUS = "computational_focus"
    CITATION_IMPACT = "citation_impact"
    YEARLY_CONSISTENCY = "yearly_consistency"
    DOMAIN_SPECIFICITY = "domain_specificity"


@dataclass
class VenueScore:
    """Comprehensive venue scoring result"""

    venue_name: str
    domain: str
    final_score: float
    component_scores: Dict[str, float]
    recommendation: str
    ranking_factors: Dict[str, Any]


class VenueScorer:
    """Comprehensive venue scoring for paper collection priority"""

    def __init__(self, venue_database: VenueDatabase, mila_analyzer: MilaVenueAnalyzer):
        self.venue_db = venue_database
        self.mila_analyzer = mila_analyzer

        # Scoring factor weights
        self.scoring_factors = {
            ScoringFactor.MILA_PAPER_COUNT.value: 0.3,  # How much Mila publishes there
            ScoringFactor.COMPUTATIONAL_FOCUS.value: 0.25,  # Emphasis on computational work
            ScoringFactor.CITATION_IMPACT.value: 0.2,  # Venue prestige/impact
            ScoringFactor.YEARLY_CONSISTENCY.value: 0.15,  # Consistent publication venue
            ScoringFactor.DOMAIN_SPECIFICITY.value: 0.1,  # Domain relevance
        }

        # Load or initialize venue impact scores
        self.venue_impact_scores = self._load_venue_impact_scores()

        # Cache for Mila publication data
        self._mila_data_cache: Optional[Dict[str, Any]] = None

    def _load_venue_impact_scores(self) -> Dict[str, float]:
        """Load or define venue impact scores (h5-index based)"""
        # Manual venue impact scoring based on known rankings
        impact_scores = {
            # Top-tier ML/AI venues
            "NeurIPS": 1.0,
            "ICML": 1.0,
            "ICLR": 0.95,
            # Top-tier CV venues
            "CVPR": 1.0,
            "ICCV": 0.98,
            "ECCV": 0.95,
            # Top-tier NLP venues
            "ACL": 0.9,
            "EMNLP": 0.88,
            "NAACL": 0.85,
            # Strong tier-2 venues
            "AAAI": 0.85,
            "IJCAI": 0.85,
            "AISTATS": 0.8,
            "UAI": 0.75,
            "WACV": 0.7,
            "BMVC": 0.65,
            # Medical imaging
            "MICCAI": 0.8,
            "IPMI": 0.7,
            "ISBI": 0.65,
            # Robotics
            "ICRA": 0.85,
            "IROS": 0.8,
            "RSS": 0.9,
            # Specialized venues
            "AAMAS": 0.75,
            "WWW": 0.8,
            "KDD": 0.85,
            "SIGMOD": 0.9,
            "VLDB": 0.9,
            # Theory venues
            "SODA": 0.8,
            "FOCS": 0.85,
            "STOC": 0.9,
            # Security venues
            "CCS": 0.85,
            "S&P": 0.9,
            "USENIX Security": 0.85,
            # HCI venues
            "CHI": 0.85,
            "UIST": 0.8,
        }

        return impact_scores

    def _get_mila_data(self) -> Dict[str, Any]:
        """Get cached Mila publication data"""
        if self._mila_data_cache is None:
            self._mila_data_cache = self.mila_analyzer.analyze_mila_venues()
        return self._mila_data_cache

    def calculate_venue_score(
        self, venue: str, domain: str, mila_data: Optional[Dict] = None
    ) -> VenueScore:
        """Comprehensive venue scoring for paper collection priority"""

        if mila_data is None:
            mila_data = self._get_mila_data()

        scores = {}
        ranking_factors = {}

        # 1. Mila publication frequency
        venue_stats = mila_data.get("venue_statistics", {}).get(venue, {})
        mila_paper_count = venue_stats.get("total_count", 0)
        scores[ScoringFactor.MILA_PAPER_COUNT.value] = min(mila_paper_count / 10, 1.0)
        ranking_factors["mila_papers"] = mila_paper_count

        # 2. Computational focus (from venue database)
        venue_info = self.venue_db.get_venue_info(venue)
        if venue_info:
            scores[ScoringFactor.COMPUTATIONAL_FOCUS.value] = (
                venue_info.computational_focus
            )
            ranking_factors["computational_focus"] = venue_info.computational_focus
            ranking_factors["venue_tier"] = venue_info.tier.value
        else:
            scores[ScoringFactor.COMPUTATIONAL_FOCUS.value] = 0.5
            ranking_factors["computational_focus"] = 0.5
            ranking_factors["venue_tier"] = "unknown"

        # 3. Citation impact (h5-index, venue rankings)
        impact_score = self.venue_impact_scores.get(venue, 0.5)
        scores[ScoringFactor.CITATION_IMPACT.value] = impact_score
        ranking_factors["impact_score"] = impact_score

        # 4. Yearly consistency (appears across multiple years)
        yearly_data = venue_stats.get("years", [])
        year_span = len(yearly_data) if yearly_data else 0
        consistency_score = min(year_span / 5, 1.0)  # Normalize to 5 years
        scores[ScoringFactor.YEARLY_CONSISTENCY.value] = consistency_score
        ranking_factors["year_span"] = year_span
        ranking_factors["years_active"] = yearly_data

        # 5. Domain specificity (how well venue matches domain)
        domain_specificity = self._assess_domain_match(venue, domain, venue_info)
        scores[ScoringFactor.DOMAIN_SPECIFICITY.value] = domain_specificity
        ranking_factors["domain_match"] = domain_specificity

        # Weighted final score
        final_score = sum(
            scores[factor] * weight for factor, weight in self.scoring_factors.items()
        )

        # Generate recommendation
        if final_score > 0.7:
            recommendation = "high"
        elif final_score > 0.4:
            recommendation = "medium"
        else:
            recommendation = "low"

        return VenueScore(
            venue_name=venue,
            domain=domain,
            final_score=round(final_score, 3),
            component_scores={k: round(v, 3) for k, v in scores.items()},
            recommendation=recommendation,
            ranking_factors=ranking_factors,
        )

    def _assess_domain_match(
        self, venue: str, target_domain: str, venue_info: Optional[VenueInfo] = None
    ) -> float:
        """Assess how well venue matches the target domain"""
        if venue_info and venue_info.domain == target_domain:
            return 1.0

        # Domain compatibility matrix
        domain_compatibility = {
            "computer_vision": {
                "ml_general": 0.8,
                "medical_imaging": 0.7,
                "data_science": 0.5,
            },
            "nlp": {"ml_general": 0.8, "hci": 0.6, "data_science": 0.5},
            "reinforcement_learning": {
                "ml_general": 0.9,
                "robotics": 0.8,
                "game_theory": 0.7,
            },
            "ml_general": {
                "computer_vision": 0.8,
                "nlp": 0.8,
                "reinforcement_learning": 0.9,
                "data_science": 0.7,
            },
        }

        if venue_info:
            venue_domain = venue_info.domain
            compatibility = domain_compatibility.get(target_domain, {})
            return compatibility.get(venue_domain, 0.3)

        return 0.5

    def score_all_venues_for_domain(self, domain: str) -> List[VenueScore]:
        """Score all venues for a specific domain"""
        mila_data = self._get_mila_data()

        # Get venues from database
        domain_venues = self.venue_db.get_venues_by_domain(domain)
        venue_names = [v.name for v in domain_venues]

        # Add venues found in Mila data that aren't in database
        mila_venues = set(mila_data.get("venue_statistics", {}).keys())
        all_venues = set(venue_names) | mila_venues

        # Score all venues
        venue_scores = []
        for venue in all_venues:
            score = self.calculate_venue_score(venue, domain, mila_data)
            venue_scores.append(score)

        # Sort by final score descending
        return sorted(venue_scores, key=lambda x: x.final_score, reverse=True)

    def get_top_venues_by_domain(
        self, domain: str, limit: int = 10
    ) -> List[VenueScore]:
        """Get top-ranked venues for a domain"""
        all_scores = self.score_all_venues_for_domain(domain)
        return all_scores[:limit]

    def generate_venue_recommendations(self, domain: str) -> Dict[str, Any]:
        """Generate comprehensive venue recommendations for a domain"""
        venue_scores = self.score_all_venues_for_domain(domain)

        # Categorize by recommendation level
        high_priority = [v for v in venue_scores if v.recommendation == "high"]
        medium_priority = [v for v in venue_scores if v.recommendation == "medium"]
        low_priority = [v for v in venue_scores if v.recommendation == "low"]

        # Extract key insights
        if venue_scores:
            avg_score = sum(v.final_score for v in venue_scores) / len(venue_scores)
            top_venue = venue_scores[0]

            # Identify scoring factors contributing most to top venues
            top_venues = venue_scores[:5]
            factor_importance = {}
            for factor in ScoringFactor:
                avg_factor_score = sum(
                    v.component_scores.get(factor.value, 0) for v in top_venues
                ) / len(top_venues)
                factor_importance[factor.value] = avg_factor_score
        else:
            avg_score = 0
            top_venue = None
            factor_importance = {}

        return {
            "domain": domain,
            "total_venues_analyzed": len(venue_scores),
            "recommendations": {
                "high_priority": [v.venue_name for v in high_priority],
                "medium_priority": [v.venue_name for v in medium_priority],
                "low_priority": [v.venue_name for v in low_priority],
            },
            "statistics": {
                "average_score": round(avg_score, 3),
                "top_venue": top_venue.venue_name if top_venue else None,
                "top_venue_score": top_venue.final_score if top_venue else None,
                "high_priority_count": len(high_priority),
                "medium_priority_count": len(medium_priority),
            },
            "scoring_insights": {
                "factor_importance": {
                    k: round(v, 3) for k, v in factor_importance.items()
                },
                "scoring_weights": self.scoring_factors,
            },
            "detailed_scores": [
                {
                    "venue": v.venue_name,
                    "score": v.final_score,
                    "recommendation": v.recommendation,
                    "factors": v.component_scores,
                }
                for v in venue_scores[:10]  # Top 10 detailed scores
            ],
        }

    def export_scoring_results(self) -> Dict[str, Any]:
        """Export comprehensive scoring results for all domains"""
        all_domains = list(self.venue_db._domain_mapping.keys())

        results = {
            "scoring_metadata": {
                "scoring_factors": self.scoring_factors,
                "total_domains": len(all_domains),
                "venue_impact_scores_count": len(self.venue_impact_scores),
            },
            "domain_recommendations": {},
            "cross_domain_analysis": {},
        }

        # Generate recommendations for each domain
        for domain in all_domains:
            results["domain_recommendations"][domain] = (
                self.generate_venue_recommendations(domain)
            )

        # Cross-domain analysis
        all_venue_scores = []
        for domain in all_domains:
            all_venue_scores.extend(self.score_all_venues_for_domain(domain))

        if all_venue_scores:
            # Global venue rankings
            global_rankings: Dict[str, Dict[str, Any]] = {}
            for score in all_venue_scores:
                venue = score.venue_name
                if (
                    venue not in global_rankings
                    or score.final_score > global_rankings[venue]["score"]
                ):
                    global_rankings[venue] = {
                        "score": score.final_score,
                        "best_domain": score.domain,
                        "recommendation": score.recommendation,
                    }

            # Sort global rankings
            sorted_global = sorted(
                global_rankings.items(),
                key=lambda x: float(x[1]["score"]),
                reverse=True,
            )

            results["cross_domain_analysis"] = {
                "top_venues_globally": [
                    (v, data["score"], data["best_domain"])
                    for v, data in sorted_global[:20]
                ],
                "venue_distribution": {
                    "high_priority": sum(
                        1
                        for _, data in global_rankings.items()
                        if data["recommendation"] == "high"
                    ),
                    "medium_priority": sum(
                        1
                        for _, data in global_rankings.items()
                        if data["recommendation"] == "medium"
                    ),
                    "low_priority": sum(
                        1
                        for _, data in global_rankings.items()
                        if data["recommendation"] == "low"
                    ),
                },
            }

        return results
