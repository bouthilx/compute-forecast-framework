"""Matching algorithms for PDF deduplication."""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging

from rapidfuzz import fuzz
from src.data.models import Paper, Author
from src.pdf_discovery.core.models import PDFRecord

logger = logging.getLogger(__name__)


@dataclass
class ExactMatch:
    """Represents an exact match between records."""
    record_ids: List[str]
    match_field: str  # 'doi', 'arxiv_id', 'paper_id', etc.
    match_value: str
    confidence: float = 1.0


@dataclass
class FuzzyMatch:
    """Represents a fuzzy match between records."""
    record_ids: List[str]
    title_similarity: float
    author_similarity: float
    venue_year_match: bool
    
    @property
    def confidence(self) -> float:
        """Calculate overall confidence score."""
        # Weighted combination
        base_score = (self.title_similarity * 0.6 + self.author_similarity * 0.4)
        # Boost if venue and year match
        if self.venue_year_match:
            base_score = min(1.0, base_score * 1.1)
        return base_score


class IdentifierNormalizer:
    """Normalize and validate paper identifiers."""
    
    def __init__(self):
        # DOI pattern: 10.xxxx/yyyy
        self.doi_pattern = re.compile(r'10\.\d{4,}/[^\s]+')
        
        # arXiv patterns
        # New format: YYMM.NNNNN (since 2007)
        self.arxiv_new_pattern = re.compile(r'(\d{4}\.\d{4,5})')
        # Old format: category/YYMMNNN
        self.arxiv_old_pattern = re.compile(r'([a-zA-Z\-\.]+/\d{7})')
        
        # Common URL prefixes to remove
        self.doi_prefixes = [
            'https://doi.org/',
            'http://doi.org/',
            'http://dx.doi.org/',
            'https://dx.doi.org/',
            'doi:',
            'DOI:',
        ]
        
        self.arxiv_prefixes = [
            'https://arxiv.org/abs/',
            'http://arxiv.org/abs/',
            'https://arxiv.org/pdf/',
            'http://arxiv.org/pdf/',
            'arXiv:',
            'arxiv:',
        ]
    
    def normalize_doi(self, doi: str) -> Optional[str]:
        """Normalize DOI to standard format."""
        if not doi:
            return None
        
        # Remove common prefixes
        normalized = doi.strip()
        for prefix in self.doi_prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove any remaining whitespace
        normalized = normalized.strip()
        
        # Validate DOI pattern
        if self.doi_pattern.match(normalized):
            return normalized
        
        return None
    
    def normalize_arxiv_id(self, arxiv_id: str) -> Optional[str]:
        """Normalize arXiv ID to standard format."""
        if not arxiv_id:
            return None
        
        # Remove common prefixes
        normalized = arxiv_id.strip()
        for prefix in self.arxiv_prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove .pdf extension if present
        if normalized.endswith('.pdf'):
            normalized = normalized[:-4]
        
        # Remove version suffix (e.g., v1, v2)
        normalized = re.sub(r'v\d+$', '', normalized)
        
        # Validate arXiv pattern
        if self.arxiv_new_pattern.match(normalized) or self.arxiv_old_pattern.match(normalized):
            return normalized
        
        return None
    
    def extract_identifiers_from_url(self, url: str) -> Dict[str, str]:
        """Extract identifiers from a URL."""
        identifiers = {}
        
        # Check for DOI
        doi_match = self.doi_pattern.search(url)
        if doi_match:
            identifiers['doi'] = doi_match.group(0)
        
        # Check for arXiv ID
        # First try new format
        arxiv_match = self.arxiv_new_pattern.search(url)
        if arxiv_match:
            identifiers['arxiv_id'] = self.normalize_arxiv_id(arxiv_match.group(0))
        else:
            # Try old format
            arxiv_match = self.arxiv_old_pattern.search(url)
            if arxiv_match:
                identifiers['arxiv_id'] = self.normalize_arxiv_id(arxiv_match.group(0))
        
        return identifiers


class PaperFuzzyMatcher:
    """Fuzzy matching for paper titles and authors."""
    
    def __init__(self, title_threshold: float = 0.95, author_threshold: float = 0.85):
        self.title_threshold = title_threshold
        self.author_threshold = author_threshold
        self.identifier_normalizer = IdentifierNormalizer()
        
        # Common title suffixes to remove for comparison
        self.title_suffixes = [
            r'\s*\(extended abstract\)',
            r'\s*\(short paper\)',
            r'\s*\(long paper\)',
            r'\s*\(poster\)',
            r'\s*\(demo\)',
            r'\s*\(supplementary material\)',
            r'\s*\(appendix\)',
            r'\s*-\s*supplementary.*',
            r'\s*:\s*supplementary.*',
        ]
    
    def normalize_title(self, title: str) -> str:
        """Normalize paper title for comparison."""
        if not title:
            return ""
        
        normalized = title.lower().strip()
        
        # Remove common suffixes
        for suffix_pattern in self.title_suffixes:
            normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def normalize_author_name(self, name: str) -> str:
        """Normalize author name for comparison."""
        if not name:
            return ""
        
        # Convert to lowercase and strip
        normalized = name.lower().strip()
        
        # Handle initials (J. Doe -> j doe)
        normalized = re.sub(r'\.\s*', ' ', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        if not title1 or not title2:
            return 0.0
        
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        if norm1 == norm2:
            return 1.0
        
        # Use multiple similarity measures
        token_sort = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        token_set = fuzz.token_set_ratio(norm1, norm2) / 100.0
        partial = fuzz.partial_ratio(norm1, norm2) / 100.0
        
        # Weighted average
        return token_sort * 0.5 + token_set * 0.3 + partial * 0.2
    
    def calculate_author_similarity(self, authors1: List[Author], authors2: List[Author]) -> float:
        """Calculate similarity between author lists."""
        if not authors1 or not authors2:
            return 0.0
        
        # Normalize author names
        names1 = [self.normalize_author_name(a.name) for a in authors1]
        names2 = [self.normalize_author_name(a.name) for a in authors2]
        
        # Track matched names to avoid double counting
        matched_indices1 = set()
        matched_indices2 = set()
        exact_matches = 0
        fuzzy_matches = 0
        
        # First pass: exact matches
        for i, name1 in enumerate(names1):
            for j, name2 in enumerate(names2):
                if i not in matched_indices1 and j not in matched_indices2:
                    if name1 == name2:
                        exact_matches += 1
                        matched_indices1.add(i)
                        matched_indices2.add(j)
                        break
        
        # Second pass: fuzzy matches on unmatched names
        for i, name1 in enumerate(names1):
            if i not in matched_indices1:
                best_match_score = 0
                best_match_j = -1
                
                for j, name2 in enumerate(names2):
                    if j not in matched_indices2:
                        # Check for initials match (J. Doe vs John Doe)
                        if self._is_initials_match(name1, name2):
                            fuzzy_matches += 0.9
                            matched_indices1.add(i)
                            matched_indices2.add(j)
                            break
                        
                        # General fuzzy match
                        similarity = fuzz.ratio(name1, name2) / 100.0
                        if similarity > best_match_score:
                            best_match_score = similarity
                            best_match_j = j
                
                # Accept fuzzy match if similarity is high enough
                if best_match_j >= 0 and best_match_score > 0.85:
                    fuzzy_matches += best_match_score
                    matched_indices1.add(i)
                    matched_indices2.add(best_match_j)
        
        # Calculate final score
        total_matches = exact_matches + fuzzy_matches
        max_possible = max(len(names1), len(names2))
        
        if max_possible == 0:
            return 0.0
        
        return min(1.0, total_matches / max_possible)
    
    def _is_initials_match(self, name1: str, name2: str) -> bool:
        """Check if one name is an initial version of the other."""
        parts1 = name1.split()
        parts2 = name2.split()
        
        if len(parts1) != len(parts2):
            return False
        
        for p1, p2 in zip(parts1, parts2):
            # Check if one is initial of the other
            if len(p1) == 1 and p2.startswith(p1):
                continue
            elif len(p2) == 1 and p1.startswith(p2):
                continue
            elif p1 != p2:
                return False
        
        return True
    
    def find_duplicates_exact(self, records: List[PDFRecord]) -> List[ExactMatch]:
        """Find exact duplicates based on identifiers."""
        matches = []
        
        # Group by identifiers
        doi_groups: Dict[str, List[PDFRecord]] = {}
        arxiv_groups: Dict[str, List[PDFRecord]] = {}
        paper_id_groups: Dict[str, List[PDFRecord]] = {}
        
        for record in records:
            # Assume paper data is attached to record
            if hasattr(record, 'paper_data'):
                paper = record.paper_data
                
                # Group by DOI
                if paper.doi:
                    normalized_doi = self.identifier_normalizer.normalize_doi(paper.doi)
                    if normalized_doi:
                        if normalized_doi not in doi_groups:
                            doi_groups[normalized_doi] = []
                        doi_groups[normalized_doi].append(record)
                
                # Group by arXiv ID
                if paper.arxiv_id:
                    normalized_arxiv = self.identifier_normalizer.normalize_arxiv_id(paper.arxiv_id)
                    if normalized_arxiv:
                        if normalized_arxiv not in arxiv_groups:
                            arxiv_groups[normalized_arxiv] = []
                        arxiv_groups[normalized_arxiv].append(record)
                
                # Group by paper ID (if from same source)
                if paper.paper_id:
                    if paper.paper_id not in paper_id_groups:
                        paper_id_groups[paper.paper_id] = []
                    paper_id_groups[paper.paper_id].append(record)
        
        # Create matches for groups with multiple records
        for doi, group in doi_groups.items():
            if len(group) > 1:
                matches.append(ExactMatch(
                    record_ids=[r.paper_id for r in group],
                    match_field='doi',
                    match_value=doi,
                ))
        
        for arxiv_id, group in arxiv_groups.items():
            if len(group) > 1:
                matches.append(ExactMatch(
                    record_ids=[r.paper_id for r in group],
                    match_field='arxiv_id',
                    match_value=arxiv_id,
                ))
        
        # Only consider paper_id matches if from different sources
        for paper_id, group in paper_id_groups.items():
            sources = {r.source for r in group}
            if len(sources) > 1:
                matches.append(ExactMatch(
                    record_ids=[r.paper_id for r in group],
                    match_field='paper_id',
                    match_value=paper_id,
                ))
        
        return matches
    
    def find_duplicates_fuzzy(self, records: List[PDFRecord]) -> List[FuzzyMatch]:
        """Find fuzzy duplicates based on title/author similarity."""
        matches = []
        
        # Skip fuzzy matching if dataset is too large to avoid O(n²) performance issues
        if len(records) > 5000:
            logger.warning(f"Skipping fuzzy matching for {len(records)} records (too large)")
            return matches
        
        # Pre-filter records that have paper_data
        valid_records = [r for r in records if hasattr(r, 'paper_data')]
        
        # Compare all pairs
        for i in range(len(valid_records)):
            for j in range(i + 1, len(valid_records)):
                record1, record2 = valid_records[i], valid_records[j]
                paper1, paper2 = record1.paper_data, record2.paper_data
                
                # Quick title check first (fastest filter)
                title_sim = self.calculate_title_similarity(paper1.title, paper2.title)
                if title_sim < self.title_threshold:
                    continue
                
                # Only calculate expensive author similarity if title matches
                author_sim = self.calculate_author_similarity(paper1.authors, paper2.authors)
                if author_sim < self.author_threshold:
                    continue
                
                # Check venue and year
                venue_year_match = (
                    paper1.year == paper2.year and 
                    paper1.venue and paper2.venue and
                    (paper1.venue.lower() in paper2.venue.lower() or 
                     paper2.venue.lower() in paper1.venue.lower())
                )
                
                matches.append(FuzzyMatch(
                    record_ids=[record1.paper_id, record2.paper_id],
                    title_similarity=title_sim,
                    author_similarity=author_sim,
                    venue_year_match=venue_year_match,
                ))
        
        return matches