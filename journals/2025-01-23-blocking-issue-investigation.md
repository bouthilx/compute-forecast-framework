# Investigation of Blocking Issues in Parallel Collection
**Date**: 2025-01-23
**Title**: Analysis of ICLR (2019-2024) and ICML (2019-2020) Collection Blocking

## Issue Summary
User reported that ICLR (2019-2024) and ICML (2019-2020) appear stuck during parallel collection, while ICML 2021-2024 works fine.

## Investigation Findings

### 1. Scraper Assignment
- **ICLR**: Uses `OpenReviewScraperV2` 
- **ICML**: Uses `PMLRScraper`

### 2. ICLR Issues (OpenReviewScraperV2)

The OpenReviewScraperV2 has different code paths based on venue and year:
- **ICLR 2024+**: Uses `_get_accepted_by_venueid_iter` (API v2, optimized)
- **ICLR 2019-2023**: Uses `_get_conference_submissions_v1_iter` (API v1)

#### Potential Issue in _get_conference_submissions_v1_iter
Found a problematic pattern in the streaming implementation (lines 645-657):
```python
submissions_iter = tools.iterget_notes(self.client_v1, invitation=invitation)

# Test if we have any submissions by peeking at the iterator
first_submission = next(submissions_iter, None)
if first_submission:
    # Recreate iterator that includes the first item
    import itertools
    submissions_iter = itertools.chain(
        [first_submission], 
        tools.iterget_notes(self.client_v1, invitation=invitation)  # <-- ISSUE: Creates new API request
    )
```

This code creates a **second API request** to OpenReview, which could cause blocking if:
1. The API is rate-limited
2. The API is slow to respond
3. The second request gets queued behind other requests

#### Non-Streaming Methods Still Present
The non-streaming methods (`_get_tmlr_papers`, `_get_accepted_by_venueid`, `_get_conference_submissions_v1`, `_get_conference_submissions_v2`) still use `list()` to convert iterators to lists (lines 244, 299, 357, 449). While these aren't called in the streaming path, they indicate the codebase is in transition.

### 3. ICML Issues (PMLRScraper)

The PMLR scraper appears to be properly implemented:
- Has a correct streaming implementation in `scrape_venue_year_iter`
- No obvious `list()` conversions in the streaming path
- URLs for ICML 2019-2020 are accessible (volumes 97 and 119)

#### Possible Causes for ICML 2019-2020 Blocking:
1. **Large page sizes**: ICML proceedings pages can be very large (733KB for 2019, 1068KB for 2020)
2. **BeautifulSoup parsing**: Parsing large HTML files with BeautifulSoup can be slow
3. **Network issues**: Temporary network slowness or rate limiting from PMLR servers

### 4. Root Cause Analysis

The most likely cause of the blocking behavior is:

1. **For ICLR 2019-2023**: The double API request issue in `_get_conference_submissions_v1_iter` creates unnecessary load and potential blocking
2. **For ICML 2019-2020**: Large HTML page sizes combined with synchronous processing might appear as blocking

## Recommendations

### Immediate Fix for ICLR
Replace the problematic iterator recreation pattern with a proper peek-and-chain approach:
```python
# Better approach - only create iterator once
from itertools import chain, tee

submissions_iter = tools.iterget_notes(self.client_v1, invitation=invitation)
peek_iter, main_iter = tee(submissions_iter, 2)

try:
    first_submission = next(peek_iter)
    # We have submissions, use main_iter
    submissions_iter = main_iter
    self.logger.info(f"Found submissions using {invitation}")
    break
except StopIteration:
    # No submissions with this invitation
    continue
```

### For ICML Performance
1. Add progress logging for HTML parsing phase
2. Consider implementing streaming HTML parsing for very large pages
3. Add timeout handling for network requests

### General Improvements
1. Add more detailed progress logging to identify exactly where blocking occurs
2. Implement request timeouts across all scrapers
3. Add performance metrics to track API response times
4. Consider implementing a circuit breaker pattern for API calls

## Next Steps
1. Fix the double API request issue in OpenReviewScraperV2
2. Add detailed timing logs to identify bottlenecks
3. Test with smaller batch sizes to verify the issue
4. Monitor API response times and network performance