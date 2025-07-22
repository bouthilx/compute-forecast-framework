"""Orchestrator for coordinating parallel PDF downloads."""

import logging
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import time
from datetime import datetime
import threading
from queue import Queue
from enum import Enum

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.storage import StorageManager
from compute_forecast.workers import PDFDownloader
from compute_forecast.monitoring import DownloadProgressManager

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be sent through the queue."""
    DOWNLOAD_COMPLETE = "download_complete"
    DOWNLOAD_FAILED = "download_failed"
    PROGRESS_UPDATE = "progress_update"
    STOP = "stop"


@dataclass
class QueueMessage:
    """Message sent through the queue from workers to processor."""
    type: MessageType
    paper_id: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailedPaper:
    """Detailed information about a failed paper download."""

    paper_id: str
    title: str
    pdf_url: str
    error_message: str
    error_type: (
        str  # 'http_404', 'http_error', 'timeout', 'validation', 'storage', 'other'
    )
    attempts: int
    last_attempt: str
    permanent_failure: bool = False  # If true, don't retry even with --retry-failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "pdf_url": self.pdf_url,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "attempts": self.attempts,
            "last_attempt": self.last_attempt,
            "permanent_failure": self.permanent_failure,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailedPaper":
        return cls(
            paper_id=data["paper_id"],
            title=data["title"],
            pdf_url=data["pdf_url"],
            error_message=data["error_message"],
            error_type=data["error_type"],
            attempts=data["attempts"],
            last_attempt=data["last_attempt"],
            permanent_failure=data.get("permanent_failure", False),
        )


@dataclass
class DownloadState:
    """State for download progress tracking."""

    completed: List[str]
    failed: Dict[str, str]  # paper_id -> error message (legacy)
    in_progress: List[str]
    last_updated: Optional[str]
    failed_papers: List[FailedPaper] = field(
        default_factory=list
    )  # Detailed failure information

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": self.in_progress,
            "last_updated": self.last_updated,
        }
        if self.failed_papers:
            result["failed_papers"] = [fp.to_dict() for fp in self.failed_papers]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadState":
        """Create from dictionary."""
        failed_papers = []
        if "failed_papers" in data:
            failed_papers = [FailedPaper.from_dict(fp) for fp in data["failed_papers"]]

        return cls(
            completed=data.get("completed", []),
            failed=data.get("failed", {}),
            in_progress=data.get("in_progress", []),
            last_updated=data.get("last_updated"),
            failed_papers=failed_papers,
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
        
        # Queue for worker communication
        self._message_queue: Queue[QueueMessage] = Queue()
        self._processor_thread: Optional[threading.Thread] = None
        self._stop_processor = threading.Event()

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

    def _categorize_error(self, error_message: str) -> Tuple[str, bool]:
        """Categorize error and determine if it's a permanent failure.

        Returns:
            Tuple of (error_type, is_permanent)
        """
        error_lower = error_message.lower()

        if "http 404" in error_lower:
            return "http_404", True  # 404 errors are permanent
        elif "http 403" in error_lower:
            return "http_403", True  # Forbidden, likely permanent
        elif "http 401" in error_lower:
            return "http_401", True  # Unauthorized, likely permanent
        elif "http" in error_lower and any(
            code in error_lower for code in ["500", "502", "503", "504"]
        ):
            return "http_server_error", False  # Server errors might be temporary
        elif "timeout" in error_lower:
            return "timeout", False  # Timeouts might be temporary
        elif "connection" in error_lower:
            return "connection_error", False  # Connection issues might be temporary
        elif "validation" in error_lower or "invalid" in error_lower:
            return "validation_error", True  # File validation errors are permanent
        elif "storage" in error_lower:
            return "storage_error", False  # Storage errors might be temporary
        else:
            return "other", False  # Unknown errors default to non-permanent

    def _update_state(
        self,
        paper_id: str,
        status: str,
        error: Optional[str] = None,
        paper_info: Optional[Dict] = None,
    ):
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
                # Remove from failed_papers if it was there
                self.state.failed_papers = [
                    fp for fp in self.state.failed_papers if fp.paper_id != paper_id
                ]
            elif status == "failed":
                self.state.failed[paper_id] = error or "Unknown error"

                # Add detailed failure information
                if paper_info and error:
                    error_type, is_permanent = self._categorize_error(error)

                    # Check if this paper already exists in failed_papers
                    existing_failure = None
                    for fp in self.state.failed_papers:
                        if fp.paper_id == paper_id:
                            existing_failure = fp
                            break

                    if existing_failure:
                        # Update existing failure
                        existing_failure.error_message = error
                        existing_failure.error_type = error_type
                        existing_failure.attempts += 1
                        existing_failure.last_attempt = datetime.now().isoformat()
                        existing_failure.permanent_failure = is_permanent
                    else:
                        # Create new failure record
                        failed_paper = FailedPaper(
                            paper_id=paper_id,
                            title=paper_info.get("title", "Unknown"),
                            pdf_url=paper_info.get("pdf_url", "Unknown"),
                            error_message=error,
                            error_type=error_type,
                            attempts=1,
                            last_attempt=datetime.now().isoformat(),
                            permanent_failure=is_permanent,
                        )
                        self.state.failed_papers.append(failed_paper)

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
        # Always load state to check for permanent failures
        if resume or retry_failed:
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

            # Skip permanently failed papers even if retry_failed is set
            permanent_failure = any(
                fp.paper_id == paper_id and fp.permanent_failure
                for fp in self.state.failed_papers
            )
            if permanent_failure:
                logger.debug(
                    f"Skipping {paper_id} - permanent failure (will not retry)"
                )
                continue

            papers_to_download.append(paper)

        return papers_to_download

    def _process_results(self, papers: List[Paper], save_papers_callback: Optional[Callable[[List[Paper]], None]] = None):
        """Process results from the message queue.
        
        Args:
            papers: List of all papers being downloaded
            save_papers_callback: Optional callback to save updated papers
        """
        logger.info("Starting result processor thread")
        processed_count = 0
        paper_dict = {p.paper_id: p for p in papers}
        
        while not self._stop_processor.is_set() or not self._message_queue.empty():
            try:
                # Get message with timeout to allow checking stop flag
                message = self._message_queue.get(timeout=0.1)
            except:
                continue
                
            if message.type == MessageType.STOP:
                break
                
            paper = paper_dict.get(message.paper_id)
            if not paper:
                logger.warning(f"Unknown paper ID in message: {message.paper_id}")
                continue
                
            if message.type == MessageType.DOWNLOAD_COMPLETE:
                self._update_state(message.paper_id, "completed")
                logger.info(f"Successfully downloaded PDF for {message.paper_id}")
                
                # Update paper metadata
                paper.pdf_downloaded = True
                paper.pdf_download_timestamp = datetime.now().isoformat()
                
                if self.progress_manager:
                    self.progress_manager.complete_download(message.paper_id, True)
                    
            elif message.type == MessageType.DOWNLOAD_FAILED:
                error_msg = message.data.get("error", "Unknown error")
                permanent = message.data.get("permanent", False)
                
                # Prepare paper info for detailed failure tracking
                paper_info = {
                    "title": paper.title,
                    "pdf_url": paper.processing_flags.get("selected_pdf_url", "Unknown"),
                }
                self._update_state(message.paper_id, "failed", error_msg, paper_info)
                logger.info(f"Failed to download PDF for {message.paper_id}: {error_msg}")
                
                # Update paper metadata
                paper.pdf_download_error = error_msg
                
                if self.progress_manager:
                    self.progress_manager.complete_download(
                        message.paper_id, False, permanent_failure=permanent
                    )
                    
            elif message.type == MessageType.PROGRESS_UPDATE:
                # Forward progress updates to progress manager
                if self.progress_manager and hasattr(self.progress_manager, 'update_download'):
                    callback = self.progress_manager.get_progress_callback()
                    callback(
                        message.paper_id,
                        message.data.get('bytes', 0),
                        message.data.get('operation', ''),
                        message.data.get('speed', 0.0)
                    )
                
            processed_count += 1
            
            # Save state periodically
            if processed_count % 10 == 0:
                self._save_state()
                # Save papers if callback provided
                if save_papers_callback:
                    save_papers_callback(papers)
                    
        logger.info("Result processor thread finished")

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

        # Start result processor thread
        self._stop_processor.clear()
        self._processor_thread = threading.Thread(
            target=self._process_results,
            args=(papers, save_papers_callback),
            name="DownloadResultProcessor"
        )
        self._processor_thread.start()

        # Track results
        successful = 0
        failed = 0

        # Shuffle papers to distribute requests across different venue servers
        shuffled_papers = papers.copy()
        random.shuffle(shuffled_papers)
        logger.info(f"Shuffled {len(shuffled_papers)} papers to distribute load across venues")

        # Process papers in parallel
        logger.info(f"Starting parallel download with {self.parallel_workers} workers")
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
            # Submit download tasks
            future_to_paper = {}

            for paper in shuffled_papers:
                # Apply rate limiting
                self._enforce_rate_limit()

                # Update state
                self._update_state(paper.paper_id, "in_progress")

                # Submit download task
                logger.debug(f"Submitting download task for {paper.paper_id}")
                future = executor.submit(self._download_single_paper, paper, downloader)
                future_to_paper[future] = paper

            # Process completed downloads
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]

                try:
                    success, error_msg = future.result()

                    if success:
                        successful += 1
                        # Send success message to queue
                        message = QueueMessage(
                            type=MessageType.DOWNLOAD_COMPLETE,
                            paper_id=paper.paper_id
                        )
                        self._message_queue.put(message)
                    else:
                        failed += 1
                        # Determine if this is a permanent failure
                        _, is_permanent = self._categorize_error(error_msg)
                        
                        # Send failure message to queue
                        message = QueueMessage(
                            type=MessageType.DOWNLOAD_FAILED,
                            paper_id=paper.paper_id,
                            data={"error": error_msg, "permanent": is_permanent}
                        )
                        self._message_queue.put(message)

                except Exception as e:
                    logger.error(f"Unexpected error processing {paper.paper_id}: {e}")
                    failed += 1
                    
                    # Send failure message to queue
                    message = QueueMessage(
                        type=MessageType.DOWNLOAD_FAILED,
                        paper_id=paper.paper_id,
                        data={"error": str(e), "permanent": False}
                    )
                    self._message_queue.put(message)

        # Stop processor thread
        self._stop_processor.set()
        # Send stop message to ensure processor exits
        self._message_queue.put(QueueMessage(type=MessageType.STOP, paper_id=""))
        
        # Wait for processor to finish
        if self._processor_thread:
            self._processor_thread.join(timeout=30)
            if self._processor_thread.is_alive():
                logger.warning("Result processor thread did not finish in time")
        
        # Final state save
        self._save_state()

        # Save papers one final time
        if save_papers_callback:
            save_papers_callback(papers)

        # Stop progress manager
        if self.progress_manager:
            self.progress_manager.stop()

        # Count actual results from state
        with self._state_lock:
            actual_successful = len(self.state.completed)
            actual_failed = len(self.state.failed)

        logger.info(f"Download complete: {actual_successful} successful, {actual_failed} failed")
        return actual_successful, actual_failed

    def export_failed_papers(
        self, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Export detailed information about failed papers to JSON file.

        Args:
            output_path: Output file path (defaults to timestamped file)

        Returns:
            Path to exported file or None if no failures
        """
        if not self.state.failed_papers:
            logger.info("No failed papers to export")
            return None

        # Generate default output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"failed_papers_{timestamp}.json")

        # Prepare export data
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_failed_papers": len(self.state.failed_papers),
            "permanent_failures": len(
                [fp for fp in self.state.failed_papers if fp.permanent_failure]
            ),
            "temporary_failures": len(
                [fp for fp in self.state.failed_papers if not fp.permanent_failure]
            ),
            "failed_papers": [fp.to_dict() for fp in self.state.failed_papers],
            "summary_by_error_type": self._get_error_type_summary(),
        }

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        try:
            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2)
            logger.info(
                f"Exported {len(self.state.failed_papers)} failed papers to {output_path}"
            )
            return output_path
        except Exception as e:
            logger.error(f"Failed to export failed papers: {e}")
            return None

    def _get_error_type_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary statistics by error type."""
        if not self.state.failed_papers:
            return {}

        summary = {}
        for fp in self.state.failed_papers:
            error_type = fp.error_type
            if error_type not in summary:
                summary[error_type] = {"count": 0, "permanent": 0, "temporary": 0}

            summary[error_type]["count"] += 1
            if fp.permanent_failure:
                summary[error_type]["permanent"] += 1
            else:
                summary[error_type]["temporary"] += 1

        return summary

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

            # Set up progress callback that sends messages to queue
            def progress_callback(paper_id: str, bytes_transferred: int, operation: str, speed: float):
                # Send progress update through queue
                message = QueueMessage(
                    type=MessageType.PROGRESS_UPDATE,
                    paper_id=paper_id,
                    data={
                        "bytes": bytes_transferred,
                        "operation": operation,
                        "speed": speed
                    }
                )
                self._message_queue.put(message)

            # Get PDF URL from processing_flags (set by load_papers_for_download)
            pdf_url = paper.processing_flags.get("selected_pdf_url")
            if not pdf_url:
                return False, "No PDF URL found"

            # Download the PDF
            success, download_error = downloader.download_pdf(
                paper_id=paper.paper_id,
                pdf_url=pdf_url,
                progress_callback=progress_callback,
                metadata={
                    "title": paper.title,
                    "authors": ", ".join([a.name for a in paper.authors])
                    if paper.authors
                    else "",
                    "year": paper.year,
                    "venue": paper.venue,
                    "urls": [url.data.url for url in paper.urls],
                },
            )

            if success:
                return True, None
            else:
                return False, download_error or "Download failed"

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
