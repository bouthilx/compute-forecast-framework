# Exhaustive Scraper-Venue-Paper Count List

**Date**: January 9, 2025
**Task**: Complete mapping of all scrapers to venues with paper counts
**Source**: venues_final_cumulative_coverage.csv top 50 analysis

## Complete Scraper List with Venues and Paper Counts

### 1. **NeurIPSScraper** ✅ (Already Implemented)
**Total Papers: 446**
- NeurIPS: 446 papers

---

### 2. **MLRScraper / PMLRScraper** ✅ (Partially Implemented)
**Total Papers: 468**
- ICML: 349 papers ✅ (already implemented)
- AISTATS: 66 papers ✅ (already implemented)
- UAI: 38 papers ✅ (already implemented)
- CoLLAs: 15 papers ✅ (already implemented)

---

### 3. **OpenReviewScraper** ✅ (Partially Implemented)
**Total Papers: 541**
- ICLR: 292 papers ✅ (already implemented)
- TMLR: 203 papers ✅ (already implemented)
- COLM: 31 papers ✅ (already implemented)
- RLC: 15 papers ✅ (already implemented)

---

### 4. **ACLAnthologyScraper** ✅ (Already Implemented)
**Total Papers: 224**
- ACL: 115 papers
- EMNLP: 109 papers

---

### 5. **CVFScraper** ✅ (Already Implemented)
**Total Papers: 53**
- CVPR: 53 papers

---

### 6. **JMLRScraper** (New)
**Total Papers: 231**
- TMLR: 203 papers (also accessible via OpenReview)
- JMLR: 28 papers

---

### 7. **NaturePortfolioScraper** (New)
**Total Papers: 145**
- Nature: 94 papers
- Scientific Reports: 35 papers
- Communications Biology: 16 papers

---

### 8. **IEEEXploreScraper** (New)
**Total Papers: 115**
- ICRA: 30 papers
- ICC: 20 papers
- IROS: 19 papers
- ICASSP: 13 papers
- IEEE Transactions on Control of Network Systems: 12 papers
- IEEE Transactions on Knowledge and Data Engineering: 11 papers
- IEEE Robotics and Automation Letters: 10 papers
- IEEE TPAMI: 10 papers (might be duplicated count)

---

### 9. **ACMDigitalLibraryScraper** (New)
**Total Papers: 70**
- ACM FAccT: 19 papers
- SIGIR: 15 papers
- ACM Computing Surveys: 15 papers
- ACM TOSEM: 13 papers
- SIGGRAPH Asia: 11 papers
- ACM Trans. Softw. Eng. Methodol.: 12 papers (likely same as TOSEM)

*Note: ACM TOSEM and ACM Trans. Softw. Eng. Methodol. might be the same venue with 13 papers total*

---

### 10. **AAAIScraper** (New)
**Total Papers: 67**
- AAAI: 67 papers

---

### 11. **CellPressScraper** (New)
**Total Papers: 36**
- iScience: 23 papers
- Cell Reports: 13 papers

---

### 12. **BMCPlatformScraper** (New)
**Total Papers: 19**
- Molecular Autism: 19 papers

---

### 13. **AstrophysicalJournalScraper** (New)
**Total Papers: 16**
- The Astrophysical Journal: 16 papers

---

### 14. **FrontiersPlatformScraper** (New)
**Total Papers: 14**
- Frontiers in Neuroscience: 14 papers

---

### 15. **BMJOpenScraper** (New)
**Total Papers: 14**
- BMJ Open: 14 papers

---

### 16. **eLifeScraper** (New)
**Total Papers: 14**
- eLife: 14 papers

---

### 17. **AAMASScraper** (New)
**Total Papers: 11**
- AAMAS: 11 papers

---

### 18. **IEEEAccessScraper** (New)
**Total Papers: 11**
- IEEE Access: 11 papers

---

### 19. **BioinformaticsScraper** (New)
**Total Papers: 11**
- Bioinformatics: 11 papers

---

### 20. **ProcediaComputerScienceScraper** (New)
**Total Papers: 10**
- Procedia Computer Science: 10 papers

---

### 21. **INFORMSScraper** (New)
**Total Papers: 10**
- INFORMS Journal on Computing: 10 papers

---

### 22. **SemanticScholarScraper** ✅ (Already Implemented as Fallback)
**Total Papers: Variable**
- Used as fallback for any venue without dedicated scraper
- Can handle any venue but with potentially lower quality/completeness

---

## Summary by Implementation Status

### **Already Fully Implemented (5 scrapers)**
**Total Papers: 1,268**
1. NeurIPSScraper: 446 papers
2. MLRScraper (ICML only): 349 papers
3. OpenReviewScraper (ICLR only): 292 papers
4. ACLAnthologyScraper: 224 papers
5. CVFScraper: 53 papers

### **Partially Implemented - Need Extension (2 scrapers)**
**Total Additional Papers: 368**
1. MLRScraper → PMLRScraper extension: +119 papers
   - AISTATS (66), UAI (38), CoLLAs (15)
2. OpenReviewScraper extension: +249 papers
   - TMLR (203), COLM (31), RLC (15)

### **New Scrapers Needed (16 scrapers)**
**Total Papers: 885**

#### High-Impact Scrapers (>50 papers):
1. JMLRScraper: 231 papers
2. NaturePortfolioScraper: 145 papers
3. IEEEXploreScraper: 115 papers
4. ACMDigitalLibraryScraper: 70 papers
5. AAAIScraper: 67 papers

#### Medium-Impact Scrapers (20-50 papers):
6. CellPressScraper: 36 papers

#### Low-Impact Scrapers (<20 papers each):
7. BMCPlatformScraper: 19 papers
8. AstrophysicalJournalScraper: 16 papers
9. FrontiersPlatformScraper: 14 papers
10. BMJOpenScraper: 14 papers
11. eLifeScraper: 14 papers
12. AAMASScraper: 11 papers
13. IEEEAccessScraper: 11 papers
14. BioinformaticsScraper: 11 papers
15. ProcediaComputerScienceScraper: 10 papers
16. INFORMSScraper: 10 papers

---

## Excluded Venues (Paywalled/Not Feasible)

**Total Papers Excluded: ~1,700**

### Major Excluded Venues:
1. JPS: 52 papers
2. Radiotherapy and Oncology: 51 papers
3. Empirical Software Engineering: 30 papers
4. NeuroImage: 27 papers
5. LNCS: 21 papers
6. Medical Physics: 17 papers
7. Biological Psychiatry: 15 papers
8. Information and Software Technology: 15 papers
9. Magnetic Resonance in Medicine: 14 papers
10. Computers & Operations Research: 11 papers

---

## Grand Total Coverage

### **Current Coverage (Already Implemented)**
- 5 scrapers fully implemented
- 1,268 papers covered (29.91% of dataset)

### **Potential Additional Coverage**
- 2 scrapers to extend: +368 papers
- 16 new scrapers to implement: +885 papers
- Total additional: 1,253 papers

### **Total Achievable Coverage**
- 21 scrapers (excluding SemanticScholar fallback)
- 2,521 papers (59.46% of dataset)
- Remaining 40.54% behind paywalls or not feasible

---

## Implementation Effort Estimates

### **Quick Wins (6-9 hours)**
- Extend MLRScraper → +119 papers
- Extend OpenReviewScraper → +249 papers
- **Subtotal**: 368 papers for 6-9 hours work

### **High-Value New Scrapers (20-30 hours)**
- JMLRScraper: 231 papers (4-6h)
- NaturePortfolioScraper: 145 papers (6-8h)
- IEEEXploreScraper: 115 papers (8-10h)
- ACMDigitalLibraryScraper: 70 papers (6-8h)
- AAAIScraper: 67 papers (4-6h)
- **Subtotal**: 628 papers for 28-38 hours work

### **Remaining Scrapers (30-45 hours)**
- 11 scrapers with 10-36 papers each
- **Subtotal**: 257 papers for 30-45 hours work

### **Total Implementation Estimate**
- **21 scrapers total**
- **56-92 hours of work**
- **2,521 papers covered**
- **59.46% of dataset coverage**
