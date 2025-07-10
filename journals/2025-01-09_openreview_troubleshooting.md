# OpenReview API Troubleshooting

**Date**: January 9, 2025  
**Task**: Debug and fix OpenReview API integration returning 0 papers  
**Duration**: ~1 hour

## Summary

Successfully debugged and fixed the OpenReview adapter that was returning 0 papers for all venues. The issue was caused by changes in the OpenReview API response format where all content fields are now wrapped in dictionaries with 'value' keys.

## Key Findings

### 1. **API Response Format Change**
The OpenReview API now returns content fields as dictionaries:
```python
# Old format:
content = {
    'title': 'Paper Title',
    'authors': ['Author 1', 'Author 2'],
    'pdf': '/pdf/123.pdf'
}

# New format:
content = {
    'title': {'value': 'Paper Title'},
    'authors': {'value': ['Author 1', 'Author 2']},
    'pdf': {'value': '/pdf/123.pdf'}
}
```

### 2. **TMLR Invitation Format**
- TMLR accepted papers use `TMLR/-/Accepted` invitation, not `TMLR/-/Paper`
- TMLR has 2,509 accepted papers as of Jan 2025
- Papers span 2022-2025

### 3. **Working Invitations**
- ICLR 2024: `ICLR.cc/2024/Conference/-/Submission` (7,404 papers)
- TMLR: `TMLR/-/Accepted` (2,509 papers)
- COLM 2024: `colmweb.org/COLM/2024/Conference/-/Submission`
- RLC 2024: `rl-conference.cc/RLC/2024/Conference/-/Submission`

### 4. **ICLR 2023 Issue**
- ICLR 2023 returns 0 papers with all tested invitation formats
- Possible that the venue ID format changed or data is not available

## Fixes Applied

### 1. **Added `_extract_value()` Helper Method**
```python
def _extract_value(self, field):
    """Extract value from OpenReview field which can be a dict with 'value' key or direct value."""
    if isinstance(field, dict) and 'value' in field:
        return field['value']
    return field
```

### 2. **Updated Field Extraction**
- Modified all content field extractions to use `_extract_value()`
- Updated PDF URL extraction to handle new format

### 3. **Fixed TMLR Invitation**
- Changed from `TMLR/-/Paper` to `TMLR/-/Accepted`
- This properly retrieves accepted TMLR papers

### 4. **Fixed API Call Issues**
- Corrected usage of `get_all_notes()` which returns a list, not a generator
- Removed incorrect `limit` parameter

## Results

### Papers Successfully Retrieved
- **ICLR 2024**: 100 papers (limited by batch size)
- **TMLR 2023**: 100 papers (limited by batch size)
- **COLM 2024**: 100 papers (limited by batch size)
- **RLC 2024**: 100 papers (limited by batch size)
- **ICLR 2023**: 0 papers (API issue)

### CLI Integration Verified
```bash
# Successfully collected TMLR papers
compute-forecast collect --venue tmlr --year 2023 --output test.json --max-papers 10
```

## Technical Notes

### API Observations
1. The OpenReview API now includes progress bars during data retrieval
2. Different venues use different invitation patterns
3. Some venues return very large datasets (7,404 papers for ICLR 2024)
4. The batch size parameter properly limits the number of papers retrieved

### Unit Tests
All 11 unit tests continue to pass after the fixes.

## Next Steps

1. **Investigate ICLR 2023**: Determine why this specific year returns no results
2. **Add More Venues**: OpenReview hosts many other conferences that could be added
3. **Performance Optimization**: Consider caching for frequently accessed venues
4. **Error Handling**: Add better error messages for venues with no data

## Conclusion

The OpenReview adapter is now fully functional for ICLR 2024, TMLR, COLM, and RLC venues. The fix properly handles the new API response format and retrieves papers successfully. The integration with the CLI is working as expected.