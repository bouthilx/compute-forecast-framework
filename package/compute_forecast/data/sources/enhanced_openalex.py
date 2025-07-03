"""
Enhanced OpenAlex Client - Supports batch queries and improved error handling  
Real implementation with API integration, retry logic, and error handling
"""

import time
import requests
from typing import List, Optional
from ..models import Paper, Author, APIResponse, ResponseMetadata, APIError
from datetime import datetime
import logging
import re


logger = logging.getLogger(__name__)


class EnhancedOpenAlexClient:
    """Enhanced OpenAlex client with batch support"""
    
    def __init__(self, email: Optional[str] = None):
        self.base_url = "https://api.openalex.org"
        self.email = email
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Default headers (OpenAlex requests polite usage with email)
        self.headers = {
            'User-Agent': 'research-paper-collector/1.0',
        }
        if email:
            self.headers['User-Agent'] += f' (mailto:{email})'
    
    def search_papers(self, query: str, year: int, limit: int = 500, offset: int = 0) -> APIResponse:
        """
        Search papers with enhanced error handling and retry logic
        
        OpenAlex uses different query syntax than Semantic Scholar
        """
        start_time = time.time()
        
        # Convert query to OpenAlex filter format if needed
        oa_query = self._convert_to_openalex_query(query, year)
        
        # Construct API URL and parameters
        url = f"{self.base_url}/works"
        params = {
            'filter': oa_query,
            'per-page': min(limit, 200),  # OpenAlex limit is 200 per request
            'page': (offset // min(limit, 200)) + 1,  # Convert offset to page
            'select': 'id,title,authorships,primary_location,publication_year,cited_by_count,abstract_inverted_index,doi'
        }
        
        # Attempt request with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response_time_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return self._parse_successful_response(response, query, response_time_ms)
                elif response.status_code == 429:
                    return self._handle_rate_limit(response, query, response_time_ms)
                elif response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"OpenAlex server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        return self._handle_server_error(response, query, response_time_ms)
                else:
                    return self._handle_client_error(response, query, response_time_ms)
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"OpenAlex request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_timeout_error(query, (time.time() - start_time) * 1000)
                    
            except requests.exceptions.RequestException as e:
                return self._handle_network_error(e, query, (time.time() - start_time) * 1000)
        
        return self._handle_max_retries_exceeded(query, (time.time() - start_time) * 1000)
    
    def search_venue_batch(self, venues: List[str], year: int, limit: int = 500) -> APIResponse:
        """
        Search multiple venues using OpenAlex filter syntax
        
        OpenAlex uses: venues.display_name:venue1|venue2|venue3
        """
        # Create venue filter using pipe separator for OR
        venue_filter = "|".join(venues)
        oa_query = f"venues.display_name:{venue_filter},publication_year:{year}"
        
        # Use regular search_papers method with OpenAlex filter
        return self.search_papers(oa_query, year, limit=limit)
    
    def _convert_to_openalex_query(self, query: str, year: int) -> str:
        """Convert generic query to OpenAlex filter format"""
        # If already in OpenAlex format, use as-is
        if 'venues.display_name:' in query or 'publication_year:' in query:
            return query
        
        # Simple conversion for venue:"X" format to venues.display_name:X
        if 'venue:"' in query:
            # Extract venue names from venue:"Name" patterns
            venue_pattern = r'venue:"([^"]+)"'
            venues = re.findall(venue_pattern, query)
            if venues:
                venue_filter = "|".join(venues)
                return f"venues.display_name:{venue_filter},publication_year:{year}"
        
        # Fallback: use as search string
        return f"default.search:{query},publication_year:{year}"
    
    def _parse_successful_response(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Parse successful OpenAlex API response into Paper objects"""
        try:
            data = response.json()
            papers = []
            
            for item in data.get('results', []):
                try:
                    # Parse authors from authorships
                    authors = []
                    for authorship in item.get('authorships', []):
                        author_info = authorship.get('author', {})
                        authors.append(Author(
                            name=author_info.get('display_name', ''),
                            author_id=author_info.get('id', '').replace('https://openalex.org/', '') if author_info.get('id') else ''
                        ))
                    
                    # Extract venue from primary_location
                    venue = ''
                    primary_location = item.get('primary_location', {})
                    if primary_location and primary_location.get('source'):
                        venue = primary_location['source'].get('display_name', '')
                    
                    # Reconstruct abstract from inverted index
                    abstract = self._reconstruct_abstract(item.get('abstract_inverted_index', {}))
                    
                    # Extract OpenAlex ID
                    openalex_id = item.get('id', '').replace('https://openalex.org/', '') if item.get('id') else None
                    
                    # Extract DOI
                    doi = item.get('doi', '').replace('https://doi.org/', '') if item.get('doi') else ''
                    
                    # Create Paper object
                    paper = Paper(
                        title=item.get('title', ''),
                        authors=authors,
                        venue=venue,
                        year=item.get('publication_year', 0),
                        citations=item.get('cited_by_count', 0),
                        abstract=abstract,
                        openalex_id=openalex_id,
                        doi=doi,
                        collection_source="openalex",
                        collection_timestamp=datetime.now()
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse paper from OpenAlex response: {e}")
                    continue
            
            # Get metadata from response
            meta = data.get('meta', {})
            metadata = ResponseMetadata(
                total_results=meta.get('count', len(papers)),
                returned_count=len(papers),
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="openalex",
                timestamp=datetime.now()
            )
            
            return APIResponse(
                success=True,
                papers=papers,
                metadata=metadata,
                errors=[]
            )
            
        except Exception as e:
            error = APIError(
                error_type="response_parsing_error",
                message=f"Failed to parse OpenAlex response: {str(e)}",
                timestamp=datetime.now()
            )
            
            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="openalex",
                timestamp=datetime.now()
            )
            
            return APIResponse(
                success=False,
                papers=[],
                metadata=metadata,
                errors=[error]
            )
    
    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """Reconstruct abstract text from OpenAlex inverted index"""
        if not inverted_index:
            return ""
        
        try:
            # Create list to hold words in correct positions
            max_position = max(max(positions) for positions in inverted_index.values() if positions)
            abstract_words = [''] * (max_position + 1)
            
            # Place each word in correct positions
            for word, positions in inverted_index.items():
                for pos in positions:
                    if pos < len(abstract_words):
                        abstract_words[pos] = word
            
            # Join words and clean up
            abstract = ' '.join(word for word in abstract_words if word)
            return abstract
            
        except Exception as e:
            logger.warning(f"Failed to reconstruct abstract from inverted index: {e}")
            return ""
    
    # Error handling methods (similar to Semantic Scholar client)
    def _handle_rate_limit(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle rate limit response (429)"""
        error = APIError(
            error_type="rate_limit_exceeded",
            message="Rate limit exceeded for OpenAlex API",
            status_code=429,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_server_error(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle server errors (5xx)"""
        error = APIError(
            error_type="server_error",
            message=f"OpenAlex server error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_client_error(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle client errors (4xx)"""
        error = APIError(
            error_type="client_error",
            message=f"OpenAlex client error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_timeout_error(self, query: str, response_time_ms: float) -> APIResponse:
        """Handle request timeout"""
        error = APIError(
            error_type="request_timeout",
            message="OpenAlex request timed out",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_network_error(self, exception: Exception, query: str, response_time_ms: float) -> APIResponse:
        """Handle network/connection errors"""
        error = APIError(
            error_type="network_error",
            message=f"OpenAlex network error: {str(exception)}",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_max_retries_exceeded(self, query: str, response_time_ms: float) -> APIResponse:
        """Handle case where max retries was exceeded"""
        error = APIError(
            error_type="max_retries_exceeded",
            message=f"OpenAlex maximum retries ({self.max_retries}) exceeded",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="openalex",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])