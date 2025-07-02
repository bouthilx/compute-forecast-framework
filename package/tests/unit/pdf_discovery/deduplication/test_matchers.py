"""Unit tests for PDF deduplication matchers."""

import pytest
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch

from src.pdf_discovery.deduplication.matchers import (
    IdentifierNormalizer,
    PaperFuzzyMatcher,
    ExactMatch,
    FuzzyMatch,
)
from src.data.models import Paper, Author
from src.pdf_discovery.core.models import PDFRecord


class TestIdentifierNormalizer:
    """Test identifier normalization functionality."""
    
    def test_normalize_doi_valid(self):
        """Test DOI normalization for valid DOIs."""
        normalizer = IdentifierNormalizer()
        
        # Test various DOI formats
        assert normalizer.normalize_doi("10.1234/example.doi") == "10.1234/example.doi"
        assert normalizer.normalize_doi("https://doi.org/10.1234/example.doi") == "10.1234/example.doi"
        assert normalizer.normalize_doi("http://dx.doi.org/10.1234/example.doi") == "10.1234/example.doi"
        assert normalizer.normalize_doi("DOI: 10.1234/example.doi") == "10.1234/example.doi"
        assert normalizer.normalize_doi("doi:10.1234/example.doi") == "10.1234/example.doi"
        
    def test_normalize_doi_invalid(self):
        """Test DOI normalization for invalid inputs."""
        normalizer = IdentifierNormalizer()
        
        assert normalizer.normalize_doi("") is None
        assert normalizer.normalize_doi("not a doi") is None
        assert normalizer.normalize_doi("10.1234") is None  # Too short
        assert normalizer.normalize_doi("1234/example") is None  # Missing prefix
        
    def test_normalize_arxiv_id_valid(self):
        """Test arXiv ID normalization for valid IDs."""
        normalizer = IdentifierNormalizer()
        
        # New format (YYMM.NNNNN)
        assert normalizer.normalize_arxiv_id("2301.12345") == "2301.12345"
        assert normalizer.normalize_arxiv_id("arXiv:2301.12345") == "2301.12345"
        assert normalizer.normalize_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"
        assert normalizer.normalize_arxiv_id("http://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"
        
        # Old format (category/YYMMNNN)
        assert normalizer.normalize_arxiv_id("cs.LG/0701001") == "cs.LG/0701001"
        assert normalizer.normalize_arxiv_id("arXiv:cs.LG/0701001") == "cs.LG/0701001"
        assert normalizer.normalize_arxiv_id("https://arxiv.org/abs/cs.LG/0701001") == "cs.LG/0701001"
        
        # With version
        assert normalizer.normalize_arxiv_id("2301.12345v2") == "2301.12345"
        assert normalizer.normalize_arxiv_id("cs.LG/0701001v3") == "cs.LG/0701001"
        
    def test_normalize_arxiv_id_invalid(self):
        """Test arXiv ID normalization for invalid inputs."""
        normalizer = IdentifierNormalizer()
        
        assert normalizer.normalize_arxiv_id("") is None
        assert normalizer.normalize_arxiv_id("not an arxiv id") is None
        assert normalizer.normalize_arxiv_id("12345") is None
        assert normalizer.normalize_arxiv_id("2301.123") is None  # Too short
        
    def test_extract_identifiers_from_url(self):
        """Test extracting identifiers from URLs."""
        normalizer = IdentifierNormalizer()
        
        # DOI URLs
        result = normalizer.extract_identifiers_from_url("https://doi.org/10.1234/example.doi")
        assert result["doi"] == "10.1234/example.doi"
        
        # arXiv URLs
        result = normalizer.extract_identifiers_from_url("https://arxiv.org/abs/2301.12345")
        assert result["arxiv_id"] == "2301.12345"
        
        result = normalizer.extract_identifiers_from_url("https://arxiv.org/pdf/2301.12345v2.pdf")
        assert result["arxiv_id"] == "2301.12345"
        
        # Non-identifier URLs
        result = normalizer.extract_identifiers_from_url("https://example.com/paper.pdf")
        assert result == {}


class TestPaperFuzzyMatcher:
    """Test fuzzy matching for papers."""
    
    @pytest.fixture
    def sample_papers(self) -> List[Paper]:
        """Create sample papers for testing."""
        return [
            Paper(
                title="Deep Learning for Natural Language Processing",
                authors=[
                    Author(name="John Doe", affiliation="MIT"),
                    Author(name="Jane Smith", affiliation="Stanford"),
                ],
                venue="NeurIPS",
                year=2023,
                citations=100,
                paper_id="paper1",
                doi="10.1234/nlp.2023",
            ),
            Paper(
                title="Deep Learning for Natural Language Processing",
                authors=[
                    Author(name="J. Doe", affiliation="MIT"),
                    Author(name="J. Smith", affiliation="Stanford University"),
                ],
                venue="NeurIPS 2023",
                year=2023,
                citations=100,
                paper_id="paper2",
                arxiv_id="2301.12345",
            ),
            Paper(
                title="A Novel Approach to Computer Vision",
                authors=[
                    Author(name="Alice Johnson", affiliation="CMU"),
                ],
                venue="CVPR",
                year=2023,
                citations=50,
                paper_id="paper3",
            ),
        ]
    
    def test_normalize_title(self):
        """Test title normalization."""
        matcher = PaperFuzzyMatcher()
        
        # Basic normalization
        assert matcher.normalize_title("Deep Learning for NLP") == "deep learning for nlp"
        assert matcher.normalize_title("  Deep  Learning  ") == "deep learning"
        
        # Remove common suffixes
        assert matcher.normalize_title("Deep Learning (Extended Abstract)") == "deep learning"
        assert matcher.normalize_title("Deep Learning - Supplementary Material") == "deep learning"
        
    def test_calculate_title_similarity(self):
        """Test title similarity calculation."""
        matcher = PaperFuzzyMatcher()
        
        # Exact match
        score = matcher.calculate_title_similarity(
            "Deep Learning for Natural Language Processing",
            "Deep Learning for Natural Language Processing"
        )
        assert score == 1.0
        
        # High similarity
        score = matcher.calculate_title_similarity(
            "Deep Learning for Natural Language Processing",
            "Deep Learning for Natural Language Processing (Extended Abstract)"
        )
        assert score > 0.95
        
        # Low similarity
        score = matcher.calculate_title_similarity(
            "Deep Learning for Natural Language Processing",
            "A Novel Approach to Computer Vision"
        )
        assert score < 0.5
        
    def test_calculate_author_similarity(self):
        """Test author similarity calculation."""
        matcher = PaperFuzzyMatcher()
        
        authors1 = [
            Author(name="John Doe", affiliation="MIT"),
            Author(name="Jane Smith", affiliation="Stanford"),
        ]
        
        authors2 = [
            Author(name="J. Doe", affiliation="MIT"),
            Author(name="J. Smith", affiliation="Stanford University"),
        ]
        
        authors3 = [
            Author(name="Alice Johnson", affiliation="CMU"),
            Author(name="Bob Wilson", affiliation="MIT"),
        ]
        
        # High similarity (same authors, different formatting)
        score = matcher.calculate_author_similarity(authors1, authors2)
        assert score > 0.85
        
        # Low similarity (different authors)
        score = matcher.calculate_author_similarity(authors1, authors3)
        assert score < 0.3
        
    def test_find_duplicates_exact(self, sample_papers):
        """Test exact duplicate detection."""
        matcher = PaperFuzzyMatcher()
        
        # Create records with duplicate from different sources
        records = []
        
        # First two papers from different sources but same DOI
        for i, source in enumerate(["arxiv", "semantic_scholar"]):
            record = PDFRecord(
                paper_id=f"paper1_{source}",
                pdf_url=f"https://{source}.com/paper1.pdf",
                source=source,
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
            )
            # Use first paper but with record's paper_id
            paper_copy = Paper(
                title=sample_papers[0].title,
                authors=sample_papers[0].authors,
                venue=sample_papers[0].venue,
                year=sample_papers[0].year,
                citations=sample_papers[0].citations,
                paper_id=record.paper_id,
                doi=sample_papers[0].doi,  # Same DOI
            )
            record.paper_data = paper_copy
            records.append(record)
        
        # Add third paper (different)
        record = PDFRecord(
            paper_id="paper3",
            pdf_url="https://example.com/paper3.pdf",
            source="test",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="valid",
        )
        record.paper_data = sample_papers[2]
        records.append(record)
        
        matches = matcher.find_duplicates_exact(records)
        
        # Should find the two records with same DOI as duplicates
        assert len(matches) >= 1
        assert any(m.match_field == "doi" for m in matches)
        
    def test_find_duplicates_fuzzy(self, sample_papers):
        """Test fuzzy duplicate detection."""
        matcher = PaperFuzzyMatcher()
        
        records = [
            PDFRecord(
                paper_id=paper.paper_id,
                pdf_url=f"https://example.com/{paper.paper_id}.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
            )
            for paper in sample_papers
        ]
        
        # Add paper data to records for matching
        for record, paper in zip(records, sample_papers):
            record.paper_data = paper
        
        matches = matcher.find_duplicates_fuzzy(records)
        
        # Should find fuzzy matches between papers 1 and 2
        assert len(matches) > 0
        assert any(match.confidence > 0.9 for match in matches)


class TestExactMatch:
    """Test exact match functionality."""
    
    def test_exact_match_creation(self):
        """Test creating exact match objects."""
        match = ExactMatch(
            record_ids=["paper1", "paper2"],
            match_field="doi",
            match_value="10.1234/example",
        )
        
        assert match.record_ids == ["paper1", "paper2"]
        assert match.match_field == "doi"
        assert match.match_value == "10.1234/example"
        assert match.confidence == 1.0


class TestFuzzyMatch:
    """Test fuzzy match functionality."""
    
    def test_fuzzy_match_creation(self):
        """Test creating fuzzy match objects."""
        match = FuzzyMatch(
            record_ids=["paper1", "paper2"],
            title_similarity=0.98,
            author_similarity=0.87,
            venue_year_match=True,
        )
        
        assert match.record_ids == ["paper1", "paper2"]
        assert match.title_similarity == 0.98
        assert match.author_similarity == 0.87
        assert match.venue_year_match is True
        assert match.confidence > 0.9  # Combined confidence


class TestVenueNormalizationIntegration:
    """Test venue normalization integration with PDF deduplication."""
    
    def test_venue_normalizer_integration(self):
        """Test that PaperFuzzyMatcher integrates with VenueNormalizer."""
        matcher = PaperFuzzyMatcher()
        
        # Should have venue_normalizer attribute
        assert hasattr(matcher, 'venue_normalizer')
        assert matcher.venue_normalizer is not None
    
    @patch('src.pdf_discovery.deduplication.matchers.VenueNormalizer')
    def test_calculate_venue_year_match_with_normalization(self, mock_venue_normalizer_class):
        """Test venue matching uses venue normalization."""
        # Setup mock
        mock_normalizer = Mock()
        mock_venue_normalizer_class.return_value = mock_normalizer
        
        # Mock normalization results for different venue formats
        from src.data.processors.venue_normalizer import VenueNormalizationResult
        nips_result = VenueNormalizationResult(
            original_venue="NIPS 2023",
            normalized_venue="NeurIPS",
            confidence=1.0,
            mapping_type="exact",
            alternatives=[]
        )
        neurips_result = VenueNormalizationResult(
            original_venue="NeurIPS 2023",
            normalized_venue="NeurIPS", 
            confidence=1.0,
            mapping_type="exact",
            alternatives=[]
        )
        
        mock_normalizer.normalize_venue.side_effect = [nips_result, neurips_result]
        
        # Create matcher
        matcher = PaperFuzzyMatcher()
        
        # Create test papers with different venue formats
        paper1 = Paper(
            title="Test Paper",
            authors=[],
            venue="NIPS 2023",
            year=2023,
            citations=0,
            abstract="",
            doi="",
            paper_id="1"
        )
        paper2 = Paper(
            title="Test Paper",
            authors=[],
            venue="NeurIPS 2023",
            year=2023,
            citations=0,
            abstract="",
            doi="",
            paper_id="2"
        )
        
        # Test venue matching
        result = matcher.calculate_venue_year_match(paper1, paper2)
        
        # Should match because both normalize to "NeurIPS"
        assert result is True
        
        # Verify venue normalizer was called
        assert mock_normalizer.normalize_venue.call_count == 2
        mock_normalizer.normalize_venue.assert_any_call("NIPS 2023")
        mock_normalizer.normalize_venue.assert_any_call("NeurIPS 2023")
    
    @patch('src.pdf_discovery.deduplication.matchers.VenueNormalizer')
    def test_venue_confidence_threshold(self, mock_venue_normalizer_class):
        """Test venue matching respects confidence thresholds."""
        # Setup mock
        mock_normalizer = Mock()
        mock_venue_normalizer_class.return_value = mock_normalizer
        
        from src.data.processors.venue_normalizer import VenueNormalizationResult
        low_confidence_result = VenueNormalizationResult(
            original_venue="Unknown Conf 2023",
            normalized_venue="ICML",
            confidence=0.7,  # Below 0.8 threshold
            mapping_type="fuzzy",
            alternatives=[]
        )
        high_confidence_result = VenueNormalizationResult(
            original_venue="ICML 2023",
            normalized_venue="ICML",
            confidence=1.0,
            mapping_type="exact", 
            alternatives=[]
        )
        
        mock_normalizer.normalize_venue.side_effect = [low_confidence_result, high_confidence_result]
        
        matcher = PaperFuzzyMatcher()
        
        paper1 = Paper(
            title="Test Paper",
            authors=[],
            venue="Unknown Conf 2023",
            year=2023,
            citations=0,
            abstract="",
            doi="",
            paper_id="1"
        )
        paper2 = Paper(
            title="Test Paper", 
            authors=[],
            venue="ICML 2023",
            year=2023,
            citations=0,
            abstract="",
            doi="",
            paper_id="2"
        )
        
        # Should not match due to low confidence
        result = matcher.calculate_venue_year_match(paper1, paper2)
        assert result is False
    
    @patch('src.pdf_discovery.deduplication.matchers.VenueNormalizer')
    def test_venue_match_different_years(self, mock_venue_normalizer_class):
        """Test venue matching fails for different years."""
        # Setup mock
        mock_normalizer = Mock()
        mock_venue_normalizer_class.return_value = mock_normalizer
        
        matcher = PaperFuzzyMatcher()
        
        paper1 = Paper(
            title="Test Paper",
            authors=[],
            venue="ICML 2023",
            year=2023,
            citations=0,
            abstract="",
            doi="",
            paper_id="1"
        )
        paper2 = Paper(
            title="Test Paper",
            authors=[],
            venue="ICML 2024", 
            year=2024,
            citations=0,
            abstract="",
            doi="",
            paper_id="2"
        )
        
        # Should not match due to different years
        result = matcher.calculate_venue_year_match(paper1, paper2)
        assert result is False
        
        # Venue normalizer should not be called if years differ
        mock_normalizer.normalize_venue.assert_not_called()
    
    def test_fuzzy_match_confidence_boost_with_venue(self):
        """Test that venue matching provides confidence boost in FuzzyMatch."""
        match_with_venue = FuzzyMatch(
            record_ids=["paper1", "paper2"],
            title_similarity=0.90,
            author_similarity=0.85,
            venue_year_match=True,
        )
        
        match_without_venue = FuzzyMatch(
            record_ids=["paper1", "paper2"], 
            title_similarity=0.90,
            author_similarity=0.85,
            venue_year_match=False,
        )
        
        # Venue match should provide confidence boost
        assert match_with_venue.confidence > match_without_venue.confidence
        assert match_with_venue.confidence > 0.9  # Should get 1.15x boost