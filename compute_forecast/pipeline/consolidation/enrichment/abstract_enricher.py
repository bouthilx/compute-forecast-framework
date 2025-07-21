from typing import List, Dict
import logging

from ..sources.base import BaseConsolidationSource
from ...metadata_collection.models import Paper
from ..models import AbstractRecord

logger = logging.getLogger(__name__)


class AbstractEnricher:
    """Handles abstract enrichment from multiple sources"""

    def __init__(self, sources: List[BaseConsolidationSource]):
        self.sources = sources

    def enrich(self, papers: List[Paper]) -> Dict[str, List[AbstractRecord]]:
        """
        Enrich papers with abstracts from all sources.
        Returns mapping of paper_id -> list of abstract records
        """
        all_abstracts: Dict[str, List[AbstractRecord]] = {}

        # Skip papers that already have abstracts
        papers_needing_abstracts = [p for p in papers if not p.abstracts]

        for source in self.sources:
            logger.info(f"Fetching abstracts from {source.name}")

            try:
                results = source.enrich_papers(papers_needing_abstracts)

                for result in results:
                    if result.abstracts:
                        if result.paper_id not in all_abstracts:
                            all_abstracts[result.paper_id] = []

                        # Keep as AbstractRecord objects
                        for abstract in result.abstracts:
                            all_abstracts[result.paper_id].append(abstract)

                        # Remove from list once we have an abstract
                        papers_needing_abstracts = [
                            p
                            for p in papers_needing_abstracts
                            if p.paper_id != result.paper_id
                        ]

            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                continue

        return all_abstracts
