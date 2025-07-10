import requests
from typing import List, Dict, Optional

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper


class SemanticScholarSource(BaseConsolidationSource):
    """Semantic Scholar consolidation source"""
    
    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()
        super().__init__("semantic_scholar", config)
        self.base_url = "https://api.semanticscholar.org/v1"
        self.graph_url = "https://api.semanticscholar.org/graph/v1"
        
        self.headers = {}
        if self.config.api_key:
            self.headers["x-api-key"] = self.config.api_key
            
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers using multiple identifiers"""
        mapping = {}
        
        # Try to match by existing Semantic Scholar ID
        for paper in papers:
            if paper.paper_id and paper.paper_id.startswith("SS:"):
                mapping[paper.paper_id] = paper.paper_id[3:]
                continue
                
        # Batch lookup by DOI
        doi_batch = []
        doi_to_paper = {}
        for paper in papers:
            if paper.paper_id not in mapping and paper.doi:
                doi_batch.append(paper.doi)
                doi_to_paper[paper.doi] = paper.paper_id
                
        if doi_batch:
            # Use paper batch endpoint
            self._rate_limit()
            response = requests.post(
                f"{self.graph_url}/paper/batch",
                json={"ids": [f"DOI:{doi}" for doi in doi_batch]},
                headers=self.headers,
                params={"fields": "paperId"}
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for item in response.json():
                    if item and "paperId" in item:
                        doi = item.get("externalIds", {}).get("DOI")
                        if doi in doi_to_paper:
                            mapping[doi_to_paper[doi]] = item["paperId"]
                            
        # Fallback: Search by title for remaining papers
        for paper in papers:
            if paper.paper_id in mapping:
                continue
                
            self._rate_limit()
            query = f'"{paper.title}"'
            response = requests.get(
                f"{self.graph_url}/paper/search",
                params={
                    "query": query,
                    "limit": 1,
                    "fields": "paperId,title,year"
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    result = data["data"][0]
                    # Verify it's the same paper (title similarity and year)
                    if (self._similar_title(paper.title, result["title"]) and 
                        result.get("year") == paper.year):
                        mapping[paper.paper_id] = result["paperId"]
                        
        return mapping
        
    def fetch_citations(self, paper_ids: List[str]) -> Dict[str, int]:
        """Fetch citation counts in batch"""
        citations = {}
        
        # Process in chunks of 500 (API limit)
        for i in range(0, len(paper_ids), 500):
            batch = paper_ids[i:i+500]
            
            self._rate_limit()
            response = requests.post(
                f"{self.graph_url}/paper/batch",
                json={"ids": batch},
                headers=self.headers,
                params={"fields": "citationCount"}
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for item in response.json():
                    if item and "citationCount" in item:
                        citations[item["paperId"]] = item["citationCount"]
                        
        return citations
        
    def fetch_abstracts(self, paper_ids: List[str]) -> Dict[str, str]:
        """Fetch abstracts in batch"""
        abstracts = {}
        
        # Process in chunks of 500 (API limit)
        for i in range(0, len(paper_ids), 500):
            batch = paper_ids[i:i+500]
            
            self._rate_limit()
            response = requests.post(
                f"{self.graph_url}/paper/batch",
                json={"ids": batch},
                headers=self.headers,
                params={"fields": "abstract"}
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for item in response.json():
                    if item and item.get("abstract"):
                        abstracts[item["paperId"]] = item["abstract"]
                        
        return abstracts
        
    def _similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough"""
        # Simple normalization and comparison
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
            
        # Check if one is substring of other (handling subtitles)
        if norm1 in norm2 or norm2 in norm1:
            return True
            
        # Could add more sophisticated matching here
        return False