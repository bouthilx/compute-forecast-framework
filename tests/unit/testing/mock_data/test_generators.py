"""Tests for mock data generators."""

from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    Author,
    ComputationalAnalysis,
    AuthorshipAnalysis,
    VenueAnalysis,
)
from compute_forecast.testing.mock_data import (
    MockDataGenerator,
    MockDataConfig,
    DataQuality,
)


class TestMockDataGenerator:
    """Test MockDataGenerator functionality."""

    def test_generate_normal_quality_papers(self):
        """Test generation of normal quality papers."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)

        assert len(papers) == 10
        assert all(isinstance(p, Paper) for p in papers)

        # Check normal quality - 95% fields populated
        for paper in papers:
            assert paper.paper_id
            assert paper.title
            assert paper.authors
            assert paper.year
            assert paper.venue
            assert paper.abstract
            assert paper.citations >= 0
            assert 2019 <= paper.year <= 2024

    def test_generate_edge_case_papers(self):
        """Test generation of edge case papers."""
        config = MockDataConfig(quality=DataQuality.EDGE_CASE, size=5, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)

        assert len(papers) == 5
        # Edge cases should have ~70% fields populated
        missing_fields_count = 0
        empty_abstract_count = 0
        extreme_citation_velocity_count = 0

        for paper in papers:
            if not paper.abstract:
                missing_fields_count += 1
            elif paper.abstract == "":  # Check for empty abstracts
                empty_abstract_count += 1

            if not paper.keywords:
                missing_fields_count += 1
            if not paper.arxiv_id:
                missing_fields_count += 1

            # Check for extreme citation velocities
            if paper.citation_velocity is not None and (
                paper.citation_velocity == 0.0 or paper.citation_velocity > 50.0
            ):
                extreme_citation_velocity_count += 1

        assert missing_fields_count > 0  # Some fields should be missing
        # Edge cases should have unusual values
        assert empty_abstract_count > 0 or extreme_citation_velocity_count > 0

    def test_generate_corrupted_papers(self):
        """Test generation of corrupted papers."""
        config = MockDataConfig(quality=DataQuality.CORRUPTED, size=5, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)

        assert len(papers) == 5
        # Corrupted should have ~30% fields populated
        for paper in papers:
            # Essential fields should still exist
            assert paper.paper_id
            assert paper.title
            # But many optional fields should be missing
            missing_count = sum(
                [
                    paper.abstract is None,
                    paper.keywords is None or len(paper.keywords) == 0,
                    paper.arxiv_id is None,
                    paper.openalex_id is None,
                    paper.computational_analysis is None,
                ]
            )
            assert missing_count >= 3

        # Test validation of corrupted papers
        assert generator.validate_output(papers, config) is True

    def test_deterministic_generation(self):
        """Test that same seed produces same results."""
        config1 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=42)
        config2 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=42)

        generator = MockDataGenerator()
        papers1 = generator.generate(config1)
        papers2 = generator.generate(config2)

        assert len(papers1) == len(papers2)
        for p1, p2 in zip(papers1, papers2):
            assert p1.paper_id == p2.paper_id
            assert p1.title == p2.title

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        config1 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=42)
        config2 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=43)

        generator = MockDataGenerator()
        papers1 = generator.generate(config1)
        papers2 = generator.generate(config2)

        # At least some papers should be different
        different_count = sum(
            p1.paper_id != p2.paper_id for p1, p2 in zip(papers1, papers2)
        )
        assert different_count > 0

    def test_computational_analysis_generation(self):
        """Test generation of computational analysis data."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        papers_with_comp = [p for p in papers if p.computational_analysis]

        # At least 80% should have computational analysis for normal quality (95% probability)
        assert len(papers_with_comp) >= 8

        for paper in papers_with_comp:
            comp = paper.computational_analysis
            assert isinstance(comp, ComputationalAnalysis)
            assert comp.computational_richness >= 0.0
            assert comp.computational_richness <= 1.0
            assert comp.confidence_score >= 0.0
            assert comp.confidence_score <= 1.0
            assert isinstance(comp.keyword_matches, dict)
            assert isinstance(comp.resource_metrics, dict)
            assert isinstance(comp.experimental_indicators, dict)

            # Check resource metrics
            if comp.resource_metrics.get("gpu_hours") is not None:
                assert comp.resource_metrics["gpu_hours"] >= 0

    def test_author_generation(self):
        """Test realistic author generation."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)

        for paper in papers:
            assert len(paper.authors) >= 1
            assert all(isinstance(a, Author) for a in paper.authors)

            for author in paper.authors:
                assert author.name
                # Some authors should have affiliations
                if author.affiliation:
                    assert len(author.affiliation) > 0

    def test_venue_distribution(self):
        """Test realistic venue distribution."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        venues = [p.venue for p in papers]

        # Should have variety of venues
        unique_venues = set(venues)
        assert len(unique_venues) >= 10

        # Top venues should appear more frequently
        venue_counts = {}
        for venue in venues:
            venue_counts[venue] = venue_counts.get(venue, 0) + 1

        top_venue_count = max(venue_counts.values())
        assert top_venue_count >= 5  # Some concentration expected

    def test_temporal_distribution(self):
        """Test realistic temporal distribution."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        years = [p.year for p in papers]

        # Should cover the range 2019-2024
        assert min(years) >= 2019
        assert max(years) <= 2024

        # Recent years should have more papers
        recent_papers = sum(1 for y in years if y >= 2022)
        older_papers = sum(1 for y in years if y < 2022)
        assert recent_papers > older_papers

    def test_citation_distribution(self):
        """Test realistic citation distribution."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        citations = [p.citations for p in papers]

        # Most papers should have few citations
        low_citation_papers = sum(1 for c in citations if c < 10)
        assert low_citation_papers > 50

        # But some should have many
        high_citation_papers = sum(1 for c in citations if c > 100)
        assert high_citation_papers > 0

        # Older papers should generally have more citations
        for paper in papers:
            if paper.year <= 2020 and paper.citations < 5:
                # Older papers with very few citations should be rare
                assert paper.venue not in ["ICML", "NeurIPS", "CVPR"]

    def test_performance_large_dataset(self):
        """Test performance with large dataset generation."""
        import time

        config = MockDataConfig(quality=DataQuality.NORMAL, size=5000, seed=42)
        generator = MockDataGenerator()

        start_time = time.time()
        papers = generator.generate(config)
        end_time = time.time()

        assert len(papers) == 5000
        assert end_time - start_time < 30  # Should complete in under 30 seconds

    def test_validate_output(self):
        """Test output validation functionality."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)

        # Should validate successfully
        assert generator.validate_output(papers, config) is True

        # Should fail with wrong size
        assert generator.validate_output(papers[:5], config) is False

        # Should fail with wrong quality (too many missing fields)
        # Create a paper with many missing fields
        corrupted_paper = Paper(
            paper_id="test",
            title="Test",
            authors=[],
            year=2023,
            venue="Test",
            citations=0,
            abstract=None,
            keywords=None,
            arxiv_id=None,
            openalex_id=None,
            computational_analysis=None,
            citation_velocity=None,
            normalized_venue="test",
            collection_source="mock_generator",
            collection_timestamp=papers[0].collection_timestamp,
        )
        # Replace multiple papers to ensure validation fails
        papers_with_corrupted = papers[:5] + [corrupted_paper] * 5
        assert generator.validate_output(papers_with_corrupted, config) is False

        # Test validation with EDGE_CASE quality
        edge_config = MockDataConfig(quality=DataQuality.EDGE_CASE, size=10, seed=42)
        assert (
            generator.validate_output(papers, edge_config) is True
        )  # Normal papers pass edge validation

        # Test validation with CORRUPTED quality - normal papers should fail
        corrupted_config = MockDataConfig(
            quality=DataQuality.CORRUPTED, size=10, seed=42
        )
        assert (
            generator.validate_output(papers, corrupted_config) is False
        )  # Too many fields populated

    def test_authorship_analysis_generation(self):
        """Test generation of authorship analysis."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        papers_with_auth = [p for p in papers if p.authorship_analysis]

        # Should have authorship analysis for many papers
        assert len(papers_with_auth) >= 5

        for paper in papers_with_auth:
            auth = paper.authorship_analysis
            assert isinstance(auth, AuthorshipAnalysis)
            assert auth.category in [
                "academic_eligible",
                "industry_eligible",
                "needs_manual_review",
            ]
            assert auth.academic_count >= 0
            assert auth.industry_count >= 0
            assert auth.unknown_count >= 0
            assert auth.confidence >= 0.0 and auth.confidence <= 1.0
            assert len(auth.author_details) == len(paper.authors)

            # Check consistency
            total_count = auth.academic_count + auth.industry_count + auth.unknown_count
            assert total_count == len(paper.authors)

    def test_venue_analysis_generation(self):
        """Test generation of venue analysis."""
        config = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=42)
        generator = MockDataGenerator()

        papers = generator.generate(config)
        papers_with_venue = [p for p in papers if p.venue_analysis]

        # Should have venue analysis for many papers
        assert len(papers_with_venue) >= 5

        for paper in papers_with_venue:
            venue = paper.venue_analysis
            assert isinstance(venue, VenueAnalysis)
            assert venue.venue_score >= 0.0 and venue.venue_score <= 1.0
            assert venue.domain_relevance >= 0.0 and venue.domain_relevance <= 1.0
            assert venue.computational_focus >= 0.0 and venue.computational_focus <= 1.0
            assert venue.importance_ranking >= 1

            # Check consistency with venue name
            if paper.venue in ["NeurIPS", "ICML", "ICLR", "CVPR"]:
                assert venue.venue_score >= 0.85
                assert venue.importance_ranking <= 10
