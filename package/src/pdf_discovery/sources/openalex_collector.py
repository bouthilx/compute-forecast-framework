"""OpenAlex PDF Collector for discovering open access PDFs."""

import logging
import time
import os
from typing import Dict, List, Optional
from datetime import datetime
import requests

from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper

logger = logging.getLogger(__name__)

# Module-level constants
OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_MAX_BATCH_SIZE = 200  # Maximum works per request
DEFAULT_MAX_RETRIES = 3
CONFIDENCE_SCORE_WITH_IDENTIFIER = 0.9  # Found via DOI or other identifier
CONFIDENCE_SCORE_TITLE_SEARCH = 0.8  # Found via title search
MILA_INSTITUTION_ID = "https://openalex.org/I162448124"  # Mila's OpenAlex ID


class OpenAlexPDFCollector(BasePDFCollector):
    """Collects PDF URLs from OpenAlex's open access fields."""
    
    def __init__(self, email: Optional[str] = None, mila_institution_id: Optional[str] = None):
        """Initialize the OpenAlex PDF collector.
        
        Args:
            email: Email for polite API access (recommended by OpenAlex)
            mila_institution_id: OpenAlex institution ID for Mila filtering
        """
        super().__init__("openalex")
        
        # API configuration
        self.email = email or os.getenv('OPENALEX_EMAIL')
        self.base_url = OPENALEX_BASE_URL
        
        # Set up headers with User-Agent
        self.headers = {
            'User-Agent': 'PDF-Discovery-Framework/1.0'
        }
        if self.email:
            self.headers['User-Agent'] += f' (mailto:{self.email})'
        
        # Batch settings
        self.supports_batch = True
        self.batch_size = OPENALEX_MAX_BATCH_SIZE
        
        # Rate limiting - OpenAlex recommends 10 requests/second with polite access
        self.rate_limit_delay = 0.1 if self.email else 1.0
        self.last_request_time = 0
        
        # Retry settings
        self.max_retries = DEFAULT_MAX_RETRIES
        self.retry_delay = 1.0
        
        # Institution filtering
        self.mila_institution_id = mila_institution_id or MILA_INSTITUTION_ID
        
        logger.info(f"Initialized OpenAlex PDF collector "
                   f"{'with' if self.email else 'without'} email for polite access")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _build_filter_query(self, paper: Paper) -> str:
        """Build OpenAlex filter query for paper search.
        
        Args:
            paper: Paper to search for
            
        Returns:
            OpenAlex filter string
        """
        filters = []
        
        # Try DOI first if available
        if hasattr(paper, 'doi') and paper.doi:
            # OpenAlex expects DOI without prefix
            doi = paper.doi.replace('https://doi.org/', '')
            filters.append(f'doi:{doi}')
        else:
            # Fall back to title search
            # Escape special characters and use title.search for fuzzy matching
            title = paper.title.replace('"', '\\"')
            filters.append(f'title.search:"{title}"')
        
        return ','.join(filters)
    
    def _extract_pdf_url(self, work: dict) -> Optional[str]:
        """Extract best available PDF URL from OpenAlex work.
        
        Args:
            work: OpenAlex work object
            
        Returns:
            PDF URL if available, None otherwise
        """
        # Prefer best_oa_location if available
        best_oa = work.get('best_oa_location')
        if best_oa and best_oa.get('pdf_url'):
            return best_oa['pdf_url']
        
        # Fall back to primary_location
        primary = work.get('primary_location', {})
        if primary.get('is_oa') and primary.get('pdf_url'):
            return primary['pdf_url']
        
        # Check all locations as last resort
        locations = work.get('locations', [])
        for location in locations:
            if location.get('is_oa') and location.get('pdf_url'):
                return location['pdf_url']
        
        return None
    
    def _extract_license(self, work: dict) -> Optional[str]:
        """Extract license information from OpenAlex work.
        
        Args:
            work: OpenAlex work object
            
        Returns:
            License string if available
        """
        # Check best_oa_location first
        best_oa = work.get('best_oa_location')
        if best_oa and best_oa.get('license'):
            return best_oa['license']
        
        # Check primary_location
        primary = work.get('primary_location', {})
        if primary.get('license'):
            return primary['license']
        
        return None
    
    def _has_mila_author(self, work: dict) -> bool:
        """Check if paper has at least one Mila-affiliated author.
        
        Args:
            work: OpenAlex work object
            
        Returns:
            True if has Mila author
        """
        if not self.mila_institution_id:
            return False
        
        authorships = work.get('authorships', [])
        for authorship in authorships:
            institutions = authorship.get('institutions', [])
            for institution in institutions:
                if institution.get('id') == self.mila_institution_id:
                    return True
        
        return False
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            ValueError: If no PDF is found
            Exception: For API errors after retries
        """
        self._enforce_rate_limit()
        
        # Build search query
        filter_query = self._build_filter_query(paper)
        
        # API parameters
        params = {
            'filter': filter_query,
            'per-page': 10,  # Small limit for single search
            'select': 'id,title,doi,best_oa_location,primary_location,locations,authorships'
        }
        
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.get(
                    f"{self.base_url}/works",
                    params=params,
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if not results:
                        raise ValueError(f"Paper not found in OpenAlex: {paper.title}")
                    
                    # Find best matching work (first result for now)
                    work = results[0]
                    
                    # Extract PDF URL
                    pdf_url = self._extract_pdf_url(work)
                    if not pdf_url:
                        raise ValueError(f"No PDF available for paper: {paper.title}")
                    
                    # Determine confidence based on search method
                    has_identifier = hasattr(paper, 'doi') and paper.doi
                    confidence_score = (
                        CONFIDENCE_SCORE_WITH_IDENTIFIER if has_identifier 
                        else CONFIDENCE_SCORE_TITLE_SEARCH
                    )
                    
                    # Extract additional metadata
                    openalex_id = work.get('id', '')
                    license_info = self._extract_license(work)
                    has_mila_author = self._has_mila_author(work)
                    
                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=confidence_score,
                        version_info={
                            'openalex_id': openalex_id,
                            'has_mila_author': has_mila_author
                        },
                        validation_status='available',
                        file_size_bytes=None,
                        license=license_info
                    )
                
                elif response.status_code == 429:
                    # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"OpenAlex rate limit hit, retry after {retry_after}s")
                    raise Exception(f"OpenAlex rate limit: retry after {retry_after}s")
                
                elif response.status_code >= 500:
                    # Server error - retry
                    retries += 1
                    if retries >= self.max_retries:
                        raise Exception(f"OpenAlex server error: {response.status_code}")
                    
                    wait_time = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(f"OpenAlex server error {response.status_code}, "
                                 f"retry {retries}/{self.max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                else:
                    # Client error
                    raise Exception(f"OpenAlex API error: {response.status_code} - {response.text}")
                
            except requests.exceptions.RequestException as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"OpenAlex request failed after {self.max_retries} retries: {e}")
                    raise
                
                wait_time = self.retry_delay * (2 ** (retries - 1))
                logger.warning(f"OpenAlex request error (retry {retries}/{self.max_retries}): {e}")
                time.sleep(wait_time)
        
        raise Exception(f"Failed to query OpenAlex after {self.max_retries} retries")
    
    def discover_pdfs_batch(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
        """Discover PDFs for multiple papers using batch API.
        
        Args:
            papers: List of papers to discover PDFs for
            
        Returns:
            Dictionary mapping paper_id to PDFRecord for successful discoveries
        """
        if not papers:
            return {}
        
        logger.info(f"Starting batch PDF discovery for {len(papers)} papers")
        results = {}
        
        # Process in batches
        for i in range(0, len(papers), self.batch_size):
            batch = papers[i:i + self.batch_size]
            self._enforce_rate_limit()
            
            # Build batch filter query
            doi_filters = []
            doi_to_paper = {}  # Map DOI to paper for result matching
            title_papers = []  # Papers without DOI
            
            for paper in batch:
                if hasattr(paper, 'doi') and paper.doi:
                    doi = paper.doi.replace('https://doi.org/', '')
                    doi_filters.append(f'doi:{doi}')
                    doi_to_paper[doi] = paper
                else:
                    title_papers.append(paper)
            
            # First, batch query by DOIs if any
            if doi_filters:
                # OpenAlex uses | for OR within a single filter
                filter_query = '|'.join(doi_filters)  
                params = {
                    'filter': filter_query,  # Already includes doi: prefix for each DOI
                    'per-page': len(doi_filters),
                    'select': 'id,title,doi,best_oa_location,primary_location,locations,authorships'
                }
                
                try:
                    response = requests.get(
                        f"{self.base_url}/works",
                        params=params,
                        headers=self.headers,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        for work in data.get('results', []):
                            # Match work to paper by DOI
                            work_doi = work.get('doi', '').replace('https://doi.org/', '')
                            if work_doi in doi_to_paper:
                                paper = doi_to_paper[work_doi]
                                pdf_url = self._extract_pdf_url(work)
                                
                                if pdf_url:
                                    pdf_record = PDFRecord(
                                        paper_id=paper.paper_id,
                                        pdf_url=pdf_url,
                                        source=self.source_name,
                                        discovery_timestamp=datetime.now(),
                                        confidence_score=CONFIDENCE_SCORE_WITH_IDENTIFIER,
                                        version_info={
                                            'openalex_id': work.get('id', ''),
                                            'has_mila_author': self._has_mila_author(work)
                                        },
                                        validation_status='available',
                                        file_size_bytes=None,
                                        license=self._extract_license(work)
                                    )
                                    results[paper.paper_id] = pdf_record
                
                except Exception as e:
                    logger.error(f"Batch DOI query failed: {e}")
            
            # Process papers without DOI individually
            for paper in title_papers:
                try:
                    pdf_record = self._discover_single(paper)
                    results[paper.paper_id] = pdf_record
                except Exception as e:
                    logger.debug(f"Failed to discover PDF for {paper.paper_id}: {e}")
        
        logger.info(f"Batch discovery complete: found {len(results)}/{len(papers)} PDFs")
        return results