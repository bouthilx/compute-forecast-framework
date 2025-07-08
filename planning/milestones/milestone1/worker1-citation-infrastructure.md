# Worker 1: Citation Data Infrastructure

## Agent ID: worker1
## Work Stream: Citation Infrastructure Setup
## Duration: 2-3 hours
## Dependencies: Worker 0 (Architecture Setup) - MUST complete first

## Objective
Set up complete citation data collection infrastructure for academic and industry paper collection across all research domains.

## Deliverables
1. **API Configuration**: Functional Google Scholar, Semantic Scholar, and OpenAlex APIs
2. **Rate Limiting System**: Robust request throttling and retry logic
3. **Paper Deduplication Pipeline**: Cross-source duplicate detection and merging
4. **Collection Framework**: Reusable paper collection functions

## Detailed Tasks

### Task 1.1: Google Scholar Citation Source (45 minutes)
```python
# File: src/data/sources/google_scholar.py
from scholarly import scholarly
import time
from typing import List
from .base import BaseCitationSource
from ..models import Paper, Author, CollectionQuery, CollectionResult
from ...core.config import ConfigManager
from ...core.logging import setup_logging

class GoogleScholarSource(BaseCitationSource):
    """Google Scholar citation data source implementation"""

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('google_scholar')
        super().__init__(config.__dict__)
        self.logger = setup_logging()

    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search Google Scholar for papers matching query"""

        papers = []
        errors = []

        try:
            # Construct search query
            search_query = self._build_search_query(query)

            search_results = scholarly.search_pubs(search_query)

            for i, result in enumerate(search_results):
                if i >= query.max_results:
                    break

                try:
                    paper = self._parse_scholar_result(result, query)
                    if paper.citations >= query.min_citations:
                        papers.append(paper)

                except Exception as e:
                    errors.append(f"Failed to parse result {i}: {e}")

                # Rate limiting
                time.sleep(self.rate_limit)

        except Exception as e:
            errors.append(f"Search failed: {e}")

        return CollectionResult(
            papers=papers,
            query=query,
            source="google_scholar",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors
        )

    def _build_search_query(self, query: CollectionQuery) -> str:
        """Build Google Scholar search query string"""
        parts = []

        if query.venue:
            if query.venue in ['NeurIPS', 'ICML', 'ICLR']:
                parts.append(f'source:"{query.venue}"')
            else:
                parts.append(f'venue:"{query.venue}"')

        if query.keywords:
            keyword_str = ' OR '.join(query.keywords[:3])  # Limit keywords
            parts.append(f'({keyword_str})')

        parts.append(f'year:{query.year}')

        return ' '.join(parts)

    def _parse_scholar_result(self, result: dict, query: CollectionQuery) -> Paper:
        """Parse Google Scholar result into Paper object"""

        # Parse authors
        authors = []
        for author_data in result.get('author', []):
            author = Author(
                name=author_data.get('name', ''),
                affiliation=author_data.get('affiliation', ''),
                author_id=author_data.get('scholar_id', '')
            )
            authors.append(author)

        # Create paper object
        paper = Paper(
            title=result.get('title', ''),
            authors=authors,
            venue=query.venue or result.get('venue', ''),
            year=query.year,
            citations=result.get('num_citations', 0),
            abstract=result.get('abstract', ''),
            urls=[result.get('url', '')] if result.get('url') else [],
            source="google_scholar",
            collection_timestamp=datetime.now().isoformat(),
            mila_domain=query.domain
        )

        return paper

    def get_paper_details(self, paper_id: str) -> Paper:
        """Get detailed paper information by Google Scholar ID"""
        # Implementation for getting detailed paper info
        raise NotImplementedError("Detailed paper retrieval not yet implemented")

    def test_connectivity(self) -> bool:
        """Test Google Scholar connectivity"""
        try:
            # Simple test search
            test_results = scholarly.search_pubs('machine learning', limit=1)
            next(test_results)  # Try to get first result
            return True
        except Exception as e:
            self.logger.error(f"Google Scholar connectivity test failed: {e}")
            return False
```

**Progress Documentation**: Create `status/worker1-google-scholar.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "apis_configured": ["google_scholar", "semantic_scholar", "openalex"],
  "test_results": {
    "google_scholar": {"status": "ok", "test_query_count": 5},
    "semantic_scholar": {"status": "ok", "rate_limit": "100/minute"},
    "openalex": {"status": "ok", "last_test": "timestamp"}
  },
  "issues": []
}
```

### Task 1.2: Semantic Scholar Citation Source (45 minutes)
```python
# File: src/data/sources/semantic_scholar.py
import requests
import time
from typing import List
from .base import BaseCitationSource
from ..models import Paper, Author, CollectionQuery, CollectionResult
from ...core.config import ConfigManager
from ...core.logging import setup_logging

class SemanticScholarSource(BaseCitationSource):
    """Semantic Scholar API citation source implementation"""

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('semantic_scholar')
        super().__init__(config.__dict__)
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.logger = setup_logging()

    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search Semantic Scholar for papers matching query"""

        papers = []
        errors = []

        try:
            search_url = f"{self.base_url}/paper/search"
            params = self._build_search_params(query)

            response = requests.get(search_url, params=params, timeout=self.config.get('timeout', 30))

            if response.status_code == 200:
                data = response.json()

                for paper_data in data.get('data', []):
                    try:
                        paper = self._parse_semantic_result(paper_data, query)
                        if paper.citations >= query.min_citations:
                            papers.append(paper)
                    except Exception as e:
                        errors.append(f"Failed to parse paper: {e}")
            else:
                errors.append(f"API request failed: {response.status_code}")

        except Exception as e:
            errors.append(f"Search failed: {e}")

        return CollectionResult(
            papers=papers,
            query=query,
            source="semantic_scholar",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors
        )

    def _build_search_params(self, query: CollectionQuery) -> dict:
        """Build Semantic Scholar API parameters"""
        params = {
            'limit': min(query.max_results, 100),
            'fields': 'title,authors,venue,year,citationCount,abstract,url,paperId'
        }

        # Build query string
        query_parts = []

        if query.venue:
            query_parts.append(f'venue:"{query.venue}"')

        if query.keywords:
            keyword_str = ' '.join(query.keywords[:3])
            query_parts.append(keyword_str)

        query_parts.append(f'year:{query.year}')

        params['query'] = ' '.join(query_parts)

        return params

    def _parse_semantic_result(self, result: dict, query: CollectionQuery) -> Paper:
        """Parse Semantic Scholar result into Paper object"""

        # Parse authors
        authors = []
        for author_data in result.get('authors', []):
            author = Author(
                name=author_data.get('name', ''),
                affiliation='',  # Semantic Scholar doesn't always provide this
                author_id=author_data.get('authorId', '')
            )
            authors.append(author)

        # Create paper object
        paper = Paper(
            title=result.get('title', ''),
            authors=authors,
            venue=result.get('venue', query.venue or ''),
            year=result.get('year', query.year),
            citations=result.get('citationCount', 0),
            abstract=result.get('abstract', ''),
            urls=[result.get('url')] if result.get('url') else [],
            source="semantic_scholar",
            collection_timestamp=datetime.now().isoformat(),
            mila_domain=query.domain
        )

        return paper

    def get_paper_details(self, paper_id: str) -> Paper:
        """Get detailed paper information by Semantic Scholar ID"""
        # Implementation for getting detailed paper info
        raise NotImplementedError("Detailed paper retrieval not yet implemented")

    def test_connectivity(self) -> bool:
        """Test Semantic Scholar API connectivity"""
        try:
            test_url = f"{self.base_url}/paper/search"
            params = {'query': 'machine learning', 'limit': 1}
            response = requests.get(test_url, params=params, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Semantic Scholar connectivity test failed: {e}")
            return False
```

**Progress Documentation**: Update `status/worker1-semantic-scholar.json`

### Task 1.3: OpenAlex Citation Source (30 minutes)
```python
# File: src/data/sources/openalex.py
import requests
from typing import List
from .base import BaseCitationSource
from ..models import Paper, Author, CollectionQuery, CollectionResult
from ...core.config import ConfigManager
from ...core.logging import setup_logging

class OpenAlexSource(BaseCitationSource):
    """OpenAlex API citation source implementation"""

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('openalex')
        super().__init__(config.__dict__)
        self.base_url = "https://api.openalex.org"
        self.logger = setup_logging()

    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search OpenAlex for papers matching query"""

        papers = []
        errors = []

        try:
            search_url = f"{self.base_url}/works"
            params = self._build_search_params(query)

            response = requests.get(search_url, params=params, timeout=self.config.get('timeout', 30))

            if response.status_code == 200:
                data = response.json()

                for work in data.get('results', []):
                    try:
                        paper = self._parse_openalex_result(work, query)
                        if paper.citations >= query.min_citations:
                            papers.append(paper)
                    except Exception as e:
                        errors.append(f"Failed to parse work: {e}")
            else:
                errors.append(f"API request failed: {response.status_code}")

        except Exception as e:
            errors.append(f"Search failed: {e}")

        return CollectionResult(
            papers=papers,
            query=query,
            source="openalex",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors
        )

    def _build_search_params(self, query: CollectionQuery) -> dict:
        """Build OpenAlex API parameters"""
        filters = []

        if query.venue:
            filters.append(f'host_venue.display_name.search:{query.venue}')

        if query.year:
            filters.append(f'publication_year:{query.year}')

        if query.keywords:
            keyword_filter = ' OR '.join(query.keywords[:3])
            filters.append(f'title.search:({keyword_filter})')

        params = {
            'filter': ','.join(filters),
            'per-page': min(query.max_results, 200),
            'select': 'id,title,display_name,publication_year,cited_by_count,abstract,doi,authorships'
        }

        return params

    def _parse_openalex_result(self, work: dict, query: CollectionQuery) -> Paper:
        """Parse OpenAlex work into Paper object"""

        # Parse authors from authorships
        authors = []
        for authorship in work.get('authorships', []):
            author_info = authorship.get('author', {})
            institution_info = authorship.get('institutions', [{}])[0] if authorship.get('institutions') else {}

            author = Author(
                name=author_info.get('display_name', ''),
                affiliation=institution_info.get('display_name', ''),
                author_id=author_info.get('id', '')
            )
            authors.append(author)

        # Create paper object
        paper = Paper(
            title=work.get('display_name', ''),
            authors=authors,
            venue=query.venue or '',  # OpenAlex venue parsing is complex
            year=work.get('publication_year', query.year),
            citations=work.get('cited_by_count', 0),
            abstract=work.get('abstract', ''),
            doi=work.get('doi', ''),
            urls=[work.get('id')] if work.get('id') else [],
            source="openalex",
            collection_timestamp=datetime.now().isoformat(),
            mila_domain=query.domain
        )

        return paper

    def get_paper_details(self, work_id: str) -> Paper:
        """Get detailed work information by OpenAlex ID"""
        raise NotImplementedError("Detailed work retrieval not yet implemented")

    def test_connectivity(self) -> bool:
        """Test OpenAlex API connectivity"""
        try:
            test_url = f"{self.base_url}/works"
            params = {'filter': 'title.search:machine learning', 'per-page': 1}
            response = requests.get(test_url, params=params, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"OpenAlex connectivity test failed: {e}")
            return False
```

**Progress Documentation**: Create `status/worker1-openalex.json`

### Task 1.4: Unified Collection Manager (30 minutes)
```python
# File: src/data/collectors/citation_collector.py
from typing import List, Dict
from ..sources.google_scholar import GoogleScholarSource
from ..sources.semantic_scholar import SemanticScholarSource
from ..sources.openalex import OpenAlexSource
from ..models import Paper, CollectionQuery, CollectionResult
from ...core.logging import setup_logging
from ...core.exceptions import APIError

class CitationCollector:
    """Unified collector that manages all citation sources"""

    def __init__(self):
        self.sources = {
            'google_scholar': GoogleScholarSource(),
            'semantic_scholar': SemanticScholarSource(),
            'openalex': OpenAlexSource()
        }
        self.logger = setup_logging()

    def collect_from_all_sources(self, query: CollectionQuery) -> Dict[str, CollectionResult]:
        """Collect papers from all available citation sources"""

        results = {}

        for source_name, source in self.sources.items():
            try:
                self.logger.info(f"Collecting from {source_name} for {query.domain} {query.year}")
                result = source.search_papers(query)
                results[source_name] = result

                self.logger.info(f"Collected {result.success_count} papers from {source_name}")

            except Exception as e:
                self.logger.error(f"Failed to collect from {source_name}: {e}")
                results[source_name] = CollectionResult(
                    papers=[],
                    query=query,
                    source=source_name,
                    collection_timestamp=datetime.now().isoformat(),
                    success_count=0,
                    failed_count=1,
                    errors=[str(e)]
                )

        return results

    def test_all_sources(self) -> Dict[str, bool]:
        """Test connectivity for all citation sources"""

        connectivity = {}

        for source_name, source in self.sources.items():
            try:
                connectivity[source_name] = source.test_connectivity()
                status = "OK" if connectivity[source_name] else "FAILED"
                self.logger.info(f"{source_name} connectivity: {status}")
            except Exception as e:
                connectivity[source_name] = False
                self.logger.error(f"{source_name} connectivity test failed: {e}")

        return connectivity

    def get_combined_papers(self, results: Dict[str, CollectionResult]) -> List[Paper]:
        """Combine papers from all sources (before deduplication)"""

        all_papers = []

        for source_name, result in results.items():
            all_papers.extend(result.papers)

        return all_papers
```

**Progress Documentation**: Create `status/worker1-citation-collector.json`

## Output Files
- `src/data/sources/google_scholar.py` - Google Scholar citation source
- `src/data/sources/semantic_scholar.py` - Semantic Scholar citation source
- `src/data/sources/openalex.py` - OpenAlex citation source
- `src/data/collectors/citation_collector.py` - Unified collection manager
- `status/worker1-*.json` - Progress documentation files

## Success Criteria
- [ ] All 3 citation sources implement BaseCitationSource interface
- [ ] Each source passes connectivity tests
- [ ] CitationCollector can query all sources successfully
- [ ] Paper objects properly constructed with all metadata
- [ ] Progress documentation complete for orchestration

## Coordination Points
- **Dependencies**: Worker 0 must complete first (architecture setup)
- **Outputs needed by**: Worker 6 (Paper Collection) - ~3 hours from start
- **Status updates**: Every 30 minutes to `status/worker1-overall.json`
- **Blocking issues**: Report immediately to orchestration agent

## Risk Mitigation
- **API failures**: Multiple backup sources configured
- **Rate limiting**: Conservative limits with exponential backoff
- **Authentication**: Backup methods for Google Scholar access
- **Testing**: Extensive validation before handoff to Worker 6

## Communication Protocol
Update `status/worker1-overall.json` every 30 minutes:
```json
{
  "worker_id": "worker1",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 75,
  "current_task": "Task 1.3: Deduplication Pipeline",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "ready_for_handoff": false,
  "outputs_available": ["citation_apis.py", "rate_limiter.py"]
}
```
