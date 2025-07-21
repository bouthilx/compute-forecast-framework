"""Citation analysis and filtering system for research papers."""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np
import logging

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.metadata_collection.collectors.state_structures import (
    VenueConfig,
)
from compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector import (
    BreakthroughDetector,
)
from compute_forecast.pipeline.metadata_collection.processors.adaptive_threshold_calculator import (
    AdaptiveThresholdCalculator,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_statistics import (
    CitationAnalysisReport,
    VenueCitationStats,
    YearCitationStats,
    CitationFilterResult,
    BreakthroughPaper,
    AdaptiveThreshold,
    FilteringQualityReport,
)
from compute_forecast.pipeline.metadata_collection.processors.citation_config import (
    CitationConfig,
)

logger = logging.getLogger(__name__)


class CitationAnalyzer:
    """Analyze and filter papers based on citation patterns and breakthrough potential."""

    def __init__(
        self, venue_configs: List[VenueConfig], config: Optional[CitationConfig] = None
    ):
        """Initialize with venue-specific citation thresholds."""
        self.venue_configs = {vc.venue_name: vc for vc in venue_configs}
        self.config = config or CitationConfig()
        self.breakthrough_detector = BreakthroughDetector(self.config)
        self.threshold_calculator = AdaptiveThresholdCalculator(self.config)
        self.current_year = datetime.now().year

    def analyze_citation_distributions(
        self, papers: List[Paper]
    ) -> CitationAnalysisReport:
        """
        Analyze citation patterns across venues and years.

        REQUIREMENTS:
        - Must calculate percentiles per venue/year
        - Must identify outliers and breakthrough candidates
        - Must suggest adaptive thresholds
        - Must process 50,000+ papers within 2 minutes
        """
        analysis_start = datetime.now()

        # Input validation
        valid_papers = self._validate_papers(papers)
        if len(valid_papers) < len(papers):
            logger.warning(
                f"Filtered out {len(papers) - len(valid_papers)} invalid papers"
            )

        # Group papers by venue and year
        venue_papers = defaultdict(list)
        year_papers = defaultdict(list)

        for paper in valid_papers:
            venue_key = paper.normalized_venue or paper.venue
            if venue_key:
                venue_papers[venue_key].append(paper)
            if paper.year:
                year_papers[paper.year].append(paper)

        # Analyze each venue
        venue_analysis = {}
        for venue, venue_paper_list in venue_papers.items():
            venue_analysis[venue] = self._analyze_venue_citations(
                venue, venue_paper_list
            )

        # Analyze each year
        year_analysis = {}
        for year, year_paper_list in year_papers.items():
            year_analysis[year] = self._analyze_year_citations(year, year_paper_list)

        # Overall distribution analysis
        all_citations = [p.get_latest_citations_count() for p in valid_papers]
        overall_percentiles = self._calculate_percentiles(all_citations)

        # Detect breakthrough candidates
        breakthrough_candidates = self.breakthrough_detector.detect_breakthrough_papers(
            valid_papers
        )

        # Identify outliers
        high_citation_threshold = overall_percentiles.get(95, 100)
        high_citation_outliers = [
            p
            for p in valid_papers
            if p.get_latest_citations_count() > high_citation_threshold
        ]
        zero_citation_papers = [
            p for p in valid_papers if p.get_latest_citations_count() == 0
        ]

        # Generate threshold recommendations
        suggested_thresholds = self._generate_threshold_recommendations(
            venue_analysis, year_analysis
        )

        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators(
            valid_papers, venue_analysis
        )

        # Generate filtering recommendations
        filtering_recommendations = self._generate_filtering_recommendations(
            venue_analysis
        )

        return CitationAnalysisReport(
            papers_analyzed=len(valid_papers),
            analysis_timestamp=analysis_start,
            venue_analysis=venue_analysis,
            year_analysis=year_analysis,
            overall_percentiles=overall_percentiles,
            breakthrough_candidates=breakthrough_candidates,
            high_citation_outliers=high_citation_outliers,
            zero_citation_papers=zero_citation_papers,
            suggested_thresholds=suggested_thresholds,
            quality_indicators=quality_indicators,
            filtering_recommendations=filtering_recommendations,
        )

    def filter_papers_by_citations(
        self, papers: List[Paper], preserve_breakthroughs: bool = True
    ) -> CitationFilterResult:
        """
        Filter papers using adaptive citation thresholds.

        REQUIREMENTS:
        - Must apply venue/year-specific thresholds
        - Must preserve breakthrough papers regardless of citations
        - Must maintain filtering statistics
        - Must provide justification for each filtering decision
        """
        original_count = len(papers)

        # Input validation
        valid_papers = self._validate_papers(papers)
        if len(valid_papers) < len(papers):
            logger.warning(
                f"Filtered out {len(papers) - len(valid_papers)} invalid papers"
            )

        papers_above_threshold = []
        papers_below_threshold = []
        breakthrough_papers_preserved = []
        filtering_statistics: Dict[str, int] = defaultdict(int)
        venue_representation: Dict[str, int] = defaultdict(int)

        # First detect breakthrough papers if preservation is enabled
        breakthrough_papers = set()
        if preserve_breakthroughs:
            breakthrough_candidates = (
                self.breakthrough_detector.detect_breakthrough_papers(valid_papers)
            )
            breakthrough_papers = {
                bp.paper.paper_id for bp in breakthrough_candidates if bp.paper.paper_id
            }

        # Calculate thresholds for each venue/year combination
        venue_year_thresholds = {}
        for paper in valid_papers:
            venue = paper.normalized_venue or paper.venue
            year = paper.year

            if venue and year and (venue, year) not in venue_year_thresholds:
                venue_tier = self._get_venue_tier(venue)
                threshold = self.threshold_calculator.calculate_venue_threshold(
                    venue, year, valid_papers, venue_tier
                )
                venue_year_thresholds[(venue, year)] = threshold

        # Filter papers
        for paper in valid_papers:
            venue = paper.normalized_venue or paper.venue
            year = paper.year

            # Check if it's a breakthrough paper
            is_breakthrough = (
                paper.paper_id in breakthrough_papers if paper.paper_id else False
            )

            if is_breakthrough and preserve_breakthroughs:
                papers_above_threshold.append(paper)
                breakthrough_papers_preserved.append(paper)
                filtering_statistics["breakthrough_preserved"] += 1
                if venue:
                    venue_representation[venue] += 1
            else:
                # Apply venue/year-specific threshold
                threshold = venue_year_thresholds.get(
                    (venue, year), 5
                )  # Default threshold

                if paper.get_latest_citations_count() >= threshold:
                    papers_above_threshold.append(paper)
                    filtering_statistics["above_threshold"] += 1
                    if venue:
                        venue_representation[venue] += 1
                else:
                    papers_below_threshold.append(paper)
                    if paper.get_latest_citations_count() == 0:
                        filtering_statistics["no_citation_data"] += 1
                    else:
                        filtering_statistics["below_threshold"] += 1

        # Calculate threshold compliance
        threshold_compliance = {}
        for (venue, year), threshold in venue_year_thresholds.items():
            venue_year_papers = [
                p
                for p in valid_papers
                if (p.normalized_venue or p.venue) == venue and p.year == year
            ]
            if venue_year_papers:
                above_count = len(
                    [p for p in venue_year_papers if p in papers_above_threshold]
                )
                compliance_rate = above_count / len(venue_year_papers)
                threshold_compliance[(venue, year)] = compliance_rate

        # Calculate quality metrics
        filtered_count = len(papers_above_threshold)

        # Estimated precision (quality of papers kept)
        avg_citations_original = (
            np.mean([p.get_latest_citations_count() for p in valid_papers])
            if valid_papers
            else 0
        )
        avg_citations_filtered = (
            np.mean([p.get_latest_citations_count() for p in papers_above_threshold])
            if papers_above_threshold
            else 0
        )
        estimated_precision = (
            min(avg_citations_filtered / avg_citations_original, 1.0)
            if avg_citations_original > 0
            else 0.0
        )

        # Estimated coverage (coverage of important papers)
        high_impact_original = len(
            [p for p in valid_papers if p.get_latest_citations_count() > 50]
        )
        high_impact_kept = len(
            [p for p in papers_above_threshold if p.get_latest_citations_count() > 50]
        )
        estimated_coverage = (
            high_impact_kept / high_impact_original if high_impact_original > 0 else 1.0
        )

        # Breakthrough preservation rate
        breakthrough_preservation_rate = (
            len(breakthrough_papers_preserved) / len(breakthrough_papers)
            if breakthrough_papers
            else 1.0
        )

        return CitationFilterResult(
            original_count=original_count,
            filtered_count=filtered_count,
            papers_above_threshold=papers_above_threshold,
            papers_below_threshold=papers_below_threshold,
            breakthrough_papers_preserved=breakthrough_papers_preserved,
            filtering_statistics=dict(filtering_statistics),
            threshold_compliance=threshold_compliance,
            venue_representation=dict(venue_representation),
            estimated_precision=estimated_precision,
            estimated_coverage=estimated_coverage,
            breakthrough_preservation_rate=breakthrough_preservation_rate,
        )

    def detect_breakthrough_papers(
        self, papers: List[Paper]
    ) -> List[BreakthroughPaper]:
        """
        Identify papers with breakthrough potential.

        REQUIREMENTS:
        - Must consider citation velocity, recency, keywords, authors
        - Must provide breakthrough score (0.0 to 1.0)
        - Must include justification for breakthrough classification
        """
        return self.breakthrough_detector.detect_breakthrough_papers(papers)

    def calculate_adaptive_threshold(
        self, venue: str, year: int, papers: List[Paper]
    ) -> AdaptiveThreshold:
        """
        Calculate adaptive citation threshold for venue/year.

        REQUIREMENTS:
        - Must consider venue prestige tier
        - Must account for paper recency (newer = lower threshold)
        - Must ensure minimum representation from each venue
        """
        venue_tier = self._get_venue_tier(venue)
        return self.threshold_calculator.calculate_adaptive_threshold(
            venue, year, papers, venue_tier
        )

    def validate_filtering_quality(
        self, original_papers: List[Paper], filtered_papers: List[Paper]
    ) -> FilteringQualityReport:
        """Validate that filtering preserves important papers."""
        original_count = len(original_papers)
        filtered_count = len(filtered_papers)

        # Venue coverage
        original_venues = set(
            p.normalized_venue or p.venue
            for p in original_papers
            if p.normalized_venue or p.venue
        )
        preserved_venues = set(
            p.normalized_venue or p.venue
            for p in filtered_papers
            if p.normalized_venue or p.venue
        )
        venue_coverage_rate = (
            len(preserved_venues) / len(original_venues) if original_venues else 0.0
        )

        # High-impact preservation
        high_impact_threshold = self.config.high_impact_citation_threshold
        high_impact_original = [
            p
            for p in original_papers
            if p.get_latest_citations_count() > high_impact_threshold
        ]
        high_impact_preserved = [
            p
            for p in filtered_papers
            if p.get_latest_citations_count() > high_impact_threshold
        ]
        impact_preservation_rate = (
            len(high_impact_preserved) / len(high_impact_original)
            if high_impact_original
            else 1.0
        )

        # Breakthrough preservation
        breakthrough_original = self.breakthrough_detector.detect_breakthrough_papers(
            original_papers
        )
        breakthrough_ids = {
            bp.paper.paper_id for bp in breakthrough_original if bp.paper.paper_id
        }
        breakthrough_preserved = [
            p for p in filtered_papers if p.paper_id in breakthrough_ids
        ]
        breakthrough_preservation_rate = (
            len(breakthrough_preserved) / len(breakthrough_original)
            if breakthrough_original
            else 1.0
        )

        # Quality indicators
        avg_citations_original = (
            np.mean([p.get_latest_citations_count() for p in original_papers])
            if original_papers
            else 0
        )
        avg_citations_filtered = (
            np.mean([p.get_latest_citations_count() for p in filtered_papers])
            if filtered_papers
            else 0
        )
        citation_improvement_ratio = (
            avg_citations_filtered / avg_citations_original
            if avg_citations_original > 0
            else 0.0
        )

        # Generate warnings and recommendations
        warnings = []
        recommendations = []

        if venue_coverage_rate < 0.8:
            warnings.append(
                f"Low venue coverage: {venue_coverage_rate:.1%} of venues preserved"
            )
            recommendations.append(
                "Consider lowering thresholds for underrepresented venues"
            )

        if impact_preservation_rate < 0.9:
            warnings.append(
                f"High-impact paper loss: {1 - impact_preservation_rate:.1%} of high-impact papers filtered out"
            )
            recommendations.append("Review threshold settings for high-impact papers")

        if breakthrough_preservation_rate < 0.95:
            warnings.append(
                f"Breakthrough paper loss: {1 - breakthrough_preservation_rate:.1%} of breakthrough papers filtered out"
            )
            recommendations.append("Enable breakthrough preservation in filtering")

        if filtered_count < original_count * 0.1:
            warnings.append(
                f"Aggressive filtering: only {filtered_count / original_count:.1%} of papers retained"
            )
            recommendations.append("Consider more lenient filtering thresholds")

        return FilteringQualityReport(
            total_papers_original=original_count,
            total_papers_filtered=filtered_count,
            venues_original=len(original_venues),
            venues_preserved=len(preserved_venues),
            venue_coverage_rate=venue_coverage_rate,
            high_impact_papers_original=len(high_impact_original),
            high_impact_papers_preserved=len(high_impact_preserved),
            impact_preservation_rate=impact_preservation_rate,
            breakthrough_papers_original=len(breakthrough_original),
            breakthrough_papers_preserved=len(breakthrough_preserved),
            breakthrough_preservation_rate=breakthrough_preservation_rate,
            average_citations_original=avg_citations_original,
            average_citations_filtered=avg_citations_filtered,
            citation_improvement_ratio=citation_improvement_ratio,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _analyze_venue_citations(
        self, venue: str, papers: List[Paper]
    ) -> VenueCitationStats:
        """Analyze citation patterns for specific venue."""
        citations = [p.get_latest_citations_count() for p in papers]

        # Calculate basic statistics
        percentiles = self._calculate_percentiles(citations)
        mean_citations = np.mean(citations) if citations else 0.0
        median_citations = np.median(citations) if citations else 0.0
        std_citations = np.std(citations) if citations else 0.0

        # Year breakdown
        yearly_stats = {}
        papers_by_year = defaultdict(list)
        for paper in papers:
            if paper.year:
                papers_by_year[paper.year].append(paper)

        for year, year_papers in papers_by_year.items():
            yearly_stats[year] = self._analyze_year_citations(year, year_papers)

        # Identify high-impact papers (top percentage from config)
        high_impact_threshold = (
            percentiles.get(int(self.config.high_impact_percentile), mean_citations * 2)
            if percentiles
            else 0
        )
        high_impact_papers = [
            p for p in papers if p.get_latest_citations_count() >= high_impact_threshold
        ]

        # Find breakthrough papers
        breakthrough_papers = self.breakthrough_detector.detect_breakthrough_papers(
            papers
        )
        venue_breakthrough_papers = [
            bp
            for bp in breakthrough_papers
            if (bp.paper.normalized_venue or bp.paper.venue) == venue
        ]

        # Calculate recommended threshold
        venue_tier = self._get_venue_tier(venue)
        recent_year = (
            max(papers_by_year.keys()) if papers_by_year else self.current_year - 1
        )
        recommended_threshold = self.threshold_calculator.calculate_venue_threshold(
            venue, recent_year, papers, venue_tier
        )

        return VenueCitationStats(
            venue_name=venue,
            venue_tier=venue_tier,
            total_papers=len(papers),
            citation_percentiles=percentiles,
            mean_citations=mean_citations,
            median_citations=median_citations,
            std_citations=std_citations,
            yearly_stats=yearly_stats,
            high_impact_papers=high_impact_papers,
            breakthrough_papers=venue_breakthrough_papers,
            recommended_threshold=recommended_threshold,
        )

    def _analyze_year_citations(
        self, year: int, papers: List[Paper]
    ) -> YearCitationStats:
        """Analyze citation patterns for specific year."""
        citations = [p.get_latest_citations_count() for p in papers]
        years_since_publication = self.current_year - year

        # Calculate statistics
        percentiles = self._calculate_percentiles(citations)
        mean_citations = np.mean(citations) if citations else 0.0
        median_citations = np.median(citations) if citations else 0.0

        # Calculate citation velocity
        if years_since_publication > 0 and citations:
            actual_velocity = mean_citations / years_since_publication
            # Expected velocity based on year (newer papers accumulate citations faster initially)
            if years_since_publication <= 2:
                expected_velocity = 10.0
            elif years_since_publication <= 5:
                expected_velocity = 8.0
            else:
                expected_velocity = 5.0
        else:
            actual_velocity = 0.0
            expected_velocity = 0.0

        return YearCitationStats(
            year=year,
            total_papers=len(papers),
            citation_percentiles=percentiles,
            mean_citations=mean_citations,
            median_citations=median_citations,
            years_since_publication=years_since_publication,
            expected_citation_velocity=expected_velocity,
            actual_citation_velocity=actual_velocity,
        )

    def _calculate_percentiles(self, citations: List[int]) -> Dict[int, float]:
        """Calculate citation percentiles."""
        if not citations:
            return {}

        percentiles = {}
        for p in [10, 25, 50, 75, 80, 90, 95, 99]:
            percentiles[p] = float(np.percentile(citations, p))

        return percentiles

    def _get_venue_tier(self, venue: str) -> str:
        """Get venue tier for prestige calculation."""
        return self.config.get_venue_tier(venue)

    def _generate_threshold_recommendations(
        self,
        venue_analysis: Dict[str, VenueCitationStats],
        year_analysis: Dict[int, YearCitationStats],
    ) -> Dict[Tuple[str, int], int]:
        """Generate threshold recommendations for each venue/year combination."""
        recommendations = {}

        for venue, venue_stats in venue_analysis.items():
            self._get_venue_tier(venue)

            # Use the venue's recommended threshold for all years in the venue
            for year in venue_stats.yearly_stats.keys():
                # Use the already calculated recommended threshold from venue stats
                threshold = venue_stats.recommended_threshold
                recommendations[(venue, year)] = threshold

        return recommendations

    def _calculate_quality_indicators(
        self, papers: List[Paper], venue_analysis: Dict[str, VenueCitationStats]
    ) -> Dict[str, float]:
        """Calculate various quality indicators for the paper collection."""
        indicators = {}

        # Overall quality metrics
        citations = [p.get_latest_citations_count() for p in papers]
        if citations:
            indicators["mean_citations"] = float(np.mean(citations))
            indicators["median_citations"] = float(np.median(citations))
            indicators["citation_variance"] = float(np.var(citations))
            indicators["zero_citation_rate"] = sum(
                1 for c in citations if c == 0
            ) / len(citations)

        # Venue diversity
        indicators["venue_count"] = len(venue_analysis)
        indicators["papers_per_venue"] = (
            len(papers) / len(venue_analysis) if venue_analysis else 0
        )

        # Breakthrough potential
        breakthrough_papers = self.breakthrough_detector.detect_breakthrough_papers(
            papers
        )
        indicators["breakthrough_rate"] = (
            len(breakthrough_papers) / len(papers) if papers else 0
        )
        indicators["avg_breakthrough_score"] = (
            np.mean([bp.breakthrough_score for bp in breakthrough_papers])
            if breakthrough_papers
            else 0
        )

        # Time relevance
        current_year = self.current_year
        recent_papers = [p for p in papers if p.year and p.year >= current_year - 3]
        indicators["recent_paper_rate"] = (
            len(recent_papers) / len(papers) if papers else 0
        )

        return indicators

    def _generate_filtering_recommendations(
        self, venue_analysis: Dict[str, VenueCitationStats]
    ) -> List[str]:
        """Generate specific recommendations for filtering strategy."""
        recommendations = []

        # Check venue representation
        low_paper_venues = [
            v for v, stats in venue_analysis.items() if stats.total_papers < 20
        ]
        if low_paper_venues:
            recommendations.append(
                f"Consider lower thresholds for venues with few papers: {', '.join(low_paper_venues[:3])}"
            )

        # Check breakthrough paper distribution
        total_breakthroughs = sum(
            len(stats.breakthrough_papers) for stats in venue_analysis.values()
        )
        if total_breakthroughs < len(venue_analysis) * 2:
            recommendations.append(
                "Enable breakthrough preservation to retain high-potential papers with lower citations"
            )

        # Check citation distribution
        high_variance_venues = []
        for venue, stats in venue_analysis.items():
            if stats.std_citations > stats.mean_citations * 2:
                high_variance_venues.append(venue)

        if high_variance_venues:
            recommendations.append(
                f"Use adaptive thresholds for high-variance venues: {', '.join(high_variance_venues[:3])}"
            )

        # General recommendations
        recommendations.append(
            "Consider venue-specific and year-specific thresholds for optimal filtering"
        )
        recommendations.append(
            "Validate filtering results to ensure important papers are preserved"
        )

        return recommendations

    def _validate_papers(self, papers: List[Paper]) -> List[Paper]:
        """Validate papers and filter out invalid ones."""
        valid_papers = []
        for paper in papers:
            # Skip papers with invalid years
            if paper.year and paper.year > self.current_year:
                logger.warning(f"Skipping paper with future year: {paper.year}")
                continue

            # Skip papers with negative citations
            if paper.get_latest_citations_count() < 0:
                logger.warning(
                    f"Skipping paper with negative citations: {paper.get_latest_citations_count()}"
                )
                continue

            valid_papers.append(paper)

        return valid_papers
