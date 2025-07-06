"""Data models for PDF discovery."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class PDFRecord:
    """Record of a discovered PDF with metadata."""
    
    paper_id: str
    pdf_url: str
    source: str
    discovery_timestamp: datetime
    confidence_score: float
    version_info: Dict[str, Any]
    validation_status: str
    file_size_bytes: Optional[int] = None
    license: Optional[str] = None
    
    def __eq__(self, other):
        """Equality based on paper_id and pdf_url."""
        if not isinstance(other, PDFRecord):
            return False
        return self.paper_id == other.paper_id and self.pdf_url == other.pdf_url
    
    def __hash__(self):
        """Hash based on paper_id and pdf_url for use in sets/dicts."""
        return hash((self.paper_id, self.pdf_url))
    
    def __str__(self):
        """String representation."""
        return (f"PDFRecord(paper_id={self.paper_id}, source={self.source}, "
                f"confidence={self.confidence_score:.2f}, status={self.validation_status})")


@dataclass
class DiscoveryResult:
    """Results from a PDF discovery operation."""
    
    total_papers: int
    discovered_count: int
    records: List[PDFRecord]
    failed_papers: List[str]
    source_statistics: Dict[str, Dict[str, int]]
    execution_time_seconds: float
    
    @property
    def discovery_rate(self) -> float:
        """Calculate the discovery rate as a percentage."""
        if self.total_papers == 0:
            return 0.0
        return self.discovered_count / self.total_papers
    
    def summary(self) -> str:
        """Generate a summary of the discovery results."""
        lines = [
            f"Discovered {self.discovered_count}/{self.total_papers} PDFs ({self.discovery_rate * 100:.1f}%)",
            f"Execution time: {self.execution_time_seconds:.1f}s",
            "Source breakdown:"
        ]
        
        for source, stats in self.source_statistics.items():
            successful = stats.get("successful", 0)
            attempted = stats.get("attempted", 0)
            lines.append(f"  - {source}: {successful}/{attempted}")
        
        return "\n".join(lines)