"""Data structures for citation analysis and filtering."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from compute_forecast.data.models import Paper


@dataclass
class YearCitationStats:
    """Citation statistics for specific year."""

    year: int
    total_papers: int

    # Distribution
    citation_percentiles: Dict[int, float]
    mean_citations: float
    median_citations: float

    # Temporal factors
    years_since_publication: int
    expected_citation_velocity: float  # Expected citations per year
    actual_citation_velocity: float  # Actual citations per year


@dataclass
class BreakthroughPaper:
    """Paper identified as potential breakthrough research."""

    paper: Paper
    breakthrough_score: float  # 0.0 to 1.0
    breakthrough_indicators: List[str]  # Reasons for breakthrough classification

    # Detailed scoring
    citation_velocity_score: float  # Citations per year factor
    keyword_score: float  # Breakthrough keyword matches
    author_reputation_score: float  # High-impact author involvement
    venue_prestige_score: float  # Venue prestige factor
    recency_bonus: float  # Bonus for recent papers

    # Supporting evidence
    matched_keywords: List[str]  # Breakthrough keywords found
    high_impact_authors: List[str]  # Recognized authors
    citation_velocity: Optional[float]  # Actual citations per year


@dataclass
class VenueCitationStats:
    """Citation statistics for specific venue."""

    venue_name: str
    venue_tier: str
    total_papers: int

    # Citation distribution
    citation_percentiles: Dict[int, float]  # percentile -> citation_count
    mean_citations: float
    median_citations: float
    std_citations: float

    # Year breakdown
    yearly_stats: Dict[int, YearCitationStats]

    # Quality indicators
    high_impact_papers: List[Paper]  # Top 10% by citations
    breakthrough_papers: List[BreakthroughPaper]
    recommended_threshold: int


@dataclass
class CitationAnalysisReport:
    """Comprehensive citation analysis results."""

    papers_analyzed: int
    analysis_timestamp: datetime
    venue_analysis: Dict[str, VenueCitationStats]
    year_analysis: Dict[int, YearCitationStats]

    # Distribution insights
    overall_percentiles: Dict[int, float]  # percentile -> citation_count
    breakthrough_candidates: List[BreakthroughPaper]
    high_citation_outliers: List[Paper]  # Unusually high citations
    zero_citation_papers: List[Paper]  # Papers with no citations

    # Recommendations
    suggested_thresholds: Dict[Tuple[str, int], int]  # (venue, year) -> threshold
    quality_indicators: Dict[str, float]  # Various quality metrics
    filtering_recommendations: List[str]


@dataclass
class CitationFilterResult:
    """Result of citation-based filtering."""

    original_count: int
    filtered_count: int
    papers_above_threshold: List[Paper]
    papers_below_threshold: List[Paper]
    breakthrough_papers_preserved: List[Paper]

    # Filtering statistics
    filtering_statistics: Dict[str, int]  # reason -> count
    threshold_compliance: Dict[
        Tuple[str, int], float
    ]  # (venue, year) -> compliance_rate
    venue_representation: Dict[str, int]  # venue -> papers_kept

    # Quality metrics
    estimated_precision: float  # Quality of papers kept
    estimated_coverage: float  # Coverage of important papers
    breakthrough_preservation_rate: float  # % of breakthrough papers kept


@dataclass
class AdaptiveThreshold:
    """Adaptive citation threshold for venue/year."""

    venue: str
    year: int
    threshold: int
    confidence: float  # 0.0 to 1.0

    # Calculation factors
    base_threshold: int  # Base threshold for venue tier
    recency_adjustment: float  # Adjustment for paper age
    venue_prestige_multiplier: float  # Venue prestige factor
    representation_requirement: int  # Minimum papers to keep

    # Supporting data
    papers_analyzed: int
    papers_above_threshold: int
    percentile_used: float  # Percentile this threshold represents
    alternative_thresholds: Dict[str, int]  # Other threshold options


@dataclass
class FilteringQualityReport:
    """Quality report for citation filtering."""

    total_papers_original: int
    total_papers_filtered: int

    # Venue coverage
    venues_original: int
    venues_preserved: int
    venue_coverage_rate: float

    # Impact preservation
    high_impact_papers_original: int
    high_impact_papers_preserved: int
    impact_preservation_rate: float

    # Breakthrough preservation
    breakthrough_papers_original: int
    breakthrough_papers_preserved: int
    breakthrough_preservation_rate: float

    # Quality indicators
    average_citations_original: float
    average_citations_filtered: float
    citation_improvement_ratio: float

    # Warning flags
    warnings: List[str]
    recommendations: List[str]
