"""
DOI Resolver Collector - Orchestrates CrossRef and Unpaywall for DOI-based PDF discovery
"""

from typing import List, Dict, Any
import logging
from datetime import datetime

from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper
from src.data.sources.enhanced_crossref import EnhancedCrossrefClient
from .unpaywall_client import UnpaywallClient

logger = logging.getLogger(__name__)


class DOIResolverCollector(BasePDFCollector):
    """PDF collector that uses DOI resolution via CrossRef and Unpaywall."""
    
    def __init__(self, email: str):
        """Initialize DOI resolver collector.
        
        Args:
            email: Contact email for API access
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError("Email is required for DOI resolver API access")
        
        super().__init__(source_name="doi_resolver")
        
        self.email = email
        self.crossref_client = EnhancedCrossrefClient(email=email)
        self.unpaywall_client = UnpaywallClient(email=email)
        
        # Set timeout for this collector (combined from both sources)
        self.timeout = 120  # 2 minutes for both API calls
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using DOI resolution.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            Exception: If paper has no DOI or no PDFs are found
        """
        if not paper.doi:
            raise Exception(f"Paper does not have a DOI: {paper.paper_id}")
        
        logger.info(f"Resolving DOI for paper {paper.paper_id}: {paper.doi}")
        
        # Try both CrossRef and Unpaywall in parallel-ish (sequential for simplicity)
        crossref_urls = []
        unpaywall_urls = []
        
        # Try CrossRef first
        try:
            crossref_response = self.crossref_client.lookup_doi(paper.doi)
            if crossref_response.success and crossref_response.papers:
                crossref_paper = crossref_response.papers[0]
                crossref_urls = crossref_paper.urls or []
                logger.info(f"CrossRef found {len(crossref_urls)} URLs for {paper.doi}")
        except Exception as e:
            logger.warning(f"CrossRef lookup failed for {paper.doi}: {e}")
        
        # Try Unpaywall
        try:
            unpaywall_response = self.unpaywall_client.find_open_access(paper.doi)
            if unpaywall_response.success and unpaywall_response.papers:
                unpaywall_paper = unpaywall_response.papers[0]
                unpaywall_urls = unpaywall_paper.urls or []
                logger.info(f"Unpaywall found {len(unpaywall_urls)} URLs for {paper.doi}")
        except Exception as e:
            logger.warning(f"Unpaywall lookup failed for {paper.doi}: {e}")
        
        # Merge and prioritize URLs
        all_urls = self._merge_pdf_urls(crossref_urls, unpaywall_urls)
        
        if not all_urls:
            raise Exception(f"No PDFs found for DOI {paper.doi}")
        
        # Calculate confidence score based on number of sources and URLs
        confidence_score = self._calculate_confidence_score(crossref_urls, unpaywall_urls)
        
        # Create PDFRecord
        pdf_record = PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=all_urls[0],  # Primary URL
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=confidence_score,
            version_info={
                "crossref_urls": crossref_urls,
                "unpaywall_urls": unpaywall_urls,
                "all_urls": all_urls,
                "doi": paper.doi,
                "sources_used": self._get_sources_used(crossref_urls, unpaywall_urls)
            },
            validation_status=self._get_validation_status(confidence_score),
            license=self._determine_license(crossref_urls, unpaywall_urls)
        )
        
        logger.info(f"Successfully resolved DOI {paper.doi} to {len(all_urls)} URLs "
                   f"with confidence {confidence_score:.2f}")
        
        return pdf_record
    
    def _merge_pdf_urls(self, crossref_urls: List[str], unpaywall_urls: List[str]) -> List[str]:
        """Merge and deduplicate PDF URLs, prioritizing CrossRef (publisher) over Unpaywall.
        
        Args:
            crossref_urls: URLs from CrossRef
            unpaywall_urls: URLs from Unpaywall
            
        Returns:
            Merged list of unique URLs with CrossRef URLs first
        """
        # Start with CrossRef URLs (typically publisher versions)
        merged_urls = list(crossref_urls)
        
        # Add Unpaywall URLs that aren't already in the list
        for url in unpaywall_urls:
            if url not in merged_urls:
                merged_urls.append(url)
        
        return merged_urls
    
    def _calculate_confidence_score(self, crossref_urls: List[str], unpaywall_urls: List[str]) -> float:
        """Calculate confidence score based on URL sources and counts.
        
        Args:
            crossref_urls: URLs from CrossRef
            unpaywall_urls: URLs from Unpaywall
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not crossref_urls and not unpaywall_urls:
            return 0.0
        
        score = 0.0
        
        # Base score for having any URLs
        score += 0.4
        
        # Bonus for CrossRef URLs (publisher sources)
        if crossref_urls:
            score += 0.3
            # Additional bonus for multiple CrossRef URLs
            if len(crossref_urls) > 1:
                score += 0.1
        
        # Bonus for Unpaywall URLs (open access)
        if unpaywall_urls:
            score += 0.2
            # Additional bonus for multiple Unpaywall URLs
            if len(unpaywall_urls) > 1:
                score += 0.1
        
        # Bonus for having both sources
        if crossref_urls and unpaywall_urls:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_validation_status(self, confidence_score: float) -> str:
        """Determine validation status based on confidence score.
        
        Args:
            confidence_score: Confidence score between 0.0 and 1.0
            
        Returns:
            Validation status string
        """
        if confidence_score >= 0.8:
            return "high_confidence"
        elif confidence_score >= 0.6:
            return "medium_confidence"
        elif confidence_score >= 0.4:
            return "low_confidence"
        else:
            return "needs_validation"
    
    def _get_sources_used(self, crossref_urls: List[str], unpaywall_urls: List[str]) -> List[str]:
        """Get list of sources that provided URLs.
        
        Args:
            crossref_urls: URLs from CrossRef
            unpaywall_urls: URLs from Unpaywall
            
        Returns:
            List of source names
        """
        sources = []
        if crossref_urls:
            sources.append("crossref")
        if unpaywall_urls:
            sources.append("unpaywall")
        return sources
    
    def _determine_license(self, crossref_urls: List[str], unpaywall_urls: List[str]) -> str:
        """Determine license information based on sources.
        
        Args:
            crossref_urls: URLs from CrossRef
            unpaywall_urls: URLs from Unpaywall
            
        Returns:
            License string or None
        """
        if unpaywall_urls:
            # Unpaywall typically provides open access content
            return "open_access"
        elif crossref_urls:
            # CrossRef may provide publisher content
            return "publisher"
        else:
            return None