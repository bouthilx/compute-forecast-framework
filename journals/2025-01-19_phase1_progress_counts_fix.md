# 2025-01-19 Fixed Phase 1 Progress Bar to Show Absolute Counts

## Issue
The Phase 1 progress bar was showing 0% for all ID types, which seemed suspicious. The user requested switching from percentages to absolute counts for better debugging visibility.

## Root Cause
The Phase1ProgressColumn was initialized with a reference to an empty dictionary (or phase_state.identifiers_collected), but when harvest_identifiers_openalex returned a new dictionary, the progress column was still referencing the old, empty dictionary.

## Solution
1. **Changed to absolute counts**: Replaced percentages with raw counts for each ID type
2. **Fixed reference issue**: 
   - Modified Phase1ProgressColumn to not require identifiers in constructor
   - Added `set_identifiers()` method to update the reference
   - Updated the checkpoint callback to call `phase1_column.set_identifiers()` with current identifiers
   - Set initial identifiers if resuming from checkpoint

## New Format
The progress bar now shows:
```
5.2% (52/1000) 00:02:45 (2025-01-19 15:32:10) [DOI:44 ArXiv:8 OA:52 S2:0 PM:2]
```

This shows absolute counts instead of percentages, making it easier to:
- See that identifiers are actually being found
- Debug if certain ID types are missing
- Track exact numbers for reporting

## Technical Details
- The checkpoint callback now updates the progress column's identifier reference on each batch
- This ensures the progress display always shows current counts
- When resuming, existing identifiers are loaded into the progress column

## Summary
Fixed the progress bar to show meaningful ID counts by ensuring the progress column always has access to the current identifiers dictionary, not an outdated reference.