"""ACL Anthology PDF collector for computational linguistics conferences.

This module implements a PDF collector for the ACL Anthology, which hosts papers
from major computational linguistics conferences including EMNLP, EACL, ACL, and NAACL.

The collector:
- Maps venue names to ACL Anthology venue codes
- Searches proceedings pages to find paper IDs
- Constructs and validates PDF URLs
- Supports fuzzy title matching for robustness

Example usage:
    from src.pdf_discovery.sources import ACLAnthologyCollector
    from src.pdf_discovery.core.framework import PDFDiscoveryFramework
    
    framework = PDFDiscoveryFramework()
    collector = ACLAnthologyCollector()
    framework.add_collector(collector)
    
    # Set ACL as priority source for computational linguistics venues
    framework.set_venue_priorities({
        "EMNLP": ["acl_anthology", "semantic_scholar"],
        "ACL": ["acl_anthology", "arxiv"],
        "NAACL": ["acl_anthology", "openalex"]
    })
    
    results = framework.discover_pdfs(papers)
"""

import re
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup

from src.data.models import Paper
from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord

logger = logging.getLogger(__name__)


class ACLAnthologyCollector(BasePDFCollector):
    """Collector for ACL Anthology PDFs from computational linguistics conferences."""
    
    # Venue mapping from conference names to ACL Anthology codes
    VENUE_MAPPING = {
        "EMNLP": ["emnlp-main", "emnlp-findings"],
        "EACL": ["eacl-main", "eacl-short"],
        "ACL": ["acl-long", "acl-short"],
        "NAACL": ["naacl-main", "naacl-short"]
    }
    
    BASE_URL = "https://aclanthology.org"
    
    def __init__(self):
        """Initialize ACL Anthology collector."""
        super().__init__("acl_anthology")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Academic PDF Collector)"
        })
    
    def _map_venue_to_codes(self, venue: str) -> List[str]:
        """Map venue name to ACL Anthology venue codes.
        
        Args:
            venue: Venue name from paper (e.g., "EMNLP", "ACL 2023")
            
        Returns:
            List of possible venue codes to try
        """
        # Normalize venue name: uppercase and remove year
        normalized = venue.upper().strip()
        
        # Remove year from venue name (e.g., "EMNLP 2023" -> "EMNLP")
        normalized = re.sub(r'\s*\d{4}\s*', '', normalized).strip()
        
        # Look up in mapping
        return self.VENUE_MAPPING.get(normalized, [])
    
    def _construct_pdf_url(self, venue_code: str, year: int, paper_id: str) -> str:
        """Construct PDF URL from components.
        
        Args:
            venue_code: ACL venue code (e.g., "emnlp-main")
            year: Publication year
            paper_id: Paper ID from proceedings
            
        Returns:
            Full PDF URL
        """
        return f"{self.BASE_URL}/{year}.{venue_code}.{paper_id}.pdf"
    
    def _search_proceedings(self, venue_code: str, year: int, title: str) -> Optional[str]:
        """Search proceedings page for paper ID by title.
        
        Args:
            venue_code: ACL venue code
            year: Publication year
            title: Paper title to search for
            
        Returns:
            Paper ID if found, None otherwise
        """
        # Construct proceedings URL
        # Extract base venue name (e.g., "emnlp-main" -> "emnlp")
        base_venue = venue_code.split('-')[0]
        proceedings_url = f"{self.BASE_URL}/events/{base_venue}-{year}/"
        
        try:
            response = self.session.get(proceedings_url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch proceedings from {proceedings_url}: {response.status_code}")
                return None
            
            # Parse proceedings HTML to find paper using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for links with paper URLs matching pattern /{year}.{venue_code}.{id}/
            pattern = rf'/{year}\.{re.escape(venue_code)}\.(\d+)/'
            
            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                
                # Check if href matches the pattern
                match = re.search(pattern, href)
                if match:
                    paper_id = match.group(1)
                    
                    # Get the text content of the link (handles nested HTML tags)
                    link_title = link.get_text(strip=True)
                    
                    # Check if title matches (fuzzy matching)
                    if self._fuzzy_match_title(link_title, title):
                        logger.info(f"Found paper ID {paper_id} for title: {title}")
                        return paper_id
            
            logger.debug(f"Paper not found in proceedings: {title}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching proceedings from {proceedings_url}: {e}")
            return None
    
    def _fuzzy_match_title(self, title1: str, title2: str, threshold: float = 0.85) -> bool:
        """Fuzzy match two titles to handle minor variations.
        
        Args:
            title1: First title
            title2: Second title
            threshold: Minimum similarity score (0-1)
            
        Returns:
            True if titles match above threshold
        """
        # Normalize titles: lowercase, remove extra spaces
        norm1 = ' '.join(title1.lower().split())
        norm2 = ' '.join(title2.lower().split())
        
        # Calculate similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold
    
    def _validate_pdf_url(self, url: str) -> Tuple[bool, Optional[int]]:
        """Validate that PDF URL exists and is accessible.
        
        Args:
            url: PDF URL to validate
            
        Returns:
            Tuple of (is_valid, file_size_bytes)
        """
        try:
            response = self.session.head(url, timeout=10)
            
            if response.status_code == 200:
                # Check content type and size
                content_type = response.headers.get('Content-Type', '')
                content_length = response.headers.get('Content-Length')
                
                if 'pdf' in content_type.lower():
                    size = int(content_length) if content_length else None
                    return True, size
            
            return False, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating PDF URL {url}: {e}")
            return False, None
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            Exception: If PDF cannot be discovered
        """
        # Get venue codes for this paper
        venue_codes = self._map_venue_to_codes(paper.venue)
        
        if not venue_codes:
            raise Exception(f"Unknown venue: {paper.venue}")
        
        # Try each venue code in order
        for venue_code in venue_codes:
            logger.info(f"Searching {venue_code} for paper: {paper.title}")
            
            # Search proceedings for paper ID
            paper_id = self._search_proceedings(venue_code, paper.year, paper.title)
            
            if paper_id:
                # Construct PDF URL
                pdf_url = self._construct_pdf_url(venue_code, paper.year, paper_id)
                
                # Validate URL
                is_valid, file_size = self._validate_pdf_url(pdf_url)
                
                if is_valid:
                    logger.info(f"Found valid PDF at: {pdf_url}")
                    
                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.95,  # High confidence for direct venue links
                        version_info={
                            "venue_code": venue_code,
                            "paper_id": paper_id,
                            "year": paper.year
                        },
                        validation_status="validated",
                        file_size_bytes=file_size,
                        license="ACL Anthology License"
                    )
        
        # No PDF found
        raise Exception(f"Could not find PDF for paper '{paper.title}' in {paper.venue}")