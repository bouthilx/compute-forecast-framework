# 2025-01-19 Configurable Batch Sizes for Each Phase

## Request
The user requested that batch sizes be configurable for each phase, with Phase 1 specifically needing batch size 1 since OpenAlex doesn't support batch title searches.

## Implementation

### 1. Added Command-Line Options
Added three new command-line options to the consolidate command:
- `--phase1-batch-size`: Batch size for Phase 1 (OpenAlex ID harvesting), default 1
- `--phase2-batch-size`: Batch size for Phase 2 (Semantic Scholar enrichment), default 500
- `--phase3-batch-size`: Batch size for Phase 3 (OpenAlex enrichment), default 50

### 2. Updated Function Signatures
Modified functions to accept batch_size parameters:
- `harvest_identifiers_openalex`: Added `batch_size` parameter (default 1)
- `enrich_semantic_scholar_batch`: Added `batch_size` parameter (default 500)

### 3. Source Configuration
Updated OpenAlex source configuration to use phase-specific batch sizes:
- `find_batch_size`: Set to `phase1_batch_size` for finding papers in Phase 1
- `batch_size`: Set to `phase3_batch_size` for enrichment in Phase 3

### 4. Phase-Specific Behavior
- **Phase 1**: Uses batch size 1 by default since OpenAlex requires individual title searches
- **Phase 2**: Uses batch size 500 by default (Semantic Scholar API limit)
- **Phase 3**: Uses batch size 50 by default for OpenAlex enrichment

## Benefits
1. **Optimized Performance**: Each phase can use the optimal batch size for its API
2. **Flexibility**: Users can tune batch sizes based on their needs
3. **API Compliance**: Respects API limitations (e.g., OpenAlex title search, S2 500-paper limit)
4. **Debugging**: Smaller batch sizes can be used for testing

## Usage Example
```bash
# Use default batch sizes
uv run python -m compute_forecast.cli consolidate -i papers.json -o enriched.json

# Custom batch sizes for debugging
uv run python -m compute_forecast.cli consolidate -i papers.json -o enriched.json \
  --phase1-batch-size 1 \
  --phase2-batch-size 100 \
  --phase3-batch-size 25
```

## Summary
The implementation provides fine-grained control over batch processing in each phase, addressing the fundamental limitation that OpenAlex doesn't support batch title searches while allowing optimal batch sizes for other operations.