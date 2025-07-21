"""OpenReview adapter v2 - Paperoni-inspired implementation with improved decision extraction."""

from typing import List, Any, Optional
from datetime import datetime
import openreview
import re
from fnmatch import fnmatch
from functools import reduce
import time
import os

from .base import BasePaperoniAdapter
from ..models import SimplePaper

# Disable tqdm progress bars
os.environ["TQDM_DISABLE"] = "1"


class OpenReviewAdapterV2(BasePaperoniAdapter):
    """
    Paperoni-inspired OpenReview adapter with sophisticated decision extraction.

    Key improvements over v1:
    - Smart decision extraction with multiple fallbacks
    - Proper filtering of rejected/withdrawn papers
    - Optimized queries based on venue and year
    - Better handling of API v1 vs v2 differences
    """

    def __init__(self, config=None):
        super().__init__("openreview_v2", config)
        self.client_v2 = None
        self.client_v1 = None

    def get_supported_venues(self) -> List[str]:
        """Return all supported OpenReview venues."""
        return ["iclr", "ICLR", "tmlr", "TMLR", "colm", "COLM", "rlc", "RLC"]

    def get_available_years(self, venue: str) -> List[int]:
        """Get available years for each venue."""
        current_year = datetime.now().year
        venue_lower = venue.lower()

        if venue_lower == "iclr":
            # ICLR started using OpenReview around 2013
            return list(range(2013, current_year + 1))
        elif venue_lower == "tmlr":
            # TMLR started in 2022
            return list(range(2022, current_year + 1))
        elif venue_lower == "colm":
            # COLM started in 2024
            return list(range(2024, current_year + 1))
        elif venue_lower == "rlc":
            # RLC started in 2024
            return list(range(2024, current_year + 2))  # Include 2025
        else:
            return []

    def _create_paperoni_scraper(self):
        """Create OpenReview clients for both API versions."""
        try:
            # Create API v2 client (for 2024+)
            self.client_v2 = openreview.api.OpenReviewClient(
                baseurl="https://api2.openreview.net"
            )

            # Create API v1 client (for 2023 and earlier)
            self.client_v1 = openreview.Client(baseurl="https://api.openreview.net")

            return self.client_v2  # Return v2 as default
        except Exception as e:
            self.logger.error(f"Failed to create OpenReview clients: {e}")
            raise

    def _get_api_client(self, venue: str, year: int) -> Any:
        """Get appropriate API client based on venue and year."""
        # Ensure clients are initialized
        if not self.client_v2 or not self.client_v1:
            self._create_paperoni_scraper()

        # Use v1 for ICLR 2023 and earlier, v2 for everything else
        if venue.lower() == "iclr" and year <= 2023:
            return self.client_v1
        else:
            return self.client_v2

    def _get_venue_id(self, venue_lower: str, year: int) -> Optional[str]:
        """Get OpenReview venue ID based on venue and year."""
        if venue_lower == "iclr":
            return f"ICLR.cc/{year}/Conference"
        elif venue_lower == "colm":
            return f"colmweb.org/COLM/{year}/Conference"
        elif venue_lower == "rlc":
            return f"rl-conference.cc/RLC/{year}/Conference"
        elif venue_lower == "tmlr":
            return "TMLR"  # TMLR doesn't use year in ID
        else:
            return None

    def _venues_from_wildcard(self, pattern: str, client: Any) -> List[str]:
        """Convert venue pattern with wildcards to actual venue IDs."""
        if isinstance(pattern, list):
            return reduce(
                list.__add__, [self._venues_from_wildcard(p, client) for p in pattern]
            )
        elif "*" not in pattern:
            return [pattern]
        else:
            try:
                members = client.get_group(id="venues").members
                return [
                    member
                    for member in members
                    if fnmatch(pat=pattern.lower(), name=member.lower())
                ]
            except Exception:
                # If venues group doesn't exist, return pattern as-is
                return [pattern]

    def _extract_field(self, content: dict, field_name: str, default=None):
        """Extract field value handling both API v1 and v2 formats."""
        if field_name not in content:
            return default

        value = content[field_name]

        # API v2 wraps values in dict with 'value' key
        if isinstance(value, dict) and "value" in value:
            return value["value"]

        return value

    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Main method to fetch papers from OpenReview with robust error handling."""
        papers = []
        venue_lower = venue.lower()

        # Get venue ID
        venue_id = self._get_venue_id(venue_lower, year)
        if not venue_id:
            self.logger.error(f"Unsupported venue for OpenReview: {venue}")
            return []

        # Rate limiting - small delay before starting
        time.sleep(0.5)

        try:
            # Choose strategy based on venue and year
            if venue_lower == "tmlr":
                # TMLR has special handling
                papers = self._get_tmlr_papers(year)
            elif venue_lower == "iclr" and year >= 2024:
                # Use optimized venueid query for ICLR 2024+
                papers = self._get_accepted_by_venueid(venue_id, venue, year)
            elif venue_lower == "iclr" and year <= 2023:
                # Use v1 API with batch decision fetching
                papers = self._get_conference_submissions_v1(venue_id, venue, year)
            else:
                # Standard approach for other venues
                papers = self._get_conference_submissions_v2(venue_id, venue, year)

            self.logger.info(
                f"Successfully collected {len(papers)} papers for {venue} {year}"
            )

        except openreview.OpenReviewException as e:
            # Handle OpenReview-specific errors
            self.logger.error(f"OpenReview API error for {venue} {year}: {e}")
            if "rate limit" in str(e).lower():
                self.logger.info("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)
            # Don't re-raise, return what we have

        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching papers for {venue} {year}: {e}"
            )
            import traceback

            self.logger.debug(traceback.format_exc())
            # Don't re-raise, return empty list

        return papers

    # Placeholder methods for Phase 2-5 implementation
    def _get_tmlr_papers(self, year: int) -> List[SimplePaper]:
        """Get TMLR papers published in a specific year."""
        papers = []

        try:
            # TMLR uses a different structure - get accepted papers
            submissions = list(
                self.client_v2.get_all_notes(
                    invitation="TMLR/-/Accepted", details="replies"
                )
            )

            self.logger.info(f"Found {len(submissions)} total TMLR papers")

            # Filter by publication year and convert
            for submission in submissions:
                try:
                    # Get publication date
                    pub_date = None
                    if hasattr(submission, "pdate") and submission.pdate:
                        pub_date = datetime.fromtimestamp(submission.pdate / 1000)
                    elif hasattr(submission, "cdate") and submission.cdate:
                        pub_date = datetime.fromtimestamp(submission.cdate / 1000)

                    if pub_date and pub_date.year != year:
                        continue
                    elif not pub_date:
                        continue

                    # TMLR papers are all accepted, no decision extraction needed
                    paper = self._convert_to_simple_paper(
                        submission, "accepted", "TMLR", year
                    )
                    if paper:
                        papers.append(paper)

                    # Respect batch size
                    if len(papers) >= self.config.batch_size:
                        break

                except Exception as e:
                    self.logger.debug(
                        f"Failed to parse TMLR submission {getattr(submission, 'id', 'unknown')}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Error fetching TMLR papers: {e}")

        return papers

    def _get_accepted_by_venueid(
        self, venue_id: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Get accepted papers using venueid for ICLR 2024+."""
        papers = []

        try:
            self.logger.info(f"Getting accepted papers for {venue_id} using venueid")

            # Use venueid to get only accepted papers
            submissions = list(
                self.client_v2.get_all_notes(content={"venueid": venue_id})
            )

            self.logger.info(f"Found {len(submissions)} accepted papers using venueid")

            for submission in submissions:
                try:
                    # For venueid-filtered papers, we know they're accepted
                    # But we still extract decision for classification (oral/poster/spotlight)
                    decision = self._extract_decision_smart(
                        submission, venue.lower(), year
                    )
                    if not decision:
                        decision = "accepted"  # Default for venueid-filtered papers

                    paper = self._convert_to_simple_paper(
                        submission, decision, venue, year
                    )
                    if paper:
                        papers.append(paper)

                except Exception as e:
                    self.logger.debug(
                        f"Failed to parse submission {getattr(submission, 'id', 'unknown')}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"Error getting accepted papers by venueid for {venue_id}: {e}"
            )

        return papers

    def _get_conference_submissions_v1(
        self, venue_id: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Get papers using API v1 for ICLR ≤2023."""
        papers: List[SimplePaper] = []

        # First, get all submissions
        invitation_formats = [
            f"{venue_id}/-/Blind_Submission",
            f"{venue_id}/-/Submission",
            f"{venue_id}/-/Paper",
        ]

        all_submissions = []
        for invitation in invitation_formats:
            try:
                self.logger.debug(f"Trying v1 invitation format: {invitation}")
                # Use iterget_notes for pagination
                from openreview import tools

                submissions_iter = tools.iterget_notes(
                    self.client_v1, invitation=invitation
                )
                all_submissions = list(submissions_iter)

                if all_submissions:
                    self.logger.info(
                        f"Found {len(all_submissions)} submissions using {invitation}"
                    )
                    break
            except Exception as e:
                self.logger.debug(f"Failed with invitation {invitation}: {e}")
                continue

        if not all_submissions:
            self.logger.error(f"No submissions found for {venue_id}")
            return papers

        # For ICLR, implement efficient decision extraction
        self.logger.info(
            f"Filtering {len(all_submissions)} submissions for accepted papers..."
        )

        # Try venue field approach first
        venue_filtered = []
        for submission in all_submissions:
            venue_field = submission.content.get("venue", "")

            # Check if this is an accepted paper based on venue field
            if self._is_accepted_by_venue_field(venue_field, year):
                # Cache the decision from venue field
                submission._cached_decision = self._extract_decision_from_venue(
                    venue_field
                )
                venue_filtered.append(submission)

        if len(venue_filtered) > 100:  # Sanity check
            self.logger.info(
                f"Used venue field to find {len(venue_filtered)} accepted papers"
            )
            submissions_to_process = venue_filtered
        else:
            # Fallback: Get all submissions and extract decisions
            self.logger.info(
                "Venue field unreliable, extracting decisions for all papers..."
            )
            submissions_to_process = all_submissions

        # Convert to SimplePaper
        for submission in submissions_to_process:
            try:
                decision = self._extract_decision_smart(submission, venue.lower(), year)

                # Skip rejected/withdrawn papers
                if decision and decision.lower() in ["rejected", "withdrawn"]:
                    continue

                paper = self._convert_to_simple_paper(submission, decision, venue, year)
                if paper:
                    papers.append(paper)

            except Exception as e:
                self.logger.debug(f"Failed to process submission: {e}")
                continue

        self.logger.info(
            f"Found {len(papers)} accepted papers out of {len(all_submissions)} total"
        )

        # Final safety check
        if len(papers) == 0 and len(all_submissions) > 100:
            self.logger.warning(
                f"No accepted papers found out of {len(all_submissions)} submissions - this might indicate a parsing issue"
            )

        return papers

    def _get_conference_submissions_v2(
        self, venue_id: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Get papers using API v2 for standard conferences."""
        papers: List[SimplePaper] = []

        # Try different invitation formats
        invitation_formats = [
            f"{venue_id}/-/Blind_Submission",
            f"{venue_id}/-/Submission",
            f"{venue_id}#-/Submission",  # Some venues use # instead of /
            f"{venue_id}/-/Paper",
        ]

        submissions = []
        for invitation in invitation_formats:
            try:
                self.logger.debug(f"Trying v2 invitation format: {invitation}")
                submissions = list(
                    self.client_v2.get_all_notes(
                        invitation=invitation, details="replies"
                    )
                )
                if submissions:
                    self.logger.info(
                        f"Found {len(submissions)} submissions using {invitation}"
                    )
                    break
            except Exception as e:
                self.logger.debug(f"Failed with invitation {invitation}: {e}")
                continue

        if not submissions:
            self.logger.error(f"No submissions found for {venue_id}")
            return papers

        # Process submissions
        self.logger.info(f"Processing {len(submissions)} submissions...")
        accepted_count = 0
        rejected_count = 0

        for submission in submissions:
            try:
                # Extract decision
                decision = self._extract_decision_smart(submission, venue.lower(), year)

                # Skip rejected/withdrawn papers
                if decision and decision.lower() in ["rejected", "withdrawn"]:
                    rejected_count += 1
                    continue

                paper = self._convert_to_simple_paper(submission, decision, venue, year)
                if paper:
                    papers.append(paper)
                    accepted_count += 1

            except Exception as e:
                self.logger.debug(f"Failed to process submission: {e}")
                continue

        self.logger.info(
            f"Processed {len(submissions)} submissions: {accepted_count} accepted, {rejected_count} rejected"
        )
        return papers

    def _is_accepted_by_venue_field(self, venue_field: str, year: int) -> bool:
        """Check if venue field indicates an accepted paper."""
        if not venue_field:
            return False

        venue_lower = venue_field.lower()

        # Different patterns for different years
        if f"{year}" in venue_field:
            # Skip if it says "Submitted to"
            if "submitted" in venue_lower:
                return False
            # Accept if it has acceptance indicators
            acceptance_indicators = ["poster", "oral", "spotlight", "notable"]
            return any(indicator in venue_lower for indicator in acceptance_indicators)

        return False

    def _extract_decision_from_venue(self, venue_field: str) -> str:
        """Extract specific decision from venue field."""
        venue_lower = venue_field.lower()

        if "oral" in venue_lower:
            return "Accept: oral"
        elif "spotlight" in venue_lower:
            return "Accept: spotlight"
        elif "notable" in venue_lower and "5%" in venue_field:
            return "Accept: notable-top-5%"
        elif "notable" in venue_lower and "25%" in venue_field:
            return "Accept: notable-top-25%"
        elif "poster" in venue_lower:
            return "Accept: poster"
        else:
            return "Accept"

    def _convert_to_simple_paper(
        self, submission: Any, decision: Optional[str], venue: str, year: int
    ) -> Optional[SimplePaper]:
        """Convert OpenReview submission to SimplePaper format."""
        try:
            content = submission.content if hasattr(submission, "content") else {}

            # Extract basic fields
            title = self._extract_field(content, "title", "")
            authors = self._extract_field(content, "authors", [])
            abstract = self._extract_field(content, "abstract", "")

            # Ensure authors is a list
            if not isinstance(authors, list):
                authors = [authors] if authors else []

            # Extract PDF URLs
            pdf_urls = []
            pdf_field = self._extract_field(content, "pdf")
            if pdf_field:
                if isinstance(pdf_field, str):
                    if not pdf_field.startswith("http"):
                        pdf_field = (
                            f"https://openreview.net{pdf_field}"
                            if pdf_field.startswith("/")
                            else f"https://openreview.net/{pdf_field}"
                        )
                    pdf_urls.append(pdf_field)

            # Paper URL
            paper_url = f"https://openreview.net/forum?id={submission.id}"

            # Classify the decision
            acceptance_type = self._classify_decision(decision) if decision else None

            # Create SimplePaper
            paper = SimplePaper(
                title=title,
                authors=authors,
                venue=venue.upper(),
                year=year,
                abstract=abstract,
                pdf_urls=pdf_urls,
                paper_id=submission.id,
                source_scraper=self.source_name,
                source_url=paper_url,
                extraction_confidence=0.95,
                decision=acceptance_type,
            )

            return paper

        except Exception as e:
            self.logger.warning(f"Failed to convert submission to SimplePaper: {e}")
            return None

    def _extract_decision_smart(
        self, submission: Any, venue_lower: str, year: int
    ) -> Optional[str]:
        """
        Extract decision using paperoni's sophisticated approach.

        Uses multiple fallback mechanisms in order:
        1. Cached decision (for v1 batch processing)
        2. Heuristics-based search through replies
        3. Venue field in content
        4. Venue ID
        5. Publication date
        6. Bibtex
        """
        try:
            # 1. Check if we have a cached decision from batch processing
            if hasattr(submission, "_cached_decision"):
                return str(submission._cached_decision) if submission._cached_decision else None

            # 2. Use heuristics-based approach for decision extraction from replies
            # Priority: lower rank = higher priority
            heuristics = [
                (5, r".*withdrawn?[^/]*$", "=withdrawn"),
                (10, r".*/decision$", "decision"),
                (20, r".*decision[^/]*$", "decision"),
                (30, r".*accept[^/]*$", "decision"),
                (40, r".*", "decision"),
                (40, r".*", "Decision"),
                (50, r".*meta_?review[^/]*$", "recommendation"),
            ]

            ranked_results = []

            # Check replies using heuristics
            if hasattr(submission, "details") and "replies" in submission.details:
                replies = submission.details["replies"]

                # Process in reverse order like paperoni
                for reply in reversed(replies):
                    # Handle both API v1 (single invitation) and v2 (invitations list)
                    invitations = reply.get(
                        "invitations", [reply.get("invitation", "")]
                    )
                    if isinstance(invitations, str):
                        invitations = [invitations]

                    for rank, pattern, field in heuristics:
                        if any(
                            re.match(pattern, inv, re.IGNORECASE) for inv in invitations
                        ):
                            if field.startswith("="):
                                # Direct decision value
                                ranked_results.append((rank, field[1:]))
                                break
                            else:
                                # Extract from content field
                                content = reply.get("content", {})
                                if field in content:
                                    value = self._extract_field(content, field)
                                    if value:
                                        ranked_results.append((rank, str(value)))
                                        break

            # Process ranked results
            if ranked_results:
                ranked_results.sort()
                # Get all decisions with the same (best) rank
                best_rank = ranked_results[0][0]
                decisions = {
                    decision for rank, decision in ranked_results if rank == best_rank
                }
                if len(decisions) == 1:
                    decision = decisions.pop()
                    return self._refine_decision(decision)

            # 3. Fallback: check venue field in content
            content = submission.content if hasattr(submission, "content") else {}
            venue_field = self._extract_field(content, "venue", "")
            if venue_field:
                refined = self._refine_decision(str(venue_field))
                if refined:
                    return refined

            # 4. Fallback: check venueid
            venueid = self._extract_field(content, "venueid", "")
            if venueid:
                refined = self._refine_decision(str(venueid))
                if refined:
                    return refined

            # 5. Check if paper was published (has pdate)
            if hasattr(submission, "pdate") and submission.pdate:
                return "published"

            # 6. Last resort: check bibtex
            bibtex = self._extract_field(content, "_bibtex", "")
            if bibtex and bibtex.startswith("@inproceedings"):
                if hasattr(submission, "id") and submission.id in bibtex:
                    return "accepted"

        except Exception as e:
            self.logger.debug(
                f"Failed to extract decision for {getattr(submission, 'id', 'unknown')}: {e}"
            )

        return None

    def _refine_decision(self, text: str) -> Optional[str]:
        """
        Refine decision text using paperoni's pattern matching.

        Maps various text patterns to standardized decisions.
        Importantly, treats "submitted" as "rejected".
        """
        if not text:
            return None

        text = text.lower()

        # Pattern mapping from paperoni
        patterns = {
            "notable": "notable",
            "poster": "poster",
            "oral": "oral",
            "spotlight": "spotlight",
            "withdraw": "withdrawn",
            "withdrawn": "withdrawn",
            "accepted": "accepted",
            "accept": "accepted",
            "reject": "rejected",
            "rejected": "rejected",
            "submitted": "rejected",  # Important: treat submitted as rejected
        }

        # Check each pattern
        for key, decision in patterns.items():
            if key in text:
                return decision

        return None

    def _classify_decision(self, decision: str) -> Optional[str]:
        """
        Classify decision string into oral/poster/spotlight/notable categories.

        Maps paperoni's refined decisions to our acceptance types.
        """
        if not decision:
            return None

        decision_lower = decision.lower()

        # Check for rejection/withdrawal first (should have been filtered earlier)
        if decision_lower in ["rejected", "withdrawn"]:
            return None

        # Direct mappings from paperoni decisions
        if decision_lower == "notable":
            return "notable"
        elif decision_lower == "oral":
            return "oral"
        elif decision_lower == "spotlight":
            return "spotlight"
        elif decision_lower == "poster":
            return "poster"
        elif decision_lower in ["accepted", "published"]:
            # Default accepted/published papers to poster
            return "poster"

        # Handle complex decision strings (e.g., "Accept: oral")
        if "notable" in decision_lower:
            # Handle cases like "notable-top-5%" or "Accept: notable-top-25%"
            return "notable"
        elif "oral" in decision_lower:
            return "oral"
        elif "spotlight" in decision_lower:
            return "spotlight"
        elif "poster" in decision_lower:
            return "poster"
        elif "accept" in decision_lower:
            # Default accepted papers to poster
            return "poster"

        # For venues that don't specify acceptance type (like TMLR)
        return None
