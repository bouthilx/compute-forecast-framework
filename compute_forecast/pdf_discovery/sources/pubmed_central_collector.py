"""PubMed Central PDF collector implementation."""

import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

import requests

from compute_forecast.data.models import Paper
from ..core.collectors import BasePDFCollector
from ..core.models import PDFRecord

logger = logging.getLogger(__name__)


class PubMedCentralCollector(BasePDFCollector):
    """Collector for PubMed Central open access PDFs."""

    def __init__(self):
        """Initialize PubMed Central collector."""
        super().__init__("pubmed_central")

        # E-utilities API configuration
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.pdf_base_url = "https://www.ncbi.nlm.nih.gov/pmc/articles"

        # Rate limiting: 3 requests per second
        self.delay_between_requests = 0.34  # Slightly more than 1/3 second
        self.last_request_time = 0

        # Timeout for API requests
        self.timeout = 30

        # Search confidence scores
        self.confidence_scores = {"doi": 0.95, "title": 0.85, "author_year": 0.75}

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using E-utilities API.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Try different search strategies in order of preference
        search_methods = []

        if hasattr(paper, "doi") and paper.doi:
            search_methods.append("doi")
        search_methods.extend(["title", "author_year"])

        for method in search_methods:
            try:
                pmc_id = self._search_for_pmc_id(paper, method)
                if pmc_id:
                    pdf_url = self._build_pdf_url(pmc_id)

                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=self.confidence_scores[method],
                        version_info={
                            "pmc_id": pmc_id,
                            "search_method": method,
                            "api": "e-utilities",
                        },
                        validation_status="valid",
                    )
            except Exception as e:
                logger.debug(f"Search method {method} failed for {paper.paper_id}: {e}")
                continue

        raise Exception(f"No PMC ID found for paper {paper.paper_id}")

    def _search_for_pmc_id(self, paper: Paper, method: str) -> Optional[str]:
        """Search for PMC ID using specified method.

        Args:
            paper: Paper to search for
            method: Search method (doi, title, author_year)

        Returns:
            PMC ID if found, None otherwise
        """
        # Build search query
        query = self._format_search_query(paper, method)
        if not query:
            return None

        # Search for PubMed IDs
        pubmed_ids = self._esearch(query)
        if not pubmed_ids:
            return None

        # Get PMC IDs from PubMed IDs
        for pubmed_id in pubmed_ids[:5]:  # Check up to 5 results
            pmc_id = self._get_pmc_id_from_pubmed(pubmed_id)
            if pmc_id:
                return pmc_id

        return None

    def _format_search_query(self, paper: Paper, method: str) -> str:
        """Format search query based on method.

        Args:
            paper: Paper to build query for
            method: Search method

        Returns:
            Formatted query string
        """
        if method == "doi" and hasattr(paper, "doi") and paper.doi:
            return f"{paper.doi}[DOI]"

        elif method == "title":
            # Clean and quote title for exact search
            title = paper.title.strip()
            return f'"{title}"[Title]'

        elif method == "author_year":
            # Use first author's last name and year
            if paper.authors and paper.year:
                first_author = paper.authors[0]
                # Extract last name (assume format "First Last" or "Last, First")
                if "," in first_author:
                    last_name = first_author.split(",")[0].strip()
                else:
                    parts = first_author.strip().split()
                    last_name = parts[-1] if parts else ""

                if last_name:
                    return f"{last_name}[Author] AND {paper.year}[PDAT]"

        return ""

    def _esearch(self, query: str) -> list:
        """Execute E-utilities search.

        Args:
            query: Search query

        Returns:
            List of PubMed IDs
        """
        self._rate_limit()

        params = {"db": "pubmed", "term": query, "retmax": 10, "retmode": "xml"}

        try:
            response = requests.get(
                f"{self.base_url}/esearch.fcgi", params=params, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.text)
            id_list = root.find(".//IdList")

            if id_list is not None:
                return [id_elem.text for id_elem in id_list.findall("Id")]

            return []

        except Exception as e:
            logger.error(f"E-search failed: {e}")
            raise

    def _get_pmc_id_from_pubmed(self, pubmed_id: str) -> Optional[str]:
        """Get PMC ID from PubMed ID using E-utilities.

        Args:
            pubmed_id: PubMed ID

        Returns:
            PMC ID if available, None otherwise
        """
        self._rate_limit()

        params = {"db": "pubmed", "id": pubmed_id, "retmode": "xml"}

        try:
            response = requests.get(
                f"{self.base_url}/esummary.fcgi", params=params, timeout=self.timeout
            )
            response.raise_for_status()

            return self._extract_pmc_id_from_xml(response.text)

        except Exception as e:
            logger.error(f"E-summary failed for PubMed ID {pubmed_id}: {e}")
            raise

    def _extract_pmc_id_from_xml(self, xml_text: str) -> Optional[str]:
        """Extract PMC ID from E-utilities XML response.

        Args:
            xml_text: XML response text

        Returns:
            PMC ID if found, None otherwise
        """
        try:
            root = ET.fromstring(xml_text)

            # Look for PMC ID in different possible locations
            # Try Item with Name="pmc"
            pmc_item = root.find(".//Item[@Name='pmc']")
            if pmc_item is not None and pmc_item.text:
                pmc_id = pmc_item.text.strip()
                # Ensure PMC prefix
                if not pmc_id.startswith("PMC"):
                    pmc_id = f"PMC{pmc_id}"
                return pmc_id

            # Try other possible locations (future-proofing)
            for elem in root.iter():
                if elem.tag.lower() == "pmc" and elem.text:
                    pmc_id = elem.text.strip()
                    if not pmc_id.startswith("PMC"):
                        pmc_id = f"PMC{pmc_id}"
                    return pmc_id

            return None

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return None

    def _build_pdf_url(self, pmc_id: str) -> str:
        """Build PDF URL from PMC ID.

        Args:
            pmc_id: PMC ID (with or without PMC prefix)

        Returns:
            Full PDF URL
        """
        # Ensure PMC prefix
        if not pmc_id.startswith("PMC"):
            pmc_id = f"PMC{pmc_id}"

        return f"{self.pdf_base_url}/{pmc_id}/pdf/"

    def _rate_limit(self):
        """Apply rate limiting to respect API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.delay_between_requests:
            sleep_time = self.delay_between_requests - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
