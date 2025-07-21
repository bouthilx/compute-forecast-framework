# 2025-01-19 Fixed Phase 1 Identifiers Collection

## Issue
The Phase 1 progress bar was showing 0 for all ID counts (DOI, ArXiv, OA, etc.) even though papers were being found in OpenAlex. The checkpoint showed `identifiers_collected` as empty `{}`.

## Root Cause
The harvest_identifiers_openalex function had two issues:

1. **Early checkpoint**: The checkpoint callback was being called immediately after find_papers, before any PaperIdentifiers objects were created
2. **Missing OpenAlex IDs**: When papers were found in OpenAlex, only the mapping was stored but PaperIdentifiers objects weren't created until later

## Solution

### 1. Create PaperIdentifiers Immediately
When papers are found in OpenAlex, immediately create PaperIdentifiers objects with the OpenAlex ID:

```python
# Create PaperIdentifiers for papers found in OpenAlex
for paper_id, oa_id in batch_mapping.items():
    if oa_id and paper_id not in identifiers:
        identifiers[paper_id] = PaperIdentifiers(
            paper_id=paper_id,
            openalex_id=oa_id
        )
```

### 2. Update Existing Identifiers
When fetching additional identifier data, update existing PaperIdentifiers objects instead of replacing them:

```python
if paper_id in identifiers:
    paper_ids = identifiers[paper_id]
    # Update with additional identifiers
    if ids.get('doi'):
        paper_ids.doi = ids.get('doi', '').replace('https://doi.org/', '')
    # ... update other fields
else:
    # Create new if somehow missed
    paper_ids = PaperIdentifiers(...)
```

## Benefits
1. **Immediate visibility**: OpenAlex IDs are tracked as soon as papers are found
2. **Accurate progress**: The progress bar now shows correct counts for each ID type
3. **Better checkpointing**: Identifiers are saved even if the process is interrupted early

## Expected Behavior
Now when running Phase 1:
- OpenAlex IDs should appear immediately after find_papers
- DOI, ArXiv, and other IDs are added as they're discovered
- Progress bar shows: `[DOI:8523 ArXiv:1247 OA:32451 S2:0 PM:156]`

## Summary
Fixed the identifiers collection to ensure all discovered IDs are properly tracked and displayed in the progress bar, giving users accurate visibility into the ID harvesting process.
