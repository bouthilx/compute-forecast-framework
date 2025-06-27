"""
Author matcher for deduplication system.
Handles author name normalization and similarity calculation for paper deduplication.
"""
import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import logging
from rapidfuzz import fuzz
from ..models import Author

logger = logging.getLogger(__name__)

@dataclass
class AuthorMatchResult:
    """Result of author matching between two papers"""
    similarity_score: float
    matched_authors: List[Tuple[Author, Author]]
    unmatched_authors1: List[Author]
    unmatched_authors2: List[Author]
    match_details: Dict[str, float]

class AuthorMatcher:
    """
    Author matching for paper deduplication.
    Implements exact interface contract from Issue #7.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common name prefixes/suffixes to normalize
        self.name_prefixes = {
            'dr', 'dr.', 'prof', 'prof.', 'professor', 'mr', 'mr.', 'mrs', 'mrs.',
            'ms', 'ms.', 'miss', 'sir', 'dame', 'lord', 'lady'
        }
        
        self.name_suffixes = {
            'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v',
            'phd', 'ph.d', 'ph.d.', 'md', 'm.d', 'm.d.', 'dphil', 'd.phil',
            'edd', 'ed.d', 'ed.d.', 'dsc', 'd.sc', 'd.sc.', 'llb', 'll.b',
            'ma', 'm.a', 'm.a.', 'msc', 'm.sc', 'm.sc.', 'mba', 'm.b.a',
            'bs', 'b.s', 'b.s.', 'ba', 'b.a', 'b.a.', 'bsc', 'b.sc'
        }
        
        # Common middle name abbreviations
        self.common_initials = set('abcdefghijklmnopqrstuvwxyz')
        
        # Affiliation keywords for fuzzy matching
        self.institution_keywords = {
            'university', 'univ', 'college', 'institute', 'inst', 'school',
            'research', 'laboratory', 'lab', 'center', 'centre', 'department',
            'dept', 'faculty', 'division', 'corp', 'corporation', 'company',
            'ltd', 'inc', 'llc', 'technologies', 'tech', 'systems'
        }
    
    def normalize_author_name(self, name: str) -> str:
        """
        Normalize author name for matching
        
        REQUIREMENTS:
        - Handle name variations (J. Smith vs John Smith)
        - Remove titles and suffixes
        - Standardize format
        - Handle unicode and special characters
        """
        if not name:
            return ""
        
        # Step 1: Basic cleanup
        normalized = name.strip()
        
        # Step 2: Remove common prefixes and suffixes
        normalized = self._remove_titles_and_suffixes(normalized)
        
        # Step 3: Handle unicode and special characters
        normalized = self._clean_unicode(normalized)
        
        # Step 4: Normalize spacing and punctuation
        normalized = re.sub(r'[,;]', ' ', normalized)  # Replace commas/semicolons with spaces
        normalized = re.sub(r'\.(?!\s)', '. ', normalized)  # Add space after periods
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        # Step 5: Convert to standard format: "Last, First Middle"
        normalized = self._standardize_name_format(normalized)
        
        # Step 6: Final cleanup
        normalized = normalized.strip().lower()
        
        return normalized
    
    def calculate_author_similarity(self, authors1: List[Author], authors2: List[Author]) -> float:
        """
        Calculate author similarity between paper author lists
        
        REQUIREMENTS:
        - Handle name variations (J. Smith vs John Smith)
        - Account for author order differences
        - Use fuzzy matching for name similarities
        - Return score 0.0 to 1.0
        """
        if not authors1 or not authors2:
            return 0.0
        
        # Get detailed match result
        match_result = self._match_author_lists(authors1, authors2)
        
        return match_result.similarity_score
    
    def _match_author_lists(self, authors1: List[Author], authors2: List[Author]) -> AuthorMatchResult:
        """
        Detailed matching between two author lists
        
        Returns comprehensive match result with details
        """
        if not authors1 or not authors2:
            return AuthorMatchResult(
                similarity_score=0.0,
                matched_authors=[],
                unmatched_authors1=authors1[:],
                unmatched_authors2=authors2[:],
                match_details={}
            )
        
        # Normalize all author names
        norm_authors1 = [(author, self.normalize_author_name(author.name)) for author in authors1]
        norm_authors2 = [(author, self.normalize_author_name(author.name)) for author in authors2]
        
        # Find best matches using Hungarian-like algorithm
        matched_pairs = []
        used_indices2 = set()
        
        # Sort by name similarity to get best matches first
        similarity_matrix = []
        for i, (author1, norm1) in enumerate(norm_authors1):
            for j, (author2, norm2) in enumerate(norm_authors2):
                if j not in used_indices2:
                    similarity = self._calculate_name_similarity(norm1, norm2, author1, author2)
                    similarity_matrix.append((similarity, i, j, author1, author2))
        
        # Sort by similarity (highest first)
        similarity_matrix.sort(reverse=True)
        
        used_indices1 = set()
        total_similarity = 0.0
        
        # Greedily match highest similarity pairs
        for similarity, i, j, author1, author2 in similarity_matrix:
            if i not in used_indices1 and j not in used_indices2 and similarity >= 0.7:
                matched_pairs.append((author1, author2))
                used_indices1.add(i)
                used_indices2.add(j)
                total_similarity += similarity
        
        # Calculate unmatched authors
        unmatched_authors1 = [authors1[i] for i in range(len(authors1)) if i not in used_indices1]
        unmatched_authors2 = [authors2[j] for j in range(len(authors2)) if j not in used_indices2]
        
        # Calculate overall similarity score
        # Favor papers with more matching authors
        num_matched = len(matched_pairs)
        max_possible_matches = max(len(authors1), len(authors2))
        
        if max_possible_matches == 0:
            overall_similarity = 0.0
        else:
            # Average similarity of matched pairs weighted by coverage
            avg_match_similarity = total_similarity / num_matched if num_matched > 0 else 0.0
            coverage = num_matched / max_possible_matches
            
            # Penalty for unmatched authors
            penalty = (len(unmatched_authors1) + len(unmatched_authors2)) / (len(authors1) + len(authors2))
            
            overall_similarity = avg_match_similarity * coverage * (1 - penalty * 0.5)
        
        return AuthorMatchResult(
            similarity_score=overall_similarity,
            matched_authors=matched_pairs,
            unmatched_authors1=unmatched_authors1,
            unmatched_authors2=unmatched_authors2,
            match_details={
                'num_matched': num_matched,
                'total_authors1': len(authors1),
                'total_authors2': len(authors2),
                'avg_match_similarity': avg_match_similarity if num_matched > 0 else 0.0,
                'coverage': coverage
            }
        )
    
    def _calculate_name_similarity(self, norm_name1: str, norm_name2: str, 
                                 author1: Author, author2: Author) -> float:
        """Calculate similarity between two normalized names"""
        if not norm_name1 or not norm_name2:
            return 0.0
        
        # Exact match
        if norm_name1 == norm_name2:
            return 1.0
        
        # Check for initial matching (J. Smith vs John Smith)
        initial_similarity = self._check_initial_match(norm_name1, norm_name2)
        if initial_similarity > 0.8:
            return initial_similarity
        
        # Use fuzzy string matching
        token_sort_ratio = fuzz.token_sort_ratio(norm_name1, norm_name2) / 100.0
        ratio = fuzz.ratio(norm_name1, norm_name2) / 100.0
        partial_ratio = fuzz.partial_ratio(norm_name1, norm_name2) / 100.0
        
        # Weighted combination
        name_similarity = (token_sort_ratio * 0.5 + ratio * 0.3 + partial_ratio * 0.2)
        
        # Boost similarity if affiliations match
        affiliation_boost = 0.0
        if author1.affiliation and author2.affiliation:
            affiliation_similarity = self._calculate_affiliation_similarity(
                author1.affiliation, author2.affiliation
            )
            if affiliation_similarity > 0.7:
                affiliation_boost = 0.1 * affiliation_similarity
        
        return min(name_similarity + affiliation_boost, 1.0)
    
    def _check_initial_match(self, name1: str, name2: str) -> float:
        """Check if names match allowing for initial variations"""
        # Split names into parts
        parts1 = name1.split()
        parts2 = name2.split()
        
        if len(parts1) < 2 or len(parts2) < 2:
            return 0.0
        
        # Check if last names match
        if parts1[-1] != parts2[-1]:
            return 0.0
        
        # Check first name / initial matching
        first1 = parts1[0]
        first2 = parts2[0]
        
        # Both full names
        if len(first1) > 1 and len(first2) > 1:
            if first1 == first2:
                return 1.0
            elif first1.startswith(first2) or first2.startswith(first1):
                return 0.9
            else:
                return fuzz.ratio(first1, first2) / 100.0
        
        # One is initial, one is full name
        elif len(first1) == 1 or len(first2) == 1:
            initial = first1 if len(first1) == 1 else first2
            full_name = first2 if len(first1) == 1 else first1
            
            if full_name.startswith(initial):
                return 0.85
            else:
                return 0.0
        
        return 0.0
    
    def _calculate_affiliation_similarity(self, affiliation1: str, affiliation2: str) -> float:
        """Calculate similarity between affiliations"""
        if not affiliation1 or not affiliation2:
            return 0.0
        
        # Normalize affiliations
        norm_aff1 = self._normalize_affiliation(affiliation1)
        norm_aff2 = self._normalize_affiliation(affiliation2)
        
        if norm_aff1 == norm_aff2:
            return 1.0
        
        # Use token-based similarity for affiliations
        return fuzz.token_set_ratio(norm_aff1, norm_aff2) / 100.0
    
    def _normalize_affiliation(self, affiliation: str) -> str:
        """Normalize affiliation string"""
        if not affiliation:
            return ""
        
        normalized = affiliation.lower().strip()
        
        # Remove common suffixes and prefixes
        normalized = re.sub(r'\b(university of|univ of|univ\.?)\b', 'university', normalized)
        normalized = re.sub(r'\b(institute of|inst of|inst\.?)\b', 'institute', normalized)
        normalized = re.sub(r'\b(college of|coll of|coll\.?)\b', 'college', normalized)
        normalized = re.sub(r'\b(department of|dept of|dept\.?)\b', 'department', normalized)
        normalized = re.sub(r'\b(school of)\b', 'school', normalized)
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def _remove_titles_and_suffixes(self, name: str) -> str:
        """Remove titles and suffixes from name"""
        parts = name.lower().split()
        
        # Remove prefixes
        while parts and parts[0] in self.name_prefixes:
            parts.pop(0)
        
        # Remove suffixes
        while parts and parts[-1] in self.name_suffixes:
            parts.pop()
        
        return ' '.join(parts)
    
    def _clean_unicode(self, name: str) -> str:
        """Clean unicode characters and normalize"""
        # Replace common unicode variants
        replacements = {
            'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ã': 'a', 'å': 'a',
            'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
            'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
            'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o', 'õ': 'o', 'ø': 'o',
            'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u',
            'ý': 'y', 'ÿ': 'y',
            'ñ': 'n', 'ç': 'c',
            'ß': 'ss'
        }
        
        cleaned = name
        for unicode_char, replacement in replacements.items():
            cleaned = cleaned.replace(unicode_char, replacement)
            cleaned = cleaned.replace(unicode_char.upper(), replacement.upper())
        
        return cleaned
    
    def _standardize_name_format(self, name: str) -> str:
        """Convert name to standard format: Last, First Middle"""
        parts = name.split()
        
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            # Assume "First Last" format
            return f"{parts[1]}, {parts[0]}"
        else:
            # Handle "First Middle Last" or "Last, First Middle"
            if ',' in name:
                # Already in "Last, First ..." format
                return name
            else:
                # Assume "First Middle ... Last" format
                first_middle = ' '.join(parts[:-1])
                last = parts[-1]
                return f"{last}, {first_middle}"
    
    def find_potential_author_matches(self, target_author: Author, 
                                    candidate_authors: List[Author],
                                    threshold: float = 0.8) -> List[Tuple[Author, float]]:
        """Find potential matches for a single author"""
        matches = []
        target_norm = self.normalize_author_name(target_author.name)
        
        for candidate in candidate_authors:
            candidate_norm = self.normalize_author_name(candidate.name)
            similarity = self._calculate_name_similarity(target_norm, candidate_norm, 
                                                       target_author, candidate)
            
            if similarity >= threshold:
                matches.append((candidate, similarity))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def is_same_author(self, author1: Author, author2: Author, threshold: float = 0.9) -> bool:
        """Check if two authors are likely the same person"""
        norm1 = self.normalize_author_name(author1.name)
        norm2 = self.normalize_author_name(author2.name)
        
        similarity = self._calculate_name_similarity(norm1, norm2, author1, author2)
        return similarity >= threshold
    
    def get_author_signature(self, author: Author) -> str:
        """Get a signature string for author indexing"""
        normalized = self.normalize_author_name(author.name)
        
        # Create signature from first letter of each name part
        parts = normalized.split()
        if len(parts) >= 2:
            # Use first initial + last name for signature
            signature = f"{parts[0][0] if parts[0] else ''}{parts[-1]}"
            return signature.replace(',', '').replace(' ', '')
        else:
            return normalized.replace(',', '').replace(' ', '')


class AuthorMatchCache:
    """Cache for author matching results to improve performance"""
    
    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self.cache: Dict[tuple, float] = {}
        self.access_order: List[tuple] = []
    
    def get_match_score(self, authors1: List[Author], authors2: List[Author]) -> Optional[float]:
        """Get cached match score or None if not cached"""
        key = self._create_cache_key(authors1, authors2)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    def set_match_score(self, authors1: List[Author], authors2: List[Author], score: float) -> None:
        """Cache match score"""
        key = self._create_cache_key(authors1, authors2)
        
        if key in self.cache:
            # Update existing entry
            self.cache[key] = score
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new entry
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            self.cache[key] = score
            self.access_order.append(key)
    
    def _create_cache_key(self, authors1: List[Author], authors2: List[Author]) -> tuple:
        """Create consistent cache key from author lists"""
        # Sort author names to ensure consistent key regardless of order
        names1 = tuple(sorted([author.name for author in authors1]))
        names2 = tuple(sorted([author.name for author in authors2]))
        
        # Ensure consistent ordering for cache key
        return (names1, names2) if names1 <= names2 else (names2, names1)
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        self.access_order.clear()