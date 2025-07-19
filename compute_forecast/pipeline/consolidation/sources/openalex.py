import requests
from typing import List, Dict, Optional, Any
import time
import logging
from requests.exceptions import ConnectionError, Timeout, RequestException

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper
from .title_matcher import TitleMatcher

logger = logging.getLogger(__name__)


def retry_on_connection_error(max_retries=3, backoff_factor=2, initial_delay=1):
    """Decorator to retry requests on connection errors with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, ConnectionResetError, Timeout) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Connection error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Connection error after {max_retries} attempts: {str(e)}")
                except RequestException as e:
                    # For other request exceptions, log but don't retry
                    logger.error(f"Request error: {str(e)}")
                    raise
                    
            # If we've exhausted all retries, raise the last exception
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class OpenAlexSource(BaseConsolidationSource):
    """OpenAlex consolidation source"""
    
    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()
        # Set optimal batch sizes for OpenAlex (limited by URL length)
        if config.find_batch_size is None:
            config.find_batch_size = 50  # URL length limit
        if config.enrich_batch_size is None:
            config.enrich_batch_size = 50  # URL length limit
        super().__init__("openalex", config)
        self.base_url = "https://api.openalex.org"
        
        # Email for polite access
        email = config.api_key  # Using api_key field for email
        self.headers = {"User-Agent": "ConsolidationBot/1.0"}
        if email:
            self.headers["User-Agent"] += f" (mailto:{email})"
            
        # Initialize fuzzy title matcher with conservative settings
        self.title_matcher = TitleMatcher(
            high_confidence_threshold=0.90,  # Conservative for OpenAlex
            medium_confidence_threshold=0.85,
            require_safety_checks=True
        )
    
    @retry_on_connection_error(max_retries=3, backoff_factor=2, initial_delay=1)
    def _make_request(self, url: str, params: dict) -> requests.Response:
        """Make HTTP request with retry logic for connection errors."""
        self._rate_limit()
        response = requests.get(url, params=params, headers=self.headers, timeout=30)
        self.api_calls += 1
        return response
            
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers using OpenAlex search"""
        mapping = {}
        
        # Check for existing OpenAlex IDs
        for paper in papers:
            if paper.openalex_id:
                mapping[paper.paper_id] = paper.openalex_id
                continue
                
        # Batch search by DOI
        dois = []
        doi_to_paper = {}
        
        for paper in papers:
            if paper.paper_id not in mapping and paper.doi:
                dois.append(paper.doi)
                doi_to_paper[paper.doi] = paper.paper_id
                
        if dois:
            # OpenAlex OR filter syntax: doi:value1|value2|value3
            filter_str = "doi:" + "|".join(dois)
            
            try:
                response = self._make_request(
                    f"{self.base_url}/works",
                    params={
                        "filter": filter_str,
                        "per-page": len(dois),
                        "select": "id,doi"
                    }
                )
                
                if response.status_code == 200:
                    for work in response.json().get("results", []):
                        doi = work.get("doi", "").replace("https://doi.org/", "")
                        if doi in doi_to_paper:
                            mapping[doi_to_paper[doi]] = work["id"]
            except Exception as e:
                logger.error(f"Failed to lookup DOIs batch after retries: {str(e)}")
                # Continue with title search for papers not found
                        
        # Search by title for remaining papers
        for paper in papers:
            if paper.paper_id in mapping:
                continue
            
            try:
                response = self._make_request(
                    f"{self.base_url}/works",
                    params={
                        "search": paper.title,
                        "filter": f"publication_year:{paper.year}",
                        "per-page": 1,
                        "select": "id,title,publication_year"
                    }
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    if results:
                        work = results[0]
                        # Verify match using fuzzy matching with year and author info
                        work_year = work.get("publication_year")
                        if self._similar_title(
                            paper.title, 
                            work.get("title", ""),
                            paper.year,
                            work_year
                        ):
                            mapping[paper.paper_id] = work["id"]
            except Exception as e:
                logger.error(f"Failed to lookup paper '{paper.title}' after retries: {str(e)}")
                # Skip this paper and continue with others
                        
        return mapping
        
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all available fields in minimal API calls"""
        results = {}
        
        # Build OR filter for all IDs using correct syntax
        # OpenAlex supports OR within a single filter: openalex:id1|id2|id3
        
        # Select all fields we need in one request
        select_fields = "id,title,abstract_inverted_index,cited_by_count,ids,publication_year,authorships,primary_location,locations,concepts"
        
        # Process in batches (OpenAlex has URL length limits)
        batch_size = self.config.enrich_batch_size or 50
        for i in range(0, len(source_ids), batch_size):
            batch = source_ids[i:i+batch_size]
            
            # Build filter string: openalex:id1|id2|id3
            filter_str = "openalex:" + "|".join(batch)
            
            try:
                response = self._make_request(
                    f"{self.base_url}/works",
                    params={
                        "filter": filter_str,
                        "per-page": len(batch),
                        "select": select_fields
                    }
                )
                
                if response.status_code == 200:
                    for work in response.json().get("results", []):
                        work_id = work.get("id")
                        if not work_id:
                            continue
                        
                        # Extract all data from single response
                        paper_data = {
                            'citations': work.get("cited_by_count", 0),
                            'abstract': None,
                            'urls': [],
                            'identifiers': [],
                            'authors': [],
                            'concepts': work.get('concepts', [])
                        }
                        
                        # Convert inverted index to text
                        inverted = work.get("abstract_inverted_index", {})
                        if inverted:
                            paper_data['abstract'] = self._inverted_to_text(inverted)
                            
                        # Extract author information
                        for authorship in work.get('authorships', []):
                            author_info = {
                                'name': authorship.get('author', {}).get('display_name'),
                                'institutions': [inst.get('display_name') for inst in authorship.get('institutions', [])]
                            }
                            paper_data['authors'].append(author_info)
                            
                        # Extract URLs from locations
                        if work.get('primary_location') and work['primary_location'].get('pdf_url'):
                            paper_data['urls'].append(work['primary_location']['pdf_url'])
                            
                        # Check other locations for open access URLs
                        for location in work.get('locations', []):
                            if location.get('pdf_url') and location['pdf_url'] not in paper_data['urls']:
                                paper_data['urls'].append(location['pdf_url'])
                        
                        # Extract all identifiers
                        # Add OpenAlex ID
                        if work_id:
                            paper_data['identifiers'].append({
                                'type': 'openalex',
                                'value': work_id
                            })
                        
                        # Extract other identifiers from 'ids' field
                        ids = work.get('ids', {})
                        
                        # Map OpenAlex identifier types to our types
                        id_mappings = {
                            'doi': 'doi',
                            'pmid': 'pmid',
                            'mag': 'mag'  # OpenAlex includes MAG IDs
                        }
                        
                        for oa_type, our_type in id_mappings.items():
                            if oa_type in ids and ids[oa_type]:
                                # Handle DOI format (OpenAlex returns full URL)
                                value = ids[oa_type]
                                if our_type == 'doi' and value.startswith('https://doi.org/'):
                                    value = value.replace('https://doi.org/', '')
                                
                                paper_data['identifiers'].append({
                                    'type': our_type,
                                    'value': str(value)
                                })
                                
                        # Use the work_id as key to match what find_papers returned
                        results[work_id] = paper_data
            except Exception as e:
                logger.error(f"Failed to fetch enrichment data for batch after retries: {str(e)}")
                # Continue with next batch
                        
        return results
        
    def _inverted_to_text(self, inverted_index: Dict[str, List[int]]) -> str:
        """Convert OpenAlex inverted index to text"""
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        return " ".join(word for _, word in words)
        
    def _similar_title(
        self, 
        title1: str, 
        title2: str,
        year1: Optional[int] = None,
        year2: Optional[int] = None,
        authors1: Optional[List] = None,
        authors2: Optional[List] = None
    ) -> bool:
        """Check if two titles are similar using fuzzy matching."""
        return self.title_matcher.is_similar(
            title1, title2, 
            year1=year1, 
            year2=year2,
            authors1=authors1,
            authors2=authors2,
            min_confidence="high_confidence"  # Conservative threshold
        )