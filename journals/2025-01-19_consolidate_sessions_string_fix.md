# 2025-01-19 Fixed consolidate-sessions String Error

## Issue
The user reported an error when running `uv run compute-forecast consolidate-sessions list`:
```
Failed to load session consolidate_20250719_130002_0b49b8e6: 'str' object has no attribute 'get'
No consolidation sessions found.
```

## Root Cause
The error was occurring in the `find_resumable_sessions` method when trying to display the sources. The new two-phase consolidation format stores sources as `{"phase": "id_harvesting"}`, and the code was trying to call `list(sources_status.keys())` to get the sources list. However, in some edge cases, `sources_status` could be a string instead of a dict.

## Solution
Added two fixes:

1. **Edge case handling**: Added a check to handle the case where `sources_status` might be a string, converting it to a dict format.
2. **Proper source list extraction**: Based on the checkpoint format, extract sources appropriately:
   - For new phase format: Use the phase name as the source
   - For old format: Use the actual source names

## Result
The consolidate-sessions list command now works correctly:
```
                             Consolidation Sessions                             
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Session   ┃           ┃ Input     ┃        ┃          ┃           ┃ Last     ┃
┃ ID        ┃ Status    ┃ File      ┃ Papers ┃ Sources  ┃ Created   ┃ Checkpo… ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━┩
│ consolid… │ interrup… │ data/pap… │ 34657  │ id_harv… │ 2025-07-… │ 2025-07… │
│           │           │           │        │          │ 13:00     │ 13:06    │
└───────────┴───────────┴───────────┴────────┴──────────┴───────────┴──────────┘

1 resumable session(s) available.
```

## Summary
Fixed the string attribute error by properly handling the new phase-based checkpoint format and adding defensive programming for edge cases.