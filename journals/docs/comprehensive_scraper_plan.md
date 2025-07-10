# Comprehensive Scraper Implementation Plan

## Available Resources

### Package Data Sources
- `enhanced_openalex.py` - Enhanced OpenAlex API client
- `enhanced_semantic_scholar.py` - Enhanced Semantic Scholar client  
- `enhanced_crossref.py` - Enhanced Crossref client
- `google_scholar.py` - Google Scholar scraper
- `base.py` - Base classes for data sources

### Paperoni Scrapers
- `neurips.py` - NeurIPS proceedings scraper
- `openreview.py` / `openreview2.py` - OpenReview API clients
- `jmlr.py` - Journal of Machine Learning Research scraper
- `mlr.py` - MLR Press (PMLR) scraper
- `openalex.py` - OpenAlex scraper
- `semantic_scholar.py` - Semantic Scholar scraper
- `refine.py` - Paper refinement/enrichment
- `base.py` - Base scraper framework

## Priority Scrapers to Implement

### Group A: Conference Proceedings (Highest Priority)

#### 1. **CVF Scraper** (CVPR/ICCV/ECCV/WACV)
- **Mila Papers**: 16+ papers
- **Base Class**: New `ConferenceProceedingsScaper` 
- **Data Source**: https://openaccess.thecvf.com/
- **Strategy**: Browse year-specific proceedings pages, extract all papers
- **Implementation**: Custom scraper (no existing base available)

#### 2. **ACL Anthology Scraper** (ACL/EMNLP/NAACL/COLING)  
- **Mila Papers**: 12+ papers
- **Base Class**: New `ACLAnthologyScaper`
- **Data Source**: https://aclanthology.org/ + potential API
- **Strategy**: Use venue-specific endpoints, bulk download
- **Implementation**: API-first approach with HTML fallback

#### 3. **AAAI Scraper**
- **Mila Papers**: 14 papers
- **Base Class**: Extend from `base.py` 
- **Data Source**: https://aaai.org/conference/ (JavaScript heavy)
- **Strategy**: Selenium/Playwright for JS rendering
- **Implementation**: Browser-based scraper

#### 4. **IJCAI Scraper**
- **Mila Papers**: Strategic importance
- **Base Class**: `ConferenceProceedingsScaper`
- **Data Source**: https://www.ijcai.org/proceedings/
- **Strategy**: Year-based HTML parsing
- **Implementation**: Similar to CVF approach

### Group B: Enhanced API Clients (Medium Priority)

#### 5. **Enhanced OpenReview Scraper**
- **Base Class**: Extend paperoni's `openreview.py`
- **Enhancement**: Add bulk venue collection, better filtering
- **Data Source**: OpenReview API
- **Strategy**: Extend existing functionality for comprehensive collection

#### 6. **Enhanced PMLR Scraper**  
- **Base Class**: Extend paperoni's `mlr.py`
- **Enhancement**: Add bulk year/venue collection
- **Data Source**: PMLR proceedings API
- **Strategy**: Bulk collection by venue and year

### Group C: Journal Publishers (Medium Priority)

#### 7. **Nature Family Scraper**
- **Mila Papers**: 15+ papers (Nature Communications)
- **Base Class**: New `JournalPublisherScaper`
- **Data Source**: nature.com search API
- **Strategy**: Search by keywords, pagination
- **Implementation**: API-based with rate limiting

#### 8. **Medical Journals Scraper** 
- **Mila Papers**: 35+ papers across venues
- **Base Class**: `JournalPublisherScaper`
- **Data Source**: PubMed, Elsevier, etc.
- **Strategy**: Multi-source aggregation
- **Implementation**: Extend existing sources

### Group D: Digital Libraries (Lower Priority)

#### 9. **IEEE Xplore Enhanced Scraper**
- **Base Class**: Extend package's enhanced clients
- **Data Source**: IEEE Xplore API
- **Strategy**: Bulk conference/journal collection
- **Implementation**: API-based

#### 10. **ACM Digital Library Scraper**
- **Base Class**: New `DigitalLibraryScaper`
- **Data Source**: ACM DL search API
- **Strategy**: Conference and journal search
- **Implementation**: API-based

## Implementation Architecture

### Base Classes to Create

```python
# compute_forecast/data/sources/scrapers/
class ConferenceProceedingsScaper(BaseScaper):
    """Base for conference proceedings scrapers"""
    
class JournalPublisherScaper(BaseScaper):  
    """Base for journal publisher scrapers"""
    
class DigitalLibraryScaper(BaseScaper):
    """Base for digital library scrapers"""
    
class APIEnhancedScaper(BaseScaper):
    """Base for enhanced API clients"""
```

### Reusable Components

```python
# Venue-specific strategies
venue_strategies = {
    'CVF': ['cvf_scraper'],
    'ACL': ['acl_anthology_scraper'], 
    'OpenReview': ['enhanced_openreview'],
    'PMLR': ['enhanced_pmlr'],
    'Nature': ['nature_scraper', 'pubmed_fallback']
}

# Institution filtering
class InstitutionMatcher:
    """Dynamic institution matching for any venue"""
```

## Investigation Plan

For each scraper, investigate:

1. **Website Structure Analysis**
   - URL patterns and navigation
   - Pagination mechanisms  
   - Data format (HTML/JSON/API)
   - JavaScript requirements

2. **Data Extraction Points**
   - Paper metadata fields available
   - Author/affiliation information
   - Publication dates and venues
   - Citation counts

3. **Technical Constraints**
   - Rate limiting policies
   - Authentication requirements
   - Bot detection/blocking
   - Bulk download limits

4. **Implementation Strategy**
   - API vs HTML scraping
   - Base class to extend
   - Error handling approach
   - Caching strategy

## Next Steps

1. **Phase 1**: Investigate top 4 priority scrapers (CVF, ACL, AAAI, IJCAI)
2. **Phase 2**: Design base classes and common components  
3. **Phase 3**: Implement scrapers in priority order
4. **Phase 4**: Integration testing and validation
5. **Phase 5**: Performance optimization and monitoring

Each scraper will be investigated individually to determine the optimal implementation approach.