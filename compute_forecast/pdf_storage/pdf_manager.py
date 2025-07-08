"""PDF Manager with caching layer and Google Drive integration."""

import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import shutil

from .google_drive_store import GoogleDriveStore
from compute_forecast.pdf_download.cache_manager import PDFCacheManager

logger = logging.getLogger(__name__)


class PDFManager:
    """Manages PDFs with local caching and Google Drive storage."""

    def __init__(
        self,
        drive_store: GoogleDriveStore,
        cache_dir: str = "./temp_pdf_cache",
        max_cache_size_gb: float = 10.0,
        cache_ttl_days: int = 7,
        cache_ttl_hours: Optional[int] = None,
    ):
        """Initialize PDF Manager.

        Args:
            drive_store: Google Drive storage backend
            cache_dir: Directory for local cache
            max_cache_size_gb: Maximum cache size in GB
            cache_ttl_days: Cache time-to-live in days
            cache_ttl_hours: Cache time-to-live in hours (overrides cache_ttl_days)
        """
        self.drive_store = drive_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize cache manager (reuse existing implementation)
        self.cache_manager = PDFCacheManager(cache_dir)

        # Cache configuration
        self.max_cache_size_bytes = int(max_cache_size_gb * 1024 * 1024 * 1024)
        if cache_ttl_hours is not None:
            self.cache_ttl = timedelta(hours=cache_ttl_hours)
        else:
            self.cache_ttl = timedelta(days=cache_ttl_days)

        # Metadata tracking
        self.metadata_file = self.cache_dir / "pdf_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load PDF metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
        return {}

    def _save_metadata(self):
        """Save PDF metadata to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def get_pdf_for_analysis(self, paper_id: str) -> Optional[Path]:
        """Get PDF for analysis, downloading from Drive if needed.

        Args:
            paper_id: Paper identifier

        Returns:
            Path to PDF file or None if not found
        """
        # Check local cache first
        cached_file = self.cache_manager.get_cached_file(paper_id)
        if cached_file:
            logger.info(f"Using cached PDF for {paper_id}")
            return cached_file

        # Check if we have Drive file ID in metadata
        if paper_id not in self.metadata:
            logger.warning(f"No metadata found for {paper_id}")
            return None

        file_id = self.metadata[paper_id].get("drive_file_id")
        if not file_id:
            logger.warning(f"No Drive file ID found for {paper_id}")
            return None

        # Download from Drive
        try:
            destination = self.cache_manager.get_cache_path(paper_id)
            self.drive_store.download_pdf(file_id, destination)

            # Update access time in metadata
            self.metadata[paper_id]["last_accessed"] = datetime.utcnow().isoformat()
            self._save_metadata()

            return destination

        except Exception as e:
            logger.error(f"Failed to download {paper_id} from Drive: {e}")
            return None

    def store_pdf(
        self, paper_id: str, pdf_path: Path, metadata: Optional[Dict] = None
    ) -> bool:
        """Store a PDF in Google Drive and update metadata.

        Args:
            paper_id: Paper identifier
            pdf_path: Path to PDF file
            metadata: Optional metadata about the PDF

        Returns:
            True if successful
        """
        try:
            # Upload to Drive
            file_id = self.drive_store.upload_pdf(paper_id, pdf_path, metadata)

            # Update metadata
            self.metadata[paper_id] = {
                "drive_file_id": file_id,
                "upload_time": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "local_path": str(pdf_path),
                "metadata": metadata or {},
            }
            self._save_metadata()

            # Cache the file locally
            if pdf_path != self.cache_manager.get_cache_path(paper_id):
                shutil.copy2(pdf_path, self.cache_manager.get_cache_path(paper_id))

            logger.info(f"Successfully stored {paper_id} in Drive")
            return True

        except Exception as e:
            logger.error(f"Failed to store {paper_id}: {e}")
            return False

    def cleanup_cache(self, force: bool = False):
        """Clean up old cached files.

        Args:
            force: Force cleanup regardless of TTL
        """
        if force:
            count = self.cache_manager.clear_cache()
            logger.info(f"Force cleared {count} files from cache")
            return

        # Remove files older than TTL
        now = datetime.utcnow()
        removed_count = 0

        for paper_id, info in list(self.metadata.items()):
            # Use cached_at if available, otherwise try last_accessed
            cached_at_str = info.get("cached_at") or info.get("last_accessed")
            if not cached_at_str:
                continue

            try:
                last_accessed = datetime.fromisoformat(cached_at_str)
            except ValueError:
                # Skip entries with invalid timestamps
                continue

            if now - last_accessed > self.cache_ttl:
                if self.cache_manager.remove_from_cache(paper_id):
                    removed_count += 1
                    del self.metadata[paper_id]

        logger.info(f"Removed {removed_count} expired files from cache")

        # Check cache size and remove oldest if needed
        self._enforce_cache_size_limit()

        return removed_count

    def _enforce_cache_size_limit(self):
        """Ensure cache doesn't exceed size limit."""
        cache_stats = self.cache_manager.get_cache_stats()
        current_size = cache_stats["total_size_bytes"]

        if current_size <= self.max_cache_size_bytes:
            return

        # Sort by last accessed time
        sorted_papers = sorted(
            self.metadata.items(),
            key=lambda x: x[1].get("last_accessed", ""),
            reverse=False,  # Oldest first
        )

        # Remove files until under limit
        for paper_id, _ in sorted_papers:
            if current_size <= self.max_cache_size_bytes:
                break

            cache_path = self.cache_manager.get_cache_path(paper_id)
            if cache_path.exists():
                file_size = cache_path.stat().st_size
                self.cache_manager.remove_from_cache(paper_id)
                current_size -= file_size

    def sync_with_drive(self) -> Dict[str, Any]:
        """Sync metadata with Google Drive.

        Returns:
            Sync statistics
        """
        logger.info("Starting sync with Google Drive")

        # Get all files from Drive
        drive_files = self.drive_store.list_files()
        drive_file_map = {f["name"].replace(".pdf", ""): f for f in drive_files}

        # Stats
        stats = {
            "drive_files": len(drive_files),
            "local_metadata": len(self.metadata),
            "new_files": 0,
            "missing_files": 0,
        }

        # Find new files in Drive
        for paper_id, file_info in drive_file_map.items():
            if paper_id not in self.metadata:
                self.metadata[paper_id] = {
                    "drive_file_id": file_info["id"],
                    "upload_time": file_info["createdTime"],
                    "last_accessed": datetime.utcnow().isoformat(),
                    "metadata": file_info.get("parsed_description", {}),
                }
                stats["new_files"] += 1

        # Find missing files
        for paper_id in list(self.metadata.keys()):
            if paper_id not in drive_file_map:
                logger.warning(f"Paper {paper_id} not found in Drive")
                stats["missing_files"] += 1

        self._save_metadata()
        logger.info(f"Sync completed: {stats}")
        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """Get storage and cache statistics.

        Returns:
            Dictionary with statistics
        """
        cache_stats = self.cache_manager.get_cache_stats()

        return {
            "total_papers": len(self.metadata),
            "cache_stats": cache_stats,
            "cache_ttl_days": self.cache_ttl.days,
            "max_cache_size_gb": self.max_cache_size_bytes / (1024**3),
            "drive_connected": self.drive_store.test_connection(),
        }
