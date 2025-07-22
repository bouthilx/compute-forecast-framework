"""
Extended models for consolidation pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper


@dataclass
class PaperIdentifiers:
    """Complete identifier set for a paper collected during consolidation."""

    paper_id: str  # Our internal ID
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID
    pmcid: Optional[str] = None  # PubMed Central ID
    mag_id: Optional[str] = None  # Microsoft Academic Graph ID

    def has_external_ids(self) -> bool:
        """Check if paper has any external identifiers for batch lookups."""
        return bool(self.doi or self.arxiv_id or self.semantic_scholar_id or self.pmid)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "paper_id": self.paper_id,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "openalex_id": self.openalex_id,
            "semantic_scholar_id": self.semantic_scholar_id,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "mag_id": self.mag_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperIdentifiers":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConsolidationPhaseState:
    """Tracks the state of two-phase consolidation."""

    phase: str  # "id_harvesting", "semantic_scholar_enrichment", "openalex_enrichment", "parallel_consolidation", "completed"
    phase_completed: bool = False
    phase_start_time: Optional[datetime] = None
    phase_end_time: Optional[datetime] = None
    identifiers_collected: Dict[str, PaperIdentifiers] = field(default_factory=dict)

    # Phase-specific progress
    papers_with_dois: int = 0
    papers_with_arxiv: int = 0
    papers_with_s2_ids: int = 0
    papers_with_external_ids: int = 0

    # Batch-level progress tracking for resume
    batch_progress: Dict[str, Any] = field(default_factory=dict)

    # Simple set of processed paper hashes for efficient resume
    processed_paper_hashes: Set[str] = field(default_factory=set)

    # Parallel consolidation state
    openalex_processed_hashes: Set[str] = field(default_factory=set)
    semantic_scholar_processed_hashes: Set[str] = field(default_factory=set)
    merged_papers: List[Paper] = field(default_factory=list)
    papers_processed: int = 0
    papers_enriched: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for checkpointing."""
        result = {
            "phase": self.phase,
            "phase_completed": self.phase_completed,
            "phase_start_time": self.phase_start_time.isoformat()
            if self.phase_start_time
            else None,
            "phase_end_time": self.phase_end_time.isoformat()
            if self.phase_end_time
            else None,
            "identifiers_collected": {
                k: v.to_dict() for k, v in self.identifiers_collected.items()
            },
            "papers_with_dois": self.papers_with_dois,
            "papers_with_arxiv": self.papers_with_arxiv,
            "papers_with_s2_ids": self.papers_with_s2_ids,
            "papers_with_external_ids": self.papers_with_external_ids,
            "batch_progress": self.batch_progress,
            "processed_paper_hashes": list(self.processed_paper_hashes),
        }

        # Add parallel consolidation fields if in that phase
        if self.phase == "parallel_consolidation":
            result["openalex_processed_hashes"] = list(self.openalex_processed_hashes)
            result["semantic_scholar_processed_hashes"] = list(
                self.semantic_scholar_processed_hashes
            )
            # Don't serialize merged_papers - they'll be saved separately
            result["papers_processed"] = self.papers_processed
            result["papers_enriched"] = self.papers_enriched

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsolidationPhaseState":
        """Create from dictionary."""
        state = cls(
            phase=data["phase"],
            phase_completed=data["phase_completed"],
            phase_start_time=datetime.fromisoformat(data["phase_start_time"])
            if data.get("phase_start_time")
            else None,
            phase_end_time=datetime.fromisoformat(data["phase_end_time"])
            if data.get("phase_end_time")
            else None,
            papers_with_dois=data.get("papers_with_dois", 0),
            papers_with_arxiv=data.get("papers_with_arxiv", 0),
            papers_with_s2_ids=data.get("papers_with_s2_ids", 0),
            papers_with_external_ids=data.get("papers_with_external_ids", 0),
            batch_progress=data.get("batch_progress", {}),
            processed_paper_hashes=set(data.get("processed_paper_hashes", [])),
            papers_processed=data.get("papers_processed", 0),
            papers_enriched=data.get("papers_enriched", 0),
        )

        # Restore identifiers
        if "identifiers_collected" in data:
            state.identifiers_collected = {
                k: PaperIdentifiers.from_dict(v)
                for k, v in data["identifiers_collected"].items()
            }

        # Restore parallel consolidation state
        if data["phase"] == "parallel_consolidation":
            state.openalex_processed_hashes = set(
                data.get("openalex_processed_hashes", [])
            )
            state.semantic_scholar_processed_hashes = set(
                data.get("semantic_scholar_processed_hashes", [])
            )
            # merged_papers will be loaded separately

        return state
