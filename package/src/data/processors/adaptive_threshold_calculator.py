"""Adaptive threshold calculation for citation filtering."""

from datetime import datetime
from typing import List
import numpy as np

from src.data.models import Paper
from src.data.processors.citation_statistics import AdaptiveThreshold


class AdaptiveThresholdCalculator:
    """Calculate adaptive citation thresholds based on venue, year, and citation patterns."""
    
    def __init__(self):
        """Initialize calculator with tier-based thresholds."""
        self.current_year = datetime.now().year
        
        # Base thresholds by venue tier and years since publication
        self.base_thresholds = {
            "tier1": {0: 3, 1: 5, 2: 8, 3: 12, 4: 15},    # NeurIPS, ICML, ICLR
            "tier2": {0: 2, 1: 4, 2: 6, 3: 9, 4: 12},     # AAAI, CVPR, etc.
            "tier3": {0: 1, 1: 3, 2: 5, 3: 7, 4: 10},     # UAI, AISTATS, etc.
            "tier4": {0: 1, 1: 2, 2: 3, 3: 5, 4: 7}       # Emerging venues
        }
        
        # Venue tier multipliers for prestige scoring
        self.venue_tier_multipliers = {
            "tier1": 1.0,
            "tier2": 0.8,
            "tier3": 0.6,
            "tier4": 0.4
        }
    
    def calculate_venue_threshold(self, venue: str, year: int, papers: List[Paper], venue_tier: str) -> int:
        """Calculate adaptive threshold for specific venue/year."""
        years_since_publication = self.current_year - year
        
        # Get base threshold from tier and age
        years_key = min(years_since_publication, 4)
        base_threshold = self.base_thresholds.get(venue_tier, self.base_thresholds["tier4"]).get(
            years_key, self.base_thresholds[venue_tier][4]
        )
        
        # Filter papers for this venue/year
        venue_papers = [
            p for p in papers 
            if (p.normalized_venue or p.venue) == venue and p.year == year
        ]
        
        if not venue_papers:
            return base_threshold
        
        # Calculate statistical threshold (75th percentile)
        citations = [p.citations for p in venue_papers if p.citations is not None]
        if citations:
            statistical_threshold = np.percentile(citations, 75)
        else:
            statistical_threshold = base_threshold
        
        # Adaptive threshold (weighted combination)
        statistical_weight = 0.6
        base_weight = 0.4
        
        adaptive_threshold = int(
            (statistical_threshold * statistical_weight) + 
            (base_threshold * base_weight)
        )
        
        # Ensure minimum representation (keep at least 30% of papers)
        if citations:
            min_representation_threshold = np.percentile(citations, 70)
            adaptive_threshold = min(adaptive_threshold, int(min_representation_threshold))
        
        return max(adaptive_threshold, 1)  # At least 1 citation required
    
    def calculate_percentile_threshold(self, citations: List[int], percentile: float) -> int:
        """Calculate citation threshold at given percentile."""
        if not citations:
            return 0
        
        threshold = np.percentile(citations, percentile)
        return int(threshold)
    
    def calculate_adaptive_threshold(self, venue: str, year: int, papers: List[Paper], 
                                   venue_tier: str) -> AdaptiveThreshold:
        """Calculate comprehensive adaptive threshold with metadata."""
        years_since_publication = self.current_year - year
        
        # Get base threshold
        years_key = min(years_since_publication, 4)
        base_threshold = self.base_thresholds.get(venue_tier, self.base_thresholds["tier4"]).get(
            years_key, self.base_thresholds[venue_tier][4]
        )
        
        # Filter papers for this venue/year
        venue_papers = [
            p for p in papers 
            if (p.normalized_venue or p.venue) == venue and p.year == year
        ]
        
        # Calculate adaptive threshold
        adaptive_threshold = self.calculate_venue_threshold(venue, year, papers, venue_tier)
        
        # Calculate confidence based on data availability
        confidence = min(len(venue_papers) / 50.0, 1.0) if venue_papers else 0.1
        
        # Calculate how many papers would be above threshold
        papers_above = len([p for p in venue_papers if p.citations >= adaptive_threshold])
        
        # Calculate alternative thresholds
        citations = [p.citations for p in venue_papers if p.citations is not None]
        alternative_thresholds = {}
        if citations:
            alternative_thresholds = {
                "50th_percentile": int(np.percentile(citations, 50)),
                "80th_percentile": int(np.percentile(citations, 80)),
                "90th_percentile": int(np.percentile(citations, 90))
            }
        
        return AdaptiveThreshold(
            venue=venue,
            year=year,
            threshold=adaptive_threshold,
            confidence=confidence,
            base_threshold=base_threshold,
            recency_adjustment=1.0 - (years_since_publication * 0.1),
            venue_prestige_multiplier=self.venue_tier_multipliers.get(venue_tier, 0.5),
            representation_requirement=max(int(len(venue_papers) * 0.3), 5) if venue_papers else 5,
            papers_analyzed=len(venue_papers),
            papers_above_threshold=papers_above,
            percentile_used=75.0,
            alternative_thresholds=alternative_thresholds
        )
    
    def get_venue_tier_multiplier(self, venue_tier: str) -> float:
        """Get prestige multiplier for venue tier."""
        return self.venue_tier_multipliers.get(venue_tier, 0.4)