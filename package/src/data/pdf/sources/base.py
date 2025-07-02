"""Base classes for PDF sources."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


class BasePDFSource(ABC):
    """Base class for all PDF sources."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        
    @abstractmethod
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF URL for a paper."""
        pass
    
    def matches_venue(self, paper: Dict[str, Any]) -> bool:
        """Check if this source handles the paper's venue."""
        return False
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for matching."""
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s]', ' ', title.lower())
        title = ' '.join(title.split())
        return title
    
    def title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity score (0-1)."""
        t1 = self.normalize_title(title1)
        t2 = self.normalize_title(title2)
        
        if t1 == t2:
            return 1.0
        
        # Word-based Jaccard similarity
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def extract_year(self, paper: Dict[str, Any]) -> Optional[int]:
        """Extract year from paper."""
        if 'year' in paper:
            return int(paper['year'])
        
        # Try to extract from venue or title
        year_match = re.search(r'20\d{2}', str(paper.get('venue', '')))
        if year_match:
            return int(year_match.group())
        
        return None
    
    def extract_first_author_lastname(self, paper: Dict[str, Any]) -> Optional[str]:
        """Extract first author's last name."""
        authors = paper.get('authors', [])
        if not authors:
            return None
        
        first_author = authors[0]
        if isinstance(first_author, dict):
            name = first_author.get('name', '')
        else:
            name = str(first_author)
        
        # Simple heuristic: last word is usually last name
        name_parts = name.strip().split()
        return name_parts[-1] if name_parts else None