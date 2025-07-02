# Issue #93: JMLR/TMLR Site Scraper Planning

**Date**: 2025-07-02
**Issue**: #93 - [PDF-JMLR] Implement JMLR/TMLR Site Scraper

## Analysis Summary

### Issue Requirements
- Implement a PDF collector for JMLR (Journal of Machine Learning Research) and TMLR (Transactions on Machine Learning Research)
- Expected to cover ~65 papers
- Time estimate: S (2-3h)
- Dependencies: #77 (Base PDF Discovery Framework) and #78 (Deduplication Engine) - both CLOSED

### URL Patterns
- JMLR: `https://jmlr.org/papers/v{volume}/{paper}.pdf`
- TMLR: `https://jmlr.org/tmlr/papers/`

### Current Codebase Status
✅ **All prerequisites are met:**
- Base PDF Discovery Framework exists (`src/pdf_discovery/core/`)
- BasePDFCollector interface is implemented
- PDFRecord data model is defined
- Deduplication engine is in place
- Other collectors (ArXiv, PMLR, etc.) provide implementation patterns

### Implementation Plan

1. **Create JMLR/TMLR Collector Class**
   - Inherit from `BasePDFCollector`
   - Initialize with source name "jmlr_tmlr"
   - Set appropriate timeout (default 60s should be fine)

2. **Implement Discovery Logic**
   - For JMLR papers:
     - Extract volume and paper ID from paper metadata
     - Construct URL using pattern: `https://jmlr.org/papers/v{volume}/{paper}.pdf`
   - For TMLR papers:
     - Scrape TMLR index page to find matching papers
     - Extract PDF URLs from the page

3. **Paper Identification Strategy**
   - Check paper venue/journal field for "JMLR" or "TMLR"
   - Use title matching for TMLR papers (since they don't have volume structure)
   - Handle edge cases (papers published in both venues, special issues, etc.)

4. **Testing Strategy**
   - Unit tests for URL construction logic
   - Unit tests for paper matching logic
   - Integration tests with real JMLR/TMLR URLs
   - Mock tests for HTML parsing

### Technical Considerations
- JMLR has a clean URL pattern based on volume/paper ID
- TMLR requires HTML parsing to find papers
- Both sites are generally stable and don't require authentication
- Should handle rate limiting gracefully (though not typically needed for these sites)

### Risk Assessment
- **Low risk**: Both sites have stable URL patterns
- **Medium complexity**: TMLR requires HTML parsing
- **Time estimate seems accurate**: 2-3 hours should be sufficient

## Next Steps
1. Create the collector implementation file
2. Implement JMLR URL construction
3. Implement TMLR HTML scraping
4. Add comprehensive tests
5. Verify integration with the discovery framework