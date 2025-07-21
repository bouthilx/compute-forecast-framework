"""Semantic Scholar worker for parallel consolidation."""

import logging
from typing import List, Dict, Any, Optional, Set, Callable, Tuple
import re

from compute_forecast.pipeline.consolidation.parallel.base_worker import (
    ConsolidationWorker,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.sources.semantic_scholar import (
    SemanticScholarSource,
)
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig

logger = logging.getLogger(__name__)


class SemanticScholarWorker(ConsolidationWorker):
    """Worker that processes papers through Semantic Scholar API."""

    def __init__(
        self,
        input_queue,
        output_queue,
        error_queue,
        ss_api_key: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        batch_size: int = 500,
        processed_hashes: Optional[Set[str]] = None,
    ):
        super().__init__(
            name="SemanticScholarWorker",
            input_queue=input_queue,
            output_queue=output_queue,
            error_queue=error_queue,
            progress_callback=progress_callback,
            batch_size=batch_size,
            processed_hashes=processed_hashes,
        )

        # Initialize Semantic Scholar source
        config = SourceConfig(api_key=ss_api_key, batch_size=batch_size)
        self.source = SemanticScholarSource(config)

    def fetch_enrichment_data(
        self, papers: List[Paper]
    ) -> List[Tuple[Paper, Dict[str, Any]]]:
        """Fetch enrichment data from Semantic Scholar."""
        results = []

        try:
            # Find papers in Semantic Scholar
            mapping = self.source.find_papers(papers)
            self.api_calls += self.source.api_calls

            # Get S2 IDs for papers found
            found_ids = []
            paper_by_s2_id = {}

            for paper in papers:
                if paper.paper_id in mapping:
                    s2_id = mapping[paper.paper_id]
                    found_ids.append(s2_id)
                    paper_by_s2_id[s2_id] = paper

            if found_ids:
                # Fetch all fields for found papers
                enrichment_data = self.source.fetch_all_fields(found_ids)
                self.api_calls += self.source.api_calls

                # Process results
                for s2_id, data in enrichment_data.items():
                    paper = paper_by_s2_id.get(s2_id)
                    if not paper:
                        continue

                    # Build enrichment dict
                    enrichment = {
                        "semantic_scholar_id": s2_id,
                        "citations": data.get("citations"),
                        "abstract": data.get("abstract"),
                        "urls": data.get("urls", []),
                        "identifiers": data.get("identifiers", []),
                    }

                    # Extract DOI
                    doi = self._extract_doi(data)
                    if doi:
                        enrichment["doi"] = doi

                    # Extract ArXiv ID
                    arxiv_id = self._extract_arxiv_id(data)
                    if arxiv_id:
                        enrichment["arxiv_id"] = arxiv_id

                    # Extract other IDs from identifiers
                    for identifier in data.get("identifiers", []):
                        if identifier["type"] == "pmid":
                            enrichment["pmid"] = identifier["value"]
                        elif identifier["type"] == "mag":
                            enrichment["mag_id"] = identifier["value"]

                    results.append((paper, enrichment))

            # Add empty results for papers not found
            for paper in papers:
                if not any(p.paper_id == paper.paper_id for p, _ in results):
                    results.append((paper, {}))

        except Exception as e:
            logger.error(f"SemanticScholarWorker enrichment error: {str(e)}")
            # Return empty results for all papers on error
            results = [(paper, {}) for paper in papers]

        return results

    def _extract_doi(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract DOI from S2 data."""
        # Check identifiers
        for identifier in data.get("identifiers", []):
            if identifier["type"] == "doi":
                return str(identifier["value"])

        # S2 sometimes has DOI in URLs
        for url in data.get("urls", []):
            if "doi.org/" in url:
                match = re.search(r"doi\.org/(.+?)(?:\s|$)", url)
                if match:
                    return match.group(1)

        return None

    def _extract_arxiv_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract ArXiv ID from S2 data."""
        # Check identifiers first
        for identifier in data.get("identifiers", []):
            if identifier["type"] == "arxiv":
                return str(identifier["value"])

        # Check URLs
        arxiv_patterns = [
            r"arxiv\.org/abs/(\d{4}\.\d{4,5})",  # New format
            r"arxiv\.org/abs/([a-z\-]+/\d{7})",  # Old format
            r"arxiv\.org/pdf/(\d{4}\.\d{4,5})",
            r"arxiv\.org/pdf/([a-z\-]+/\d{7})",
        ]

        for url in data.get("urls", []):
            for pattern in arxiv_patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return match.group(1)

        return None
