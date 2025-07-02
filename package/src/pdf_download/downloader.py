"""PDF downloader with caching, retry logic, and batch processing."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional, Any

import requests
from tqdm import tqdm

from src.pdf_discovery.core.models import PDFRecord

logger = logging.getLogger(__name__)


class SimplePDFDownloader:
    """Simple PDF downloader with caching and retry logic."""
    
    def __init__(self, cache_dir: str = "./pdf_cache"):
        """Initialize the downloader with cache directory.
        
        Args:
            cache_dir: Directory to store downloaded PDFs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Academic PDF Collector)"
        })
        
        # Configuration
        self.max_retries = 3
        self.timeout = 30
        self.min_file_size = 10 * 1024  # 10KB minimum
    
    def _get_cache_path(self, paper_id: str) -> Path:
        """Get the cache file path for a paper ID.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            Path to the cached file
        """
        return self.cache_dir / f"{paper_id}.pdf"
    
    def _is_cached(self, paper_id: str) -> bool:
        """Check if a paper is already cached.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            True if the paper is cached
        """
        return self._get_cache_path(paper_id).exists()
    
    def _validate_pdf_content(self, response: requests.Response) -> None:
        """Validate that the response contains a valid PDF.
        
        Args:
            response: HTTP response object
            
        Raises:
            ValueError: If content is not a valid PDF
        """
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type:
            raise ValueError(f"Invalid content type: {content_type}")
        
        if len(response.content) < self.min_file_size:
            raise ValueError(f"PDF file too small: {len(response.content)} bytes")
    
    def download_pdf(self, url: str, paper_id: str) -> Path:
        """Download a PDF with retry logic and caching.
        
        Args:
            url: URL of the PDF to download
            paper_id: Unique identifier for the paper
            
        Returns:
            Path to the downloaded/cached PDF file
            
        Raises:
            requests.RequestException: If download fails after retries
            ValueError: If content validation fails
        """
        # Check cache first
        cache_path = self._get_cache_path(paper_id)
        if self._is_cached(paper_id):
            logger.info(f"Using cached PDF for {paper_id}")
            return cache_path
        
        # Download with retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading PDF for {paper_id} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # Validate content
                self._validate_pdf_content(response)
                
                # Save to cache
                cache_path.write_bytes(response.content)
                logger.info(f"Successfully downloaded PDF for {paper_id}")
                return cache_path
                
            except (requests.RequestException, ValueError) as e:
                last_exception = e
                logger.warning(f"Download failed for {paper_id}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = 2 ** attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries exhausted
        raise last_exception
    
    def download_batch(
        self, 
        pdf_records: Dict[str, PDFRecord], 
        max_workers: int = 5,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """Download multiple PDFs in parallel.
        
        Args:
            pdf_records: Dictionary mapping paper_id to PDFRecord
            max_workers: Maximum number of parallel downloads
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary with download results:
                - successful: Dict of paper_id -> Path
                - failed: Dict of paper_id -> error message
                - total: Total number of PDFs
                - success_rate: Percentage of successful downloads
        """
        if not pdf_records:
            return {
                "successful": {},
                "failed": {},
                "total": 0,
                "success_rate": 0.0
            }
        
        successful = {}
        failed = {}
        
        # Progress bar setup
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(total=len(pdf_records), desc="Downloading PDFs", unit="pdf")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all download tasks
                future_to_paper = {
                    executor.submit(
                        self.download_pdf, 
                        record.pdf_url, 
                        paper_id
                    ): (paper_id, record)
                    for paper_id, record in pdf_records.items()
                }
                
                # Process completed downloads
                for future in as_completed(future_to_paper):
                    paper_id, record = future_to_paper[future]
                    
                    try:
                        path = future.result()
                        successful[paper_id] = path
                        logger.info(f"Successfully processed {paper_id}")
                    except Exception as e:
                        failed[paper_id] = str(e)
                        logger.error(f"Failed to download {paper_id}: {str(e)}")
                    
                    if progress_bar:
                        progress_bar.update(1)
        
        finally:
            if progress_bar:
                progress_bar.close()
        
        total = len(pdf_records)
        success_count = len(successful)
        
        return {
            "successful": successful,
            "failed": failed,
            "total": total,
            "success_rate": success_count / total if total > 0 else 0.0
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        pdf_files = list(self.cache_dir.glob("*.pdf"))
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            "cache_dir": str(self.cache_dir),
            "total_files": len(pdf_files),
            "total_size_bytes": total_size
        }
    
    def clear_cache(self) -> int:
        """Clear all cached PDFs.
        
        Returns:
            Number of files cleared
        """
        pdf_files = list(self.cache_dir.glob("*.pdf"))
        
        for pdf_file in pdf_files:
            pdf_file.unlink()
        
        logger.info(f"Cleared {len(pdf_files)} files from cache")
        return len(pdf_files)