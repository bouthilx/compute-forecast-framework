import requests
from typing import List, Dict, Optional, Any

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper


class OpenAlexSource(BaseConsolidationSource):
    """OpenAlex consolidation source"""
    
    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()
        # Set optimal batch sizes for OpenAlex (limited by URL length)
        if config.find_batch_size is None:
            config.find_batch_size = 50  # URL length limit
        if config.enrich_batch_size is None:
            config.enrich_batch_size = 50  # URL length limit
        super().__init__("openalex", config)
        self.base_url = "https://api.openalex.org"
        
        # Email for polite access
        email = config.api_key  # Using api_key field for email
        self.headers = {"User-Agent": "ConsolidationBot/1.0"}
        if email:
            self.headers["User-Agent"] += f" (mailto:{email})"
            
    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers using OpenAlex search"""
        mapping = {}
        
        # Check for existing OpenAlex IDs
        for paper in papers:
            if paper.openalex_id:
                mapping[paper.paper_id] = paper.openalex_id
                continue
                
        # Batch search by DOI
        doi_filter_parts = []
        doi_to_paper = {}
        
        for paper in papers:
            if paper.paper_id not in mapping and paper.doi:
                doi_filter_parts.append(f'doi:"{paper.doi}"')
                doi_to_paper[paper.doi] = paper.paper_id
                
        if doi_filter_parts:
            # OpenAlex OR filter syntax
            filter_str = "|".join(doi_filter_parts)
            
            self._rate_limit()
            response = requests.get(
                f"{self.base_url}/works",
                params={
                    "filter": filter_str,
                    "per-page": len(doi_filter_parts),
                    "select": "id,doi"
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for work in response.json().get("results", []):
                    doi = work.get("doi", "").replace("https://doi.org/", "")
                    if doi in doi_to_paper:
                        mapping[doi_to_paper[doi]] = work["id"]
                        
        # Search by title for remaining papers
        for paper in papers:
            if paper.paper_id in mapping:
                continue
                
            self._rate_limit()
            response = requests.get(
                f"{self.base_url}/works",
                params={
                    "search": paper.title,
                    "filter": f"publication_year:{paper.year}",
                    "per-page": 1,
                    "select": "id,title,publication_year"
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    work = results[0]
                    # Verify match
                    if self._similar_title(paper.title, work.get("title", "")):
                        mapping[paper.paper_id] = work["id"]
                        
        return mapping
        
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all available fields in minimal API calls"""
        results = {}
        
        # Build OR filter for all IDs
        id_filters = [f'openalex:"{id}"' for id in source_ids]
        
        # Select all fields we need in one request
        select_fields = "id,title,abstract_inverted_index,cited_by_count,publication_year,authorships,primary_location,locations,concepts"
        
        # Process in batches (OpenAlex has URL length limits)
        batch_size = self.config.enrich_batch_size or 50
        for i in range(0, len(id_filters), batch_size):
            batch = id_filters[i:i+batch_size]
            filter_str = "|".join(batch)
            
            self._rate_limit()
            response = requests.get(
                f"{self.base_url}/works",
                params={
                    "filter": filter_str,
                    "per-page": len(batch),
                    "select": select_fields
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for work in response.json().get("results", []):
                    work_id = work.get("id")
                    if not work_id:
                        continue
                        
                    # Extract all data from single response
                    paper_data = {
                        'citations': work.get("cited_by_count", 0),
                        'abstract': None,
                        'urls': [],
                        'authors': [],
                        'concepts': work.get('concepts', [])
                    }
                    
                    # Convert inverted index to text
                    inverted = work.get("abstract_inverted_index", {})
                    if inverted:
                        paper_data['abstract'] = self._inverted_to_text(inverted)
                        
                    # Extract author information
                    for authorship in work.get('authorships', []):
                        author_info = {
                            'name': authorship.get('author', {}).get('display_name'),
                            'institutions': [inst.get('display_name') for inst in authorship.get('institutions', [])]
                        }
                        paper_data['authors'].append(author_info)
                        
                    # Extract URLs from locations
                    if work.get('primary_location') and work['primary_location'].get('pdf_url'):
                        paper_data['urls'].append(work['primary_location']['pdf_url'])
                        
                    # Check other locations for open access URLs
                    for location in work.get('locations', []):
                        if location.get('pdf_url') and location['pdf_url'] not in paper_data['urls']:
                            paper_data['urls'].append(location['pdf_url'])
                            
                    results[work_id] = paper_data
                    
        return results
        
    def _inverted_to_text(self, inverted_index: Dict[str, List[int]]) -> str:
        """Convert OpenAlex inverted index to text"""
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        return " ".join(word for _, word in words)
        
    def _similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar"""
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()
        return norm1 == norm2 or norm1 in norm2 or norm2 in norm1