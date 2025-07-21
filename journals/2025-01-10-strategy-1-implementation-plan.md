# 2025-01-10 Detailed Implementation Plan for Strategy 1: Parallel First-Pass ID Harvesting

## Overview

Strategy 1 optimizes consolidation by separating ID discovery from enrichment, allowing us to leverage each source's strengths optimally. The key insight is that OpenAlex has 100% title search success but Semantic Scholar has better ArXiv-specific data.

## Current Architecture Analysis

The existing consolidation system:
- Processes sources sequentially (one source completes before next starts)
- Each source does both ID lookup and enrichment in one pass
- Uses `find_papers()` then `fetch_all_fields()` pattern
- Supports progress callbacks but not parallel execution
- Already has batch processing infrastructure

## Implementation Plan

### Phase 1: ID Harvesting Component

#### 1.1 Create ID Harvester Class

```python
# compute_forecast/pipeline/consolidation/id_harvester.py

@dataclass
class PaperIdentifiers:
    """Complete identifier set for a paper"""
    paper_id: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    crossref_id: Optional[str] = None  # Same as DOI usually

class IDHarvester:
    """Fast first-pass identifier collection using OpenAlex"""

    def __init__(self, openalex_source: OpenAlexSource):
        self.source = openalex_source
        self.logger = logging.getLogger("consolidation.id_harvester")

    def harvest_identifiers(self, papers: List[Paper],
                          progress_callback=None) -> Dict[str, PaperIdentifiers]:
        """
        Collect all available identifiers in a single fast pass.
        Uses OpenAlex's 100% title search success rate.
        Returns: {paper_id: PaperIdentifiers}
        """
        identifiers = {}

        # Process in batches of 50 (OpenAlex optimal)
        for batch_start in range(0, len(papers), 50):
            batch = papers[batch_start:batch_start + 50]

            # Use OpenAlex's find_papers which returns their IDs
            id_mapping = self.source.find_papers(batch)

            # Fetch minimal data to extract other identifiers
            if id_mapping:
                oa_ids = list(id_mapping.values())
                # Custom method to get just identifiers, not full enrichment
                id_data = self._fetch_identifiers_only(oa_ids)

                # Build complete identifier records
                for our_id, oa_id in id_mapping.items():
                    if oa_id in id_data:
                        data = id_data[oa_id]
                        identifiers[our_id] = PaperIdentifiers(
                            paper_id=our_id,
                            openalex_id=oa_id,
                            doi=data.get('doi'),
                            arxiv_id=self._extract_arxiv_id(data),
                            # S2 ID if available in external IDs
                            semantic_scholar_id=data.get('ids', {}).get('s2')
                        )

            if progress_callback:
                progress_callback(len(batch))

        return identifiers
```

#### 1.2 Optimize OpenAlex for ID-Only Fetching

```python
# Add to OpenAlexSource

def fetch_identifiers_only(self, openalex_ids: List[str]) -> Dict[str, Dict]:
    """Lightweight fetch for identifiers only"""
    # Use select parameter to get only what we need
    params = {
        'filter': f'openalex:{"openalex:".join(openalex_ids)}',
        'select': 'id,doi,ids,locations',  # Minimal fields
        'per_page': 50
    }

    results = {}
    response = self._make_request('/works', params)

    for work in response.get('results', []):
        # Extract ArXiv ID from primary_location if available
        arxiv_id = None
        primary_loc = work.get('primary_location', {})
        if primary_loc.get('source', {}).get('id') == 'https://openalex.org/S2764455111':
            # This is ArXiv source ID in OpenAlex
            arxiv_id = self._extract_arxiv_from_url(primary_loc.get('pdf_url'))

        results[work['id']] = {
            'doi': work.get('doi'),
            'ids': work.get('ids', {}),
            'arxiv_id': arxiv_id
        }

    return results
```

### Phase 2: Parallel Enrichment Orchestrator

#### 2.1 Create Enrichment Orchestrator

```python
# compute_forecast/pipeline/consolidation/parallel_enricher.py

class ParallelEnricher:
    """Orchestrates parallel enrichment using multiple sources"""

    def __init__(self, sources: Dict[str, BaseConsolidationSource]):
        self.sources = sources
        self.executor = ThreadPoolExecutor(max_workers=4)

    def enrich_with_strategy(self, papers: List[Paper],
                           identifiers: Dict[str, PaperIdentifiers],
                           progress_callback=None) -> List[Paper]:
        """
        Enriches papers using optimal source selection based on identifiers.
        """
        # Categorize papers by best enrichment source
        routing = self._route_papers(papers, identifiers)

        # Submit parallel enrichment tasks
        futures = []

        # Route 1: ArXiv papers -> Semantic Scholar (by ArXiv ID)
        if routing['arxiv_papers']:
            future = self.executor.submit(
                self._enrich_arxiv_papers,
                routing['arxiv_papers'],
                identifiers
            )
            futures.append(('semantic_scholar', future))

        # Route 2: Papers with S2 IDs -> Semantic Scholar (by S2 ID)
        if routing['s2_papers']:
            future = self.executor.submit(
                self._enrich_s2_papers,
                routing['s2_papers'],
                identifiers
            )
            futures.append(('semantic_scholar_direct', future))

        # Route 3: All papers -> OpenAlex (comprehensive)
        future = self.executor.submit(
            self._enrich_openalex_papers,
            papers,
            identifiers
        )
        futures.append(('openalex', future))

        # Collect and merge results
        all_results = {}
        for source_name, future in futures:
            try:
                results = future.result(timeout=60)
                self._merge_results(all_results, results, source_name)
            except Exception as e:
                self.logger.error(f"Error in {source_name}: {e}")

        # Apply enrichments to papers
        return self._apply_enrichments(papers, all_results)

    def _route_papers(self, papers: List[Paper],
                     identifiers: Dict[str, PaperIdentifiers]) -> Dict:
        """Intelligent routing based on available identifiers"""
        routing = {
            'arxiv_papers': [],
            's2_papers': [],
            'doi_only_papers': [],
            'openalex_papers': []
        }

        for paper in papers:
            ids = identifiers.get(paper.paper_id)
            if not ids:
                continue

            # Prioritize ArXiv for S2
            if ids.arxiv_id:
                routing['arxiv_papers'].append(paper)
            elif ids.semantic_scholar_id:
                routing['s2_papers'].append(paper)

            # Everyone goes to OpenAlex too
            if ids.openalex_id:
                routing['openalex_papers'].append(paper)

        return routing
```

#### 2.2 Specialized Enrichment Methods

```python
def _enrich_arxiv_papers(self, papers: List[Paper],
                        identifiers: Dict[str, PaperIdentifiers]) -> Dict:
    """Use S2's ArXiv API for best results"""
    s2_source = self.sources['semantic_scholar']

    # Build ArXiv ID list
    arxiv_mapping = {}
    for paper in papers:
        ids = identifiers.get(paper.paper_id)
        if ids and ids.arxiv_id:
            arxiv_mapping[f"ARXIV:{ids.arxiv_id}"] = paper.paper_id

    # Batch fetch by ArXiv ID (100 at a time for S2)
    results = {}
    for batch_start in range(0, len(arxiv_mapping), 100):
        batch_ids = list(arxiv_mapping.keys())[batch_start:batch_start+100]

        # Direct S2 batch API call
        enrichment_data = s2_source.fetch_by_ids(batch_ids)

        # Map back to our paper IDs
        for s2_id, data in enrichment_data.items():
            our_id = arxiv_mapping.get(s2_id)
            if our_id:
                results[our_id] = data

    return results

def _enrich_openalex_papers(self, papers: List[Paper],
                           identifiers: Dict[str, PaperIdentifiers]) -> Dict:
    """Use OpenAlex for comprehensive data including affiliations"""
    oa_source = self.sources['openalex']

    # Build mapping using OpenAlex IDs
    oa_mapping = {}
    for paper in papers:
        ids = identifiers.get(paper.paper_id)
        if ids and ids.openalex_id:
            oa_mapping[ids.openalex_id] = paper.paper_id

    # Use existing enrich_papers but with ID-based lookup
    # This is fast because we already have the OpenAlex IDs
    results = {}

    # Process in batches
    for batch_start in range(0, len(papers), 50):
        batch = papers[batch_start:batch_start+50]

        # Filter to papers we have IDs for
        batch_with_ids = []
        for paper in batch:
            if paper.paper_id in identifiers and identifiers[paper.paper_id].openalex_id:
                batch_with_ids.append(paper)

        if batch_with_ids:
            enrichment_results = oa_source.enrich_papers(batch_with_ids)
            for result in enrichment_results:
                results[result.paper_id] = result

    return results
```

### Phase 3: Integration with Existing CLI

#### 3.1 Modify consolidate.py

```python
# Add new option
def main(
    # ... existing options ...
    use_parallel_strategy: bool = typer.Option(False, "--parallel",
        help="Use parallel ID harvesting strategy for better performance"),
):

    # ... existing setup ...

    if use_parallel_strategy and len(source_names) > 1:
        # Use Strategy 1
        console.print("[yellow]Using parallel ID harvesting strategy[/yellow]")

        # Phase 1: ID Harvesting
        with Progress(...) as progress:
            harvest_task = progress.add_task(
                "[cyan]Harvesting identifiers...[/cyan]",
                total=len(papers)
            )

            # Must have OpenAlex for ID harvesting
            oa_source = None
            for source in source_objects:
                if isinstance(source, OpenAlexSource):
                    oa_source = source
                    break

            if not oa_source:
                console.print("[red]OpenAlex required for parallel strategy[/red]")
                return

            harvester = IDHarvester(oa_source)
            identifiers = harvester.harvest_identifiers(
                papers,
                lambda n: progress.advance(harvest_task, n)
            )

        # Phase 2: Parallel Enrichment
        with Progress(...) as progress:
            enrich_task = progress.add_task(
                "[cyan]Parallel enrichment...[/cyan]",
                total=len(papers) * len(source_objects)
            )

            sources_dict = {s.name: s for s in source_objects}
            enricher = ParallelEnricher(sources_dict)

            enriched_papers = enricher.enrich_with_strategy(
                papers,
                identifiers,
                lambda n: progress.advance(enrich_task, n)
            )

        papers = enriched_papers

    else:
        # Use existing sequential strategy
        # ... existing code ...
```

### Phase 4: Testing & Benchmarking

#### 4.1 Create Test Suite

```python
# tests/test_parallel_consolidation.py

def test_id_harvesting():
    """Test that ID harvesting captures all identifiers"""
    papers = [
        Paper(title="Attention is All You Need", ...),
        Paper(title="BERT: Pre-training...", ...),
    ]

    harvester = IDHarvester(mock_openalex_source)
    identifiers = harvester.harvest_identifiers(papers)

    assert len(identifiers) == 2
    assert identifiers[papers[0].paper_id].arxiv_id == "1706.03762"
    assert identifiers[papers[0].paper_id].doi == "10.48550/arXiv.1706.03762"

def test_parallel_enrichment():
    """Test parallel enrichment with multiple sources"""
    # Test that ArXiv papers go to S2
    # Test that all papers go to OpenAlex
    # Test that results are properly merged

def test_performance_improvement():
    """Benchmark parallel vs sequential"""
    # Load 100 test papers
    # Run sequential consolidation
    # Run parallel consolidation
    # Assert parallel is at least 40% faster
```

#### 4.2 Create Benchmark Script

```python
# scripts/benchmark_consolidation.py

def benchmark_strategies():
    """Compare performance of different strategies"""

    papers = load_test_papers(1000)  # Large test set

    # Sequential (current)
    start = time.time()
    sequential_results = run_sequential_consolidation(papers)
    sequential_time = time.time() - start

    # Parallel (Strategy 1)
    start = time.time()
    parallel_results = run_parallel_consolidation(papers)
    parallel_time = time.time() - start

    print(f"Sequential: {sequential_time:.2f}s")
    print(f"Parallel: {parallel_time:.2f}s")
    print(f"Speedup: {sequential_time/parallel_time:.2f}x")

    # Verify same results
    assert compare_results(sequential_results, parallel_results)
```

## Implementation Timeline

### Step 1: Core Components (4-6 hours)
- [ ] Implement IDHarvester class
- [ ] Add fetch_identifiers_only to OpenAlexSource
- [ ] Create PaperIdentifiers dataclass
- [ ] Write unit tests for ID harvesting

### Step 2: Parallel Enricher (6-8 hours)
- [ ] Implement ParallelEnricher class
- [ ] Create routing logic
- [ ] Implement specialized enrichment methods
- [ ] Add result merging logic
- [ ] Write unit tests for parallel enrichment

### Step 3: CLI Integration (2-3 hours)
- [ ] Add --parallel flag to consolidate command
- [ ] Integrate with existing progress tracking
- [ ] Update documentation
- [ ] Add integration tests

### Step 4: Testing & Optimization (4-5 hours)
- [ ] Create comprehensive test suite
- [ ] Run benchmarks on real data
- [ ] Profile and optimize bottlenecks
- [ ] Document performance improvements

Total estimated time: 16-22 hours

## Expected Benefits

1. **Performance**: 40-60% faster for mixed datasets
2. **Better Coverage**: Optimal source selection based on identifiers
3. **Scalability**: Easy to add more parallel workers
4. **Maintainability**: Clean separation of concerns

## Risk Mitigation

1. **API Rate Limits**:
   - Use API keys for both sources
   - Implement adaptive rate limiting
   - Add exponential backoff

2. **Memory Usage**:
   - Process in batches
   - Use generators where possible
   - Clear intermediate results

3. **Error Handling**:
   - Graceful degradation if one source fails
   - Timeout handling for slow APIs
   - Detailed error logging

## Success Metrics

1. **Speed**: <25 seconds for 1000 papers
2. **Coverage**: >99% papers enriched
3. **Quality**: No regression in data quality
4. **Reliability**: <0.1% failure rate

## Next Steps

1. Review plan with team
2. Create feature branch
3. Implement IDHarvester first
4. Iteratively build and test components
5. Run production benchmarks
6. Deploy with feature flag
