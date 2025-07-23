# 2025-01-23 - Fix: Max Papers Limit in Parallel Collection

## Issue

The `--max-papers` limit was not being respected in parallel collection mode:
- NeurIPS scraper correctly limited papers (already implemented)
- ICML (PMLR) scraper returned all 1828 papers instead of respecting the limit
- ICLR (OpenReview) scraper appeared stuck but was actually processing all papers

## Root Cause

1. **Worker Process**: The `VenueWorker` was not enforcing the `max_papers` limit from `config.batch_size`
2. **PMLR Scraper**: The `scrape_venue_year_iter()` method didn't check `batch_size`
3. **OpenReview Scrapers**: None of the iterator methods checked `batch_size`

## Solution Implemented

### 1. Worker Process (`parallel/worker.py`)

Added max_papers enforcement in two places:

```python
# In paper estimation
max_papers = self.config.batch_size if self.config.batch_size < 10000 else None
if max_papers and estimated_count > max_papers:
    estimated_count = max_papers

# In paper collection loop
for paper in scraper.scrape_venue_year_iter(self.venue, year):
    # ... send paper to queue ...
    paper_count += 1
    
    # Check if we've reached the max_papers limit
    if max_papers and paper_count >= max_papers:
        logger.info(f"Reached max_papers limit ({max_papers}), stopping")
        break
```

### 2. PMLR Scraper

Added batch_size limit to the iterator:

```python
# Apply batch size limit if configured
limit = len(paper_entries)
if self.config.batch_size < 10000:  # Reasonable batch size
    limit = min(self.config.batch_size, len(paper_entries))
    self.logger.info(f"Limiting to {limit} papers (batch_size={self.config.batch_size})")

for i, entry in enumerate(paper_entries[:limit]):
    # ... yield papers ...
```

### 3. OpenReview Scraper V2

Added paper counting and limit checking to all iterator methods:

```python
paper_count = 0
max_papers = self.config.batch_size if self.config.batch_size < 10000 else None

for submission in submissions:
    # ... process and yield paper ...
    paper_count += 1
    
    # Check batch size limit
    if max_papers and paper_count >= max_papers:
        self.logger.info(f"Reached batch_size limit ({max_papers})")
        return
```

## Testing

Verified the fix with a test collecting from 3 venues with `--max-papers 5`:
- NeurIPS: 5 papers ✓
- ICML: 5 papers ✓ 
- ICLR: 5 papers ✓

Total: 15 papers (correct, 5 per venue)

## Lessons Learned

1. **Consistency**: When implementing limits, ensure they're enforced at all levels (worker, scraper, iterator)
2. **Defense in Depth**: Having the limit check in the worker provides a safety net even if scrapers don't implement it
3. **Testing**: Always test with limits to catch these issues early

The parallel collection now correctly respects the `--max-papers` limit across all venues.