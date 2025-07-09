# Venue Scraper Consolidation Analysis

**Date**: January 9, 2025  
**Objective**: Group top 50 venues by platform/publisher to identify consolidated scrapers

## Executive Summary

Analysis of the top 50 venues reveals significant consolidation opportunities:
- **10 platform-based scrapers** can cover 35 venues (70%)
- **6 scrapers already exist**, covering 6 venues
- Only **4 new platform scrapers** needed to cover 29 additional venues
- Remaining 15 venues require individual scrapers or are paywalled

## Platform Groupings

### 1. PMLR (Proceedings of Machine Learning Research)
**Venues**: ICML, AISTATS, UAI, CoLLAs (Proceedings of 2nd Conference on Lifelong Learning Agents)
**Coverage**: 4 venues, 280+ papers
**Scraper**: MLRScraper (exists, needs extension)
**Implementation**: Extend existing MLRScraper to handle all PMLR venues

### 2. OpenReview
**Venues**: ICLR, COLM, TMLR, RLC
**Coverage**: 4 venues, 500+ papers  
**Scraper**: OpenReviewScraper (exists, needs extension)
**Implementation**: Extend to handle journal format (TMLR) and new conferences

### 3. ACL Anthology
**Venues**: ACL, EMNLP
**Coverage**: 2 venues, 200+ papers
**Scraper**: ACLAnthologyScraper (exists)
**Implementation**: Already complete

### 4. Computer Vision Foundation (CVF)
**Venues**: CVPR
**Coverage**: 1 venue, 100+ papers
**Scraper**: CVFScraper (exists)
**Implementation**: Already complete

### 5. NeurIPS
**Venues**: NeurIPS
**Coverage**: 1 venue, 300+ papers
**Scraper**: NeurIPSScraper (exists)
**Implementation**: Already complete

### 6. IEEE Xplore
**Venues**: ICRA, IROS, ICASSP, IEEE RA-L, ICC, IEEE Access, IEEE Transactions on Control of Network Systems, IEEE TKDE
**Coverage**: 8 venues, 150+ papers
**Scraper**: IEEEScraper (new)
**Implementation**: Single base scraper with venue-specific configurations

### 7. ACM Digital Library
**Venues**: SIGIR, SIGGRAPH Asia, ACM FAccT, ACM Computing Surveys, ACM TOSEM
**Coverage**: 5 venues, 50+ papers
**Scraper**: ACMScraper (new)
**Implementation**: Unified ACM DL scraper with access handling

### 8. Nature Portfolio
**Venues**: Nature, Scientific Reports, Communications Biology
**Coverage**: 3 venues, 150+ papers
**Scraper**: NatureScraper (new)
**Implementation**: Use Nature API with differentiation for open vs subscription

### 9. BMC/BioMed Central
**Venues**: Molecular Autism, BMJ Open
**Coverage**: 2 venues, 20+ papers
**Scraper**: BMCScraper (new)
**Implementation**: Standard BMC open access format

### 10. Frontiers
**Venues**: Frontiers in Neuroscience
**Coverage**: 1 venue, 15+ papers
**Scraper**: FrontiersScraper (new)
**Implementation**: Frontiers standard format

## Individual Venue Scrapers Needed

### High Priority (Open Access)
1. **AAAI** - 67 papers, unique OJS platform
2. **JMLR** - 28 papers, custom website
3. **AAMAS** - 11 papers, conference proceedings
4. **eLife** - 10 papers, unique platform
5. **Astrophysical Journal** - papers, AAS platform

### Medium Priority (Mixed Access)
6. **Cell Reports** - Cell Press platform
7. **Bioinformatics** - Oxford Academic
8. **Procedia Computer Science** - Elsevier
9. **iScience** - ScienceDirect

## Implementation Strategy

### Phase 1: Platform Extensions (6-8h)
- Extend MLRScraper for AISTATS, UAI, CoLLAs
- Extend OpenReviewScraper for COLM, TMLR, RLC

### Phase 2: Major Platform Scrapers (20-30h)
1. **IEEEScraper** - Cover 8 venues, highest ROI
2. **ACMScraper** - Cover 5 venues
3. **NatureScraper** - Cover 3 high-impact venues

### Phase 3: Specialized Platform Scrapers (15-20h)
1. **BMCScraper** - Medical/biology venues
2. **FrontiersScraper** - Neuroscience venue
3. **AAAIScraper** - Major AI conference
4. **JMLRScraper** - Classic ML journal

### Phase 4: Individual Venues (As Needed)
- Prioritize based on paper count and relevance
- Skip truly paywalled venues

## Code Architecture

```python
# Proposed structure for platform scrapers

class PlatformBaseScraper(BaseScraper):
    """Base class for multi-venue platform scrapers"""
    
    def get_venue_config(self, venue_name):
        """Get venue-specific configuration"""
        pass

class IEEEScraper(PlatformBaseScraper):
    """Handles all IEEE Xplore venues"""
    VENUE_CONFIGS = {
        "icra": {"collection": "conferences", "id": "ICRA"},
        "iros": {"collection": "conferences", "id": "IROS"},
        "ieee_access": {"collection": "journals", "id": "6287639"},
        # ...
    }

class ACMScraper(PlatformBaseScraper):
    """Handles all ACM Digital Library venues"""
    VENUE_CONFIGS = {
        "sigir": {"doi_prefix": "10.1145", "venue_id": "sigir"},
        "siggraph_asia": {"doi_prefix": "10.1145", "venue_id": "sa"},
        # ...
    }
```

## Registry Updates

```python
# Updated _venue_mapping in registry.py
_venue_mapping = {
    # Existing
    "neurips": "NeurIPSScraper",
    "icml": "MLRScraper",
    "iclr": "OpenReviewScraper",
    "acl": "ACLAnthologyScraper",
    "emnlp": "ACLAnthologyScraper",
    "cvpr": "CVFScraper",
    
    # Platform extensions
    "aistats": "MLRScraper",
    "uai": "MLRScraper",
    "collas": "MLRScraper",
    "colm": "OpenReviewScraper",
    "tmlr": "OpenReviewScraper",
    "rlc": "OpenReviewScraper",
    
    # New platform scrapers
    "icra": "IEEEScraper",
    "iros": "IEEEScraper",
    "icassp": "IEEEScraper",
    "ieee_ral": "IEEEScraper",
    "icc": "IEEEScraper",
    "ieee_access": "IEEEScraper",
    "ieee_tcns": "IEEEScraper",
    "ieee_tkde": "IEEEScraper",
    
    "sigir": "ACMScraper",
    "siggraph_asia": "ACMScraper",
    "acm_facct": "ACMScraper",
    "acm_computing_surveys": "ACMScraper",
    "acm_tosem": "ACMScraper",
    
    "nature": "NatureScraper",
    "scientific_reports": "NatureScraper",
    "communications_biology": "NatureScraper",
    
    "molecular_autism": "BMCScraper",
    "bmj_open": "BMCScraper",
    
    "frontiers_in_neuroscience": "FrontiersScraper",
    
    # Individual scrapers
    "aaai": "AAAIScraper",
    "jmlr": "JMLRScraper",
    "aamas": "AAMASScraper",
    "elife": "eLifeScraper",
    "astrophysical_journal": "AstrophysicalJournalScraper",
}
```

## ROI Analysis

### Highest ROI (Papers per Implementation Hour)
1. **MLRScraper extensions**: 280+ papers / 2h = 140 papers/hour
2. **OpenReviewScraper extensions**: 500+ papers / 3h = 167 papers/hour
3. **IEEEScraper**: 150+ papers / 8h = 19 papers/hour
4. **NatureScraper**: 150+ papers / 6h = 25 papers/hour

### Total Coverage with Platform Approach
- **10 platform scrapers** → 35 venues (70% of top 50)
- **5 individual scrapers** → 5 additional venues (10%)
- **Total**: 40 venues (80%) are implementable

## Benefits of Consolidation

1. **Code Reuse**: Single scraper handles multiple venues
2. **Maintenance**: Update once for platform changes
3. **Consistency**: Uniform data extraction across venues
4. **Error Handling**: Centralized retry/fallback logic
5. **Authentication**: Single auth handler per platform

## Risk Mitigation

1. **Platform Changes**: Monitor platform APIs/structures quarterly
2. **Access Restrictions**: Implement fallback strategies
3. **Rate Limiting**: Built-in delays and retry logic
4. **Venue Variations**: Flexible configuration system

## Conclusion

By implementing 4 new platform scrapers and extending 2 existing ones, we can cover 35 of the top 50 venues. This consolidated approach reduces implementation time from ~100 hours to ~35 hours while improving maintainability and coverage.

**Recommended Priority**:
1. Extend MLRScraper and OpenReviewScraper (quick wins)
2. Implement IEEEScraper (covers 8 venues)
3. Implement NatureScraper (high-impact venues)
4. Implement ACMScraper (computer science venues)
5. Add individual scrapers based on specific needs