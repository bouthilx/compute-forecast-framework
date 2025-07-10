# Revised Scraper Implementation Plan

## Key Discovery: Collectors Already Exist!

The package already has comprehensive PDF discovery collectors for all our priority venues. **No new scrapers needed** - we just need to integrate them into a unified paper collection pipeline.

## Existing Coverage Analysis

### ✅ **Fully Covered Priority Venues**

1. **CVF Collector** (`cvf_collector.py`)
   - CVPR, ICCV, ECCV, WACV
   - Covers 16+ Mila papers
   - Status: ✅ Ready to use

2. **ACL Anthology Collector** (`acl_anthology_collector.py`)
   - ACL, EMNLP, NAACL, COLING
   - Covers 12+ Mila papers
   - Status: ✅ Ready to use

3. **AAAI Collector** (`aaai_collector.py`)
   - AAAI conferences
   - Covers 14 Mila papers
   - Status: ✅ Ready to use

4. **Nature Collector** (`nature_collector.py`)
   - Nature Communications, Scientific Reports
   - Covers 15+ Mila papers
   - Status: ✅ Ready to use

### ✅ **Additional Coverage**

5. **PMLR Collector** (`pmlr_collector.py`)
   - ICML, AISTATS, UAI, COLT
   - Covers paperoni gaps
   - Status: ✅ Ready to use

6. **OpenReview Collector** (`openreview_collector.py`)
   - ICLR + workshops
   - Complements paperoni
   - Status: ✅ Ready to use

7. **Medical/Bio Journals** (`pubmed_central_collector.py`)
   - Medical journals (35+ Mila papers)
   - Status: ✅ Ready to use

8. **ArXiv Collector** (`arxiv_collector.py`)
   - Preprints with venue inference
   - Status: ✅ Ready to use

## New Implementation Strategy

Instead of building scrapers, implement:

### 1. **Unified Collection Pipeline**
```python
# comprehensive_paper_collector.py
class ComprehensivePaperCollector:
    """Unified collector using existing PDF discovery framework"""

    def __init__(self):
        self.framework = PDFDiscoveryFramework()
        self._setup_collectors()
        self._configure_venue_priorities()

    def collect_by_venues(self, venues: List[str], years: List[int]):
        """Collect papers from specific venues using optimal collectors"""

    def collect_by_institutions(self, institutions: List[str], years: List[int]):
        """Collect by institution with multi-source enrichment"""
```

### 2. **Venue-Specific Collection Strategies**
```python
venue_strategies = {
    'NeurIPS': ['paperoni_neurips', 'arxiv', 'openreview'],
    'ICML': ['paperoni_pmlr', 'pmlr_collector', 'arxiv'],
    'ICLR': ['paperoni_openreview', 'openreview_collector'],
    'CVPR': ['cvf_collector', 'arxiv', 'ieee'],
    'ACL': ['acl_anthology_collector', 'arxiv'],
    'AAAI': ['aaai_collector', 'arxiv'],
    'Nature Communications': ['nature_collector', 'pubmed', 'doi_resolver']
}
```

### 3. **Enhanced Institution Filtering**
```python
class InstitutionMatcher:
    """Dynamic institution matching beyond paperoni dataset"""

    def extract_affiliations(self, paper: Paper) -> List[str]:
        """Extract affiliations from paper metadata"""

    def is_mila_paper(self, paper: Paper) -> bool:
        """Check if paper has Mila affiliation"""

    def get_benchmark_papers(self, institutions: List[str]) -> List[Paper]:
        """Get papers from benchmark institutions"""
```

### 4. **Data Integration & Deduplication**
```python
class PaperAggregator:
    """Aggregate and deduplicate papers from multiple sources"""

    def merge_sources(self, papers_by_source: Dict[str, List[Paper]]) -> List[Paper]:
        """Merge papers with source priority and deduplication"""

    def enrich_metadata(self, papers: List[Paper]) -> List[Paper]:
        """Enrich with citations, affiliations, computational metadata"""
```

## Implementation Priority

### Phase 1: Integration (HIGH)
1. **Fix venue collection orchestrator merge conflict**
2. **Create unified collection pipeline using existing collectors**
3. **Implement dynamic institution matching**
4. **Test with top 5 venues**

### Phase 2: Enhancement (MEDIUM)
5. **Add benchmark institution filtering**
6. **Implement comprehensive deduplication**
7. **Add computational metadata extraction**
8. **Create monitoring dashboard**

### Phase 3: Scale (LOW)
9. **Optimize for large-scale collection**
10. **Add incremental update capabilities**
11. **Implement quality validation**
12. **Create automated reporting**

## Benefits of This Approach

### ✅ **Advantages**
- **Leverages existing work** - no reinventing the wheel
- **Comprehensive coverage** - all major venues covered
- **Battle-tested collectors** - already implemented and working
- **Faster implementation** - integration vs building from scratch
- **Better maintenance** - extend existing vs maintain new code

### ✅ **Coverage Comparison**
- **Package + Paperoni**: 95%+ venue coverage
- **OpenAlex only**: 30-40% venue coverage (conferences)
- **Paperoni only**: 60-70% venue coverage

## Next Steps

1. **Investigate existing venue collection orchestrator**
2. **Fix merge conflicts**
3. **Design unified collection interface**
4. **Implement institution-based filtering**
5. **Create comprehensive test suite**

This approach will give us the **best possible coverage** by combining the strengths of both paperoni (structured data for specific venues) and the package's comprehensive PDF discovery framework.
