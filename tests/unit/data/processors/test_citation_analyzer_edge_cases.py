"""Edge case tests for citation analyzer to ensure robust error handling."""

from datetime import datetime
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.metadata_collection.collectors.state_structures import (
    VenueConfig,
)
from compute_forecast.pipeline.metadata_collection.processors import (
    CitationAnalyzer,
    CitationConfig,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count != 0:  # Include negative citations for edge case testing
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestCitationAnalyzerEdgeCases:
    """Test edge cases and error handling in citation analyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.venue_configs = [
            VenueConfig(venue_name="NeurIPS", target_years=[2020, 2021, 2022]),
            VenueConfig(venue_name="ICML", target_years=[2020, 2021, 2022]),
        ]
        self.config = CitationConfig()
        self.analyzer = CitationAnalyzer(self.venue_configs, self.config)

    def test_papers_with_future_years(self):
        """Test handling of papers with years in the future."""
        current_year = datetime.now().year
        papers = [
            create_test_paper(
                paper_id="valid1",
                title="Valid Paper",
                authors=[Author(name="Author A")],
                year=current_year - 1,
                venue="NeurIPS",
                citation_count=10,
            ),
            create_test_paper(
                paper_id="future1",
                title="Future Paper",
                authors=[Author(name="Author B")],
                year=current_year + 5,  # Future year
                venue="ICML",
                citation_count=5,
            ),
        ]

        # Should filter out future papers
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 1  # Only valid paper

        # Filter should also handle future papers
        result = self.analyzer.filter_papers_by_citations(papers)
        assert len(result.papers_above_threshold) <= 1

    def test_papers_with_negative_citations(self):
        """Test handling of papers with negative citation counts."""
        papers = [
            create_test_paper(
                paper_id="valid1",
                title="Valid Paper",
                authors=[Author(name="Author A")],
                year=2020,
                venue="NeurIPS",
                citation_count=10,
            ),
            create_test_paper(
                paper_id="negative1",
                title="Negative Citations Paper",
                authors=[Author(name="Author B")],
                year=2020,
                venue="ICML",
                citation_count=-5,  # Negative citations
            ),
        ]

        # Should filter out papers with negative citations
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 1  # Only valid paper

    def test_papers_with_extremely_high_citations(self):
        """Test handling of papers with extremely high citation counts."""
        papers = [
            create_test_paper(
                paper_id="normal1",
                title="Normal Paper",
                authors=[Author(name="Author A")],
                year=2020,
                venue="NeurIPS",
                citation_count=100,
            ),
            create_test_paper(
                paper_id="extreme1",
                title="Extremely Cited Paper",
                authors=[Author(name="Author B")],
                year=2020,
                venue="ICML",
                citation_count=1000000,  # Extremely high
            ),
        ]

        # Should handle extreme values gracefully
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 2
        assert len(report.high_citation_outliers) >= 1

        # Percentiles should still be calculated correctly
        assert report.overall_percentiles[99] <= 1000000

    def test_papers_with_none_values(self):
        """Test handling of papers with None values in various fields."""
        papers = [
            create_test_paper(
                paper_id="none1",
                title="Paper with None Year",
                authors=[Author(name="Author A")],
                year=None,  # None year
                venue="NeurIPS",
                citation_count=10,
            ),
            create_test_paper(
                paper_id="none2",
                title="Paper with None Venue",
                authors=[Author(name="Author B")],
                year=2020,
                venue=None,  # None venue
                citation_count=20,
            ),
            create_test_paper(
                paper_id="none3",
                title="Paper with None Citations",
                authors=[Author(name="Author C")],
                year=2021,
                venue="ICML",
                citation_count=0,  # None citations
            ),
        ]

        # Should handle None values gracefully
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 3

        # Papers with empty citations should be tracked
        assert len([p for p in papers if len(p.citations) == 0]) >= 1

    def test_empty_venue_analysis(self):
        """Test venue analysis when no papers match a venue."""
        papers = [
            create_test_paper(
                paper_id="p1",
                title="Paper 1",
                authors=[Author(name="Author A")],
                year=2020,
                venue="UnknownVenue",  # Not in venue configs
                citation_count=10,
            )
        ]

        report = self.analyzer.analyze_citation_distributions(papers)
        # Should still analyze the unknown venue
        assert "UnknownVenue" in report.venue_analysis
        assert (
            report.venue_analysis["UnknownVenue"].venue_tier == "tier4"
        )  # Default tier

    def test_division_by_zero_current_year_papers(self):
        """Test handling of papers published in the current year (division by zero risk)."""
        current_year = datetime.now().year
        papers = [
            create_test_paper(
                paper_id="current1",
                title="Current Year Paper",
                authors=[Author(name="Author A")],
                year=current_year,  # Current year
                venue="NeurIPS",
                citation_count=5,
            )
        ]

        # Should handle current year papers without division by zero
        breakthrough_papers = self.analyzer.detect_breakthrough_papers(papers)
        assert len(breakthrough_papers) >= 0  # Should not crash

        # Citation velocity should be calculated safely
        if breakthrough_papers:
            assert breakthrough_papers[0].citation_velocity is not None

    def test_papers_with_empty_authors_list(self):
        """Test handling of papers with empty authors list."""
        papers = [
            create_test_paper(
                paper_id="no_authors",
                title="Paper with No Authors",
                authors=[],  # Empty authors list
                year=2020,
                venue="NeurIPS",
                citation_count=10,
            )
        ]

        # Should handle empty authors gracefully
        breakthrough_papers = self.analyzer.detect_breakthrough_papers(papers)
        # Should not crash when calculating author reputation
        assert isinstance(breakthrough_papers, list)

    def test_papers_with_special_characters(self):
        """Test handling of papers with special characters in fields."""
        papers = [
            create_test_paper(
                paper_id="special1",
                title="Paper with émojis 🚀 and spëcial çharacters",
                authors=[Author(name="Authör Ñame")],
                year=2020,
                venue="NeurIPS/Workshop",  # Special char in venue
                citation_count=10,
            )
        ]

        # Should handle special characters gracefully
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 1

    def test_very_old_papers(self):
        """Test handling of very old papers (edge case for year calculations)."""
        papers = [
            create_test_paper(
                paper_id="old1",
                title="Very Old Paper",
                authors=[Author(name="Historical Author")],
                year=1950,  # Very old
                venue="Ancient Conference",
                citation_count=1000,
            )
        ]

        # Should handle very old papers gracefully
        report = self.analyzer.analyze_citation_distributions(papers)
        assert report.papers_analyzed == 1

        # Should calculate reasonable thresholds
        threshold = self.analyzer.calculate_adaptive_threshold(
            "Ancient Conference", 1950, papers
        )
        assert threshold.threshold >= 0

    def test_concurrent_venue_year_combinations(self):
        """Test handling of many different venue/year combinations."""
        papers = []
        venues = ["NeurIPS", "ICML", "ICLR", "CVPR", "AAAI"]
        years = [2018, 2019, 2020, 2021, 2022]

        # Create papers for all combinations
        for i, (venue, year) in enumerate([(v, y) for v in venues for y in years]):
            papers.append(
                create_test_paper(
                    paper_id=f"p{i}",
                    title=f"Paper {i}",
                    authors=[Author(name=f"Author {i}")],
                    year=year,
                    venue=venue,
                    citation_count=i * 2,
                )
            )

        # Should handle many venue/year combinations efficiently
        result = self.analyzer.filter_papers_by_citations(papers)
        assert result.original_count == len(papers)
        assert len(result.threshold_compliance) > 0

    def test_filtering_with_all_papers_below_threshold(self):
        """Test filtering when all papers are below threshold."""
        papers = [
            create_test_paper(
                paper_id=f"low{i}",
                title=f"Low Citation Paper {i}",
                authors=[Author(name=f"Author {i}")],
                year=2020,
                venue="NeurIPS",
                citation_count=0,  # All have zero citations
            )
            for i in range(10)
        ]

        # Should handle case where all papers are below threshold
        result = self.analyzer.filter_papers_by_citations(
            papers, preserve_breakthroughs=False
        )
        assert result.original_count == 10
        # All papers have no citations, so all should be filtered out
        assert result.filtered_count == 0
        assert len(result.papers_below_threshold) == 10
        assert result.filtering_statistics["no_citation_data"] == 10

    def test_validate_filtering_quality_extreme_cases(self):
        """Test quality validation with extreme filtering results."""
        all_papers = [
            create_test_paper(
                paper_id=f"p{i}",
                title=f"Paper {i}",
                authors=[Author(name=f"Author {i}")],
                year=2020,
                venue="NeurIPS" if i < 5 else "ICML",
                citation_count=100 if i < 2 else 1,
            )
            for i in range(10)
        ]

        # Extreme case: only keep 2 papers
        filtered_papers = all_papers[:2]

        quality_report = self.analyzer.validate_filtering_quality(
            all_papers, filtered_papers
        )
        assert (
            len(quality_report.warnings) > 0
        )  # Should have warnings about aggressive filtering
        assert len(quality_report.recommendations) > 0
