# Scraper Implementation Plan for Missing Venues

## Overview

This document outlines the plan to implement scrapers for venues not covered by paperoni but important for Mila publications and benchmarking.

## Priority Classification

Based on Mila publication volume and strategic importance for benchmarking:

### Priority 1: High Impact (Many Mila Papers)
1. **CVF Scraper** (CVPR/ICCV/ECCV) - 16+ Mila papers
2. **AAAI Scraper** - 14 Mila papers
3. **ACL Anthology Scraper** (ACL/EMNLP/NAACL) - 12+ Mila papers
4. **Nature Communications Scraper** - 15 Mila papers

### Priority 2: Strategic Importance
5. **IJCAI Scraper** - Major AI conference for benchmarking
6. **Medical Journals Scraper** - 35+ Mila papers total (various venues)
7. **COLING Scraper** - Additional NLP coverage
8. **Additional CV Conferences** (BMVC, WACV) - Comprehensive CV coverage

### Priority 3: Comprehensive Coverage
9. **IEEE Xplore Enhanced Scraper** - General conference/journal coverage
10. **ACM Digital Library Scraper** - General conference/journal coverage
11. **Springer/Elsevier Scrapers** - Journal coverage
12. **ArXiv Enhanced Scraper** - Preprint coverage with venue linking

## Planned Scrapers by Implementation Group

### Group A: Conference Proceedings Platforms
```python
# Reusable base: ConferenceProceedingsScaper
scrapers = [
    'CVFScraper',        # cvf.thecvf.com (CVPR/ICCV/ECCV)
    'AAAIScraper',       # aaai.org proceedings
    'IJCAIScraper',      # ijcai.org proceedings
    'ACLAnthologyScraper' # aclanthology.org (ACL/EMNLP/NAACL/COLING)
]
```

### Group B: Journal Publishers
```python
# Reusable base: JournalPublisherScraper
scrapers = [
    'NatureScraper',     # nature.com (Nature, Nature Communications, etc.)
    'ElsevierScraper',   # sciencedirect.com (medical journals, etc.)
    'SpringerScraper',   # link.springer.com
    'WileyScraper',      # onlinelibrary.wiley.com
]
```

### Group C: Digital Libraries
```python
# Reusable base: DigitalLibraryScraper
scrapers = [
    'IEEEXploreScraper', # ieeexplore.ieee.org
    'ACMDLScraper',      # dl.acm.org
    'PMCScraper',        # PMC for biomedical papers
]
```

### Group D: Specialized Platforms
```python
# Custom implementations
scrapers = [
    'ArXivEnhancedScraper',  # arxiv.org with venue inference
    'OpenReviewScraper',     # openreview.net (extend paperoni's)
    'HALScraper',            # hal.science (French academic archive)
]
```

## Investigation Targets

For each scraper, we need to investigate:

1. **Website Structure**
   - URL patterns
   - Page structure/DOM elements
   - Pagination mechanism
   - Search functionality

2. **API Availability**
   - Official APIs
   - Rate limiting
   - Authentication requirements
   - Data format (JSON/XML/HTML)

3. **Data Extraction Points**
   - Paper metadata (title, authors, abstract, DOI)
   - Author affiliations
   - Publication dates
   - Citation information
   - PDF links

4. **Technical Considerations**
   - JavaScript rendering requirements
   - CAPTCHA/bot protection
   - IP blocking policies
   - Bulk download limitations

## Next Steps

1. **Phase 1**: Investigate Priority 1 scrapers (CVF, AAAI, ACL, Nature)
2. **Phase 2**: Check existing package PDF collectors for reusability
3. **Phase 3**: Design base scraper classes for each group
4. **Phase 4**: Implement scrapers in priority order
5. **Phase 5**: Integration testing and validation

## Implementation Notes

- Check existing package collectors first to avoid duplication
- Design for rate limiting and polite crawling
- Include robust error handling and retry logic
- Support both bulk collection and incremental updates
- Implement data validation and deduplication
- Add comprehensive logging and monitoring
