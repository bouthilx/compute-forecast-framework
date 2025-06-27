"""
Similarity index for efficient large dataset processing.
Optimizes deduplication performance for datasets with 10,000+ papers.
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import logging
from ..models import Paper

logger = logging.getLogger(__name__)

@dataclass
class IndexStats:
    """Statistics about the similarity index"""
    total_papers: int
    total_tokens: int
    average_tokens_per_paper: float
    index_size_mb: float
    build_time_seconds: float

class SimilarityIndex:
    """
    Efficient similarity search for large paper datasets using inverted indexing.
    Implements optimizations required for 10,000+ paper processing.
    """
    
    def __init__(self, min_token_length: int = 3, max_tokens_per_paper: int = 50):
        """
        Initialize similarity index
        
        Args:
            min_token_length: Minimum length of tokens to index
            max_tokens_per_paper: Maximum tokens to index per paper (for memory control)
        """
        self.min_token_length = min_token_length
        self.max_tokens_per_paper = max_tokens_per_paper
        self.logger = logging.getLogger(__name__)
        
        # Inverted index: token -> set of paper indices
        self.token_index: Dict[str, Set[int]] = defaultdict(set)
        
        # Paper storage
        self.papers: List[Paper] = []
        self.paper_tokens: Dict[int, Set[str]] = {}
        
        # Author index for quick author-based lookups
        self.author_index: Dict[str, Set[int]] = defaultdict(set)
        
        # Venue index for quick venue-based lookups
        self.venue_index: Dict[str, Set[int]] = defaultdict(set)
        
        # Year index for temporal filtering
        self.year_index: Dict[int, Set[int]] = defaultdict(set)
        
        # Statistics
        self.stats = IndexStats(0, 0, 0.0, 0.0, 0.0)
    
    def build_index(self, papers: List[Paper], title_normalizer, author_matcher) -> None:
        """
        Build similarity index from papers
        
        Args:
            papers: List of papers to index
            title_normalizer: TitleNormalizer instance for token extraction
            author_matcher: AuthorMatcher instance for author signatures
        """
        import time
        start_time = time.time()
        
        self.papers = papers
        self.token_index.clear()
        self.paper_tokens.clear()
        self.author_index.clear()
        self.venue_index.clear()
        self.year_index.clear()
        
        total_tokens = 0
        
        for i, paper in enumerate(papers):
            # Index title tokens
            title_tokens = title_normalizer.get_title_tokens(paper.title)
            
            # Limit tokens per paper for memory efficiency
            if len(title_tokens) > self.max_tokens_per_paper:
                # Keep most important tokens (longer ones typically more specific)
                title_tokens = set(sorted(title_tokens, key=len, reverse=True)[:self.max_tokens_per_paper])
            
            # Filter by minimum token length
            title_tokens = {token for token in title_tokens if len(token) >= self.min_token_length}
            
            self.paper_tokens[i] = title_tokens
            total_tokens += len(title_tokens)
            
            # Add to token index
            for token in title_tokens:
                self.token_index[token].add(i)
            
            # Index authors
            for author in paper.authors:
                author_signature = author_matcher.get_author_signature(author)
                if author_signature:
                    self.author_index[author_signature].add(i)
            
            # Index venue
            venue = paper.normalized_venue or paper.venue
            if venue:
                self.venue_index[venue.lower()].add(i)
            
            # Index year
            if paper.year:
                self.year_index[paper.year].add(i)
        
        # Update statistics
        build_time = time.time() - start_time
        self.stats = IndexStats(
            total_papers=len(papers),
            total_tokens=total_tokens,
            average_tokens_per_paper=total_tokens / len(papers) if papers else 0.0,
            index_size_mb=self._estimate_index_size_mb(),
            build_time_seconds=build_time
        )
        
        self.logger.info(f"Built similarity index for {len(papers)} papers in {build_time:.2f}s")
        self.logger.info(f"Index size: {self.stats.index_size_mb:.1f}MB, avg tokens/paper: {self.stats.average_tokens_per_paper:.1f}")
    
    def find_similar_papers(self, 
                          paper_index: int, 
                          min_token_overlap: int = 2,
                          include_venue_filter: bool = True,
                          include_year_filter: bool = True,
                          year_window: int = 2) -> List[int]:
        """
        Find papers similar to the given paper using token overlap
        
        Args:
            paper_index: Index of target paper
            min_token_overlap: Minimum number of overlapping tokens
            include_venue_filter: Filter by venue similarity
            include_year_filter: Filter by year proximity
            year_window: Years +/- to consider if year filtering enabled
            
        Returns:
            List of paper indices sorted by token overlap (descending)
        """
        if paper_index >= len(self.papers):
            return []
        
        target_paper = self.papers[paper_index]
        target_tokens = self.paper_tokens.get(paper_index, set())
        
        if not target_tokens:
            return []
        
        # Find candidates using token overlap
        candidate_scores: Dict[int, int] = defaultdict(int)
        
        for token in target_tokens:
            for candidate_idx in self.token_index.get(token, set()):
                if candidate_idx != paper_index:
                    candidate_scores[candidate_idx] += 1
        
        # Filter by minimum token overlap
        candidates = [(idx, score) for idx, score in candidate_scores.items() 
                     if score >= min_token_overlap]
        
        # Apply venue filter
        if include_venue_filter and (target_paper.normalized_venue or target_paper.venue):
            target_venue = (target_paper.normalized_venue or target_paper.venue).lower()
            venue_candidates = self.venue_index.get(target_venue, set())
            candidates = [(idx, score) for idx, score in candidates if idx in venue_candidates]
        
        # Apply year filter
        if include_year_filter and target_paper.year:
            year_candidates = set()
            for year in range(target_paper.year - year_window, target_paper.year + year_window + 1):
                year_candidates.update(self.year_index.get(year, set()))
            candidates = [(idx, score) for idx, score in candidates if idx in year_candidates]
        
        # Sort by token overlap (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [idx for idx, score in candidates]
    
    def find_candidates_by_author(self, paper_index: int, author_matcher) -> Set[int]:
        """Find candidate papers with overlapping authors"""
        if paper_index >= len(self.papers):
            return set()
        
        target_paper = self.papers[paper_index]
        candidates = set()
        
        for author in target_paper.authors:
            author_signature = author_matcher.get_author_signature(author)
            if author_signature:
                candidates.update(self.author_index.get(author_signature, set()))
        
        # Remove self
        candidates.discard(paper_index)
        
        return candidates
    
    def find_candidates_by_venue(self, paper_index: int) -> Set[int]:
        """Find candidate papers from same venue"""
        if paper_index >= len(self.papers):
            return set()
        
        target_paper = self.papers[paper_index]
        venue = target_paper.normalized_venue or target_paper.venue
        
        if not venue:
            return set()
        
        candidates = self.venue_index.get(venue.lower(), set())
        
        # Remove self
        candidates = candidates.copy()
        candidates.discard(paper_index)
        
        return candidates
    
    def find_candidates_by_year(self, paper_index: int, year_window: int = 1) -> Set[int]:
        """Find candidate papers from similar years"""
        if paper_index >= len(self.papers):
            return set()
        
        target_paper = self.papers[paper_index]
        
        if not target_paper.year:
            return set()
        
        candidates = set()
        for year in range(target_paper.year - year_window, target_paper.year + year_window + 1):
            candidates.update(self.year_index.get(year, set()))
        
        # Remove self
        candidates.discard(paper_index)
        
        return candidates
    
    def get_paper_by_index(self, paper_index: int) -> Optional[Paper]:
        """Get paper by index"""
        if 0 <= paper_index < len(self.papers):
            return self.papers[paper_index]
        return None
    
    def get_token_overlap_score(self, paper_index1: int, paper_index2: int) -> float:
        """Calculate token overlap score between two papers"""
        tokens1 = self.paper_tokens.get(paper_index1, set())
        tokens2 = self.paper_tokens.get(paper_index2, set())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        # Jaccard similarity
        return intersection / union if union > 0 else 0.0
    
    def get_frequent_tokens(self, min_frequency: int = 10) -> Dict[str, int]:
        """Get tokens that appear in at least min_frequency papers"""
        frequent_tokens = {}
        
        for token, paper_indices in self.token_index.items():
            if len(paper_indices) >= min_frequency:
                frequent_tokens[token] = len(paper_indices)
        
        return frequent_tokens
    
    def get_rare_tokens(self, max_frequency: int = 2) -> Dict[str, int]:
        """Get tokens that appear in at most max_frequency papers (likely noise)"""
        rare_tokens = {}
        
        for token, paper_indices in self.token_index.items():
            if len(paper_indices) <= max_frequency:
                rare_tokens[token] = len(paper_indices)
        
        return rare_tokens
    
    def optimize_index(self) -> None:
        """Remove rare tokens to optimize index size and performance"""
        rare_tokens = self.get_rare_tokens(max_frequency=1)
        
        # Remove rare tokens from index
        for token in rare_tokens:
            del self.token_index[token]
        
        # Remove rare tokens from paper tokens
        for paper_idx, tokens in self.paper_tokens.items():
            self.paper_tokens[paper_idx] = tokens - set(rare_tokens.keys())
        
        self.logger.info(f"Removed {len(rare_tokens)} rare tokens from index")
    
    def _estimate_index_size_mb(self) -> float:
        """Estimate memory usage of the index in MB"""
        import sys
        
        size_bytes = 0
        
        # Token index
        for token, indices in self.token_index.items():
            size_bytes += sys.getsizeof(token) + sys.getsizeof(indices)
            size_bytes += sum(sys.getsizeof(idx) for idx in indices)
        
        # Paper tokens
        for paper_idx, tokens in self.paper_tokens.items():
            size_bytes += sys.getsizeof(paper_idx) + sys.getsizeof(tokens)
            size_bytes += sum(sys.getsizeof(token) for token in tokens)
        
        # Author index
        for signature, indices in self.author_index.items():
            size_bytes += sys.getsizeof(signature) + sys.getsizeof(indices)
            size_bytes += sum(sys.getsizeof(idx) for idx in indices)
        
        # Venue index
        for venue, indices in self.venue_index.items():
            size_bytes += sys.getsizeof(venue) + sys.getsizeof(indices)
            size_bytes += sum(sys.getsizeof(idx) for idx in indices)
        
        # Year index
        for year, indices in self.year_index.items():
            size_bytes += sys.getsizeof(year) + sys.getsizeof(indices)
            size_bytes += sum(sys.getsizeof(idx) for idx in indices)
        
        return size_bytes / (1024 * 1024)  # Convert to MB
    
    def get_index_statistics(self) -> IndexStats:
        """Get current index statistics"""
        return self.stats
    
    def clear_index(self) -> None:
        """Clear all index data"""
        self.token_index.clear()
        self.papers.clear()
        self.paper_tokens.clear()
        self.author_index.clear()
        self.venue_index.clear()
        self.year_index.clear()
        
        self.stats = IndexStats(0, 0, 0.0, 0.0, 0.0)


class BatchSimilarityProcessor:
    """
    Batch processor for efficient similarity calculations on large datasets.
    Reduces redundant calculations by caching and grouping operations.
    """
    
    def __init__(self, similarity_index: SimilarityIndex):
        self.similarity_index = similarity_index
        self.logger = logging.getLogger(__name__)
        
        # Cache for similarity calculations
        self._similarity_cache: Dict[Tuple[int, int], float] = {}
    
    def find_all_similar_pairs(self, 
                             title_normalizer,
                             similarity_threshold: float = 0.9,
                             max_candidates_per_paper: int = 100) -> List[Tuple[int, int, float]]:
        """
        Find all similar paper pairs in the dataset
        
        Returns:
            List of (paper_idx1, paper_idx2, similarity_score) tuples
        """
        similar_pairs = []
        processed_pairs = set()
        
        for i in range(len(self.similarity_index.papers)):
            # Find candidates using index
            candidates = self.similarity_index.find_similar_papers(
                i, 
                min_token_overlap=2,
                include_venue_filter=False,  # Don't filter by venue for broader search
                include_year_filter=True,
                year_window=3
            )
            
            # Limit candidates for performance
            candidates = candidates[:max_candidates_per_paper]
            
            for candidate_idx in candidates:
                # Avoid duplicate pairs
                pair_key = (min(i, candidate_idx), max(i, candidate_idx))
                if pair_key in processed_pairs:
                    continue
                
                processed_pairs.add(pair_key)
                
                # Calculate detailed similarity
                similarity = self._get_cached_similarity(i, candidate_idx, title_normalizer)
                
                if similarity >= similarity_threshold:
                    similar_pairs.append((i, candidate_idx, similarity))
        
        # Sort by similarity (highest first)
        similar_pairs.sort(key=lambda x: x[2], reverse=True)
        
        return similar_pairs
    
    def _get_cached_similarity(self, idx1: int, idx2: int, title_normalizer) -> float:
        """Get similarity with caching"""
        # Ensure consistent ordering for cache key
        cache_key = (min(idx1, idx2), max(idx1, idx2))
        
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # Calculate similarity
        paper1 = self.similarity_index.papers[idx1]
        paper2 = self.similarity_index.papers[idx2]
        
        similarity = title_normalizer.calculate_title_similarity(paper1.title, paper2.title)
        
        # Cache result
        self._similarity_cache[cache_key] = similarity
        
        return similarity
    
    def clear_cache(self) -> None:
        """Clear similarity cache"""
        self._similarity_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cache_size': len(self._similarity_cache),
            'cache_hits': getattr(self, '_cache_hits', 0),
            'cache_misses': getattr(self, '_cache_misses', 0)
        }