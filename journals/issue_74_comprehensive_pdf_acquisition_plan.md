# Comprehensive PDF Acquisition Plan for Mila Papers

**Timestamp**: 2025-07-01 19:00
**Title**: Venue-Specific PDF Acquisition Strategy

## Key Findings from Merged Venue Analysis

### Top Venues (Papers Count)
1. **NeurIPS**: 152 papers (11.2%)
2. **ICML**: 122 papers (9.0%)
3. **ICLR**: 94 papers (6.9%)
4. **TMLR**: 54 papers (4.0%)
5. **AAAI**: 49 papers (3.6%)
6. **EMNLP**: 41 papers (3.0%)

**Top 6 venues = 512 papers (37.7% of all papers)**

### Temporal Distribution
- Most papers are from 2022-2024
- 2023 peak: 316 papers from top venues
- 2024 (partial): 236 papers

## Venue-Specific PDF Acquisition Strategies

### 1. NeurIPS (152 papers)
**PDF Sources:**
- **Primary**: papers.nips.cc (2019-2022)
- **New site**: neurips.cc (2023-2024)
- **OpenReview**: Some years use OpenReview
- **ArXiv**: ~80% have ArXiv versions

**Implementation:**
```python
class NeurIPSPDFSource:
    def find_pdf(self, paper):
        year = paper.get('year')
        
        # Different sites by year
        if year <= 2022:
            # papers.nips.cc/paper/{year}/hash/{paper-slug}.pdf
            return self.search_papers_nips_cc(paper)
        else:
            # neurips.cc/{year}/papers
            return self.search_neurips_cc(paper)
```

### 2. ICML (122 papers)
**PDF Sources:**
- **Primary**: proceedings.mlr.press
- **Format**: v{volume}/lastname{year}.pdf
- **Coverage**: 100% for accepted papers

**Implementation:**
```python
class ICMLPDFSource:
    def find_pdf(self, paper):
        # PMLR volumes by year
        volume_map = {
            2024: 235, 2023: 202, 2022: 162,
            2021: 139, 2020: 119, 2019: 97
        }
        
        # Search by title/author on PMLR
        return self.search_pmlr(paper, volume_map[paper.year])
```

### 3. ICLR (94 papers)
**PDF Sources:**
- **Primary**: openreview.net
- **Coverage**: 100% for all years
- **API**: OpenReview API available

**Implementation:**
```python
class ICLRPDFSource:
    def find_pdf(self, paper):
        # All ICLR papers on OpenReview
        return self.search_openreview_api(
            paper, 
            venue=f"ICLR.cc/{paper.year}/Conference"
        )
```

### 4. TMLR (54 papers)
**PDF Sources:**
- **Primary**: openreview.net
- **Format**: Transactions on Machine Learning Research
- **Coverage**: 100%

### 5. AAAI (49 papers)
**PDF Sources:**
- **Primary**: ojs.aaai.org
- **Alternative**: aaai.org/Library/AAAI/
- **Coverage**: ~90%

### 6. EMNLP (41 papers)
**PDF Sources:**
- **Primary**: aclanthology.org
- **Coverage**: 100%
- **Format**: {year}.emnlp-main.{paper_id}.pdf

## Implementation Architecture

### Phase 1: Conference-Specific Loaders (1-2 days)

```python
# src/data/pdf/sources/conferences.py

class ConferencePDFManager:
    def __init__(self):
        self.sources = {
            'neurips': NeurIPSPDFSource(),
            'icml': ICMLPDFSource(),
            'iclr': ICLRPDFSource(),
            'aaai': AAAIPDFSource(),
            'emnlp': EMNLPPDFSource(),
            'cvpr': CVPRPDFSource(),
            'acl': ACLPDFSource(),
        }
    
    def find_pdf(self, paper):
        venue = self.identify_venue(paper)
        if venue in self.sources:
            return self.sources[venue].find_pdf(paper)
```

### Phase 2: Journal PDF Sources (1 day)

```python
# src/data/pdf/sources/journals.py

class JournalPDFManager:
    def __init__(self):
        self.open_access_apis = {
            'nature': NatureOAAPI(),
            'ieee': IEEEXploreAPI(),
            'elsevier': ElsevierAPI(),
        }
    
    def find_pdf(self, paper):
        # Try DOI first
        if doi := self.extract_doi(paper):
            # Unpaywall, CORE, etc.
            return self.resolve_doi_to_pdf(doi)
```

### Phase 3: Enhanced Search Strategies (1 day)

```python
# src/data/pdf/sources/enhanced_search.py

class EnhancedPDFSearch:
    def __init__(self):
        self.strategies = [
            GoogleScholarStrategy(),
            SemanticScholarStrategy(),
            ArXivStrategy(),
            WebSearchStrategy(),
        ]
    
    def comprehensive_search(self, paper):
        # Try each strategy with fingerprinting
        fingerprint = self.create_paper_fingerprint(paper)
        
        for strategy in self.strategies:
            if pdf_url := strategy.search(paper, fingerprint):
                return pdf_url
```

## Detailed Implementation Steps

### Day 1: Core Conference Sites
1. **NeurIPS loader** (2-3 hours)
   - Handle both old and new sites
   - Parse conference pages
   - Match papers by title/author

2. **ICML/PMLR loader** (2 hours)
   - Search PMLR proceedings
   - Handle volume mapping
   - Fuzzy title matching

3. **ICLR/OpenReview loader** (2 hours)
   - Use OpenReview API
   - Handle all years uniformly
   - Include workshop papers

### Day 2: ACL Anthology & More
1. **ACL Anthology loader** (2 hours)
   - EMNLP, ACL, NAACL papers
   - Parse anthology structure
   - Direct PDF links

2. **AAAI loader** (2 hours)
   - Navigate AAAI library
   - Handle different year formats

3. **CVPR/CVF loader** (2 hours)
   - OpenAccess CVF site
   - CVPR, ICCV, ECCV papers

### Day 3: Journals & Enhanced Search
1. **DOI resolver enhancement** (2 hours)
   - Unpaywall integration
   - CORE API
   - PubMed Central

2. **Google Scholar scraper** (3 hours)
   - Scholarly library integration
   - Rate limiting
   - Multiple PDF source extraction

3. **Web search fallback** (2 hours)
   - DuckDuckGo API
   - PDF validation
   - Author website search

## Expected Coverage by Source

### After Implementation
- **Conference sites**: 40-50% (500-600 papers)
- **ArXiv**: +20% (250 papers)
- **Journal OA**: +10% (120 papers)
- **Google Scholar**: +15% (180 papers)
- **Other sources**: +5% (60 papers)

**Total Expected: 85-90% coverage (~1150 papers)**

## Priority Order

1. **Top 6 conference loaders** → 512 papers (37.7%)
2. **ArXiv enhancement** → +250 papers 
3. **Google Scholar** → +180 papers
4. **Journal APIs** → +120 papers

## Code Structure

```
src/data/pdf/
├── acquisition.py          # Main orchestrator (existing)
├── sources/
│   ├── __init__.py
│   ├── conferences/
│   │   ├── neurips.py     # NeurIPS specific
│   │   ├── icml.py        # PMLR/ICML
│   │   ├── iclr.py        # OpenReview/ICLR
│   │   ├── aaai.py        # AAAI library
│   │   ├── acl.py         # ACL anthology
│   │   └── cvf.py         # CVPR/ICCV/ECCV
│   ├── journals/
│   │   ├── nature.py      # Nature family
│   │   ├── ieee.py        # IEEE Xplore
│   │   └── elsevier.py    # ScienceDirect
│   ├── enhanced/
│   │   ├── scholar.py     # Google Scholar
│   │   ├── websearch.py   # General web search
│   │   └── author_sites.py # Author homepages
│   └── base.py            # Base classes
├── parser.py              # PDF parsing (to implement)
└── cache.py               # Caching logic
```

## Testing Strategy

### Test on Known Papers
1. Select 10 papers from each top venue
2. Verify PDF acquisition works
3. Measure success rate per source

### Performance Targets
- **Per-paper time**: <5 seconds average
- **Success rate**: >85% for top venues
- **Cache hit rate**: >90% on re-runs

## Next Steps

1. **Approve plan and priorities**
2. **Start with NeurIPS loader** (highest impact)
3. **Implement ICML/ICLR** (good APIs)
4. **Test on 100 papers** from top venues
5. **Scale to full corpus**

This plan focuses on the most common venues first, which will give us the highest coverage quickly. The modular design allows parallel development and easy testing of each source.