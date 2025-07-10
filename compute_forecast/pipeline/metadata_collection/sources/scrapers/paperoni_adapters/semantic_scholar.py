"""Semantic Scholar adapter using the semanticscholar package."""

from typing import List, Any
import os
from datetime import datetime
from semanticscholar import SemanticScholar as S2API

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class SemanticScholarAdapter(BasePaperoniAdapter):
    """Adapter for Semantic Scholar API using the official Python client."""
    
    def __init__(self, config=None):
        super().__init__("semantic_scholar", config)
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        
    def get_supported_venues(self) -> List[str]:
        # Semantic Scholar can search any venue
        return ["*"]  
        
    def _create_paperoni_scraper(self):
        """Create Semantic Scholar API client."""
        try:
            if self.api_key:
                return S2API(api_key=self.api_key)
            else:
                return S2API()
        except Exception as e:
            self.logger.error(f"Failed to create Semantic Scholar client: {e}")
            raise
            
    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Use Semantic Scholar API to search for papers."""
        papers = []
        
        try:
            # Build search query
            query = self._build_search_query(venue, year)
            
            # Search for papers
            # The semanticscholar package returns a generator, so we convert to list
            search_results = list(scraper.search_paper(
                query=query,
                year=f"{year}-{year}",  # Year range format
                limit=self.config.batch_size or 500,
                fields=['title', 'authors', 'venue', 'year', 'abstract', 'url', 
                       'openAccessPdf', 'externalIds', 'paperId']
            ))
            
            # Convert to SimplePaper format
            for result in search_results:
                try:
                    # Extract authors
                    authors = []
                    if hasattr(result, 'authors') and result.authors:
                        authors = [author['name'] for author in result.authors if 'name' in author]
                    
                    # Extract PDF URLs
                    pdf_urls = []
                    if hasattr(result, 'openAccessPdf') and result.openAccessPdf:
                        pdf_urls.append(result.openAccessPdf['url'])
                    
                    # Extract identifiers
                    doi = None
                    arxiv_id = None
                    if hasattr(result, 'externalIds') and result.externalIds:
                        doi = result.externalIds.get('DOI')
                        arxiv_id = result.externalIds.get('ArXiv')
                    
                    # Create SimplePaper
                    paper = SimplePaper(
                        title=result.title or "",
                        authors=authors,
                        venue=venue,  # Use the queried venue
                        year=year,
                        abstract=result.abstract,
                        pdf_urls=pdf_urls,
                        doi=doi,
                        arxiv_id=arxiv_id,
                        paper_id=result.paperId,
                        source_scraper=self.source_name,
                        source_url=result.url or f"https://www.semanticscholar.org/paper/{result.paperId}",
                        scraped_at=datetime.now(),
                        extraction_confidence=0.95
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert search result: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error searching Semantic Scholar for {venue} {year}: {e}")
            raise
            
        return papers
            
    def _build_search_query(self, venue: str, year: int) -> str:
        """Build search query for venue and year."""
        # Map common venue names to their full names for better search results
        venue_mapping = {
            "cvpr": "Computer Vision and Pattern Recognition",
            "iccv": "International Conference on Computer Vision", 
            "eccv": "European Conference on Computer Vision",
            "aaai": "AAAI Conference on Artificial Intelligence",
            "miccai": "Medical Image Computing and Computer Assisted Intervention",
            "kdd": "Knowledge Discovery and Data Mining",
            "www": "World Wide Web Conference",
            "nips": "Neural Information Processing Systems",
            "neurips": "Neural Information Processing Systems",
            "icml": "International Conference on Machine Learning",
            "iclr": "International Conference on Learning Representations",
            "acl": "Annual Meeting of the Association for Computational Linguistics",
            "emnlp": "Empirical Methods in Natural Language Processing",
            "naacl": "North American Chapter of the Association for Computational Linguistics",
        }
        
        venue_full = venue_mapping.get(venue.lower(), venue)
        
        # Simple query - just the venue name
        # The year filter is handled separately in the API call
        return venue_full