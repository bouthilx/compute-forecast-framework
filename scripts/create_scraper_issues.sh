#!/bin/bash

# Script to create all scraper milestone issues

echo "Creating scraper infrastructure issues..."

# Issue 2: Enhanced Data Models for Scraped Papers
gh issue create --title "Enhanced Data Models for Scraped Papers" --body "$(cat <<'EOF'
## Priority
Critical

## Estimate
M (4-6 hours)

## Dependencies
Issue #140 (Base Scraper Classes Framework)

## Description
Extend existing Paper models to handle scraped data, ensuring compatibility with paperoni and package data structures.

## Detailed Implementation

The implementation should include:

1. **ScrapedPaper Model**
   - Extends base Paper model with scraper-specific fields
   - Source tracking (scraper name, URL, timestamp)
   - Enhanced metadata (PDF URLs, keywords, session/track info)
   - Quality indicators (completeness score, extraction confidence)
   - Conversion methods for compatibility

2. **ScrapedAuthor Model**
   - Enhanced affiliation data (raw text, department, country)
   - Author position tracking
   - Corresponding author flag

3. **VenueMetadata Model**
   - Venue name variations and mappings
   - Publisher information
   - URL patterns for scraping
   - Scraping notes and tips

## Acceptance Criteria
- [ ] ScrapedPaper extends Paper with scraper-specific fields
- [ ] Conversion methods for compatibility with existing systems
- [ ] Enhanced author affiliation tracking
- [ ] Venue metadata management
- [ ] Data validation and quality scoring

## Implementation Location
`compute_forecast/data/sources/scrapers/models.py`
EOF
)" --label "work:implementation,domain:installation"

# Issue 3: Institution Filtering Wrapper
gh issue create --title "Institution Filtering Wrapper" --body "$(cat <<'EOF'
## Priority
Low

## Estimate
S (2-3 hours)

## Dependencies
Issue #141 (Enhanced Data Models)

## Description
Create thin wrapper around existing institution processing infrastructure (EnhancedOrganizationClassifier with 225+ institutions, fuzzy matching, and alias support) to provide unified filtering interface for scraped papers.

## Detailed Implementation

The wrapper should:

1. **Leverage Existing Infrastructure**
   - Use EnhancedOrganizationClassifier (225+ institutions)
   - Use EnhancedAffiliationParser (complex parsing)
   - No duplication of existing functionality

2. **Provide Simple Interface**
   - filter_papers_by_institutions() method
   - get_mila_papers() convenience method
   - get_benchmark_institution_papers() for common institutions
   - get_institution_statistics() for reporting

3. **Institution Confidence Tracking**
   - Store confidence scores on filtered papers
   - Support configurable confidence thresholds

## Acceptance Criteria
- [ ] Leverages existing EnhancedOrganizationClassifier (225+ institutions)
- [ ] Uses existing fuzzy matching and alias support
- [ ] Simple wrapper interface for scraper pipeline
- [ ] Convenience methods for common use cases
- [ ] No duplication of existing functionality
- [ ] Institution statistics reporting

## Implementation Location
`compute_forecast/data/sources/scrapers/institution_filter.py`
EOF
)" --label "work:implementation,domain:extraction"

# Issue 4: Robust Error Handling & Monitoring
gh issue create --title "Robust Error Handling & Monitoring" --body "$(cat <<'EOF'
## Priority
High

## Estimate
M (4-6 hours)

## Dependencies
Issue #140 (Base Scraper Classes Framework)

## Description
Implement comprehensive error handling, retry logic, and monitoring for all scrapers to ensure reliable long-running collection jobs.

## Detailed Implementation

1. **Error Classification System**
   - Network errors (timeouts, connection failures)
   - Parsing errors (HTML structure changes)
   - Rate limit errors (429 responses)
   - Authentication errors
   - Data validation errors

2. **Retry Logic**
   - Exponential backoff for network errors
   - Different strategies per error type
   - Maximum retry limits
   - Circuit breaker pattern

3. **Monitoring Infrastructure**
   - Error tracking and categorization
   - Success/failure statistics
   - Performance metrics (papers/second)
   - Progress reporting
   - Alert thresholds

4. **Rate Limiting**
   - Adaptive rate limiting based on errors
   - Per-source rate limit configuration
   - Backoff when hitting limits

## Acceptance Criteria
- [ ] Comprehensive error categorization and tracking
- [ ] Retry logic with exponential backoff
- [ ] Rate limiting with adaptive delays
- [ ] Performance monitoring and reporting
- [ ] Graceful error recovery without stopping entire collection
- [ ] Detailed logging for debugging

## Implementation Location
`compute_forecast/data/sources/scrapers/error_handling.py`
EOF
)" --label "work:implementation,domain:installation"

# Issue 5: IJCAI Conference Scraper
gh issue create --title "IJCAI Conference Scraper" --body "$(cat <<'EOF'
## Priority
High

## Estimate
M (4-6 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement IJCAI proceedings scraper - highest success rate target with 1,048+ papers immediately available.

## Technical Investigation Results
- **URL Pattern**: https://www.ijcai.org/proceedings/{year}/
- **Structure**: Direct PDF links with adjacent metadata
- **Complexity**: Low - static HTML, no JavaScript
- **Expected Papers**: ~500-700 per year

## Implementation Details

1. **Venue Support**
   - Single venue: "IJCAI"
   - Years: 2018-2024 confirmed available

2. **Data Extraction**
   - PDF URLs directly available
   - Title extraction from link text or nearby elements
   - Author extraction from surrounding text patterns
   - Paper ID from PDF filename

3. **Quality Assurance**
   - Metadata completeness scoring
   - Confidence scoring based on extraction method
   - Validation of required fields

## API Specification
```python
scraper = IJCAIScraper()
years = scraper.get_available_years("IJCAI")  # [2024, 2023, 2022, ...]
result = scraper.scrape_venue_year("IJCAI", 2024)
```

## Acceptance Criteria
- [ ] Successfully extracts 1,000+ papers from IJCAI 2024
- [ ] Parses paper titles, authors, and PDF URLs accurately
- [ ] Handles missing data gracefully
- [ ] Provides confidence scores for extracted data
- [ ] Supports multiple years (2018-2024)
- [ ] Rate limiting and error recovery

## Implementation Location
`compute_forecast/data/sources/scrapers/conference_scrapers/ijcai_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 6: ACL Anthology Scraper
gh issue create --title "ACL Anthology Scraper" --body "$(cat <<'EOF'
## Priority
High

## Estimate
L (6-8 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement ACL Anthology scraper for comprehensive NLP conference coverage (ACL, EMNLP, NAACL, COLING) with 465 venues available.

## Technical Investigation Results
- **URL Pattern**: https://aclanthology.org/volumes/{year}.{venue}-main/
- **Structure**: Structured entries with paper links
- **Complexity**: Medium - multiple volume types per conference
- **Coverage**: 465 different venues/workshops

## Implementation Details

1. **Venue Support**
   - Main venues: ACL, EMNLP, NAACL, COLING, EACL, CoNLL, SemEval, WMT
   - Volume types: main, short, demo, findings, workshop

2. **URL Patterns**
   - Main: /volumes/{year}.{venue}-main/
   - Short: /volumes/{year}.{venue}-short/
   - Findings: /volumes/{year}.{venue}-findings/

3. **Data Extraction**
   - Structured paper entries with consistent format
   - Direct PDF links available
   - Rich metadata including DOIs

## API Specification
```python
scraper = ACLAnthologyScraper()
venues = scraper.get_supported_venues()  # ["ACL", "EMNLP", "NAACL", ...]
result = scraper.scrape_venue_year("EMNLP", 2024)
```

## Acceptance Criteria
- [ ] Successfully scrapes major NLP venues (ACL, EMNLP, NAACL, COLING)
- [ ] Handles multiple volume types (main, short, findings, demo)
- [ ] Extracts structured metadata with high accuracy
- [ ] Supports 465+ venue variations
- [ ] Provides PDF URLs when available
- [ ] Robust error handling for missing volumes

## Implementation Location
`compute_forecast/data/sources/scrapers/conference_scrapers/acl_anthology_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 7: CVF Scraper (CVPR/ICCV/ECCV/WACV)
gh issue create --title "CVF Scraper (CVPR/ICCV/ECCV/WACV)" --body "$(cat <<'EOF'
## Priority
High

## Estimate
L (6-8 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement CVF (Computer Vision Foundation) scraper for comprehensive computer vision conference coverage with 12+ conferences and 40,000+ papers across years.

## Technical Investigation Results
- **URL Pattern**: https://openaccess.thecvf.com/{Conference}{Year}
- **Structure**: Well-organized proceedings pages
- **Papers**: 2,000+ per major conference
- **Schedule**: CVPR (annual), ICCV (odd years), ECCV (even years), WACV (annual)

## Implementation Details

1. **Venue Support**
   - CVPR: Annual conference
   - ICCV: Odd years only (2019, 2021, 2023)
   - ECCV: Even years only (2020, 2022, 2024)
   - WACV: Annual conference

2. **URL Construction**
   - Main proceedings: /{Conference}{Year}
   - Paper pages: /{Conference}{Year}/html/{paper_id}.html
   - PDFs: /{Conference}{Year}/papers/{paper_id}.pdf

3. **Data Extraction**
   - Index pages list all papers
   - Individual paper pages have full metadata
   - Direct PDF links available

## API Specification
```python
scraper = CVFScraper()
venues = scraper.get_supported_venues()  # ["CVPR", "ICCV", "ECCV", "WACV"]
years = scraper.get_available_years("ICCV")  # [2023, 2021, 2019, ...] - odd years only
result = scraper.scrape_venue_year("CVPR", 2024)
```

## Acceptance Criteria
- [ ] Successfully scrapes all 4 CVF conferences (CVPR, ICCV, ECCV, WACV)
- [ ] Respects conference schedules (ICCV odd years, ECCV even years)
- [ ] Extracts 2,000+ papers per major conference
- [ ] Handles workshop papers separately
- [ ] High extraction confidence for structured proceedings

## Implementation Location
`compute_forecast/data/sources/scrapers/conference_scrapers/cvf_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 8: Enhanced OpenReview Scraper
gh issue create --title "Enhanced OpenReview Scraper" --body "$(cat <<'EOF'
## Priority
High

## Estimate
M (4-6 hours)

## Dependencies
Issues #140, #141, paperoni OpenReview collector

## Description
Extend paperoni's OpenReview scraper for comprehensive venue collection beyond individual paper lookup.

## Current Limitations
- Paperoni's OpenReview focuses on individual paper discovery
- No bulk venue collection capability
- Limited to paper-by-paper lookups

## Enhancement Requirements

1. **Bulk Venue Collection**
   - Get all papers from a venue/year combination
   - Support for ICLR main conference
   - Support for workshop papers

2. **Integration with Paperoni**
   - Reuse existing OpenReview API client
   - Maintain data model compatibility
   - Extend rather than replace functionality

3. **Venue Coverage**
   - ICLR (main venue focus)
   - NeurIPS workshops hosted on OpenReview
   - Other ML workshops

## API Specification
```python
scraper = EnhancedOpenReviewScraper()
venues = scraper.get_available_venues()  # ICLR workshops, NeurIPS workshops, etc.
result = scraper.scrape_venue_year("ICLR", 2024)
result = scraper.scrape_venue_year("NeurIPS/Workshop", 2024)
```

## Acceptance Criteria
- [ ] Extends paperoni's OpenReview base functionality
- [ ] Collects all papers from ICLR main conference
- [ ] Handles workshop paper collection
- [ ] Maintains compatibility with existing paperoni data

## Implementation Location
`compute_forecast/data/sources/scrapers/enhanced_scrapers/openreview_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 9: Enhanced PMLR Scraper
gh issue create --title "Enhanced PMLR Scraper" --body "$(cat <<'EOF'
## Priority
High

## Estimate
M (4-6 hours)

## Dependencies
Issues #140, #141, paperoni MLR collector

## Description
Extend paperoni's PMLR scraper for comprehensive proceedings collection (ICML, AISTATS, UAI, COLT).

## Current Limitations
- Paperoni's MLR focuses on individual paper lookups
- No bulk proceedings collection
- Limited venue coverage

## Enhancement Requirements

1. **Bulk Proceedings Collection**
   - Get all papers from a volume
   - Map conferences to PMLR volume numbers
   - Support major ML conferences

2. **Venue Mapping**
   - ICML: Multiple volumes per year
   - AISTATS: Annual proceedings
   - UAI: Annual proceedings
   - COLT: Annual proceedings

3. **Integration Points**
   - Reuse paperoni's MLR client
   - Extend data models as needed
   - Maintain compatibility

## API Specification
```python
scraper = EnhancedPMLRScraper()
volumes = scraper.get_available_volumes()  # All PMLR proceedings
result = scraper.scrape_venue_year("ICML", 2024)
result = scraper.scrape_venue_year("AISTATS", 2024)
```

## Acceptance Criteria
- [ ] Extends paperoni's MLR base functionality
- [ ] Collects complete ICML proceedings (1,000+ papers per year)
- [ ] Handles AISTATS, UAI, COLT proceedings
- [ ] Maintains compatibility with existing paperoni data

## Implementation Location
`compute_forecast/data/sources/scrapers/enhanced_scrapers/pmlr_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 10: Nature Family Journal Scraper
gh issue create --title "Nature Family Journal Scraper" --body "$(cat <<'EOF'
## Priority
Medium

## Estimate
L (6-8 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement Nature journal family scraper for scientific publication coverage (Nature Communications, Scientific Reports, Nature Machine Intelligence).

## Target Journals
- Nature Communications (high Mila publication count)
- Scientific Reports
- Nature Machine Intelligence
- Nature Methods
- Nature Biotechnology

## Implementation Approach

1. **Search-Based Collection**
   - Use Nature API for search queries
   - Filter by keywords AND institution
   - Date range filtering

2. **Metadata Extraction**
   - Full abstracts available
   - Author affiliations in structured format
   - DOIs for all papers
   - Citation counts

3. **Access Considerations**
   - Some content may be paywalled
   - Focus on metadata and abstracts
   - Link to publisher page for full text

## API Specification
```python
scraper = NatureFamilyScraper()
papers = scraper.search_papers(
    journal="Nature Communications",
    keywords=["machine learning", "artificial intelligence"],
    year_range=(2019, 2024),
    institutions=["Mila", "MIT", "Stanford"]
)
```

## Acceptance Criteria
- [ ] Search-based collection for multiple Nature journals
- [ ] Institution-aware filtering during collection
- [ ] Handles pagination and rate limiting
- [ ] Extracts complete metadata including abstracts

## Implementation Location
`compute_forecast/data/sources/scrapers/journal_scrapers/nature_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 11: AAAI Scraper (JavaScript-Heavy)
gh issue create --title "AAAI Scraper (JavaScript-Heavy)" --body "$(cat <<'EOF'
## Priority
Medium

## Estimate
XL (8-12 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement AAAI scraper requiring JavaScript rendering for dynamic content proceedings.

## Technical Challenges
- **JavaScript Required**: Content loaded dynamically
- **Complex Navigation**: Multi-step process to reach papers
- **Session Management**: Requires maintaining state
- **Performance**: Slower due to browser automation

## Implementation Approach

1. **Browser Automation**
   - Use Selenium or Playwright
   - Headless browser configuration
   - JavaScript execution support

2. **Navigation Strategy**
   - Load main proceedings page
   - Navigate through session listings
   - Extract papers from dynamic content
   - Handle pagination

3. **Error Recovery**
   - Browser crash handling
   - Session timeout management
   - Retry with fresh browser instance

## API Specification
```python
scraper = AAAIScraper(use_browser=True)
scraper.configure_browser(headless=True, timeout=60)
result = scraper.scrape_venue_year("AAAI", 2024)
```

## Acceptance Criteria
- [ ] Uses Selenium/Playwright for JavaScript rendering
- [ ] Handles dynamic content loading
- [ ] Extracts 1,000+ papers per AAAI conference
- [ ] Robust error handling for browser automation
- [ ] Configurable browser options

## Implementation Location
`compute_forecast/data/sources/scrapers/conference_scrapers/aaai_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 12: Medical Journals Scraper
gh issue create --title "Medical Journals Scraper" --body "$(cat <<'EOF'
## Priority
Low

## Estimate
L (6-8 hours)

## Dependencies
Issues #140, #141, #143 (Base classes, Models, Error handling)

## Description
Implement medical journal scraper for specialized venues where Mila researchers publish.

## Target Journals
Based on Mila publication analysis:
- Radiotherapy and Oncology
- Journal of Pediatric Surgery
- Medical Physics
- Physics in Medicine & Biology
- Other specialized medical AI journals

## Implementation Approach

1. **PubMed Integration**
   - Use PubMed API for comprehensive coverage
   - Search by author affiliation
   - Filter by journal names

2. **Publisher-Specific Scrapers**
   - Elsevier journals
   - Springer medical journals
   - Open access medical journals

3. **Metadata Focus**
   - Abstracts and metadata only
   - Link to publisher for full text
   - Handle access restrictions gracefully

## API Specification
```python
scraper = MedicalJournalsScraper()
venues = ["Radiotherapy and Oncology", "Journal of Pediatric Surgery"]
papers = scraper.search_medical_papers(venues, year_range=(2019, 2024))
```

## Acceptance Criteria
- [ ] Covers top medical journals with Mila publications
- [ ] PubMed integration for comprehensive coverage
- [ ] Institution filtering for relevant papers
- [ ] Handles medical journal access restrictions

## Implementation Location
`compute_forecast/data/sources/scrapers/journal_scrapers/medical_scraper.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 13: Unified Collection Pipeline
gh issue create --title "Unified Collection Pipeline" --body "$(cat <<'EOF'
## Priority
Critical

## Estimate
L (6-8 hours)

## Dependencies
Issues #144, #145, #146, #147, #148 (IJCAI, ACL, CVF, OpenReview, PMLR scrapers)

## Description
Create unified pipeline orchestrating all scrapers with intelligent venue routing and institutional filtering.

## Core Components

1. **Scraper Registry**
   - Auto-discover available scrapers
   - Map venues to appropriate scrapers
   - Handle scraper capabilities

2. **Venue Router**
   - Intelligent routing based on venue name
   - Fallback strategies
   - Coverage reporting

3. **Parallel Execution**
   - Concurrent scraper execution
   - Resource management
   - Progress tracking

4. **Institution Filtering**
   - Apply filtering during or after collection
   - Configurable strategies
   - Performance optimization

## API Specification
```python
pipeline = UnifiedScraperPipeline()

collection_plan = {
    "venues": ["IJCAI", "ACL", "CVPR", "ICLR", "ICML", "Nature Communications"],
    "years": [2019, 2020, 2021, 2022, 2023, 2024],
    "institutions": ["Mila", "MIT", "Stanford", "CMU"]
}

results = pipeline.execute_collection(collection_plan)
# Returns: Dict[institution, List[ScrapedPaper]]
```

## Acceptance Criteria
- [ ] Routes venues to optimal scrapers automatically
- [ ] Collects 100,000+ papers across all venues
- [ ] Filters by institutions during collection
- [ ] Progress tracking and checkpoint/resume capability
- [ ] Comprehensive error reporting and recovery

## Implementation Location
`compute_forecast/data/sources/scrapers/unified_pipeline.py`
EOF
)" --label "work:implementation,domain:collection"

# Issue 14: Quality Validation & Deduplication
gh issue create --title "Quality Validation & Deduplication" --body "$(cat <<'EOF'
## Priority
High

## Estimate
M (4-6 hours)

## Dependencies
Issue #152 (Unified Collection Pipeline)

## Description
Implement data quality validation and deduplication across all collected papers.

## Validation Components

1. **Metadata Completeness**
   - Required fields check (title, authors, venue, year)
   - Field format validation
   - Quality scoring per paper

2. **Deduplication Strategy**
   - Title similarity matching
   - Author overlap detection
   - DOI/URL matching
   - Venue/year consistency

3. **Institution Validation**
   - Verify institution extraction accuracy
   - Flag low-confidence matches
   - Manual review queue for edge cases

4. **Quality Reporting**
   - Per-scraper quality metrics
   - Overall collection statistics
   - Problematic papers flagging

## API Specification
```python
validator = PaperQualityValidator()

# Validate collected papers
quality_report = validator.validate_papers(collected_papers)

# Deduplicate across sources
deduplicated_papers = validator.deduplicate_papers(collected_papers)
```

## Acceptance Criteria
- [ ] Metadata completeness scoring
- [ ] Cross-source deduplication (>95% accuracy)
- [ ] Institution affiliation validation
- [ ] Quality reporting and flagging
- [ ] <5% duplicate rate in final dataset

## Implementation Location
`compute_forecast/data/sources/scrapers/quality_validation.py`
EOF
)" --label "work:implementation,domain:testing"

# Issue 15: Performance Optimization
gh issue create --title "Performance Optimization" --body "$(cat <<'EOF'
## Priority
Medium

## Estimate
M (4-6 hours)

## Dependencies
Issue #152 (Unified Collection Pipeline)

## Description
Optimize scraper performance for large-scale collection operations.

## Optimization Areas

1. **Parallel Processing**
   - Multi-threaded scraper execution
   - Async I/O where possible
   - Resource pool management

2. **Caching Strategy**
   - Response caching for retries
   - Parsed data caching
   - Disk-based cache for large datasets

3. **Memory Management**
   - Streaming processing for large collections
   - Batch processing with memory limits
   - Garbage collection optimization

4. **Performance Monitoring**
   - Real-time metrics collection
   - Bottleneck identification
   - Performance regression detection

## API Specification
```python
pipeline = UnifiedScraperPipeline()
pipeline.configure_performance(
    parallel_scrapers=3,
    cache_size="10GB",
    batch_size=500
)
```

## Acceptance Criteria
- [ ] Parallel scraper execution
- [ ] Intelligent caching and retry logic
- [ ] Memory-efficient processing for 100,000+ papers
- [ ] Complete collection runs in <24 hours
- [ ] Monitoring and performance metrics

## Implementation Location
`compute_forecast/data/sources/scrapers/performance_optimization.py`
EOF
)" --label "work:implementation,domain:testing"

# Issue 16: Documentation & Testing Suite
gh issue create --title "Documentation & Testing Suite" --body "$(cat <<'EOF'
## Priority
Medium

## Estimate
M (4-6 hours)

## Dependencies
Issues #152, #153, #154 (Pipeline, Validation, Performance)

## Description
Create comprehensive documentation and testing suite for the scraper infrastructure.

## Documentation Components

1. **API Documentation**
   - Complete docstrings for all classes/methods
   - Usage examples for each scraper
   - Configuration reference

2. **User Guide**
   - Getting started guide
   - Scraper configuration
   - Troubleshooting guide
   - Performance tuning

3. **Developer Guide**
   - Adding new scrapers
   - Architecture overview
   - Testing guidelines

## Testing Components

1. **Unit Tests**
   - Individual scraper tests
   - Mock HTTP responses
   - Edge case handling

2. **Integration Tests**
   - End-to-end pipeline tests
   - Multi-scraper coordination
   - Error recovery scenarios

3. **Performance Tests**
   - Load testing
   - Memory usage profiling
   - Benchmarking suite

## Acceptance Criteria
- [ ] Complete API documentation
- [ ] Integration test suite covering all scrapers
- [ ] Performance benchmarking tests
- [ ] User guide for scraper configuration
- [ ] Example scripts for common use cases

## Implementation Locations
- Documentation: `docs/scrapers/`
- Tests: `tests/integration/scrapers/`
- Examples: `examples/scraper_usage/`
EOF
)" --label "work:writing,domain:testing"

echo "All issues created successfully!"

# Add all issues to milestone 21
echo "Adding all issues to milestone..."
for issue_num in {141..155}; do
    echo "Adding issue #$issue_num to milestone 21..."
    gh api repos/:owner/:repo/issues/$issue_num --method PATCH --field milestone=21
done

echo "Script complete!"