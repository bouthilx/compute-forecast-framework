# PDF Acquisition Implementation Plan

**Timestamp**: 2025-07-01 19:15
**Title**: High-Level Plan for Comprehensive PDF Acquisition Infrastructure

## Issue Summary

### Current State
- **Extraction success rate: 1.9%** (7 out of 362 benchmark papers)
- **Root cause**: Relying only on abstracts and metadata, not full paper content
- **Affiliation coverage: 7.7%** due to missing full text
- **M3-2 blocked**: Cannot proceed with analysis without computational requirements data

### Requirements
- **Target coverage: 95%+** of papers (excluding paywalled content)
- **Need full text** for:
  - Computational specifications (GPU hours, model sizes, etc.)
  - Author affiliations
  - Experimental details
  - Supplementary information

## Preliminary Acquisition Tests Results

### Test 1: Semantic Scholar API (40% coverage)
- Tested 20 papers using `openAccessPdf` field
- **Result**: 8/20 PDFs found (40%)
- **Sources**: Direct PDF links and ArXiv IDs

### Test 2: Basic Implementation (50% coverage)
- Implemented `PDFAcquisitionManager` with:
  - Semantic Scholar PDF source
  - ArXiv search (basic)
  - Unpaywall DOI resolver
- **Result**: 5/10 PDFs acquired (50%)
- **Issues**: ArXiv parser errors, 403 download failures

### Test 3: Venue Analysis
Using merged venue data from `visualize_venue_trends_merged.py`:
- **Total Mila papers**: 1,358
- **Top 6 venues**: 512 papers (37.7%)
  - NeurIPS: 152 papers
  - ICML: 122 papers
  - ICLR: 94 papers
  - TMLR: 54 papers
  - AAAI: 49 papers
  - EMNLP: 41 papers

## Comprehensive Implementation Plan

### Architecture Overview

```
PDFAcquisitionPipeline
├── VenueRouter          # Routes papers to appropriate sources
├── ConferenceSources    # Venue-specific implementations
│   ├── NeurIPS         # papers.nips.cc, neurips.cc, OpenReview
│   ├── ICML            # proceedings.mlr.press
│   ├── ICLR            # OpenReview API
│   ├── AAAI            # ojs.aaai.org
│   ├── ACL/EMNLP       # aclanthology.org
│   └── CVPR/ICCV       # openaccess.thecvf.com
├── GeneralSources       # Fallback sources
│   ├── ArXiv           # Enhanced multi-strategy search
│   ├── GoogleScholar   # Scholarly library + scraping
│   ├── DOIResolvers    # Unpaywall, CORE, BASE
│   └── WebSearch       # Last resort web scraping
└── PDFProcessor         # Download, verify, parse
```

### Implementation Phases

#### Phase 1: Top Conference Sources (2 days)
**Goal**: Cover 512 papers from top 6 venues

1. **NeurIPS Source** (4 hours)
   - Handle multiple sites by year
   - Parse proceedings pages
   - OpenReview integration for 2023+

2. **ICML/PMLR Source** (3 hours)
   - PMLR volume mapping
   - Search by author/title
   - Direct PDF construction

3. **ICLR/OpenReview Source** (3 hours)
   - OpenReview API client
   - Handle all years uniformly
   - Workshop papers included

4. **ACL Anthology Source** (3 hours)
   - EMNLP, ACL, NAACL support
   - Direct PDF URL construction
   - BibTeX parsing for metadata

5. **AAAI Source** (3 hours)
   - Navigate AAAI digital library
   - Handle authentication if needed
   - Fallback to ojs.aaai.org

#### Phase 2: Enhanced General Sources (1.5 days)
**Goal**: Add 300+ papers from other venues

1. **ArXiv Enhancement** (4 hours)
   - Fix parser bugs
   - Multiple search strategies
   - Author+year search
   - Abstract similarity matching

2. **Google Scholar Integration** (4 hours)
   - Scholarly library setup
   - Multiple PDF link extraction
   - Rate limiting and caching
   - Institutional repository links

3. **DOI Resolution Chain** (3 hours)
   - Unpaywall enhancement
   - CORE API integration
   - BASE search engine
   - CrossRef metadata

4. **Web Search Fallback** (3 hours)
   - DuckDuckGo API
   - PDF validation
   - Author homepage search
   - ResearchGate/Academia.edu

#### Phase 3: Specialized Sources (1 day)
**Goal**: Reach 95% coverage

1. **Journal Publishers** (4 hours)
   - Nature OA API
   - IEEE Xplore metadata
   - Elsevier/ScienceDirect
   - PubMed Central

2. **Preprint Servers** (2 hours)
   - bioRxiv/medRxiv
   - SSRN
   - OSF Preprints

3. **Institutional Repositories** (2 hours)
   - University OAI-PMH endpoints
   - Lab/group websites
   - Author personal pages

### Expected Coverage Timeline

| Phase | Duration | Papers Covered | Cumulative Coverage |
|-------|----------|----------------|-------------------|
| Current | - | 0 | 0% |
| Phase 1 | 2 days | 512 | 37.7% |
| Phase 2 | 1.5 days | 450 | 70.8% |
| Phase 3 | 1 day | 250 | 89.2% |
| Manual | 0.5 days | 80 | 95%+ |

### Technical Considerations

#### Rate Limiting Strategy
- Per-domain delays (2-5 seconds)
- Exponential backoff on 429s
- Concurrent requests limit (4-6)
- Polite user agent headers

#### Caching Architecture
- Local PDF cache by paper ID
- URL cache to avoid re-searching
- Metadata cache for parsed content
- Failed attempts tracking

#### Verification Pipeline
- PDF header validation
- File size checks (>10KB)
- Title/author matching
- Page count validation

#### Error Handling
- Graceful degradation
- Source fallback chain
- Detailed error logging
- Manual review queue

### Success Metrics

1. **Coverage Metrics**
   - Overall PDF acquisition: >95%
   - Top venue coverage: >90%
   - Failed attempts: <5%

2. **Performance Metrics**
   - Average acquisition time: <5s per paper
   - Cache hit rate: >80% on re-runs
   - Parallel efficiency: >70%

3. **Quality Metrics**
   - Correct PDF matches: >98%
   - Full text extraction: >95%
   - Affiliation extraction: >70%

### Risk Mitigation

1. **Technical Risks**
   - **403/429 errors**: Implement rotating headers, respect robots.txt
   - **Parser failures**: Multiple parser fallbacks (PyMuPDF, pdfplumber)
   - **Storage limits**: Compress PDFs, deduplicate

2. **Legal/Ethical Risks**
   - **Only access open content**: No paywall circumvention
   - **Respect rate limits**: Polite crawling
   - **Clear attribution**: Track PDF sources

3. **Time Risks**
   - **Scope creep**: Fixed time boxes per source
   - **Debugging delays**: Comprehensive logging
   - **Performance issues**: Early optimization

### Next Steps

1. **Immediate (Today)**
   - Fix ArXiv parser bug in current implementation
   - Test NeurIPS source on 20 papers
   - Set up OpenReview API access

2. **Tomorrow**
   - Implement top 3 conference sources
   - Test on 100 papers from each
   - Measure coverage improvement

3. **Day 3-4**
   - Complete remaining sources
   - Run on full benchmark corpus
   - Generate coverage report

4. **Day 5**
   - Manual acquisition for gaps
   - Final extraction run
   - Deliver results for M3-2

### Alternative Approach (If Time Constrained)

If full implementation proves too time-consuming:

1. **Focus on top 3 venues** (NeurIPS, ICML, ICLR) = 368 papers
2. **Use existing ArXiv** for additional ~200 papers
3. **Manual download** top 50 missing papers
4. **Accept 70-80% coverage** but ensure high quality

This would still represent a **35-40x improvement** over current 1.9% extraction rate.

### Conclusion

The PDF acquisition infrastructure is essential for meaningful computational requirement extraction. Without it, we cannot:
- Extract affiliations (currently 7.7%)
- Find computational specifications
- Validate SOTA claims
- Complete M3-2 analysis

The proposed implementation is ambitious but necessary. Even partial implementation (70-80% coverage) would dramatically improve our analysis capabilities.
