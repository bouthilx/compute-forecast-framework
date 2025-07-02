"""CORE API PDF collector for institutional repository access."""

import logging
import time
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import quote

from src.data.models import Paper
from src.pdf_discovery.core.models import PDFRecord
from src.pdf_discovery.core.collectors import BasePDFCollector

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for CORE API requests."""
    
    def __init__(self, requests_per_minute: int = 100):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute (CORE limit is 100)
        """
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class COREPDFCollector(BasePDFCollector):
    """CORE API collector for discovering PDFs from institutional repositories."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize CORE collector.
        
        Args:
            api_key: Optional CORE API key for higher rate limits
        """
        super().__init__("core")
        self.api_url = "https://api.core.ac.uk/v3/search/outputs"
        self.api_key = api_key
        self.rate_limiter = RateLimiter(100)  # 100 requests per minute
        
        # Set up headers
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "PDFDiscoveryFramework/1.0"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper using CORE API.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            Exception: If PDF cannot be discovered
        """
        # Build search query
        query = self._build_search_query(paper)
        
        # Apply rate limiting
        self.rate_limiter.wait()
        
        # Search CORE API
        params = {
            "q": query,
            "limit": 10,
            "fulltext": "false"
        }
        
        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"CORE API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            if data.get("totalHits", 0) == 0:
                raise Exception("No results found in CORE")
            
            # Find best matching result with PDF
            for result in data.get("results", []):
                pdf_url = self._extract_pdf_url(result)
                if pdf_url:
                    return PDFRecord(
                        paper_id=paper.paper_id,
                        pdf_url=pdf_url,
                        source=self.source_name,
                        discovery_timestamp=datetime.now(),
                        confidence_score=0.9,
                        version_info={
                            "core_id": result.get("id"),
                            "published_date": result.get("publishedDate"),
                            "repository": result.get("repositoryDocument", {}).get("repository", {}).get("name")
                        },
                        validation_status="verified",
                        file_size_bytes=result.get("repositoryDocument", {}).get("pdfSize"),
                        license=self._extract_license(result)
                    )
            
            raise Exception("No PDF found in CORE results")
            
        except requests.RequestException as e:
            raise Exception(f"CORE API request failed: {str(e)}")
    
    def _build_search_query(self, paper: Paper) -> str:
        """Build search query for CORE API.
        
        Args:
            paper: Paper to search for
            
        Returns:
            Search query string
        """
        # Prefer DOI search if available
        if paper.doi:
            return f'doi:"{paper.doi}"'
        
        # Otherwise use title search
        return f'title:"{paper.title}"'
    
    def _extract_pdf_url(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract PDF URL from CORE result.
        
        Args:
            result: CORE API result object
            
        Returns:
            PDF URL if found, None otherwise
        """
        # Check downloadUrl first
        download_url = result.get("downloadUrl")
        if download_url and download_url.endswith(".pdf"):
            return download_url
        
        # Check repository document
        repo_doc = result.get("repositoryDocument", {})
        if repo_doc:
            # Check if PDF is available
            if repo_doc.get("pdfStatus") == 1:
                pdf_url = repo_doc.get("pdfUrl")
                if pdf_url:
                    return pdf_url
        
        # Last resort: check if downloadUrl exists (might not end with .pdf)
        if download_url:
            return download_url
        
        return None
    
    def _extract_license(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract license information from CORE result.
        
        Args:
            result: CORE API result object
            
        Returns:
            License string if found
        """
        # Check for open access status
        if result.get("openAccess") is True:
            return "open_access"
        
        # Check rights field
        rights = result.get("rights")
        if rights:
            return rights
        
        return None