# Issue #86: OpenAlex PDF Discovery Implementation Plan

**Date**: 2025-07-02
**Issue**: #86 - [PDF-OpenAlex] Implement OpenAlex Integration
**Time Estimate**: S (2-3h)

## Summary

This issue requires implementing OpenAlex integration for PDF discovery, using their API to find open access URLs for academic papers. The work involves creating a new PDF collector that integrates with the existing PDF discovery framework established in issues #77 and #78.

## Current Codebase State

### ✅ Prerequisites Met
- **Issue #77** (Base PDF Discovery Framework) - CLOSED
- **Issue #78** (Deduplication Engine) - CLOSED
- Both dependencies are complete, providing the foundation for adding new sources

### 📚 Existing Infrastructure

1. **PDF Discovery Framework** (`package/src/pdf_discovery/`)
   - `BasePDFCollector` abstract class that all sources must implement
   - `PDFRecord` and `DiscoveryResult` models
   - Parallel execution with progress tracking
   - Framework orchestrates multiple collectors

2. **Existing PDF Collectors**
   - Semantic Scholar collector (good template for implementation)
   - OpenReview, DOI Resolver, PMLR, PubMed Central
   - All follow consistent pattern with rate limiting and error handling

3. **OpenAlex Implementation** (`package/src/data/sources/`)
   - `openalex.py` - Basic OpenAlex API client for citation collection
   - `enhanced_openalex.py` - Enhanced version with better error handling
   - **Note**: These are for citation collection, NOT PDF discovery

### 🔧 What Needs Implementation

1. **New OpenAlex PDF Collector**
   - Create `package/src/pdf_discovery/sources/openalex_collector.py`
   - Extend `BasePDFCollector` class
   - Implement `_discover_single()` method
   - Support batch operations (`supports_batch = True`)

2. **Key OpenAlex API Fields**
   - `primary_location.pdf_url` - Primary PDF location
   - `best_oa_location.pdf_url` - Best open access PDF
   - `locations[].pdf_url` - All available PDF URLs
   - Institution filtering via `authorships[].institutions`

3. **Implementation Pattern** (based on Semantic Scholar collector)
   - API rate limiting (OpenAlex: 10 requests/second with API key)
   - Retry logic for failed requests
   - Confidence scoring based on match quality
   - Batch processing for efficiency

## Implementation Tasks

1. **Create OpenAlex PDF Collector** [HIGH]
   - Set up class structure following existing patterns
   - Configure API client with rate limiting
   - Implement paper lookup by DOI, title, and other identifiers

2. **Implement Batch Lookup** [HIGH]
   - Use OpenAlex batch API endpoints
   - Handle pagination for large result sets
   - Map responses back to original papers

3. **Extract OA URLs** [HIGH]
   - Parse `best_oa_location` and `primary_location` fields
   - Handle multiple PDF URLs per paper
   - Set appropriate confidence scores

4. **Add Institution Filtering** [MEDIUM]
   - Filter by Mila's institution ID in OpenAlex
   - Prioritize Mila-authored papers
   - Make filtering configurable

5. **Write Tests** [MEDIUM]
   - Unit tests for collector functionality
   - Mock API responses
   - Test error handling and rate limiting

6. **Framework Integration** [MEDIUM]
   - Add to PDF discovery framework initialization
   - Update documentation
   - Ensure proper registration with orchestrator

## Technical Considerations

- **API Key**: OpenAlex requires email in User-Agent or API key for polite access
- **Rate Limits**: 10 requests/second with key, lower without
- **Batch Size**: OpenAlex supports up to 200 works per request
- **Institution ID**: Mila's OpenAlex ID needed for filtering

## Success Criteria

- Collector successfully discovers PDF URLs from OpenAlex
- Batch processing works efficiently for large paper sets
- Institution filtering properly prioritizes Mila papers
- All tests pass with appropriate coverage
- Integration with PDF discovery framework is seamless

## Next Steps

Begin implementation starting with the basic collector structure, following the patterns established by existing collectors like Semantic Scholar.