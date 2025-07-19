# 2025-01-19 Mark All Papers as Processed Regardless of Success

## Request
User pointed out that papers not found during any phase should still be marked as processed in the checkpoint, as retrying them won't yield different results.

## Solution
Updated all three phases to mark papers as processed regardless of whether they were successfully found or enriched:

### Phase 1 (OpenAlex ID Harvesting)
- Changed from only marking papers that were found to marking ALL papers in each batch as processed
- This prevents retrying papers that OpenAlex couldn't find

### Phase 2 (Semantic Scholar Enrichment)
- Updated to use hash-based tracking instead of index-based
- Mark all papers in each batch as processed after the API call
- Papers without external IDs are also marked as processed (they can't be enriched anyway)

### Phase 3 (OpenAlex Full Enrichment)
- Mark all papers as processed at the end of the phase
- Since Phase 3 processes all papers, this ensures complete coverage

## Implementation Changes

1. **Phase 1**: Changed from marking only found papers to marking all attempted papers:
```python
# Before: Only marked papers that were found
for paper_id, oa_id in batch_mapping.items():
    paper = next((p for p in batch if p.paper_id == paper_id), None)
    if paper:
        processed_hashes.add(get_paper_hash(paper))

# After: Mark ALL papers in batch as processed
for paper in batch:
    processed_hashes.add(get_paper_hash(paper))
```

2. **Phase 2**: 
- Added hash-based tracking with `processed_hashes` parameter
- Filter papers before processing
- Mark all papers in batch as processed after API calls
- Mark papers without external IDs as processed

3. **Phase 3**: Added logic to mark all papers as processed after completion

## Benefits
1. **No Redundant Retries**: Papers that couldn't be found won't be retried on resume
2. **Consistent Behavior**: All phases now consistently mark attempted papers as processed
3. **Better Performance**: Fewer unnecessary API calls on resume
4. **Cleaner Logic**: Hash-based tracking is consistent across all phases

## Test Results
With 20 test papers:
- Initial run: Processed 7 papers before interruption
- Resume: "Skipping 7 papers already processed (hashes: 7)"
- Phase 2: "Phase 2: Skipping 8 papers already processed"
- All papers marked as processed, no redundant API calls