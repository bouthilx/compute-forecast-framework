"""
Unit tests for deduplication system.
Tests DeduplicationEngine, TitleNormalizer, AuthorMatcher, and SimilarityIndex.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.data.processors import (
    DeduplicationEngine,
    DeduplicationResult,
    TitleNormalizer,
    AuthorMatcher,
    SimilarityIndex,
    SimilarityScore
)
from src.data.models import Paper, Author


class TestTitleNormalizer:
    """Test title normalization functionality"""
    
    def setup_method(self):
        self.normalizer = TitleNormalizer()
    
    def test_normalize_title_basic(self):
        """Test basic title normalization"""
        # Test basic normalization
        assert self.normalizer.normalize_title("Deep Learning for Computer Vision") == "deep learning computer vision"
        assert self.normalizer.normalize_title("A Study of Machine Learning") == "study machine learning"
        
        # Test punctuation removal
        assert self.normalizer.normalize_title("Title: With Punctuation!") == "title punctuation"
        assert self.normalizer.normalize_title("Paper (2024)") == "paper"
        
        # Test abbreviation expansion
        normalized = self.normalizer.normalize_title("AI for ML Applications")
        assert "artificial intelligence" in normalized
        assert "machine learning" in normalized
    
    def test_normalize_title_edge_cases(self):
        """Test edge cases in title normalization"""
        # Empty title
        assert self.normalizer.normalize_title("") == ""
        assert self.normalizer.normalize_title(None) == ""
        
        # Very short title
        assert self.normalizer.normalize_title("AI") == "artificial intelligence"
        
        # Title with numbers and Roman numerals
        result = self.normalizer.normalize_title("Paper III: Version 2.0")
        assert "3" in result or "iii" in result
    
    def test_calculate_title_similarity(self):
        """Test title similarity calculation"""
        # Exact match
        similarity = self.normalizer.calculate_title_similarity("Same Title", "Same Title")
        assert similarity == 1.0
        
        # High similarity
        similarity = self.normalizer.calculate_title_similarity(
            "Deep Learning for Computer Vision",
            "Deep Learning in Computer Vision"
        )
        assert similarity > 0.8
        
        # Low similarity
        similarity = self.normalizer.calculate_title_similarity(
            "Deep Learning for Computer Vision",
            "Natural Language Processing with Transformers"
        )
        assert similarity < 0.5
        
        # Empty titles
        similarity = self.normalizer.calculate_title_similarity("", "")
        assert similarity == 0.0
    
    def test_title_variants(self):
        """Test detection of title variants"""
        # Common variations
        assert self.normalizer.is_title_variant(
            "Learning to Learn",
            "Learning to Learn: A Survey",
            threshold=0.8
        )
        
        # Different titles
        assert not self.normalizer.is_title_variant(
            "Deep Learning",
            "Reinforcement Learning",
            threshold=0.9
        )
    
    def test_performance(self):
        """Test performance requirements"""
        import time
        
        title1 = "A Comprehensive Survey of Deep Learning Techniques for Computer Vision Applications"
        title2 = "Deep Learning Methods for Computer Vision: A Comprehensive Review"
        
        start_time = time.time()
        for _ in range(100):  # 100 comparisons
            self.normalizer.calculate_title_similarity(title1, title2)
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / 100) * 1000
        
        # Should complete within 5ms per comparison
        assert avg_time_ms < 5.0


class TestAuthorMatcher:
    """Test author matching functionality"""
    
    def setup_method(self):
        self.matcher = AuthorMatcher()
    
    def test_normalize_author_name(self):
        """Test author name normalization"""
        # Basic normalization
        assert "smith, john" in self.matcher.normalize_author_name("John Smith")
        assert "smith, j" in self.matcher.normalize_author_name("J. Smith")
        
        # Handle titles and suffixes
        assert "dr" not in self.matcher.normalize_author_name("Dr. John Smith")
        assert "phd" not in self.matcher.normalize_author_name("John Smith PhD")
        
        # Handle unicode
        normalized = self.matcher.normalize_author_name("José García")
        assert "jose garcia" in normalized
    
    def test_calculate_author_similarity(self):
        """Test author similarity calculation"""
        authors1 = [
            Author("John Smith", "University A"),
            Author("Jane Doe", "University B")
        ]
        authors2 = [
            Author("J. Smith", "University A"),
            Author("Jane Doe", "University B")
        ]
        
        # High similarity (initials vs full name)
        similarity = self.matcher.calculate_author_similarity(authors1, authors2)
        assert similarity > 0.8
        
        # Low similarity (different authors)
        authors3 = [
            Author("Bob Johnson", "University C"),
            Author("Alice Brown", "University D")
        ]
        similarity = self.matcher.calculate_author_similarity(authors1, authors3)
        assert similarity < 0.3
        
        # Empty author lists
        similarity = self.matcher.calculate_author_similarity([], [])
        assert similarity == 0.0
    
    def test_initial_matching(self):
        """Test matching of initials vs full names"""
        # J. Smith should match John Smith
        result = self.matcher._check_initial_match("smith, j", "smith, john")
        assert result > 0.8
        
        # Different last names shouldn't match
        result = self.matcher._check_initial_match("smith, j", "jones, john")
        assert result == 0.0
    
    def test_affiliation_similarity(self):
        """Test affiliation similarity calculation"""
        # Similar affiliations
        similarity = self.matcher._calculate_affiliation_similarity(
            "University of California",
            "University of California, Berkeley"
        )
        assert similarity > 0.7
        
        # Different affiliations
        similarity = self.matcher._calculate_affiliation_similarity(
            "Stanford University",
            "Massachusetts Institute of Technology"
        )
        assert similarity < 0.5
    
    def test_author_signature(self):
        """Test author signature generation"""
        author = Author("John Smith", "University A")
        signature = self.matcher.get_author_signature(author)
        
        # Should contain elements of the name
        assert len(signature) > 0
        assert signature.isalnum()  # Should be alphanumeric only


class TestSimilarityIndex:
    """Test similarity index functionality"""
    
    def setup_method(self):
        self.index = SimilarityIndex()
        self.title_normalizer = TitleNormalizer()
        self.author_matcher = AuthorMatcher()
        
        # Create test papers
        self.test_papers = [
            Paper(
                title="Deep Learning for Computer Vision",
                authors=[Author("John Smith", "University A")],
                venue="CVPR",
                year=2024,
                citations=50
            ),
            Paper(
                title="Deep Learning in Computer Vision",
                authors=[Author("J. Smith", "University A")],
                venue="CVPR",
                year=2024,
                citations=52
            ),
            Paper(
                title="Natural Language Processing with Transformers",
                authors=[Author("Jane Doe", "University B")],
                venue="ACL",
                year=2023,
                citations=30
            ),
            Paper(
                title="Reinforcement Learning for Robotics",
                authors=[Author("Bob Johnson", "University C")],
                venue="ICRA",
                year=2024,
                citations=25
            )
        ]
    
    def test_build_index(self):
        """Test building similarity index"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        # Check that index was built
        assert self.index.stats.total_papers == 4
        assert self.index.stats.total_tokens > 0
        assert self.index.stats.build_time_seconds > 0
        
        # Check that tokens were indexed
        assert len(self.index.token_index) > 0
        assert len(self.index.paper_tokens) == 4
    
    def test_find_similar_papers(self):
        """Test finding similar papers using index"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        # Find papers similar to first paper (should find the very similar second paper)
        similar = self.index.find_similar_papers(0, min_token_overlap=2)
        
        # Should find at least one similar paper
        assert len(similar) > 0
        # Second paper should be similar due to title overlap
        assert 1 in similar
    
    def test_venue_filtering(self):
        """Test venue-based filtering"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        # Find candidates from same venue
        candidates = self.index.find_candidates_by_venue(0)  # CVPR paper
        
        # Should include other CVPR papers
        assert 1 in candidates  # Second paper is also CVPR
        assert 2 not in candidates  # ACL paper should not be included
    
    def test_year_filtering(self):
        """Test year-based filtering"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        # Find candidates from similar years
        candidates = self.index.find_candidates_by_year(0, year_window=1)  # 2024 paper
        
        # Should include other 2024 papers but not 2023
        assert 1 in candidates  # 2024 paper
        assert 3 in candidates  # 2024 paper
        assert 2 not in candidates  # 2023 paper
    
    def test_token_overlap_score(self):
        """Test token overlap scoring"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        # Calculate overlap between similar papers
        score = self.index.get_token_overlap_score(0, 1)
        assert score > 0.5  # Should have significant overlap
        
        # Calculate overlap between different papers
        score = self.index.get_token_overlap_score(0, 2)
        assert score < 0.3  # Should have low overlap
    
    def test_index_optimization(self):
        """Test index optimization"""
        self.index.build_index(self.test_papers, self.title_normalizer, self.author_matcher)
        
        original_size = len(self.index.token_index)
        self.index.optimize_index()
        
        # Should remove some rare tokens
        assert len(self.index.token_index) <= original_size


class TestDeduplicationEngine:
    """Test main deduplication engine functionality"""
    
    def setup_method(self):
        self.engine = DeduplicationEngine()
        
        # Create test papers with duplicates
        self.test_papers = [
            # Exact duplicate by ID
            Paper(
                title="Test Paper 1",
                authors=[Author("John Smith", "University A")],
                venue="CVPR",
                year=2024,
                citations=10,
                paper_id="paper_001"
            ),
            Paper(
                title="Test Paper 1 (Different Title)",
                authors=[Author("J. Smith", "University A")],
                venue="CVPR 2024",
                year=2024,
                citations=12,
                paper_id="paper_001"  # Same ID
            ),
            # Title + venue duplicate
            Paper(
                title="Deep Learning for Computer Vision",
                authors=[Author("Jane Doe", "University B")],
                venue="ICCV",
                year=2023,
                citations=50
            ),
            Paper(
                title="Deep Learning for Computer Vision",
                authors=[Author("Jane D.", "University B")],
                venue="ICCV",
                year=2023,
                citations=52
            ),
            # Fuzzy duplicate
            Paper(
                title="Machine Learning Applications in Healthcare",
                authors=[Author("Bob Johnson", "Hospital A")],
                venue="Journal of AI",
                year=2024,
                citations=25
            ),
            Paper(
                title="ML Applications for Healthcare Systems",
                authors=[Author("Robert Johnson", "Hospital A")],
                venue="Journal of AI",
                year=2024,
                citations=28
            ),
            # Unique paper
            Paper(
                title="Quantum Computing Fundamentals",
                authors=[Author("Alice Brown", "University C")],
                venue="Nature",
                year=2024,
                citations=100
            )
        ]
    
    def test_exact_id_matching(self):
        """Test Stage 1: Exact ID matching"""
        unique_papers, duplicate_groups = self.engine._stage1_exact_id_matching(self.test_papers)
        
        # Should find one duplicate group (papers with same ID)
        assert len(duplicate_groups) == 1
        assert duplicate_groups[0].merge_confidence == 1.0
        
        # Should have one less unique paper
        assert len(unique_papers) == len(self.test_papers) - 1
    
    def test_title_venue_matching(self):
        """Test Stage 2: Title + venue matching"""
        # Skip papers that would be caught by ID matching
        test_papers = self.test_papers[2:]  # Skip first 2 papers with same ID
        
        unique_papers, duplicate_groups = self.engine._stage2_title_venue_matching(test_papers)
        
        # Should find duplicate groups for papers with same title+venue
        assert len(duplicate_groups) >= 1
        
        # Should have fewer unique papers
        assert len(unique_papers) < len(test_papers)
    
    def test_calculate_similarity(self):
        """Test similarity calculation between papers"""
        paper1 = self.test_papers[0]
        paper2 = self.test_papers[1]
        
        similarity = self.engine.calculate_similarity(paper1, paper2)
        
        # Should detect ID overlap
        assert similarity.id_overlap == True
        assert similarity.overall_score == 1.0  # Perfect match due to ID overlap
        
        # Test papers without ID overlap
        paper3 = self.test_papers[2]
        paper4 = self.test_papers[3]
        
        similarity = self.engine.calculate_similarity(paper3, paper4)
        
        assert similarity.title_similarity > 0.9  # Same title
        assert similarity.venue_similarity > 0.8  # Same venue
        assert similarity.year_match == True
        assert similarity.overall_score > 0.8
    
    def test_resolve_duplicate_group(self):
        """Test resolving duplicate groups"""
        # Create papers with different quality scores
        papers = [
            Paper(
                title="Test Paper",
                authors=[Author("John Smith")],
                venue="CVPR",
                year=2024,
                citations=10,
                abstract=""  # No abstract
            ),
            Paper(
                title="Test Paper",
                authors=[Author("John Smith")],
                venue="CVPR",
                year=2024,
                citations=20,
                abstract="This is a test abstract"  # Has abstract
            )
        ]
        
        best_paper = self.engine.resolve_duplicate_group(papers)
        
        # Should select paper with higher quality (more complete metadata)
        assert best_paper.citations == 20
        assert best_paper.abstract == "This is a test abstract"
    
    def test_full_deduplication_pipeline(self):
        """Test complete deduplication pipeline"""
        result = self.engine.deduplicate_papers(self.test_papers)
        
        # Check result structure
        assert isinstance(result, DeduplicationResult)
        assert result.original_count == len(self.test_papers)
        assert result.deduplicated_count < result.original_count
        assert result.duplicates_removed > 0
        
        # Check that we found some duplicates
        assert len(result.duplicate_groups) > 0
        
        # Check processing time
        assert result.processing_time_seconds > 0
        
        # Check quality metrics
        assert 0.0 <= result.quality_score <= 1.0
        assert 0.0 <= result.false_positive_estimate <= 1.0
        assert 0.0 <= result.false_negative_estimate <= 1.0
    
    def test_performance_requirements(self):
        """Test performance requirements for large datasets"""
        # Create larger dataset
        large_dataset = []
        for i in range(1000):
            paper = Paper(
                title=f"Test Paper {i}",
                authors=[Author(f"Author {i}")],
                venue="Test Venue",
                year=2024,
                citations=i
            )
            large_dataset.append(paper)
        
        # Add some duplicates
        for i in range(10):
            duplicate = Paper(
                title=f"Test Paper {i}",  # Same title as original
                authors=[Author(f"Author {i}")],
                venue="Test Venue",
                year=2024,
                citations=i + 1000  # Different citation count
            )
            large_dataset.append(duplicate)
        
        import time
        start_time = time.time()
        
        result = self.engine.deduplicate_papers(large_dataset)
        
        processing_time = time.time() - start_time
        
        # Should process 1000+ papers within 5 minutes (300 seconds)
        assert processing_time < 300.0
        
        # Should find the duplicates we added
        assert result.duplicates_removed >= 10
    
    def test_find_potential_duplicates(self):
        """Test finding potential duplicates for a single paper"""
        target_paper = self.test_papers[0]
        candidates = self.test_papers[1:]
        
        matches = self.engine.find_potential_duplicates(target_paper, candidates)
        
        # Should find some matches
        assert len(matches) > 0
        
        # Matches should be sorted by confidence
        if len(matches) > 1:
            assert matches[0].overall_confidence >= matches[1].overall_confidence
        
        # Should complete quickly (within 100ms for this small dataset)
        import time
        start_time = time.time()
        
        for _ in range(10):
            self.engine.find_potential_duplicates(target_paper, candidates)
        
        avg_time = (time.time() - start_time) / 10
        assert avg_time < 0.1  # 100ms
    
    def test_validate_deduplication_quality(self):
        """Test deduplication quality validation"""
        # Run deduplication
        result = self.engine.deduplicate_papers(self.test_papers)
        
        # Get deduplicated papers (would need to extract from result in real implementation)
        deduplicated_papers = self.test_papers[:result.deduplicated_count]  # Simplified
        
        # Validate quality
        quality_report = self.engine.validate_deduplication_quality(
            self.test_papers, deduplicated_papers
        )
        
        # Check report structure
        assert quality_report.total_papers_analyzed == len(self.test_papers)
        assert 0.0 <= quality_report.estimated_precision <= 1.0
        assert 0.0 <= quality_report.estimated_recall <= 1.0
        assert 0.0 <= quality_report.f1_score <= 1.0
        assert quality_report.processing_time_seconds > 0
        assert quality_report.papers_per_second > 0
    
    def test_thread_safety(self):
        """Test thread safety of deduplication engine"""
        import threading
        import time
        
        results = []
        errors = []
        
        def run_deduplication():
            try:
                result = self.engine.deduplicate_papers(self.test_papers[:4])  # Smaller dataset
                results.append(result)
                time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_deduplication)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors and expected number of results
        assert len(errors) == 0
        assert len(results) == 3
        
        # All results should be valid
        for result in results:
            assert isinstance(result, DeduplicationResult)
            assert result.original_count > 0


class TestIntegration:
    """Integration tests for deduplication system"""
    
    def test_end_to_end_deduplication(self):
        """Test complete deduplication workflow"""
        # Create realistic test dataset
        papers = [
            Paper(
                title="Attention Is All You Need",
                authors=[Author("Ashish Vaswani", "Google"), Author("Noam Shazeer", "Google")],
                venue="NeurIPS",
                year=2017,
                citations=50000,
                paper_id="vaswani2017attention"
            ),
            Paper(
                title="Attention Is All You Need",
                authors=[Author("A. Vaswani", "Google Brain"), Author("N. Shazeer", "Google Brain")],
                venue="NIPS",
                year=2017,
                citations=50100,
                doi="10.5555/3295222.3295349"
            ),
            Paper(
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors=[Author("Jacob Devlin", "Google"), Author("Ming-Wei Chang", "Google")],
                venue="NAACL",
                year=2019,
                citations=40000
            ),
            Paper(
                title="GPT-3: Language Models are Few-Shot Learners",
                authors=[Author("Tom Brown", "OpenAI"), Author("Benjamin Mann", "OpenAI")],
                venue="NeurIPS",
                year=2020,
                citations=15000
            )
        ]
        
        # Run deduplication
        engine = DeduplicationEngine()
        result = engine.deduplicate_papers(papers)
        
        # Should detect the duplicate Attention paper
        assert result.duplicates_removed >= 1
        assert result.deduplicated_count == 3  # 4 papers -> 3 after deduplication
        
        # Should have high quality score
        assert result.quality_score > 0.8
        
        # Should find duplicate groups
        assert len(result.duplicate_groups) >= 1
        
        # First duplicate group should be the Attention paper
        attention_group = None
        for group in result.duplicate_groups:
            if "attention" in group.selected_paper.title.lower():
                attention_group = group
                break
        
        assert attention_group is not None
        assert attention_group.merge_confidence > 0.8
        assert len(attention_group.duplicate_papers) == 2
    
    def test_performance_with_realistic_data(self):
        """Test performance with realistic paper dataset"""
        # Create dataset with realistic paper characteristics
        import random
        
        venues = ["NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "CVPR", "ICCV"]
        authors_pool = [
            "John Smith", "Jane Doe", "Bob Johnson", "Alice Brown", "Charlie Wilson",
            "David Lee", "Emma Davis", "Frank Miller", "Grace Taylor", "Henry Chen"
        ]
        
        papers = []
        for i in range(500):  # 500 papers
            # Random paper characteristics
            venue = random.choice(venues)
            year = random.choice([2020, 2021, 2022, 2023, 2024])
            num_authors = random.randint(1, 4)
            authors = [Author(random.choice(authors_pool), f"University {j}") 
                      for j in range(num_authors)]
            citations = random.randint(0, 1000)
            
            paper = Paper(
                title=f"Research Paper {i}: {venue} Study",
                authors=authors,
                venue=venue,
                year=year,
                citations=citations
            )
            papers.append(paper)
        
        # Add some intentional duplicates
        for i in range(10):
            original = papers[i]
            duplicate = Paper(
                title=original.title + " (Extended Version)",  # Slightly different title
                authors=original.authors[:],  # Same authors
                venue=original.venue,
                year=original.year,
                citations=original.citations + random.randint(1, 10)
            )
            papers.append(duplicate)
        
        # Run deduplication
        engine = DeduplicationEngine()
        import time
        start_time = time.time()
        
        result = engine.deduplicate_papers(papers)
        
        processing_time = time.time() - start_time
        
        # Performance requirements
        assert processing_time < 60.0  # Should complete within 1 minute for 500 papers
        assert result.original_count == len(papers)
        
        # Should achieve reasonable quality
        assert result.quality_score > 0.7
        
        # Should find some duplicates
        assert result.duplicates_removed >= 5  # Should find at least half of intentional duplicates