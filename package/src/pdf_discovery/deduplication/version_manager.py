"""Version management for selecting best PDF versions."""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from src.pdf_discovery.core.models import PDFRecord

logger = logging.getLogger(__name__)


@dataclass
class SourcePriority:
    """Configuration for source priorities."""
    source_rankings: Dict[str, int]
    prefer_published: bool = True
    
    def get_priority(self, source: str) -> int:
        """Get priority for a source (higher is better)."""
        return self.source_rankings.get(source, 0)


class VersionManager:
    """Manage version selection for duplicate papers."""
    
    def __init__(self):
        """Initialize version manager with default priorities."""
        # Default source priorities (higher is better)
        self.default_priorities = SourcePriority(
            source_rankings={
                'venue_direct': 10,     # Direct from venue (ACL, PMLR, OpenReview)
                'semantic_scholar': 8,
                'openalex': 7,
                'arxiv': 5,
                'repository': 3,
                'other': 1,
            },
            prefer_published=True
        )
        
        self.custom_priorities = None
    
    def set_priorities(self, priorities: SourcePriority):
        """Set custom source priorities."""
        self.custom_priorities = priorities
    
    def select_best_version(self, versions: List[PDFRecord]) -> PDFRecord:
        """Select the best version from multiple PDFs of the same paper.
        
        Selection criteria (in order):
        1. Validation status (valid > unknown > invalid)
        2. Published vs preprint (if prefer_published is True)
        3. Source priority ranking
        4. Confidence score
        5. Discovery timestamp (newer is better)
        
        Args:
            versions: List of PDFRecord for the same paper
            
        Returns:
            The best PDFRecord according to selection criteria
        """
        if not versions:
            raise ValueError("No versions provided")
        
        if len(versions) == 1:
            return versions[0]
        
        priorities = self.custom_priorities or self.default_priorities
        
        # Score each version
        scored_versions = []
        for version in versions:
            score = self._calculate_version_score(version, priorities)
            scored_versions.append((score, version))
        
        # Sort by score (descending) and return best
        scored_versions.sort(key=lambda x: x[0], reverse=True)
        
        best_version = scored_versions[0][1]
        
        # Log decision if there were close alternatives
        if len(scored_versions) > 1:
            second_best_score = scored_versions[1][0]
            if scored_versions[0][0] - second_best_score < 0.1:
                logger.debug(
                    f"Close decision for paper {best_version.paper_id}: "
                    f"selected {best_version.source} (score: {scored_versions[0][0]:.3f}) "
                    f"over {scored_versions[1][1].source} (score: {second_best_score:.3f})"
                )
        
        return best_version
    
    def _calculate_version_score(self, record: PDFRecord, priorities: SourcePriority) -> float:
        """Calculate a score for version selection.
        
        Returns a score between 0 and 100.
        """
        score = 0.0
        
        # 1. Validation status (0-20 points)
        if record.validation_status == "valid":
            score += 20
        elif record.validation_status == "unknown":
            score += 10
        # invalid gets 0
        
        # 2. Published vs preprint (0-20 points)
        if priorities.prefer_published:
            version_info = record.version_info or {}
            if version_info.get("is_published", False):
                score += 20
            elif version_info.get("is_preprint", False):
                score += 5
        
        # 3. Source priority (0-30 points)
        source_priority = priorities.get_priority(record.source)
        max_priority = max(priorities.source_rankings.values())
        if max_priority > 0:
            score += (source_priority / max_priority) * 30
        
        # 4. Confidence score (0-20 points)
        score += record.confidence_score * 20
        
        # 5. File size indicator (0-10 points)
        # Prefer files with reasonable size (not too small)
        if record.file_size_bytes:
            if record.file_size_bytes > 100_000:  # > 100KB
                score += 10
            elif record.file_size_bytes > 50_000:  # > 50KB
                score += 5
        
        return score