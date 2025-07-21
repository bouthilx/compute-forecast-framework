"""Unit tests for BreakthroughDetector."""

import pytest
from datetime import datetime
from unittest.mock import patch, mock_open
import json

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector import (
    BreakthroughDetector,
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
    if citation_count > 0:
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


class TestBreakthroughDetector:
    """Test breakthrough detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.Path.exists",
            return_value=False,
        ):
            return BreakthroughDetector()

    @pytest.fixture
    def high_impact_paper(self):
        """Create a high-impact paper."""
        return create_test_paper(
            paper_id="high1",
            title="Transformer: A Novel Architecture for State-of-the-Art Performance",
            abstract_text="We introduce a groundbreaking new method that achieves unprecedented results.",
            venue="NeurIPS",
            year=2023,
            citation_count=150,
            authors=[Author(name="Geoffrey Hinton"), Author(name="Yann LeCun")],
        )

    @pytest.fixture
    def medium_impact_paper(self):
        """Create a medium-impact paper."""
        return create_test_paper(
            paper_id="med1",
            title="Improving Neural Networks with Better Optimization",
            abstract_text="We present an incremental improvement to existing methods.",
            venue="ICML",
            year=2022,
            citation_count=30,
            authors=[Author(name="John Doe"), Author(name="Jane Smith")],
        )

    @pytest.fixture
    def low_impact_paper(self):
        """Create a low-impact paper."""
        return create_test_paper(
            paper_id="low1",
            title="A Survey of Recent Methods",
            abstract_text="We survey existing approaches in the field.",
            venue="Workshop",
            year=2020,
            citation_count=5,
            authors=[Author(name="Unknown Author")],
        )

    def test_load_breakthrough_keywords_default(self, detector):
        """Test loading default breakthrough keywords."""
        keywords = detector.breakthrough_keywords

        assert "breakthrough" in keywords
        assert "novel" in keywords
        assert "transformer" in keywords
        assert "state-of-the-art" in keywords
        assert len(keywords) > 20  # Should have many keywords

    def test_load_breakthrough_keywords_from_file(self):
        """Test loading breakthrough keywords from file."""
        mock_keywords = {"keywords": ["test1", "test2", "test3"]}

        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.Path.exists",
            return_value=True,
        ):
            with patch("builtins.open", mock_open(read_data=json.dumps(mock_keywords))):
                detector = BreakthroughDetector()

        assert detector.breakthrough_keywords == {"test1", "test2", "test3"}

    def test_load_high_impact_authors_default(self, detector):
        """Test loading default high-impact authors."""
        authors = detector.high_impact_authors

        assert "Geoffrey Hinton" in authors
        assert "Yann LeCun" in authors
        assert "Yoshua Bengio" in authors
        assert len(authors) > 10  # Should have many authors

    def test_calculate_breakthrough_score_high_impact(
        self, detector, high_impact_paper
    ):
        """Test breakthrough score for high-impact paper."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            score = detector.calculate_breakthrough_score(high_impact_paper)

            # Should have high score due to:
            # - High citation velocity (150 citations in 1 year)
            # - Multiple breakthrough keywords
            # - High-impact authors
            # - Top-tier venue (NeurIPS)
            # - Very recent publication
            assert score > 0.8

    def test_calculate_breakthrough_score_medium_impact(
        self, detector, medium_impact_paper
    ):
        """Test breakthrough score for medium-impact paper."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            score = detector.calculate_breakthrough_score(medium_impact_paper)

            # Should have medium score
            assert 0.3 < score < 0.7

    def test_calculate_breakthrough_score_low_impact(self, detector, low_impact_paper):
        """Test breakthrough score for low-impact paper."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            score = detector.calculate_breakthrough_score(low_impact_paper)

            # Should have low score
            assert score < 0.3

    def test_calculate_breakthrough_score_no_citations(self, detector):
        """Test breakthrough score for paper with no citations."""
        paper = create_test_paper(
            paper_id="new1",
            title="A New Method",
            venue="ICML",
            year=2023,
            citation_count=0,
            authors=[Author(name="Test")],
        )

        score = detector.calculate_breakthrough_score(paper)

        # Should still get some score from venue and recency
        assert score > 0  # Not zero due to venue/recency
        assert score < 0.5  # But not high without citations

    def test_identify_breakthrough_indicators(self, detector, high_impact_paper):
        """Test identification of breakthrough indicators."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            indicators = detector.identify_breakthrough_indicators(high_impact_paper)

            # Should identify multiple indicators
            assert any("citation velocity" in ind.lower() for ind in indicators)
            assert any("breakthrough keywords" in ind.lower() for ind in indicators)
            assert any("high-impact authors" in ind.lower() for ind in indicators)
            assert any("top-tier venue" in ind.lower() for ind in indicators)
            assert any("recent publication" in ind.lower() for ind in indicators)

    def test_detect_breakthrough_papers(
        self, detector, high_impact_paper, medium_impact_paper, low_impact_paper
    ):
        """Test detecting breakthrough papers from a list."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            papers = [high_impact_paper, medium_impact_paper, low_impact_paper]
            breakthrough_papers = detector.detect_breakthrough_papers(papers)

            # Should detect high-impact paper as breakthrough
            assert len(breakthrough_papers) >= 1
            assert breakthrough_papers[0].paper.paper_id == "high1"
            assert breakthrough_papers[0].breakthrough_score > 0.5

            # Should be sorted by score (highest first)
            if len(breakthrough_papers) > 1:
                for i in range(len(breakthrough_papers) - 1):
                    assert (
                        breakthrough_papers[i].breakthrough_score
                        >= breakthrough_papers[i + 1].breakthrough_score
                    )

    def test_keyword_matching_case_insensitive(self, detector):
        """Test that keyword matching is case-insensitive."""
        paper = create_test_paper(
            paper_id="1",
            title="TRANSFORMER: A NOVEL APPROACH",  # Uppercase
            abstract_text="We present a BREAKTHROUGH method.",  # Mixed case
            venue="NeurIPS",
            year=2023,
            citation_count=50,
            authors=[Author(name="Test")],
        )

        score, keywords = detector._calculate_keyword_score(paper)

        assert score > 0
        # Keywords should be lowercase as they match the lowercase content
        assert any("transformer" in kw.lower() for kw in keywords)
        assert any("novel" in kw.lower() for kw in keywords)
        assert any("breakthrough" in kw.lower() for kw in keywords)

    def test_author_reputation_with_h_index(self, detector):
        """Test author reputation calculation with high-impact authors."""
        authors = [
            Author(name="Unknown Author"),
            Author(name="Geoffrey Hinton"),  # High-impact author
            Author(name="Yann LeCun"),  # High-impact author
        ]

        score, high_impact_authors = detector._calculate_author_reputation_score(
            authors
        )

        # Should get points for:
        # - Geoffrey Hinton: 0.3
        # - Yann LeCun: 0.3
        # Total: 0.6 (capped at 1.0)
        assert score == 0.6
        assert "Geoffrey Hinton" in high_impact_authors
        assert "Yann LeCun" in high_impact_authors

    def test_venue_prestige_score(self, detector):
        """Test venue prestige scoring."""
        assert detector._calculate_venue_prestige_score("NeurIPS") == 1.0
        assert detector._calculate_venue_prestige_score("ICML") == 1.0
        assert detector._calculate_venue_prestige_score("CVPR") == 0.8
        assert detector._calculate_venue_prestige_score("UAI") == 0.6
        assert detector._calculate_venue_prestige_score("Unknown") == 0.4

    def test_recency_bonus(self, detector):
        """Test recency bonus in breakthrough scoring."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            # Very recent paper (1 year old)
            recent_paper = create_test_paper(
                paper_id="1",
                title="Recent Paper",
                venue="ICML",
                year=2023,
                citation_count=20,
                authors=[Author(name="Test")],
            )

            # Older paper (5 years old)
            old_paper = create_test_paper(
                paper_id="2",
                title="Old Paper",
                venue="ICML",
                year=2019,
                citation_count=20,
                authors=[Author(name="Test")],
            )

            recent_score = detector.calculate_breakthrough_score(recent_paper)
            old_score = detector.calculate_breakthrough_score(old_paper)

            # Recent paper should have higher score due to recency bonus
            assert recent_score > old_score

    def test_empty_paper_list(self, detector):
        """Test detecting breakthrough papers with empty list."""
        breakthrough_papers = detector.detect_breakthrough_papers([])
        assert breakthrough_papers == []

    def test_paper_without_authors(self, detector):
        """Test handling paper without authors."""
        paper = create_test_paper(
            paper_id="1",
            title="Paper without authors",
            venue="NeurIPS",
            year=2023,
            citation_count=50,
            authors=[],
        )

        score = detector.calculate_breakthrough_score(paper)
        # Should still get score from other factors
        assert score > 0

    def test_breakthrough_paper_dataclass(self, detector, high_impact_paper):
        """Test BreakthroughPaper dataclass creation."""
        with patch(
            "compute_forecast.pipeline.metadata_collection.processors.breakthrough_detector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            detector.current_year = 2024

            breakthrough_papers = detector.detect_breakthrough_papers(
                [high_impact_paper]
            )

            assert len(breakthrough_papers) == 1
            bp = breakthrough_papers[0]

            assert bp.paper == high_impact_paper
            assert bp.breakthrough_score > 0
            assert len(bp.breakthrough_indicators) > 0
            assert bp.citation_velocity_score > 0
            assert bp.keyword_score > 0
            assert bp.author_reputation_score > 0
            assert bp.venue_prestige_score > 0
            assert bp.recency_bonus > 0
            assert len(bp.matched_keywords) > 0
            assert len(bp.high_impact_authors) > 0
            assert bp.citation_velocity == 150.0  # 150 citations in 1 year
