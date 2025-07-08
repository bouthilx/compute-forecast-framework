"""
Fuzzy venue matcher for venue normalization.
Handles similarity scoring and fuzzy matching of venue names.
"""

import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy venue matching"""

    original_venue: str
    matched_venue: Optional[str]
    similarity_score: float
    normalized_original: str
    normalized_matched: Optional[str]
    match_type: str  # "exact", "fuzzy", "abbreviation", "none"


class FuzzyVenueMatcher:
    """Fuzzy matching for venue names with normalization and similarity scoring"""

    def __init__(self, fuzzy_threshold: float = 0.9):
        self.fuzzy_threshold = fuzzy_threshold
        self.logger = logging.getLogger(__name__)

        # Common abbreviations and expansions
        self.abbreviation_map = {
            # Conference names
            "NIPS": "NEURIPS",
            "IJCAI": "International Joint Conference on Artificial Intelligence",
            "AAAI": "Association for the Advancement of Artificial Intelligence",
            "SIGIR": "Special Interest Group on Information Retrieval",
            "SIGKDD": "Knowledge Discovery and Data Mining",
            "KDD": "Knowledge Discovery and Data Mining",
            "WWW": "World Wide Web Conference",
            "CHI": "Computer Human Interaction",
            "CSCW": "Computer Supported Cooperative Work",
            "UIST": "User Interface Software and Technology",
            "ICSE": "International Conference on Software Engineering",
            "FSE": "Foundations of Software Engineering",
            "OOPSLA": "Object-Oriented Programming Systems Languages and Applications",
            "PLDI": "Programming Language Design and Implementation",
            "POPL": "Principles of Programming Languages",
            "OSDI": "Operating Systems Design and Implementation",
            "SOSP": "Symposium on Operating Systems Principles",
            "NSDI": "Networked Systems Design and Implementation",
            "VLDB": "Very Large Data Base",
            "SIGMOD": "Special Interest Group on Management of Data",
            "ICDE": "International Conference on Data Engineering",
            # ML/AI specific
            "ML": "Machine Learning",
            "AI": "Artificial Intelligence",
            "CV": "Computer Vision",
            "NLP": "Natural Language Processing",
            "RL": "Reinforcement Learning",
            "DL": "Deep Learning",
            # Common words
            "CONF": "Conference",
            "SYMP": "Symposium",
            "WORKSHOP": "Workshop",
            "PROC": "Proceedings",
            "INTL": "International",
            "NATL": "National",
            "ASSOC": "Association",
            "COMP": "Computer",
            "SCI": "Science",
            "TECH": "Technology",
            "ENG": "Engineering",
            "MATH": "Mathematics",
            "STAT": "Statistics",
            "PHYS": "Physics",
        }

        # Common venue suffixes to ignore
        self.ignore_suffixes = [
            r"\s*\d{4}",  # Years: 2024, 2023, etc.
            r"\s*\'\d{2}",  # Short years: '24, '23, etc.
            r"\s*\(.*\)",  # Parenthetical content
            r"\s*-\s*\d{4}",  # Dash years: - 2024
            r"\s*workshops?",  # Workshop(s)
            r"\s*demos?",  # Demo(s)
            r"\s*tutorials?",  # Tutorial(s)
            r"\s*posters?",  # Poster(s)
            r"\s*extended\s*abstracts?",  # Extended abstracts
            r"\s*short\s*papers?",  # Short papers
            r"\s*long\s*papers?",  # Long papers
            r"\s*volume\s*\d+",  # Volume numbers
            r"\s*vol\.\s*\d+",  # Vol. numbers
            r"\s*proceedings\s*of\s*the",  # "Proceedings of the"
            r"\s*conference\s*papers?",  # Conference papers
            r"\s*main\s*track",  # Main track
            r"\s*findings",  # Findings
        ]

    def normalize_venue_name(self, venue: str) -> str:
        """
        Normalize venue name for comparison

        Steps:
        1. Convert to uppercase
        2. Remove years and parenthetical content
        3. Handle abbreviations
        4. Remove extra whitespace and punctuation
        5. Sort words for order-independent comparison
        """
        if not venue:
            return ""

        # Step 1: Convert to uppercase
        normalized = venue.upper().strip()

        # Step 2: Remove suffixes and noise
        for suffix_pattern in self.ignore_suffixes:
            normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)

        # Step 3: Handle abbreviations
        words = normalized.split()
        expanded_words = []
        for word in words:
            # Remove punctuation from word
            clean_word = re.sub(r"[^\w]", "", word)
            if clean_word in self.abbreviation_map:
                expanded_words.extend(self.abbreviation_map[clean_word].upper().split())
            else:
                expanded_words.append(clean_word)

        # Step 4: Remove common stop words and noise
        stop_words = {
            "THE",
            "OF",
            "ON",
            "IN",
            "FOR",
            "AND",
            "OR",
            "AT",
            "TO",
            "WITH",
            "BY",
        }
        filtered_words = [
            word for word in expanded_words if word and word not in stop_words
        ]

        # Step 5: Sort words for order-independent comparison (but preserve some order)
        # Keep first word in place (often the main conference name)
        if filtered_words:
            first_word = filtered_words[0]
            other_words = sorted(filtered_words[1:])
            normalized = " ".join([first_word] + other_words)
        else:
            normalized = " ".join(sorted(filtered_words))

        return normalized.strip()

    def calculate_venue_similarity(self, venue1: str, venue2: str) -> float:
        """
        Calculate similarity score between two venue names

        Uses multiple similarity measures:
        1. Exact match after normalization
        2. Token sort ratio (order-independent)
        3. Partial ratio (substring matching)
        4. Token set ratio (word set comparison)
        """
        if not venue1 or not venue2:
            return 0.0

        # Normalize both venues
        norm1 = self.normalize_venue_name(venue1)
        norm2 = self.normalize_venue_name(venue2)

        # Exact match after normalization
        if norm1 == norm2:
            return 1.0

        # Multiple similarity measures
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        partial_ratio = fuzz.partial_ratio(norm1, norm2) / 100.0
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2) / 100.0
        ratio = fuzz.ratio(norm1, norm2) / 100.0

        # Weighted combination (favor token-based comparisons)
        similarity = (
            token_sort_ratio * 0.4
            + token_set_ratio * 0.3
            + partial_ratio * 0.2
            + ratio * 0.1
        )

        return similarity

    def find_fuzzy_matches(
        self, raw_venue: str, candidates: List[str], threshold: float = None
    ) -> List[Tuple[str, float]]:
        """
        Find fuzzy matches above threshold

        Returns matches sorted by confidence (highest first)
        """
        if threshold is None:
            threshold = self.fuzzy_threshold

        matches = []
        self.normalize_venue_name(raw_venue)

        for candidate in candidates:
            similarity = self.calculate_venue_similarity(raw_venue, candidate)
            if similarity >= threshold:
                matches.append((candidate, similarity))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def find_best_match(
        self, raw_venue: str, candidates: List[str], threshold: float = None
    ) -> FuzzyMatchResult:
        """
        Find the best fuzzy match for a venue name

        Returns the highest-scoring match above threshold, or None
        """
        if threshold is None:
            threshold = self.fuzzy_threshold

        normalized_raw = self.normalize_venue_name(raw_venue)

        # Check for exact match first
        for candidate in candidates:
            if self.normalize_venue_name(candidate) == normalized_raw:
                return FuzzyMatchResult(
                    original_venue=raw_venue,
                    matched_venue=candidate,
                    similarity_score=1.0,
                    normalized_original=normalized_raw,
                    normalized_matched=self.normalize_venue_name(candidate),
                    match_type="exact",
                )

        # Check for abbreviation match
        for candidate in candidates:
            if self._is_abbreviation_match(raw_venue, candidate):
                similarity = self.calculate_venue_similarity(raw_venue, candidate)
                return FuzzyMatchResult(
                    original_venue=raw_venue,
                    matched_venue=candidate,
                    similarity_score=similarity,
                    normalized_original=normalized_raw,
                    normalized_matched=self.normalize_venue_name(candidate),
                    match_type="abbreviation",
                )

        # Find fuzzy matches
        matches = self.find_fuzzy_matches(raw_venue, candidates, threshold)

        if matches:
            best_match, best_score = matches[0]
            return FuzzyMatchResult(
                original_venue=raw_venue,
                matched_venue=best_match,
                similarity_score=best_score,
                normalized_original=normalized_raw,
                normalized_matched=self.normalize_venue_name(best_match),
                match_type="fuzzy",
            )

        # No match found
        return FuzzyMatchResult(
            original_venue=raw_venue,
            matched_venue=None,
            similarity_score=0.0,
            normalized_original=normalized_raw,
            normalized_matched=None,
            match_type="none",
        )

    def _is_abbreviation_match(self, venue1: str, venue2: str) -> bool:
        """Check if one venue is an abbreviation of another"""
        norm1 = self.normalize_venue_name(venue1)
        norm2 = self.normalize_venue_name(venue2)

        # Check if either is an abbreviation in our map
        for abbrev, expansion in self.abbreviation_map.items():
            if (abbrev in norm1 and expansion.upper() in norm2) or (
                abbrev in norm2 and expansion.upper() in norm1
            ):
                return True

        return False

    def batch_find_matches(
        self, raw_venues: List[str], candidates: List[str], threshold: float = None
    ) -> Dict[str, FuzzyMatchResult]:
        """
        Batch processing for multiple venue matches

        More efficient than calling find_best_match repeatedly
        """
        if threshold is None:
            threshold = self.fuzzy_threshold

        results = {}

        # Use rapidfuzz's process.extract for efficient batch processing
        for raw_venue in raw_venues:
            try:
                # Get top matches using rapidfuzz
                matches = process.extract(
                    raw_venue,
                    candidates,
                    scorer=fuzz.token_sort_ratio,
                    limit=3,
                    score_cutoff=threshold * 100,
                )

                if matches:
                    # Get the best match and calculate our custom similarity
                    best_candidate = matches[0][0]
                    custom_similarity = self.calculate_venue_similarity(
                        raw_venue, best_candidate
                    )

                    if custom_similarity >= threshold:
                        results[raw_venue] = FuzzyMatchResult(
                            original_venue=raw_venue,
                            matched_venue=best_candidate,
                            similarity_score=custom_similarity,
                            normalized_original=self.normalize_venue_name(raw_venue),
                            normalized_matched=self.normalize_venue_name(
                                best_candidate
                            ),
                            match_type="fuzzy",
                        )
                    else:
                        results[raw_venue] = FuzzyMatchResult(
                            original_venue=raw_venue,
                            matched_venue=None,
                            similarity_score=0.0,
                            normalized_original=self.normalize_venue_name(raw_venue),
                            normalized_matched=None,
                            match_type="none",
                        )
                else:
                    results[raw_venue] = FuzzyMatchResult(
                        original_venue=raw_venue,
                        matched_venue=None,
                        similarity_score=0.0,
                        normalized_original=self.normalize_venue_name(raw_venue),
                        normalized_matched=None,
                        match_type="none",
                    )

            except Exception as e:
                self.logger.error(f"Error matching venue '{raw_venue}': {e}")
                results[raw_venue] = FuzzyMatchResult(
                    original_venue=raw_venue,
                    matched_venue=None,
                    similarity_score=0.0,
                    normalized_original=self.normalize_venue_name(raw_venue),
                    normalized_matched=None,
                    match_type="none",
                )

        return results
