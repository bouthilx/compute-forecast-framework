# 2025-01-19 Simplified Checkpoint Resume with Hash-Based Tracking

## Request
User reported that when resuming consolidation with checkpoints, the system was re-processing papers that were already in the checkpoint, making unnecessary API calls.

## Problem Analysis
The checkpoint system was storing complex identifier objects but wasn't efficiently checking if papers were already processed during resume. The resume logic was checking if `paper.paper_id` existed in the identifiers dictionary, but:
1. Some papers might not have paper_id set properly
2. The check was happening after the API call in some cases
3. The system was too complex for simple "already processed" tracking

## Solution
Implemented a simple hash-based tracking system:

1. **Paper Hash Function**: Created `get_paper_hash()` that generates a unique SHA256 hash for each paper based on:
   - Title (normalized to lowercase)
   - Authors (sorted alphabetically, normalized)
   - Venue (normalized)
   - Year

2. **Simplified Tracking**: Added `processed_paper_hashes: Set[str]` to `ConsolidationPhaseState` to track which papers have been processed

3. **Efficient Resume**: During resume, papers are filtered based on their hash before any API calls are made

## Implementation Details

### Hash Function
```python
def get_paper_hash(paper: Paper) -> str:
    """Generate a unique hash for a paper based on title, authors, venue, and year."""
    title = paper.title.lower().strip() if paper.title else ""

    # Sort and normalize author names
    authors = []
    if hasattr(paper, 'authors') and paper.authors:
        for author in paper.authors:
            if isinstance(author, dict):
                name = author.get('name', '').lower().strip()
            else:
                name = str(author).lower().strip()
            if name:
                authors.append(name)
    authors.sort()
    authors_str = ";".join(authors)

    venue = paper.venue.lower().strip() if paper.venue else ""
    year = str(paper.year) if paper.year else ""

    content = f"{title}|{authors_str}|{venue}|{year}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### Updated Resume Logic
The `harvest_identifiers_openalex` function now:
1. Accepts a `processed_hashes` parameter
2. Filters papers based on hash before processing
3. Updates progress for already-processed papers
4. Adds new hashes to the set after processing

### Fixed Issues
1. Added `__getattr__` to `LoggingSourceWrapper` to forward attribute access to the wrapped source
2. Updated checkpoint callbacks to pass both identifiers and processed hashes
3. Modified phase state serialization to include the hash set

## Results
Testing with a 10-paper dataset:
- Initial run: Processed 7 papers before interruption
- Resume: Successfully skipped 7 papers, only processed remaining 3
- Log output: "Skipping 7 papers already processed (hashes: 7)"

The system now efficiently resumes from checkpoints without making redundant API calls for already-processed papers.

## Benefits
1. **Simplicity**: Hash-based tracking is much simpler than complex object comparisons
2. **Efficiency**: Papers are filtered before any API calls
3. **Robustness**: Works regardless of paper_id presence or format
4. **Scalability**: Set-based hash lookup is O(1) even with thousands of papers
