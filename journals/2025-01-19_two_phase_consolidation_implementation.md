# 2025-01-19 Two-Phase Consolidation Implementation Progress

## Work Completed

### 1. Problem Analysis
- Identified that Semantic Scholar was making individual API requests per paper (one request every 10 seconds)
- Root cause: Papers in dataset have NO external identifiers (DOIs, ArXiv IDs)
- Semantic Scholar API doesn't support batch title searches
- Result: 500 papers would take ~83 minutes to process

### 2. Solution Design
Created a two-phase consolidation plan:
- **Phase 1**: Use OpenAlex for identifier discovery (100% title search success)
- **Phase 2**: Use discovered identifiers for efficient Semantic Scholar batch lookups
- **Phase 3**: Final enrichment from OpenAlex with full data

### 3. Implementation Started

#### Created Data Models
- `PaperIdentifiers` dataclass in `models_extended.py` to track all identifiers:
  - DOI, ArXiv ID, OpenAlex ID, Semantic Scholar ID, PubMed ID, etc.
  - Helper method `has_external_ids()` to check if batch lookup is possible

- `ConsolidationPhaseState` dataclass to track two-phase progress:
  - Current phase and completion status
  - Collected identifiers
  - Statistics (papers with DOIs, ArXiv IDs, etc.)

#### Started New Consolidate Implementation
- Created `consolidate_v2.py` with hardcoded two-phase approach
- Implemented `harvest_identifiers_openalex()` function:
  - Uses OpenAlex find_papers for title matching
  - Fetches minimal fields (id, ids, doi, primary_location)
  - Extracts ArXiv IDs from primary_location URLs
  - Returns PaperIdentifiers mapping

#### Key Design Decisions
1. **Removed --sources option**: Two-phase approach is hardcoded for optimal performance
2. **Minimal data fetching**: Phase 1 only fetches identifiers, not full enrichment
3. **ArXiv ID extraction**: Special logic to extract ArXiv IDs from OpenAlex URLs
4. **Progress tracking**: Separate progress bars for each phase

## Current Status

The implementation is partially complete:
- ✅ Data models created
- ✅ Phase 1 (OpenAlex ID harvesting) implemented
- ⏳ Phase 2 (Semantic Scholar batch enrichment) scaffolded but not implemented
- ❌ Phase 3 (OpenAlex full enrichment) not started
- ❌ Integration with main CLI not completed

## Next Steps

1. **Complete Phase 2 Implementation**:
   - Use collected DOIs/ArXiv IDs for S2 batch lookups
   - Handle papers without external IDs separately
   - Merge enrichment results

2. **Implement Phase 3**:
   - Full OpenAlex enrichment for all papers
   - Extract abstracts, citations, affiliations

3. **Replace Original Consolidate**:
   - Update main consolidate.py with two-phase approach
   - Update CLI help text
   - Test with real data

4. **Update Checkpointing**:
   - Save phase state in checkpoints
   - Allow resuming from specific phase

## Expected Benefits

Once complete, this implementation will provide:
- **40-50x speedup**: From ~83 minutes to ~2 minutes for 500 papers
- **Better data quality**: Leverages each source's strengths
- **Simpler code**: No complex source selection logic
- **More reliable**: Less dependent on flaky title searches

## Technical Notes

### OpenAlex ArXiv ID Extraction
OpenAlex stores ArXiv papers with source ID 'https://openalex.org/S2764455111'. The ArXiv ID can be extracted from the PDF URL pattern: `https://arxiv.org/pdf/1706.03762.pdf`

### Identifier Mapping Strategy
1. Papers get OpenAlex IDs first (best title matching)
2. OpenAlex provides DOIs, ArXiv IDs, MAG IDs
3. These external IDs enable efficient S2 batch lookups
4. S2 provides additional identifiers and better citation data

### Rate Limiting Considerations
- OpenAlex: No strict rate limit with email
- Semantic Scholar: 0.1 req/s without key, 1.0 req/s with key
- Batch processing minimizes API calls regardless
