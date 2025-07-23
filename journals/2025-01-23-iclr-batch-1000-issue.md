# 2025-01-23 - Root Cause: ICLR Pre-fetches 1000 Papers

## Discovery

The OpenReview `iterget_notes` function fetches papers in batches of **1000** before yielding any.

### Evidence

When requesting 10 papers:
```
[API CALL] get_notes called with: offset=0, limit=1000
[API RESPONSE] Returned 1000 notes  # Actually returned 1000!
```

Then it yields papers 1-10 from memory at ~5000 papers/second.

## Why This Matters

1. **Progress Bar**: Stays at 0% while fetching 1000 papers (~2 seconds)
2. **Then Jumps**: Processes requested papers instantly from memory
3. **Appears Broken**: User sees no progress, then sudden completion

## Comparison

- **NeurIPS**: Each paper requires HTTP request → natural delays → gradual progress
- **ICML**: Downloads HTML first, then parses → some initial delay, then gradual
- **ICLR**: Downloads 1000 papers → long initial delay → instant processing

## Solutions

### Option 1: Reduce Batch Size (Recommended)

Create our own iterator with smaller batches:
```python
def iterget_notes_streaming(client, batch_size=50, **kwargs):
    offset = 0
    while True:
        notes = client.get_notes(offset=offset, limit=batch_size, **kwargs)
        if not notes:
            break
        for note in notes:
            yield note
        offset += batch_size
```

### Option 2: Add Progress During Initial Fetch

Show a different progress bar during the initial API call:
- "Fetching paper metadata from OpenReview..."
- Then switch to per-paper progress

### Option 3: Accept Current Behavior

Document that ICLR fetches in large batches for efficiency.

## Impact

With Option 1 (batch_size=50):
- First paper appears after fetching only 50 papers (~0.1s)
- Progress updates every 50 papers
- Better user experience
- Slightly more API calls (but still efficient)

## Recommendation

Implement Option 1 with configurable batch size:
- Default: 50 for good UX
- Allow override for efficiency when needed
- Maintains streaming appearance while being efficient