# Scraper Paper Count Analysis

**Date**: January 9, 2025  
**Task**: Calculate total papers covered by each consolidated scraper  
**Source**: venues_final_cumulative_coverage.csv

## Paper Count by Scraper (Sorted by Total Papers)

### 1. **PMLR Scraper** - 468 papers (11.04%)
- ICML: 349 papers ✅ (already implemented)
- AISTATS: 66 papers
- UAI: 38 papers
- Proceedings of 2nd Conference on Lifelong Learning Agents: 15 papers

### 2. **OpenReview Scraper** - 541 papers (12.76%)
- ICLR: 292 papers ✅ (already implemented)
- TMLR: 203 papers
- COLM: 31 papers
- RLC: 15 papers

### 3. **ACL Anthology Scraper** - 224 papers (5.28%)
- ACL: 115 papers ✅
- EMNLP: 109 papers ✅

### 4. **JMLR Scraper** - 231 papers (5.45%)
- TMLR: 203 papers (primary access)
- JMLR: 28 papers

### 5. **Nature Portfolio Scraper** - 145 papers (3.42%)
- Nature: 94 papers
- Scientific Reports: 35 papers
- Communications Biology: 16 papers

### 6. **IEEE Xplore Scraper** - 115 papers (2.71%)
- ICRA: 30 papers
- ICC: 20 papers
- IROS: 19 papers
- ICASSP: 13 papers
- IEEE Transactions on Control of Network Systems: 12 papers
- IEEE Transactions on Knowledge and Data Engineering: 11 papers
- IEEE Robotics and Automation Letters: 10 papers
- IEEE TPAMI: 10 papers

### 7. **ACM Digital Library Scraper** - 70 papers (1.65%)
- SIGIR: 15 papers
- ACM Computing Surveys: 15 papers
- ACM FAccT: 19 papers
- ACM TOSEM: 13 papers
- SIGGRAPH Asia: 11 papers
- ACM Trans. Softw. Eng. Methodol.: 12 papers (same as TOSEM?)

### 8. **AAAI Scraper** - 67 papers (1.58%)
- AAAI: 67 papers

### 9. **CVF Scraper** - 53 papers (1.25%)
- CVPR: 53 papers ✅ (already implemented)

### 10. **NeurIPS Scraper** - 446 papers (10.52%)
- NeurIPS: 446 papers ✅ (already implemented)

### 11. **Cell Press Scraper** - 36 papers (0.85%)
- iScience: 23 papers
- Cell Reports: 13 papers

### 12. **BMC Platform Scraper** - 19 papers (0.45%)
- Molecular Autism: 19 papers

### 13. **Astrophysical Journal Scraper** - 16 papers (0.38%)
- The Astrophysical Journal: 16 papers

### 14. **Frontiers Platform Scraper** - 14 papers (0.33%)
- Frontiers in Neuroscience: 14 papers

### 15. **BMJ Open Scraper** - 14 papers (0.33%)
- BMJ Open: 14 papers

### 16. **eLife Scraper** - 14 papers (0.33%)
- eLife: 14 papers

### 17. **AAMAS Scraper** - 11 papers (0.26%)
- AAMAS: 11 papers

### 18. **IEEE Access Scraper** - 11 papers (0.26%)
- IEEE Access: 11 papers

### 19. **Bioinformatics Scraper** - 11 papers (0.26%)
- Bioinformatics: 11 papers

### 20. **Procedia Computer Science Scraper** - 10 papers (0.24%)
- Procedia Computer Science: 10 papers

### 21. **INFORMS Scraper** - 10 papers (0.24%)
- INFORMS Journal on Computing: 10 papers

---

## Summary Statistics

### **Total Papers Covered**: 2,521 papers (59.46% of dataset)

### **Papers by Scraper Category**:

#### **Already Implemented** (6 scrapers): 1,615 papers (38.09%)
- NeurIPS Scraper: 446 papers
- PMLR Scraper (ICML only): 349 papers
- OpenReview Scraper (ICLR only): 292 papers
- ACL Anthology Scraper: 224 papers
- CVF Scraper: 53 papers
- (SemanticScholar as fallback: N/A)

#### **Extensions Needed** (2 scrapers): 368 papers (8.68%)
- PMLR Scraper (extend): +119 papers (AISTATS, UAI, CoLLAs)
- OpenReview Scraper (extend): +249 papers (TMLR, COLM, RLC)

#### **New Scrapers Needed** (9-15 scrapers): 538 papers (12.69%)
- Major platforms: 366 papers
  - Nature Portfolio: 145 papers
  - IEEE Xplore: 115 papers
  - ACM Digital Library: 70 papers
  - Cell Press: 36 papers
- Individual scrapers: 172 papers
  - AAAI: 67 papers
  - JMLR: 28 papers
  - Others: 77 papers

### **Excluded (Paywalled)**: ~1,700 papers (40.54%)
- JPS: 52 papers
- Radiotherapy and Oncology: 51 papers
- Empirical Software Engineering: 30 papers
- NeuroImage: 27 papers
- LNCS: 21 papers
- Medical Physics: 17 papers
- Biological Psychiatry: 15 papers
- Information and Software Technology: 15 papers
- Magnetic Resonance in Medicine: 14 papers
- Computers & Operations Research: 11 papers

---

## ROI Analysis (Papers per Implementation Effort)

### **Highest ROI** (Most papers for least effort):
1. **Extend OpenReview** → 249 papers (2-3h work)
2. **Extend PMLR** → 119 papers (2-3h work)
3. **JMLR Scraper** → 231 papers (4-6h work)
4. **Nature Portfolio** → 145 papers (6-8h work)
5. **IEEE Xplore** → 115 papers (8-10h work)

### **Medium ROI**:
6. **ACM Digital Library** → 70 papers (6-8h work)
7. **AAAI Scraper** → 67 papers (4-6h work)
8. **Cell Press** → 36 papers (4-6h work)

### **Lower ROI** (Individual scrapers):
9. Various individual scrapers → 10-19 papers each

---

## Implementation Priority Recommendation

### **Phase 1: Maximum Impact** (6-9h work, +368 papers)
1. Extend OpenReview Scraper (+249 papers)
2. Extend PMLR Scraper (+119 papers)

### **Phase 2: High-Value Targets** (18-26h work, +443 papers)
3. JMLR Scraper (231 papers)
4. Nature Portfolio Scraper (145 papers)
5. AAAI Scraper (67 papers)

### **Phase 3: Platform Consolidation** (14-18h work, +221 papers)
6. IEEE Xplore Scraper (115 papers)
7. ACM Digital Library Scraper (70 papers)
8. Cell Press Scraper (36 papers)

### **Phase 4: Long Tail** (20-30h work, +124 papers)
9. Individual scrapers for remaining venues

---

## Key Insights

1. **80/20 Rule Applies**: The top 5 scrapers cover 1,641 papers (65% of implementable papers)

2. **Quick Wins Available**: Simply extending existing OpenReview and PMLR scrapers adds 368 papers

3. **Platform Concentration**: 
   - OpenReview emerging as dominant (541 papers across 4 venues)
   - PMLR established for ML conferences (468 papers)
   - IEEE/ACM have many venues but fewer papers per venue

4. **Open Access Advantage**: The highest paper counts come from fully open access platforms

5. **Total Coverage Potential**: Implementing all scrapers would cover 2,521 papers (59.46% of the dataset)

This analysis shows that focusing on extending existing scrapers and implementing a few key new ones (JMLR, Nature Portfolio, AAAI) would quickly achieve coverage of over 1,800 papers with minimal effort.