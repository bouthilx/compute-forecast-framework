# Consolidation Resumption Analysis

**Date**: 2025-01-20
**Time**: Late afternoon session
**Focus**: Investigating consolidation checkpoint resumption issues

## Issue Description

User reported discrepancies when resuming consolidation:
- Before interruption: ~274 OpenAlex papers (228 citations, 228 abstracts), 22 Semantic Scholar papers (9 citations, 7 abstracts)
- After resumption: Similar OpenAlex count but fewer Semantic Scholar papers, much fewer citations and abstracts for both

## Analysis Findings

### 1. Checkpoint Format Analysis

Examined the latest checkpoint at: `.cf_state/consolidate/consolidate_20250719_201418_d9bb5987/`

The checkpoint structure shows:
```json
{
  "sources": {
    "openalex": {
      "papers_processed": 297,
      "papers_enriched": 27,
      "api_calls": 1830
    },
    "semantic_scholar": {
      "papers_processed": 16,
      "papers_enriched": 2,
      "api_calls": 21
    },
    "merge": {
      "papers_merged": 36,
      "merged_paper_count": 36
    }
  }
}
```

### 2. Output File Analysis

The `papers_enriched.json` file contains:
- Total papers: 34,648 (the full input set)
- Papers with OpenAlex ID: 247 (not 297 as checkpoint claims)
- Papers with Semantic Scholar ID: 0 (not 16 as checkpoint claims)
- Papers with abstracts field: 9,665
- Papers with actual abstract data: 247 (all from OpenAlex)
- Total citations: 16,121 across 247 papers

### 3. Data Structure Issues

Found that the enriched data uses a different structure than expected:
- Abstracts are stored in `abstracts` field (plural), not `abstract`
- Each abstract is a metadata object: `{'source': 'openalex', 'timestamp': '...', 'data': {'text': '...'}}`
- Citations follow similar structure: `{'source': 'openalex', 'data': {'count': 8}}`

### 4. Key Problems Identified

1. **Data Loss**: The checkpoint claims more papers were processed than appear in the output
   - 297 OpenAlex processed → only 247 in output
   - 16 Semantic Scholar processed → 0 in output

2. **Incomplete Saving**: The consolidation appears to be saving incomplete data
   - Missing Semantic Scholar results entirely
   - Missing 50 OpenAlex results

3. **Field Mismatch**: The statistics counting logic may be looking for wrong field names
   - Looking for `abstract` but data is in `abstracts`
   - Not accounting for nested data structure

## Code Updates Made

### 1. Enhanced Session List Display

Updated `consolidate_sessions.py` to show source-specific statistics:
- Added OpenAlex and Semantic Scholar columns
- Display format: "Xp/Ye" (X papers processed / Y papers enriched)
- Extract statistics from checkpoint data

### 2. Updated Checkpoint Manager

Modified `find_resumable_sessions` to include source statistics:
- Extract papers_processed, papers_enriched, citations_found, abstracts_found
- Add to session info for display in list command

## Recommendations

1. **Fix Data Saving**: Investigate why processed papers aren't being saved to output
2. **Update Statistics**: Fix the counting logic to use correct field names (`abstracts` not `abstract`)
3. **Verify Resumption**: Check if the resumption logic is correctly loading and continuing from checkpoint
4. **Add Validation**: Add checks to ensure checkpoint counts match output counts

## Next Steps

1. Investigate the consolidation save logic to understand data loss
2. Update the progress display to show accurate counts based on actual data structure
3. Add integrity checks between checkpoint claims and actual output
4. Test resumption with a smaller dataset to verify behavior