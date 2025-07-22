# 2025-01-19 Connection Error Handling Improvements

## Request
User reported getting `ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))` during Phase 1 execution and requested better error handling.

## Solution
Implemented retry logic with exponential backoff for all HTTP requests in the consolidation pipeline:

### 1. OpenAlex Source
- Added `retry_on_connection_error` decorator with:
  - 3 retry attempts by default
  - Exponential backoff (1s, 2s, 4s delays)
  - Handles `ConnectionError`, `ConnectionResetError`, and `Timeout` exceptions
- Created `_make_request` method that wraps all HTTP calls with retry logic
- Updated all requests in `find_papers` and `fetch_all_fields` to use the retry wrapper

### 2. Semantic Scholar Source
- Added the same retry decorator
- Created `_make_get_request` and `_make_post_request` methods with retry logic
- Updated all HTTP calls to use these retry-enabled methods

### 3. Consolidate Command (Phase 2)
- Added inline retry logic for Semantic Scholar batch API calls
- Same retry pattern: 3 attempts with exponential backoff

## Implementation Details

### Retry Decorator
```python
def retry_on_connection_error(max_retries=3, backoff_factor=2, initial_delay=1):
    """Decorator to retry requests on connection errors with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, ConnectionResetError, Timeout) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Connection error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Connection error after {max_retries} attempts: {str(e)}")
```

### Error Handling Strategy
1. **Transient Errors**: Connection errors are retried automatically
2. **Persistent Errors**: After max retries, the error is logged and:
   - In Phase 1: Paper is marked as processed (won't retry on resume)
   - In Phase 2: Batch is skipped, continues with next batch
   - In Phase 3: Handled by the source's internal error handling

3. **Non-retryable Errors**: Other RequestExceptions are logged but not retried

## Benefits
1. **Resilience**: Temporary network issues won't crash the consolidation
2. **Transparency**: Users see retry attempts in logs
3. **Efficiency**: Failed papers are marked as processed to avoid infinite retries
4. **Graceful Degradation**: Partial failures don't stop the entire process

## Testing
Created basic test to verify consolidation still runs correctly with retry logic in place. The retry logic is transparent when there are no connection errors.

## Future Improvements
Could consider:
- Making retry parameters configurable via command line
- Adding circuit breaker pattern for persistent failures
- Collecting retry statistics for monitoring
