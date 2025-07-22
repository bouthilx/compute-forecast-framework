"""
Unpaywall Client - For finding open access versions of papers by DOI
"""

import time
import requests
import re
from typing import List, Dict, Any
from datetime import datetime
import logging

from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
    Author,
    APIResponse,
    ResponseMetadata,
    APIError,
    URLRecord,
)
from compute_forecast.pipeline.consolidation.models import URLData

logger = logging.getLogger(__name__)


class UnpaywallClient:
    """Client for finding open access versions of papers using Unpaywall API."""

    def __init__(self, email: str):
        """Initialize Unpaywall client.

        Args:
            email: Contact email (required by Unpaywall API)

        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError("Email is required for Unpaywall API access")

        self.email = email
        self.base_url = "https://api.unpaywall.org/v2"
        self.max_retries = 3
        self.retry_delay = 1.0  # Unpaywall recommends being gentle with requests

        # Headers for requests
        self.headers = {"User-Agent": f"research-paper-collector/1.0 (mailto:{email})"}

    def normalize_doi(self, doi: str) -> str:
        """Normalize DOI to standard format.

        Args:
            doi: DOI in various formats

        Returns:
            Normalized DOI without prefix
        """
        if not doi:
            return ""

        # Remove common DOI prefixes and normalize
        doi = doi.strip()
        doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)

        return doi

    def find_open_access(self, doi: str) -> APIResponse:
        """Find open access versions of a paper by DOI.

        Args:
            doi: The DOI to look up

        Returns:
            APIResponse with paper and open access URLs if found
        """
        start_time = time.time()
        normalized_doi = self.normalize_doi(doi)

        if not normalized_doi:
            error = APIError(
                error_type="invalid_doi",
                message="Invalid or empty DOI provided",
                timestamp=datetime.now(),
            )
            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=doi,
                response_time_ms=0,
                api_name="unpaywall",
                timestamp=datetime.now(),
            )
            return APIResponse(
                success=False, papers=[], metadata=metadata, errors=[error]
            )

        # Construct Unpaywall API URL
        url = f"{self.base_url}/{normalized_doi}"
        params = {"email": self.email}

        # Attempt request with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, params=params, headers=self.headers, timeout=30
                )
                response_time_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return self._parse_unpaywall_response(
                        response, normalized_doi, response_time_ms
                    )
                elif response.status_code == 404:
                    return self._handle_not_found(normalized_doi, response_time_ms)
                elif response.status_code == 429:
                    return self._handle_rate_limit(normalized_doi, response_time_ms)
                elif response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(
                            f"Unpaywall server error {response.status_code}, retrying in {wait_time}s"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        return self._handle_server_error(
                            response, normalized_doi, response_time_ms
                        )
                else:
                    return self._handle_client_error(
                        response, normalized_doi, response_time_ms
                    )

            except requests.exceptions.Timeout:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Unpaywall request timeout, retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_timeout_error(normalized_doi, response_time_ms)

            except requests.exceptions.RequestException as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Unpaywall request error: {e}, retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return self._handle_network_error(
                        e, normalized_doi, response_time_ms
                    )

        # Should not reach here, but handle it just in case
        response_time_ms = (time.time() - start_time) * 1000
        return self._handle_max_retries_exceeded(normalized_doi, response_time_ms)

    def _parse_unpaywall_response(
        self, response: requests.Response, doi: str, response_time_ms: float
    ) -> APIResponse:
        """Parse response from Unpaywall API."""
        try:
            data = response.json()

            # Create paper from Unpaywall data
            paper = self._create_paper_from_unpaywall_data(data)

            metadata = ResponseMetadata(
                total_results=1,
                returned_count=1,
                query_used=doi,
                response_time_ms=response_time_ms,
                api_name="unpaywall",
                timestamp=datetime.now(),
            )

            return APIResponse(
                success=True, papers=[paper], metadata=metadata, errors=[]
            )

        except Exception as e:
            logger.error(f"Failed to parse Unpaywall response: {e}")
            error = APIError(
                error_type="parse_error",
                message=f"Failed to parse Unpaywall response: {str(e)}",
                timestamp=datetime.now(),
            )

            metadata = ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used=doi,
                response_time_ms=response_time_ms,
                api_name="unpaywall",
                timestamp=datetime.now(),
            )

            return APIResponse(
                success=False, papers=[], metadata=metadata, errors=[error]
            )

    def _create_paper_from_unpaywall_data(self, data: Dict[str, Any]) -> Paper:
        """Create a Paper object from Unpaywall API data."""
        # Extract open access URLs
        oa_urls = self._extract_oa_urls(data.get("oa_locations", []))

        # Parse authors (Unpaywall sometimes provides just a list of names)
        authors = []
        author_data = data.get("authors", [])
        if isinstance(author_data, list):
            for author in author_data:
                if isinstance(author, str):
                    authors.append(Author(name=author))
                elif isinstance(author, dict):
                    name = (
                        author.get("name", "")
                        or f"{author.get('given', '')} {author.get('family', '')}".strip()
                    )
                    authors.append(Author(name=name))

        return Paper(
            title=data.get("title", ""),
            authors=authors,
            venue=data.get("journal_name", ""),
            year=data.get("year", 0) or 0,
            abstracts=[],  # Unpaywall doesn't provide abstracts
            citations=[],  # Unpaywall doesn't provide citation counts
            doi=data.get("doi", ""),
            urls=[
                URLRecord(
                    source="unpaywall",
                    timestamp=datetime.now(),
                    original=True,
                    data=URLData(url=url),
                )
                for url in oa_urls
            ],
            paper_id=f"unpaywall_{data.get('doi', '')}",
        )

    def _extract_oa_urls(self, oa_locations: List[Dict[str, Any]]) -> List[str]:
        """Extract and prioritize open access URLs from Unpaywall data.

        Args:
            oa_locations: List of OA location dicts from Unpaywall

        Returns:
            List of URLs ordered by preference (publisher first, then repository)
        """
        if not oa_locations:
            return []

        publisher_urls = []
        repository_urls = []

        for location in oa_locations:
            url = location.get("url")
            if not url:
                continue

            host_type = location.get("host_type", "").lower()
            if host_type == "publisher":
                publisher_urls.append(url)
            elif host_type == "repository":
                repository_urls.append(url)
            else:
                # Unknown type, add to repository list
                repository_urls.append(url)

        # Prioritize publisher versions over repository versions
        return publisher_urls + repository_urls

    def _handle_not_found(self, doi: str, response_time_ms: float) -> APIResponse:
        """Handle DOI not found response."""
        error = APIError(
            error_type="not_found",
            message=f"DOI not found in Unpaywall: {doi}",
            status_code=404,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_rate_limit(self, doi: str, response_time_ms: float) -> APIResponse:
        """Handle rate limit response."""
        error = APIError(
            error_type="rate_limit_exceeded",
            message="Rate limit exceeded for Unpaywall API",
            status_code=429,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_server_error(
        self, response: requests.Response, doi: str, response_time_ms: float
    ) -> APIResponse:
        """Handle server errors."""
        error = APIError(
            error_type="server_error",
            message=f"Unpaywall server error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_client_error(
        self, response: requests.Response, doi: str, response_time_ms: float
    ) -> APIResponse:
        """Handle client errors."""
        error = APIError(
            error_type="client_error",
            message=f"Unpaywall client error: {response.status_code}",
            status_code=response.status_code,
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_timeout_error(self, doi: str, response_time_ms: float) -> APIResponse:
        """Handle request timeout."""
        error = APIError(
            error_type="request_timeout",
            message="Unpaywall request timed out",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_network_error(
        self, exception: Exception, doi: str, response_time_ms: float
    ) -> APIResponse:
        """Handle network/connection errors."""
        error = APIError(
            error_type="network_error",
            message=f"Unpaywall network error: {str(exception)}",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])

    def _handle_max_retries_exceeded(
        self, doi: str, response_time_ms: float
    ) -> APIResponse:
        """Handle case where max retries was exceeded."""
        error = APIError(
            error_type="max_retries_exceeded",
            message=f"Unpaywall maximum retries ({self.max_retries}) exceeded",
            timestamp=datetime.now(),
        )

        metadata = ResponseMetadata(
            total_results=0,
            returned_count=0,
            query_used=doi,
            response_time_ms=response_time_ms,
            api_name="unpaywall",
            timestamp=datetime.now(),
        )

        return APIResponse(success=False, papers=[], metadata=metadata, errors=[error])
