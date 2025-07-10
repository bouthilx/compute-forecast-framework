from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import time
from datetime import datetime
import logging

from ..models import EnrichmentResult, CitationRecord, AbstractRecord, URLRecord, CitationData, AbstractData, URLData
from ...metadata_collection.models import Paper


@dataclass
class SourceConfig:
    """Configuration for a consolidation source"""
    api_key: Optional[str] = None
    rate_limit: float = 1.0  # requests per second
    batch_size: int = 50
    timeout: int = 30
    max_retries: int = 3


class BaseConsolidationSource(ABC):
    """Base class for all consolidation sources"""
    
    def __init__(self, name: str, config: SourceConfig):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"consolidation.{name}")
        self.api_calls = 0
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        sleep_time = (1.0 / self.config.rate_limit) - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def _create_provenance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create provenance record"""
        return {
            "source": self.name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
    @abstractmethod
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """
        Find paper IDs in this source for the given papers.
        Returns mapping of our paper_id -> source_paper_id
        """
        pass
        
    @abstractmethod
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all available fields for papers in one go.
        Returns mapping of source_id -> {
            'citations': int,
            'abstract': str,
            'urls': List[str],
            'authors': List[Dict],  # For future affiliation enrichment
            ...other fields...
        }
        """
        pass
        
    def enrich_papers(self, papers: List[Paper]) -> List[EnrichmentResult]:
        """Main enrichment workflow - single pass for all fields"""
        results = []
        
        # Process in batches
        for i in range(0, len(papers), self.config.batch_size):
            batch = papers[i:i + self.config.batch_size]
            
            # Find papers in this source ONCE
            id_mapping = self.find_papers(batch)
            source_ids = list(id_mapping.values())
            
            if not source_ids:
                continue
                
            # Fetch ALL enrichment data in one API call (or minimal calls)
            try:
                enrichment_data = self.fetch_all_fields(source_ids)
            except Exception as e:
                self.logger.error(f"Error fetching data: {e}")
                continue
            
            # Create results with provenance
            for paper in batch:
                result = EnrichmentResult(paper_id=paper.paper_id)
                
                source_id = id_mapping.get(paper.paper_id)
                if source_id and source_id in enrichment_data:
                    data = enrichment_data[source_id]
                    
                    # Add citation if found
                    if data.get('citations') is not None:
                        citation_record = CitationRecord(
                            source=self.name,
                            timestamp=datetime.now(),
                            original=False,
                            data=CitationData(count=data['citations'])
                        )
                        result.citations.append(citation_record)
                    
                    # Add abstract if found
                    if data.get('abstract'):
                        abstract_record = AbstractRecord(
                            source=self.name,
                            timestamp=datetime.now(),
                            original=False,
                            data=AbstractData(text=data['abstract'])
                        )
                        result.abstracts.append(abstract_record)
                        
                    # Add URLs if found
                    for url in data.get('urls', []):
                        url_record = URLRecord(
                            source=self.name,
                            timestamp=datetime.now(),
                            original=False,
                            data=URLData(url=url)
                        )
                        result.urls.append(url_record)
                
                results.append(result)
                
        return results