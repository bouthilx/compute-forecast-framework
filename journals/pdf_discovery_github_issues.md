# GitHub Issues for PDF Discovery Infrastructure

**Timestamp**: 2025-01-01 10:45
**Title**: Ready-to-Create GitHub Issues for PDF Discovery Implementation

## Issue Templates

### Issue #75: [PDF-Core] Implement Base PDF Discovery Framework with Deduplication
**Labels**: enhancement, priority:critical, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: L (6-8h)

**Description**:
Create the foundational framework for PDF discovery that all collectors will use. This includes the core data models, deduplication logic, and version management.

**Acceptance Criteria**:
- [ ] Define PDFRecord data model with all necessary fields
- [ ] Implement paper deduplication by DOI, arXiv ID, and fuzzy title matching
- [ ] Create version tracking system for preprints vs published papers
- [ ] Build confidence scoring mechanism for PDF-paper matches
- [ ] Implement URL validation and normalization
- [ ] Add comprehensive logging and error handling
- [ ] Write unit tests with 90%+ coverage

**Technical Details**:
```python
@dataclass
class PDFRecord:
    paper_id: str
    pdf_url: str
    source: str
    discovery_timestamp: datetime
    confidence_score: float
    version_info: Dict[str, Any]
    validation_status: str
    file_size_bytes: Optional[int]
    license: Optional[str]
```

---

### Issue #76: [PDF-API-1] Implement Semantic Scholar PDF Collector
**Labels**: enhancement, priority:high, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Implement PDF discovery using Semantic Scholar's API, focusing on the `openAccessPdf` field.

**Acceptance Criteria**:
- [ ] Integrate with existing Semantic Scholar API client
- [ ] Extract PDF URLs from openAccessPdf field
- [ ] Handle batch requests efficiently
- [ ] Implement proper rate limiting
- [ ] Return standardized PDFRecord objects
- [ ] Add retry logic for failed requests
- [ ] Test with 100+ papers

---

### Issue #77: [PDF-API-2] Implement OpenAlex PDF Collector
**Labels**: enhancement, priority:high, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Implement PDF discovery using OpenAlex API's open access URLs.

**Acceptance Criteria**:
- [ ] Use open_access.oa_url field from OpenAlex
- [ ] Handle various OA status types
- [ ] Extract repository URLs
- [ ] Map to existing paper IDs
- [ ] Test with diverse publication types

---

### Issue #78: [PDF-API-3] Implement CORE API PDF Collector
**Labels**: enhancement, priority:medium, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Integrate CORE API for accessing 200M+ open access papers.

**Acceptance Criteria**:
- [ ] Register for CORE API access
- [ ] Implement search by DOI/title
- [ ] Extract direct PDF download links
- [ ] Handle CORE's specific metadata format
- [ ] Implement pagination for large result sets

---

### Issue #79: [PDF-Venue-1] Implement OpenReview PDF Scraper
**Labels**: enhancement, priority:high, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Build scraper for OpenReview (ICLR, NeurIPS 2023+) with full PDF access.

**Acceptance Criteria**:
- [ ] Use OpenReview API v2
- [ ] Handle conference/workshop distinction
- [ ] Extract main paper + supplementary PDFs
- [ ] Support bulk downloads
- [ ] Track paper versions/revisions

---

### Issue #80: [PDF-Venue-2] Implement ACL Anthology PDF Scraper
**Labels**: enhancement, priority:high, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Create scraper for ACL Anthology covering ACL, EMNLP, NAACL, etc.

**Acceptance Criteria**:
- [ ] Parse anthology IDs from paper metadata
- [ ] Construct PDF URLs using venue/year/ID pattern
- [ ] Handle legacy vs new URL formats
- [ ] Support workshop papers
- [ ] Validate URLs before returning

---

### Issue #81: [PDF-Preprint-1] Enhance arXiv PDF Miner
**Labels**: enhancement, priority:critical, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75

**Description**:
Improve arXiv integration with robust version handling and better search.

**Acceptance Criteria**:
- [ ] Fix existing arXiv parser bugs
- [ ] Implement version detection (v1, v2, etc.)
- [ ] Support multiple search strategies (title, author, abstract)
- [ ] Handle withdrawn papers appropriately
- [ ] Extract license information
- [ ] Add bulk download support

---

### Issue #82: [PDF-Dedup] Advanced Deduplication & Version Management System
**Labels**: enhancement, priority:critical, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: L (6-8h)
**Dependencies**: #75

**Description**:
Build sophisticated deduplication to handle papers appearing in multiple sources.

**Acceptance Criteria**:
- [ ] Implement multi-level deduplication strategy
- [ ] Handle workshop → conference paper progression
- [ ] Detect and merge different versions
- [ ] Create preference rules (published > preprint)
- [ ] Build manual review queue for ambiguous cases
- [ ] Generate deduplication report

**Technical Requirements**:
- Exact matching: DOI, arXiv ID, PubMed ID
- Fuzzy matching: Title (>95%), Authors (>85%)
- Version detection: arXiv versions, camera-ready, extended versions
- Output: Canonical paper ID → best PDF URL mapping

---

### Issue #83: [PDF-Valid] PDF Discovery Validation Pipeline
**Labels**: enhancement, priority:high, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75, #82

**Description**:
Create validation tools to ensure PDF URLs are correct and accessible.

**Acceptance Criteria**:
- [ ] Implement URL format validation
- [ ] Check HTTP headers without downloading
- [ ] Verify content-type is PDF
- [ ] Extract and validate first page
- [ ] Match paper title/authors with metadata
- [ ] Calculate confidence scores
- [ ] Flag suspicious matches for review

---

### Issue #84: [PDF-Monitor] PDF Discovery Monitoring Dashboard
**Labels**: enhancement, priority:medium, work:implementation, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75-83

**Description**:
Build real-time dashboard for monitoring PDF discovery progress.

**Acceptance Criteria**:
- [ ] Show discovery statistics by source
- [ ] Display deduplication metrics
- [ ] Track failed discoveries
- [ ] Implement manual review interface
- [ ] Add export functionality
- [ ] Create alerting for low coverage

---

### Issue #85: [PDF-Test] Comprehensive PDF Discovery Test Suite
**Labels**: enhancement, priority:high, work:testing, domain:extraction
**Milestone**: PDF Infrastructure
**Effort**: M (4-6h)
**Dependencies**: #75-83

**Description**:
Create extensive tests for the PDF discovery system.

**Test Scenarios**:
- [ ] Multi-version paper handling
- [ ] Workshop to conference progression
- [ ] Retracted paper detection
- [ ] URL stability over time
- [ ] Source priority validation
- [ ] Performance benchmarks
- [ ] Edge cases (special characters, long titles)

---

## Implementation Priority Order

### Critical Path (Must Have):
1. #75 - Core Framework (blocks everything)
2. #81 - arXiv Miner (highest coverage)
3. #76 - Semantic Scholar (good coverage)
4. #82 - Deduplication (essential for quality)

### High Priority (Should Have):
5. #79 - OpenReview (ICLR/NeurIPS)
6. #80 - ACL Anthology (NLP papers)
7. #77 - OpenAlex (broad coverage)
8. #83 - Validation Pipeline

### Medium Priority (Nice to Have):
9. #78 - CORE API
10. #84 - Monitoring Dashboard
11. #85 - Test Suite

## Parallel Work Assignments

### Developer 1 (Core Systems):
- Day 1-2: #75 (Core Framework)
- Day 3-4: #82 (Deduplication)
- Day 5: #83 (Validation)

### Developer 2 (API Integration):
- Day 1-2: #76 (Semantic Scholar)
- Day 3: #77 (OpenAlex)
- Day 4-5: #78 (CORE)

### Developer 3 (Scrapers):
- Day 1-2: #81 (arXiv)
- Day 3-4: #79 (OpenReview)
- Day 5: #80 (ACL Anthology)

### Developer 4 (Quality & Monitoring):
- Day 1-3: #85 (Test Suite)
- Day 4-5: #84 (Dashboard)

## Success Metrics

By end of implementation:
- 95%+ PDF discovery rate for Mila papers
- 90%+ PDF discovery rate for benchmark papers
- <1% false positive rate
- <5s average discovery time per paper
- 98%+ deduplication accuracy
