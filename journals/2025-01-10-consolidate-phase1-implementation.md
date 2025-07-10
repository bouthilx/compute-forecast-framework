# Phase 1 Implementation Plan: Citation and Abstract Enrichment

**Date**: 2025-07-10
**Time**: 05:00
**Task**: Detailed implementation plan for Phase 1 of the consolidate command

## Executive Summary

Phase 1 focuses on implementing the core enrichment functionality for citations and abstracts with full provenance tracking. This phase establishes the foundation for the consolidation pipeline, including the base source interface, data models, and the minimal CLI command to test the functionality.

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
class EnrichmentResult:
    """Result of enriching a single paper"""
    paper_id: str
    citations: List[CitationRecord] = field(default_factory=list)
    abstracts: List[AbstractRecord] = field(default_factory=list)
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
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
from datetime import datetime
import logging

from ..models import EnrichmentResult, CitationRecord, AbstractRecord
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
    def fetch_citations(self, paper_ids: List[str]) -> Dict[str, int]:
        """
        Fetch citation counts for papers.
        Returns mapping of paper_id -> citation_count
        """
        pass
        
    @abstractmethod
    def fetch_abstracts(self, paper_ids: List[str]) -> Dict[str, str]:
        """
        Fetch abstracts for papers.
        Returns mapping of paper_id -> abstract_text
        """
        pass
        
    def enrich_papers(self, papers: List[Paper]) -> List[EnrichmentResult]:
        """Main enrichment workflow"""
        results = []
        
        # Process in batches
        for i in range(0, len(papers), self.config.batch_size):
            batch = papers[i:i + self.config.batch_size]
            
            # Find papers in this source
            id_mapping = self.find_papers(batch)
            source_ids = list(id_mapping.values())
            
            if not source_ids:
                continue
                
            # Fetch enrichment data
            citations = self.fetch_citations(source_ids)
            abstracts = self.fetch_abstracts(source_ids)
            
            # Create results with provenance
            for paper in batch:
                result = EnrichmentResult(paper_id=paper.paper_id)
                
                source_id = id_mapping.get(paper.paper_id)
                if source_id:
                    # Add citation if found
                    if source_id in citations:
                        citation_record = CitationRecord(
                            source=self.name,
                            timestamp=datetime.now(),
                            data=CitationData(count=citations[source_id])
                        )
                        result.citations.append(citation_record)
                    
                    # Add abstract if found
                    if source_id in abstracts:
                        abstract_record = AbstractRecord(
                            source=self.name,
                            timestamp=datetime.now(),
                            data=AbstractData(text=abstracts[source_id])
                        )
                        result.abstracts.append(abstract_record)
                
                results.append(result)
                
        return results
```

### Step 3: Implement Semantic Scholar Source (4 hours)

#### 3.1 Create Semantic Scholar Source (`compute_forecast/pipeline/consolidation/sources/semantic_scholar.py`)

```python
import requests
from typing import List, Dict, Optional
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
```

### Step 4: Implement OpenAlex Source (4 hours)

#### 4.1 Create OpenAlex Source (`compute_forecast/pipeline/consolidation/sources/openalex.py`)

```python
import requests
from typing import List, Dict, Optional
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
        
    def fetch_citations(self, paper_ids: List[str]) -> Dict[str, int]:
        """Fetch citation counts"""
        citations = {}
        
        # Build OR filter for all IDs
        id_filters = [f'openalex:"{id}"' for id in paper_ids]
        
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
                    "select": "id,cited_by_count"
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for work in response.json().get("results", []):
                    citations[work["id"]] = work.get("cited_by_count", 0)
                    
        return citations
        
    def fetch_abstracts(self, paper_ids: List[str]) -> Dict[str, str]:
        """Fetch abstracts"""
        abstracts = {}
        
        # Build OR filter for all IDs
        id_filters = [f'openalex:"{id}"' for id in paper_ids]
        
        # Process in batches
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
                    "select": "id,abstract_inverted_index"
                },
                headers=self.headers
            )
            self.api_calls += 1
            
            if response.status_code == 200:
                for work in response.json().get("results", []):
                    # Convert inverted index to text
                    inverted = work.get("abstract_inverted_index", {})
                    if inverted:
                        abstract_text = self._inverted_to_text(inverted)
                        abstracts[work["id"]] = abstract_text
                        
        return abstracts
        
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

### Step 5: Create Enrichment Orchestrator (3 hours)

#### 5.1 Create Citation Enricher (`compute_forecast/pipeline/consolidation/enrichment/citation_enricher.py`)

```python
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
```

#### 5.2 Create Abstract Enricher (`compute_forecast/pipeline/consolidation/enrichment/abstract_enricher.py`)

```python
from typing import List, Dict
import logging

from ..sources.base import BaseConsolidationSource
from ...metadata_collection.models import Paper

logger = logging.getLogger(__name__)

class AbstractEnricher:
    """Handles abstract enrichment from multiple sources"""
    
    def __init__(self, sources: List[BaseConsolidationSource]):
        self.sources = sources
        
    def enrich(self, papers: List[Paper]) -> Dict[str, List[Dict]]:
        """
        Enrich papers with abstracts from all sources.
        Returns mapping of paper_id -> list of abstract records
        """
        all_abstracts = {}
        
        # Skip papers that already have abstracts
        papers_needing_abstracts = [p for p in papers if not p.abstract]
        
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
                            p for p in papers_needing_abstracts 
                            if p.paper_id != result.paper_id
                        ]
                        
            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                continue
                
        return all_abstracts
```

### Step 6: Implement CLI Command (3 hours)

#### 6.1 Create CLI Command (`compute_forecast/cli/commands/consolidate.py`)

```python
import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig
from compute_forecast.pipeline.consolidation.enrichment.citation_enricher import CitationEnricher
from compute_forecast.pipeline.consolidation.enrichment.abstract_enricher import AbstractEnricher
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
    # Convert papers to dict format with proper serialization
    papers_data = []
    for p in papers:
        paper_dict = p.to_dict()
        
        # Convert CitationRecord objects to dicts
        if hasattr(p, 'citations_history') and p.citations_history:
            paper_dict['citations_history'] = [
                {
                    "source": record.source,
                    "timestamp": record.timestamp.isoformat(),
                    "data": {"count": record.data.count}
                }
                for record in p.citations_history
            ]
            
        # Convert AbstractRecord objects to dicts
        if hasattr(p, 'abstracts_history') and p.abstracts_history:
            paper_dict['abstracts_history'] = [
                {
                    "source": record.source,
                    "timestamp": record.timestamp.isoformat(),
                    "data": {
                        "text": record.data.text,
                        "language": record.data.language
                    }
                }
                for record in p.abstracts_history
            ]
            
        papers_data.append(paper_dict)
    
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
        "api_calls": {}
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Enrich citations
        if "citations" in enrich_fields:
            task = progress.add_task("Enriching citations...", total=None)
            
            enricher = CitationEnricher(source_objects)
            citation_records = enricher.enrich(papers)
            
            # Update papers
            for paper in papers:
                if paper.paper_id in citation_records:
                    paper.citations_history.extend(citation_records[paper.paper_id])
                    stats["citations_added"] += len(citation_records[paper.paper_id])
                    
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Added {stats['citations_added']} citation records")
        
        # Enrich abstracts
        if "abstracts" in enrich_fields:
            task = progress.add_task("Enriching abstracts...", total=None)
            
            enricher = AbstractEnricher(source_objects)
            abstract_records = enricher.enrich(papers)
            
            # Update papers
            for paper in papers:
                if paper.paper_id in abstract_records:
                    paper.abstracts_history.extend(abstract_records[paper.paper_id])
                    stats["abstracts_added"] += len(abstract_records[paper.paper_id])
                    
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Added {stats['abstracts_added']} abstract records")
    
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

def test_citation_enricher():
    """Test citation enrichment"""
    # Create test papers
    papers = [
        Paper(
            title="Test Paper 1",
            authors=[Author(name="John Doe")],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            doi="10.1234/test1",
            citations=10
        )
    ]
    
    # Mock source
    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.enrich_papers.return_value = [
        Mock(
            paper_id="paper1",
            citations=[Mock(
                source="test_source",
                timestamp=datetime.now(),
                data={"count": 25}
            )]
        )
    ]
    
    # Test enrichment
    enricher = CitationEnricher([mock_source])
    results = enricher.enrich(papers)
    
    assert "paper1" in results
    assert len(results["paper1"]) == 1
    assert results["paper1"][0].data.count == 25
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
- API efficiency: <5 calls per paper average
- Processing speed: >100 papers/minute
- Zero data loss or corruption

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
   - Maintained backward compatibility in JSON format

This implementation plan provides a solid foundation for Phase 1, establishing the core enrichment functionality with proper provenance tracking, type safety, and extensibility for future phases.
