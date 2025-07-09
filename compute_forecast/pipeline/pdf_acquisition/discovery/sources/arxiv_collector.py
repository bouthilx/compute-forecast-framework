"""ArXiv PDF collector with enhanced discovery and version handling."""

import re
import time
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime
from urllib.parse import quote_plus

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.utils.exceptions import (
    SourceNotApplicableError,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second allowed
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()


class ArXivPDFCollector(BasePDFCollector):
    """Enhanced arXiv PDF collector with multiple search strategies."""

    def __init__(self):
        """Initialize the arXiv PDF collector."""
        super().__init__("arxiv")
        self.base_url = "https://arxiv.org/pdf/"
        self.api_url = "http://export.arxiv.org/api/query"
        self.rate_limiter = RateLimiter(3.0)  # 3 requests per second

        # Compile regex patterns for efficiency
        self.arxiv_id_pattern = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
        self.arxiv_url_pattern = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})")

    def extract_arxiv_id(self, paper: Paper) -> Optional[str]:
        """Extract arXiv ID from various sources in the paper.

        Args:
            paper: Paper to extract arXiv ID from

        Returns:
            Clean arXiv ID (without version) or None if not found
        """
        # Strategy 1: Check paper.arxiv_id field
        if paper.arxiv_id:
            extracted_id = self._extract_id_from_string(paper.arxiv_id)
            if extracted_id:
                logger.debug(f"Found arXiv ID from paper.arxiv_id: {extracted_id}")
                return extracted_id

        # Strategy 2: Check URLs for arxiv.org links
        if paper.urls:
            for url in paper.urls:
                if isinstance(url, str):
                    extracted_id = self._extract_id_from_string(url)
                    if extracted_id:
                        logger.debug(f"Found arXiv ID from URL: {extracted_id}")
                        return extracted_id

        # Strategy 3: Check DOI for arXiv references (some papers have arXiv DOIs)
        if paper.doi:
            extracted_id = self._extract_id_from_string(paper.doi)
            if extracted_id:
                logger.debug(f"Found arXiv ID from DOI: {extracted_id}")
                return extracted_id

        logger.debug(f"No arXiv ID found for paper {paper.paper_id}")
        return None

    def _extract_id_from_string(self, text: str) -> Optional[str]:
        """Extract arXiv ID from a string (ID, URL, etc.).

        Args:
            text: String to extract ID from

        Returns:
            Clean arXiv ID without version, or None if not found
        """
        if not text:
            return None

        # First try URL pattern
        url_match = self.arxiv_url_pattern.search(text)
        if url_match:
            return str(url_match.group(1))

        # Then try direct ID pattern
        id_match = self.arxiv_id_pattern.search(text)
        if id_match:
            return str(id_match.group(1))  # Return without version

        return None

    def _extract_version(self, arxiv_id: str) -> Optional[str]:
        """Extract version from arXiv ID.

        Args:
            arxiv_id: arXiv ID potentially with version

        Returns:
            Version string (e.g., 'v5') or None if no version
        """
        match = self.arxiv_id_pattern.search(arxiv_id)
        if match and match.group(2):
            return str(match.group(2))  # Returns 'v5', 'v1', etc.
        return None

    def _build_pdf_url(self, arxiv_id: str) -> str:
        """Build PDF URL for arXiv ID.

        Args:
            arxiv_id: Clean arXiv ID without version

        Returns:
            PDF URL for the paper
        """
        return f"{self.base_url}{arxiv_id}.pdf"

    def search_by_title_author(self, paper: Paper) -> Optional[str]:
        """Search arXiv API using title and first author.

        Args:
            paper: Paper to search for

        Returns:
            arXiv ID if found, None otherwise
        """
        if not paper.title or not paper.authors:
            return None

        # Prepare search query
        title = paper.title.strip()
        first_author = (
            paper.authors[0].name.split(",")[0].strip() if paper.authors else ""
        )

        # Build search query - search by title and first author
        query_parts = []
        if title:
            # Escape special characters and quote the title
            safe_title = quote_plus(f'"{title}"')
            query_parts.append(f"ti:{safe_title}")

        if first_author:
            safe_author = quote_plus(first_author)
            query_parts.append(f"au:{safe_author}")

        if not query_parts:
            return None

        query = " AND ".join(query_parts)
        url = f"{self.api_url}?search_query={query}&start=0&max_results=5"

        try:
            self.rate_limiter.wait()
            logger.debug(f"Searching arXiv API: {url}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            return self._parse_search_response(response.text, paper)

        except Exception as e:
            logger.warning(f"arXiv API search failed for paper {paper.paper_id}: {e}")
            return None

    def _parse_search_response(self, xml_response: str, paper: Paper) -> Optional[str]:
        """Parse arXiv API XML response and find matching paper.

        Args:
            xml_response: XML response from arXiv API
            paper: Original paper to match against

        Returns:
            arXiv ID if matching paper found, None otherwise
        """
        try:
            root = ET.fromstring(xml_response)

            # Define namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            entries = root.findall("atom:entry", ns)
            if not entries:
                logger.debug("No entries found in arXiv search response")
                return None

            # Look for exact title match in the results
            paper_title_lower = paper.title.lower().strip()

            for entry in entries:
                title_elem = entry.find("atom:title", ns)
                if title_elem is not None:
                    entry_title = (title_elem.text or "").strip().lower()

                    # Check for exact or very close title match
                    if self._titles_match(paper_title_lower, entry_title):
                        # Extract arXiv ID from the entry
                        id_elem = entry.find("atom:id", ns)
                        if id_elem is not None and id_elem.text:
                            arxiv_url = id_elem.text
                            arxiv_id = self._extract_id_from_string(arxiv_url)
                            if arxiv_id:
                                logger.info(
                                    f"Found arXiv match via API search: {arxiv_id}"
                                )
                                return arxiv_id

            logger.debug("No matching papers found in arXiv search results")
            return None

        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv API response: {e}")
            return None

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two titles match (allowing for minor differences).

        Args:
            title1: First title (normalized to lowercase)
            title2: Second title (normalized to lowercase)

        Returns:
            True if titles match, False otherwise
        """

        # Remove common punctuation and extra whitespace
        def normalize_title(title):
            # Remove punctuation and normalize whitespace
            normalized = re.sub(r"[^\w\s]", " ", title)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            return normalized

        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)

        # Check exact match first
        if norm_title1 == norm_title2:
            return True

        # Check if one title contains the other (for cases with subtitles)
        if norm_title1 in norm_title2 or norm_title2 in norm_title1:
            return True

        return False

    def handle_versions(self, arxiv_id: str) -> PDFRecord:
        """Handle arXiv version management and create PDFRecord.

        Args:
            arxiv_id: arXiv ID (may include version)

        Returns:
            PDFRecord with PDF information

        Raises:
            Exception: If PDF cannot be validated or accessed
        """
        original_version = self._extract_version(arxiv_id)
        clean_id = self._extract_id_from_string(arxiv_id)

        if not clean_id:
            raise Exception(f"Invalid arXiv ID: {arxiv_id}")

        # Always fetch latest version by constructing URL without version
        pdf_url = self._build_pdf_url(clean_id)

        # Validate PDF availability
        try:
            self.rate_limiter.wait()
            response = requests.head(pdf_url, timeout=30, allow_redirects=True)

            if response.status_code == 200:
                file_size = response.headers.get("Content-Length")
                file_size_bytes = int(file_size) if file_size else None

                return PDFRecord(
                    paper_id="",  # Will be set by caller
                    pdf_url=pdf_url,
                    source=self.source_name,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95 if original_version else 0.8,
                    version_info={
                        "original_version": original_version or "unknown",
                        "fetched_version": "latest",
                        "arxiv_id": clean_id,
                    },
                    validation_status="pending",
                    file_size_bytes=file_size_bytes,
                )
            else:
                raise Exception(
                    f"PDF not accessible, status code: {response.status_code}"
                )

        except requests.RequestException as e:
            raise Exception(f"Failed to validate PDF at {pdf_url}: {e}")

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using multiple strategies.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If no arXiv version can be found
        """
        logger.debug(f"Discovering arXiv PDF for paper {paper.paper_id}")

        # Strategy 1: Direct arXiv ID lookup
        arxiv_id = self.extract_arxiv_id(paper)

        if arxiv_id:
            logger.debug(f"Using direct arXiv ID: {arxiv_id}")
            pdf_record = self.handle_versions(arxiv_id)
            pdf_record.paper_id = paper.paper_id or f"arxiv_{arxiv_id}"
            return pdf_record

        # Strategy 2: Title + author search
        logger.debug(f"Falling back to title+author search for paper {paper.paper_id}")
        arxiv_id = self.search_by_title_author(paper)

        if arxiv_id:
            logger.info(f"Found arXiv ID via search: {arxiv_id}")
            pdf_record = self.handle_versions(arxiv_id)
            pdf_record.paper_id = paper.paper_id or f"arxiv_{arxiv_id}"
            # Lower confidence for search-based discovery
            pdf_record.confidence_score = min(pdf_record.confidence_score, 0.8)
            return pdf_record

        # No arXiv version found
        raise SourceNotApplicableError(
            f"No arXiv ID for {paper.paper_id}", source="arxiv"
        )
