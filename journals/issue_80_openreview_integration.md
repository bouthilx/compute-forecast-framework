# Journal: OpenReview PDF Collector Integration

## 2025-07-02 - Implementation Planning for Issue #80

### Analysis Summary

**Issue**: Implement OpenReview API v2 integration for PDF collection
**Purpose**: Collect PDFs from ICLR, NeurIPS (2023+), COLM, and other conferences using OpenReview platform
**Expected Coverage**: 239+ Mila papers from ICLR (94), NeurIPS 2023-24 (134), COLM (11)

### Current Codebase State

#### What's Available:
1. **PDF Discovery Framework** (Issue #77 - CLOSED)
   - `BasePDFCollector` abstract class in `/package/src/pdf_discovery/core/collectors.py`
   - `PDFRecord` and `DiscoveryResult` models in `/package/src/pdf_discovery/core/models.py`
   - Framework for multi-source orchestration
   - Statistics tracking and timeout handling

2. **Deduplication Engine** (Issue #78 - CLOSED)
   - Deduplication logic exists in `/package/src/pdf_discovery/deduplication/`
   - Helps manage duplicate PDFs across sources

3. **Paper Model**
   - Has necessary fields: `title`, `authors`, `venue`, `year`
   - Multiple ID types supported (paper_id, openalex_id, arxiv_id)

#### What's Missing:
1. **openreview-py library** - Not installed in pyproject.toml
2. **venue_mappings.py** - File doesn't exist yet
3. **OpenReviewPDFCollector** implementation
4. **Tests** for the collector

### Implementation Plan

1. **Install Dependencies** (5 min)
   - Add openreview-py to pyproject.toml
   - Run uv sync to install

2. **Create Venue Mappings** (15 min)
   - Create `/package/src/pdf_discovery/sources/venue_mappings.py`
   - Map conference names to OpenReview venues
   - Handle year-specific variations

3. **Implement OpenReviewPDFCollector** (2-3 hours)
   - Inherit from BasePDFCollector
   - Implement _discover_single method
   - Add title-based search with fuzzy matching
   - Build PDF URL construction logic

4. **Add Fallback Search** (1 hour)
   - Implement author-based search when title fails
   - Handle special characters and variations

5. **Rate Limiting & Error Handling** (30 min)
   - Add exponential backoff
   - Handle API errors gracefully
   - Clear logging

6. **Testing** (1 hour)
   - Create mock API responses
   - Test various edge cases
   - Validate with real conference papers

### Key Technical Decisions

1. **API Version**: Using OpenReview API v2 at https://api2.openreview.net
2. **Search Strategy**: Title-first, author fallback
3. **URL Format**: `https://openreview.net/pdf?id={forum_id}`
4. **No Authentication**: Public API, no auth needed

### Risks & Mitigations

1. **Title Variations**: Papers may have slightly different titles on OpenReview
   - Mitigation: Use fuzzy matching with high threshold

2. **Rate Limits**: API may have undocumented rate limits
   - Mitigation: Implement exponential backoff

3. **Venue Mapping Complexity**: Different URL patterns by year
   - Mitigation: Comprehensive venue_mappings configuration

### Success Metrics
- 95%+ coverage for OpenReview-hosted papers
- Robust handling of title variations
- Clear error messages for failed discoveries
- Respects API rate limits

Total Estimated Time: 4-6 hours (M task as specified)