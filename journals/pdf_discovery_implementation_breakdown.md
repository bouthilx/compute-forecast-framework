# PDF Discovery Implementation Breakdown

**Timestamp**: 2025-01-01 10:30
**Title**: Parallel Implementation Plan for Robust PDF Discovery Infrastructure

## Extended PDF Discovery Sources

### Option 1: Academic API Direct Links (Extended)
- **Semantic Scholar**: openAccessPdf field provides direct PDF URLs
- **OpenAlex**: open_access.oa_url field for open access papers
- **CrossRef**: DOI resolution to publisher sites
- **CORE API**: 200M+ open access papers with direct PDF links
- **BASE (Bielefeld)**: 300M+ documents from 8000+ repositories
- **Microsoft Academic Graph**: Before shutdown, archived data available
- **AMiner**: 320M+ papers from Tang et al.
- **Dimensions.ai**: Free tier API with 100M+ publications
- **Lens.org**: Patent and scholarly literature
- **Scilit**: 140M+ scholarly articles
- **DOAB (Directory of Open Access Books)**: For book chapters
- **OpenAIRE**: European research infrastructure
- **SHARE**: Meta-aggregator of institutional repositories

### Option 2: Venue-Specific Scrapers (Extended)
- **OpenReview API**: ICLR, NeurIPS (2023+), complete PDF access
- **ACL Anthology**: Direct URL construction
- **PMLR**: Machine learning proceedings
- **CVF Open Access**: CVPR/ICCV
- **AAAI Digital Library**: Direct proceedings access
- **IEEE Xplore**: Open access subset
- **Springer Open**: Open access proceedings
- **JMLR**: Journal of Machine Learning Research
- **TACL**: Transactions of ACL
- **AIJ**: Artificial Intelligence Journal archives
- **MLJ**: Machine Learning Journal
- **JAIR**: Journal of AI Research
- **ECML-PKDD**: European conference proceedings
- **UAI**: Uncertainty in AI proceedings
- **AISTATS**: AI and Statistics proceedings
- **CoRL**: Conference on Robot Learning
- **RSS**: Robotics Science and Systems

### Option 3: Preprint & Repository Mining (Extended)
- **arXiv API**: Search by title/author, construct PDF URL from ID
- **bioRxiv/medRxiv**: Life sciences preprints with metadata API
- **HAL**: French research archive with 1M+ documents
- **SSRN**: Social sciences repository
- **OSF Preprints**: Multi-disciplinary preprint aggregator
- **viXra**: Alternative preprint server
- **TechRxiv**: IEEE/engineering preprints
- **engrXiv**: Engineering focused
- **PsyArXiv**: Psychology preprints
- **SocArXiv**: Social sciences
- **EarthArXiv**: Earth sciences
- **Authorea**: Collaborative writing platform
- **Preprints.org**: Multidisciplinary
- **CogPrints**: Cognitive sciences archive
- **PhilSci**: Philosophy of science archive

## Implementation Issues Breakdown

### Issue 1: Core Discovery Framework
**Title**: Implement Base PDF Discovery Framework with Deduplication
**Effort**: L (6-8h)
**Components**:
```python
class PDFDiscoveryFramework:
    def __init__(self):
        self.discovered_papers = {}  # paper_id -> PDFRecord
        self.url_to_papers = {}      # url -> [paper_ids]
        self.title_index = {}        # normalized_title -> [paper_ids]
        
    def add_discovery(self, paper: Paper, pdf_url: str, source: str):
        # Handle deduplication
        # Track multiple versions
        # Score confidence
```

**Key Features**:
- Unified PDFRecord model for all sources
- Deduplication by DOI, arXiv ID, title similarity
- Version tracking (preprint vs published)
- Confidence scoring per source
- URL validation and normalization

### Issue 2: Academic API Collectors (Parallel Work)
**Title**: Implement Academic API PDF Collectors
**Effort**: M (4-6h) per API
**Sub-issues**:
- 2a: Semantic Scholar PDF Collector
- 2b: OpenAlex PDF Collector  
- 2c: CORE API PDF Collector
- 2d: BASE API PDF Collector
- 2e: CrossRef/Unpaywall Collector

**Template Implementation**:
```python
class SemanticScholarPDFCollector(BasePDFCollector):
    def collect_pdfs(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
        # Batch API calls
        # Extract openAccessPdf
        # Handle rate limits
        # Return standardized records
```

### Issue 3: Venue-Specific Scrapers (Parallel Work)
**Title**: Implement Conference/Journal PDF Scrapers
**Effort**: M (4-6h) per venue type
**Sub-issues**:
- 3a: OpenReview Integration (ICLR, NeurIPS)
- 3b: ACL Anthology Scraper (ACL, EMNLP, NAACL)
- 3c: PMLR/JMLR Scraper (ICML, AISTATS)
- 3d: CVF Scraper (CVPR, ICCV, ECCV)
- 3e: AAAI/IJCAI Scraper

**Key Challenges**:
- Handle year-specific URL patterns
- Workshop vs main conference papers
- Supplementary materials

### Issue 4: Preprint Miners (Parallel Work)
**Title**: Implement Preprint Repository Miners
**Effort**: S (2-3h) per repository
**Sub-issues**:
- 4a: Enhanced arXiv Miner (handle versions)
- 4b: bioRxiv/medRxiv Miner
- 4c: HAL Archive Miner
- 4d: Multi-preprint Aggregator

**Special Considerations**:
- Version management (v1, v2, etc.)
- Withdrawal handling
- License extraction

### Issue 5: Deduplication & Version Management
**Title**: Implement Robust Paper Deduplication System
**Effort**: L (6-8h)
**Components**:
```python
class PaperDeduplicator:
    def __init__(self):
        self.similarity_threshold = 0.95
        self.version_patterns = [...]
        
    def find_duplicates(self, paper: Paper) -> List[DuplicateMatch]:
        # Check DOI exact match
        # Check arXiv ID match
        # Fuzzy title + author match
        # Return confidence scores
        
    def resolve_versions(self, duplicates: List[DuplicateMatch]) -> PDFRecord:
        # Prefer: Published > Preprint
        # Prefer: Latest version
        # Merge metadata
```

**Features**:
- DOI normalization and matching
- arXiv ID extraction from various formats
- Fuzzy matching with configurable thresholds
- Version preference rules
- Metadata merging strategies

### Issue 6: Quality Validation Pipeline
**Title**: Implement PDF Discovery Validation Tools
**Effort**: M (4-6h)
**Components**:
```python
class PDFValidator:
    def validate_url(self, url: str) -> ValidationResult:
        # Check URL format
        # Verify HTTP headers
        # Check content-type
        # Estimate file size
        
    def validate_match(self, paper: Paper, pdf_url: str) -> float:
        # Download first page
        # Extract title/authors
        # Compare with metadata
        # Return confidence score
```

### Issue 7: Monitoring & Reporting Dashboard
**Title**: Build PDF Discovery Monitoring Dashboard
**Effort**: M (4-6h)
**Features**:
- Real-time discovery statistics
- Source coverage analysis
- Deduplication metrics
- Failed discovery tracking
- Manual review queue

### Issue 8: Integration Testing Suite
**Title**: Comprehensive PDF Discovery Testing
**Effort**: M (4-6h)
**Test Cases**:
- Multi-version paper handling
- Workshop -> Conference progression
- Retracted paper detection
- URL stability over time
- Source priority validation

## Deduplication Strategy

### Level 1: Exact Matches
```python
exact_matches = {
    'doi': normalize_doi(paper.doi),
    'arxiv_id': extract_arxiv_id(paper),
    'pubmed_id': paper.pubmed_id,
    'semantic_scholar_id': paper.paper_id
}
```

### Level 2: Fuzzy Matches
```python
fuzzy_matches = {
    'title_authors': {
        'title_similarity': fuzz.ratio(title1, title2),
        'author_overlap': jaccard_similarity(authors1, authors2),
        'threshold': 0.9
    }
}
```

### Level 3: Version Detection
```python
version_patterns = [
    r'arxiv:(\d+\.\d+)v(\d+)',  # arXiv versions
    r'workshop|camera-ready|extended',  # Publication stages
    r'preprint|submitted|accepted'  # Status indicators
]
```

## Parallel Execution Plan

### Week 1: Foundation (Can be parallelized)
- **Developer 1**: Core Framework (Issue 1) + Deduplication (Issue 5)
- **Developer 2**: Academic APIs (Issue 2a-2c)
- **Developer 3**: Venue Scrapers (Issue 3a-3b)
- **Developer 4**: Preprint Miners (Issue 4a-4b)

### Week 2: Extension & Integration
- **Developer 1**: Quality Validation (Issue 6)
- **Developer 2**: Remaining APIs (Issue 2d-2e)
- **Developer 3**: Remaining Venues (Issue 3c-3e)
- **Developer 4**: Dashboard (Issue 7) + Testing (Issue 8)

## Success Metrics

### Coverage Targets
- **Mila papers**: 95%+ PDF discovery rate
- **Benchmark papers**: 90%+ PDF discovery rate
- **False positive rate**: <1%
- **Deduplication accuracy**: >98%

### Performance Targets
- **Discovery speed**: <2s per paper (parallelized)
- **Validation speed**: <5s per PDF
- **Daily capacity**: 10,000+ papers

### Quality Metrics
- **URL stability**: 90%+ working after 30 days
- **Version accuracy**: Correctly identify latest version 95%+ time
- **Metadata match**: 95%+ confidence on paper-PDF matching

## Risk Mitigation

### Technical Risks
- **API changes**: Implement adapter pattern for easy updates
- **Rate limits**: Aggressive caching + exponential backoff
- **URL rot**: Periodic re-validation + wayback machine fallback

### Data Risks
- **Incorrect matches**: Manual review queue for low-confidence matches
- **Version confusion**: Clear version tracking + user confirmations
- **License issues**: Respect robots.txt + only open access content

## Next Steps

1. **Immediate**: Create GitHub issues for each sub-task
2. **Day 1**: Start parallel implementation of Issues 1, 2a, 3a, 4a
3. **Day 2-3**: Complete core framework + initial collectors
4. **Day 4-5**: Integration testing + dashboard
5. **Day 6-7**: Full system test + optimization

This parallel approach allows 4+ developers to work simultaneously, reducing total time from 20-30 days to 5-7 days.