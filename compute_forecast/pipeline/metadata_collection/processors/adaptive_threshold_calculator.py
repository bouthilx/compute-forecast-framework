"""Adaptive threshold calculation for citation filtering."""

from datetime import datetime
from typing import List, Optional
import numpy as np

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.metadata_collection.processors.citation_statistics import (
    AdaptiveThreshold,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_config import (
    CitationConfig,
)


class AdaptiveThresholdCalculator:
    """Calculate adaptive citation thresholds based on venue, year, and citation patterns."""

    def __init__(self, config: Optional[CitationConfig] = None):
        """Initialize calculator with tier-based thresholds."""
        self.config = config or CitationConfig()
        self.current_year = datetime.now().year

        # Base thresholds by venue tier and years since publication
        self.base_thresholds = {
            "tier1": {0: 3, 1: 5, 2: 8, 3: 12, 4: 15},  # NeurIPS, ICML, ICLR
            "tier2": {0: 2, 1: 4, 2: 6, 3: 9, 4: 12},  # AAAI, CVPR, etc.
            "tier3": {0: 1, 1: 3, 2: 5, 3: 7, 4: 10},  # UAI, AISTATS, etc.
            "tier4": {0: 1, 1: 2, 2: 3, 3: 5, 4: 7},  # Emerging venues
        }

    def calculate_venue_threshold(
        self, venue: str, year: int, papers: List[Paper], venue_tier: str
    ) -> int:
        """Calculate adaptive threshold for specific venue/year."""
        years_since_publication = self.current_year - year

        # Get base threshold from tier and age
        years_key = min(years_since_publication, 4)
        base_threshold = self.base_thresholds.get(
            venue_tier, self.base_thresholds["tier4"]
        ).get(years_key, self.base_thresholds[venue_tier][4])

        # Filter papers for this venue/year
        venue_papers = [
            p
            for p in papers
            if (p.normalized_venue or p.venue) == venue and p.year == year
        ]

        if not venue_papers:
            return base_threshold

        # Calculate statistical threshold (percentile from config)
        citations = [p.get_latest_citations_count() for p in venue_papers]
        if citations:
            statistical_threshold = np.percentile(
                citations, self.config.statistical_percentile
            )
        else:
            statistical_threshold = base_threshold

        # Adaptive threshold (weighted combination using config weights)
        adaptive_threshold = int(
            (statistical_threshold * self.config.statistical_weight)
            + (base_threshold * self.config.base_weight)
        )

        # Ensure minimum representation (keep at least config.min_representation_percent of papers)
        if citations:
            min_representation_threshold = np.percentile(
                citations, self.config.min_representation_percentile
            )
            adaptive_threshold = min(
                adaptive_threshold, int(min_representation_threshold)
            )

            # Special case: if all papers have very low citations, we need to keep some
            # This ensures we don't filter out everything when all papers are below threshold
            if (
                adaptive_threshold >= self.config.min_citation_threshold
                and max(citations) < self.config.min_citation_threshold
            ):
                # Keep papers at the maximum citation level (even if it's 0)
                adaptive_threshold = max(citations)

        return max(adaptive_threshold, 0)  # Allow 0 citations in edge cases

    def calculate_percentile_threshold(
        self, citations: List[int], percentile: float
    ) -> int:
        """Calculate citation threshold at given percentile."""
        if not citations:
            return 0

        threshold = np.percentile(citations, percentile)
        return int(threshold)

    def calculate_adaptive_threshold(
        self, venue: str, year: int, papers: List[Paper], venue_tier: str
    ) -> AdaptiveThreshold:
        """Calculate comprehensive adaptive threshold with metadata."""
        years_since_publication = self.current_year - year

        # Get base threshold
        years_key = min(years_since_publication, 4)
        base_threshold = self.base_thresholds.get(
            venue_tier, self.base_thresholds["tier4"]
        ).get(years_key, self.base_thresholds[venue_tier][4])

        # Filter papers for this venue/year
        venue_papers = [
            p
            for p in papers
            if (p.normalized_venue or p.venue) == venue and p.year == year
        ]

        # Calculate adaptive threshold
        adaptive_threshold = self.calculate_venue_threshold(
            venue, year, papers, venue_tier
        )

        # Calculate confidence based on data availability
        confidence = (
            min(len(venue_papers) / self.config.min_papers_for_full_confidence, 1.0)
            if venue_papers
            else 0.1
        )

        # Calculate how many papers would be above threshold
        papers_above = len(
            [p for p in venue_papers if p.get_latest_citations_count() >= adaptive_threshold]
        )

        # Calculate alternative thresholds
        citations = [p.get_latest_citations_count() for p in venue_papers]
        alternative_thresholds = {}
        if citations:
            alternative_thresholds = {
                "50th_percentile": int(np.percentile(citations, 50)),
                "80th_percentile": int(np.percentile(citations, 80)),
                "90th_percentile": int(np.percentile(citations, 90)),
            }

        return AdaptiveThreshold(
            venue=venue,
            year=year,
            threshold=adaptive_threshold,
            confidence=confidence,
            base_threshold=base_threshold,
            recency_adjustment=1.0 - (years_since_publication * 0.1),
            venue_prestige_multiplier=self.config.venue_tier_multipliers.get(
                venue_tier, 0.5
            ),
            representation_requirement=max(
                int(len(venue_papers) * self.config.min_representation_percent), 5
            )
            if venue_papers
            else 5,
            papers_analyzed=len(venue_papers),
            papers_above_threshold=papers_above,
            percentile_used=self.config.statistical_percentile,
            alternative_thresholds=alternative_thresholds,
        )

    def get_venue_tier_multiplier(self, venue_tier: str) -> float:
        """Get prestige multiplier for venue tier."""
        return self.config.venue_tier_multipliers.get(venue_tier, 0.4)
