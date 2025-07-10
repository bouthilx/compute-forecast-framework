# 2025-01-10 Optimal Consolidation Strategies Using OpenAlex and Semantic Scholar

## Overview

Based on the API comparison results, I'm designing three consolidation strategies that maximize speed and coverage by leveraging the strengths of both OpenAlex and Semantic Scholar. Each strategy makes different trade-offs between complexity, speed, and coverage.

## Strategy 1: Parallel First-Pass ID Harvesting

**Concept:** Use OpenAlex's fast title search to harvest all identifiers (DOI, ArXiv ID) in a first pass, then distribute enrichment across both sources in parallel based on identifier availability.

### Implementation:

```python
# Phase 1: ID Harvesting (Single-threaded, uses OpenAlex only)
def harvest_identifiers(papers: List[Paper]) -> Dict[str, Dict[str, str]]:
    """
    Fast first pass to collect all identifiers from OpenAlex
    Returns: {paper_id: {'doi': ..., 'arxiv_id': ..., 'openalex_id': ...}}
    """
    # Batch process with OpenAlex (50 papers per request)
    # Extract DOI, ArXiv ID, OpenAlex ID from results
    # ~0.5s per 50 papers = ~10s for 1000 papers

# Phase 2: Parallel Enrichment (Multi-threaded)
def parallel_enrich(papers: List[Paper], identifiers: Dict):
    # Split papers into optimal groups:
    arxiv_papers = [p for p in papers if identifiers[p.id].get('arxiv_id')]
    doi_only_papers = [p for p in papers if identifiers[p.id].get('doi') and not identifiers[p.id].get('arxiv_id')]
    
    # Run in parallel:
    # Worker 1: Semantic Scholar batch process ArXiv papers (500/batch, use ArXiv ID lookup)
    # Worker 2: OpenAlex batch process all papers (50/batch, use OpenAlex ID)
    # Worker 3: Semantic Scholar process high-value DOI papers (100/batch)
    
    # Merge results, preferring:
    # - Semantic Scholar for ArXiv papers (better citation data)
    # - OpenAlex for everything else (better affiliations)
```

### Advantages:
- Leverages OpenAlex's 100% title search success rate
- Uses Semantic Scholar's 100% ArXiv lookup success
- Parallel processing minimizes total time
- Can distribute load based on API rate limits

### Estimated Performance:
- 1000 papers: ~25 seconds total
  - Phase 1: 10s (OpenAlex ID harvesting)
  - Phase 2: 15s (parallel enrichment)
- Coverage: ~99% (combines best of both sources)

### Resource Requirements:
- 3-4 parallel workers
- Semantic Scholar API key recommended
- ~2x memory usage due to parallel processing

## Strategy 2: Smart Router with Fallback Cascade

**Concept:** Route papers intelligently based on their characteristics, with automatic fallback to ensure maximum coverage.

### Implementation:

```python
class SmartConsolidationRouter:
    def __init__(self):
        self.openalex = OpenAlexSource()
        self.s2 = SemanticScholarSource()
        
    def route_papers(self, papers: List[Paper]) -> List[EnrichmentResult]:
        # Categorize papers
        arxiv_papers = []
        cs_papers = []  # Computer Science papers (by venue/keywords)
        recent_papers = []  # Papers from last 2 years
        other_papers = []
        
        for paper in papers:
            if paper.arxiv_id:
                arxiv_papers.append(paper)
            elif self._is_cs_venue(paper.venue) or self._has_ml_keywords(paper.title):
                cs_papers.append(paper)
            elif paper.year >= 2023:
                recent_papers.append(paper)
            else:
                other_papers.append(paper)
        
        # Process in parallel with optimal source selection
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            # ArXiv papers -> Semantic Scholar first, OpenAlex fallback
            future1 = executor.submit(self._process_with_fallback, 
                                    arxiv_papers, self.s2, self.openalex)
            
            # CS papers -> Try both in parallel, merge results
            future2 = executor.submit(self._process_both_merge, cs_papers)
            
            # Recent papers -> OpenAlex (better coverage of new papers)
            future3 = executor.submit(self.openalex.enrich_papers, recent_papers)
            
            # Other papers -> OpenAlex only
            future4 = executor.submit(self.openalex.enrich_papers, other_papers)
            
        return self._merge_all_results(futures)
```

### Routing Logic:
1. **ArXiv papers** → Semantic Scholar (by ArXiv ID) → OpenAlex fallback
2. **CS/ML papers** → Both sources in parallel → Merge best fields
3. **Recent papers** → OpenAlex (better for new publications)
4. **Other papers** → OpenAlex only

### Advantages:
- Intelligent routing based on paper characteristics
- Automatic fallback ensures no papers are missed
- Can merge data from both sources for maximum completeness
- Adapts to source strengths

### Estimated Performance:
- 1000 papers: ~20-30 seconds (depends on paper distribution)
- Coverage: ~99.5% (fallback ensures near-complete coverage)

### Resource Requirements:
- 4 parallel workers
- More complex logic but better results
- Handles rate limits gracefully

## Strategy 3: Speculative Parallel Fetch with Result Racing

**Concept:** Aggressively fetch from both sources in parallel for all papers, use the first complete result, and cancel redundant requests.

### Implementation:

```python
class SpeculativeConsolidator:
    def __init__(self):
        self.sources = {
            'openalex': OpenAlexSource(),
            'semantic_scholar': SemanticScholarSource()
        }
        
    async def consolidate_papers(self, papers: List[Paper]) -> List[EnrichmentResult]:
        # Create tasks for both sources for all papers
        tasks = []
        for paper in papers:
            # Create competing tasks
            oa_task = self._fetch_with_timeout(self.sources['openalex'], paper, timeout=3.0)
            s2_task = self._fetch_with_timeout(self.sources['semantic_scholar'], paper, timeout=5.0)
            
            # Race condition: first to return valid data wins
            tasks.append(self._race_sources(paper, oa_task, s2_task))
        
        # Process all papers concurrently
        results = await asyncio.gather(*tasks)
        
        # Post-process: fill missing fields from slower source if available
        return self._backfill_missing_fields(results)
    
    async def _race_sources(self, paper, oa_task, s2_task):
        # First valid result wins
        for task in asyncio.as_completed([oa_task, s2_task]):
            result = await task
            if result and self._is_valid_result(result):
                # Cancel the other task
                other_task.cancel()
                return result
        return None
```

### Optimization Features:
1. **Speculative fetching**: Try both sources simultaneously
2. **Result racing**: Use whichever returns first with valid data
3. **Adaptive timeouts**: Shorter timeout for OpenAlex (faster API)
4. **Backfilling**: Use slower results to fill missing fields
5. **Batch optimization**: Group papers by identifier type

### Advantages:
- Minimum latency (limited by fastest source)
- Maximum coverage (tries everything)
- Naturally load balances between sources
- Handles API failures gracefully

### Estimated Performance:
- 1000 papers: ~15-20 seconds
- Coverage: ~99.9% (both sources attempted)
- Latency: As fast as the fastest available source

### Resource Requirements:
- High parallelism (10+ concurrent requests)
- 2x API calls (but many cancelled early)
- Requires async implementation
- Higher bandwidth usage

## Comparison Table

| Strategy | Speed (1000 papers) | Coverage | Complexity | Resource Usage | Best For |
|----------|-------------------|----------|------------|----------------|-----------|
| **1. ID Harvesting** | ~25s | 99% | Medium | Medium | Balanced approach |
| **2. Smart Router** | ~20-30s | 99.5% | High | Medium | Heterogeneous datasets |
| **3. Speculative** | ~15-20s | 99.9% | High | High | Speed critical |

## Recommended Implementation Order

1. **Start with Strategy 1** (ID Harvesting)
   - Easiest to implement with current architecture
   - Good balance of speed and coverage
   - Can be enhanced incrementally

2. **Enhance with Strategy 2** (Smart Router)
   - Add routing logic on top of Strategy 1
   - Better for mixed datasets
   - More intelligent resource usage

3. **Consider Strategy 3** (Speculative) for:
   - Real-time applications
   - Small batch sizes
   - When API costs are not a concern

## Implementation Tips

### For All Strategies:
```python
# Optimal batch sizes based on testing
OPENALEX_BATCH_SIZE = 50  # URL length limited
S2_BATCH_SIZE = 500       # API maximum
S2_ARXIV_BATCH_SIZE = 100 # Separate endpoint

# Rate limits
OPENALEX_RATE_LIMIT = None  # No hard limit
S2_RATE_LIMIT = 1.0         # 1 req/sec with key
S2_RATE_LIMIT_NO_KEY = 0.1  # 1 req/10sec without

# Timeouts
OPENALEX_TIMEOUT = 5.0
S2_TIMEOUT = 10.0
```

### Parallel Processing:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

# For CPU-bound merging
executor = ThreadPoolExecutor(max_workers=cpu_count())

# For I/O-bound API calls
async with aiohttp.ClientSession() as session:
    tasks = [fetch_paper(session, paper) for paper in papers]
    results = await asyncio.gather(*tasks)
```

### Result Merging Priority:
```python
def merge_results(oa_result, s2_result):
    # Priority rules based on testing
    merged = {}
    
    # Prefer S2 for: citations, fields_of_study
    # Prefer OA for: affiliations, concepts, abstract
    # Merge both: authors, venues, URLs
    
    return merged
```

## Conclusion

All three strategies can achieve >99% coverage with sub-30 second performance for 1000 papers. The choice depends on:

- **Strategy 1**: Best for getting started, good balance
- **Strategy 2**: Best for heterogeneous datasets with mixed venues/years  
- **Strategy 3**: Best for absolute minimum latency

For the compute forecast project, I recommend implementing Strategy 1 first, then adding Strategy 2's intelligent routing as an enhancement. Strategy 3 is overkill unless real-time performance becomes critical.