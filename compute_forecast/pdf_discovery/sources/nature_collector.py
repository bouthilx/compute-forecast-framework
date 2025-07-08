"""Nature.com PDF collector for open access papers."""

import re
import logging
import time
import requests
from typing import Optional
from datetime import datetime

from compute_forecast.data.models import Paper
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector
from compute_forecast.core.exceptions import (
    UnsupportedSourceError,
    PDFNotAvailableError,
    PDFNetworkError,
)
from .doi_resolver_collector import DOIResolverCollector

logger = logging.getLogger(__name__)


class NaturePDFCollector(BasePDFCollector):
    """Nature PDF collector for open access content from Nature Communications and Scientific Reports."""

    def __init__(self, email: str):
        """Initialize Nature PDF collector.

        Args:
            email: Contact email for API access

        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError("Email is required for Nature PDF discovery")

        super().__init__("nature")
        self.email = email
        self.doi_resolver = DOIResolverCollector(email)

        # Nature-specific configuration
        self.base_url = "https://www.nature.com"
        self.supported_journals = {
            "nature communications": "ncomms",
            "nat commun": "ncomms",
            "nat. commun.": "ncomms",
            "scientific reports": "srep",
            "sci rep": "srep",
            "sci. rep.": "srep",
        }

        # Rate limiting - be respectful to Nature servers
        self.request_delay = 2.0  # 2 seconds between requests
        self.last_request_time = 0

        # Patterns for Nature DOIs
        self.nature_doi_pattern = re.compile(
            r"10\.1038/(?:s41467|srep|ncomms)-?\d+(?:-\d+)?(?:-\w+)?"
        )

    def is_nature_paper(self, paper: Paper) -> bool:
        """Check if a paper is from a supported Nature journal.

        Args:
            paper: Paper to check

        Returns:
            True if paper is from Nature Communications or Scientific Reports
        """
        # Check by venue
        if paper.venue:
            venue_lower = paper.venue.lower()
            if any(
                journal in venue_lower for journal in self.supported_journals.keys()
            ):
                return True

        # Check by DOI pattern
        if paper.doi and self.nature_doi_pattern.match(paper.doi):
            return True

        # Check URLs for nature.com
        if paper.urls:
            for url in paper.urls:
                if isinstance(url, str) and "nature.com" in url:
                    return True

        return False

    def _extract_article_id_from_doi(self, doi: str) -> Optional[str]:
        """Extract Nature article ID from DOI.

        Args:
            doi: DOI string

        Returns:
            Article ID or None if not a Nature DOI
        """
        # Nature DOI patterns:
        # 10.1038/s41467-023-36000-6 -> s41467-023-36000-6
        # 10.1038/srep12345 -> srep12345
        # 10.1038/ncomms1234 -> ncomms1234
        match = self.nature_doi_pattern.match(doi)
        if match:
            # Extract the part after 10.1038/
            return doi.split("10.1038/")[1]
        return None

    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _check_open_access_availability(self, article_id: str) -> Optional[str]:
        """Check if a Nature article has open access PDF available.

        Args:
            article_id: Nature article ID (e.g., 's41467-023-36000-6')

        Returns:
            PDF URL if available, None otherwise
        """
        # Nature open access PDFs follow predictable patterns
        pdf_url = f"{self.base_url}/articles/{article_id}.pdf"

        try:
            self._wait_for_rate_limit()

            # Use HEAD request to check if PDF exists without downloading
            response = requests.head(
                pdf_url,
                timeout=30,
                allow_redirects=True,
                headers={"User-Agent": f"Academic PDF Discovery Bot ({self.email})"},
            )

            # Check if we get a successful response or open access redirect
            if response.status_code == 200:
                # Check content type to ensure it's a PDF
                content_type = response.headers.get("Content-Type", "")
                if "application/pdf" in content_type:
                    logger.info(f"Found open access PDF at {pdf_url}")
                    return pdf_url

            # If we get redirected to authentication, it's not open access
            if response.status_code in [302, 303] and "idp.nature.com" in str(
                response.headers.get("Location", "")
            ):
                logger.debug(
                    f"Article {article_id} requires authentication - not open access"
                )
                return None

        except requests.RequestException as e:
            logger.warning(
                f"Network error checking Nature PDF availability for {article_id}: {e}"
            )
            raise PDFNetworkError(
                f"Failed to check PDF availability due to network error: {e}"
            )
        except Exception as e:
            logger.warning(
                f"Error checking Nature PDF availability for {article_id}: {e}"
            )

        return None

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single Nature paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            UnsupportedSourceError: If paper is not from a supported Nature journal
            PDFNotAvailableError: If no open access PDF can be found
            PDFNetworkError: If network requests fail during PDF discovery
        """
        logger.debug(f"Attempting Nature PDF discovery for paper {paper.paper_id}")

        # First check if this is actually a Nature paper
        if not self.is_nature_paper(paper):
            raise UnsupportedSourceError(
                f"Paper {paper.paper_id} is not from a supported Nature journal"
            )

        # If paper has DOI, try multiple strategies
        if paper.doi:
            logger.info(f"Paper {paper.paper_id} has DOI: {paper.doi}")

            # Strategy 1: Direct Nature PDF check
            article_id = self._extract_article_id_from_doi(paper.doi)
            if article_id:
                pdf_url = self._check_open_access_availability(article_id)
                if pdf_url:
                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.95,  # High confidence for direct Nature URLs
                        version_info={
                            "doi": paper.doi,
                            "article_id": article_id,
                            "journal": self._identify_journal(paper),
                        },
                        validation_status="pending",
                        # License assignment based on Nature journal policies:
                        # Nature Communications (ncomms, s41467): typically CC-BY
                        # Scientific Reports (srep): typically CC-BY-NC
                        # Note: Actual license may vary per article - this is a reasonable default
                        license="CC-BY"
                        if "ncomms" in article_id or "s41467" in article_id
                        else "CC-BY-NC",
                    )

            # Strategy 2: Use DOI resolver (Unpaywall/CrossRef) for open access versions
            logger.info(f"Falling back to DOI resolver for paper {paper.paper_id}")
            try:
                pdf_record = self.doi_resolver._discover_single(paper)
                # Update the source to indicate it came through Nature collector
                pdf_record.source = f"{self.source_name}_via_doi"
                pdf_record.version_info["nature_paper"] = True
                pdf_record.version_info["journal"] = self._identify_journal(paper)
                return pdf_record
            except Exception as e:
                logger.debug(f"DOI resolver failed: {e}")

        # No PDF found
        raise PDFNotAvailableError(
            f"No open access PDF found for Nature paper {paper.paper_id}"
        )

    def _identify_journal(self, paper: Paper) -> str:
        """Identify which Nature journal the paper is from.

        Args:
            paper: Paper to identify journal for

        Returns:
            Journal name or 'unknown'
        """
        if paper.venue:
            venue_lower = paper.venue.lower()
            for journal_name, journal_code in self.supported_journals.items():
                if journal_name in venue_lower:
                    return journal_name.title()

        if paper.doi:
            if "s41467" in paper.doi or "ncomms" in paper.doi:
                return "Nature Communications"
            elif "srep" in paper.doi:
                return "Scientific Reports"

        return "unknown"
