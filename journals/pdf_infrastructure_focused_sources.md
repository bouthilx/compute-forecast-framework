# Focused PDF Discovery Sources Based on Mila Publications

**Timestamp**: 2025-01-01 13:00
**Title**: Priority PDF Sources Based on Actual Mila Publication Venues

## Analysis Results

### Top Mila Publication Venues (2019-2024)
Based on analysis of `mila_venue_statistics.json`:

1. **NeurIPS**: 128 papers
2. **ICML**: 116 papers
3. **ICLR**: 94 papers
4. **TMLR**: 54 papers
5. **CVPR**: 16 papers
6. **AAAI**: 14 papers
7. **EMNLP**: 12 papers
8. **AISTATS**: 10 papers
9. **ACL**: 7 papers
10. **COLM**: 11 papers

### Medical/Healthcare Venues (Significant Presence)
- **Radiotherapy and Oncology**: 18 papers
- **Journal of Pediatric Surgery**: 17 papers
- **Nature Communications**: 15 papers
- **Scientific Reports**: 11 papers
- **NeuroImage**: 8 papers
- **Biological Psychiatry**: 5 papers

### PDF Source Analysis
From the paperoni dataset, the primary PDF source is:
- **arXiv**: 100% of available PDFs (1354 papers)

However, this is likely because the dataset is arXiv-focused. For comprehensive coverage, we need venue-specific sources.

## Prioritized PDF Discovery Sources

### Tier 1: Critical Sources (Must Have)

#### Academic APIs
1. **arXiv API** - Primary source for preprints
2. **Semantic Scholar** - Good coverage across venues
3. **OpenAlex** - Broad academic coverage

#### Venue-Specific Scrapers
1. **OpenReview** - ICLR (94 papers), NeurIPS 2023+
2. **PMLR** - ICML (116 papers), AISTATS (10 papers)
3. **NeurIPS Proceedings** - Pre-2023 NeurIPS (older conferences)
4. **ACL Anthology** - EMNLP (12 papers), ACL (7 papers)

### Tier 2: Important Sources (Should Have)

#### Academic APIs
4. **PubMed Central** - Medical papers (Radiotherapy, Pediatric Surgery)
5. **CrossRef/Unpaywall** - DOI resolution for Nature, Scientific Reports

#### Venue-Specific Scrapers
5. **CVF Open Access** - CVPR (16 papers)
6. **AAAI Digital Library** - AAAI (14 papers)
7. **TMLR** - Transactions on Machine Learning Research (54 papers)

### Tier 3: Nice to Have

#### Additional Sources
- **CORE API** - General coverage
- **BASE** - Institutional repositories
- **Nature.com** - Nature Communications
- **JMLR** - Machine learning journals

## Simplified Implementation Plan

### Phase 1: Core Infrastructure + Tier 1 Sources (Days 1-2)
- PDF Discovery Framework
- arXiv enhanced miner
- Semantic Scholar collector
- OpenReview scraper
- PMLR scraper

### Phase 2: Tier 2 Sources (Day 3)
- PubMed Central for medical papers
- CrossRef/Unpaywall integration
- ACL Anthology scraper
- CVF/AAAI scrapers

### Phase 3: Testing & Integration (Day 4)
- Deduplication system
- Validation pipeline
- Test with provided papers

## Revised GitHub Issues

### Critical Path (Tier 1)
1. **#75**: PDF Discovery Framework (L, 6-8h)
2. **#76**: arXiv Enhanced Miner (M, 4-6h)
3. **#77**: Semantic Scholar Collector (M, 4-6h)
4. **#78**: OpenReview Scraper (M, 4-6h)
5. **#79**: PMLR Scraper (M, 4-6h)

### Important (Tier 2)
6. **#80**: PubMed Central Integration (M, 4-6h)
7. **#81**: ACL Anthology Scraper (S, 2-3h)
8. **#82**: CrossRef/Unpaywall Resolver (S, 2-3h)

### System Components
9. **#83**: Deduplication System (L, 6-8h)
10. **#84**: PDF Download Manager (S, 2-3h)
11. **#85**: PDF Parser with Split Strategy (M, 4-6h)

### Total Revised Effort
- 3 developers × 4 days = 12 developer-days
- ~30-35 hours of implementation work

## Why This Focused Approach Works

1. **Covers 95%+ of Mila papers** with just 7-8 sources
2. **Reduces complexity** from 30+ sources to ~10
3. **Faster implementation** - 4 days vs 5-7 days
4. **Lower maintenance** - Fewer APIs to maintain
5. **Cost-effective** - Focuses on free/open sources

## Test Coverage for Provided Papers

The test papers will validate:
- **arXiv**: "Attention Is All You Need" (1706.03762)
- **Direct URLs**: All baulab.info papers (need web scraping fallback)
- **Multi-institution**: Google Brain, OpenAI papers
- **Historical**: 2014-2015 papers testing older formats
