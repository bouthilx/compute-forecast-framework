"""IEEE Xplore PDF Collector for discovering PDFs from IEEE Digital Library."""

import logging
import os
import time
from typing import Optional
from datetime import datetime
from urllib.parse import quote

import requests

from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper

logger = logging.getLogger(__name__)

# Module-level constants
IEEE_BASE_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
CONFIDENCE_SCORE_WITH_DOI = 0.95  # High confidence when found via DOI
CONFIDENCE_SCORE_TITLE_SEARCH = 0.8  # Lower confidence for title search
RATE_LIMIT_DELAY = 1.0  # 1 second between requests for free API tier


class IEEEXplorePDFCollector(BasePDFCollector):
    """Collects PDF URLs from IEEE Xplore Digital Library.

    This collector uses the IEEE Xplore API to discover PDFs for IEEE conference
    papers, particularly focusing on venues like ICRA and other IEEE conferences.
    Due to limited free API access, it implements rate limiting and fallback
    mechanisms.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the IEEE Xplore PDF collector.

        Args:
            api_key: IEEE Xplore API key (required)

        Raises:
            ValueError: If no API key is provided
        """
        super().__init__("ieee_xplore")

        # API configuration
        self.api_key = api_key or os.getenv("IEEE_XPLORE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "IEEE Xplore API key required. Provide via api_key parameter "
                "or IEEE_XPLORE_API_KEY environment variable."
            )

        self.base_url = IEEE_BASE_URL
        self.timeout = 30  # 30 second timeout for API requests

        # Rate limiting
        self.rate_limit_delay = RATE_LIMIT_DELAY
        self.last_request_time = 0

        # Batch not supported for IEEE API free tier
        self.supports_batch = False

        logger.info("Initialized IEEE Xplore PDF collector")

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _build_api_url(
        self, doi: Optional[str] = None, title: Optional[str] = None
    ) -> str:
        """Build IEEE Xplore API URL with query parameters.

        Args:
            doi: DOI to search for
            title: Title to search for

        Returns:
            Complete API URL with query parameters
        """
        params = [f"apikey={self.api_key}"]

        if doi:
            # Remove DOI prefix if present
            clean_doi = doi.replace("https://doi.org/", "").replace(
                "http://doi.org/", ""
            )
            params.append(f"doi={clean_doi}")
        elif title:
            # URL encode the title
            encoded_title = quote(title)
            params.append(f"article_title={encoded_title}")

        # Add format parameter
        params.append("format=json")

        # Limit results
        params.append("max_records=10")

        return f"{self.base_url}?{'&'.join(params)}"

    def _parse_api_response(self, response_data: dict, paper: Paper) -> PDFRecord:
        """Parse IEEE API response and create PDFRecord.

        Args:
            response_data: API response JSON
            paper: Original paper object

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            ValueError: If no valid article or PDF found
        """
        articles = response_data.get("articles", [])

        if not articles:
            raise ValueError(f"Paper not found in IEEE Xplore: {paper.title}")

        # Take the first matching article
        article = articles[0]

        # Check for PDF availability
        pdf_url = article.get("pdf_url")
        if not pdf_url:
            # Try to construct PDF URL from article number if not provided
            article_number = article.get("article_number")
            if article_number:
                # IEEE PDF URLs often follow a pattern, but this is not guaranteed
                # This is a fallback attempt
                logger.warning(
                    "No pdf_url in response, article may not have open PDF access"
                )
            raise ValueError(f"No PDF available for paper: {paper.title}")

        # Determine access type and validation status
        access_type = article.get("access_type", "UNKNOWN")
        if access_type == "OPEN_ACCESS":
            validation_status = "open_access"
        elif access_type == "SUBSCRIPTION":
            validation_status = "subscription"
        else:
            validation_status = access_type.lower()

        # Determine confidence score
        confidence_score = (
            CONFIDENCE_SCORE_WITH_DOI
            if hasattr(paper, "doi") and paper.doi
            else CONFIDENCE_SCORE_TITLE_SEARCH
        )

        return PDFRecord(
            paper_id=paper.paper_id
            or f"ieee_{article.get('article_number', 'unknown')}",
            pdf_url=pdf_url,
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=confidence_score,
            version_info={
                "article_number": article.get("article_number"),
                "doi": article.get("doi"),
                "access_type": access_type,
                "content_type": article.get("content_type", "Unknown"),
                "publication_title": article.get("publication_title"),
                "publication_year": article.get("publication_year"),
            },
            validation_status=validation_status,
            file_size_bytes=None,  # IEEE API doesn't provide file size
            license=access_type if access_type == "OPEN_ACCESS" else None,
        )

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            ValueError: If no PDF is found or API errors occur
            requests.HTTPError: For API HTTP errors
        """
        self._enforce_rate_limit()

        # Build API URL - prefer DOI search if available
        if hasattr(paper, "doi") and paper.doi:
            api_url = self._build_api_url(doi=paper.doi)
            logger.debug(f"Searching IEEE Xplore by DOI: {paper.doi}")
        else:
            api_url = self._build_api_url(title=paper.title)
            logger.debug(f"Searching IEEE Xplore by title: {paper.title}")

        try:
            # Make API request
            response = requests.get(api_url, timeout=self.timeout)

            # Check for rate limiting
            if response.status_code == 429:
                raise ValueError("Rate limit exceeded for IEEE Xplore API")

            response.raise_for_status()

            # Parse response
            response_data = response.json()

            # Create and return PDFRecord
            return self._parse_api_response(response_data, paper)

        except requests.exceptions.RequestException as e:
            logger.error(f"IEEE Xplore API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error discovering PDF for {paper.paper_id}: {e}")
            raise

    def _resolve_doi_to_pdf(self, doi: str) -> Optional[str]:
        """Attempt to resolve DOI to PDF URL using alternative sources.

        This is a fallback mechanism when IEEE API doesn't provide direct PDF access.

        Args:
            doi: DOI to resolve

        Returns:
            PDF URL if found, None otherwise
        """
        # This method could integrate with Unpaywall or other DOI resolvers
        # For now, it's a placeholder for future enhancement
        logger.debug(f"Attempting DOI resolution fallback for: {doi}")
        return None
