# 2025-01-19: Fix consolidate-sessions list command error

## Issue
The `cf consolidate-sessions list` command was failing with error:
```
AttributeError: 'str' object has no attribute 'get'
```

## Analysis
Investigation revealed that the consolidate command was updated to use a two-phase approach with phase tracking, storing phase information differently than expected by the `find_resumable_sessions` method:

- **Old format**: Sources with status dictionaries (e.g., `{"semantic_scholar": {"status": "completed"}}`)
- **New format**: Phase tracking (e.g., `{"phase": "id_harvesting"}`)

The error occurred because the code was trying to call `.get("status")` on string values in the new format.

## Solution
Updated the `ConsolidationCheckpointManager.find_resumable_sessions` method to handle both checkpoint formats:

1. Added detection for the new phase-based format
2. Implemented appropriate status mapping for phase values
3. Maintained backward compatibility with the old format

The fix properly maps phase values to session statuses:
- "completed" → completed
- Active phases ("id_harvesting", "semantic_scholar_enrichment", etc.) → interrupted
- Between-phase states ("id_harvesting_complete", etc.) → interrupted
- Others → pending

## Testing
Verified the fix works correctly:
- `cf consolidate-sessions list` now displays sessions properly
- `cf consolidate-sessions list --all` also works as expected
- The command correctly shows resumable sessions with phase information

## Outcome
The consolidate-sessions list command now handles both old and new checkpoint formats, providing users with proper session management capabilities for the two-phase consolidation process.