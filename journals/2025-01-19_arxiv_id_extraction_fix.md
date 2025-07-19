# 2025-01-19 Fixed ArXiv ID Extraction

## Issue
After processing 360 papers, no ArXiv IDs were being found, which was suspicious given that many ML papers are published on ArXiv.

## Investigation
Tested the OpenAlex API with a known ArXiv paper (Attention is All You Need) and found:
1. The ArXiv source ID in the code (`https://openalex.org/S2764455111`) was incorrect
2. The actual ArXiv source ID is `https://openalex.org/S4306400194`
3. Many ArXiv papers have `pdf_url` as null, so the existing regex wouldn't work
4. ArXiv IDs can be found in multiple places: DOIs, landing page URLs, and locations

## Solution
Implemented a comprehensive ArXiv ID extraction strategy:

### 1. Extract from DOI
Many ArXiv papers have DOIs like `10.48550/arxiv.1706.03762`:
```python
doi = ids.get('doi', '')
if 'arxiv' in doi.lower():
    match = re.search(r'arxiv\.(\d{4}\.\d{4,5})', doi.lower())
    if match:
        arxiv_id = match.group(1)
```

### 2. Extract from Primary Location
Check both landing_page_url and pdf_url:
```python
for url in [landing_url, pdf_url]:
    if url and 'arxiv.org' in url:
        match = re.search(r'arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})', url)
        if match:
            arxiv_id = match.group(1)
            break
```

### 3. Extract from All Locations
If not found in primary location, check all locations:
```python
for location in work.get('locations', []):
    landing_url = location.get('landing_page_url', '')
    if landing_url and 'arxiv.org' in landing_url:
        # Extract ID...
```

### 4. Updated Regex Pattern
Updated to handle both old format (1234.5678) and new format (2301.12345):
```regex
r'arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})'
```

## Benefits
1. **Multiple extraction methods**: Increases chances of finding ArXiv IDs
2. **DOI parsing**: Catches papers with ArXiv DOIs
3. **All locations checked**: Doesn't miss IDs in secondary locations
4. **Flexible regex**: Handles both old and new ArXiv ID formats

## Expected Results
With these fixes, the progress bar should now show ArXiv IDs being discovered:
- Before: `[DOI:234 ArXiv:0 OA:360 S2:0 PM:12]`
- After: `[DOI:234 ArXiv:89 OA:360 S2:0 PM:12]`

## Summary
Fixed the ArXiv ID extraction by implementing multiple detection methods and correcting the regex patterns, ensuring that ArXiv papers are properly identified during Phase 1.