"""Fuzzy title matching for consolidation with safety mechanisms."""

import re
from typing import Optional, Tuple, List
import logging

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class TitleMatcher:
    """Fuzzy title matching for consolidation with safety mechanisms."""
    
    def __init__(
        self,
        exact_threshold: float = 1.0,
        high_confidence_threshold: float = 0.95,
        medium_confidence_threshold: float = 0.85,
        require_safety_checks: bool = True
    ):
        """
        Initialize the title matcher.
        
        Args:
            exact_threshold: Score for exact matches (default 1.0)
            high_confidence_threshold: Minimum score for high confidence matches
            medium_confidence_threshold: Minimum score for medium confidence matches
            require_safety_checks: Whether to apply year/author safety checks
        """
        self.exact_threshold = exact_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.require_safety_checks = require_safety_checks
        
        # Title normalization patterns
        self.title_suffixes = [
            r"\s*\(extended abstract\)",
            r"\s*\(short paper\)",
            r"\s*\(long paper\)",
            r"\s*\(poster\)",
            r"\s*\(demo\)",
            r"\s*\(vision paper\)",
            r"\s*\(position paper\)",
            r"\s*\(supplementary material\)",
            r"\s*\(appendix\)",
            r"\s*:\s*supplementary.*",
            r"\s*-\s*supplementary.*",
            # ArXiv-specific patterns
            r"\s*\[.*\]$",  # Remove bracketed content at end
            r"\s*\(.*arxiv.*\)",  # Remove arxiv references
        ]
        
    def normalize_title(self, title: str) -> str:
        """
        Normalize title for comparison.
        
        Steps:
        1. Convert to lowercase
        2. Remove common suffixes (extended abstract, etc.)
        3. Normalize punctuation to spaces
        4. Remove extra whitespace
        """
        if not title:
            return ""
            
        normalized = title.lower().strip()
        
        # Remove common suffixes
        for suffix_pattern in self.title_suffixes:
            normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)
            
        # Normalize punctuation - keep alphanumeric and basic punctuation
        # This is less aggressive than removing all punctuation
        normalized = re.sub(r'[^\w\s\-:,]', ' ', normalized)
        normalized = re.sub(r'[:,-]', ' ', normalized)
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
        
    def _normalize_authors(self, authors1: List, authors2: List) -> Tuple[set, set]:
        """Normalize author lists for comparison."""
        authors1_normalized = set()
        for author in authors1:
            # Handle both string and Author objects
            name = author.name if hasattr(author, 'name') else str(author)
            # Simple normalization - lowercase and remove extra spaces
            normalized = ' '.join(name.lower().strip().split())
            # Also add last name only for better matching
            last_name = normalized.split()[-1] if normalized else ""
            authors1_normalized.add(normalized)
            if last_name:
                authors1_normalized.add(last_name)
                
        authors2_normalized = set()
        for author in authors2:
            name = author.name if hasattr(author, 'name') else str(author)
            normalized = ' '.join(name.lower().strip().split())
            last_name = normalized.split()[-1] if normalized else ""
            authors2_normalized.add(normalized)
            if last_name:
                authors2_normalized.add(last_name)
                
        return authors1_normalized, authors2_normalized
        
    def calculate_similarity(
        self, 
        title1: str, 
        title2: str,
        year1: Optional[int] = None,
        year2: Optional[int] = None,
        authors1: Optional[List[str]] = None,
        authors2: Optional[List[str]] = None
    ) -> Tuple[float, str]:
        """
        Calculate title similarity with safety checks.
        
        Args:
            title1: First title
            title2: Second title
            year1: Publication year of first paper
            year2: Publication year of second paper
            authors1: List of author names for first paper
            authors2: List of author names for second paper
            
        Returns:
            (similarity_score, match_type)
            match_type: "exact", "high_confidence", "medium_confidence", "low_confidence", "no_match"
        """
        if not title1 or not title2:
            return 0.0, "no_match"
            
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        # Exact match after normalization
        if norm1 == norm2:
            # Apply safety checks even for exact normalized matches
            if self.require_safety_checks:
                # Check year difference
                if year1 and year2:
                    year_diff = abs(year1 - year2)
                    if year_diff > 1:
                        # Papers more than 1 year apart - not exact match
                        return 0.5, "low_confidence"
            return 1.0, "exact"
            
        # Check substring containment (common for ArXiv vs conference)
        if norm1 in norm2 or norm2 in norm1:
            # One title contains the other - high confidence
            similarity = 0.98
            
            # Apply safety checks
            if self.require_safety_checks:
                # Check year difference
                if year1 and year2:
                    year_diff = abs(year1 - year2)
                    if year_diff > 1:
                        similarity *= 0.5
                        
                # Check author overlap
                if authors1 and authors2 and similarity >= self.medium_confidence_threshold:
                    authors1_normalized, authors2_normalized = self._normalize_authors(authors1, authors2)
                    overlap = len(authors1_normalized & authors2_normalized)
                    if overlap == 0:
                        similarity *= 0.7
                        
            if similarity >= self.high_confidence_threshold:
                return similarity, "high_confidence"
            elif similarity >= self.medium_confidence_threshold:
                return similarity, "medium_confidence"
            else:
                return similarity, "low_confidence"
            
        # Calculate multiple similarity measures
        token_sort = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        token_set = fuzz.token_set_ratio(norm1, norm2) / 100.0
        partial = fuzz.partial_ratio(norm1, norm2) / 100.0
        ratio = fuzz.ratio(norm1, norm2) / 100.0
        
        # Log detailed scores for debugging
        logger.debug(
            f"Title similarity scores - token_sort: {token_sort:.3f}, "
            f"token_set: {token_set:.3f}, partial: {partial:.3f}, ratio: {ratio:.3f}"
        )
        
        # Weighted combination (favor token-based for academic titles)
        similarity = (
            token_sort * 0.4 +
            token_set * 0.3 +
            partial * 0.2 +
            ratio * 0.1
        )
        
        # Apply safety checks if enabled
        if self.require_safety_checks and similarity < self.exact_threshold:
            # Require year match for fuzzy matches
            if year1 and year2:
                year_diff = abs(year1 - year2)
                if year_diff > 1:
                    # Papers more than 1 year apart - reduce confidence
                    logger.debug(f"Year mismatch penalty: {year1} vs {year2}")
                    similarity *= 0.5
                elif year_diff == 1:
                    # Adjacent years (common for ArXiv->conference) - small penalty
                    similarity *= 0.95
                    
            # Check author overlap for medium confidence matches
            if similarity >= self.medium_confidence_threshold:
                if authors1 and authors2:
                    authors1_normalized, authors2_normalized = self._normalize_authors(authors1, authors2)
                    overlap = len(authors1_normalized & authors2_normalized)
                    if overlap == 0:
                        logger.debug("No author overlap - reducing confidence")
                        similarity *= 0.7
                    else:
                        logger.debug(f"Found {overlap} author overlaps")
                        
        # Determine match type based on final similarity
        if similarity >= self.high_confidence_threshold:
            match_type = "high_confidence"
        elif similarity >= self.medium_confidence_threshold:
            match_type = "medium_confidence"
        elif similarity > 0.7:
            match_type = "low_confidence"
        else:
            match_type = "no_match"
            
        logger.debug(
            f"Title match result: {similarity:.3f} ({match_type}) for "
            f"'{title1[:50]}...' vs '{title2[:50]}...'"
        )
            
        return similarity, match_type
        
    def is_similar(
        self,
        title1: str,
        title2: str,
        year1: Optional[int] = None,
        year2: Optional[int] = None,
        authors1: Optional[List[str]] = None,
        authors2: Optional[List[str]] = None,
        min_confidence: str = "high_confidence"
    ) -> bool:
        """
        Check if two titles are similar enough based on confidence threshold.
        
        Args:
            title1, title2: Titles to compare
            year1, year2: Publication years
            authors1, authors2: Author lists
            min_confidence: Minimum confidence level to accept
                ("exact", "high_confidence", "medium_confidence", "low_confidence")
                
        Returns:
            True if similarity meets the minimum confidence level
        """
        confidence_levels = {
            "exact": 4,
            "high_confidence": 3,
            "medium_confidence": 2,
            "low_confidence": 1,
            "no_match": 0
        }
        
        _, match_type = self.calculate_similarity(
            title1, title2, year1, year2, authors1, authors2
        )
        
        min_level = confidence_levels.get(min_confidence, 3)
        actual_level = confidence_levels.get(match_type, 0)
        
        return actual_level >= min_level