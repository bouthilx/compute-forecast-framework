"""JMLR and TMLR PDF collector."""

import re
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from difflib import SequenceMatcher

from compute_forecast.data.models import Paper
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector

logger = logging.getLogger(__name__)


class JMLRCollector(BasePDFCollector):
    """Collector for JMLR and TMLR papers."""

    # Constants for configuration
    JMLR_CONFIDENCE_SCORE = 0.95
    TMLR_CONFIDENCE_SCORE = 0.90
    DEFAULT_TIMEOUT = 10
    TMLR_TIMEOUT = 30
    FUZZY_MATCH_THRESHOLD = 0.8

    def __init__(self):
        """Initialize the JMLR/TMLR PDF collector."""
        super().__init__("jmlr_tmlr")
        self.jmlr_base_url = "https://jmlr.org/papers/"
        self.tmlr_base_url = "https://jmlr.org/tmlr/papers/"
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; Academic Paper Collector)"}
        )

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Determine if this is a JMLR or TMLR paper
        venue = paper.venue.lower() if paper.venue else ""
        # Note: Paper model only has 'venue' field, no separate 'journal' field

        is_jmlr = "jmlr" in venue or "journal of machine learning research" in venue
        is_tmlr = (
            "tmlr" in venue or "transactions on machine learning research" in venue
        )

        if not (is_jmlr or is_tmlr):
            raise ValueError(f"Paper {paper.paper_id} is not from JMLR or TMLR")

        if is_jmlr:
            return self._discover_jmlr(paper)
        else:
            return self._discover_tmlr(paper)

    def _discover_jmlr(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a JMLR paper.

        JMLR URL pattern: https://jmlr.org/papers/v{volume}/{paper}.pdf
        """
        # Try to extract volume and paper ID from paper metadata
        volume_info = self._extract_jmlr_volume_info(paper)

        if not volume_info:
            # Fall back to searching the JMLR website
            return self._search_jmlr_website(paper)

        pdf_url = f"{self.jmlr_base_url}v{volume_info['volume']}/{volume_info['paper_id']}.pdf"

        # Verify the URL exists
        try:
            response = self.session.head(pdf_url, timeout=self.DEFAULT_TIMEOUT)
            if response.status_code == 200:
                return PDFRecord(
                    paper_id=paper.paper_id or f"jmlr_{volume_info['paper_id']}",
                    pdf_url=pdf_url,
                    source=self.source_name,
                    discovery_timestamp=datetime.now(),
                    confidence_score=self.JMLR_CONFIDENCE_SCORE,
                    version_info={"type": "published", "venue": "JMLR"},
                    validation_status="verified",
                    license="JMLR",
                )
        except Exception as e:
            logger.debug(f"Failed to verify JMLR URL {pdf_url}: {e}")

        # If direct URL construction failed, search the website
        return self._search_jmlr_website(paper)

    def _discover_tmlr(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a TMLR paper by searching the TMLR papers page."""
        try:
            response = self.session.get(self.tmlr_base_url, timeout=self.TMLR_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find paper by title
            paper_title = paper.title.lower().strip()

            # TMLR papers are listed with links
            for link in soup.find_all("a"):
                link_text = link.get_text().lower().strip()

                # Check if this link contains the paper title
                if self._fuzzy_title_match(paper_title, link_text):
                    href = link.get("href")
                    if href and href.endswith(".pdf"):
                        pdf_url = urljoin(self.tmlr_base_url, href)

                        return PDFRecord(
                            paper_id=paper.paper_id
                            or f"tmlr_{href.split('/')[-1].replace('.pdf', '')}",
                            pdf_url=pdf_url,
                            source=self.source_name,
                            discovery_timestamp=datetime.now(),
                            confidence_score=self.TMLR_CONFIDENCE_SCORE,
                            version_info={"type": "published", "venue": "TMLR"},
                            validation_status="discovered",
                            license="TMLR",
                        )

            raise ValueError(f"Could not find TMLR paper: {paper.title}")

        except Exception as e:
            logger.error(f"Error discovering TMLR paper {paper.paper_id}: {e}")
            raise

    def _extract_jmlr_volume_info(self, paper: Paper) -> Optional[Dict[str, Any]]:
        """Extract volume and paper ID from paper metadata.

        Returns:
            Dictionary with 'volume' and 'paper_id' keys, or None if not found
        """
        # Check if paper has URLs that might contain volume info
        if paper.urls:
            for url in paper.urls:
                # Pattern: jmlr.org/papers/v23/21-1234.html or similar
                match = re.search(r"jmlr\.org/papers/v(\d+)/([^/\s]+)(?:\.html)?", url)
                if match:
                    return {
                        "volume": match.group(1),
                        "paper_id": match.group(2).replace(".html", ""),
                    }

        # Check if paper has volume field
        if hasattr(paper, "volume") and paper.volume:
            # Need to find paper ID - might be in URLs or other fields
            paper_id = None
            if paper.urls:
                for url in paper.urls:
                    # Extract paper ID from URL
                    match = re.search(r"/([^/]+?)(?:\.html)?$", url)
                    if match:
                        paper_id = match.group(1)
                        break

            if paper_id:
                return {"volume": paper.volume, "paper_id": paper_id}

        return None

    def _search_jmlr_website(self, paper: Paper) -> PDFRecord:
        """Search JMLR website for a paper by title.

        Implements basic title-based search as fallback when URL construction fails.
        """
        try:
            # Search the JMLR papers page
            response = self.session.get(self.jmlr_base_url, timeout=self.TMLR_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            paper_title = paper.title.lower().strip()

            # Look for links that might contain the paper title
            for link in soup.find_all("a"):
                link_text = link.get_text().lower().strip()

                # Use improved fuzzy matching
                if self._improved_fuzzy_title_match(paper_title, link_text):
                    href = link.get("href")
                    if href:
                        # Check if this links to a PDF or paper page
                        if href.endswith(".pdf"):
                            pdf_url = (
                                href
                                if href.startswith("http")
                                else self.jmlr_base_url + href
                            )

                            return PDFRecord(
                                paper_id=paper.paper_id
                                or f"jmlr_{href.split('/')[-1].replace('.pdf', '')}",
                                pdf_url=pdf_url,
                                source=self.source_name,
                                discovery_timestamp=datetime.now(),
                                confidence_score=self.TMLR_CONFIDENCE_SCORE,  # Lower confidence for search-based
                                version_info={"type": "published", "venue": "JMLR"},
                                validation_status="discovered",
                                license="JMLR",
                            )
                        elif "papers/v" in href:
                            # Extract volume info from link and construct PDF URL
                            match = re.search(r"/v(\d+)/([^/\s]+)(?:\.html)?", href)
                            if match:
                                volume = match.group(1)
                                paper_id = match.group(2).replace(".html", "")
                                pdf_url = (
                                    f"{self.jmlr_base_url}v{volume}/{paper_id}.pdf"
                                )

                                return PDFRecord(
                                    paper_id=paper.paper_id or f"jmlr_{paper_id}",
                                    pdf_url=pdf_url,
                                    source=self.source_name,
                                    discovery_timestamp=datetime.now(),
                                    confidence_score=self.TMLR_CONFIDENCE_SCORE,
                                    version_info={"type": "published", "venue": "JMLR"},
                                    validation_status="discovered",
                                    license="JMLR",
                                )

            raise ValueError(f"Could not find JMLR paper: {paper.title}")

        except Exception as e:
            logger.error(
                f"Error searching JMLR website for paper {paper.paper_id}: {e}"
            )
            raise ValueError(
                f"Could not find JMLR paper {paper.paper_id} through website search: {e}"
            )

    def _fuzzy_title_match(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be the same paper.

        Simple implementation - can be enhanced with fuzzy string matching.
        """

        # Remove common words and punctuation for comparison
        def normalize_title(title):
            # Remove punctuation and convert to lowercase
            title = re.sub(r"[^\w\s]", " ", title.lower())
            # Remove extra whitespace
            title = " ".join(title.split())
            return title

        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)

        # Check if one title contains the other (handling subtitles)
        return norm_title1 in norm_title2 or norm_title2 in norm_title1

    def _improved_fuzzy_title_match(self, title1: str, title2: str) -> bool:
        """Improved fuzzy title matching using sequence similarity.

        Uses both substring matching and sequence similarity for better accuracy.
        """

        def normalize_title(title):
            # Remove punctuation and convert to lowercase
            title = re.sub(r"[^\w\s]", " ", title.lower())
            # Remove extra whitespace and common words
            words = title.split()
            # Remove very common words that don't help with matching
            stop_words = {
                "a",
                "an",
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            }
            words = [w for w in words if w not in stop_words and len(w) > 2]
            return " ".join(words)

        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)

        # If one title is empty after normalization, fall back to simple check
        if not norm_title1 or not norm_title2:
            return self._fuzzy_title_match(title1, title2)

        # Check substring containment (for subtitles and variations)
        if norm_title1 in norm_title2 or norm_title2 in norm_title1:
            return True

        # Use sequence similarity for more robust matching
        similarity = SequenceMatcher(None, norm_title1, norm_title2).ratio()
        return similarity >= self.FUZZY_MATCH_THRESHOLD
