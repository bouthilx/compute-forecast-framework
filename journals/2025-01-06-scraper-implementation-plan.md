# Scraper Implementation Plan for Bulk Paper Collection

**Date**: 2025-01-06  
**Author**: Claude  
**Objective**: Implement dedicated scrapers for bulk paper collection from venues not covered by paperoni

## Scraper Module Architecture

```
compute_forecast/data/sources/scrapers/
├── base.py (existing)
│   └── BaseScaper class - foundation for all scrapers
├── conference_scrapers/
│   ├── __init__.py (todo)
│   ├── cvf_scraper.py (todo: CVPR, ICCV, ECCV, WACV)
│   ├── acl_anthology_scraper.py (todo: ACL, EMNLP, NAACL, COLING, CoNLL)
│   ├── aaai_scraper.py (todo: AAAI)
│   ├── ijcai_scraper.py (todo: IJCAI)
│   └── conference_base.py (todo: ConferenceProceedingsScaper)
├── journal_scrapers/
│   ├── __init__.py (todo)
│   ├── nature_scraper.py (todo: Nature Communications, Scientific Reports, Nature Machine Intelligence)
│   ├── medical_journals_scraper.py (todo: Radiotherapy and Oncology, Journal of Pediatric Surgery, Medical journals)
│   └── journal_base.py (todo: JournalPublisherScaper)
├── enhanced_api_scrapers/
│   ├── __init__.py (todo)
│   ├── enhanced_openreview.py (todo: ICLR, NeurIPS workshops, ICML workshops)
│   ├── enhanced_pmlr.py (todo: ICML, AISTATS, UAI, COLT)
│   └── api_base.py (todo: APIEnhancedScaper)
├── digital_library_scrapers/
│   ├── __init__.py (todo)
│   ├── ieee_xplore_scraper.py (todo: Various IEEE conferences)
│   ├── acm_dl_scraper.py (todo: Various ACM conferences)
│   └── library_base.py (todo: DigitalLibraryScaper)
└── paperoni_bridges/
    ├── __init__.py (todo)
    ├── neurips_bridge.py (existing via paperoni: NeurIPS)
    ├── openreview_bridge.py (existing via paperoni: ICLR base)
    ├── jmlr_bridge.py (existing via paperoni: JMLR)
    └── mlr_bridge.py (existing via paperoni: PMLR base)
```

## Implementation Analysis Summary

Based on investigation results from scripts/investigate_venue_scrapers.py:

### ✅ High Success Probability (Implement First)
1. **IJCAI Scraper** - 1,048 PDF links found, simple HTML parsing
2. **ACL Anthology Scraper** - 465 venues × 25 year collections, excellent structure
3. **CVF Scraper** - 12 conferences available, clear proceedings structure

### ⚠️ Medium Complexity
4. **Nature Scraper** - Search-based collection, pagination support
5. **Enhanced PMLR** - Extend paperoni's mlr.py for bulk collection
6. **Enhanced OpenReview** - Extend paperoni's openreview.py for comprehensive venue coverage

### ❌ High Complexity (Implement Last)
7. **AAAI Scraper** - JavaScript rendering required (Selenium/Playwright)
8. **Medical Journals** - Multi-source aggregation needed
9. **IEEE/ACM Digital Libraries** - Complex authentication and rate limiting

## Detailed Implementation Plan

### Phase 1: Foundation & Quick Wins (Week 1-2)

#### 1.1 Create Base Classes
```python
# conference_base.py
class ConferenceProceedingsScaper(BaseScaper):
    """Base for scraping conference proceedings pages"""
    
    def get_conference_years(self, venue: str) -> List[int]:
        """Get available years for a venue"""
        
    def get_papers_for_year(self, venue: str, year: int) -> List[Paper]:
        """Get all papers from a venue/year"""
        
    def parse_paper_metadata(self, paper_element) -> Paper:
        """Extract paper metadata from HTML element"""
```

#### 1.2 Implement IJCAI Scraper (Highest Success Rate)
- **Target**: 1,048 papers from IJCAI 2024 alone
- **Approach**: HTML parsing of proceedings pages
- **URL Pattern**: `https://www.ijcai.org/proceedings/{year}/`
- **Implementation**: Direct PDF link extraction + metadata parsing
- **Timeline**: 2-3 days

#### 1.3 Implement ACL Anthology Scraper  
- **Target**: 465 venues × multiple years = 10,000+ papers
- **Approach**: Volume-based collection via `/volumes/{year}.{venue}/`
- **Implementation**: Structured HTML parsing, no API needed
- **Timeline**: 3-4 days

### Phase 2: Major Conference Coverage (Week 3-4)

#### 2.1 Implement CVF Scraper
- **Target**: CVPR/ICCV/ECCV/WACV across multiple years
- **Approach**: Conference-specific proceedings browsing
- **URL Pattern**: `https://openaccess.thecvf.com/{CONFERENCE}{YEAR}`
- **Implementation**: Dynamic proceedings page parsing
- **Timeline**: 4-5 days

#### 2.2 Enhanced API Scrapers
- **Enhanced OpenReview**: Extend paperoni's openreview.py for bulk venue collection
- **Enhanced PMLR**: Extend paperoni's mlr.py for comprehensive year/venue coverage
- **Timeline**: 3-4 days each

### Phase 3: Journal & Complex Sources (Week 5-6)

#### 3.1 Nature Family Scraper
- **Target**: Nature Communications, Scientific Reports
- **Approach**: Search API + pagination
- **Implementation**: Keyword-based search with institutional filtering
- **Timeline**: 4-5 days

#### 3.2 AAAI Scraper (Most Complex)
- **Target**: AAAI conferences (requires JavaScript)
- **Approach**: Selenium/Playwright browser automation
- **Implementation**: Dynamic content scraping
- **Timeline**: 5-7 days

### Phase 4: Integration & Testing (Week 7)

#### 4.1 Unified Collection Interface
```python
class ComprehensiveScraperOrchestrator:
    """Orchestrate all scrapers for unified collection"""
    
    def collect_by_venues(self, venues: List[str], years: List[int]) -> List[Paper]:
        """Collect papers using optimal scraper for each venue"""
        
    def collect_by_institutions(self, institutions: List[str], years: List[int]) -> List[Paper]:
        """Collect papers with institution filtering"""
```

#### 4.2 Institution Filtering
```python
class InstitutionMatcher:
    """Dynamic institution matching for collected papers"""
    
    def extract_affiliations(self, paper: Paper) -> List[str]:
        """Extract all affiliations from paper metadata"""
        
    def is_target_institution(self, paper: Paper, target_institutions: List[str]) -> bool:
        """Check if paper has target institution affiliation"""
```

## Expected Coverage After Implementation

### Conference Papers (Estimated)
- **IJCAI**: 1,000+ papers per year × 6 years = 6,000+ papers
- **ACL Family**: 465 venues × avg 50 papers = 23,000+ papers  
- **CVF**: 4 conferences × avg 2,000 papers × 6 years = 48,000+ papers
- **AAAI**: 1,000+ papers per year × 6 years = 6,000+ papers
- **Enhanced OpenReview**: 5,000+ papers across workshops
- **Enhanced PMLR**: 10,000+ papers across proceedings

### Journal Papers (Estimated)  
- **Nature Family**: 500+ papers per journal
- **Medical Journals**: 1,000+ papers across venues

### Total Coverage Projection
- **Conference Papers**: ~90,000+ papers
- **Journal Papers**: ~5,000+ papers
- **Combined with Paperoni**: 95%+ venue coverage for Mila publication analysis

## Technical Implementation Strategy

### 1. Rate Limiting & Politeness
- Implement 1-2 second delays between requests
- Use session management for cookie persistence
- Respect robots.txt and site policies
- Implement exponential backoff for errors

### 2. Error Handling & Robustness
- Comprehensive exception handling for network issues
- Partial failure recovery (continue with other papers)
- Data validation and cleaning
- Checkpoint/resume capability for large collections

### 3. Data Quality & Validation
- Fuzzy matching for author name variations
- Institution name normalization
- Duplicate detection across sources
- Metadata completeness validation

### 4. Performance Optimization
- Parallel processing where appropriate
- Caching of proceedings pages
- Incremental updates for new papers
- Memory-efficient processing for large datasets

## Success Metrics

### Phase 1 Success Criteria
- IJCAI scraper: 1,000+ papers collected successfully
- ACL Anthology scraper: 10,000+ papers from major venues
- Zero critical errors during collection

### Phase 2 Success Criteria  
- CVF scraper: 40,000+ computer vision papers
- Enhanced API scrapers: 15,000+ additional papers
- Institution filtering accuracy >95%

### Phase 3 Success Criteria
- Nature scraper: 500+ journal papers
- AAAI scraper: 5,000+ AI conference papers
- Combined coverage >90% of Mila publication venues

### Final Success Criteria
- **Coverage**: 95%+ of venues where Mila researchers publish
- **Volume**: 100,000+ papers collected across all sources
- **Quality**: <5% duplicate rate, >95% metadata completeness
- **Performance**: Full collection runs in <24 hours
- **Integration**: Seamless combination with paperoni data

## Risk Mitigation

### Technical Risks
- **Website structure changes**: Implement robust selectors, regular testing
- **Rate limiting/blocking**: Use polite scraping, proxy rotation if needed
- **JavaScript requirements**: Selenium fallback for dynamic content

### Data Quality Risks
- **Inconsistent metadata**: Implement data cleaning pipelines
- **Missing affiliations**: Multiple extraction strategies
- **Duplicates**: Multi-field matching algorithms

### Timeline Risks
- **Complex venues take longer**: Start with easiest venues first
- **Unforeseen technical issues**: 25% buffer time in each phase
- **Dependency conflicts**: Use isolated environments

This plan provides a systematic approach to implementing comprehensive paper collection scrapers that will give us 95%+ coverage of venues where Mila researchers publish, complementing paperoni's existing capabilities.