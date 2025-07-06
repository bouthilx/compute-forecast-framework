"""Configuration for citation analysis and filtering system."""

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class CitationConfig:
    """Configuration for citation analysis and filtering."""

    # Venue tier mappings
    venue_tiers: Dict[str, str] = field(
        default_factory=lambda: {
            # Tier 1 - Top conferences
            "NeurIPS": "tier1",
            "ICML": "tier1",
            "ICLR": "tier1",
            # Tier 2 - Major conferences
            "AAAI": "tier2",
            "CVPR": "tier2",
            "ICCV": "tier2",
            "ECCV": "tier2",
            "ACL": "tier2",
            "EMNLP": "tier2",
            "NAACL": "tier2",
            # Tier 3 - Specialized conferences
            "UAI": "tier3",
            "AISTATS": "tier3",
            "KDD": "tier3",
            "WWW": "tier3",
            "SIGIR": "tier3",
            "WSDM": "tier3",
        }
    )

    # Venue sets by tier (for fast lookup)
    tier1_venues: Set[str] = field(default_factory=lambda: {"NeurIPS", "ICML", "ICLR"})
    tier2_venues: Set[str] = field(
        default_factory=lambda: {
            "AAAI",
            "CVPR",
            "ICCV",
            "ECCV",
            "ACL",
            "EMNLP",
            "NAACL",
        }
    )
    tier3_venues: Set[str] = field(
        default_factory=lambda: {"UAI", "AISTATS", "KDD", "WWW", "SIGIR", "WSDM"}
    )

    # Citation velocity thresholds for breakthrough detection
    velocity_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "very_high": 50.0,  # Very high velocity
            "high": 20.0,  # High velocity
            "good": 10.0,  # Good velocity
            "moderate": 5.0,  # Moderate velocity
            "low": 2.0,  # Low velocity
        }
    )

    # Citation velocity scores
    velocity_scores: Dict[str, float] = field(
        default_factory=lambda: {
            "very_high": 1.0,
            "high": 0.8,
            "good": 0.6,
            "moderate": 0.4,
            "low": 0.2,
            "very_low": 0.0,
        }
    )

    # Breakthrough detection weights
    breakthrough_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "citation_velocity": 0.3,
            "keywords": 0.25,
            "author_reputation": 0.2,
            "venue_prestige": 0.15,
            "recency": 0.1,
        }
    )

    # Adaptive threshold calculation parameters
    statistical_weight: float = 0.6
    base_weight: float = 0.4
    min_representation_percent: float = 0.3  # Keep at least 30% of papers
    statistical_percentile: float = (
        75.0  # Use 75th percentile for statistical threshold
    )
    min_representation_percentile: float = (
        70.0  # 70th percentile for minimum representation
    )

    # Quality thresholds
    high_impact_citation_threshold: int = (
        50  # Papers with >50 citations considered high impact
    )
    high_impact_percentile: float = 90.0  # Top 10% by citations

    # Venue tier multipliers for prestige calculation
    venue_tier_multipliers: Dict[str, float] = field(
        default_factory=lambda: {
            "tier1": 1.0,
            "tier2": 0.8,
            "tier3": 0.6,
            "tier4": 0.4,  # Default for unknown venues
        }
    )

    # Recency scoring thresholds (years since publication)
    recency_thresholds: Dict[str, int] = field(
        default_factory=lambda: {"very_recent": 2, "recent": 3, "somewhat_recent": 5}
    )

    # Recency scores
    recency_scores: Dict[str, float] = field(
        default_factory=lambda: {
            "very_recent": 1.0,
            "recent": 0.8,
            "somewhat_recent": 0.6,
            "older": 0.0,
        }
    )

    # Author reputation thresholds
    author_h_index_thresholds: Dict[str, int] = field(
        default_factory=lambda: {"high": 50, "medium": 30}
    )

    # Author reputation scores
    author_reputation_scores: Dict[str, float] = field(
        default_factory=lambda: {
            "high_impact_author": 0.3,
            "high_h_index": 0.2,
            "medium_h_index": 0.1,
        }
    )

    # Keyword matching parameters
    max_keywords_for_score: int = 5  # Max keywords to consider for full score

    # Minimum thresholds
    min_citation_threshold: int = 1  # Minimum citations required

    # Confidence calculation parameters
    min_papers_for_full_confidence: int = 50  # Need 50 papers for confidence = 1.0

    def get_venue_tier(self, venue: str) -> str:
        """Get tier for a venue, defaulting to tier4 for unknown venues."""
        return self.venue_tiers.get(venue, "tier4")

    def get_venue_prestige_multiplier(self, venue: str) -> float:
        """Get prestige multiplier for a venue based on its tier."""
        tier = self.get_venue_tier(venue)
        return self.venue_tier_multipliers.get(
            tier, self.venue_tier_multipliers["tier4"]
        )

    def get_velocity_score(self, velocity: float) -> float:
        """Get breakthrough score for citation velocity."""
        if velocity >= self.velocity_thresholds["very_high"]:
            return self.velocity_scores["very_high"]
        elif velocity >= self.velocity_thresholds["high"]:
            return self.velocity_scores["high"]
        elif velocity >= self.velocity_thresholds["good"]:
            return self.velocity_scores["good"]
        elif velocity >= self.velocity_thresholds["moderate"]:
            return self.velocity_scores["moderate"]
        elif velocity >= self.velocity_thresholds["low"]:
            return self.velocity_scores["low"]
        else:
            return self.velocity_scores["very_low"]

    def get_recency_score(self, years_since_pub: int) -> float:
        """Get recency score based on years since publication."""
        if years_since_pub <= self.recency_thresholds["very_recent"]:
            return self.recency_scores["very_recent"]
        elif years_since_pub <= self.recency_thresholds["recent"]:
            return self.recency_scores["recent"]
        elif years_since_pub <= self.recency_thresholds["somewhat_recent"]:
            return self.recency_scores["somewhat_recent"]
        else:
            return self.recency_scores["older"]
