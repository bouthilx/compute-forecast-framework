"""AAAI (Association for the Advancement of Artificial Intelligence) PDF collector."""

import logging
import re
import time
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from urllib.parse import urljoin

import requests
from rapidfuzz import fuzz
from rapidfuzz import process
from bs4 import BeautifulSoup

from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper

logger = logging.getLogger(__name__)


class AAICollector(BasePDFCollector):
    """Collector for AAAI conference papers."""
    
    # Class constants
    FUZZY_MATCH_THRESHOLD = 85
    REQUEST_TIMEOUT = 30
    CONFIDENCE_SCORE = 0.95
    
    def __init__(self):
        """Initialize AAAI collector."""
        super().__init__("aaai")
        self.base_url = "https://ojs.aaai.org"
        self.proceedings_path = "/index.php/AAAI"
        self.search_path = "/index.php/AAAI/search/search"
        
        # Cache for search results and proceedings
        self._search_cache = {}
        self._issue_cache = {}
        
        # Conference name to AAAI mapping
        self.conference_mapping = {
            "Thirty-Ninth": 39,
            "Thirty-Eighth": 38,
            "Thirty-Seventh": 37,
            "Thirty-Sixth": 36,
            "Thirty-Fifth": 35,
            "Thirty-Fourth": 34,
            "Thirty-Third": 33,
            "Thirty-Second": 32,
            "Thirty-First": 31,
            "Thirtieth": 30,
        }
        
        # Year to conference edition mapping (estimated)
        self.year_to_edition = {
            2025: 39,
            2024: 38,
            2023: 37,
            2022: 36,
            2021: 35,
            2020: 34,
            2019: 33,
            2018: 32,
            2017: 31,
            2016: 30,
        }
        
        # Configure timeout for HTTP requests
        self.request_timeout = self.REQUEST_TIMEOUT
        
        # Rate limiting
        self.request_delay = 0.5  # Delay between requests in seconds
        self.last_request_time = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request with rate limiting and retry logic.
        
        Args:
            url: URL to request
            params: Optional query parameters
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                self.last_request_time = time.time()
                return response
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
        
        raise last_exception
    
    def _search_by_title(self, title: str, year: int) -> Optional[Tuple[str, str]]:
        """Search for paper by title using AAAI search.
        
        Args:
            title: Paper title to search for
            year: Publication year
            
        Returns:
            Tuple of (article_id, pdf_id) or None if not found
        """
        cache_key = f"{title}:{year}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        try:
            # URL encode the query
            search_url = urljoin(self.base_url, self.search_path)
            params = {"query": title}
            
            response = self._make_request(search_url, params=params)
            
            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all article results
            articles = soup.find_all('article', class_='obj_article_summary')
            
            if not articles:
                logger.debug(f"No search results found for '{title}'")
                return None
            
            # Extract article data
            candidates = []
            for article in articles:
                # Get title
                title_elem = article.find('h3', class_='title')
                if not title_elem:
                    continue
                    
                article_title = title_elem.get_text(strip=True)
                
                # Get article link
                link_elem = title_elem.find('a')
                if not link_elem or 'href' not in link_elem.attrs:
                    continue
                
                article_url = link_elem['href']
                
                # Extract article ID from URL
                match = re.search(r'/article/view/(\d+)', article_url)
                if not match:
                    continue
                    
                article_id = match.group(1)
                
                # Check if it's from the correct year (if year info available)
                year_elem = article.find('div', class_='published')
                if year_elem:
                    year_text = year_elem.get_text()
                    if str(year) not in year_text:
                        continue
                
                candidates.append((article_id, article_title))
            
            if not candidates:
                logger.debug(f"No candidates found for '{title}' in year {year}")
                return None
            
            # Fuzzy match to find best candidate
            titles = [c[1] for c in candidates]
            best_match = process.extractOne(
                title,
                titles,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=self.FUZZY_MATCH_THRESHOLD
            )
            
            if best_match:
                matched_title, score, idx = best_match
                article_id = candidates[idx][0]
                logger.info(f"Found paper '{title}' as '{matched_title}' (score: {score}) -> article {article_id}")
                
                # Now fetch the article page to get PDF ID
                pdf_id = self._get_pdf_id_from_article(article_id)
                if pdf_id:
                    result = (article_id, pdf_id)
                    self._search_cache[cache_key] = result
                    return result
            
            logger.warning(f"No match found for '{title}' in search results")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for paper '{title}': {e}")
            return None
    
    def _get_pdf_id_from_article(self, article_id: str) -> Optional[str]:
        """Extract PDF ID from article page.
        
        Args:
            article_id: Article ID
            
        Returns:
            PDF ID or None if not found
        """
        try:
            article_url = f"{self.base_url}{self.proceedings_path}/article/view/{article_id}"
            response = self._make_request(article_url)
            
            # Look for PDF download link
            match = re.search(r'/article/download/\d+/(\d+)', response.text)
            if match:
                return match.group(1)
            
            # Alternative pattern
            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_link = soup.find('a', class_='obj_galley_link pdf')
            if pdf_link and 'href' in pdf_link.attrs:
                match = re.search(r'/(\d+)/?$', pdf_link['href'])
                if match:
                    return match.group(1)
            
            logger.warning(f"Could not find PDF ID for article {article_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting PDF ID for article {article_id}: {e}")
            return None
    
    def _search_by_authors(self, authors: List[str], title: str, year: int) -> Optional[Tuple[str, str]]:
        """Search for paper by authors as fallback.
        
        Args:
            authors: List of author names
            title: Paper title for verification
            year: Publication year
            
        Returns:
            Tuple of (article_id, pdf_id) or None if not found
        """
        if not authors:
            return None
            
        # Try searching with first author's last name
        first_author = authors[0].strip()
        last_name = first_author.split()[-1] if first_author else None
        
        if not last_name:
            return None
            
        try:
            search_url = urljoin(self.base_url, self.search_path)
            params = {"authors": last_name}
            
            response = self._make_request(search_url, params=params)
            
            # Parse and look for matching paper
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article', class_='obj_article_summary')
            
            for article in articles:
                title_elem = article.find('h3', class_='title')
                if not title_elem:
                    continue
                    
                article_title = title_elem.get_text(strip=True)
                
                # Check title similarity
                similarity = fuzz.token_sort_ratio(title, article_title)
                if similarity >= self.FUZZY_MATCH_THRESHOLD:
                    link_elem = title_elem.find('a')
                    if link_elem and 'href' in link_elem.attrs:
                        match = re.search(r'/article/view/(\d+)', link_elem['href'])
                        if match:
                            article_id = match.group(1)
                            pdf_id = self._get_pdf_id_from_article(article_id)
                            if pdf_id:
                                return (article_id, pdf_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching by authors: {e}")
            return None
    
    def _construct_pdf_url(self, article_id: str, pdf_id: str) -> str:
        """Construct PDF URL from article and PDF IDs.
        
        Args:
            article_id: Article ID
            pdf_id: PDF ID
            
        Returns:
            Full PDF URL
        """
        return f"{self.base_url}{self.proceedings_path}/article/download/{article_id}/{pdf_id}"
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            ValueError: If PDF cannot be discovered
        """
        # First try searching by title
        result = self._search_by_title(paper.title, paper.year)
        
        # If not found, try searching by authors
        if not result and paper.authors:
            author_names = [author.name for author in paper.authors]
            result = self._search_by_authors(author_names, paper.title, paper.year)
        
        if not result:
            raise ValueError(f"Paper not found in AAAI proceedings: {paper.title}")
        
        article_id, pdf_id = result
        pdf_url = self._construct_pdf_url(article_id, pdf_id)
        
        # Create PDF record
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=pdf_url,
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=self.CONFIDENCE_SCORE,
            version_info={
                "article_id": article_id,
                "pdf_id": pdf_id,
                "venue": paper.venue,
                "year": paper.year,
                "conference_edition": self.year_to_edition.get(paper.year, "unknown")
            },
            validation_status="verified"
        )