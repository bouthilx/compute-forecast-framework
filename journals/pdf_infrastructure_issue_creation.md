# PDF Infrastructure Issue Creation Log

**Timestamp**: 2025-01-02 10:15
**Title**: Creating GitHub Issues for PDF Handling Pipeline

## Issue Creation Plan

### Total Issues: 19

All issues will have:
- **Milestone**: "Milestone 02-B: PDF Handling Pipeline" (number 19)
- **Project**: "Orchestrator: Computational Needs Analysis 2025-2027" (#3)
- **Base labels**: "enhancement" (all are new features)

### Issue List with Specific Labels

#### Core Infrastructure (2 issues) - COMPLETED
1. ✅ **#77**: [PDF-Core] PDF Discovery Framework
   - Labels: `work:implementation`, `domain:extraction`, `priority:critical`
   - Dependencies: Blocks all source implementations

2. ✅ **#78**: [PDF-Dedup] Deduplication Engine
   - Labels: `work:implementation`, `domain:extraction`, `priority:critical`
   - Dependencies: Requires #77

#### Tier 1 Sources (5 issues) - Critical Path
3. **[PDF-arXiv]** arXiv Enhanced Discovery
   - Labels: `work:implementation`, `domain:collection`, `priority:high`
   - Dependencies: Requires #77, #78
   - Effort: M (4-6h)

4. **[PDF-OpenReview]** OpenReview API Integration
   - Labels: `work:implementation`, `domain:collection`, `priority:high`
   - Dependencies: Requires #77, #78
   - Effort: M (4-6h)

5. **[PDF-PMLR]** PMLR Direct Scraper
   - Labels: `work:implementation`, `domain:collection`, `priority:high`
   - Dependencies: Requires #77, #78
   - Effort: S (2-3h)

6. **[PDF-ACL]** ACL Anthology Scraper
   - Labels: `work:implementation`, `domain:collection`, `priority:high`
   - Dependencies: Requires #77, #78
   - Effort: S (2-3h)

7. **[PDF-SS]** Semantic Scholar Collector
   - Labels: `work:implementation`, `domain:collection`, `priority:high`
   - Dependencies: Requires #77, #78
   - Effort: M (4-6h)

#### Tier 2 Sources (5 issues) - High Value
8. **[PDF-PMC]** PubMed Central Harvester
   - Labels: `work:implementation`, `domain:collection`, `priority:medium`
   - Dependencies: Requires #77, #78
   - Effort: M (4-6h)

9. **[PDF-CrossRef]** CrossRef/Unpaywall Resolver
   - Labels: `work:implementation`, `domain:collection`, `priority:medium`
   - Dependencies: Requires #77, #78
   - Effort: S (2-3h)

10. **[PDF-OpenAlex]** OpenAlex Integration
    - Labels: `work:implementation`, `domain:collection`, `priority:medium`
    - Dependencies: Requires #77, #78
    - Effort: S (2-3h)

11. **[PDF-CVF]** CVF Open Access Scraper
    - Labels: `work:implementation`, `domain:collection`, `priority:medium`
    - Dependencies: Requires #77, #78
    - Effort: S (2-3h)

12. **[PDF-AAAI]** AAAI Proceedings Scraper
    - Labels: `work:implementation`, `domain:collection`, `priority:medium`
    - Dependencies: Requires #77, #78
    - Effort: M (4-6h)

#### Tier 3 Sources (4 issues) - Extended Coverage
13. **[PDF-IEEE]** IEEE Xplore Metadata Extractor
    - Labels: `work:implementation`, `domain:collection`, `priority:low`
    - Dependencies: Requires #77, #78
    - Effort: M (4-6h)

14. **[PDF-Nature]** Nature.com Scraper
    - Labels: `work:implementation`, `domain:collection`, `priority:low`
    - Dependencies: Requires #77, #78
    - Effort: M (4-6h)

15. **[PDF-JMLR]** JMLR/TMLR Site Scraper
    - Labels: `work:implementation`, `domain:collection`, `priority:low`
    - Dependencies: Requires #77, #78
    - Effort: S (2-3h)

16. **[PDF-CORE]** CORE/HAL API Integration
    - Labels: `work:implementation`, `domain:collection`, `priority:low`
    - Dependencies: Requires #77, #78
    - Effort: S (2-3h)

#### System Components (3 issues)
17. **[PDF-Download]** Simple PDF Download Manager
    - Labels: `work:implementation`, `domain:extraction`, `priority:high`
    - Dependencies: None (can start immediately)
    - Effort: S (2-3h)

18. **[PDF-Parser]** Optimized PDF Parser (Split Strategy)
    - Labels: `work:implementation`, `domain:extraction`, `priority:high`
    - Dependencies: Requires #91 (PDF Download)
    - Effort: M (4-6h)

19. **[PDF-Monitor]** Monitoring Dashboard
    - Labels: `work:implementation`, `domain:installation`, `priority:medium`
    - Dependencies: Requires all other components
    - Effort: M (4-6h)

## Progress Tracking

### Completed
- ✅ Created milestone "Milestone 02-B: PDF Handling Pipeline"
- ✅ All 19 issues created and added to project #3

### Issue Numbers Created
- **Core Infrastructure**:
  - #77: PDF Discovery Framework
  - #78: Deduplication Engine

- **Tier 1 Sources**:
  - #79: arXiv Enhanced Discovery
  - #80: OpenReview API Integration
  - #81: PMLR Direct Scraper
  - #82: ACL Anthology Scraper
  - #83: Semantic Scholar Collector

- **Tier 2 Sources**:
  - #84: PubMed Central Harvester
  - #85: CrossRef/Unpaywall Resolver
  - #86: OpenAlex Integration
  - #87: CVF Open Access Scraper
  - #88: AAAI Proceedings Scraper

- **Tier 3 Sources**:
  - #91: IEEE Xplore Metadata Extractor
  - #92: Nature.com Scraper
  - #93: JMLR/TMLR Site Scraper
  - #94: CORE/HAL API Integration

- **System Components**:
  - #89: Simple PDF Download Manager
  - #90: Optimized PDF Parser (Split Strategy)
  - #95: Monitoring Dashboard

## Summary
Successfully created all 19 issues for the PDF handling pipeline milestone. All issues have been:
- Tagged with appropriate work type and domain labels
- Added to Milestone 02-B: PDF Handling Pipeline
- Added to Project #3: Orchestrator: Computational Needs Analysis 2025-2027
- Given detailed descriptions with clear dependencies and time estimates

The implementation can now proceed with 4 developers working in parallel across the different tiers.

---

## Update: PDF Parser Breakdown (2025-01-02 10:45)

### Issue #90 Too Large
Issue #90 ([PDF-Parser] Optimized PDF Parser) was identified as too large, containing 5 different integrations. Breaking it down into focused issues.

### Plan
1. **Update #90** to be just the core parser framework
2. **Create 5 new issues** for individual integrations:
   - PyMuPDF Basic Text Extractor
   - EasyOCR Integration
   - GROBID Academic Structure Extractor
   - Google Cloud Vision OCR
   - Claude Vision for Affiliation Extraction

### New Issues to Create
All will have:
- **Milestone**: "Milestone 02-B: PDF Handling Pipeline"
- **Project**: #3 (Orchestrator: Computational Needs Analysis 2025-2027)
- **Labels**: `work:implementation`, `domain:extraction`, `enhancement`
- **Priority**: `priority:high` for PyMuPDF/OCR/GROBID, `priority:medium` for cloud services
- **Dependencies**: All depend on #90 (Parser Core)

### Issues Created in Parser Breakdown
- ✅ **Updated #90**: Now just PDF Parser Core Framework (S, 2-3h)
- ✅ **#96**: [PDF-Parser-PyMuPDF] PyMuPDF Basic Text Extractor (S, 2-3h)
- ✅ **#97**: [PDF-Parser-OCR] EasyOCR Integration (M, 4-6h)
- ✅ **#98**: [PDF-Parser-GROBID] GROBID Academic Structure Extractor (M, 4-6h)
- ✅ **#99**: [PDF-Parser-GCV] Google Cloud Vision OCR (M, 4-6h)
- ✅ **#100**: [PDF-Parser-Claude] Claude Vision for Affiliation Extraction (M, 4-6h)

### Final Summary
Total issues for PDF Handling Pipeline: **24 issues**
- Original: 19 issues (#77-95)
- Parser breakdown: Added 5 new issues (#96-100), updated 1 (#90)

All issues have been:
- Created with detailed descriptions
- Tagged with appropriate labels
- Added to Milestone 02-B
- Added to Project #3
- Dependencies clearly marked

The PDF parser is now properly broken down into manageable, focused components that can be developed in parallel.

---

## Implementation Flow Diagram (2025-01-02 11:00)

### PDF Infrastructure Implementation Flow

```
Phase 1: Core Infrastructure (Day 1)
------------------------------------
┌─────────────────────────────────────────────────────────────────┐
│ #77: [PDF-Core] PDF Discovery Framework (Critical, blocks all)  │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ #78: [PDF-Dedup] Deduplication Engine (Critical)               │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
Phase 2: Parallel Implementation (Days 2-3)
-------------------------------------------
                ┌────┴────┬────────┬────────┬────────┐
                │         │        │        │        │
    ┌───────────▼───┐ ┌───▼───┐ ┌─▼──┐ ┌───▼───┐ ┌─▼──┐
    │ Developer 1   │ │ Dev 2 │ │Dev3│ │ Dev 4 │ │Dev5│
    └───────────────┘ └───────┘ └────┘ └───────┘ └────┘
           │              │        │        │        │
    ┌──────▼──────┐ ┌────▼────┐ ┌▼───┐ ┌──▼───┐ ┌─▼──┐
    │#89: Download│ │#79: arXiv│ │#80:│ │ #81: │ │#82:│
    │Manager (S)  │ │Enhanced │ │Open│ │ PMLR │ │ACL │
    │             │ │   (M)    │ │Rev │ │  (S) │ │(S) │
    └──────┬──────┘ └─────────┘ │(M) │ └──────┘ └────┘
           │                     └────┘
           ▼
    ┌──────────────┐
    │#90: Parser   │     Tier 1 Sources (Critical Path)
    │Core Framework│     ================================
    │     (S)      │     #83: Semantic Scholar (M)
    └──────┬───────┘     #84: PubMed Central (M)
           │             #85: CrossRef/Unpaywall (S)
           ▼             #86: OpenAlex (S)
    ┌──────┴───────┬──────────┬──────────┬──────────┬─────────┐
    │              │          │          │          │         │
┌───▼────┐ ┌──────▼───┐ ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌──▼───┐
│#96:    │ │#97:      │ │#98:    │ │#99:    │ │#100:   │ │ Tier │
│PyMuPDF │ │EasyOCR   │ │GROBID  │ │Google  │ │Claude  │ │  2   │
│  (S)   │ │   (M)    │ │  (M)   │ │Vision  │ │Vision  │ │      │
└────────┘ └──────────┘ └────────┘ │  (M)   │ │  (M)   │ └──────┘
                                    └────────┘ └────────┘

Phase 3: Extended Coverage (Day 3-4)
------------------------------------
Tier 2 Sources (Parallel):          Tier 3 Sources (Day 4):
#87: CVF Open Access (S)            #91: IEEE Xplore (M)
#88: AAAI Proceedings (M)           #92: Nature.com (M)
                                    #93: JMLR/TMLR (S)
                                    #94: CORE/HAL (S)

Phase 4: Integration & Monitoring (Day 4)
-----------------------------------------
                    ┌─────────────────────┐
                    │ #95: Monitoring     │
                    │ Dashboard (M)       │
                    └─────────────────────┘

Legend:
=======
S = Small (2-3h)
M = Medium (4-6h)
L = Large (6-8h)
→ = Sequential dependency
│ = Parallel execution possible
```

### Key Implementation Insights

1. **Critical Path**: #77 → #78 → Source implementations
2. **Parallel Opportunities**:
   - 5 developers can work on Tier 1 sources simultaneously after core is done
   - PDF Download (#89) and Parser Core (#90) can start immediately (no dependencies)
   - Parser integrations (#96-100) can be developed in parallel after #90
3. **Bottlenecks**:
   - Core framework (#77, #78) blocks everything else
   - Parser Core (#90) blocks all parser integrations (#96-100)
4. **Optimization Strategy**:
   - Start #89 and #90 early since they have no dependencies
   - Assign strongest developers to #77 and #78 to unblock others quickly
   - Run all Tier 1 sources in parallel with 5 developers

### Recommended Developer Assignment

- **Developer 1**: #77 → #78 → #89 → #90 (Core infrastructure path)
- **Developer 2**: Wait for #77/78 → #79 (arXiv) → #96 (PyMuPDF)
- **Developer 3**: Wait for #77/78 → #80 (OpenReview) → #97 (EasyOCR)
- **Developer 4**: Wait for #77/78 → #81 (PMLR) + #82 (ACL) → #98 (GROBID)
- **Developer 5**: Wait for #77/78 → #83 (Semantic Scholar) → #99/100 (Cloud services)

This assignment ensures maximum parallelization while respecting dependencies.
