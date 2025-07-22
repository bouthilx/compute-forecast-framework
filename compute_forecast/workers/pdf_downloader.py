"""Worker for downloading individual PDFs."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Callable, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import tempfile

from compute_forecast.storage import StorageManager

logger = logging.getLogger(__name__)


class PDFDownloader:
    """Downloads PDFs from URLs with retry logic and progress tracking."""

    # Minimum PDF size (1KB) - anything smaller is likely an error page
    MIN_PDF_SIZE = 1024

    # PDF magic number
    PDF_HEADER = b"%PDF"

    def __init__(
        self,
        storage_manager: StorageManager,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5,
        exponential_backoff: bool = False,
        chunk_size: int = 8192,
    ):
        """Initialize PDF downloader.

        Args:
            storage_manager: Storage manager for saving PDFs
            timeout: Download timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries in seconds
            exponential_backoff: Use exponential backoff for retries
            chunk_size: Size of chunks for streaming downloads
        """
        self.storage_manager = storage_manager
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.chunk_size = chunk_size

        # Configure session with retry strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay if self.exponential_backoff else 0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        return session

    def download_pdf(
        self,
        paper_id: str,
        pdf_url: str,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Download a PDF from URL and save to storage.

        Args:
            paper_id: Paper identifier
            pdf_url: URL to download PDF from
            progress_callback: Progress callback function with signature:
                (paper_id: str, bytes_transferred: int, operation: str, speed: float) -> None
                - paper_id: The paper being processed
                - bytes_transferred: Bytes downloaded so far (or total size at start)
                - operation: "Starting", "Downloading", "Uploading to Drive", etc.
                - speed: Transfer speed in bytes/second
            metadata: Optional metadata to store with PDF

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            - success: True if download and storage succeeded
            - error_message: Detailed error description if failed, None if successful
        """
        logger.info(f"Downloading PDF for {paper_id} from {pdf_url}")

        # Notify progress manager about starting download
        if progress_callback:
            progress_callback(paper_id, 0, "Starting", 0)

        # Check if already exists
        exists, location = self.storage_manager.exists(paper_id)
        if exists:
            logger.info(f"PDF for {paper_id} already exists in {location}")
            return True, None

        # Download with retries
        for attempt in range(self.max_retries + 1):
            try:
                success, error = self._download_attempt(
                    paper_id, pdf_url, progress_callback, metadata
                )

                if success:
                    return True, None

                # Check if error is retryable
                if not self._is_retryable_error(error) or attempt == self.max_retries:
                    logger.info(f"Non-retryable error or max retries reached: {error}")
                    return False, error

                # Calculate retry delay
                if self.exponential_backoff:
                    delay = self.retry_delay * (2**attempt)
                else:
                    delay = self.retry_delay

                logger.info(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s: {error}"
                )
                time.sleep(delay)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Unexpected error downloading {paper_id}: {e}")
                if attempt == self.max_retries:
                    return False, error_msg

        return False, "Maximum retries exceeded"

    def _download_attempt(
        self,
        paper_id: str,
        pdf_url: str,
        progress_callback: Optional[Callable[[str, int, str, float], None]],
        metadata: Optional[Dict],
    ) -> Tuple[bool, Optional[str]]:
        """Single download attempt.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Make request
            logger.debug(f"Making HTTP request to {pdf_url}")
            response = self.session.get(
                pdf_url, timeout=self.timeout, stream=True, allow_redirects=True
            )

            # Check status code
            logger.debug(f"HTTP response status: {response.status_code}")
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                # Try to get more details from response
                if response.text and len(response.text) < 500:
                    # Include short error messages from server
                    error_msg += f" - {response.text.strip()}"
                elif response.reason:
                    error_msg += f" - {response.reason}"
                return False, error_msg

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            logger.debug(f"Content type: {content_type}")
            if "pdf" not in content_type and "octet-stream" not in content_type:
                logger.warning(
                    f"Unexpected content type for {paper_id}: {content_type}"
                )

            # Get content length
            content_length = int(response.headers.get("Content-Length", 0))
            logger.debug(
                f"Content length: {content_length} bytes ({content_length / 1024 / 1024:.1f} MB)"
            )

            # Initialize progress tracking
            if progress_callback and content_length > 0:
                progress_callback(paper_id, content_length, "Downloading", 0.0)

            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = Path(tmp_file.name)
                logger.debug(f"Downloading to temporary file: {tmp_path}")

                bytes_downloaded = 0
                start_time = time.time()

                # Download in chunks
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        tmp_file.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Update progress
                        if progress_callback and content_length > 0:
                            elapsed = time.time() - start_time
                            speed = bytes_downloaded / elapsed if elapsed > 0 else 0
                            progress_callback(
                                paper_id, bytes_downloaded, "Downloading", speed
                            )

            logger.debug(f"Downloaded {bytes_downloaded} bytes to temporary file")

            # Validate downloaded file
            logger.debug(f"Validating downloaded file: {tmp_path}")
            validation_error = self._validate_pdf(tmp_path, bytes_downloaded)
            if validation_error:
                logger.warning(
                    f"PDF validation failed for {paper_id}: {validation_error}"
                )
                tmp_path.unlink()  # Delete invalid file
                return False, validation_error

            # Save to storage
            logger.debug(f"Saving PDF to storage for {paper_id}")
            success = self.storage_manager.save_pdf(
                paper_id, tmp_path, progress_callback, metadata
            )

            # Clean up temp file
            tmp_path.unlink()
            logger.debug(f"Cleaned up temporary file: {tmp_path}")

            if success:
                logger.info(f"Successfully downloaded PDF for {paper_id}")
                return True, None
            else:
                logger.error(f"Failed to save PDF to storage for {paper_id}")
                return False, "Failed to save to storage"

        except requests.exceptions.Timeout as e:
            return False, f"Download timeout after {self.timeout}s: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection error: {str(e)}"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {type(e).__name__}: {str(e)}"

    def _validate_pdf(self, file_path: Path, expected_size: int) -> Optional[str]:
        """Validate downloaded PDF file.

        Args:
            file_path: Path to downloaded file
            expected_size: Expected file size

        Returns:
            Error message if invalid, None if valid
        """
        # Check file exists
        if not file_path.exists():
            return "File does not exist"

        # Check file size
        actual_size = file_path.stat().st_size
        if actual_size < self.MIN_PDF_SIZE:
            return f"File too small ({actual_size} bytes)"

        if expected_size > 0 and actual_size != expected_size:
            logger.warning(
                f"Size mismatch: expected {expected_size}, got {actual_size}"
            )

        # Check for common error page patterns first (more specific than PDF header check)
        try:
            with open(file_path, "rb") as f:
                # Read first 1KB
                content = f.read(1024)
                content_lower = content.lower()

                # Check for HTML content
                if b"<html" in content_lower or b"<!doctype" in content_lower:
                    return "File appears to be HTML, not PDF"

                # Reset to check PDF header from the beginning
                f.seek(0)
                header = f.read(4)
                if header != self.PDF_HEADER:
                    return f"Invalid PDF header: {header}"

                # Check for common error messages with more specific categorization
                error_patterns = [
                    (
                        b"404 not found",
                        "HTTP 404 - Page not found in downloaded content",
                    ),
                    (
                        b"403 forbidden",
                        "HTTP 403 - Access forbidden in downloaded content",
                    ),
                    (
                        b"401 unauthorized",
                        "HTTP 401 - Unauthorized access in downloaded content",
                    ),
                    (b"access denied", "Access denied by server"),
                    (b"error occurred", "Server error page detected"),
                    (b"page not found", "Page not found error in content"),
                    (b"not available", "Content not available"),
                    (b"coming soon", "Content not yet available"),
                ]

                for pattern, message in error_patterns:
                    if pattern in content_lower:
                        return message

        except Exception as e:
            logger.warning(f"Failed to check file content: {e}")

        return None

    def _is_retryable_error(self, error: Optional[str]) -> bool:
        """Check if error is retryable.

        Args:
            error: Error message

        Returns:
            True if error is retryable
        """
        if not error:
            return True

        # Non-retryable errors
        non_retryable = [
            "HTTP 404",  # Not found
            "HTTP 403",  # Forbidden
            "HTTP 401",  # Unauthorized
            "Invalid PDF",
            "File appears to be HTML",
            "access denied",
            "forbidden",
        ]

        error_lower = error.lower()
        for pattern in non_retryable:
            if pattern.lower() in error_lower:
                return False

        return True

    def close(self):
        """Close the downloader and clean up resources."""
        self.session.close()
