"""OpenReview adapter using openreview-py package."""

from typing import List, Any
from datetime import datetime
import openreview

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class OpenReviewAdapter(BasePaperoniAdapter):
    """Adapter for OpenReview using the official Python client."""
    
    def __init__(self, config=None):
        super().__init__("openreview", config)
        self.client = None
        
    def get_supported_venues(self) -> List[str]:
        return ["iclr", "ICLR"]
        
    def _create_paperoni_scraper(self):
        """Create OpenReview client."""
        try:
            # Create guest client (no authentication needed for public data)
            self.client = openreview.api.OpenReviewClient(
                baseurl='https://api2.openreview.net'
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
        if venue_lower == "iclr":
            venue_id = f"ICLR.cc/{year}/Conference"
        else:
            self.logger.error(f"Unsupported venue for OpenReview: {venue}")
            return []
        
        try:
            # Get accepted papers
            # Note: The API has changed over the years, so we try different approaches
            submissions = []
            
            try:
                # Try the newer API format first
                submissions = list(self.client.get_all_notes(
                    invitation=f'{venue_id}/-/Blind_Submission',
                    details='original'
                ))
            except Exception:
                # Try alternative invitation formats
                try:
                    submissions = list(self.client.get_all_notes(
                        invitation=f'{venue_id}/-/Submission'
                    ))
                except Exception:
                    # For older conferences
                    try:
                        submissions = list(self.client.get_all_notes(
                            invitation=f'{venue_id}/-/Paper'
                        ))
                    except Exception as e:
                        self.logger.error(f"Failed to get submissions for {venue_id}: {e}")
                        return []
            
            # Filter accepted papers and convert to SimplePaper
            for submission in submissions[:self.config.batch_size]:
                try:
                    # Check if paper is accepted (if decision is available)
                    # This varies by conference, so we'll include all for now
                    content = submission.content
                    
                    # Extract basic information
                    title = content.get('title', '')
                    authors = content.get('authors', [])
                    abstract = content.get('abstract', '')
                    
                    # PDF URL
                    pdf_urls = []
                    if 'pdf' in content:
                        pdf_url = content['pdf']
                        if not pdf_url.startswith('http'):
                            pdf_url = f"https://openreview.net{pdf_url}"
                        pdf_urls.append(pdf_url)
                    
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
                        scraped_at=datetime.now(),
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