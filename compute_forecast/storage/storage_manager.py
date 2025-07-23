"""Unified storage manager for coordinating local cache and Google Drive."""

import logging
from pathlib import Path
from typing import Optional, Dict, Callable, Tuple, Any
import os
from datetime import datetime

from .local_cache import LocalCache
from .google_drive import GoogleDriveStorage

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages PDF storage across local cache and Google Drive."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        google_drive_credentials: Optional[str] = None,
        google_drive_folder_id: Optional[str] = None,
    ):
        """Initialize storage manager.

        Args:
            cache_dir: Local cache directory (defaults to env or .cache/pdfs)
            google_drive_credentials: Path to Google credentials (defaults to env)
            google_drive_folder_id: Google Drive folder ID (defaults to env)
        """
        # Initialize local cache
        cache_dir = cache_dir or os.getenv("LOCAL_CACHE_DIR", ".cache/pdfs")
        self.local_cache = LocalCache(cache_dir)

        # Initialize Google Drive if credentials provided
        self.google_drive = None
        creds_path = google_drive_credentials or os.getenv("GOOGLE_CREDENTIALS_PATH")
        folder_id = google_drive_folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        if creds_path and folder_id:
            try:
                self.google_drive = GoogleDriveStorage(creds_path, folder_id)
                if self.google_drive.test_connection():
                    logger.info("Google Drive storage initialized successfully")
                else:
                    logger.warning("Google Drive connection test failed")
                    self.google_drive = None
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive: {e}")
                self.google_drive = None
        else:
            logger.info("Google Drive not configured, using local cache only")

    def exists(self, paper_id: str) -> Tuple[bool, str]:
        """Check if PDF exists in any storage location.

        Args:
            paper_id: Paper identifier

        Returns:
            Tuple of (exists, location) where location is "cache", "drive", or ""
        """
        # Check local cache first
        if self.local_cache.exists(paper_id):
            return True, "cache"

        # Check Google Drive
        if self.google_drive and self.google_drive.file_exists(paper_id):
            return True, "drive"

        return False, ""

    def get_pdf_path(self, paper_id: str) -> Optional[Path]:
        """Get path to PDF, downloading from Drive if necessary.

        Args:
            paper_id: Paper identifier

        Returns:
            Path to local PDF file or None if not found
        """
        # Check local cache first
        local_path = self.local_cache.get_path(paper_id)
        if local_path:
            return local_path

        # Try to download from Google Drive
        if self.google_drive:
            file_id = self.google_drive.get_file_id(paper_id)
            if file_id:
                # Download to cache
                cache_path = self.local_cache._get_cache_path(paper_id)
                downloaded_path = self.google_drive.download_with_progress(
                    file_id, paper_id, cache_path
                )
                if downloaded_path:
                    # Update cache metadata
                    self.local_cache.metadata[paper_id] = {
                        "path": str(
                            downloaded_path.relative_to(self.local_cache.cache_dir)
                        ),
                        "size": downloaded_path.stat().st_size,
                        "cached_at": datetime.now().isoformat(),
                        "from_drive": True,
                    }
                    self.local_cache._save_metadata()
                    return downloaded_path

        return None

    def save_pdf(
        self,
        paper_id: str,
        source_path: Path,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Save PDF to both local cache and Google Drive.

        Args:
            paper_id: Paper identifier
            source_path: Path to source PDF file
            progress_callback: Progress callback for uploads
            metadata: Optional metadata to store

        Returns:
            True if saved successfully to at least one location
        """
        logger.debug(f"Saving PDF for {paper_id} from {source_path}")
        success = False

        # Save to local cache first
        logger.debug(f"Saving {paper_id} to local cache")
        cache_path = self.local_cache.save(paper_id, source_path, metadata)
        if cache_path:
            success = True
            logger.info(f"Saved {paper_id} to local cache: {cache_path}")
        else:
            logger.error(f"Failed to save {paper_id} to local cache")

        # Upload to Google Drive
        if self.google_drive:
            logger.debug(f"Uploading {paper_id} to Google Drive")
            file_id = self.google_drive.upload_with_progress(
                source_path, paper_id, progress_callback, metadata
            )
            if file_id:
                success = True
                logger.info(f"Uploaded {paper_id} to Google Drive (file_id: {file_id})")
            else:
                logger.warning(f"Failed to upload {paper_id} to Google Drive")
        else:
            logger.debug(f"Google Drive not configured, skipping upload for {paper_id}")

        return success

    def save_pdf_from_bytes(
        self,
        paper_id: str,
        content: bytes,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Save PDF content to storage.

        Args:
            paper_id: Paper identifier
            content: PDF content as bytes
            progress_callback: Progress callback for uploads
            metadata: Optional metadata to store

        Returns:
            True if saved successfully
        """
        # Save to local cache first
        cache_path = self.local_cache.save_from_bytes(paper_id, content, metadata)
        if not cache_path:
            return False

        # Upload to Google Drive
        if self.google_drive:
            file_id = self.google_drive.upload_with_progress(
                cache_path, paper_id, progress_callback, metadata
            )
            if not file_id:
                logger.warning(f"Failed to upload {paper_id} to Google Drive")

        return True

    def remove(self, paper_id: str) -> bool:
        """Remove PDF from all storage locations.

        Args:
            paper_id: Paper identifier

        Returns:
            True if removed from at least one location
        """
        removed = False

        # Remove from local cache
        if self.local_cache.remove(paper_id):
            removed = True

        # Remove from Google Drive
        if self.google_drive:
            file_id = self.google_drive.get_file_id(paper_id)
            if file_id and self.google_drive.delete_file(file_id):
                removed = True

        return removed

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        stats = {
            "local_cache": self.local_cache.get_stats(),
            "google_drive": {
                "enabled": self.google_drive is not None,
                "connected": False,
            },
        }

        if self.google_drive:
            stats["google_drive"]["connected"] = self.google_drive.test_connection()

        return stats

    def verify_integrity(self, paper_id: str) -> bool:
        """Verify integrity of stored PDF.

        Args:
            paper_id: Paper identifier

        Returns:
            True if PDF exists and is valid
        """
        # Check local cache
        if self.local_cache.exists(paper_id):
            return self.local_cache.verify_integrity(paper_id)

        # Check Google Drive
        if self.google_drive:
            return self.google_drive.file_exists(paper_id)

        return False

    def sync_to_drive(
        self, progress_callback: Optional[Callable[[str, int, str, float], None]] = None
    ) -> Dict[str, int]:
        """Sync all cached PDFs to Google Drive.

        Args:
            progress_callback: Progress callback for uploads

        Returns:
            Dictionary with sync statistics
        """
        if not self.google_drive:
            logger.warning("Google Drive not configured, cannot sync")
            return {"skipped": len(self.local_cache.list_cached())}

        stats = {"uploaded": 0, "skipped": 0, "failed": 0}

        for paper_id in self.local_cache.list_cached():
            # Skip if already in Drive
            if self.google_drive.file_exists(paper_id):
                stats["skipped"] += 1
                continue

            # Upload to Drive
            cache_path = self.local_cache.get_path(paper_id)
            if cache_path:
                metadata = self.local_cache.get_metadata(paper_id)
                file_id = self.google_drive.upload_with_progress(
                    cache_path,
                    paper_id,
                    progress_callback,
                    metadata.get("metadata") if metadata else None,
                )
                if file_id:
                    stats["uploaded"] += 1
                else:
                    stats["failed"] += 1
            else:
                stats["failed"] += 1

        logger.info(f"Sync complete: {stats}")
        return stats

    def download_from_drive(
        self,
        paper_id: str,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
    ) -> Optional[Path]:
        """Download PDF from Google Drive to cache.

        Args:
            paper_id: Paper identifier
            progress_callback: Progress callback for download

        Returns:
            Path to downloaded file or None if failed
        """
        if not self.google_drive:
            logger.error("Google Drive not configured")
            return None

        file_id = self.google_drive.get_file_id(paper_id)
        if not file_id:
            logger.error(f"File not found in Google Drive: {paper_id}")
            return None

        cache_path = self.local_cache._get_cache_path(paper_id)
        downloaded_path = self.google_drive.download_with_progress(
            file_id, paper_id, cache_path, progress_callback
        )

        if downloaded_path:
            # Update cache metadata
            from datetime import datetime

            self.local_cache.metadata[paper_id] = {
                "path": str(cache_path.relative_to(self.local_cache.cache_dir)),
                "size": cache_path.stat().st_size,
                "cached_at": datetime.now().isoformat(),
                "from_drive": True,
            }
            self.local_cache._save_metadata()

        return downloaded_path
