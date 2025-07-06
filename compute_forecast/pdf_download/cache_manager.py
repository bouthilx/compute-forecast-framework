"""Cache management utilities for PDF downloads."""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class PDFCacheManager:
    """Manages local cache for PDF files."""
    
    def __init__(self, cache_dir: str = "./pdf_cache"):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cached PDFs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_path(self, paper_id: str) -> Path:
        """Get the cache file path for a paper ID.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            Path to the cached file
        """
        return self.cache_dir / f"{paper_id}.pdf"
    
    def is_cached(self, paper_id: str) -> bool:
        """Check if a paper is already cached.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            True if the paper is cached
        """
        return self.get_cache_path(paper_id).exists()
    
    def get_cached_file(self, paper_id: str) -> Optional[Path]:
        """Get cached file if it exists.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            Path to cached file or None if not cached
        """
        cache_path = self.get_cache_path(paper_id)
        return cache_path if cache_path.exists() else None
    
    def save_to_cache(self, paper_id: str, content: bytes) -> Path:
        """Save PDF content to cache.
        
        Args:
            paper_id: Unique identifier for the paper
            content: PDF content to save
            
        Returns:
            Path to the saved file
        """
        cache_path = self.get_cache_path(paper_id)
        cache_path.write_bytes(content)
        logger.info(f"Saved PDF to cache: {paper_id}")
        return cache_path
    
    def list_cached_files(self) -> List[Path]:
        """List all cached PDF files.
        
        Returns:
            List of paths to cached PDFs
        """
        return list(self.cache_dir.glob("*.pdf"))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        pdf_files = self.list_cached_files()
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            "cache_dir": str(self.cache_dir),
            "total_files": len(pdf_files),
            "total_size_bytes": total_size,
            "average_size_bytes": total_size // len(pdf_files) if pdf_files else 0
        }
    
    def clear_cache(self) -> int:
        """Clear all cached PDFs.
        
        Returns:
            Number of files cleared
        """
        pdf_files = self.list_cached_files()
        
        for pdf_file in pdf_files:
            pdf_file.unlink()
        
        logger.info(f"Cleared {len(pdf_files)} files from cache")
        return len(pdf_files)
    
    def remove_from_cache(self, paper_id: str) -> bool:
        """Remove a specific file from cache.
        
        Args:
            paper_id: Paper ID to remove
            
        Returns:
            True if file was removed, False if not found
        """
        cache_path = self.get_cache_path(paper_id)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Removed {paper_id} from cache")
            return True
        return False