"""Merge worker that combines results from parallel sources."""

import threading
import queue
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.models import (
    CitationData,
    CitationRecord,
    AbstractData,
    AbstractRecord,
    URLData,
    URLRecord,
    IdentifierData,
    IdentifierRecord,
)

logger = logging.getLogger(__name__)


class MergeWorker(threading.Thread):
    """Worker that merges enrichment results from multiple sources."""

    def __init__(
        self,
        input_queue: queue.Queue,
        output_queue: queue.Queue,
        error_queue: queue.Queue,
        checkpoint_callback: Optional[Callable[[], None]] = None,
        checkpoint_interval: int = 300,  # 5 minutes default
    ):
        super().__init__(name="MergeWorker")
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.error_queue = error_queue
        self.checkpoint_callback = checkpoint_callback
        self.checkpoint_interval = checkpoint_interval

        # Control flags
        self.stop_event = threading.Event()

        # Track merged papers
        self.merged_papers: Dict[str, Paper] = {}  # paper_id -> Paper
        self.papers_by_hash: Dict[str, str] = {}  # paper_hash -> paper_id

        # Statistics
        self.papers_merged = 0
        self.last_checkpoint = time.time()
        self.start_time = None

    def stop(self):
        """Signal the worker to stop."""
        self.stop_event.set()

    def run(self):
        """Main merge loop."""
        self.start_time = time.time()
        logger.info("MergeWorker started")

        try:
            while not self.stop_event.is_set():
                try:
                    # Get enrichment result with timeout
                    result = self.input_queue.get(timeout=0.1)

                    # Process the enrichment
                    self._merge_enrichment(result)

                    # Checkpoint if needed
                    if (
                        self.checkpoint_callback
                        and time.time() - self.last_checkpoint
                        > self.checkpoint_interval
                    ):
                        self.checkpoint_callback()
                        self.last_checkpoint = time.time()

                except queue.Empty:
                    continue

        except Exception as e:
            logger.error(f"MergeWorker error: {str(e)}")
            self.error_queue.put(
                {"worker": "MergeWorker", "error": str(e), "timestamp": datetime.now()}
            )

        finally:
            duration = time.time() - self.start_time
            logger.info(
                f"MergeWorker stopped. Papers merged: {self.papers_merged}, "
                f"Duration: {duration:.1f}s"
            )

    def _merge_enrichment(self, result: Dict[str, Any]):
        """Merge enrichment data into paper."""
        paper = result["paper"]
        enrichment = result["enrichment"]
        source = result["source"]

        paper_hash = self._get_paper_hash(paper)

        # Get or create consolidated paper
        if paper_hash in self.papers_by_hash:
            paper_id = self.papers_by_hash[paper_hash]
            consolidated = self.merged_papers[paper_id]
        else:
            # First time seeing this paper - use as base
            consolidated = paper
            self.merged_papers[paper.paper_id] = consolidated
            self.papers_by_hash[paper_hash] = paper.paper_id

        # Skip if no enrichment data (paper not found in source)
        if not enrichment:
            self.papers_merged += 1
            return

        # Apply merge rules
        timestamp = datetime.now()

        # 1. ID fields - only override if None or empty
        if enrichment.get("doi") and not consolidated.doi:
            consolidated.doi = enrichment["doi"]

        if enrichment.get("arxiv_id") and not consolidated.arxiv_id:
            consolidated.arxiv_id = enrichment["arxiv_id"]

        if enrichment.get("openalex_id") and not consolidated.openalex_id:
            consolidated.openalex_id = enrichment["openalex_id"]

        # Store S2 ID in external_ids if present
        if enrichment.get("semantic_scholar_id"):
            # Store as identifier record
            id_record = IdentifierRecord(
                source=source,
                timestamp=datetime.now(),
                original=False,
                data=IdentifierData(
                    identifier_type="s2_paper",
                    identifier_value=enrichment["semantic_scholar_id"],
                ),
            )
            consolidated.identifiers.append(id_record)

        # Store other IDs as identifiers
        for id_field in ["pmid", "pmcid", "mag_id"]:
            if enrichment.get(id_field):
                id_type = id_field.replace("_id", "")
                id_record = IdentifierRecord(
                    source=source,
                    timestamp=datetime.now(),
                    original=False,
                    data=IdentifierData(
                        identifier_type=id_type, identifier_value=enrichment[id_field]
                    ),
                )
                consolidated.identifiers.append(id_record)

        # 2. Citations - append CitationRecord
        if enrichment.get("citations") is not None:
            consolidated.citations.append(
                CitationRecord(
                    source=source,
                    timestamp=timestamp,
                    original=False,
                    data=CitationData(count=enrichment["citations"]),
                )
            )

        # 3. Abstract - append AbstractRecord
        if enrichment.get("abstract"):
            consolidated.abstracts.append(
                AbstractRecord(
                    source=source,
                    timestamp=timestamp,
                    original=False,
                    data=AbstractData(text=enrichment["abstract"]),
                )
            )

        # 4. URLs - append URLRecord
        for url in enrichment.get("urls", []):
            consolidated.urls.append(
                URLRecord(
                    source=source,
                    timestamp=timestamp,
                    original=False,
                    data=URLData(url=url),
                )
            )

        # 5. Identifiers - append IdentifierRecord
        for identifier in enrichment.get("identifiers", []):
            consolidated.identifiers.append(
                IdentifierRecord(
                    source=source,
                    timestamp=timestamp,
                    original=False,
                    data=IdentifierData(
                        identifier_type=identifier["type"],
                        identifier_value=identifier["value"],
                    ),
                )
            )

        # Send to output queue
        self.output_queue.put(consolidated)
        self.papers_merged += 1

        logger.debug(
            f"Merged enrichment from {source} for paper: {paper.title[:50]}... "
            f"(Citations: {len(consolidated.citations)}, "
            f"Abstracts: {len(consolidated.abstracts)})"
        )

    def _get_paper_hash(self, paper: Paper) -> str:
        """Generate hash for paper (same as in consolidate.py)."""
        title = paper.title.lower().strip() if paper.title else ""

        authors = []
        if hasattr(paper, "authors") and paper.authors:
            for author in paper.authors:
                if isinstance(author, dict):
                    name = author.get("name", "").lower().strip()
                else:
                    name = str(author).lower().strip()
                if name:
                    authors.append(name)
        authors.sort()
        authors_str = ";".join(authors)

        venue = paper.venue.lower().strip() if paper.venue else ""
        year = str(paper.year) if paper.year else ""

        content = f"{title}|{authors_str}|{venue}|{year}"
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()

    def get_merged_papers(self) -> List[Paper]:
        """Get all merged papers."""
        return list(self.merged_papers.values())

    def get_state(self) -> Dict[str, Any]:
        """Get current state for checkpointing."""
        return {
            "papers_merged": self.papers_merged,
            "merged_paper_count": len(self.merged_papers),
            "timestamp": datetime.now().isoformat(),
        }
