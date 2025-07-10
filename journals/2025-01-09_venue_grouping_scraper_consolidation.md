# Venue Grouping and Scraper Consolidation Analysis

**Date**: January 9, 2025
**Task**: Group venues by common platforms to minimize scraper implementation
**Analyst**: Claude

## Executive Summary

By grouping venues by their common platforms, we can reduce the number of scrapers needed from 37 individual implementations to **15 consolidated scrapers** that would support all feasible venues from the top 50.

## Consolidated Scraper List

### 1. **PMLR Scraper** (Extends existing MLRScraper)
**Venues Supported (4):**
- ICML ✅ (already implemented)
- AISTATS
- UAI
- Proceedings of 2nd Conference on Lifelong Learning Agents (CoLLAs)

**Common Pattern:** All use https://proceedings.mlr.press/v{volume}/

---

### 2. **OpenReview Scraper** (Extends existing)
**Venues Supported (4):**
- ICLR ✅ (already implemented)
- COLM
- TMLR (also has jmlr.org site)
- RLC (Reinforcement Learning Conference)

**Common Pattern:** All use https://openreview.net/group?id={venue}

---

### 3. **IEEE Xplore Scraper** (New base scraper)
**Venues Supported (8):**
- ICRA
- IROS
- ICASSP
- ICC
- IEEE Robotics and Automation Letters (RA-L)
- IEEE Transactions on Control of Network Systems
- IEEE Transactions on Knowledge and Data Engineering
- IEEE TPAMI

**Common Pattern:** All use https://ieeexplore.ieee.org/

---

### 4. **ACM Digital Library Scraper** (New base scraper)
**Venues Supported (5):**
- SIGIR
- SIGGRAPH Asia
- ACM FAccT
- ACM Computing Surveys
- ACM TOSEM

**Common Pattern:** All use https://dl.acm.org/

---

### 5. **Nature Portfolio Scraper** (New base scraper)
**Venues Supported (3):**
- Nature (main journal)
- Scientific Reports
- Communications Biology

**Common Pattern:** All use nature.com subdomain structure

---

### 6. **BMC Platform Scraper** (New)
**Venues Supported (1):**
- Molecular Autism

**Note:** Could be extended to other BMC journals in future

---

### 7. **Frontiers Platform Scraper** (New)
**Venues Supported (1):**
- Frontiers in Neuroscience

**Note:** Could support all Frontiers journals

---

### 8. **Cell Press Scraper** (New)
**Venues Supported (2):**
- Cell Reports
- iScience

**Common Pattern:** Both use cell.com platform

---

### 9. **Oxford Academic Scraper** (New)
**Venues Supported (1):**
- Bioinformatics

**Note:** Could support other Oxford journals

---

### 10. **CVF Scraper** ✅ (Already implemented)
**Venues Supported (4):**
- CVPR ✅
- ICCV (if in top venues)
- ECCV (if in top venues)
- WACV (if in top venues)

---

### 11. **ACL Anthology Scraper** ✅ (Already implemented)
**Venues Supported (4+):**
- ACL ✅
- EMNLP ✅
- NAACL (if needed)
- COLING (if needed)

---

### 12. **AAAI Scraper** (New)
**Venues Supported (1):**
- AAAI

**Note:** Standalone due to unique structure at ojs.aaai.org

---

### 13. **JMLR Scraper** (New)
**Venues Supported (2):**
- JMLR
- TMLR (secondary access point)

**Common Pattern:** Both hosted at jmlr.org

---

### 14. **AAMAS Scraper** (New)
**Venues Supported (1):**
- AAMAS

**Note:** Uses ifaamas.org proceedings

---

### 15. **Specialized Scrapers** (New)
**Individual venues requiring custom implementation:**
- BMJ Open (bmjopen.bmj.com)
- eLife (elifesciences.org)
- IEEE Access (ieeeaccess.ieee.org)
- Astrophysical Journal (AAS journals)
- Procedia Computer Science (ScienceDirect open access)

---

## Implementation Priority Matrix

### 🎯 **Tier 1: Highest ROI** (Minimal effort, maximum venues)
1. **Extend PMLR Scraper** → +3 venues (AISTATS, UAI, CoLLAs)
2. **Extend OpenReview Scraper** → +3 venues (COLM, TMLR, RLC)
3. **Implement JMLR Scraper** → +2 venues (JMLR, TMLR secondary)

**Total: 3 scrapers → 8 venues**

### 🔧 **Tier 2: Platform Scrapers** (One scraper, multiple venues)
4. **IEEE Xplore Scraper** → 8 venues (requires subscription/API)
5. **ACM DL Scraper** → 5 venues (requires subscription/API)
6. **Nature Portfolio Scraper** → 3 venues (API available)
7. **Cell Press Scraper** → 2 venues (open access)

**Total: 4 scrapers → 18 venues**

### 📋 **Tier 3: Individual Scrapers** (One scraper, one venue)
8. **AAAI Scraper** → 1 venue (high impact)
9. **AAMAS Scraper** → 1 venue
10. **BMJ Open Scraper** → 1 venue
11. **eLife Scraper** → 1 venue
12. **Other specialized scrapers** → 5 venues

**Total: 10 scrapers → 10 venues**

---

## Scraper Sharing Opportunities

### **Multi-Platform Support**
Some scrapers could potentially handle multiple platforms:

1. **ScienceDirect Scraper** (if implemented)
   - Could handle: Procedia Computer Science, iScience
   - Note: Many are paywalled, but some open access

2. **Generic Journal Scraper**
   - Could provide base for: BMJ Open, eLife, Frontiers
   - Common patterns: issue/volume structure, DOI handling

3. **Conference Proceedings Scraper**
   - Base class for: AAAI, AAMAS, conference-style venues
   - Common patterns: year-based organization, paper sessions

---

## Technical Implementation Strategy

### **Base Classes Hierarchy**
```
BaseScraper
├── ConferenceProceedingsScraper
│   ├── PMLRScraper (extends existing)
│   ├── CVFScraper ✅
│   ├── ACLAnthologyScraper ✅
│   ├── AAAIScraper
│   └── AAMASScraper
├── JournalPublisherScraper
│   ├── JMLRScraper
│   ├── NaturePortfolioScraper
│   ├── CellPressScraper
│   ├── BMCPlatformScraper
│   └── FrontiersScraper
└── APIEnhancedScraper
    ├── IEEEXploreScraper
    ├── ACMDigitalLibraryScraper
    └── OpenReviewScraper ✅
```

### **Shared Components**
1. **Authentication Manager** - For IEEE/ACM access
2. **DOI Resolver** - Common across journal scrapers
3. **Paper Metadata Extractor** - Standardized extraction
4. **Rate Limiter** - Configurable per platform

---

## Summary Statistics

### **Current State**
- **6 venues** already covered by existing scrapers
- **31 venues** need new scraper functionality
- **13 venues** behind strict paywalls (excluded)

### **Proposed Solution**
- **15 total scrapers** needed (including existing)
- **9 new scrapers** to implement
- **6 existing scrapers** to extend/reuse

### **Coverage Achievement**
- **37 out of 50 venues** covered (74%)
- **Average venues per scraper**: 2.47
- **Maximum reuse**: IEEE Xplore (8 venues), ACM DL (5 venues)

---

## Recommended Implementation Order

### **Phase 1: Quick Wins** (1 week)
1. Extend PMLR scraper (+3 venues)
2. Extend OpenReview scraper (+3 venues)
3. Implement JMLR scraper (+2 venues)

**Result: +8 venues with minimal effort**

### **Phase 2: High-Impact Platforms** (2 weeks)
4. Implement Nature Portfolio scraper (+3 venues)
5. Implement AAAI scraper (+1 venue)
6. Implement Cell Press scraper (+2 venues)

**Result: +6 high-impact venues**

### **Phase 3: Subscription Platforms** (2 weeks)
7. Implement IEEE Xplore scraper (+8 venues)
8. Implement ACM DL scraper (+5 venues)

**Result: +13 venues (if access available)**

### **Phase 4: Remaining Venues** (1 week)
9. Individual scrapers for remaining open access venues

**Result: Complete coverage of feasible venues**

---

## Key Insights

1. **Platform Consolidation**: Many venues share common platforms, enabling significant code reuse
2. **OpenReview Growth**: Emerging as a major platform for AI/ML conferences
3. **Publisher APIs**: Nature, IEEE, and ACM offer APIs that could simplify implementation
4. **Open Access Trend**: More venues than expected are fully open access
5. **Scraper Reusability**: Average of 2.47 venues per scraper shows good consolidation opportunity

This consolidation reduces implementation complexity while maintaining comprehensive coverage of the top venues.
