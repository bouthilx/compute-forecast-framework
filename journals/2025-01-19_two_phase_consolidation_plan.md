# 2025-01-19 Two-Phase Consolidation Implementation Plan

## Problem Analysis

The current consolidation implementation faces a critical performance issue when using Semantic Scholar:
- Papers in our dataset have NO external identifiers (DOIs, ArXiv IDs)
- Semantic Scholar API doesn't support batch title searches
- This forces individual API calls per paper with 10-second rate limiting
- Result: 500 papers take ~83 minutes to process

## Proposed Solution: Two-Phase Consolidation

Implement a hardcoded two-phase approach that leverages each source's strengths:

### Phase 1: OpenAlex ID Harvesting
- Use OpenAlex as primary source for identifier discovery
- OpenAlex has 100% title search success rate
- Collect all available identifiers: DOI, ArXiv ID, OpenAlex ID, and potentially Semantic Scholar ID

### Phase 2: Semantic Scholar Enrichment
- Use collected identifiers (especially DOIs and ArXiv IDs) for efficient batch lookups
- Semantic Scholar can process 500 papers in a single batch request when using external IDs
- This reduces API calls from 500 to 1-2, improving speed by ~250-500x

## Implementation Details

### 1. Data Model for Identifiers

Based on the strategy document, we need to collect these identifiers:

```python
@dataclass
class PaperIdentifiers:
    """Complete identifier set for a paper"""
    paper_id: str  # Our internal ID
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID if available
```

### 2. Modified Consolidation Flow

Remove the `--sources` option and hardcode the two-phase approach:

```python
def consolidate(papers: List[Paper]) -> List[Paper]:
    # Phase 1: OpenAlex ID Harvesting
    print("Phase 1: Collecting identifiers from OpenAlex...")
    identifiers = harvest_identifiers_openalex(papers)
    
    # Enrich papers with discovered identifiers
    papers = add_identifiers_to_papers(papers, identifiers)
    
    # Phase 2: Semantic Scholar Enrichment (using discovered IDs)
    print("Phase 2: Enriching from Semantic Scholar using collected IDs...")
    enrichments = enrich_semantic_scholar(papers)
    
    # Phase 3: Final OpenAlex Enrichment
    print("Phase 3: Final enrichment from OpenAlex...")
    final_enrichments = enrich_openalex_full(papers)
    
    # Merge all enrichments
    return merge_enrichments(papers, enrichments, final_enrichments)
```

### 3. OpenAlex ID Harvesting

Optimize OpenAlex to fetch only identifiers in the first pass:

```python
def harvest_identifiers_openalex(papers: List[Paper]) -> Dict[str, PaperIdentifiers]:
    """Fast first-pass to collect all identifiers"""
    
    # Use OpenAlex's select parameter to fetch minimal data
    # Fields needed: id, doi, ids (contains external IDs)
    
    identifiers = {}
    
    # Process in batches of 50 (OpenAlex optimal)
    for batch in batches(papers, 50):
        # Use title search to find OpenAlex IDs
        oa_ids = openalex_source.find_papers(batch)
        
        # Fetch just identifier fields
        id_data = fetch_minimal_fields(oa_ids, fields=['id', 'doi', 'ids'])
        
        # Extract all identifiers
        for paper_id, data in id_data.items():
            identifiers[paper_id] = PaperIdentifiers(
                paper_id=paper_id,
                openalex_id=data['id'],
                doi=data.get('doi'),
                arxiv_id=extract_arxiv_id(data),
                semantic_scholar_id=data.get('ids', {}).get('semantic_scholar')
            )
    
    return identifiers
```

### 4. Semantic Scholar Batch Enrichment

Use collected identifiers for efficient batch processing:

```python
def enrich_semantic_scholar(papers: List[Paper]) -> List[EnrichmentResult]:
    """Use discovered IDs for efficient S2 enrichment"""
    
    # Build ID lists for batch lookup
    doi_batch = []
    arxiv_batch = []
    s2_batch = []
    
    for paper in papers:
        if paper.doi:
            doi_batch.append(f"DOI:{paper.doi}")
        if paper.arxiv_id:
            arxiv_batch.append(f"ARXIV:{paper.arxiv_id}")
        if hasattr(paper, 'semantic_scholar_id'):
            s2_batch.append(paper.semantic_scholar_id)
    
    # Single batch API call (or minimal calls for 500+ papers)
    all_ids = doi_batch + arxiv_batch + s2_batch
    
    # Process in chunks of 500
    results = []
    for chunk in chunks(all_ids, 500):
        batch_data = s2_source.fetch_by_ids(chunk)
        results.extend(batch_data)
    
    return results
```

### 5. Benefits of This Approach

1. **Performance**: 
   - Current: 500 papers = ~83 minutes (500 API calls)
   - New: 500 papers = ~2 minutes (10-20 API calls total)
   - Speedup: ~40-50x faster

2. **Reliability**:
   - No dependency on title searches for S2
   - Leverages OpenAlex's superior title matching
   - Falls back gracefully if identifiers not found

3. **Simplicity**:
   - No complex parallelization
   - Clear two-phase flow
   - Easy to debug and maintain

4. **Data Quality**:
   - Gets best of both sources
   - OpenAlex: Better coverage, affiliations
   - Semantic Scholar: Better ArXiv data, citation counts

## Implementation Steps

1. **Remove source selection** (2-3 hours)
   - Remove `--sources` option from CLI
   - Hardcode two-phase approach
   - Update help text and documentation

2. **Implement ID harvesting** (3-4 hours)
   - Create `PaperIdentifiers` dataclass
   - Add ID harvesting logic to OpenAlex source
   - Optimize for minimal API calls

3. **Update Semantic Scholar** (2-3 hours)
   - Prioritize batch lookups by external IDs
   - Fall back to title search only when necessary
   - Add logging to show efficiency gains

4. **Integration and testing** (2-3 hours)
   - Wire up two-phase flow
   - Add progress tracking for each phase
   - Test with real data

5. **Update checkpointing** (1-2 hours)
   - Save phase completion state
   - Allow resuming from Phase 2 if Phase 1 complete

Total estimate: 10-15 hours

## Next Steps

1. Get approval for removing source selection option
2. Create feature branch
3. Implement PaperIdentifiers model
4. Start with OpenAlex ID harvesting
5. Test with small dataset to verify ID discovery
6. Implement S2 batch enrichment
7. Full integration testing

This approach solves the immediate performance problem while keeping the implementation simple and maintainable.