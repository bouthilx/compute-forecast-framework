import requests
import time
from typing import List, Dict, Optional, Any
import logging
from requests.exceptions import ConnectionError, Timeout, RequestException

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper
from ....utils.profiling import profile_operation

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


class SemanticScholarSource(BaseConsolidationSource):
    """Semantic Scholar consolidation source"""
    
    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()
        
        # Set optimal batch sizes for Semantic Scholar
        if config.find_batch_size is None:
            config.find_batch_size = 500  # API supports up to 500
        if config.enrich_batch_size is None:
            config.enrich_batch_size = 500  # API supports up to 500
            
        # Override rate limit based on API key presence
        if config.api_key:
            # With API key: introductory rate limit
            config.rate_limit = 1.0  # 1 request per second
        else:
            # Without API key: be conservative with shared pool
            # Unauthenticated users share 5,000 requests/5 minutes
            # Be very conservative to avoid 429 errors
            config.rate_limit = 0.1  # 1 request per 10 seconds
            
        super().__init__("semantic_scholar", config)
        self.base_url = "https://api.semanticscholar.org/v1"
        self.graph_url = "https://api.semanticscholar.org/graph/v1"
        
        self.headers = {}
        if self.config.api_key:
            self.headers["x-api-key"] = self.config.api_key
    
    @retry_on_connection_error(max_retries=3, backoff_factor=2, initial_delay=1)
    def _make_get_request(self, url: str, params: dict, headers: dict, timeout: int = 30) -> requests.Response:
        """Make GET request with retry logic for connection errors."""
        return requests.get(url, params=params, headers=headers, timeout=timeout)
    
    @retry_on_connection_error(max_retries=3, backoff_factor=2, initial_delay=1)
    def _make_post_request(self, url: str, json: dict, headers: dict, params: dict = None, timeout: int = 30) -> requests.Response:
        """Make POST request with retry logic for connection errors."""
        return requests.post(url, json=json, headers=headers, params=params, timeout=timeout)
            
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers using multiple identifiers"""
        mapping = {}
        
        # Try to match by existing Semantic Scholar ID
        for paper in papers:
            if paper.paper_id and paper.paper_id.startswith("SS:"):
                mapping[paper.paper_id] = paper.paper_id[3:]
                continue
                
        # Batch lookup by DOI and ArXiv ID
        id_batch = []
        id_to_paper = {}
        
        for paper in papers:
            if paper.paper_id in mapping:
                continue
                
            # Collect all available IDs (Semantic Scholar can match any)
            if paper.doi:
                id_batch.append(f"DOI:{paper.doi}")
                id_to_paper[f"DOI:{paper.doi}"] = paper.paper_id
            if paper.arxiv_id:
                id_batch.append(f"ARXIV:{paper.arxiv_id}")
                id_to_paper[f"ARXIV:{paper.arxiv_id}"] = paper.paper_id
            # Note: OpenAlex IDs are not directly supported by Semantic Scholar
            # We'd need to map them through DOI or other identifiers
                
        if id_batch:
            # Use paper batch endpoint
            with profile_operation('id_batch_lookup', source=self.name, count=len(id_batch)) as prof:
                self._rate_limit()
                
                # Track API response time separately
                api_start = time.time()
                response = self._make_post_request(
                    f"{self.graph_url}/paper/batch",
                    json={"ids": id_batch},  # Already formatted with prefixes
                    headers=self.headers,
                    params={"fields": "paperId,externalIds"},
                    timeout=30  # Add timeout
                )
                api_time = time.time() - api_start
                self.api_calls += 1
                
                if prof:
                    prof.metadata['api_response_time'] = api_time
                    prof.metadata['status_code'] = response.status_code
                
                if response.status_code == 200:
                    matches_found = 0
                    with profile_operation('parse_id_response', source=self.name):
                        for item in response.json():
                            if item and "paperId" in item:
                                ext_ids = item.get("externalIds", {})
                                
                                # Check DOI match
                                doi = ext_ids.get("DOI")
                                if doi and f"DOI:{doi}" in id_to_paper:
                                    mapping[id_to_paper[f"DOI:{doi}"]] = item["paperId"]
                                    matches_found += 1
                                
                                # Check ArXiv match
                                arxiv = ext_ids.get("ArXiv")
                                if arxiv and f"ARXIV:{arxiv}" in id_to_paper:
                                    mapping[id_to_paper[f"ARXIV:{arxiv}"]] = item["paperId"]
                                    matches_found += 1
                    
                    if prof:
                        prof.metadata['matches_found'] = matches_found
                        prof.metadata['match_rate'] = matches_found / len(id_batch) if id_batch else 0
                            
        # Fallback: Search by title for remaining papers
        unmapped_count = len([p for p in papers if p.paper_id not in mapping])
        if unmapped_count > 0:
            with profile_operation('title_searches', source=self.name, count=unmapped_count):
                for paper in papers:
                    if paper.paper_id in mapping:
                        continue
                        
                    with profile_operation('title_search_single', source=self.name) as prof:
                        self._rate_limit()
                        query = f'"{paper.title}"'
                        
                        # Track API response time
                        api_start = time.time()
                        response = self._make_get_request(
                            f"{self.graph_url}/paper/search",
                            params={
                                "query": query,
                                "limit": 1,
                                "fields": "paperId,title,year"
                            },
                            headers=self.headers,
                            timeout=30
                        )
                        api_time = time.time() - api_start
                        self.api_calls += 1
                        
                        if prof:
                            prof.metadata['api_response_time'] = api_time
                            prof.metadata['status_code'] = response.status_code
                            prof.metadata['title_length'] = len(paper.title)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("data"):
                                result = data["data"][0]
                                # Verify it's the same paper (title similarity and year)
                                if (self._similar_title(paper.title, result["title"]) and 
                                    result.get("year") == paper.year):
                                    mapping[paper.paper_id] = result["paperId"]
                                    if prof:
                                        prof.metadata['match_found'] = True
                                else:
                                    if prof:
                                        prof.metadata['match_found'] = False
                            else:
                                if prof:
                                    prof.metadata['match_found'] = False
                        
        return mapping
        
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all available fields in a single API call per batch"""
        results = {}
        
        # All fields we want in one request (added corpusId)
        fields = "paperId,title,abstract,citationCount,year,authors,externalIds,corpusId,openAccessPdf,fieldsOfStudy,venue"
        
        # Process in chunks of 500 (API limit)
        for i in range(0, len(source_ids), 500):
            batch = source_ids[i:i+500]
            
            with profile_operation('fetch_batch', source=self.name, batch_size=len(batch)) as prof:
                self._rate_limit()
                
                api_start = time.time()
                response = requests.post(
                    f"{self.graph_url}/paper/batch",
                    json={"ids": batch},
                    headers=self.headers,
                    params={"fields": fields},
                    timeout=30
                )
                api_time = time.time() - api_start
                self.api_calls += 1
                
                if prof:
                    prof.metadata['api_response_time'] = api_time
                    prof.metadata['status_code'] = response.status_code
                
                if response.status_code == 200:
                    with profile_operation('parse_enrichment_response', source=self.name):
                        for item in response.json():
                            if item is None:
                                continue
                                
                            paper_id = item.get("paperId")
                            if not paper_id:
                                continue
                                
                            # Extract all data from single response
                            paper_data = {
                                'citations': item.get('citationCount'),
                                'abstract': item.get('abstract'),
                                'urls': [],
                                'identifiers': [],
                                'authors': item.get('authors', []),
                                'venue': item.get('venue'),
                                'fields_of_study': item.get('fieldsOfStudy', [])
                            }
                            
                            # Add open access PDF URL if available
                            if item.get('openAccessPdf') and item['openAccessPdf'].get('url'):
                                paper_data['urls'].append(item['openAccessPdf']['url'])
                            
                            # Extract all identifiers
                            # Add Semantic Scholar IDs
                            if item.get('paperId'):
                                paper_data['identifiers'].append({
                                    'type': 's2_paper',
                                    'value': item['paperId']
                                })
                            
                            if item.get('corpusId'):
                                paper_data['identifiers'].append({
                                    'type': 's2_corpus',
                                    'value': str(item['corpusId'])
                                })
                            
                            # Extract external identifiers
                            ext_ids = item.get('externalIds', {})
                            id_mappings = {
                                'DOI': 'doi',
                                'ArXiv': 'arxiv',
                                'PubMed': 'pmid',
                                'ACL': 'acl',
                                'MAG': 'mag'
                            }
                            
                            for ext_type, our_type in id_mappings.items():
                                if ext_type in ext_ids:
                                    paper_data['identifiers'].append({
                                        'type': our_type,
                                        'value': ext_ids[ext_type]
                                    })
                                
                            results[paper_id] = paper_data
                    
        return results
        
    def _similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough"""
        # Simple normalization and comparison
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
            
        # Check if one is substring of other (handling subtitles)
        if norm1 in norm2 or norm2 in norm1:
            return True
            
        # Could add more sophisticated matching here
        return False