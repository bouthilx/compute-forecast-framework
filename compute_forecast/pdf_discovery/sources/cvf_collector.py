"""CVF Open Access PDF collector for computer vision conferences."""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper

logger = logging.getLogger(__name__)


class CVFCollector(BasePDFCollector):
    """Collector for Computer Vision Foundation open access papers."""

    # Class constants
    FUZZY_MATCH_THRESHOLD = 85
    REQUEST_TIMEOUT = 30
    CONFIDENCE_SCORE = 0.95

    def __init__(self):
        """Initialize CVF collector."""
        super().__init__("cvf")
        self.base_url = "https://openaccess.thecvf.com/"
        self.supported_venues = ["CVPR", "ICCV", "ECCV", "WACV"]

        # Conference schedules
        self.venue_schedules = {
            "CVPR": "annual",  # Every year
            "ICCV": "biannual_odd",  # Odd years only (2019, 2021, 2023...)
            "ECCV": "biannual_even",  # Even years only (2020, 2022, 2024...)
            "WACV": "annual",  # Every year
        }

        # Cache for proceedings pages to avoid repeated fetches
        self._proceedings_cache: Dict[Tuple[str, int], str] = {}

        # Configure timeout for HTTP requests
        self.request_timeout = self.REQUEST_TIMEOUT

    def _validate_venue_year(self, venue: str, year: int) -> bool:
        """Validate if a conference occurs in a given year.

        Args:
            venue: Conference name
            year: Publication year

        Returns:
            True if the conference occurs in that year
        """
        schedule = self.venue_schedules.get(venue, "annual")

        if schedule == "annual":
            return True
        elif schedule == "biannual_odd":
            return year % 2 == 1
        elif schedule == "biannual_even":
            return year % 2 == 0

        return True

    def _construct_proceedings_url(self, venue: str, year: int) -> str:
        """Construct proceedings URL for a venue and year.

        Args:
            venue: Conference name (e.g., "CVPR")
            year: Conference year

        Returns:
            Full proceedings URL
        """
        return urljoin(self.base_url, f"{venue}{year}")

    def _construct_pdf_url(self, venue: str, year: int, paper_id: str) -> str:
        """Construct PDF URL from components.

        Args:
            venue: Conference name
            year: Conference year
            paper_id: Paper identifier from proceedings

        Returns:
            Full PDF URL
        """
        return urljoin(self.base_url, f"{venue}{year}/papers/{paper_id}.pdf")

    def _search_proceedings_page(
        self, venue: str, year: int, paper_title: str
    ) -> Optional[str]:
        """Search proceedings page for paper by title.

        Args:
            venue: Conference name
            year: Conference year
            paper_title: Title to search for

        Returns:
            Paper ID if found, None otherwise
        """
        cache_key = (venue, year)

        # Fetch proceedings page (use cache if available)
        if cache_key not in self._proceedings_cache:
            proceedings_url = self._construct_proceedings_url(venue, year)

            try:
                response = requests.get(proceedings_url, timeout=self.request_timeout)
                response.raise_for_status()
                self._proceedings_cache[cache_key] = response.text
                logger.info(f"Fetched CVF proceedings for {venue}{year}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch CVF proceedings for {venue}{year}: {e}")
                return None

        # Parse proceedings HTML
        html_content = self._proceedings_cache[cache_key]
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all paper links
        # CVF uses pattern: /content/{venue}{year}/papers/{paper_id}.pdf
        pdf_pattern = re.compile(rf"/content/{venue}{year}/papers/([^/]+)\.pdf")

        papers_found = []

        # Look for all links to PDFs
        for link in soup.find_all("a", href=pdf_pattern):
            href = link.get("href", "")
            match = pdf_pattern.search(href)
            if match:
                paper_id = match.group(1)
                # Get the link text as title
                link_title = link.get_text(strip=True)
                if link_title:
                    papers_found.append((paper_id, link_title))

        if not papers_found:
            logger.warning(f"No papers found in {venue}{year} proceedings")
            return None

        # Find best title match
        best_match = None
        best_score = 0

        for paper_id, found_title in papers_found:
            # Calculate fuzzy match score
            score = fuzz.ratio(paper_title.lower(), found_title.lower())

            if score > best_score:
                best_score = score
                best_match = paper_id

        # Return if score is above threshold
        if best_score >= self.FUZZY_MATCH_THRESHOLD:
            logger.info(f"Found paper '{paper_title}' with score {best_score}")
            return best_match

        logger.warning(f"No match found for '{paper_title}' (best score: {best_score})")
        return None

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            ValueError: If PDF cannot be discovered
        """
        # Check if venue is supported
        if paper.venue not in self.supported_venues:
            raise ValueError(
                f"Venue '{paper.venue}' is not a CVF venue. Supported: {self.supported_venues}"
            )

        # Validate venue/year combination
        if not self._validate_venue_year(paper.venue, paper.year):
            raise ValueError(f"{paper.venue} does not occur in {paper.year}")

        # Search proceedings for paper
        paper_id = self._search_proceedings_page(paper.venue, paper.year, paper.title)

        if not paper_id:
            raise ValueError(
                f"Could not find paper '{paper.title}' in {paper.venue}{paper.year} proceedings"
            )

        # Construct PDF URL
        pdf_url = self._construct_pdf_url(paper.venue, paper.year, paper_id)

        # Create and return PDF record
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=pdf_url,
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=self.CONFIDENCE_SCORE,
            version_info={
                "venue": paper.venue,
                "year": paper.year,
                "cvf_paper_id": paper_id,
            },
            validation_status="validated",
            license="CVF Open Access",
        )
