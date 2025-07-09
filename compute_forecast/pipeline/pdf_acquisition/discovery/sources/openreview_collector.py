"""OpenReview PDF collector implementation."""

import time
import logging
from typing import List, Optional, Any
from datetime import datetime

import openreview
from rapidfuzz import fuzz

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
)
from .venue_mappings import OPENREVIEW_VENUES, get_venue_invitation, is_venue_supported


logger = logging.getLogger(__name__)


class OpenReviewPDFCollector(BasePDFCollector):
    """Collector for PDFs from OpenReview platform."""

    def __init__(self):
        """Initialize OpenReview collector."""
        super().__init__("openreview")

        # Initialize OpenReview client
        self.client = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net"
        )

        # Copy venue mapping from config
        self.venue_mapping = {k: v["venue_id"] for k, v in OPENREVIEW_VENUES.items()}

        # Search configuration
        self.title_similarity_threshold = 85  # Minimum fuzzy match score
        self.author_match_threshold = 0.5  # Fraction of authors that must match

        # Rate limiting
        self.min_request_interval = 0.5  # Seconds between requests
        self.last_request_time = 0
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.

        Args:
            paper: Paper to find PDF for

        Returns:
            PDFRecord with discovered PDF information

        Raises:
            Exception: If PDF cannot be discovered
        """
        # Check if venue/year is supported
        if not is_venue_supported(paper.venue, paper.year):
            raise ValueError(
                f"{paper.venue} {paper.year} is not available on OpenReview"
            )

        # Try title-based search first
        logger.info(f"Searching for '{paper.title}' in {paper.venue} {paper.year}")

        try:
            submission = self._search_by_title(paper)
            if submission:
                return self._create_pdf_record(paper, submission, confidence=0.95)
        except Exception as e:
            logger.warning(f"Title search failed: {e}")

        # Fallback to author-based search
        logger.info(f"Falling back to author search for paper {paper.paper_id}")

        try:
            submission = self._search_by_authors(paper)
            if submission:
                return self._create_pdf_record(paper, submission, confidence=0.75)
        except Exception as e:
            logger.warning(f"Author search failed: {e}")

        raise Exception(f"PDF not found for paper '{paper.title}' on OpenReview")

    def _search_by_title(self, paper: Paper) -> Optional[Any]:
        """Search for paper by title.

        Args:
            paper: Paper to search for

        Returns:
            OpenReview submission object if found, None otherwise
        """
        invitation = get_venue_invitation(paper.venue, paper.year)

        # Search for papers in the venue
        submissions = self._make_api_request(
            lambda: self.client.get_all_notes(invitation=invitation, details="original")
        )

        # Apply manual limit to avoid memory issues
        if len(submissions) > 1000:
            submissions = submissions[:1000]

        # Find best title match
        best_match = None
        best_score = 0

        for submission in submissions:
            # Get title from submission
            submission_title = self._extract_title(submission)
            if not submission_title:
                continue

            # Calculate similarity
            score = fuzz.ratio(paper.title.lower(), submission_title.lower())

            if score > best_score and score >= self.title_similarity_threshold:
                best_score = score
                best_match = submission

                # Perfect match, no need to continue
                if score == 100:
                    break

        if best_match:
            logger.info(
                f"Found title match with score {best_score}: "
                f"'{self._extract_title(best_match)}'"
            )
            return best_match

        return None

    def _search_by_authors(self, paper: Paper) -> Optional[Any]:
        """Search for paper by authors.

        Args:
            paper: Paper to search for

        Returns:
            OpenReview submission object if found, None otherwise
        """
        invitation = get_venue_invitation(paper.venue, paper.year)

        # Get author names for search
        paper_authors = [author.name.lower() for author in paper.authors]

        # Search for papers by first author
        if paper.authors:
            first_author = paper.authors[0].name
            submissions = self._make_api_request(
                lambda: self.client.get_all_notes(
                    invitation=invitation,
                    content={"authors": first_author},
                    details="original",
                )
            )

            # Apply manual limit to avoid memory issues
            if len(submissions) > 100:
                submissions = submissions[:100]

            # Check author overlap
            for submission in submissions:
                submission_authors = self._extract_authors(submission)
                if not submission_authors:
                    continue

                # Calculate author overlap
                submission_authors_lower = [a.lower() for a in submission_authors]
                matches = sum(
                    1
                    for author in paper_authors
                    if any(author in s_author for s_author in submission_authors_lower)
                )

                match_ratio = matches / len(paper_authors)

                if match_ratio >= self.author_match_threshold:
                    logger.info(
                        f"Found author match ({matches}/{len(paper_authors)} authors): "
                        f"'{self._extract_title(submission)}'"
                    )
                    return submission

        return None

    def _create_pdf_record(
        self, paper: Paper, submission: Any, confidence: float
    ) -> PDFRecord:
        """Create PDF record from OpenReview submission.

        Args:
            paper: Original paper
            submission: OpenReview submission object
            confidence: Confidence score for the match

        Returns:
            PDFRecord instance
        """
        forum_id = submission.forum
        pdf_url = self._build_pdf_url(forum_id)

        return PDFRecord(
            paper_id=paper.paper_id or f"openreview_{forum_id}",
            pdf_url=pdf_url,
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=confidence,
            version_info={
                "forum_id": forum_id,
                "submission_id": submission.id,
                "title": self._extract_title(submission),
                "venue": paper.venue,
                "year": paper.year,
            },
            validation_status="valid",
        )

    def _build_pdf_url(self, forum_id: str) -> str:
        """Build PDF URL from forum ID.

        Args:
            forum_id: OpenReview forum ID

        Returns:
            Full PDF URL
        """
        return f"https://openreview.net/pdf?id={forum_id}"

    def _extract_title(self, submission: Any) -> Optional[str]:
        """Extract title from submission object.

        Args:
            submission: OpenReview submission

        Returns:
            Title string or None
        """
        if hasattr(submission, "content") and isinstance(submission.content, dict):
            title_field = submission.content.get("title", {})
            if isinstance(title_field, dict):
                return str(title_field.get("value", ""))
            return str(title_field) if title_field else None
        return None

    def _extract_authors(self, submission: Any) -> List[str]:
        """Extract authors from submission object.

        Args:
            submission: OpenReview submission

        Returns:
            List of author names
        """
        if hasattr(submission, "content") and isinstance(submission.content, dict):
            authors_field = submission.content.get("authors", {})
            if isinstance(authors_field, dict):
                authors = authors_field.get("value", [])
                if isinstance(authors, list):
                    return authors
        return []

    def _make_api_request(self, request_func):
        """Make API request with rate limiting and retry logic.

        Args:
            request_func: Function that makes the API request

        Returns:
            API response

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)

            try:
                self.last_request_time = time.time()
                return request_func()

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Check for rate limiting
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                else:
                    # For other errors, fail immediately
                    raise

        raise Exception(f"Failed after {self.max_retries} retries: {last_error}")
