"""Local file cache management for PDFs."""

import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalCache:
    """Local file cache for storing PDFs."""

    def __init__(self, cache_dir: str = ".cache/pdfs"):
        """Initialize local cache.

        Args:
            cache_dir: Directory to store cached PDFs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / ".cache_metadata.json"
        self._load_metadata()

    def _load_metadata(self):
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}

    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _get_paper_dir(self, paper_id: str) -> Path:
        """Get directory path for a paper.

        Uses first 2 characters of paper_id for directory sharding
        to avoid too many files in one directory.
        """
        # Create subdirectory based on first 2 chars of paper_id
        if len(paper_id) >= 2:
            subdir = paper_id[:2]
        else:
            subdir = "misc"

        paper_dir = self.cache_dir / subdir
        paper_dir.mkdir(parents=True, exist_ok=True)
        return paper_dir

    def _get_cache_path(self, paper_id: str) -> Path:
        """Get full cache path for a paper PDF."""
        paper_dir = self._get_paper_dir(paper_id)
        return paper_dir / f"{paper_id}.pdf"

    def exists(self, paper_id: str) -> bool:
        """Check if a PDF exists in cache.

        Args:
            paper_id: Paper identifier

        Returns:
            True if PDF exists in cache
        """
        cache_path = self._get_cache_path(paper_id)
        return cache_path.exists()

    def get_path(self, paper_id: str) -> Optional[Path]:
        """Get path to cached PDF if it exists.

        Args:
            paper_id: Paper identifier

        Returns:
            Path to cached PDF or None if not found
        """
        cache_path = self._get_cache_path(paper_id)
        if cache_path.exists():
            return cache_path
        return None

    def save(
        self, paper_id: str, source_path: Path, metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """Save a PDF to cache.

        Args:
            paper_id: Paper identifier
            source_path: Path to source PDF file
            metadata: Optional metadata to store

        Returns:
            Path to cached file or None if failed
        """
        if not source_path.exists():
            logger.error(f"Source file not found: {source_path}")
            return None

        try:
            cache_path = self._get_cache_path(paper_id)

            # Calculate file hash for integrity
            file_hash = self._calculate_hash(source_path)

            # Copy file to cache (atomic operation)
            temp_path = cache_path.with_suffix(".tmp")
            shutil.copy2(source_path, temp_path)
            temp_path.replace(cache_path)

            # Update metadata
            self.metadata[paper_id] = {
                "path": str(cache_path.relative_to(self.cache_dir)),
                "size": cache_path.stat().st_size,
                "hash": file_hash,
                "cached_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            self._save_metadata()

            logger.info(f"Cached PDF for {paper_id} at {cache_path}")
            return cache_path

        except Exception as e:
            logger.error(f"Failed to cache PDF for {paper_id}: {e}")
            return None

    def save_from_bytes(
        self, paper_id: str, content: bytes, metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """Save PDF content directly to cache.

        Args:
            paper_id: Paper identifier
            content: PDF content as bytes
            metadata: Optional metadata to store

        Returns:
            Path to cached file or None if failed
        """
        try:
            cache_path = self._get_cache_path(paper_id)

            # Calculate content hash
            file_hash = hashlib.sha256(content).hexdigest()

            # Write content atomically
            temp_path = cache_path.with_suffix(".tmp")
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_path.replace(cache_path)

            # Update metadata
            self.metadata[paper_id] = {
                "path": str(cache_path.relative_to(self.cache_dir)),
                "size": len(content),
                "hash": file_hash,
                "cached_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            self._save_metadata()

            logger.info(f"Cached PDF for {paper_id} from bytes")
            return cache_path

        except Exception as e:
            logger.error(f"Failed to cache PDF for {paper_id}: {e}")
            return None

    def remove(self, paper_id: str) -> bool:
        """Remove a PDF from cache.

        Args:
            paper_id: Paper identifier

        Returns:
            True if removed successfully
        """
        cache_path = self._get_cache_path(paper_id)

        try:
            if cache_path.exists():
                cache_path.unlink()

            # Remove from metadata
            if paper_id in self.metadata:
                del self.metadata[paper_id]
                self._save_metadata()

            logger.info(f"Removed {paper_id} from cache")
            return True

        except Exception as e:
            logger.error(f"Failed to remove {paper_id} from cache: {e}")
            return False

    def get_metadata(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a cached PDF.

        Args:
            paper_id: Paper identifier

        Returns:
            Metadata dictionary or None if not found
        """
        result = self.metadata.get(paper_id)
        return result if result is not None else None

    def list_cached(self) -> List[str]:
        """List all cached paper IDs.

        Returns:
            List of paper IDs in cache
        """
        return list(self.metadata.keys())

    def get_cache_size(self) -> int:
        """Get total size of cache in bytes.

        Returns:
            Total size in bytes
        """
        total_size = 0
        for paper_id, info in self.metadata.items():
            total_size += info.get("size", 0)
        return total_size

    def clear_cache(self) -> int:
        """Clear all cached files.

        Returns:
            Number of files removed
        """
        count = 0
        for paper_id in list(self.metadata.keys()):
            if self.remove(paper_id):
                count += 1

        logger.info(f"Cleared {count} files from cache")
        return count

    def verify_integrity(self, paper_id: str) -> bool:
        """Verify integrity of cached file.

        Args:
            paper_id: Paper identifier

        Returns:
            True if file is intact and matches stored hash
        """
        cache_path = self._get_cache_path(paper_id)
        metadata = self.metadata.get(paper_id)

        if not cache_path.exists() or not metadata:
            return False

        try:
            # Check file size
            actual_size = cache_path.stat().st_size
            if actual_size != metadata.get("size", -1):
                logger.warning(f"Size mismatch for {paper_id}")
                return False

            # Check hash if available
            if "hash" in metadata:
                actual_hash = self._calculate_hash(cache_path)
                if actual_hash != metadata["hash"]:
                    logger.warning(f"Hash mismatch for {paper_id}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to verify integrity for {paper_id}: {e}")
            return False

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex string of file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_size = 0
        total_files = len(self.metadata)

        for info in self.metadata.values():
            total_size += info.get("size", 0)

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_directory": str(self.cache_dir),
        }
