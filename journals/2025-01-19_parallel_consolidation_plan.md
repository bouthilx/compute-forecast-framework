# 2025-01-19 Parallel Consolidation Architecture Plan

## Request
User identified that Phase 1 (OpenAlex ID harvesting) is ineffective - finding no DOIs or ArXiv IDs, making Phase 2 slower and Phase 3 redundant. Requested removal of Phase 1 and parallel execution of OpenAlex and Semantic Scholar with merged results.

## Analysis

### Current Issues
1. **Phase 1 Inefficiency**: OpenAlex API doesn't return DOIs/ArXiv IDs in title search responses
2. **Sequential Bottleneck**: Phase 2 depends on Phase 1 results
3. **Redundant API Calls**: Phase 3 duplicates OpenAlex calls from Phase 1
4. **Poor Performance**: Sequential execution wastes time

### Root Cause
The three-phase approach assumed OpenAlex title searches would return identifiers, but they only return the OpenAlex ID. This makes Phase 1 pointless for accelerating subsequent phases.

## Solution: Parallel Architecture

### Core Design
Replace three sequential phases with two parallel workers that perform complete enrichment:

```
Input Papers ──┬─→ OpenAlex Worker ─────→ Queue ──┐
               │                                    ├─→ Merge Worker → Output
               └─→ Semantic Scholar Worker → Queue ─┘
```

### Components

#### 1. OpenAlex Worker
- Performs find + enrich in single pass per paper
- Extracts ALL identifiers from enrichment response
- Processes papers in configurable batches
- Sends complete enrichment data to merge queue

#### 2. Semantic Scholar Worker
- Attempts batch lookup by existing IDs (DOI, ArXiv)
- Falls back to title search for unfound papers
- Extracts ALL identifiers from responses
- Sends complete enrichment data to merge queue

#### 3. Merge Worker
- Consumes results from both queues
- Applies merge rules:
  - **IDs** (`doi`, `arxiv_id`, `openalex_id`): Only set if None
  - **Records**: Append to lists (`citations`, `abstracts`, `urls`, `identifiers`)
- Maintains consolidated state
- Handles checkpointing

#### 4. Progress Display
Two progress bars at bottom showing real-time status:
```
OpenAlex:         [████████████████----] 80% (800/1000) 02:30:45 (2025-01-19 18:45:00 ETA)
Semantic Scholar: [██████████----------] 50% (500/1000) 04:15:30 (2025-01-19 20:29:45 ETA)
```

### Data Flow Example

1. **Paper Input**: `{"title": "Deep Learning", "year": 2015, ...}`

2. **OpenAlex Worker Output**:
   ```python
   {
       'openalex_id': 'W2964298273',
       'doi': '10.1038/nature14539',
       'citations': 50000,
       'abstract': 'Deep learning allows...',
       'identifiers': [
           {'type': 'doi', 'value': '10.1038/nature14539'},
           {'type': 'pmid', 'value': '26017442'},
           {'type': 'mag', 'value': '2964298273'}
       ]
   }
   ```

3. **Semantic Scholar Worker Output**:
   ```python
   {
       'doi': '10.1038/nature14539',  # Would be ignored (already set)
       'citations': 48500,
       'abstract': 'Deep learning allows computational models...',
       'identifiers': [
           {'type': 's2_paper', 'value': '5ca9566ea9de8f8cb34dc7f1d7c0f4d2dae26b91'},
           {'type': 'arxiv', 'value': '1505.00387'}
       ]
   }
   ```

4. **Merged Result**:
   - `paper.doi` = '10.1038/nature14539' (from OpenAlex, first to set)
   - `paper.openalex_id` = 'W2964298273'
   - `paper.citations` = [CitationRecord(OpenAlex, 50000), CitationRecord(S2, 48500)]
   - `paper.abstracts` = [AbstractRecord(OpenAlex), AbstractRecord(S2)]
   - `paper.identifiers` = [4 IdentifierRecords from both sources]

### Benefits

1. **Parallel Processing**: 2x theoretical speedup
2. **No Dependencies**: Workers are independent
3. **Complete ID Coverage**: Each source contributes all its known IDs
4. **Single API Pass**: No redundant calls
5. **Source Attribution**: All data tracked with provenance
6. **Real-time Visibility**: Dual progress bars

### Implementation Plan

1. Create base `ConsolidationWorker` class with common functionality
2. Implement `OpenAlexWorker` and `SemanticScholarWorker`
3. Create `MergeWorker` with correct merge rules
4. Build `ParallelConsolidator` orchestrator with queues
5. Implement dual progress bar display using Rich
6. Adapt checkpoint system for parallel state tracking
7. Update CLI to support new architecture

### Checkpoint Strategy

```python
checkpoint_state = {
    'openalex_processed_hashes': set(),
    'semantic_scholar_processed_hashes': set(),
    'merged_papers': [],
    'timestamp': datetime.now()
}
```

On resume:
- Each worker skips papers in its processed_hashes
- Merge worker loads previous merged_papers
- Progress bars show remaining work per source

### Configuration

- `--openalex-batch-size`: Batch size for OpenAlex (default: 50)
- `--ss-batch-size`: Batch size for Semantic Scholar (default: 500)
- `--checkpoint-interval`: Minutes between checkpoints (default: 5)
- `--single-source`: Optional mode to run only one source

## Outcome

This architecture eliminates the ineffective Phase 1, removes sequential dependencies, and provides better performance through parallelization while maintaining data quality through proper merge rules and source attribution.
