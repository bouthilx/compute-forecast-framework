"""
Enhanced Semantic Scholar Client - Supports batch queries and improved error handling
Real implementation with API integration, retry logic, and error handling
"""

import time
import requests
from typing import List, Optional, Dict, Any
from ..models import Paper, Author, APIResponse, ResponseMetadata, APIError
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class EnhancedSemanticScholarClient:
    """Enhanced Semantic Scholar client with batch support"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.api_key = api_key
        self.max_retries = 3
        self.retry_delay = 1.0  # Start with 1 second delay

        # Default headers
        self.headers = {"User-Agent": "research-paper-collector/1.0"}
        if api_key:
            self.headers["x-api-key"] = api_key

    def search_papers(
        self, query: str, year: int, limit: int = 500, offset: int = 0
    ) -> APIResponse:
        """
        Search papers with enhanced error handling and retry logic

        REQUIREMENTS:
        - 100 requests/5min limit, retry logic (max 3 retries)
        - Support pagination with offset
        - Parse Semantic Scholar API response format
        """
        start_time = time.time()

        # Construct API URL and parameters
        url = f"{self.base_url}/paper/search"
        params: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),  # SS API limit is 100 per request
            "offset": offset,
            "fields": "paperId,title,authors,venue,year,citationCount,abstract,url",
        }

        # Attempt request with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, params=params, headers=self.headers, timeout=30
                )
                response_time_ms = (time.time() - start_time) * 1000

                # Handle different response codes
                if response.status_code == 200:
                    return self._parse_successful_response(
                        response, query, response_time_ms
                    )
                elif response.status_code == 429:
                    return self._handle_rate_limit(response, query, response_time_ms)
                elif response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (
                            2**attempt
                        )  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {wait_time}s"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        return self._handle_server_error(
                            response, query, response_time_ms
                        )
                else:
                    return self._handle_client_error(response, query, response_time_ms)

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(f"Request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_timeout_error(
                        query, (time.time() - start_time) * 1000
                    )

            except requests.exceptions.RequestException as e:
                return self._handle_network_error(
                    e, query, (time.time() - start_time) * 1000
                )

        # Should not reach here, but handle gracefully
        return self._handle_max_retries_exceeded(
            query, (time.time() - start_time) * 1000
        )

    def search_venue_batch(
        self, venues: List[str], year: int, limit: int = 500
    ) -> APIResponse:
        """
        Search multiple venues in a single query using OR logic

        REQUIREMENTS:
        - Construct OR query: (venue:"X" OR venue:"Y")
        - Handle large venue lists (split if needed)
        """
        # Construct OR query for venues
        venue_queries = [f'venue:"{venue}"' for venue in venues]
        venue_or_query = " OR ".join(venue_queries)

        # Add year filter
        full_query = f"({venue_or_query}) AND year:{year}"

        # Use regular search_papers method with the OR query
        return self.search_papers(full_query, year, limit=limit)

    def _parse_successful_response(
        self, response: requests.Response, query: str, response_time_ms: float
    ) -> APIResponse:
        """Parse successful API response into Paper objects"""
        try:
            data = response.json()
            papers = []

            for item in data.get("data", []):
                try:
                    # Parse authors
                    authors = []
                    for author_data in item.get("authors", []):
                        authors.append(
                            Author(
                                name=author_data.get("name", ""),
                                author_id=author_data.get("authorId", ""),
                            )
                        )

                    # Create Paper object
                    paper = Paper(
                        title=item.get("title", ""),
                        authors=authors,
                        venue=item.get("venue", ""),
                        year=item.get("year", 0),
                        citations=item.get("citationCount", 0),
                        abstract=item.get("abstract", ""),
                        paper_id=item.get("paperId"),
                        urls=[item.get("url")] if item.get("url") else [],
                        collection_source="semantic_scholar",
                        collection_timestamp=datetime.now(),
                    )
                    papers.append(paper)

                except Exception as e:
                    logger.warning(f"Failed to parse paper from SS response: {e}")
                    continue

            metadata = ResponseMetadata(
                total_results=data.get("total", len(papers)),
                returned_count=len(papers),
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="semantic_scholar",
                timestamp=datetime.now(),
            )

            return APIResponse(
                success=True, papers=papers, metadata=metadata, errors=[]
            )

        except Exception as e:
            error = APIError(
                error_type="response_parsing_error",
                message=f"Failed to parse SS response: {str(e)}",
                timestamp=datetime.now(),
            )

            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=query,
                response_time_ms=response_time_ms,
                api_name="semantic_scholar",
                timestamp=datetime.now(),
            )

            return APIResponse(
                success=False, papers=[], metadata=metadata, errors=[error]
            )

    def _handle_rate_limit(
        self, response: requests.Response, query: str, response_time_ms: float
    ) -> APIResponse:
        """Handle rate limit response (429)"""
        retry_after = response.headers.get("Retry-After", "60")

        error = APIError(
            error_type="rate_limit_exceeded",
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_server_error(
        self, response: requests.Response, query: str, response_time_ms: float
    ) -> APIResponse:
        """Handle server errors (5xx)"""
        error = APIError(
            error_type="server_error",
            message=f"Server error: {response.status_code} - {response.text}",
            status_code=response.status_code,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_client_error(
        self, response: requests.Response, query: str, response_time_ms: float
    ) -> APIResponse:
        """Handle client errors (4xx)"""
        error = APIError(
            error_type="client_error",
            message=f"Client error: {response.status_code} - {response.text}",
            status_code=response.status_code,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_timeout_error(self, query: str, response_time_ms: float) -> APIResponse:
        """Handle request timeout"""
        error = APIError(
            error_type="request_timeout",
            message="Request timed out after 30 seconds",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_network_error(
        self, exception: Exception, query: str, response_time_ms: float
    ) -> APIResponse:
        """Handle network/connection errors"""
        error = APIError(
            error_type="network_error",
            message=f"Network error: {str(exception)}",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_max_retries_exceeded(
        self, query: str, response_time_ms: float
    ) -> APIResponse:
        """Handle case where max retries was exceeded"""
        error = APIError(
            error_type="max_retries_exceeded",
            message=f"Maximum retries ({self.max_retries}) exceeded",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=query,
            response_time_ms=response_time_ms,
            api_name="semantic_scholar",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
