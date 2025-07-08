# Comprehensive PDF Infrastructure for Top Mila Venues

**Timestamp**: 2025-01-01 13:30
**Title**: Extended Coverage for Top 15 Mila Publication Venues

## Top 15 Mila Publication Venues (2019-2024)

Based on deduplicated analysis:

1. **NeurIPS**: 152 papers
2. **ICML**: 122 papers
3. **ICLR**: 94 papers
4. **TMLR**: 54 papers
5. **AAAI**: 49 papers
6. **EMNLP**: 41 papers
7. **EACL**: 31 papers
8. **Radiotherapy and Oncology**: 18 papers
9. **Journal of Pediatric Surgery**: 17 papers
10. **CVPR**: 16 papers
11. **Nature Communications**: 15 papers
12. **ICRA**: 12 papers
13. **Scientific Reports**: 11 papers
14. **COLM**: 11 papers
15. **Trans. Mach. Learn. Res.**: 11 papers

## Estimated PDF Source Distribution

Based on typical publication patterns for these venues:

### Machine Learning Conferences (Top 8)
1. **NeurIPS (152)**:
   - OpenReview (2023-2024): ~134 papers
   - NeurIPS Proceedings: ~18 papers
   - arXiv preprints: ~120 papers

2. **ICML (122)**:
   - PMLR: ~122 papers
   - arXiv preprints: ~100 papers

3. **ICLR (94)**:
   - OpenReview: ~94 papers
   - arXiv preprints: ~80 papers

4. **TMLR (54)**:
   - JMLR/TMLR site: ~54 papers
   - arXiv preprints: ~40 papers

5. **AAAI (49)**:
   - AAAI Digital Library: ~49 papers
   - arXiv preprints: ~30 papers

6. **EMNLP (41)**:
   - ACL Anthology: ~41 papers
   - arXiv preprints: ~35 papers

7. **EACL (31)**:
   - ACL Anthology: ~31 papers
   - arXiv preprints: ~25 papers

8. **CVPR (16)**:
   - CVF Open Access: ~16 papers
   - arXiv preprints: ~12 papers

### Medical/Scientific Journals (9-15)
9. **Radiotherapy and Oncology (18)**:
   - Elsevier/ScienceDirect: ~18 papers
   - PubMed Central: ~10 papers

10. **Journal of Pediatric Surgery (17)**:
    - Elsevier/ScienceDirect: ~17 papers
    - PubMed Central: ~8 papers

11. **Nature Communications (15)**:
    - Nature.com: ~15 papers
    - PubMed Central: ~15 papers

12. **ICRA (12)**:
    - IEEE Xplore: ~12 papers
    - arXiv preprints: ~8 papers

13. **Scientific Reports (11)**:
    - Nature.com: ~11 papers
    - PubMed Central: ~11 papers

14. **COLM (11)**:
    - OpenReview: ~11 papers

15. **Trans. Mach. Learn. Res. (11)**:
    - JMLR site: ~11 papers

## Top 15 PDF Discovery Sources (Prioritized)

### Tier 1: Essential Sources (Must Have)

1. **arXiv API**
   - Coverage: ~500+ papers (preprints for most venues)
   - Implementation: Enhanced with multiple search strategies

2. **OpenReview API**
   - Coverage: NeurIPS 2023-2024, ICLR, COLM (~239 papers)
   - Implementation: Direct API access

3. **PMLR (Proceedings of Machine Learning Research)**
   - Coverage: ICML, AISTATS (~129 papers)
   - Implementation: Direct URL construction

4. **ACL Anthology**
   - Coverage: EMNLP, EACL, ACL (~72+ papers)
   - Implementation: Structured scraping

5. **Semantic Scholar API**
   - Coverage: Cross-venue discovery, metadata enrichment
   - Implementation: Batch API with openAccessPdf field

### Tier 2: High-Value Sources (Should Have)

6. **PubMed Central**
   - Coverage: Medical journals (~70+ papers)
   - Implementation: OAI-PMH protocol + E-utilities

7. **CrossRef/Unpaywall**
   - Coverage: DOI resolution for all journal papers
   - Implementation: REST API with DOI batch queries

8. **OpenAlex API**
   - Coverage: Broad academic coverage, open access links
   - Implementation: REST API with institutional filtering

9. **CVF Open Access**
   - Coverage: CVPR, ICCV, ECCV (~16+ papers)
   - Implementation: Direct URL patterns

10. **AAAI Digital Library**
    - Coverage: AAAI conferences (~49 papers)
    - Implementation: Proceedings scraping

### Tier 3: Specialized Sources (Nice to Have)

11. **IEEE Xplore API**
    - Coverage: ICRA, IROS, other IEEE conferences (~18+ papers)
    - Implementation: Limited free API or metadata only

12. **Nature.com**
    - Coverage: Nature Communications, Scientific Reports (~26 papers)
    - Implementation: Web scraping with rate limits

13. **JMLR/TMLR**
    - Coverage: TMLR, JMLR papers (~65 papers)
    - Implementation: Direct site scraping

14. **CORE API**
    - Coverage: Aggregated institutional repositories
    - Implementation: REST API with search

15. **HAL (French Archive)**
    - Coverage: Mila's French connections
    - Implementation: OAI-PMH harvesting

## Implementation Strategy by Source Type

### 1. API-Based Sources (Parallel Implementation)
```python
# Tier 1 APIs
- arXiv API (enhanced search)
- OpenReview API v2
- Semantic Scholar API

# Tier 2 APIs
- PubMed Central (E-utilities + OAI)
- CrossRef/Unpaywall
- OpenAlex API

# Tier 3 APIs
- CORE API
- HAL OAI-PMH
```

### 2. Direct URL Construction (Simple Scrapers)
```python
# Predictable URL patterns
- PMLR: proceedings.mlr.press/v{volume}/{paper}.pdf
- ACL: aclanthology.org/{venue}{year}.{id}.pdf
- CVF: openaccess.thecvf.com/{venue}{year}/papers/{paper}.pdf
- JMLR: jmlr.org/papers/v{volume}/{paper}.pdf
```

### 3. Web Scraping (Complex Scrapers)
```python
# Requires parsing HTML
- AAAI Digital Library
- IEEE Xplore (metadata)
- Nature.com
- Conference proceedings pages
```

## Expected Coverage by Implementation Phase

### Phase 1 (Tier 1 Sources)
- Papers covered: ~600-700 (75-85%)
- Sources: arXiv, OpenReview, PMLR, ACL, Semantic Scholar

### Phase 2 (Tier 1 + 2)
- Papers covered: ~750-800 (90-95%)
- Added: PubMed, CrossRef, OpenAlex, CVF, AAAI

### Phase 3 (All Sources)
- Papers covered: ~800-850 (95-99%)
- Added: IEEE, Nature, JMLR, CORE, HAL

## Revised GitHub Issues for Comprehensive Coverage

### Core Infrastructure
1. **#75**: PDF Discovery Framework with Multi-Source Orchestration (L, 6-8h)
2. **#76**: Deduplication Engine with Version Management (L, 6-8h)

### Tier 1 Sources (Critical Path)
3. **#77**: arXiv Enhanced Discovery (M, 4-6h)
4. **#78**: OpenReview API Integration (M, 4-6h)
5. **#79**: PMLR Direct Scraper (S, 2-3h)
6. **#80**: ACL Anthology Scraper (S, 2-3h)
7. **#81**: Semantic Scholar Collector (M, 4-6h)

### Tier 2 Sources (High Value)
8. **#82**: PubMed Central Harvester (M, 4-6h)
9. **#83**: CrossRef/Unpaywall Resolver (S, 2-3h)
10. **#84**: OpenAlex Integration (S, 2-3h)
11. **#85**: CVF Open Access Scraper (S, 2-3h)
12. **#86**: AAAI Proceedings Scraper (M, 4-6h)

### Tier 3 Sources (Extended Coverage)
13. **#87**: IEEE/Nature/JMLR Scrapers (M, 4-6h)
14. **#88**: CORE/HAL API Integration (S, 2-3h)

### System Components
15. **#89**: PDF Download Manager (S, 2-3h)
16. **#90**: Optimized PDF Parser (M, 4-6h)
17. **#91**: Monitoring Dashboard (M, 4-6h)

## Success Metrics

### Coverage Targets
- **Top 8 ML venues**: 95%+ PDF discovery
- **Top 15 all venues**: 90%+ PDF discovery
- **Overall Mila papers**: 85%+ PDF discovery

### Source Distribution
- arXiv: ~40% of PDFs
- Conference sites: ~35% of PDFs
- Journal publishers: ~15% of PDFs
- Other sources: ~10% of PDFs

### Performance
- Discovery time: <3s per paper (parallelized)
- 15 sources checked per paper
- Intelligent source ordering based on venue
