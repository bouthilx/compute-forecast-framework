"""PDF downloader with caching, retry logic, and batch processing."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any

import requests
from rich.progress import Progress

from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.pdf_download.cache_manager import PDFCacheManager

logger = logging.getLogger(__name__)


class SimplePDFDownloader:
    """Simple PDF downloader with caching and retry logic."""

    def __init__(self, cache_dir: str = "./pdf_cache"):
        """Initialize the downloader with cache directory.

        Args:
            cache_dir: Directory to store downloaded PDFs
        """
        self.cache_manager = PDFCacheManager(cache_dir)

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; Academic PDF Collector)"}
        )

        # Configuration
        self.max_retries = 3
        self.timeout = 30
        self.min_file_size = 10 * 1024  # 10KB minimum

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
        cached_file = self.cache_manager.get_cached_file(paper_id)
        if cached_file:
            logger.info(f"Using cached PDF for {paper_id}")
            return cached_file

        # Download with retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Downloading PDF for {paper_id} (attempt {attempt + 1}/{self.max_retries})"
                )

                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Validate content
                self._validate_pdf_content(response)

                # Save to cache
                cache_path = self.cache_manager.save_to_cache(
                    paper_id, response.content
                )
                logger.info(f"Successfully downloaded PDF for {paper_id}")
                return cache_path

            except (requests.RequestException, ValueError) as e:
                last_exception = e
                logger.warning(f"Download failed for {paper_id}: {str(e)}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = 2**attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        # All retries exhausted
        raise last_exception

    def download_batch(
        self,
        pdf_records: Dict[str, PDFRecord],
        max_workers: int = 5,
        show_progress: bool = True,
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
            return {"successful": {}, "failed": {}, "total": 0, "success_rate": 0.0}

        successful = {}
        failed = {}

        # Progress bar setup using rich
        if show_progress:
            with Progress() as progress:
                task_id = progress.add_task("Downloading PDFs", total=len(pdf_records))

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all download tasks
                    future_to_paper = {
                        executor.submit(self.download_pdf, record.pdf_url, paper_id): (
                            paper_id,
                            record,
                        )
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

                        progress.update(task_id, advance=1)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all download tasks
                future_to_paper = {
                    executor.submit(self.download_pdf, record.pdf_url, paper_id): (
                        paper_id,
                        record,
                    )
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

        total = len(pdf_records)
        success_count = len(successful)

        return {
            "successful": successful,
            "failed": failed,
            "total": total,
            "success_rate": success_count / total if total > 0 else 0.0,
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_cache_stats()

    def clear_cache(self) -> int:
        """Clear all cached PDFs.

        Returns:
            Number of files cleared
        """
        return self.cache_manager.clear_cache()
