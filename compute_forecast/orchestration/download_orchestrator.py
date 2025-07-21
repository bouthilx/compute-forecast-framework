"""Orchestrator for coordinating parallel PDF downloads."""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time
from datetime import datetime
import threading

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.storage import StorageManager
from compute_forecast.workers import PDFDownloader
from compute_forecast.monitoring import DownloadProgressManager

logger = logging.getLogger(__name__)


@dataclass
class DownloadState:
    """State for download progress tracking."""

    completed: List[str]
    failed: Dict[str, str]  # paper_id -> error message
    in_progress: List[str]
    last_updated: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": self.in_progress,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadState":
        """Create from dictionary."""
        return cls(
            completed=data.get("completed", []),
            failed=data.get("failed", {}),
            in_progress=data.get("in_progress", []),
            last_updated=data.get("last_updated"),
        )


class DownloadOrchestrator:
    """Orchestrates parallel PDF downloads with progress tracking."""

    def __init__(
        self,
        parallel_workers: int = 5,
        rate_limit: Optional[float] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5,
        exponential_backoff: bool = False,
        cache_dir: Optional[str] = None,
        google_drive_credentials: Optional[str] = None,
        google_drive_folder_id: Optional[str] = None,
        progress_manager: Optional[DownloadProgressManager] = None,
        state_path: Optional[Path] = None,
    ):
        """Initialize download orchestrator.

        Args:
            parallel_workers: Number of parallel download workers
            rate_limit: Rate limit in requests per second
            timeout: Download timeout per file in seconds
            max_retries: Maximum retry attempts per paper
            retry_delay: Base delay between retries in seconds
            exponential_backoff: Use exponential backoff for retries
            cache_dir: Local cache directory
            google_drive_credentials: Path to Google credentials
            google_drive_folder_id: Google Drive folder ID
            progress_manager: Progress tracking manager
            state_path: Path to save state for resume capability
        """
        self.parallel_workers = parallel_workers
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.progress_manager = progress_manager
        self.state_path = state_path or Path(
            ".cf_state/download/download_progress.json"
        )

        # Initialize storage manager
        self.storage_manager = StorageManager(
            cache_dir=cache_dir,
            google_drive_credentials=google_drive_credentials,
            google_drive_folder_id=google_drive_folder_id,
        )

        # Rate limiting
        self._rate_limiter_lock = threading.Lock()
        self._last_request_time = 0.0
        self._min_request_interval = 1.0 / rate_limit if rate_limit else 0

        # State management
        self.state = DownloadState([], {}, [], None)
        self._state_lock = threading.Lock()

    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        if self._min_request_interval <= 0:
            return

        with self._rate_limiter_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _load_state(self) -> DownloadState:
        """Load state from file."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                return DownloadState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

        return DownloadState([], {}, [], None)

    def _save_state(self):
        """Save current state to file."""
        with self._state_lock:
            self.state.last_updated = datetime.now().isoformat()
            self.state_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(self.state_path, "w") as f:
                    json.dump(self.state.to_dict(), f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    def _update_state(self, paper_id: str, status: str, error: Optional[str] = None):
        """Update download state for a paper."""
        with self._state_lock:
            # Remove from in_progress
            if paper_id in self.state.in_progress:
                self.state.in_progress.remove(paper_id)

            # Add to appropriate list
            if status == "completed":
                if paper_id not in self.state.completed:
                    self.state.completed.append(paper_id)
                # Remove from failed if it was there
                if paper_id in self.state.failed:
                    del self.state.failed[paper_id]
            elif status == "failed":
                self.state.failed[paper_id] = error or "Unknown error"
            elif status == "in_progress":
                if paper_id not in self.state.in_progress:
                    self.state.in_progress.append(paper_id)

    def filter_papers_for_download(
        self, papers: List[Paper], retry_failed: bool = False, resume: bool = False
    ) -> List[Paper]:
        """Filter papers based on download state and flags.

        Args:
            papers: List of all papers with PDF URLs
            retry_failed: Whether to retry previously failed downloads
            resume: Whether to resume from previous state

        Returns:
            List of papers to download
        """
        if resume:
            self.state = self._load_state()

        papers_to_download = []

        for paper in papers:
            paper_id = paper.paper_id

            # Skip if already completed
            if paper_id in self.state.completed:
                # Check if actually exists in storage
                exists, location = self.storage_manager.exists(paper_id)
                if exists:
                    logger.debug(f"Skipping {paper_id} - already in {location}")
                    continue
                else:
                    # Was marked completed but not found, re-download
                    logger.warning(
                        f"{paper_id} marked completed but not found in storage"
                    )
                    self.state.completed.remove(paper_id)

            # Skip failed papers unless retry_failed is set
            if paper_id in self.state.failed and not retry_failed:
                logger.debug(f"Skipping {paper_id} - previously failed")
                continue

            papers_to_download.append(paper)

        return papers_to_download

    def download_papers(
        self,
        papers: List[Paper],
        save_papers_callback: Optional[Callable[[List[Paper]], None]] = None,
    ) -> Tuple[int, int]:
        """Download PDFs for all papers.

        Args:
            papers: List of papers to download
            save_papers_callback: Optional callback to save updated papers

        Returns:
            Tuple of (successful_downloads, failed_downloads)
        """
        if not papers:
            logger.info("No papers to download")
            return 0, 0

        # Initialize progress manager if provided
        if self.progress_manager:
            self.progress_manager.start(len(papers))

        # Create downloader
        downloader = PDFDownloader(
            storage_manager=self.storage_manager,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            exponential_backoff=self.exponential_backoff,
        )

        # Track results
        successful = 0
        failed = 0

        # Process papers in parallel
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
            # Submit download tasks
            future_to_paper = {}

            for paper in papers:
                # Apply rate limiting
                self._enforce_rate_limit()

                # Update state
                self._update_state(paper.paper_id, "in_progress")

                # Submit download task
                future = executor.submit(self._download_single_paper, paper, downloader)
                future_to_paper[future] = paper

            # Process completed downloads
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]

                try:
                    success, error_msg = future.result()

                    if success:
                        successful += 1
                        self._update_state(paper.paper_id, "completed")

                        # Update paper metadata
                        paper.pdf_downloaded = True
                        paper.pdf_download_timestamp = datetime.now().isoformat()

                        if self.progress_manager:
                            self.progress_manager.complete_download(
                                paper.paper_id, True
                            )
                    else:
                        failed += 1
                        self._update_state(paper.paper_id, "failed", error_msg)

                        # Update paper metadata
                        paper.pdf_download_error = error_msg

                        if self.progress_manager:
                            self.progress_manager.complete_download(
                                paper.paper_id, False
                            )

                except Exception as e:
                    logger.error(f"Unexpected error processing {paper.paper_id}: {e}")
                    failed += 1
                    self._update_state(paper.paper_id, "failed", str(e))

                    if self.progress_manager:
                        self.progress_manager.complete_download(paper.paper_id, False)

                # Save state periodically
                if (successful + failed) % 10 == 0:
                    self._save_state()

                    # Save papers if callback provided
                    if save_papers_callback:
                        save_papers_callback(papers)

        # Final state save
        self._save_state()

        # Save papers one final time
        if save_papers_callback:
            save_papers_callback(papers)

        # Stop progress manager
        if self.progress_manager:
            self.progress_manager.stop()

        logger.info(f"Download complete: {successful} successful, {failed} failed")
        return successful, failed

    def _download_single_paper(
        self, paper: Paper, downloader: PDFDownloader
    ) -> Tuple[bool, Optional[str]]:
        """Download a single paper.

        Args:
            paper: Paper to download
            downloader: PDF downloader instance

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check if already exists
            exists, location = self.storage_manager.exists(paper.paper_id)
            if exists:
                logger.info(f"{paper.paper_id} already exists in {location}")
                return True, None

            # Set up progress callback if manager exists
            progress_callback = None
            if self.progress_manager:
                progress_callback = self.progress_manager.get_progress_callback()

            # Download the PDF
            success = downloader.download_pdf(
                paper_id=paper.paper_id,
                pdf_url=paper.pdf_url,
                progress_callback=progress_callback,
                metadata={
                    "title": paper.title,
                    "authors": ", ".join(paper.authors) if paper.authors else "",
                    "year": paper.year,
                    "venue": paper.venue,
                    "source_url": paper.source_url,
                },
            )

            if success:
                return True, None
            else:
                return False, "Download failed"

        except Exception as e:
            error_msg = f"Error downloading {paper.paper_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_download_stats(self) -> Dict[str, Any]:
        """Get current download statistics.

        Returns:
            Dictionary with download stats
        """
        return {
            "completed": len(self.state.completed),
            "failed": len(self.state.failed),
            "in_progress": len(self.state.in_progress),
            "last_updated": self.state.last_updated,
            "storage_stats": self.storage_manager.get_storage_stats(),
        }
