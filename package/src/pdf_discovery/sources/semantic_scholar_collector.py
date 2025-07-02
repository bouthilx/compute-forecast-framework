"""Semantic Scholar PDF Collector for discovering open access PDFs."""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
import os

import semanticscholar

from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper

logger = logging.getLogger(__name__)

# Module-level constants
SEMANTIC_SCHOLAR_MAX_BATCH_SIZE = 500  # Maximum papers per batch API call
DEFAULT_MAX_RETRIES = 3  # Default number of retries for API failures
CONFIDENCE_SCORE_WITH_IDENTIFIER = 0.9  # Confidence when found via DOI/arXiv/SS ID
CONFIDENCE_SCORE_TITLE_SEARCH = 0.8  # Confidence when found via title search


class SemanticScholarPDFCollector(BasePDFCollector):
    """Collects PDF URLs from Semantic Scholar's openAccessPdf field."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Semantic Scholar PDF collector.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        super().__init__("semantic_scholar")
        
        # API configuration
        self.api_key = api_key or os.getenv('SEMANTIC_SCHOLAR_API_KEY')
        self.api = semanticscholar.SemanticScholar(api_key=self.api_key)
        
        # Batch settings
        self.supports_batch = True
        self.batch_size = SEMANTIC_SCHOLAR_MAX_BATCH_SIZE
        
        # Rate limiting
        # Without API key: 100 requests per 5 minutes = 1 request per 3 seconds
        # With API key: 5000 requests per 5 minutes = 1 request per 0.06 seconds
        self.rate_limit_delay = 0.5 if self.api_key else 3.0
        self.last_request_time = 0
        
        # Retry settings
        self.max_retries = DEFAULT_MAX_RETRIES
        self.retry_delay = 1.0
        
        logger.info(f"Initialized Semantic Scholar PDF collector "
                   f"{'with' if self.api_key else 'without'} API key")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _match_paper_to_response(self, ss_paper: dict, paper_map: Dict[str, Paper]) -> Optional[Paper]:
        """Match a Semantic Scholar response to our original paper.
        
        Args:
            ss_paper: Semantic Scholar API response for a paper
            paper_map: Mapping of identifiers to our Paper objects
            
        Returns:
            The matched Paper object, or None if no match found
        """
        # Direct ID match
        paper_id = ss_paper.get('paperId')
        if paper_id in paper_map:
            return paper_map[paper_id]
        
        # DOI match
        doi = ss_paper.get('doi')
        if doi and f"DOI:{doi}" in paper_map:
            return paper_map[f"DOI:{doi}"]
        
        # arXiv match
        arxiv_id = ss_paper.get('arxivId')
        if arxiv_id and f"ARXIV:{arxiv_id}" in paper_map:
            return paper_map[f"ARXIV:{arxiv_id}"]
        
        return None
    
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
        
        # Try to find paper by various identifiers
        ss_paper = None
        retries = 0
        
        while retries < self.max_retries:
            try:
                # First try direct lookup if we have identifiers
                if hasattr(paper, 'doi') and paper.doi:
                    ss_paper = self.api.get_paper(f"DOI:{paper.doi}")
                elif hasattr(paper, 'arxiv_id') and paper.arxiv_id:
                    ss_paper = self.api.get_paper(f"ARXIV:{paper.arxiv_id}")
                elif hasattr(paper, 'semantic_scholar_id') and paper.semantic_scholar_id:
                    ss_paper = self.api.get_paper(paper.semantic_scholar_id)
                    
                # If no identifiers or lookup returned None, try by title
                if not ss_paper:
                    # Fallback to title search
                    logger.debug(f"Searching by title: {paper.title}")
                    search_results = self.api.search_paper(
                        query=paper.title,
                        limit=5
                    )
                    
                    if search_results:
                        # Handle both dict and list responses
                        if isinstance(search_results, dict) and 'data' in search_results:
                            results_list = search_results['data']
                        elif isinstance(search_results, list):
                            results_list = search_results
                        else:
                            results_list = []
                        
                        # Find best match by title similarity
                        for result in results_list:
                            if result.get('title', '').lower() == paper.title.lower():
                                ss_paper = result
                                break
                        
                        # If no exact match, take first result
                        if not ss_paper and results_list:
                            ss_paper = results_list[0]
                
                break  # Success
                
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to query Semantic Scholar after {self.max_retries} retries: {e}")
                    raise
                
                logger.warning(f"Semantic Scholar API error (retry {retries}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay * retries)
        
        # Extract PDF information
        if not ss_paper:
            raise ValueError(f"Paper not found in Semantic Scholar: {paper.title}")
        
        open_access_pdf = ss_paper.get('openAccessPdf')
        if not open_access_pdf or not open_access_pdf.get('url'):
            raise ValueError(f"No PDF available for paper: {paper.title}")
        
        # Determine confidence based on how we found the paper
        has_identifier = (
            (hasattr(paper, 'doi') and paper.doi) or
            (hasattr(paper, 'arxiv_id') and paper.arxiv_id) or
            (hasattr(paper, 'semantic_scholar_id') and paper.semantic_scholar_id)
        )
        confidence_score = CONFIDENCE_SCORE_WITH_IDENTIFIER if has_identifier else CONFIDENCE_SCORE_TITLE_SEARCH
        
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=open_access_pdf['url'],
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=confidence_score,
            version_info={
                'ss_paper_id': ss_paper.get('paperId'),
                'pdf_status': open_access_pdf.get('status', 'unknown')
            },
            validation_status=open_access_pdf.get('status', 'unknown'),
            file_size_bytes=None,  # SS doesn't provide file size
            license=None  # Could be extracted from status (e.g., GOLD = open access)
        )
    
    def discover_pdfs_batch(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
        """Discover PDFs for multiple papers using batch API.
        
        Args:
            papers: List of papers to discover PDFs for
            
        Returns:
            Dictionary mapping paper_id to PDFRecord for successful discoveries
            
        Example:
            collector = SemanticScholarPDFCollector()
            records = collector.discover_pdfs_batch([paper1, paper2])
        """
        if not papers:
            return {}
        
        logger.info(f"Starting batch PDF discovery for {len(papers)} papers")
        results = {}
        
        # Process in batches of max batch size
        for i in range(0, len(papers), self.batch_size):
            batch = papers[i:i + self.batch_size]
            self._enforce_rate_limit()
            
            try:
                # Collect paper identifiers for batch lookup
                paper_ids = []
                paper_map = {}  # SS ID -> our paper
                
                for paper in batch:
                    # Build list of identifiers to search
                    if hasattr(paper, 'semantic_scholar_id') and paper.semantic_scholar_id:
                        paper_ids.append(paper.semantic_scholar_id)
                        paper_map[paper.semantic_scholar_id] = paper
                    elif hasattr(paper, 'doi') and paper.doi:
                        paper_ids.append(f"DOI:{paper.doi}")
                        paper_map[f"DOI:{paper.doi}"] = paper
                    elif hasattr(paper, 'arxiv_id') and paper.arxiv_id:
                        paper_ids.append(f"ARXIV:{paper.arxiv_id}")
                        paper_map[f"ARXIV:{paper.arxiv_id}"] = paper
                    else:
                        # Can't batch search by title, will need individual lookup
                        continue
                
                if paper_ids:
                    # Batch API call
                    ss_papers = self.api.get_papers(paper_ids)
                    
                    for ss_paper in ss_papers:
                        if not ss_paper:
                            continue
                        
                        # Find our paper using helper method
                        our_paper = self._match_paper_to_response(ss_paper, paper_map)
                        if not our_paper:
                            continue
                        
                        # Extract PDF if available
                        open_access_pdf = ss_paper.get('openAccessPdf')
                        if open_access_pdf and open_access_pdf.get('url'):
                            pdf_record = PDFRecord(
                                paper_id=our_paper.paper_id,
                                pdf_url=open_access_pdf['url'],
                                source=self.source_name,
                                discovery_timestamp=datetime.now(),
                                confidence_score=CONFIDENCE_SCORE_WITH_IDENTIFIER,
                                version_info={
                                    'ss_paper_id': ss_paper.get('paperId'),
                                    'pdf_status': open_access_pdf.get('status', 'unknown')
                                },
                                validation_status=open_access_pdf.get('status', 'unknown'),
                                file_size_bytes=None,
                                license=None
                            )
                            results[our_paper.paper_id] = pdf_record
                
                # Handle papers that couldn't be batched (no identifiers)
                for paper in batch:
                    if paper.paper_id not in results and paper not in paper_map.values():
                        try:
                            pdf_record = self._discover_single(paper)
                            results[paper.paper_id] = pdf_record
                        except Exception as e:
                            logger.debug(f"Failed to discover PDF for {paper.paper_id}: {e}")
                
            except Exception as e:
                logger.error(f"Batch discovery failed: {e}")
                # Fall back to individual discovery for this batch
                for paper in batch:
                    if paper.paper_id not in results:
                        try:
                            pdf_record = self._discover_single(paper)
                            results[paper.paper_id] = pdf_record
                        except Exception as e:
                            logger.debug(f"Failed to discover PDF for {paper.paper_id}: {e}")
        
        logger.info(f"Batch discovery complete: found {len(results)}/{len(papers)} PDFs")
        return results