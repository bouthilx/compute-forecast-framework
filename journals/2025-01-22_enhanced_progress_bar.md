# Enhanced Progress Bar for Download Command

**Date**: 2025-01-22
**Task**: Add detailed progress information with success/failed/broken counts

## Requirements

User requested an enhanced progress bar format:
```
% (n/total) DD HH:MM:SS (YYYY-MM-DD HH:MM:SS ETA) [success:n failed:n broken:n]
```

Where:
- `success`: Successfully downloaded PDFs
- `failed`: PDFs that failed but can be retried (temporary failures)
- `broken`: PDFs that failed and should not be retried (permanent failures)

## Implementation

### 1. Custom Progress Columns

Created two custom Rich progress columns:

**StatusColumn**: Shows the colored status counts
```python
[green]success:2[/green] [yellow]failed:1[/yellow] [red]broken:1[/red]
```

**DetailedProgressColumn**: Shows percentage, counts, elapsed time, and ETA
```python
75% (3/4) 00:02:45 (2025-01-22 15:35:00 ETA)
```

### 2. Enhanced Progress Manager

Updated `SimpleDownloadProgressManager` to:
- Track three types of failures: `completed`, `failed` (temporary), and `broken` (permanent)
- Pass failure type information through `complete_download(paper_id, success, permanent_failure=False)`
- Update progress bar with real-time counts

### 3. Integration with Orchestrator

Modified `DownloadOrchestrator` to:
- Use `_categorize_error()` to determine if failures are permanent
- Pass `permanent_failure` flag to progress manager
- Properly categorize errors:
  - HTTP 404, 403, 401 → Permanent (broken)
  - HTTP 5xx, timeouts, connection errors → Temporary (failed)

## Error Categories

**Permanent failures (broken)**:
- `http_404`: File not found
- `http_403`: Forbidden access
- `http_401`: Unauthorized
- `validation_error`: Invalid PDF file

**Temporary failures (failed)**:
- `http_server_error`: 500, 502, 503, 504
- `timeout`: Connection timeouts
- `connection_error`: Network issues
- `storage_error`: Local storage issues
- `other`: Unknown errors

## Final Summary

The enhanced summary now shows:
```
✓ Downloaded 2 papers successfully
⚠ Failed to download 1 papers (can retry)
✗ Failed to download 1 papers (permanent failures)
```

## Benefits

1. **Clear visibility** of download status during execution
2. **Differentiation** between retryable and permanent failures
3. **Better decision making** about whether to retry with `--retry-failed`
4. **Time awareness** with elapsed time and ETA
5. **Actionable information** for troubleshooting

## Testing

Tested with mixed success/failure scenarios:
- Successful downloads show in green
- Temporary failures (connection errors) show in yellow
- Permanent failures (404 errors) show in red
- Progress bar updates in real-time with all counts
