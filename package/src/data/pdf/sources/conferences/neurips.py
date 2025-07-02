"""NeurIPS PDF source implementation."""

import re
import requests
from typing import Optional, Dict, Any
from urllib.parse import quote
import logging

from ..base import BasePDFSource

logger = logging.getLogger(__name__)


class NeurIPSPDFSource(BasePDFSource):
    """PDF source for NeurIPS papers."""
    
    def __init__(self):
        super().__init__()
        self.venue_patterns = [
            'neurips', 'nips', 'neural information processing',
            'advances in neural information'
        ]
    
    def matches_venue(self, paper: Dict[str, Any]) -> bool:
        """Check if this is a NeurIPS paper."""
        venue = paper.get('venue', '').lower()
        return any(pattern in venue for pattern in self.venue_patterns)
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF for NeurIPS paper."""
        year = self.extract_year(paper)
        if not year:
            return None
        
        # Try different strategies based on year
        if year <= 2022:
            pdf_url = self._find_papers_nips_cc(paper, year)
        else:
            pdf_url = self._find_neurips_cc(paper, year)
        
        if pdf_url:
            return pdf_url
        
        # Fallback to proceedings search
        return self._search_proceedings_page(paper, year)
    
    def _find_papers_nips_cc(self, paper: Dict[str, Any], year: int) -> Optional[str]:
        """Find PDF on papers.nips.cc (legacy site)."""
        # papers.nips.cc uses format:
        # https://papers.nips.cc/paper/{year}/hash/{paper-slug}.pdf
        
        title = paper.get('title', '')
        if not title:
            return None
        
        # Create slug from title
        slug = self._create_slug(title)
        
        # We don't have the hash, so try to search the proceedings page
        search_url = f"https://papers.nips.cc/paper/{year}"
        
        try:
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                # Look for the paper link
                pattern = rf'href="/paper/{year}/([^"]+/{re.escape(slug)}[^"]*\.pdf)"'
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    return f"https://papers.nips.cc/paper/{year}/{match.group(1)}"
                
                # Try partial match
                escaped_words = [re.escape(word) for word in slug.split('-')[:5]]
                partial_pattern = rf'href="/paper/{year}/([^"]+{escaped_words[0]}[^"]*\.pdf)"'
                matches = re.findall(partial_pattern, response.text, re.IGNORECASE)
                
                # Check each match for title similarity
                for match_path in matches:
                    if self._verify_title_match(match_path, title):
                        return f"https://papers.nips.cc/paper/{year}/{match_path}"
                        
        except Exception as e:
            logger.error(f"Error searching papers.nips.cc: {e}")
        
        return None
    
    def _find_neurips_cc(self, paper: Dict[str, Any], year: int) -> Optional[str]:
        """Find PDF on neurips.cc (new site)."""
        # neurips.cc format varies by year
        # Try OpenReview first for recent years
        
        if year >= 2023:
            # Recent years use OpenReview
            openreview_url = self._search_openreview_neurips(paper, year)
            if openreview_url:
                return openreview_url
        
        # Try direct proceedings page
        proceedings_url = f"https://neurips.cc/virtual/{year}/papers"
        
        try:
            # This would need more sophisticated parsing
            # For now, return None to try other methods
            pass
        except Exception as e:
            logger.error(f"Error searching neurips.cc: {e}")
        
        return None
    
    def _search_openreview_neurips(self, paper: Dict[str, Any], year: int) -> Optional[str]:
        """Search OpenReview for NeurIPS papers."""
        # OpenReview API search
        title = paper.get('title', '')
        if not title:
            return None
        
        # Use OpenReview API
        api_url = "https://api.openreview.net/notes"
        params = {
            'content.venue': f'NeurIPS {year}',
            'content.title': title,
            'limit': 10
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                notes = data.get('notes', [])
                
                for note in notes:
                    note_title = note.get('content', {}).get('title', '')
                    if self.title_similarity(title, note_title) > 0.85:
                        # Get PDF link
                        pdf_link = note.get('content', {}).get('pdf')
                        if pdf_link:
                            if pdf_link.startswith('/'):
                                return f"https://openreview.net{pdf_link}"
                            return pdf_link
                            
        except Exception as e:
            logger.error(f"OpenReview API error: {e}")
        
        return None
    
    def _search_proceedings_page(self, paper: Dict[str, Any], year: int) -> Optional[str]:
        """Search proceedings page as fallback."""
        # This would implement scraping of the main proceedings page
        # For now, return None
        return None
    
    def _create_slug(self, title: str) -> str:
        """Create URL slug from title."""
        # Convert to lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
        slug = slug.strip('-')
        return slug
    
    def _verify_title_match(self, pdf_path: str, original_title: str) -> bool:
        """Verify if PDF path likely matches the title."""
        # Extract title-like part from path
        path_parts = pdf_path.split('/')
        if path_parts:
            filename = path_parts[-1].replace('.pdf', '')
            # Remove hash if present
            if '-' in filename:
                title_part = '-'.join(filename.split('-')[1:])
            else:
                title_part = filename
            
            # Compare with original title
            return self.title_similarity(title_part.replace('-', ' '), original_title) > 0.6
        
        return False