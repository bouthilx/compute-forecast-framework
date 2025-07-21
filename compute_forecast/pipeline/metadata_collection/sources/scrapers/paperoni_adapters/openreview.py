"""OpenReview adapter using openreview-py package."""

from typing import List, Any, Optional
from datetime import datetime
import openreview
import re

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class OpenReviewAdapter(BasePaperoniAdapter):
    """Adapter for OpenReview using the official Python client."""

    def __init__(self, config=None):
        super().__init__("openreview", config)
        self.client = None
        self.client_v1 = None  # For legacy API access

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
        """Create OpenReview client."""
        try:
            # Create API v2 client (for 2024+)
            self.client = openreview.api.OpenReviewClient(
                baseurl="https://api2.openreview.net"
            )

            # Create API v1 client (for 2023 and earlier)
            self.client_v1 = openreview.Client(baseurl="https://api.openreview.net")

            return self.client
        except Exception as e:
            self.logger.error(f"Failed to create OpenReview client: {e}")
            raise

    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Use OpenReview API to get papers."""
        papers = []

        venue_lower = venue.lower()

        # Map venue to OpenReview conference ID format
        venue_id = self._get_venue_id(venue_lower, year)
        if not venue_id:
            self.logger.error(f"Unsupported venue for OpenReview: {venue}")
            return []

        try:
            # Special handling for TMLR (continuous publication)
            if venue_lower == "tmlr":
                papers = self._get_tmlr_papers(year)
                return papers

            # For conference venues (ICLR, COLM, RLC)
            # Use API v1 for ICLR 2023 and earlier
            if venue_lower == "iclr" and year <= 2023:
                submissions = self._get_conference_submissions_v1(venue_id, venue_lower, year)
            elif venue_lower == "iclr" and year >= 2024:
                # For ICLR 2024+, use venueid to get only accepted papers
                submissions = self._get_accepted_papers_by_venueid(venue_id)
            else:
                submissions = self._get_conference_submissions(venue_id, venue_lower)

            # Filter accepted papers and convert to SimplePaper
            for submission in submissions:
                try:
                    # Extract decision information using paperoni's approach
                    decision = self._extract_decision(submission, venue_lower, year)
                    
                    # Skip rejected or withdrawn papers
                    if decision and decision.lower() in ["rejected", "withdrawn"]:
                        self.logger.debug(f"Skipping {decision} paper: {submission.id}")
                        continue
                    
                    # Determine acceptance type
                    if decision:
                        # We have a decision, classify it
                        acceptance_type = self._classify_decision(decision)
                    elif venue_lower == "iclr" and year >= 2024:
                        # For ICLR 2024+, check venue field in content for acceptance type
                        venue_info = content.get('venue', {})
                        if isinstance(venue_info, dict):
                            venue_info = venue_info.get('value', '')
                        
                        if 'oral' in str(venue_info).lower():
                            acceptance_type = 'oral'
                        elif 'spotlight' in str(venue_info).lower():
                            acceptance_type = 'spotlight'
                        else:
                            # Default to poster for accepted papers
                            acceptance_type = 'poster'
                    elif venue_lower == "iclr":
                        # For ICLR 2023 and before without decision info, default to poster
                        self.logger.debug(f"No decision found for {submission.id}, defaulting to poster")
                        acceptance_type = "poster"
                    else:
                        # Other venues without decision
                        acceptance_type = None
                    
                    content = submission.content

                    # Determine if we're using API v1 or v2 based on content structure
                    is_api_v1 = isinstance(content.get("title", ""), str)

                    # Extract basic information
                    if is_api_v1:
                        # API v1: Direct values
                        title = content.get("title", "")
                        authors = content.get("authors", [])
                        abstract = content.get("abstract", "")
                    else:
                        # API v2: Values wrapped in dicts
                        title = self._extract_value(content.get("title", ""))
                        authors = self._extract_value(content.get("authors", []))
                        abstract = self._extract_value(content.get("abstract", ""))

                    # PDF URL
                    pdf_urls = self._extract_pdf_urls(content)

                    # Paper URL
                    paper_url = f"https://openreview.net/forum?id={submission.id}"

                    # Create SimplePaper
                    paper = SimplePaper(
                        title=title,
                        authors=authors if isinstance(authors, list) else [authors],
                        venue=venue.upper(),
                        year=year,
                        abstract=abstract,
                        pdf_urls=pdf_urls,
                        paper_id=submission.id,
                        source_scraper=self.source_name,
                        source_url=paper_url,
                        extraction_confidence=0.95,
                        decision=acceptance_type
                    )

                    papers.append(paper)

                except Exception as e:
                    self.logger.warning(f"Failed to parse OpenReview submission: {e}")
                    continue

        except Exception as e:
            self.logger.error(
                f"Error fetching OpenReview papers for {venue} {year}: {e}"
            )
            raise
        
        self.logger.info(f"After filtering: {len(papers)} accepted papers from {len(submissions)} total submissions")
        return papers

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

    def _get_conference_submissions(self, venue_id: str, venue_lower: str) -> List[Any]:
        """Get submissions for conference venues with various invitation formats."""
        submissions = []

        # Try different invitation formats based on venue
        invitation_formats = [
            f"{venue_id}/-/Blind_Submission",
            f"{venue_id}/-/Submission",
            f"{venue_id}/-/Paper",
        ]

        # Add venue-specific formats
        if venue_lower == "colm":
            invitation_formats.insert(0, f"{venue_id}#-/Submission")
        elif venue_lower == "rlc":
            invitation_formats.insert(0, f"{venue_id}#-/Submission")

        for invitation in invitation_formats:
            try:
                self.logger.debug(f"Trying invitation format: {invitation}")
                submissions = list(self.client.get_all_notes(
                    invitation=invitation,
                    details='replies'  # Changed from 'directReplies' to 'replies'
                ))
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

        return submissions
    
    def _get_conference_submissions_v1(self, venue_id: str, venue_lower: str, year: int) -> List[Any]:
        """Get submissions for conference venues using API v1 (for ICLR ≤2023)."""
        submissions = []

        # Ensure we have a v1 client
        if not self.client_v1:
            self.client_v1 = openreview.Client(
                baseurl='https://api.openreview.net'
            )
        
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
                # Use iterget_notes to handle pagination automatically
                from openreview import tools
                submissions_iter = tools.iterget_notes(
                    self.client_v1,
                    invitation=invitation
                )
                
                # Convert iterator to list
                all_submissions = list(submissions_iter)
                
                if all_submissions:
                    self.logger.info(f"Found {len(all_submissions)} total submissions using v1 API with {invitation}")
                    break
            except Exception as e:
                self.logger.debug(f"Failed with v1 invitation {invitation}: {e}")
                continue
        
        if not all_submissions:
            self.logger.error(f"No submissions found for {venue_id} using API v1")
            return []
        
        # For ICLR, we need to fetch decisions properly since venue field is unreliable
        if venue_lower == "iclr" and all_submissions:
            self.logger.info(f"Filtering {len(all_submissions)} submissions...")
            
            # First try venue field approach for years where it works
            venue_filtered = []
            has_venue_info = False
            
            # Check if venue field is reliable for this year
            sample_venues = [sub.content.get('venue', '') for sub in all_submissions[:20]]
            venues_with_data = sum(1 for v in sample_venues if v)
            
            if venues_with_data > 10:  # More than 50% have venue data
                # Try venue-based filtering
                for submission in all_submissions:
                    venue = submission.content.get('venue', '')
                    
                    # Different patterns for different years
                    if year == 2022 and venue == f'ICLR {year} Submitted':
                        continue  # Skip submitted papers
                    elif year >= 2023 and 'Submitted to' in venue:
                        continue  # Skip submitted papers
                    elif f'ICLR {year}' in venue and any(t in venue.lower() for t in ['poster', 'oral', 'spotlight', 'notable']):
                        # Extract decision from venue
                        if 'poster' in venue.lower():
                            submission._cached_decision = 'Accept: poster'
                        elif 'spotlight' in venue.lower():
                            submission._cached_decision = 'Accept: spotlight'
                        elif 'oral' in venue.lower():
                            submission._cached_decision = 'Accept: oral'
                        elif 'notable' in venue.lower() and '5%' in venue:
                            submission._cached_decision = 'Accept: notable-top-5%'
                        elif 'notable' in venue.lower() and '25%' in venue:
                            submission._cached_decision = 'Accept: notable-top-25%'
                        else:
                            submission._cached_decision = 'Accept'
                        venue_filtered.append(submission)
                        has_venue_info = True
            
            if has_venue_info and len(venue_filtered) > 100:  # Sanity check
                self.logger.info(f"Used venue field to find {len(venue_filtered)} accepted papers")
                submissions = venue_filtered
            else:
                # Fallback: Fetch decisions individually (but with better batching)
                self.logger.info("Venue field unreliable, fetching decisions...")
                accepted_submissions = []
                
                # Process in batches to show progress
                batch_size = 100
                for i in range(0, len(all_submissions), batch_size):
                    batch = all_submissions[i:i+batch_size]
                    
                    for submission in batch:
                        if hasattr(submission, 'number'):
                            try:
                                decisions = self.client_v1.get_notes(
                                    invitation=f'{venue_id}/Paper{submission.number}/-/Decision',
                                    limit=1
                                )
                                
                                if decisions and 'decision' in decisions[0].content:
                                    decision = decisions[0].content['decision']
                                    if 'Accept' in decision:
                                        submission._cached_decision = decision
                                        accepted_submissions.append(submission)
                            except:
                                # Skip on error
                                pass
                    
                    # Log progress
                    processed = min(i + batch_size, len(all_submissions))
                    self.logger.debug(f"Processed {processed}/{len(all_submissions)} papers, found {len(accepted_submissions)} accepted")
                
                submissions = accepted_submissions
                self.logger.info(f"Found {len(submissions)} accepted papers out of {len(all_submissions)} total")
        else:
            # For other venues, include all submissions
            self.logger.warning(f"Cannot filter decisions for {venue_lower}, including all submissions")
            submissions = all_submissions
        
        return submissions
    
    def _get_accepted_papers_by_venueid(self, venue_id: str) -> List[Any]:
        """Get accepted papers using venueid (for ICLR 2024+)."""
        try:
            self.logger.info(f"Getting accepted papers for {venue_id} using venueid")
            
            # Ensure we have a client
            if not self.client:
                self.client = self._create_paperoni_scraper()
            
            # Use venueid to get only accepted papers
            submissions = list(self.client.get_all_notes(
                content={'venueid': venue_id}
            ))
            
            self.logger.info(f"Found {len(submissions)} accepted papers using venueid")
            return submissions
            
        except Exception as e:
            self.logger.error(f"Error getting accepted papers by venueid for {venue_id}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _get_tmlr_papers(self, year: int) -> List[SimplePaper]:
        """Get TMLR papers published in a specific year."""
        papers = []

        try:
            # Ensure we have a client
            if not self.client:
                self.client = self._create_paperoni_scraper()

            # TMLR uses a different structure - get accepted papers
            submissions = list(self.client.get_all_notes(
                invitation='TMLR/-/Accepted',
                details='replies'
            ))
            
            self.logger.info(f"Found {len(submissions)} total TMLR papers")

            # Filter by publication year
            for submission in submissions:
                try:
                    # Get publication date from pdate (publication date in milliseconds)
                    # Fall back to cdate if pdate not available
                    pub_date = None
                    if hasattr(submission, "pdate") and submission.pdate:
                        pub_date = datetime.fromtimestamp(submission.pdate / 1000)
                    elif hasattr(submission, "cdate") and submission.cdate:
                        # Fallback to creation date if no publication date
                        pub_date = datetime.fromtimestamp(submission.cdate / 1000)
                        self.logger.debug(
                            f"Using cdate for submission {getattr(submission, 'id', 'unknown')}"
                        )

                    if pub_date and pub_date.year != year:
                        continue
                    elif not pub_date:
                        # If no date available, skip the paper
                        self.logger.debug(
                            f"No date for submission {getattr(submission, 'id', 'unknown')}"
                        )
                        continue

                    # Extract paper information
                    content = submission.content

                    paper = SimplePaper(
                        title=self._extract_value(content.get("title", "")),
                        authors=self._extract_value(content.get("authors", [])),
                        venue="TMLR",
                        year=year,
                        abstract=self._extract_value(content.get("abstract", "")),
                        pdf_urls=self._extract_pdf_urls(content),
                        paper_id=submission.id,
                        source_scraper=self.source_name,
                        source_url=f"https://openreview.net/forum?id={submission.id}",
                        extraction_confidence=0.95,
                        decision=None  # TMLR doesn't have oral/poster/spotlight distinctions
                    )

                    papers.append(paper)

                    # Respect batch size
                    if len(papers) >= self.config.batch_size:
                        break

                except Exception as e:
                    self.logger.warning(f"Failed to parse TMLR submission: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error fetching TMLR papers: {e}")

        self.logger.info(f"Collected {len(papers)} TMLR papers for year {year}")
        return papers

    def _extract_pdf_urls(self, content: dict) -> List[str]:
        """Extract PDF URLs from content, handling different formats."""
        pdf_urls = []
        if "pdf" in content and content["pdf"]:
            pdf_url = content["pdf"]
            # Handle different pdf formats
            if isinstance(pdf_url, dict):
                # Check for 'value' key first (API v2 format)
                if "value" in pdf_url:
                    pdf_url = pdf_url["value"]
                else:
                    # Sometimes it's a dict with a 'url' field
                    pdf_url = pdf_url.get("url", "") or pdf_url.get("href", "")
            # For string URLs (API v1 or extracted values)
            if pdf_url and isinstance(pdf_url, str):
                if not pdf_url.startswith("http"):
                    # Use api.openreview.net for v1 URLs
                    if pdf_url.startswith("/pdf/"):
                        pdf_url = f"https://openreview.net{pdf_url}"
                    else:
                        pdf_url = f"https://openreview.net/{pdf_url}"
                pdf_urls.append(pdf_url)
        return pdf_urls

    def _extract_value(self, field):
        """Extract value from OpenReview field which can be a dict with 'value' key or direct value."""
        if isinstance(field, dict) and 'value' in field:
            return field['value']
        return field
    
    def _extract_decision(self, submission, venue_lower: str, year: int):
        """Extract decision from submission using paperoni's sophisticated approach."""
        try:
            # Check if we have a cached decision from API v1 batch processing
            if hasattr(submission, '_cached_decision'):
                return submission._cached_decision
            
            # Use paperoni's heuristics-based approach for decision extraction
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
            if hasattr(submission, 'details') and 'replies' in submission.details:
                replies = submission.details['replies']
                
                for reply in reversed(replies):  # Process in reverse order like paperoni
                    # Handle both API v1 (single invitation) and v2 (invitations list)
                    invitations = reply.get('invitations', [reply.get('invitation', '')])
                    if isinstance(invitations, str):
                        invitations = [invitations]
                    
                    for rank, pattern, field in heuristics:
                        if any(re.match(pattern, inv, re.IGNORECASE) for inv in invitations):
                            if field.startswith("="):
                                # Direct decision value
                                ranked_results.append((rank, field[1:]))
                                break
                            else:
                                # Extract from content field
                                content = reply.get('content', {})
                                if field in content:
                                    value = content[field]
                                    if isinstance(value, dict) and 'value' in value:
                                        value = value['value']
                                    if value:
                                        ranked_results.append((rank, str(value)))
                                        break
            
            # Process ranked results
            if ranked_results:
                ranked_results.sort()
                # Get all decisions with the same (best) rank
                best_rank = ranked_results[0][0]
                decisions = {decision for rank, decision in ranked_results if rank == best_rank}
                if len(decisions) == 1:
                    decision = decisions.pop()
                    return self._refine_decision(decision)
            
            # Fallback: check venue field in content
            content = submission.content if hasattr(submission, 'content') else {}
            venue_field = content.get('venue', '')
            if isinstance(venue_field, dict):
                venue_field = venue_field.get('value', '')
            if venue_field:
                refined = self._refine_decision(str(venue_field))
                if refined:
                    return refined
            
            # Fallback: check venueid
            venueid = content.get('venueid', '')
            if isinstance(venueid, dict):
                venueid = venueid.get('value', '')
            if venueid:
                refined = self._refine_decision(str(venueid))
                if refined:
                    return refined
            
            # Check if paper was published (has pdate)
            if hasattr(submission, 'pdate') and submission.pdate:
                return "published"
            
            # Last resort: check bibtex
            bibtex = content.get('_bibtex', '')
            if isinstance(bibtex, dict):
                bibtex = bibtex.get('value', '')
            if bibtex.startswith('@inproceedings') and hasattr(submission, 'id') and submission.id in bibtex:
                return "accepted"
                            
        except Exception as e:
            self.logger.debug(f"Failed to extract decision for {getattr(submission, 'id', 'unknown')}: {e}")
            
        return None
    
    def _refine_decision(self, text: str) -> Optional[str]:
        """Refine decision text using paperoni's pattern matching."""
        if not text:
            return None
            
        text = text.lower()
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
            "submitted": "rejected",  # Treat submitted as rejected
        }
        
        for key, decision in patterns.items():
            if key in text:
                return decision
        
        return None
    
    def _classify_decision(self, decision: str) -> Optional[str]:
        """Classify decision string into oral/poster/spotlight categories."""
        if not decision:
            return None
            
        decision_lower = decision.lower()
        
        # Check for rejection/withdrawal first (should have been filtered earlier)
        if decision_lower in ['rejected', 'withdrawn']:
            return None
        
        # Map decision types from paperoni
        if decision_lower == 'notable':
            return 'notable'
        elif decision_lower == 'oral':
            return 'oral'
        elif decision_lower == 'spotlight':
            return 'spotlight'
        elif decision_lower == 'poster':
            return 'poster'
        elif decision_lower in ['accepted', 'published']:
            # Default accepted/published papers to poster
            return 'poster'
        elif 'notable' in decision_lower:
            # Handle cases like "notable-top-5%" or "notable-top-25%"
            return 'notable'
        elif 'oral' in decision_lower:
            return 'oral'
        elif 'spotlight' in decision_lower:
            return 'spotlight'
        elif 'poster' in decision_lower:
            return 'poster'
        elif 'accept' in decision_lower:
            # Default accepted papers to poster
            return 'poster'
        
        # For TMLR and other venues that don't specify
        return None
