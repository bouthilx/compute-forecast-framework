"""
Enhanced Crossref Client - Supports batch queries and improved error handling
Simplified real implementation with API integration and error handling
"""

import time
import requests
from typing import List, Optional, Dict, Any
from ..models import Paper, Author, APIResponse, ResponseMetadata, APIError
from datetime import datetime
import logging
import re


logger = logging.getLogger(__name__)


class EnhancedCrossrefClient:
    """Enhanced Crossref client with batch support"""
    
    def __init__(self, email: Optional[str] = None):
        self.base_url = "https://api.crossref.org"
        self.email = email
        self.max_retries = 3
        self.retry_delay = 2.0  # Crossref prefers slower requests
        
        # Default headers (Crossref strongly recommends including email)
        self.headers = {
            'User-Agent': 'research-paper-collector/1.0'
        }
        if email:
            self.headers['User-Agent'] += f' (mailto:{email})'
    
    def search_papers(self, query: str, year: int, limit: int = 500, offset: int = 0) -> APIResponse:
        """
        Search papers with enhanced error handling and retry logic
        
        Crossref uses different query syntax and has more conservative rate limits
        """
        start_time = time.time()
        
        # Convert query to Crossref format if needed
        cr_query = self._convert_to_crossref_query(query, year)
        
        # Construct API URL and parameters
        url = f"{self.base_url}/works"
        params = {
            'query': cr_query,
            'rows': min(limit, 1000),  # Crossref limit is 1000 per request
            'offset': offset,
            'select': 'DOI,title,author,container-title,published-print,is-referenced-by-count,abstract'
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
                        logger.warning(f"Crossref server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        return self._handle_server_error(response, query, response_time_ms)
                else:
                    return self._handle_client_error(response, query, response_time_ms)
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Crossref request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_timeout_error(query, (time.time() - start_time) * 1000)
                    
            except requests.exceptions.RequestException as e:
                return self._handle_network_error(e, query, (time.time() - start_time) * 1000)
        
        return self._handle_max_retries_exceeded(query, (time.time() - start_time) * 1000)
    
    def search_venue_batch(self, venues: List[str], year: int, limit: int = 500) -> APIResponse:
        """
        Search multiple venues using Crossref query syntax
        
        Crossref doesn't support OR queries as cleanly, so we construct a complex query
        """
        # Create venue query for Crossref format
        venue_queries = [f'container-title:"{venue}"' for venue in venues]
        full_query = f"({' OR '.join(venue_queries)}) AND published:{year}"
        
        # Use regular search_papers method
        return self.search_papers(full_query, year, limit=limit)
    
    def _convert_to_crossref_query(self, query: str, year: int) -> str:
        """Convert generic query to Crossref format"""
        # If already in Crossref format, use as-is
        if 'container-title:' in query or 'published:' in query:
            return query
        
        # Simple conversion for venue:"X" format to container-title:"X"
        if 'venue:"' in query:
            converted = query.replace('venue:"', 'container-title:"')
            return f"{converted} AND published:{year}"
        
        # Fallback: use as general query with year
        return f"{query} AND published:{year}"
    
    def _parse_successful_response(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Parse successful Crossref API response into Paper objects"""
        try:
            data = response.json()
            papers = []
            
            items = data.get('message', {}).get('items', [])
            
            for item in items:
                try:
                    # Parse authors
                    authors = []
                    for author_data in item.get('author', []):
                        if 'given' in author_data and 'family' in author_data:
                            name = f"{author_data['given']} {author_data['family']}"
                        elif 'name' in author_data:
                            name = author_data['name']
                        else:
                            continue
                        
                        authors.append(Author(name=name))
                    
                    # Extract venue (container-title)
                    venue = ''
                    container_titles = item.get('container-title', [])
                    if container_titles:
                        venue = container_titles[0]
                    
                    # Extract year from published-print
                    year = 0
                    published = item.get('published-print', {}).get('date-parts', [[]])
                    if published and published[0]:
                        year = published[0][0]
                    
                    # Clean abstract (remove JATS XML tags)
                    abstract = item.get('abstract', '')
                    if abstract:
                        abstract = self._clean_jats_abstract(abstract)
                    
                    # Extract title
                    title = ''
                    titles = item.get('title', [])
                    if titles:
                        title = titles[0]
                    
                    # Create Paper object
                    paper = Paper(
                        title=title,
                        authors=authors,
                        venue=venue,
                        year=year,
                        citations=item.get('is-referenced-by-count', 0),
                        abstract=abstract,
                        doi=item.get('DOI', ''),
                        collection_source="crossref",
                        collection_timestamp=datetime.now()
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse paper from Crossref response: {e}")
                    continue
            
            # Get metadata from response
            message = data.get('message', {})
            metadata = ResponseMetadata(
                total_results=message.get('total-results', len(papers)),
                returned_count=len(papers),
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="crossref",
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
                message=f"Failed to parse Crossref response: {str(e)}",
                timestamp=datetime.now()
            )
            
            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="crossref",
                timestamp=datetime.now()
            )
            
            return APIResponse(
                success=False,
                papers=[],
                metadata=metadata,
                errors=[error]
            )
    
    def _clean_jats_abstract(self, abstract: str) -> str:
        """Clean JATS XML tags from abstract"""
        if not abstract:
            return ""
        
        # Remove JATS XML tags
        cleaned = re.sub(r'<jats:[^>]*>', '', abstract)
        cleaned = re.sub(r'</jats:[^>]*>', '', cleaned)
        cleaned = re.sub(r'<[^>]*>', '', cleaned)  # Remove any remaining tags
        
        return cleaned.strip()
    
    # Error handling methods (similar to other clients)
    def _handle_rate_limit(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle rate limit response (429)"""
        error = APIError(
            error_type="rate_limit_exceeded",
            message="Rate limit exceeded for Crossref API",
            status_code=429,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_server_error(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle server errors (5xx)"""
        error = APIError(
            error_type="server_error",
            message=f"Crossref server error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_client_error(self, response: requests.Response, query: str, response_time_ms: float) -> APIResponse:
        """Handle client errors (4xx)"""
        error = APIError(
            error_type="client_error",
            message=f"Crossref client error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_timeout_error(self, query: str, response_time_ms: float) -> APIResponse:
        """Handle request timeout"""
        error = APIError(
            error_type="request_timeout",
            message="Crossref request timed out",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_network_error(self, exception: Exception, query: str, response_time_ms: float) -> APIResponse:
        """Handle network/connection errors"""
        error = APIError(
            error_type="network_error",
            message=f"Crossref network error: {str(exception)}",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def _handle_max_retries_exceeded(self, query: str, response_time_ms: float) -> APIResponse:
        """Handle case where max retries was exceeded"""
        error = APIError(
            error_type="max_retries_exceeded",
            message=f"Crossref maximum retries ({self.max_retries}) exceeded",
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
    
    def normalize_doi(self, doi: str) -> str:
        """Normalize DOI to standard format.
        
        Args:
            doi: DOI in various formats (with or without prefix)
            
        Returns:
            Normalized DOI without prefix
        """
        if not doi:
            return ""
        
        # Remove common DOI prefixes and normalize
        doi = doi.strip()
        doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
        doi = re.sub(r'^doi:\s*', '', doi, flags=re.IGNORECASE)
        
        return doi
    
    def lookup_doi(self, doi: str) -> APIResponse:
        """Look up a specific paper by DOI.
        
        Args:
            doi: The DOI to look up
            
        Returns:
            APIResponse with paper information if found
        """
        start_time = time.time()
        normalized_doi = self.normalize_doi(doi)
        
        if not normalized_doi:
            error = APIError(
                error_type="invalid_doi",
                message="Invalid or empty DOI provided",
                timestamp=datetime.now()
            )
            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=doi,
                response_time_ms=0,
                api_name="crossref",
                timestamp=datetime.now()
            )
            return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
        
        # Construct DOI lookup URL
        url = f"{self.base_url}/works/{normalized_doi}"
        
        # Attempt request with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response_time_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return self._parse_doi_response(response, normalized_doi, response_time_ms)
                elif response.status_code == 404:
                    return self._handle_doi_not_found(normalized_doi, response_time_ms)
                elif response.status_code == 429:
                    return self._handle_rate_limit(response, normalized_doi, response_time_ms)
                elif response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Crossref server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        return self._handle_server_error(response, normalized_doi, response_time_ms)
                else:
                    return self._handle_client_error(response, normalized_doi, response_time_ms)
                    
            except requests.exceptions.Timeout:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Crossref request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_timeout_error(normalized_doi, response_time_ms)
                    
            except requests.exceptions.RequestException as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Crossref request error: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_network_error(e, normalized_doi, response_time_ms)
        
        # Should not reach here, but handle it just in case
        response_time_ms = (time.time() - start_time) * 1000
        return self._handle_max_retries_exceeded(normalized_doi, response_time_ms)
    
    def _parse_doi_response(self, response: requests.Response, doi: str, response_time_ms: float) -> APIResponse:
        """Parse response from DOI lookup."""
        try:
            data = response.json()
            message = data.get("message", {})
            
            # Extract PDF URLs from links if available
            pdf_urls = []
            if "link" in message:
                pdf_urls = self._extract_pdf_urls_from_links(message["link"])
            
            # Create paper object
            paper = Paper(
                title=message.get("title", [""])[0] if message.get("title") else "",
                authors=[
                    Author(
                        name=f"{author.get('given', '')} {author.get('family', '')}".strip(),
                        affiliation=author.get("affiliation", [{}])[0].get("name", "") if author.get("affiliation") else ""
                    )
                    for author in message.get("author", [])
                ],
                venue=message.get("container-title", [""])[0] if message.get("container-title") else "",
                year=message.get("published-print", {}).get("date-parts", [[0]])[0][0] or 
                     message.get("published-online", {}).get("date-parts", [[0]])[0][0] or 0,
                citations=message.get("is-referenced-by-count", 0),
                abstract=self._clean_jats_abstract(message.get("abstract", "")),
                doi=message.get("DOI", doi),
                urls=pdf_urls,
                paper_id=f"crossref_{doi}"
            )
            
            metadata = ResponseMetadata(
                total_results=1,
                returned_count=1,
                query_used=doi,
                response_time_ms=response_time_ms,
                api_name="crossref",
                timestamp=datetime.now()
            )
            
            return APIResponse(
                success=True,
                papers=[paper],
                metadata=metadata,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Crossref DOI response: {e}")
            error = APIError(
                error_type="parse_error",
                message=f"Failed to parse Crossref DOI response: {str(e)}",
                timestamp=datetime.now()
            )
            
            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=doi,
                response_time_ms=response_time_ms,
                api_name="crossref",
                timestamp=datetime.now()
            )
            
            return APIResponse(
                success=False,
                papers=[],
                metadata=metadata,
                errors=[error]
            )
    
    def _extract_pdf_urls_from_links(self, links: List[Dict[str, Any]]) -> List[str]:
        """Extract PDF URLs from CrossRef link data."""
        pdf_urls = []
        for link in links:
            if link.get("content-type") == "application/pdf" and "URL" in link:
                pdf_urls.append(link["URL"])
        return pdf_urls
    
    def _handle_doi_not_found(self, doi: str, response_time_ms: float) -> APIResponse:
        """Handle DOI not found response."""
        error = APIError(
            error_type="not_found",
            message=f"DOI not found: {doi}",
            status_code=404,
            timestamp=datetime.now()
        )
        
        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="crossref",
            timestamp=datetime.now()
        )
        
        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
