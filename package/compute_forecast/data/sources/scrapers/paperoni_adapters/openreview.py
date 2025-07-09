"""OpenReview adapter using openreview-py package."""

from typing import List, Any, Optional
from datetime import datetime
import openreview

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
        return [
            "iclr", "ICLR",
            "tmlr", "TMLR", 
            "colm", "COLM",
            "rlc", "RLC"
        ]
    
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
                baseurl='https://api2.openreview.net'
            )
            
            # Create API v1 client (for 2023 and earlier)
            self.client_v1 = openreview.Client(
                baseurl='https://api.openreview.net'
            )
            
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
                submissions = self._get_conference_submissions_v1(venue_id, venue_lower)
            else:
                submissions = self._get_conference_submissions(venue_id, venue_lower)
            
            # Filter accepted papers and convert to SimplePaper
            for submission in submissions[:self.config.batch_size]:
                try:
                    # Check if paper is accepted (if decision is available)
                    # This varies by conference, so we'll include all for now
                    content = submission.content
                    
                    # Determine if we're using API v1 or v2 based on content structure
                    is_api_v1 = isinstance(content.get('title', ''), str)
                    
                    # Extract basic information
                    if is_api_v1:
                        # API v1: Direct values
                        title = content.get('title', '')
                        authors = content.get('authors', [])
                        abstract = content.get('abstract', '')
                    else:
                        # API v2: Values wrapped in dicts
                        title = self._extract_value(content.get('title', ''))
                        authors = self._extract_value(content.get('authors', []))
                        abstract = self._extract_value(content.get('abstract', ''))
                    
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
                        extraction_confidence=0.95
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse OpenReview submission: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error fetching OpenReview papers for {venue} {year}: {e}")
            raise
            
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
            f'{venue_id}/-/Blind_Submission',
            f'{venue_id}/-/Submission',
            f'{venue_id}/-/Paper'
        ]
        
        # Add venue-specific formats
        if venue_lower == "colm":
            invitation_formats.insert(0, f'{venue_id}#-/Submission')
        elif venue_lower == "rlc":
            invitation_formats.insert(0, f'{venue_id}#-/Submission')
        
        for invitation in invitation_formats:
            try:
                self.logger.debug(f"Trying invitation format: {invitation}")
                submissions = list(self.client.get_all_notes(
                    invitation=invitation,
                    details='directReplies'
                ))
                if submissions:
                    self.logger.info(f"Found {len(submissions)} submissions using {invitation}")
                    break
            except Exception as e:
                self.logger.debug(f"Failed with invitation {invitation}: {e}")
                continue
        
        if not submissions:
            self.logger.error(f"No submissions found for {venue_id}")
        
        return submissions
    
    def _get_conference_submissions_v1(self, venue_id: str, venue_lower: str) -> List[Any]:
        """Get submissions for conference venues using API v1 (for ICLR ≤2023)."""
        submissions = []
        
        # Ensure we have a v1 client
        if not self.client_v1:
            self.client_v1 = openreview.Client(
                baseurl='https://api.openreview.net'
            )
        
        # Try different invitation formats
        invitation_formats = [
            f'{venue_id}/-/Blind_Submission',
            f'{venue_id}/-/Submission',
            f'{venue_id}/-/Paper'
        ]
        
        for invitation in invitation_formats:
            try:
                self.logger.debug(f"Trying v1 invitation format: {invitation}")
                # API v1 uses get_notes instead of get_all_notes
                submissions = self.client_v1.get_notes(
                    invitation=invitation,
                    details='replyCount'
                )
                if submissions:
                    self.logger.info(f"Found {len(submissions)} submissions using v1 API with {invitation}")
                    break
            except Exception as e:
                self.logger.debug(f"Failed with v1 invitation {invitation}: {e}")
                continue
        
        if not submissions:
            self.logger.error(f"No submissions found for {venue_id} using API v1")
        
        return submissions
    
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
                details='directReplies'
            ))
            
            self.logger.info(f"Found {len(submissions)} total TMLR papers")
            
            # Filter by publication year
            for submission in submissions:
                try:
                    # Get publication date from pdate (publication date in milliseconds)
                    # Fall back to cdate if pdate not available
                    pub_date = None
                    if hasattr(submission, 'pdate') and submission.pdate:
                        pub_date = datetime.fromtimestamp(submission.pdate / 1000)
                    elif hasattr(submission, 'cdate') and submission.cdate:
                        # Fallback to creation date if no publication date
                        pub_date = datetime.fromtimestamp(submission.cdate / 1000)
                        self.logger.debug(f"Using cdate for submission {getattr(submission, 'id', 'unknown')}")
                    
                    if pub_date and pub_date.year != year:
                        continue
                    elif not pub_date:
                        # If no date available, skip the paper
                        self.logger.debug(f"No date for submission {getattr(submission, 'id', 'unknown')}")
                        continue
                    
                    # Extract paper information
                    content = submission.content
                    
                    paper = SimplePaper(
                        title=self._extract_value(content.get('title', '')),
                        authors=self._extract_value(content.get('authors', [])),
                        venue="TMLR",
                        year=year,
                        abstract=self._extract_value(content.get('abstract', '')),
                        pdf_urls=self._extract_pdf_urls(content),
                        paper_id=submission.id,
                        source_scraper=self.source_name,
                        source_url=f"https://openreview.net/forum?id={submission.id}",
                        extraction_confidence=0.95
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
        if 'pdf' in content and content['pdf']:
            pdf_url = content['pdf']
            # Handle different pdf formats
            if isinstance(pdf_url, dict):
                # Check for 'value' key first (API v2 format)
                if 'value' in pdf_url:
                    pdf_url = pdf_url['value']
                else:
                    # Sometimes it's a dict with a 'url' field
                    pdf_url = pdf_url.get('url', '') or pdf_url.get('href', '')
            # For string URLs (API v1 or extracted values)
            if pdf_url and isinstance(pdf_url, str):
                if not pdf_url.startswith('http'):
                    # Use api.openreview.net for v1 URLs
                    if pdf_url.startswith('/pdf/'):
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