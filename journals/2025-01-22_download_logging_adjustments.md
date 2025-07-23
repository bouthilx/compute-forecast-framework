# Download Command Logging Adjustments

**Date**: 2025-01-22
**Task**: Adjust logging levels for expected failure scenarios

## Changes Made

1. **Fixed datetime.timedelta import error** in progress bar
   - Changed `datetime.timedelta()` to `timedelta()` since we imported it directly

2. **Adjusted logging levels** from WARNING/ERROR to INFO for:
   - Retry attempts: "Attempt X failed, retrying in Ys"
   - Non-retryable errors: "Non-retryable error or max retries reached"
   - Failed downloads: "Failed to download PDF for paper_id"

## Rationale

These are expected scenarios that we handle gracefully:
- Retries are normal for network operations
- Non-available content (404s, 403s) are expected for some papers
- We track all failures in the state file and report them properly

Using INFO level reduces log noise while still providing visibility when verbose mode is enabled.

## Result

Cleaner logs that focus on actual unexpected errors rather than handled failure cases.
