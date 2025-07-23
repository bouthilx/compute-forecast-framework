# 2025-01-23 - ICLR Streaming Troubleshooting Plan

## Problem Statement

ICLR scraper with `--parallel` flag receives all data at once at the end, not streaming in real-time like NeurIPS and ICML scrapers.

## Key Observations

1. **Speed**: ICLR processes at 3000-5000 papers/second
2. **Timing**: All 10 papers collected in 1-2ms
3. **Progress**: Progress bar jumps from 0% to 100% instantly
4. **Comparison**: NeurIPS/ICML stream gradually due to network delays

## Hypothesis

The OpenReview API's `iterget_notes` might be:
1. Pre-fetching all results before yielding any
2. Using internal buffering/caching
3. Making a single bulk request instead of paginated requests

## Troubleshooting Plan

### Step 1: Add Detailed Timing Logs

Add timestamps at key points:
- When iterator is created
- When first API call is made
- When first result is received from API
- When first paper is yielded
- When each batch of 100 papers is received

### Step 2: Monitor Network Activity

Add logging to see:
- How many HTTP requests are made
- Size of each request/response
- Timing of requests

### Step 3: Test API Behavior Directly

Create minimal test that:
- Uses `iterget_notes` directly
- Logs each iteration with timestamp
- Tests with small limits (1, 10, 100)
- Compares with sequential `get_notes` calls

### Step 4: Analyze Iterator Implementation

Check if `iterget_notes`:
- Actually makes paginated requests
- Or downloads all data first
- Has any buffering parameters

### Step 5: Add Artificial Delays

If API returns all data at once, add:
- Small delay after each paper yield (0.01s)
- To simulate gradual streaming
- Only for display purposes

### Step 6: Compare API Versions

Test differences between:
- v1 API (ICLR 2019-2023)
- v2 API with efficient_iterget
- Different query parameters

## Implementation Order

1. **Immediate**: Add timing logs to understand exact behavior
2. **Quick test**: Create minimal API test to isolate issue
3. **If confirmed**: Document that OpenReview API pre-fetches data
4. **Optional fix**: Add artificial delays for better UX

## Expected Outcome

Either:
- Find a way to make OpenReview truly stream
- Document that bulk fetching is API behavior
- Add artificial delays for better progress display