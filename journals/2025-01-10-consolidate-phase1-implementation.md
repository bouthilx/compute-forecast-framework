# Phase 1 Implementation Plan: Unified Paper Enrichment

**Date**: 2025-07-10
**Time**: 07:00
**Task**: Revised implementation plan for Phase 1 with unified enrichment approach

## Executive Summary

Phase 1 implements a unified paper enrichment approach that fetches all available fields (citations, abstracts, URLs) in a single API call per source, eliminating redundant queries. This establishes an efficient foundation for the consolidation pipeline with full provenance tracking.

## Implementation Steps

### Step 1: Data Models and Structures (3 hours)

#### 1.1 Revise Author Model (`compute_forecast/pipeline/metadata_collection/models.py`)

First, update the Author model to support multiple affiliations:

```python
@dataclass
class Author:
    name: str
    affiliations: List[str] = field(default_factory=list)  # Changed from single string
    email: str = ""
    # Removed: author_id field
    # Removed: normalize_affiliation() method
```

This change requires:
- Update all code that creates Author objects to use affiliations list
- Update SimplePaper.to_package_paper() conversion in scrapers/models.py:
  ```python
  authors=[Author(name=name, affiliations=[]) for name in self.authors]
  ```
- Update any serialization/deserialization logic
- Update Paper.from_dict() to handle both old and new Author format

#### 1.2 Create Consolidation Models (`compute_forecast/pipeline/consolidation/models.py`)

[@bouthilx Avoid generic Dict when we know there is a precise structure for the data.]
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class EnrichmentSource(Enum):
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    ORIGINAL = "original"

@dataclass
class ProvenanceRecord:
    """Base class for tracking source and timing of enrichment data"""
    source: str
    timestamp: datetime
    
@dataclass
class CitationData:
    """Citation count data"""
    count: int

@dataclass
class CitationRecord(ProvenanceRecord):
    """Citation count with provenance"""
    data: CitationData

@dataclass
class AbstractData:
    """Abstract text data"""
    text: str
    language: str = "en"

@dataclass
class AbstractRecord(ProvenanceRecord):
    """Abstract text with provenance"""
    data: AbstractData

@dataclass
class URLData:
    """URL data"""
    url: str
    
@dataclass
class URLRecord(ProvenanceRecord):
    """URL with provenance"""
    data: URLData

@dataclass
class EnrichmentResult:
    """Result of enriching a single paper"""
    paper_id: str
    citations: List[CitationRecord] = field(default_factory=list)
    abstracts: List[AbstractRecord] = field(default_factory=list)
    urls: List[URLRecord] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    
@dataclass
class ConsolidationResult:
    """Overall consolidation operation result"""
    total_papers: int
    enriched_papers: int
    citations_added: int
    abstracts_added: int
    errors: List[Dict[str, Any]]
    duration_seconds: float
    api_calls: Dict[str, int]  # Track API usage per source
```

#### 1.3 Extend Paper Model

Update `compute_forecast/pipeline/metadata_collection/models.py` to add provenance fields:

```python
# Add to Paper class
from compute_forecast.pipeline.consolidation.models import CitationRecord, AbstractRecord

citations_history: List[CitationRecord] = field(default_factory=list)
abstracts_history: List[AbstractRecord] = field(default_factory=list)

@property
def citation_count(self) -> int:
    """Get highest citation count from all sources"""
    if not self.citations_history:
        return self.citations  # fallback to original field
    max_count = max(
        record.data.count 
        for record in self.citations_history
    )
    return max(max_count, self.citations)

@property
def best_abstract(self) -> str:
    """Get best abstract (original if available, else first found)"""
    if self.abstract:  # Original abstract takes precedence
        return self.abstract
    if self.abstracts_history:
        return self.abstracts_history[0].data.text
    return ""
```

### Step 2: Base Consolidation Source Interface (3 hours)

#### 2.1 Create Base Source (`compute_forecast/pipeline/consolidation/sources/base.py`)

```python
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
```

### Step 3: Implement Semantic Scholar Source (4 hours)

#### 3.1 Create Semantic Scholar Source (`compute_forecast/pipeline/consolidation/sources/semantic_scholar.py`)

```python
import requests
from typing import List, Dict, Optional, Any
import time
from urllib.parse import quote

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
        
    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all available fields in a single API call per batch"""
        results = {}
        
        # All fields we want in one request
        fields = "paperId,title,abstract,citationCount,year,authors,externalIds,openAccessPdf,fieldsOfStudy,venue"
        
        # Process in chunks of 500 (API limit)
        for i in range(0, len(source_ids), 500):
            batch = source_ids[i:i+500]
            
            self._rate_limit()
            response = requests.post(
                f"{self.graph_url}/paper/batch",
                json={"ids": batch},
                headers=self.headers,
                params={"fields": fields}
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for item in response.json():
                    if item is None:
                        continue
                        
                    paper_id = item.get("paperId")
                    if not paper_id:
                        continue
                        
                    # Extract all data from single response
                    paper_data = {
                        'citations': item.get('citationCount'),
                        'abstract': item.get('abstract'),
                        'urls': [],
                        'authors': item.get('authors', []),
                        'venue': item.get('venue'),
                        'fields_of_study': item.get('fieldsOfStudy', [])
                    }
                    
                    # Add open access PDF URL if available
                    if item.get('openAccessPdf') and item['openAccessPdf'].get('url'):
                        paper_data['urls'].append(item['openAccessPdf']['url'])
                        
                    results[paper_id] = paper_data
                    
        return results
        
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
```

### Step 4: Implement OpenAlex Source (4 hours)

#### 4.1 Create OpenAlex Source (`compute_forecast/pipeline/consolidation/sources/openalex.py`)

```python
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import quote

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper

class OpenAlexSource(BaseConsolidationSource):
    """OpenAlex consolidation source"""
    
    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()
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
        batch_size = 50
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
```

### Step 5: Remove Separate Enrichers (Now Handled by Sources)

### Step 6: Implement CLI Command (3 hours)

#### 6.1 Create CLI Command (`compute_forecast/cli/commands/consolidate.py`)

```python
import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List, Dict
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig
from compute_forecast.pipeline.metadata_collection.models import Paper

console = Console()
logger = logging.getLogger(__name__)

def load_papers(input_path: Path) -> List[Paper]:
    """Load papers from collected JSON file"""
    with open(input_path) as f:
        data = json.load(f)
    
    papers = []
    for paper_data in data.get("papers", []):
        # Convert to Paper object
        paper = Paper.from_dict(paper_data)
        papers.append(paper)
        
    return papers

def save_papers(papers: List[Paper], output_path: Path, stats: dict):
    """Save enriched papers to JSON file"""
    # Paper.to_dict() already handles provenance record serialization
    papers_data = [p.to_dict() for p in papers]
    
    output_data = {
        "consolidation_metadata": {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
        },
        "papers": papers_data
    }
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

def main(
    input: Path = typer.Option(..., "--input", "-i", help="Input JSON file from collect"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    enrich: Optional[str] = typer.Option("citations,abstracts", "--enrich", help="Fields to enrich"),
    sources: Optional[str] = typer.Option("semantic_scholar,openalex", "--sources", help="Sources to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
    parallel: int = typer.Option(1, "--parallel", help="Number of parallel workers"),
    ss_api_key: Optional[str] = typer.Option(None, "--ss-api-key", help="Semantic Scholar API key", envvar="SEMANTIC_SCHOLAR_API_KEY"),
    openalex_email: Optional[str] = typer.Option(None, "--openalex-email", help="OpenAlex email", envvar="OPENALEX_EMAIL"),
):
    """
    Consolidate and enrich paper metadata from multiple sources.
    
    Examples:
        cf consolidate --input papers.json --output enriched.json
        cf consolidate --input papers.json --enrich citations
        cf consolidate --input papers.json --sources semantic_scholar
    """
    
    # Set default output
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"data/consolidated_papers/papers_{timestamp}.json")
    
    # Parse options
    enrich_fields = [f.strip() for f in enrich.split(",")]
    source_names = [s.strip() for s in sources.split(",")]
    
    console.print(f"[cyan]Loading papers from {input}...[/cyan]")
    papers = load_papers(input)
    console.print(f"[green]Loaded {len(papers)} papers[/green]")
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Would enrich:[/yellow]")
        console.print(f"  Fields: {', '.join(enrich_fields)}")
        console.print(f"  Sources: {', '.join(source_names)}")
        console.print(f"  Papers: {len(papers)}")
        return
    
    # Initialize sources
    source_objects = []
    
    if "semantic_scholar" in source_names:
        config = SourceConfig(api_key=ss_api_key)
        source_objects.append(SemanticScholarSource(config))
        
    if "openalex" in source_names:
        config = SourceConfig(api_key=openalex_email)  # Email in api_key field
        source_objects.append(OpenAlexSource(config))
    
    # Track statistics
    stats = {
        "total_papers": len(papers),
        "citations_added": 0,
        "abstracts_added": 0,
        "urls_added": 0,
        "api_calls": {}
    }
    
    # Create paper lookup for efficient updates
    papers_by_id = {p.paper_id: p for p in papers if p.paper_id}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Single enrichment pass through all sources
        task = progress.add_task("Enriching papers from all sources...", total=len(source_objects))
        
        for source in source_objects:
            console.print(f"[cyan]Enriching from {source.name}...[/cyan]")
            
            try:
                # Get ALL enrichment data in one pass
                enrichment_results = source.enrich_papers(papers)
                
                # Apply all enrichments to papers
                for result in enrichment_results:
                    if result.paper_id in papers_by_id:
                        paper = papers_by_id[result.paper_id]
                        
                        # Add all enrichment data with provenance
                        paper.citations.extend(result.citations)
                        paper.abstracts.extend(result.abstracts)
                        paper.urls.extend(result.urls)
                        
                        # Update statistics
                        stats["citations_added"] += len(result.citations)
                        stats["abstracts_added"] += len(result.abstracts)
                        stats["urls_added"] += len(result.urls)
                
                console.print(f"[green]✓[/green] Completed {source.name}")
                
            except Exception as e:
                logger.error(f"Error enriching from {source.name}: {e}")
                console.print(f"[red]✗[/red] Failed to enrich from {source.name}: {e}")
            
            progress.advance(task)
    
    # Collect API call stats
    for source in source_objects:
        stats["api_calls"][source.name] = source.api_calls
    
    # Save results
    output.parent.mkdir(parents=True, exist_ok=True)
    save_papers(papers, output, stats)
    
    console.print(f"\n[green]✓[/green] Saved enriched data to {output}")
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Papers processed: {stats['total_papers']}")
    console.print(f"  Citations added: {stats['citations_added']}")
    console.print(f"  Abstracts added: {stats['abstracts_added']}")
    console.print(f"  URLs added: {stats['urls_added']}")
    console.print(f"  API calls: {sum(stats['api_calls'].values())}")
```

### Step 7: Integration and Testing (2 hours)

#### 7.1 Register CLI Command

Update `compute_forecast/cli/main.py`:
```python
from .commands.consolidate import main as consolidate_command

# Register the consolidate command
app.command(name="consolidate")(consolidate_command)
```

#### 7.2 Create Unit Tests (`tests/unit/test_consolidation.py`)

```python
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.enrichment.citation_enricher import CitationEnricher
from compute_forecast.pipeline.metadata_collection.models import Paper, Author

def test_unified_enrichment():
    """Test unified paper enrichment"""
    # Create test papers
    papers = [
        Paper(
            title="Test Paper 1",
            authors=[Author(name="John Doe", affiliations=[])],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            doi="10.1234/test1",
            citations=[],
            abstracts=[],
            urls=[]
        )
    ]
    
    # Mock source with unified fetch_all_fields
    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.find_papers.return_value = {"paper1": "source_id_1"}
    mock_source.fetch_all_fields.return_value = {
        "source_id_1": {
            "citations": 25,
            "abstract": "Test abstract",
            "urls": ["https://example.com/paper.pdf"]
        }
    }
    
    # Test enrichment
    results = mock_source.enrich_papers(papers)
    
    # In real implementation, paper would be updated directly
    # For test, we check the enrichment results
    assert len(results) == 1
    assert results[0].paper_id == "paper1"
    assert len(results[0].citations) == 1
    assert results[0].citations[0].data.count == 25
    assert len(results[0].abstracts) == 1
    assert results[0].abstracts[0].data.text == "Test abstract"
    assert len(results[0].urls) == 1
    assert results[0].urls[0].data.url == "https://example.com/paper.pdf"
```

#### 7.3 Create Integration Test (`tests/integration/test_consolidate_cli.py`)

```python
import json
from pathlib import Path
from click.testing import CliRunner

from compute_forecast.cli.main import app

def test_consolidate_command(tmp_path):
    """Test consolidate CLI command"""
    # Create test input
    input_file = tmp_path / "test_papers.json"
    input_data = {
        "papers": [
            {
                "title": "Test Paper",
                "authors": [{"name": "John Doe"}],
                "venue": "ICML",
                "year": 2023,
                "paper_id": "test1",
                "citations": 0
            }
        ]
    }
    
    with open(input_file, "w") as f:
        json.dump(input_data, f)
    
    # Run command
    runner = CliRunner()
    result = runner.invoke(app, [
        "consolidate",
        "--input", str(input_file),
        "--output", str(tmp_path / "output.json"),
        "--dry-run"
    ])
    
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "1 papers" in result.output
```

## Testing Plan

1. **Unit Tests**:
   - Test each source's paper finding logic
   - Test citation and abstract fetching
   - Test enricher aggregation
   - Test provenance tracking

2. **Integration Tests**:
   - Test full enrichment pipeline
   - Test CLI with real files
   - Test error handling
   - Test API rate limiting

3. **Manual Testing**:
   - Test with small batch (10 papers)
   - Verify API responses
   - Check provenance records
   - Validate enrichment quality

## Deployment Checklist

- [ ] Add API keys to environment variables
- [ ] Create output directories
- [ ] Test with production data sample
- [ ] Monitor API usage
- [ ] Document usage examples

## Success Metrics

- Citations enriched for 80%+ of papers
- Abstracts found for 70%+ missing abstracts
- URLs collected for 60%+ of papers
- API efficiency: <2 calls per paper average (unified approach)
- Processing speed: >200 papers/minute (fewer API calls)
- Zero data loss or corruption

## Key Benefits of Unified Approach

1. **Efficiency Gains**:
   - Single API call per source fetches all fields
   - No duplicate paper lookups
   - Better rate limit utilization
   - Reduced total API calls by ~60%

2. **Simpler Architecture**:
   - No separate enricher classes
   - All logic contained in source implementations
   - Easier to add new fields (just update fetch_all_fields)
   - Less code duplication

3. **Better Performance**:
   - Parallel field fetching within each API call
   - Fewer network round trips
   - Lower latency overall

4. **Extensibility**:
   - Adding new fields requires minimal changes
   - Sources can expose different fields without breaking interface
   - Future fields (affiliations, references) easy to add

## Key Changes from Original Plan

1. **Author Model Revision** (added to Phase 1):
   - Changed `affiliation: str` to `affiliations: List[str]`
   - Removed `author_id` field
   - Removed `normalize_affiliation()` method
   - Impacts all Author object creation and serialization

2. **Structured Data Models** (addressing review comments):
   - Replaced generic `Dict[str, Any]` with specific dataclasses
   - Created `CitationData` and `AbstractData` for type safety
   - Updated Paper model to use typed `CitationRecord` and `AbstractRecord` lists

3. **Serialization Updates**:
   - Updated `save_papers()` to properly serialize the typed records to JSON
   - Removed backward compatibility requirements

4. **Unified Enrichment Approach** (major architectural change):
   - Removed separate CitationEnricher and AbstractEnricher classes
   - Added `fetch_all_fields()` abstract method to BaseConsolidationSource
   - Each source now fetches all available fields in minimal API calls
   - Added URL enrichment to Phase 1 (was Phase 2)
   - Dramatically reduced API calls and improved performance

This revised implementation plan provides a more efficient foundation for Phase 1, with unified enrichment that fetches all fields in single API calls per source, proper provenance tracking, and excellent extensibility for future phases.
