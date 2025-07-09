"""HAL (Hyper Articles en Ligne) PDF collector for French research repositories."""

import logging
import re
import requests
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Union
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


class HALPDFCollector(BasePDFCollector):
    """HAL PDF collector using OAI-PMH protocol and Search API."""

    def __init__(
        self,
        oai_url: Optional[str] = None,
        search_url: Optional[str] = None,
        requests_per_second: float = 1.0,
    ):
        """Initialize HAL collector.

        Args:
            oai_url: Optional custom OAI-PMH URL
            search_url: Optional custom search API URL
            requests_per_second: Rate limit for requests (default: 1.0)
        """
        super().__init__("hal")
        self.oai_url = oai_url or "https://api.archives-ouvertes.fr/oai/hal"
        self.search_url = search_url or "https://api.archives-ouvertes.fr/search"
        self.rate_limiter = RateLimiter.per_second(requests_per_second)

        # Compile regex for HAL ID extraction
        self.hal_id_pattern = re.compile(r"(hal-\d+)")

        # Namespaces for XML parsing
        self.namespaces = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
        }

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using HAL.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Try OAI-PMH first (if we have an identifier)
        if paper.doi or self._extract_hal_id_from_urls(paper):
            try:
                return self._discover_via_oai(paper)
            except Exception as e:
                logger.debug(f"OAI-PMH discovery failed: {e}")

        # Fall back to Search API
        return self._discover_via_search(paper)

    def _discover_via_oai(self, paper: Paper) -> PDFRecord:
        """Discover PDF using OAI-PMH protocol.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        identifier = self._build_oai_identifier(paper)
        if not identifier:
            raise NoResultsError("No identifier available for OAI-PMH")

        # Apply rate limiting
        self.rate_limiter.wait()

        # Make OAI-PMH request
        params = {
            "verb": "GetRecord",
            "identifier": identifier,
            "metadataPrefix": "oai_dc",
        }

        try:
            response = requests.get(self.oai_url, params=params, timeout=30)

            if response.status_code != 200:
                raise APIError(
                    f"OAI-PMH error: {response.status_code}",
                    status_code=response.status_code,
                )

            # Parse XML response
            root = self._parse_oai_response(response.text)

            # Extract metadata
            record = root.find(".//oai:record", self.namespaces)
            if record is None:
                raise NoResultsError("No record found in OAI-PMH response")

            # Extract PDF URL from identifiers
            identifiers = record.findall(".//dc:identifier", self.namespaces)
            pdf_url = self._extract_pdf_url_from_identifiers(
                [id.text for id in identifiers if id.text]
            )

            if not pdf_url:
                raise NoPDFFoundError("No PDF found in OAI-PMH record")

            # Extract other metadata
            rights = record.findall(".//dc:rights", self.namespaces)
            is_open_access = any("openAccess" in r.text for r in rights if r.text)

            return PDFRecord(
                paper_id=paper.paper_id or f"hal_{identifier.replace('oai:HAL:', '')}",
                pdf_url=pdf_url,
                source=self.source_name,
                discovery_timestamp=datetime.now(),
                confidence_score=0.85,
                version_info={
                    "hal_id": identifier,
                    "oai_datestamp": getattr(
                        record.find(".//oai:datestamp", self.namespaces),
                        "text",
                        "unknown",
                    ),
                },
                validation_status="verified",
                license="open_access" if is_open_access else None,
            )

        except requests.RequestException as e:
            raise APIError(f"OAI-PMH request failed: {str(e)}") from e

    def _discover_via_search(self, paper: Paper) -> PDFRecord:
        """Discover PDF using HAL Search API.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Apply rate limiting
        self.rate_limiter.wait()

        # Build search query
        query_parts = []
        if paper.doi:
            query_parts.append(f'doiId_s:"{paper.doi}"')
        else:
            query_parts.append(f'title_t:"{paper.title}"')

        params: Dict[str, Union[str, int]] = {
            "q": " OR ".join(query_parts),
            "fl": "docid,title_s,authFullName_s,files_s,doiId_s,openAccess_bool",
            "rows": 10,
            "wt": "json",
        }

        try:
            response = requests.get(self.search_url, params=params, timeout=30)

            if response.status_code != 200:
                raise APIError(
                    f"Search API error: {response.status_code}",
                    status_code=response.status_code,
                )

            data = response.json()
            docs = data.get("response", {}).get("docs", [])

            if not docs:
                raise NoResultsError(
                    "No results found in HAL", query=" OR ".join(query_parts)
                )

            # Find document with PDF
            for doc in docs:
                files = doc.get("files_s", [])
                pdf_url = self._extract_pdf_url_from_identifiers(files)

                if pdf_url:
                    return PDFRecord(
                        paper_id=paper.paper_id or f"hal_{doc.get('docid', 'unknown')}",
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.85,
                        version_info={
                            "hal_id": doc.get("docid"),
                        },
                        validation_status="verified",
                        license="open_access"
                        if doc.get("openAccess_bool", False)
                        else None,
                    )

            raise NoPDFFoundError(
                "No PDF found in HAL search results", results_count=len(docs)
            )

        except requests.RequestException as e:
            raise APIError(f"Search API request failed: {str(e)}") from e

    def _build_oai_identifier(self, paper: Paper) -> Optional[str]:
        """Build OAI identifier for HAL.

        Args:
            paper: Paper to build identifier for

        Returns:
            OAI identifier or None
        """
        # Try DOI first
        if paper.doi:
            return f"oai:HAL:{paper.doi}"

        # Try to extract HAL ID from URLs
        hal_id = self._extract_hal_id_from_urls(paper)
        if hal_id:
            return f"oai:HAL:{hal_id}v1"

        return None

    def _extract_hal_id_from_urls(self, paper: Paper) -> Optional[str]:
        """Extract HAL ID from paper URLs.

        Args:
            paper: Paper to extract HAL ID from

        Returns:
            HAL ID or None
        """
        if not paper.urls:
            return None

        for url in paper.urls:
            if isinstance(url, str) and "hal.science" in url:
                match = self.hal_id_pattern.search(url)
                if match:
                    return match.group(1)

        return None

    def _extract_pdf_url_from_identifiers(
        self, identifiers: List[str]
    ) -> Optional[str]:
        """Extract PDF URL from HAL identifiers.

        Args:
            identifiers: List of identifiers

        Returns:
            PDF URL or None
        """
        if not identifiers:
            return None

        # Priority order: .pdf files, /file/, /document
        for identifier in identifiers:
            if identifier and identifier.endswith(".pdf"):
                return identifier

        for identifier in identifiers:
            if identifier and "/file/" in identifier:
                return identifier

        for identifier in identifiers:
            if identifier and "/document" in identifier:
                return identifier

        return None

    def _parse_oai_response(self, xml_text: str) -> ET.Element:
        """Parse OAI-PMH XML response.

        Args:
            xml_text: XML response text

        Returns:
            Parsed XML root element

        Raises:
            Exception: If response contains OAI error or parsing fails
        """
        root = ET.fromstring(xml_text)

        # Check for OAI errors
        error = root.find(".//oai:error", self.namespaces)
        if error is not None:
            error_code = error.get("code", "unknown")
            error_text = error.text or "Unknown error"
            raise APIError(f"OAI-PMH error ({error_code}): {error_text}")

        return root
