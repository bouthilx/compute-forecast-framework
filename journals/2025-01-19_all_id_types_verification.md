# 2025-01-19 Verified and Fixed All ID Type Extractions

## Request
User asked to verify that all ID types are being extracted correctly, not just ArXiv IDs.

## Investigation
Tested OpenAlex API responses for different paper types and found:

1. **DOI**: Provided as full URL like `https://doi.org/10.1038/s41586-021-03819-2`
2. **ArXiv ID**: Not directly provided, must be extracted from DOIs or landing page URLs
3. **PMID**: Provided as URL like `https://pubmed.ncbi.nlm.nih.gov/34265844`
4. **PMCID**: Provided as URL like `https://www.ncbi.nlm.nih.gov/pmc/articles/8371605`
5. **MAG ID**: Provided as numeric value (Microsoft Academic Graph)
6. **OpenAlex ID**: Always provided as the work ID

## Issues Found and Fixed

### 1. PMID Extraction
- **Issue**: PMID was stored as full URL instead of just the ID number
- **Fix**: Extract the numeric ID from the URL
```python
if 'pubmed.ncbi.nlm.nih.gov/' in pmid:
    paper_ids.pmid = pmid.split('/')[-1]
```

### 2. PMCID Extraction
- **Issue**: PMCID wasn't being extracted at all
- **Fix**: Added extraction logic with proper PMC prefix
```python
if ids.get('pmcid'):
    pmcid = str(ids.get('pmcid'))
    if '/pmc/articles/' in pmcid:
        paper_ids.pmcid = 'PMC' + pmcid.split('/')[-1]
```

### 3. ArXiv ID Extraction (Previously Fixed)
- Multiple extraction methods from DOIs, landing pages, and locations
- Updated regex to handle both old (1234.5678) and new (2301.12345) formats

### 4. DOI Extraction
- Already working correctly, stripping the `https://doi.org/` prefix

### 5. MAG ID Extraction
- Working correctly, converting to string

## Verification Results
All ID extraction patterns tested and verified:
- ✓ DOI: Correctly strips URL prefix
- ✓ ArXiv: Extracts from multiple sources with flexible regex
- ✓ PMID: Extracts numeric ID from URL
- ✓ PMCID: Extracts ID with PMC prefix
- ✓ MAG: Stores as string
- ✓ OpenAlex: Always captured from work ID

## Progress Bar Display
The progress bar currently shows:
- DOI: DOI count
- ArXiv: ArXiv ID count
- OA: OpenAlex ID count
- S2: Semantic Scholar ID count (populated in Phase 2)
- PM: PubMed ID count

Note: PMCID is extracted but not shown in the progress bar to keep it concise.

## Summary
Verified and fixed all ID type extractions to ensure comprehensive identifier collection during Phase 1. The system now properly extracts and stores all available identifiers from OpenAlex responses.
