from typing import List, Dict
import logging

from ..sources.base import BaseConsolidationSource
from ...metadata_collection.models import Paper

logger = logging.getLogger(__name__)


class CitationEnricher:
    """Handles citation enrichment from multiple sources"""
    
    def __init__(self, sources: List[BaseConsolidationSource]):
        self.sources = sources
        
    def enrich(self, papers: List[Paper]) -> Dict[str, List[Dict]]:
        """
        Enrich papers with citations from all sources.
        Returns mapping of paper_id -> list of citation records
        """
        all_citations = {}
        
        for source in self.sources:
            logger.info(f"Fetching citations from {source.name}")
            
            try:
                results = source.enrich_papers(papers)
                
                for result in results:
                    if result.citations:
                        if result.paper_id not in all_citations:
                            all_citations[result.paper_id] = []
                        
                        # Keep as CitationRecord objects
                        for citation in result.citations:
                            all_citations[result.paper_id].append(citation)
                            
            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                continue
                
        return all_citations