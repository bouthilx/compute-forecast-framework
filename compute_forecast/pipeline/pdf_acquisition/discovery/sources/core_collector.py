"""CORE API PDF collector for institutional repository access."""

import logging
import requests
from typing import Optional, Union, Dict, Any
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.utils import (
    RateLimiter,
    APIError,
    NoResultsError,
    NoPDFFoundError,
)

logger = logging.getLogger(__name__)


class COREPDFCollector(BasePDFCollector):
    """CORE API collector for discovering PDFs from institutional repositories."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        requests_per_minute: int = 100,
    ):
        """Initialize CORE collector.

        Args:
            api_key: Optional CORE API key for higher rate limits
            api_url: Optional custom API URL (defaults to CORE v3)
            requests_per_minute: Rate limit for requests (default: 100)
        """
        super().__init__("core")
        self.api_url = api_url or "https://api.core.ac.uk/v3/search/outputs"
        self.api_key = api_key
        self.rate_limiter = RateLimiter.per_minute(requests_per_minute)

        # Set up headers
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "PDFDiscoveryFramework/1.0",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using CORE API.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Build search query
        query = self._build_search_query(paper)

        # Apply rate limiting
        self.rate_limiter.wait()

        # Search CORE API
        params: Dict[str, Union[str, int]] = {
            "q": query,
            "limit": 10,
            "fulltext": "false",
        }

        try:
            response = requests.get(
                self.api_url, params=params, headers=self.headers, timeout=30
            )

            if response.status_code != 200:
                raise APIError(
                    f"CORE API error: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            data = response.json()

            if data.get("totalHits", 0) == 0:
                raise NoResultsError("No results found in CORE", query=query)

            # Find best matching result with PDF
            for result in data.get("results", []):
                pdf_url = self._extract_pdf_url(result)
                if pdf_url:
                    return PDFRecord(
                        paper_id=paper.paper_id
                        or f"core_{result.get('id', 'unknown')}",
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.9,
                        version_info={
                            "core_id": result.get("id"),
                            "published_date": result.get("publishedDate"),
                            "repository": result.get("repositoryDocument", {})
                            .get("repository", {})
                            .get("name"),
                        },
                        validation_status="verified",
                        file_size_bytes=result.get("repositoryDocument", {}).get(
                            "pdfSize"
                        ),
                        license=self._extract_license(result),
                    )

            raise NoPDFFoundError(
                "No PDF found in CORE results",
                results_count=len(data.get("results", [])),
            )

        except requests.RequestException as e:
            raise APIError(f"CORE API request failed: {str(e)}") from e

    def _build_search_query(self, paper: Paper) -> str:
        """Build search query for CORE API.

        Args:
            paper: Paper to search for

        Returns:
            Search query string
        """
        # Prefer DOI search if available
        if paper.doi:
            return f'doi:"{paper.doi}"'

        # Otherwise use title search
        return f'title:"{paper.title}"'

    def _extract_pdf_url(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract PDF URL from CORE result.

        Args:
            result: CORE API result object

        Returns:
            PDF URL if found, None otherwise
        """
        # Check downloadUrl first
        download_url = result.get("downloadUrl")
        if download_url and str(download_url).endswith(".pdf"):
            return str(download_url)

        # Check repository document
        repo_doc = result.get("repositoryDocument", {})
        if repo_doc:
            # Check if PDF is available
            if repo_doc.get("pdfStatus") == 1:
                pdf_url = repo_doc.get("pdfUrl")
                if pdf_url:
                    return str(pdf_url)

        # Last resort: check if downloadUrl exists (might not end with .pdf)
        if download_url:
            return str(download_url)

        return None

    def _extract_license(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract license information from CORE result.

        Args:
            result: CORE API result object

        Returns:
            License string if found
        """
        # Check for open access status
        if result.get("openAccess") is True:
            return "open_access"

        # Check rights field
        rights = result.get("rights")
        if rights:
            return str(rights)

        return None
