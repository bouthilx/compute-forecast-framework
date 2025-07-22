"""OpenAlex worker for parallel consolidation."""

import logging
from typing import List, Dict, Any, Optional, Set, Callable, Tuple
import re

from compute_forecast.pipeline.consolidation.parallel.base_worker import (
    ConsolidationWorker,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig

logger = logging.getLogger(__name__)


class OpenAlexWorker(ConsolidationWorker):
    """Worker that processes papers through OpenAlex API."""

    def __init__(
        self,
        input_queue,
        output_queue,
        error_queue,
        openalex_email: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        batch_size: int = 50,
        processed_hashes: Optional[Set[str]] = None,
    ):
        super().__init__(
            name="OpenAlexWorker",
            input_queue=input_queue,
            output_queue=output_queue,
            error_queue=error_queue,
            progress_callback=progress_callback,
            batch_size=batch_size,
            processed_hashes=processed_hashes,
        )

        # Initialize OpenAlex source
        config = SourceConfig(
            api_key=openalex_email,  # Email for polite access
            batch_size=batch_size,
        )
        self.source = OpenAlexSource(config)

    def fetch_enrichment_data(
        self, papers: List[Paper]
    ) -> List[Tuple[Paper, Dict[str, Any]]]:
        """Fetch enrichment data from OpenAlex."""
        results = []

        try:
            # Find papers in OpenAlex
            mapping = self.source.find_papers(papers)
            self.api_calls += self.source.api_calls

            # Get OpenAlex IDs for papers found
            found_ids = []
            paper_by_oa_id = {}

            for paper in papers:
                if paper.paper_id in mapping:
                    oa_id = mapping[paper.paper_id]
                    found_ids.append(oa_id)
                    paper_by_oa_id[oa_id] = paper

            if found_ids:
                # Fetch all fields for found papers
                enrichment_data = self.source.fetch_all_fields(found_ids)
                self.api_calls += self.source.api_calls

                # Process results
                for oa_id, data in enrichment_data.items():
                    matched_paper = paper_by_oa_id.get(oa_id)
                    if not matched_paper:
                        continue

                    # Extract IDs from the enrichment response
                    enrichment = {
                        "openalex_id": oa_id,
                        "citations": data.get("citations"),
                        "abstract": data.get("abstract"),
                        "urls": data.get("urls", []),
                        "identifiers": data.get("identifiers", []),
                    }

                    # Extract DOI
                    for identifier in data.get("identifiers", []):
                        if identifier["type"] == "doi":
                            enrichment["doi"] = identifier["value"]
                            break

                    # Extract ArXiv ID from identifiers or URLs
                    arxiv_id = self._extract_arxiv_id(data)
                    if arxiv_id:
                        enrichment["arxiv_id"] = arxiv_id

                    results.append((matched_paper, enrichment))

            # Add empty results for papers not found
            for paper in papers:
                if not any(p.paper_id == paper.paper_id for p, _ in results):
                    results.append((paper, {}))

        except Exception as e:
            logger.error(f"OpenAlexWorker enrichment error: {str(e)}")
            # Return empty results for all papers on error
            results = [(paper, {}) for paper in papers]

        return results

    def _extract_arxiv_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract ArXiv ID from various locations in OpenAlex data."""
        # Check identifiers first
        for identifier in data.get("identifiers", []):
            if identifier["type"] == "arxiv":
                return str(identifier["value"])

        # Check URLs for ArXiv links
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
