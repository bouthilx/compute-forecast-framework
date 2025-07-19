"""Unit tests for fuzzy title matching in consolidation."""

import pytest
from compute_forecast.pipeline.consolidation.sources.title_matcher import TitleMatcher


class TestTitleMatcher:
    """Test the TitleMatcher class."""
    
    def test_exact_match(self):
        """Test exact title matches."""
        matcher = TitleMatcher()
        
        score, match_type = matcher.calculate_similarity(
            "Deep Learning for Computer Vision",
            "Deep Learning for Computer Vision"
        )
        assert score == 1.0
        assert match_type == "exact"
        
    def test_exact_match_with_normalization(self):
        """Test exact match after normalization."""
        matcher = TitleMatcher()
        
        # Different case
        score, match_type = matcher.calculate_similarity(
            "DEEP LEARNING for Computer Vision",
            "deep learning for computer vision"
        )
        assert score == 1.0
        assert match_type == "exact"
        
        # Extra spaces
        score, match_type = matcher.calculate_similarity(
            "Deep  Learning   for Computer Vision",
            "Deep Learning for Computer Vision"
        )
        assert score == 1.0
        assert match_type == "exact"
        
    def test_arxiv_conference_variations(self):
        """Test common ArXiv to conference paper title variations."""
        matcher = TitleMatcher()
        
        # Subtitle variation
        score, match_type = matcher.calculate_similarity(
            "Attention Is All You Need: A Transformer Architecture",
            "Attention Is All You Need"
        )
        assert score >= 0.95
        assert match_type == "high_confidence"
        
        # Extended abstract suffix
        score, match_type = matcher.calculate_similarity(
            "Neural Networks for NLP (Extended Abstract)",
            "Neural Networks for NLP"
        )
        assert score >= 0.95
        assert match_type in ["exact", "high_confidence"]
        
        # ArXiv bracketed content
        score, match_type = matcher.calculate_similarity(
            "Vision Transformers at Scale [v2]",
            "Vision Transformers at Scale"
        )
        assert score >= 0.95
        assert match_type in ["exact", "high_confidence"]
        
    def test_punctuation_variations(self):
        """Test handling of punctuation differences."""
        matcher = TitleMatcher()
        
        # Colon vs dash
        score, match_type = matcher.calculate_similarity(
            "BERT: Pre-training of Deep Bidirectional Transformers",
            "BERT - Pre-training of Deep Bidirectional Transformers"
        )
        assert score >= 0.95
        assert match_type in ["exact", "high_confidence"]
        
        # Different quote styles
        score, match_type = matcher.calculate_similarity(
            'Learning to "Read" Images',
            "Learning to 'Read' Images"
        )
        assert score >= 0.90
        assert match_type in ["exact", "high_confidence"]  # Could be exact after normalization
        
    def test_fuzzy_matches(self):
        """Test fuzzy matching with minor differences."""
        matcher = TitleMatcher()
        
        # Minor word difference
        score, match_type = matcher.calculate_similarity(
            "A Method for Deep Learning",
            "Method for Deep Learning"
        )
        assert score >= 0.85
        assert match_type in ["high_confidence", "medium_confidence"]
        
        # Word order variation (less common but happens)
        score, match_type = matcher.calculate_similarity(
            "Deep Learning: A Comprehensive Survey",
            "A Comprehensive Survey: Deep Learning"
        )
        assert score >= 0.80
        assert match_type in ["medium_confidence", "high_confidence"]
        
    def test_year_safety_check(self):
        """Test year-based safety checks."""
        matcher = TitleMatcher(require_safety_checks=True)
        
        # Same title, same year
        score1, match_type1 = matcher.calculate_similarity(
            "Neural Networks",
            "Neural Networks",
            year1=2023,
            year2=2023
        )
        
        # Same title, different years (should reduce confidence)
        score2, match_type2 = matcher.calculate_similarity(
            "Neural Networks",
            "Neural Networks",
            year1=2023,
            year2=2020
        )
        
        assert score1 > score2
        assert match_type1 == "exact"
        assert match_type2 != "exact"  # Should be downgraded
        
    def test_author_safety_check(self):
        """Test author-based safety checks."""
        matcher = TitleMatcher(require_safety_checks=True)
        
        # High similarity title, with authors
        score1, match_type1 = matcher.calculate_similarity(
            "Transformers for Vision",
            "Transformers for Vision Tasks",
            authors1=["John Doe", "Jane Smith"],
            authors2=["Jane Smith", "Bob Wilson"]
        )
        
        # Same titles, no author overlap
        score2, match_type2 = matcher.calculate_similarity(
            "Transformers for Vision",
            "Transformers for Vision Tasks",
            authors1=["John Doe", "Jane Smith"],
            authors2=["Alice Cooper", "Bob Wilson"]
        )
        
        assert score1 > score2
        
    def test_is_similar_convenience_method(self):
        """Test the is_similar convenience method."""
        matcher = TitleMatcher()
        
        # High confidence match
        assert matcher.is_similar(
            "Deep Learning",
            "Deep Learning",
            min_confidence="high_confidence"
        )
        
        # Medium confidence match
        assert matcher.is_similar(
            "Deep Learning for NLP",
            "Deep Learning in NLP",
            min_confidence="medium_confidence"
        )
        
        # Should fail with high confidence requirement
        assert not matcher.is_similar(
            "Deep Learning for NLP",
            "Machine Learning for NLP",
            min_confidence="high_confidence"
        )
        
    def test_empty_titles(self):
        """Test handling of empty or None titles."""
        matcher = TitleMatcher()
        
        score, match_type = matcher.calculate_similarity("", "Deep Learning")
        assert score == 0.0
        assert match_type == "no_match"
        
        score, match_type = matcher.calculate_similarity(None, "Deep Learning")
        assert score == 0.0
        assert match_type == "no_match"
        
    def test_substring_containment(self):
        """Test substring containment (common in ArXiv variations)."""
        matcher = TitleMatcher()
        
        # Conference paper contains ArXiv title
        score, match_type = matcher.calculate_similarity(
            "ViT: Vision Transformer",
            "ViT: Vision Transformer - An Image is Worth 16x16 Words"
        )
        assert score >= 0.95
        assert match_type == "high_confidence"
        
        # ArXiv title contains conference title
        score, match_type = matcher.calculate_similarity(
            "CLIP: Contrastive Language-Image Pre-training",
            "CLIP"
        )
        assert score >= 0.95
        assert match_type == "high_confidence"