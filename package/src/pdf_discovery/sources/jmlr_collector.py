"""JMLR and TMLR PDF collector."""

import re
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.data.models import Paper
from src.pdf_discovery.core.models import PDFRecord
from src.pdf_discovery.core.collectors import BasePDFCollector

logger = logging.getLogger(__name__)


class JMLRCollector(BasePDFCollector):
    """Collector for JMLR and TMLR papers."""
    
    def __init__(self):
        """Initialize the JMLR/TMLR PDF collector."""
        super().__init__("jmlr_tmlr")
        self.jmlr_base_url = "https://jmlr.org/papers/"
        self.tmlr_base_url = "https://jmlr.org/tmlr/papers/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Academic Paper Collector)"
        })
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            Exception: If PDF cannot be discovered
        """
        # Determine if this is a JMLR or TMLR paper
        venue = paper.venue.lower() if paper.venue else ""
        journal = paper.journal.lower() if hasattr(paper, 'journal') and paper.journal else ""
        
        is_jmlr = "jmlr" in venue or "journal of machine learning research" in venue or \
                  "jmlr" in journal or "journal of machine learning research" in journal
        is_tmlr = "tmlr" in venue or "transactions on machine learning research" in venue or \
                  "tmlr" in journal or "transactions on machine learning research" in journal
        
        if not (is_jmlr or is_tmlr):
            raise ValueError(f"Paper {paper.paper_id} is not from JMLR or TMLR")
        
        if is_jmlr:
            return self._discover_jmlr(paper)
        else:
            return self._discover_tmlr(paper)
    
    def _discover_jmlr(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a JMLR paper.
        
        JMLR URL pattern: https://jmlr.org/papers/v{volume}/{paper}.pdf
        """
        # Try to extract volume and paper ID from paper metadata
        volume_info = self._extract_jmlr_volume_info(paper)
        
        if not volume_info:
            # Fall back to searching the JMLR website
            return self._search_jmlr_website(paper)
        
        pdf_url = f"{self.jmlr_base_url}v{volume_info['volume']}/{volume_info['paper_id']}.pdf"
        
        # Verify the URL exists
        try:
            response = self.session.head(pdf_url, timeout=10)
            if response.status_code == 200:
                return PDFRecord(
                    paper_id=paper.paper_id,
                    pdf_url=pdf_url,
                    source=self.source_name,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={"type": "published", "venue": "JMLR"},
                    validation_status="verified",
                    license="JMLR"
                )
        except Exception as e:
            logger.debug(f"Failed to verify JMLR URL {pdf_url}: {e}")
        
        # If direct URL construction failed, search the website
        return self._search_jmlr_website(paper)
    
    def _discover_tmlr(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a TMLR paper by searching the TMLR papers page."""
        try:
            response = self.session.get(self.tmlr_base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find paper by title
            paper_title = paper.title.lower().strip()
            
            # TMLR papers are listed with links
            for link in soup.find_all('a'):
                link_text = link.get_text().lower().strip()
                
                # Check if this link contains the paper title
                if self._fuzzy_title_match(paper_title, link_text):
                    href = link.get('href')
                    if href and href.endswith('.pdf'):
                        pdf_url = urljoin(self.tmlr_base_url, href)
                        
                        return PDFRecord(
                            paper_id=paper.paper_id,
                            pdf_url=pdf_url,
                            source=self.source_name,
                            discovery_timestamp=datetime.now(),
                            confidence_score=0.90,
                            version_info={"type": "published", "venue": "TMLR"},
                            validation_status="discovered",
                            license="TMLR"
                        )
            
            raise ValueError(f"Could not find TMLR paper: {paper.title}")
            
        except Exception as e:
            logger.error(f"Error discovering TMLR paper {paper.paper_id}: {e}")
            raise
    
    def _extract_jmlr_volume_info(self, paper: Paper) -> Optional[Dict[str, Any]]:
        """Extract volume and paper ID from paper metadata.
        
        Returns:
            Dictionary with 'volume' and 'paper_id' keys, or None if not found
        """
        # Check if paper has URLs that might contain volume info
        if paper.urls:
            for url in paper.urls:
                # Pattern: jmlr.org/papers/v23/21-1234.html or similar
                match = re.search(r'jmlr\.org/papers/v(\d+)/([^/\s]+)(?:\.html)?', url)
                if match:
                    return {
                        'volume': match.group(1),
                        'paper_id': match.group(2).replace('.html', '')
                    }
        
        # Check if paper has volume field
        if hasattr(paper, 'volume') and paper.volume:
            # Need to find paper ID - might be in URLs or other fields
            paper_id = None
            if paper.urls:
                for url in paper.urls:
                    # Extract paper ID from URL
                    match = re.search(r'/([^/]+?)(?:\.html)?$', url)
                    if match:
                        paper_id = match.group(1)
                        break
            
            if paper_id:
                return {
                    'volume': paper.volume,
                    'paper_id': paper_id
                }
        
        return None
    
    def _search_jmlr_website(self, paper: Paper) -> PDFRecord:
        """Search JMLR website for a paper by title."""
        # For now, we'll raise an exception as implementing full website search
        # would require more complex scraping logic
        raise ValueError(f"Could not construct JMLR URL for paper {paper.paper_id}. "
                        "Website search not implemented in this version.")
    
    def _fuzzy_title_match(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be the same paper.
        
        Simple implementation - can be enhanced with fuzzy string matching.
        """
        # Remove common words and punctuation for comparison
        def normalize_title(title):
            # Remove punctuation and convert to lowercase
            title = re.sub(r'[^\w\s]', ' ', title.lower())
            # Remove extra whitespace
            title = ' '.join(title.split())
            return title
        
        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)
        
        # Check if one title contains the other (handling subtitles)
        return norm_title1 in norm_title2 or norm_title2 in norm_title1