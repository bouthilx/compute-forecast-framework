"""
Statistical Analyzer for Issue #9 - Data Analysis System.
Provides comprehensive statistical analysis of collected academic papers.
"""

import logging
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, cast
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PaperStatistics:
    """Statistics for individual papers or paper collections."""

    total_papers: int = 0
    citation_stats: Dict[str, float] = field(default_factory=dict)
    author_stats: Dict[str, float] = field(default_factory=dict)
    venue_distribution: Dict[str, int] = field(default_factory=dict)
    year_distribution: Dict[int, int] = field(default_factory=dict)
    page_stats: Dict[str, float] = field(default_factory=dict)

    # Derived metrics
    avg_citations_per_paper: float = 0.0
    citation_growth_rate: float = 0.0
    venue_diversity_index: float = 0.0
    temporal_coverage: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_papers": self.total_papers,
            "citation_stats": self.citation_stats,
            "author_stats": self.author_stats,
            "venue_distribution": self.venue_distribution,
            "year_distribution": self.year_distribution,
            "page_stats": self.page_stats,
            "avg_citations_per_paper": self.avg_citations_per_paper,
            "citation_growth_rate": self.citation_growth_rate,
            "venue_diversity_index": self.venue_diversity_index,
            "temporal_coverage": self.temporal_coverage,
        }


@dataclass
class VenueStatistics:
    """Statistics for specific venues."""

    venue_name: str
    total_papers: int = 0
    years_covered: List[int] = field(default_factory=list)
    impact_metrics: Dict[str, float] = field(default_factory=dict)
    author_metrics: Dict[str, Any] = field(default_factory=dict)
    citation_metrics: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "venue_name": self.venue_name,
            "total_papers": self.total_papers,
            "years_covered": self.years_covered,
            "impact_metrics": self.impact_metrics,
            "author_metrics": self.author_metrics,
            "citation_metrics": self.citation_metrics,
            "quality_metrics": self.quality_metrics,
        }


@dataclass
class AnalysisSummary:
    """Overall analysis summary."""

    analysis_timestamp: datetime = field(default_factory=datetime.now)
    total_papers_analyzed: int = 0
    venues_analyzed: List[str] = field(default_factory=list)
    year_range: Tuple[int, int] = (0, 0)
    key_insights: List[str] = field(default_factory=list)
    statistical_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "total_papers_analyzed": self.total_papers_analyzed,
            "venues_analyzed": self.venues_analyzed,
            "year_range": self.year_range,
            "key_insights": self.key_insights,
            "statistical_summary": self.statistical_summary,
        }


class StatisticalAnalyzer:
    """
    Comprehensive statistical analyzer for academic paper collections.

    Features:
    - Descriptive statistics for papers, citations, and authors
    - Venue-specific statistical analysis
    - Temporal analysis and trends
    - Citation distribution analysis
    - Author collaboration patterns
    - Quality metrics calculation
    """

    def __init__(self):
        self.analysis_cache: Dict[str, Any] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=1)

        logger.info("StatisticalAnalyzer initialized")

    def analyze_paper_collection(self, papers: List[Dict[str, Any]]) -> PaperStatistics:
        """
        Perform comprehensive statistical analysis of paper collection.

        Args:
            papers: List of paper dictionaries with metadata

        Returns:
            PaperStatistics object with comprehensive analysis
        """
        if not papers:
            return PaperStatistics()

        # Cache key for this analysis
        cache_key = f"paper_analysis_{len(papers)}_{hash(str(sorted(p.get('paper_id', '') for p in papers[:10])))}"

        if self._is_cached(cache_key):
            cached_result = self.analysis_cache[cache_key]
            if isinstance(cached_result, PaperStatistics):
                return cached_result
            return cast(PaperStatistics, cached_result)

        stats = PaperStatistics()
        stats.total_papers = len(papers)

        # Extract data for analysis
        citations = [
            p.get("citation_count", 0)
            for p in papers
            if p.get("citation_count") is not None
        ]
        authors = [
            p.get("author_count", 0)
            for p in papers
            if p.get("author_count") is not None
        ]
        pages = [
            p.get("page_count", 0) for p in papers if p.get("page_count") is not None
        ]
        venues = [p.get("venue", "Unknown") for p in papers if p.get("venue")]
        years = [
            year for p in papers if (year := p.get("year")) is not None and year > 1900
        ]

        # Citation statistics
        if citations:
            stats.citation_stats = {
                "mean": float(np.mean(citations)),
                "median": float(np.median(citations)),
                "std": float(np.std(citations)),
                "min": float(np.min(citations)),
                "max": float(np.max(citations)),
                "q25": float(np.percentile(citations, 25)),
                "q75": float(np.percentile(citations, 75)),
                "skewness": float(self._calculate_skewness(citations)),
                "total_citations": sum(citations),
            }
            stats.avg_citations_per_paper = stats.citation_stats["mean"]

        # Author statistics
        if authors:
            stats.author_stats = {
                "mean_authors_per_paper": float(np.mean(authors)),
                "median_authors_per_paper": float(np.median(authors)),
                "std_authors_per_paper": float(np.std(authors)),
                "min_authors": int(np.min(authors)),
                "max_authors": int(np.max(authors)),
                "single_author_papers": sum(1 for a in authors if a == 1),
                "multi_author_papers": sum(1 for a in authors if a > 1),
            }

        # Page statistics
        if pages:
            stats.page_stats = {
                "mean_pages": float(np.mean(pages)),
                "median_pages": float(np.median(pages)),
                "std_pages": float(np.std(pages)),
                "min_pages": int(np.min(pages)),
                "max_pages": int(np.max(pages)),
            }

        # Venue distribution
        venue_counts = Counter(venues)
        stats.venue_distribution = dict(venue_counts)

        # Calculate venue diversity (Shannon diversity index)
        if venue_counts:
            total = sum(venue_counts.values())
            proportions = [count / total for count in venue_counts.values()]
            stats.venue_diversity_index = -sum(
                p * np.log(p) for p in proportions if p > 0
            )

        # Year distribution
        year_counts = Counter(years)
        stats.year_distribution = dict(year_counts)

        # Temporal coverage
        if years:
            stats.temporal_coverage = max(years) - min(years) + 1

            # Calculate citation growth rate if we have multi-year data
            if len(set(years)) > 1:
                stats.citation_growth_rate = self._calculate_citation_growth_rate(
                    papers
                )

        # Cache the result
        self._cache_result(cache_key, stats)

        return stats

    def analyze_venue_specific(
        self, papers: List[Dict[str, Any]], venue: str
    ) -> VenueStatistics:
        """
        Perform venue-specific statistical analysis.

        Args:
            papers: List of papers from the venue
            venue: Venue name

        Returns:
            VenueStatistics object with venue-specific analysis
        """
        venue_papers = [
            p for p in papers if p.get("venue", "").lower() == venue.lower()
        ]

        if not venue_papers:
            return VenueStatistics(venue_name=venue)

        stats = VenueStatistics(venue_name=venue)
        stats.total_papers = len(venue_papers)

        # Years covered
        years = [
            year
            for p in venue_papers
            if (year := p.get("year")) is not None
            and isinstance(year, int)
            and year > 1900
        ]
        stats.years_covered = sorted(list(set(years)))

        # Impact metrics
        citations = [
            p.get("citation_count", 0)
            for p in venue_papers
            if p.get("citation_count") is not None
        ]
        if citations:
            stats.impact_metrics = {
                "total_citations": sum(citations),
                "avg_citations_per_paper": np.mean(citations),
                "h_index": self._calculate_h_index(citations),
                "citation_variance": np.var(citations),
                "high_impact_papers": sum(
                    1 for c in citations if c > np.percentile(citations, 90)
                ),
            }

        # Author metrics
        authors_per_paper = [
            p.get("author_count", 0) for p in venue_papers if p.get("author_count")
        ]
        if authors_per_paper:
            # Extract unique authors (simplified - would need actual author lists)
            estimated_unique_authors = sum(authors_per_paper) * 0.7  # Rough estimate

            stats.author_metrics = {
                "avg_authors_per_paper": np.mean(authors_per_paper),
                "estimated_unique_authors": int(estimated_unique_authors),
                "collaboration_index": np.mean(authors_per_paper)
                / max(authors_per_paper)
                if authors_per_paper
                else 0,
            }

        # Citation metrics by year
        if years and citations:
            citation_by_year = defaultdict(list)
            for paper in venue_papers:
                year = paper.get("year")
                cites = paper.get("citation_count", 0)
                if year and cites is not None:
                    citation_by_year[year].append(cites)

            stats.citation_metrics = {
                "citation_growth_trend": self._analyze_yearly_citation_trend(
                    citation_by_year
                ),
                "peak_year": max(
                    citation_by_year.keys(), key=lambda y: np.mean(citation_by_year[y])
                )
                if citation_by_year
                else None,
                "most_productive_year": max(years, key=years.count) if years else None,
            }

        # Quality metrics
        if venue_papers:
            quality_scores = []
            for paper in venue_papers:
                # Calculate a simple quality score based on available metrics
                citation_count = (
                    int(paper.get("citation_count", 0))
                    if isinstance(paper.get("citation_count", 0), (int, float))
                    else 0
                )
                authors = (
                    int(paper.get("author_count", 1))
                    if isinstance(paper.get("author_count", 1), (int, float))
                    else 1
                )
                pages = (
                    int(paper.get("page_count", 0))
                    if isinstance(paper.get("page_count", 0), (int, float))
                    else 0
                )

                # Simple quality scoring
                quality_score = (
                    min(citation_count / 50.0, 1.0) * 0.6  # Citation component
                    + min(authors / 10.0, 1.0) * 0.2  # Author component
                    + min(pages / 20.0, 1.0) * 0.2  # Page component
                )
                quality_scores.append(quality_score)

            if quality_scores:
                stats.quality_metrics = {
                    "avg_quality_score": float(np.mean(quality_scores)),
                    "quality_variance": float(np.var(quality_scores)),
                    "high_quality_papers": sum(1 for q in quality_scores if q > 0.7),
                    "excellent_papers": sum(1 for q in quality_scores if q > 0.8),
                    "good_papers": sum(1 for q in quality_scores if 0.6 < q <= 0.8),
                    "fair_papers": sum(1 for q in quality_scores if 0.4 < q <= 0.6),
                    "poor_papers": sum(1 for q in quality_scores if q <= 0.4),
                }

        return stats

    def generate_analysis_summary(
        self, papers: List[Dict[str, Any]]
    ) -> AnalysisSummary:
        """
        Generate comprehensive analysis summary.

        Args:
            papers: Complete paper collection

        Returns:
            AnalysisSummary with key insights and statistics
        """
        summary = AnalysisSummary()
        summary.total_papers_analyzed = len(papers)

        if not papers:
            return summary

        # Extract basic information
        venues = list(set(p.get("venue", "Unknown") for p in papers if p.get("venue")))
        years = [
            year
            for p in papers
            if (year := p.get("year")) is not None
            and isinstance(year, int)
            and year > 1900
        ]

        summary.venues_analyzed = sorted(venues)
        if years:
            summary.year_range = (min(years), max(years))

        # Generate statistical summary
        paper_stats = self.analyze_paper_collection(papers)
        summary.statistical_summary = paper_stats.to_dict()

        # Generate key insights
        insights = self._generate_key_insights(papers, paper_stats)
        summary.key_insights = insights

        return summary

    def compare_venues(
        self, papers: List[Dict[str, Any]], venues: List[str]
    ) -> Dict[str, VenueStatistics]:
        """
        Compare statistical metrics across multiple venues.

        Args:
            papers: Complete paper collection
            venues: List of venues to compare

        Returns:
            Dictionary mapping venue names to their statistics
        """
        comparison = {}

        for venue in venues:
            venue_stats = self.analyze_venue_specific(papers, venue)
            comparison[venue] = venue_stats

        return comparison

    def _calculate_h_index(self, citations: List[int]) -> int:
        """Calculate h-index from citation counts."""
        if not citations:
            return 0

        # Sort citations in descending order
        sorted_citations = sorted(citations, reverse=True)

        h_index = 0
        for i, citation_count in enumerate(sorted_citations, 1):
            if citation_count >= i:
                h_index = i
            else:
                break

        return h_index

    def _calculate_skewness(self, data: List[float]) -> float:
        """Calculate skewness of data distribution."""
        if len(data) < 3:
            return 0.0

        mean = np.mean(data)
        std = np.std(data)

        if std == 0:
            return 0.0

        n = len(data)
        skewness = (n / ((n - 1) * (n - 2))) * sum(
            ((x - mean) / std) ** 3 for x in data
        )

        return float(skewness)

    def _calculate_citation_growth_rate(self, papers: List[Dict[str, Any]]) -> float:
        """Calculate citation growth rate over time."""
        # Group papers by year and calculate average citations
        year_citations = defaultdict(list)

        for paper in papers:
            year = paper.get("year")
            citations = paper.get("citation_count", 0)
            if year and year > 1900 and citations is not None:
                year_citations[year].append(citations)

        if len(year_citations) < 2:
            return 0.0

        # Calculate average citations per year
        yearly_averages = {
            year: np.mean(cites) for year, cites in year_citations.items()
        }

        # Sort by year
        sorted_years = sorted(yearly_averages.keys())

        if len(sorted_years) < 2:
            return 0.0

        # Calculate simple growth rate
        first_year_avg = yearly_averages[sorted_years[0]]
        last_year_avg = yearly_averages[sorted_years[-1]]
        years_span = sorted_years[-1] - sorted_years[0]

        if first_year_avg == 0 or years_span == 0:
            return 0.0

        growth_rate = ((last_year_avg / first_year_avg) ** (1 / years_span)) - 1

        return float(growth_rate)

    def _analyze_yearly_citation_trend(
        self, citation_by_year: Dict[int, List[int]]
    ) -> str:
        """Analyze citation trend across years."""
        if len(citation_by_year) < 2:
            return "insufficient_data"

        yearly_averages = {
            year: np.mean(cites) for year, cites in citation_by_year.items()
        }
        sorted_years = sorted(yearly_averages.keys())

        # Simple trend analysis
        averages = [yearly_averages[year] for year in sorted_years]

        # Calculate correlation with time
        years_numeric = list(range(len(sorted_years)))
        correlation = np.corrcoef(years_numeric, averages)[0, 1]

        if correlation > 0.3:
            return "increasing"
        elif correlation < -0.3:
            return "decreasing"
        else:
            return "stable"

    def _generate_key_insights(
        self, papers: List[Dict[str, Any]], stats: PaperStatistics
    ) -> List[str]:
        """Generate key insights from the analysis."""
        insights = []

        # Citation insights
        if stats.citation_stats:
            avg_citations = stats.citation_stats["mean"]
            if avg_citations > 20:
                insights.append(
                    f"High-impact collection with average {avg_citations:.1f} citations per paper"
                )
            elif avg_citations < 5:
                insights.append(
                    "Collection contains primarily recent or emerging research papers"
                )

            # Citation distribution insights
            median_citations = stats.citation_stats["median"]
            if avg_citations > median_citations * 2:
                insights.append(
                    "Citation distribution is highly skewed with some extremely high-impact papers"
                )

        # Venue diversity insights
        if stats.venue_diversity_index > 2.0:
            insights.append(
                "Highly diverse collection spanning multiple research venues"
            )
        elif stats.venue_diversity_index < 1.0:
            insights.append("Collection is concentrated in a few specific venues")

        # Temporal insights
        if stats.temporal_coverage > 10:
            insights.append(
                f"Comprehensive temporal coverage spanning {stats.temporal_coverage} years"
            )

        # Collaboration insights
        if stats.author_stats:
            avg_authors = stats.author_stats["mean_authors_per_paper"]
            if avg_authors > 5:
                insights.append(
                    "Strong collaboration patterns with large research teams"
                )
            elif avg_authors < 2:
                insights.append("Individual research focus with limited collaboration")

        # Growth insights
        if stats.citation_growth_rate > 0.1:
            insights.append(
                "Strong citation growth indicating increasing research impact"
            )
        elif stats.citation_growth_rate < -0.1:
            insights.append("Declining citation patterns suggesting field maturation")

        return insights

    def _is_cached(self, cache_key: str) -> bool:
        """Check if analysis result is cached and still valid."""
        if cache_key not in self.analysis_cache:
            return False

        if cache_key not in self.cache_timestamp:
            return False

        return bool(
            (datetime.now() - self.cache_timestamp[cache_key]) < self.cache_duration
        )

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache analysis result with timestamp."""
        self.analysis_cache[cache_key] = result
        self.cache_timestamp[cache_key] = datetime.now()

        # Limit cache size
        if len(self.analysis_cache) > 100:
            # Remove oldest entries
            oldest_key = min(
                self.cache_timestamp.keys(), key=lambda k: self.cache_timestamp[k]
            )
            del self.analysis_cache[oldest_key]
            del self.cache_timestamp[oldest_key]
