"""Models for parallel collection communication."""

from dataclasses import dataclass
from typing import Optional
from ..sources.scrapers.models import SimplePaper


@dataclass
class CollectionResult:
    """Result item for queue-based communication between workers and main process."""
    
    venue: str
    year: int
    paper: Optional[SimplePaper] = None
    error: Optional[str] = None
    is_complete: bool = False  # Signals end of venue/year
    total_expected: Optional[int] = None  # For progress bar initialization
    
    @property
    def is_worker_done(self) -> bool:
        """Check if this signals worker completion."""
        return self.venue == "WORKER_DONE" and self.is_complete
    
    @classmethod
    def paper_result(cls, venue: str, year: int, paper: SimplePaper) -> "CollectionResult":
        """Create a result for a successfully collected paper."""
        return cls(venue=venue, year=year, paper=paper)
    
    @classmethod
    def error_result(cls, venue: str, year: int, error: str) -> "CollectionResult":
        """Create a result for an error during collection."""
        return cls(venue=venue, year=year, error=error)
    
    @classmethod
    def progress_result(cls, venue: str, year: int, total_expected: int) -> "CollectionResult":
        """Create a result for progress bar initialization."""
        return cls(venue=venue, year=year, total_expected=total_expected)
    
    @classmethod
    def completion_result(cls, venue: str, year: int) -> "CollectionResult":
        """Create a result signaling venue/year completion."""
        return cls(venue=venue, year=year, is_complete=True)
    
    @classmethod
    def worker_done_result(cls) -> "CollectionResult":
        """Create a result signaling worker completion."""
        return cls(venue="WORKER_DONE", year=0, is_complete=True)