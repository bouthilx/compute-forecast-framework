# CVF Open Access Scraper Planning - Issue #87

## Timestamp: 2025-07-02 @ 14:30

### Analysis Request
Plan implementation of issue #87 (CVF Open Access Scraper) and verify codebase readiness.

### Investigation Process

1. **Issue Details**:
   - Implement scraper for CVF Open Access (CVPR, ICCV, ECCV conferences)
   - URL Pattern: `https://openaccess.thecvf.com/{venue}{year}/papers/{paper}.pdf`
   - Dependencies: #77 (PDF Framework) and #78 (Deduplication) - both CLOSED
   - Time estimate: S (2-3h)

2. **Codebase Analysis**:
   - PDF Discovery Framework exists at `src/pdf_discovery/core/`
   - Base collector interface (`BasePDFCollector`) provides required abstraction
   - Several collectors already implemented (PMLR, OpenReview, etc.) serve as patterns
   - NO existing CVF collector found

3. **Required Components Status**:
   - ✅ `BasePDFCollector` abstract class with `_discover_single()` method
   - ✅ `PDFRecord` data model for storing PDF metadata
   - ✅ Framework orchestration supporting parallel collectors
   - ✅ Venue database includes CVF conferences (CVPR, ICCV, ECCV)
   - ❌ CVF-specific collector implementation

### Implementation Plan

1. **Create CVF Collector** (`src/pdf_discovery/sources/cvf_collector.py`):
   - Inherit from `BasePDFCollector`
   - Source name: "cvf"
   - Confidence score: ~0.95 (direct source)

2. **Core Implementation**:
   - Map venue names to CVF format (e.g., "CVPR" → "CVPR", "ICCV" → "ICCV")
   - Construct proceedings URL for venue+year
   - Parse proceedings page to find paper by title match
   - Extract paper ID from proceedings
   - Build final PDF URL

3. **Key Methods**:
   - `_discover_single(paper: Paper) -> PDFRecord`
   - Helper methods for URL construction and title matching

4. **Testing Strategy**:
   - Unit tests for URL construction
   - Mock tests for proceedings parsing
   - Integration test with sample papers

### Outcome
All dependencies are satisfied and the codebase is ready for CVF collector implementation. The pattern is well-established from existing collectors, making this a straightforward implementation task within the 2-3 hour estimate.
