# Download Command Output File Fix

**Date**: 2025-01-22
**Task**: Fix download command to not modify input files

## Problem Identified

The download command was modifying the input JSON file in-place by adding download status fields:
- `pdf_downloaded: true` and `pdf_download_timestamp` for successful downloads
- `pdf_download_error` for failed downloads

This behavior was dangerous because:
1. It could corrupt the input file if interrupted during save
2. It caused data loss when files were truncated (as seen with papers-phase-1-v3.json)
3. It violated the principle of not modifying input data

## Investigation

Found that the issue was in `download.py`:
- The `save_papers_callback` function was updating papers with download status
- This callback was triggered every 10 downloads and at the end
- The updates were saved back to the **original input file**

This explains why:
- papers-phase-1-v2.json (44MB) was smaller than papers-phase-1.json (82MB)
- papers-phase-1-v3.json (36MB) was even smaller - truncated during a save operation

## Solution Implemented

Modified the download command to:
1. Added optional `--output` parameter for specifying output file
2. Modified `save_papers_callback` to only save when output file is specified
3. Updated `save_papers_to_file` to write to the output file, not input file
4. Preserved backward compatibility - if no output specified, no file is modified

## Usage

```bash
# Safe usage - input file is never modified
uv run compute-forecast download --papers input.json --output output.json

# Legacy usage - no file modification occurs
uv run compute-forecast download --papers input.json
```

## Benefits

1. **Data Safety**: Input files are never modified
2. **Interrupted Downloads**: Can't corrupt input data
3. **Clear Separation**: Input and output are separate files
4. **Backward Compatible**: Existing scripts still work
5. **Optional Output**: Users can choose whether to save status

## Testing

Verified that:
- With `--output`: Creates new file with download status
- Without `--output`: No files are modified
- Download tracking still works through state file
- All existing functionality preserved

## Recommendation

Always use the `--output` flag when you need to track download status in the papers file. This prevents accidental data loss from interrupted downloads.