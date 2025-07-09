"""Nature Portfolio adapter using Crossref API."""

import re
import time
from typing import List, Any, Optional
from datetime import datetime

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class NaturePortfolioAdapter(BasePaperoniAdapter):
    """Adapter for Nature Portfolio journals using Crossref API."""
    
    # Mapping of venue names to ISSNs
    VENUE_TO_ISSN = {
        "nature": "1476-4687",
        "scientific-reports": "2045-2322", 
        "nature-communications": "2041-1723",
        "communications-biology": "2399-3642",
        "nature-machine-intelligence": "2522-5839",
        "nature-neuroscience": "1546-1726",
        "nature-methods": "1548-7105",
        "nature-biotechnology": "1546-1696",
        "nature-genetics": "1546-1718",
        "nature-medicine": "1546-170X",
        "nature-physics": "1745-2481",
        "nature-chemistry": "1755-4349",
        "nature-materials": "1476-4660",
        "nature-climate-change": "1758-6798",
        "nature-energy": "2058-7546"
    }
    
    # Journal start years
    JOURNAL_START_YEARS = {
        "nature": 1869,
        "scientific-reports": 2011,
        "nature-communications": 2010,
        "communications-biology": 2018,
        "nature-machine-intelligence": 2019,
        "nature-neuroscience": 1998,
        "nature-methods": 2004,
        "nature-biotechnology": 1996,
        "nature-genetics": 1992,
        "nature-medicine": 1995,
        "nature-physics": 2005,
        "nature-chemistry": 2009,
        "nature-materials": 2002,
        "nature-climate-change": 2011,
        "nature-energy": 2016
    }
    
    def __init__(self, config=None):
        super().__init__("nature_portfolio", config)
        self.base_url = "https://api.crossref.org"
        
    def get_supported_venues(self) -> List[str]:
        """Return all supported Nature Portfolio venues."""
        return list(self.VENUE_TO_ISSN.keys())
    
    def get_available_years(self, venue: str) -> List[int]:
        """Get available years for each venue."""
        venue_lower = venue.lower()
        
        if venue_lower not in self.JOURNAL_START_YEARS:
            return []
            
        start_year = self.JOURNAL_START_YEARS[venue_lower]
        current_year = datetime.now().year
        
        return list(range(start_year, current_year + 1))
    
    def _get_issn(self, venue: str) -> Optional[str]:
        """Get ISSN for a given venue."""
        return self.VENUE_TO_ISSN.get(venue.lower())
        
    def _create_paperoni_scraper(self):
        """Create HTTP session for Crossref API."""
        # Use the session from base class
        self.session.headers.update({
            'User-Agent': 'ComputeForecast/1.0 (mailto:research@institution.edu)',
            'Accept': 'application/json'
        })
        return self.session
        
    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[SimplePaper]:
        """Use Crossref API to get papers."""
        papers = []
        
        venue_lower = venue.lower()
        issn = self._get_issn(venue_lower)
        
        if not issn:
            self.logger.error(f"Unsupported venue for Nature Portfolio: {venue}")
            return []
            
        try:
            # Ensure session is configured
            self._create_paperoni_scraper()
                
            # Query Crossref for papers from the specified year
            url = f"{self.base_url}/journals/{issn}/works"
            params = {
                'filter': f'from-pub-date:{year}-01-01,until-pub-date:{year}-12-31,type:journal-article',
                'rows': min(self.config.batch_size, 1000),  # Crossref max is 1000
                'sort': 'published',
                'order': 'desc',
                'select': 'DOI,title,author,published-print,published-online,abstract,URL,link,type'
            }
            
            self.logger.info(f"Querying Crossref for {venue} papers from {year}")
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Crossref API error: {response.status_code} - {response.text}")
                
            data = response.json()
            items = data['message']['items']
            total_results = data['message']['total-results']
            
            self.logger.info(f"Found {total_results} total papers, processing {len(items)}")
            
            # Convert Crossref items to SimplePaper objects
            for item in items:
                try:
                    paper = self._convert_to_simple_paper(item, venue, year)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"Failed to parse paper {item.get('DOI', 'unknown')}: {e}")
                    continue
                    
            # Add small delay to be polite to Crossref API
            time.sleep(0.5)
            
        except Exception as e:
            self.logger.error(f"Error fetching Nature Portfolio papers for {venue} {year}: {e}")
            raise
            
        return papers
    
    def _convert_to_simple_paper(self, item: dict, venue: str, year: int) -> Optional[SimplePaper]:
        """Convert Crossref item to SimplePaper."""
        # Skip if not a journal article
        if item.get('type') != 'journal-article':
            return None
            
        # Extract title
        title = item.get('title', [''])[0] if item.get('title') else ''
        if not title:
            return None
            
        # Extract authors
        authors = []
        for author in item.get('author', []):
            given = author.get('given', '')
            family = author.get('family', '')
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
                
        # Extract publication date
        pub_date = item.get('published-print', item.get('published-online', {}))
        if pub_date and pub_date.get('date-parts'):
            date_parts = pub_date['date-parts'][0]
            # Sometimes year might be different from what we queried
            # Use the actual publication year
            if len(date_parts) > 0:
                actual_year = date_parts[0]
            else:
                actual_year = year
        else:
            actual_year = year
            
        # Extract abstract
        abstract = self._clean_abstract(item.get('abstract', ''))
        
        # Extract PDF URLs if available
        pdf_urls = self._extract_pdf_urls(item)
        
        # Paper URL
        doi = item.get('DOI', '')
        paper_url = item.get('URL', f"https://doi.org/{doi}" if doi else '')
        
        return SimplePaper(
            title=title,
            authors=authors,
            venue=venue.upper().replace('-', ' '),
            year=actual_year,
            abstract=abstract,
            pdf_urls=pdf_urls,
            paper_id=doi,
            source_scraper=self.source_name,
            source_url=paper_url,
            extraction_confidence=0.95
        )
    
    def _extract_pdf_urls(self, item: dict) -> List[str]:
        """Extract PDF URLs from Crossref link field."""
        pdf_urls = []
        
        # Check for links in the item
        for link in item.get('link', []):
            if link.get('content-type') == 'application/pdf':
                url = link.get('URL', '')
                if url:
                    pdf_urls.append(url)
                    
        return pdf_urls
    
    def _clean_abstract(self, abstract: str) -> str:
        """Clean abstract text by removing HTML tags."""
        if not abstract:
            return ""
            
        # Replace closing tags with space to preserve word boundaries
        clean_text = re.sub(r'</[^>]+>', ' ', abstract)
        
        # Remove remaining HTML tags
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # Replace multiple spaces with single space
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Strip leading/trailing whitespace
        clean_text = clean_text.strip()
        
        return clean_text