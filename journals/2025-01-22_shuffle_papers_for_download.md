# Shuffle Papers for Download

**Date**: 2025-01-22
**Task**: Add paper shuffling to distribute load across venue servers

## Problem

When downloading papers, we were processing them in order, which could result in:
- Multiple concurrent requests hitting the same venue server (e.g., all NeurIPS papers)
- Increased chance of rate limiting from a single server
- "RemoteDisconnected" errors when servers close connections

## Solution

Added shuffling of the papers list before parallel download begins:
```python
# Shuffle papers to distribute requests across different venue servers
shuffled_papers = papers.copy()
random.shuffle(shuffled_papers)
```

## Benefits

1. **Load Distribution**: Requests are spread across different venue servers (NeurIPS, ICML, ICLR, etc.)
2. **Reduced Rate Limiting**: Less likely to trigger rate limits on any single server
3. **Better Parallelism**: When using multiple workers, they're less likely to hit the same server simultaneously
4. **Fewer Connection Drops**: Reduces "RemoteDisconnected" errors from overwhelmed servers

## Implementation

- Import `random` module
- Create a copy of the papers list to avoid modifying the original
- Shuffle the copy before submitting to the thread pool
- Process shuffled list in parallel as before

This is a simple but effective optimization for large-scale paper downloads across multiple venues.
