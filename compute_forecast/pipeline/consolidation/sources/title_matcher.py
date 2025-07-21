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
        """Normalize author lists for comparison with smart initial matching."""
        
        def normalize_author_name(name: str) -> Tuple[str, str]:
            """Extract first initial and last name from author name.
            
            Returns:
                (first_initial, last_name) tuple
            """
            # Handle comma-separated names (Last, First)
            if ',' in name:
                parts = name.split(',', 1)
                last_name = parts[0].strip().lower()
                first_parts = parts[1].strip().lower().split() if len(parts) > 1 else []
            else:
                # Normal order (First Last)
                parts = name.lower().strip().split()
                if not parts:
                    return ("", "")
                last_name = parts[-1]
                first_parts = parts[:-1]
            
            # Clean last name of suffixes
            last_name = re.sub(r'\b(jr|sr|iii|ii|iv|v)\.?$', '', last_name).strip()
            
            # Get first initial
            first_initial = ""
            if first_parts:
                first_part = first_parts[0].rstrip('.')
                # Always use just the first character as initial
                first_initial = first_part[0] if first_part else ""
                
            return (first_initial, last_name)
        
        # Extract author representations
        authors1_normalized = []
        authors2_normalized = []
        
        for author in authors1:
            name = author.name if hasattr(author, 'name') else str(author)
            first, last = normalize_author_name(name)
            if last:  # Must have at least a last name
                authors1_normalized.append((first, last))
                
        for author in authors2:
            name = author.name if hasattr(author, 'name') else str(author)
            first, last = normalize_author_name(name)
            if last:  # Must have at least a last name
                authors2_normalized.append((first, last))
        
        # Count matches with flexible matching
        # For each author in the smaller list, find best match in larger list
        matches = 0
        used_indices = set()
        
        # Process the smaller list first to maximize match potential
        if len(authors1_normalized) <= len(authors2_normalized):
            for a1_first, a1_last in authors1_normalized:
                for i, (a2_first, a2_last) in enumerate(authors2_normalized):
                    if i in used_indices:
                        continue
                    # Check if last names match
                    if a1_last == a2_last:
                        # Check first initial compatibility
                        # Empty matches anything (missing first name)
                        # Same initial matches
                        # Full name matches initial (j matches jacob)
                        if (not a1_first or not a2_first or  # One is missing
                            a1_first == a2_first):  # Same initial
                            matches += 1
                            used_indices.add(i)
                            break
        else:
            # Process from authors2 perspective
            for a2_first, a2_last in authors2_normalized:
                for i, (a1_first, a1_last) in enumerate(authors1_normalized):
                    if i in used_indices:
                        continue
                    if a2_last == a1_last:
                        if (not a1_first or not a2_first or
                            a1_first == a2_first):
                            matches += 1
                            used_indices.add(i)
                            break
        
        # Return sets that represent the actual author lists and their overlap
        # set1 represents all authors from list 1
        # set2 should represent all authors from list 2, not just matches
        # The intersection will represent the matches
        set1 = set(range(len(authors1_normalized)))
        set2 = set(range(len(authors1_normalized), len(authors1_normalized) + len(authors2_normalized)))
        
        # Add common elements to represent matches
        # We'll add the first 'matches' elements from set1 to set2
        for i in range(matches):
            set2.add(i)
            
        return set1, set2
        
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
            similarity = 1.0
            # Apply safety checks even for exact normalized matches
            if self.require_safety_checks:
                # Check year difference
                if year1 and year2:
                    year_diff = abs(year1 - year2)
                    if year_diff > 1:
                        # Papers more than 1 year apart - reduce score
                        similarity *= 0.5
                        
                # Check author overlap - always apply if authors provided
                if authors1 and authors2:
                    authors1_normalized, authors2_normalized = self._normalize_authors(authors1, authors2)
                    overlap = len(authors1_normalized & authors2_normalized)
                    # Calculate overlap ratio based on smaller author list
                    min_authors = min(len(authors1_normalized), len(authors2_normalized))
                    if min_authors > 0:
                        overlap_ratio = overlap / min_authors
                        # Apply penalty based on overlap ratio
                        # Full overlap (1.0) = no penalty
                        # No overlap (0.0) = multiply by 0.3
                        # Linear interpolation: penalty = 0.3 + 0.7 * overlap_ratio
                        author_penalty = 0.3 + 0.7 * overlap_ratio
                        similarity *= author_penalty
                        logger.debug(f"Author overlap: {overlap}/{min_authors} = {overlap_ratio:.2f}, penalty factor: {author_penalty:.2f}")
            
            # Determine match type based on final similarity
            if similarity >= 1.0:
                return similarity, "exact"
            elif similarity >= self.high_confidence_threshold:
                return similarity, "high_confidence"
            elif similarity >= self.medium_confidence_threshold:
                return similarity, "medium_confidence"
            elif similarity > 0.7:
                return similarity, "low_confidence"
            else:
                return similarity, "no_match"
            
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
                        
                # Check author overlap - always apply if authors provided
                if authors1 and authors2:
                    authors1_normalized, authors2_normalized = self._normalize_authors(authors1, authors2)
                    overlap = len(authors1_normalized & authors2_normalized)
                    # Calculate overlap ratio based on smaller author list
                    min_authors = min(len(authors1_normalized), len(authors2_normalized))
                    if min_authors > 0:
                        overlap_ratio = overlap / min_authors
                        # Apply penalty based on overlap ratio
                        # Full overlap (1.0) = no penalty
                        # No overlap (0.0) = multiply by 0.3
                        # Linear interpolation: penalty = 0.3 + 0.7 * overlap_ratio
                        author_penalty = 0.3 + 0.7 * overlap_ratio
                        similarity *= author_penalty
                        logger.debug(f"Author overlap: {overlap}/{min_authors} = {overlap_ratio:.2f}, penalty factor: {author_penalty:.2f}")
                        
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
                    
            # Check author overlap - always apply if authors provided
            if authors1 and authors2:
                authors1_normalized, authors2_normalized = self._normalize_authors(authors1, authors2)
                overlap = len(authors1_normalized & authors2_normalized)
                # Calculate overlap ratio based on smaller author list
                min_authors = min(len(authors1_normalized), len(authors2_normalized))
                if min_authors > 0:
                    overlap_ratio = overlap / min_authors
                    # Apply penalty based on overlap ratio
                    # Full overlap (1.0) = no penalty
                    # No overlap (0.0) = multiply by 0.3
                    # Linear interpolation: penalty = 0.3 + 0.7 * overlap_ratio
                    author_penalty = 0.3 + 0.7 * overlap_ratio
                    similarity *= author_penalty
                    logger.debug(f"Author overlap: {overlap}/{min_authors} = {overlap_ratio:.2f}, penalty factor: {author_penalty:.2f}")
                        
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