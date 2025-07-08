# Consolidated PDF Infrastructure Implementation Plan

**Timestamp**: 2025-01-01 12:00
**Title**: Complete PDF Discovery, Download, and Parsing Infrastructure

## Overview

This document consolidates the complete implementation plan for PDF infrastructure to unblock issue #74 and enable extraction of computational requirements from research papers.

## 1. PDF Discovery Infrastructure

### Architecture
```
PDFDiscoveryFramework
├── Tier 1: Essential Sources (Must Have)
│   ├── arXiv API (500+ papers, enhanced search)
│   ├── OpenReview API (239+ papers: NeurIPS 2023-24, ICLR, COLM)
│   ├── PMLR (129+ papers: ICML, AISTATS)
│   ├── ACL Anthology (72+ papers: EMNLP, EACL, ACL)
│   └── Semantic Scholar API (cross-venue discovery)
├── Tier 2: High-Value Sources (Should Have)
│   ├── PubMed Central (70+ medical papers)
│   ├── CrossRef/Unpaywall (DOI resolution)
│   ├── OpenAlex API (broad coverage)
│   ├── CVF Open Access (16+ papers: CVPR/ICCV)
│   └── AAAI Digital Library (49 papers)
├── Tier 3: Specialized Sources (Nice to Have)
│   ├── IEEE Xplore API (18+ papers: ICRA, IROS)
│   ├── Nature.com (26 papers: Nature Communications, Scientific Reports)
│   ├── JMLR/TMLR (65 papers)
│   ├── CORE API (institutional repositories)
│   └── HAL Archive (French connections)
└── Deduplication Engine
    ├── Exact matching (DOI, arXiv ID)
    ├── Fuzzy matching (title >95%, authors >85%)
    └── Version management (preprint vs published)
```

### Core Framework Implementation
```python
@dataclass
class PDFRecord:
    paper_id: str
    pdf_url: str
    source: str
    discovery_timestamp: datetime
    confidence_score: float
    version_info: Dict[str, Any]
    validation_status: str
    file_size_bytes: Optional[int]
    license: Optional[str]

class PDFDiscoveryFramework:
    def __init__(self):
        self.discovered_papers = {}  # paper_id -> PDFRecord
        self.url_to_papers = {}      # url -> [paper_ids]
        self.deduplicator = PaperDeduplicator()

    def discover_pdfs(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
        """Main discovery orchestration"""
        # Parallel discovery from all sources
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Submit all discovery tasks
            for collector in self.collectors:
                future = executor.submit(collector.collect_pdfs, papers)
                futures.append((collector.name, future))

            # Collect results
            for source_name, future in futures:
                try:
                    records = future.result(timeout=60)
                    self._merge_records(records, source_name)
                except Exception as e:
                    logger.error(f"{source_name} failed: {e}")

        # Deduplicate and select best URLs
        return self.deduplicator.deduplicate_records(self.discovered_papers)
```

### Deduplication Strategy
```python
class PaperDeduplicator:
    def deduplicate_records(self, all_records: Dict) -> Dict[str, PDFRecord]:
        """Select best PDF for each paper"""

        # Group by paper identity
        paper_groups = self._group_by_identity(all_records)

        # Select best version for each paper
        best_records = {}
        for paper_id, versions in paper_groups.items():
            best_records[paper_id] = self._select_best_version(versions)

        return best_records

    def _select_best_version(self, versions: List[PDFRecord]) -> PDFRecord:
        """Priority: Published > Preprint, Direct > Repository"""
        # Source priority ranking
        priority = {
            'venue_direct': 10,  # ACL, PMLR, etc.
            'semantic_scholar': 8,
            'openalex': 7,
            'arxiv': 5,
            'repository': 3
        }

        return max(versions, key=lambda r: (
            priority.get(r.source, 0),
            r.confidence_score,
            r.discovery_timestamp
        ))
```

## 2. PDF Download Infrastructure

### Simple, Robust Downloader
```python
class SimplePDFDownloader:
    def __init__(self, cache_dir="./pdf_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Academic PDF Collector)'
        })

    def download_pdf(self, url: str, paper_id: str) -> Path:
        """Download PDF with caching and retry logic"""
        # Check cache
        pdf_path = self.cache_dir / f"{paper_id}.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 10000:
            return pdf_path

        # Download with retries
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=30, stream=True)
                response.raise_for_status()

                # Verify content type
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' not in content_type:
                    raise ValueError(f"Not a PDF: {content_type}")

                # Stream to file
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify file
                if pdf_path.stat().st_size < 10000:
                    pdf_path.unlink()
                    raise ValueError("PDF too small")

                return pdf_path

            except Exception as e:
                if attempt == 2:
                    raise PDFDownloadError(f"Failed to download {url}: {e}")
                time.sleep(2 ** attempt)

    def download_batch(self, pdf_records: Dict[str, PDFRecord],
                      max_workers: int = 5) -> Dict[str, Path]:
        """Parallel batch download"""
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_pdf, record.pdf_url, paper_id): paper_id
                for paper_id, record in pdf_records.items()
            }

            for future in as_completed(futures):
                paper_id = futures[future]
                try:
                    pdf_path = future.result()
                    results[paper_id] = pdf_path
                except Exception as e:
                    logger.error(f"Failed to download {paper_id}: {e}")

        return results
```

## 3. PDF Parsing Infrastructure (Optimized)

### Split Processing Strategy
- **First 2 pages**: Advanced processing for affiliations
- **Full document**: Basic extraction for computational specs

### Optimized Parser Implementation
```python
class OptimizedPDFProcessor:
    def __init__(self, config: Dict[str, Any]):
        # Basic extractor (always available)
        self.basic_extractor = PyMuPDFExtractor()

        # Advanced extractors (for first pages only)
        self.ocr_reader = easyocr.Reader(['en'], gpu=True)
        self.grobid_client = GROBIDClient(config.get('grobid_url'))

        # Cloud services (fallback)
        self.google_vision = GoogleVisionClient(config.get('google_key'))
        self.claude_vision = ClaudeVisionClient(config.get('anthropic_key'))

    def process_pdf(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
        """Main processing pipeline"""

        # Step 1: Process first 2 pages for affiliations
        affiliation_data = self._extract_affiliations(pdf_path, paper_metadata)

        # Step 2: Extract full text for computational specs
        full_text = self.basic_extractor.extract_full_text(pdf_path)

        # Step 3: Extract computational requirements
        comp_specs = self._extract_computational_specs(full_text)

        return {
            **affiliation_data,
            'full_text': full_text,
            'computational_specs': comp_specs,
            'extraction_timestamp': datetime.now()
        }

    def _extract_affiliations(self, pdf_path: Path, metadata: Dict) -> Dict:
        """Multi-level extraction for first 2 pages only"""

        # Level 1: Try basic extraction
        first_pages_text = self.basic_extractor.extract_pages(pdf_path, [0, 1])
        affiliations = self._parse_affiliations(first_pages_text)

        if self._affiliations_complete(affiliations, metadata):
            return {'affiliations': affiliations, 'method': 'basic'}

        # Level 2: Try EasyOCR
        if self.ocr_reader:
            ocr_text = self._ocr_first_pages(pdf_path)
            affiliations = self._parse_affiliations(ocr_text)

            if self._affiliations_complete(affiliations, metadata):
                return {'affiliations': affiliations, 'method': 'ocr'}

        # Level 3: Try GROBID
        if self.grobid_client:
            grobid_data = self.grobid_client.process_header(pdf_path)
            if grobid_data.get('affiliations'):
                return {'affiliations': grobid_data['affiliations'], 'method': 'grobid'}

        # Level 4: Cloud services (last resort)
        if self.claude_vision and len(affiliations) < len(metadata.get('authors', [])) * 0.5:
            cloud_data = self._extract_with_claude(pdf_path, metadata)
            if cloud_data:
                return {'affiliations': cloud_data, 'method': 'claude'}

        return {'affiliations': affiliations, 'method': 'partial'}

    def _extract_computational_specs(self, full_text: str) -> Dict[str, Any]:
        """Extract computational requirements from full text"""
        specs = {
            'gpu_info': self._extract_gpu_info(full_text),
            'training_time': self._extract_training_time(full_text),
            'model_size': self._extract_model_size(full_text),
            'dataset_info': self._extract_dataset_info(full_text),
            'computational_budget': self._extract_computational_budget(full_text)
        }

        # Find relevant sections
        comp_sections = self._find_computational_sections(full_text)
        specs['relevant_sections'] = comp_sections

        return specs

    def _extract_gpu_info(self, text: str) -> Dict[str, Any]:
        """Extract GPU/TPU information"""
        gpu_patterns = [
            r'(\d+)\s*×?\s*(V100|A100|A6000|RTX\s*\d+|TPU|GPU)',
            r'(V100|A100|A6000|RTX\s*\d+|TPU).*?(\d+)\s*(?:GPUs?|cards?|devices?)',
            r'trained on\s*(\d+)\s*(V100|A100|A6000|RTX\s*\d+|TPU|GPU)'
        ]

        results = {}
        for pattern in gpu_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                results['devices'] = matches
                break

        return results
```

### Technology Stack Summary
1. **PDF Discovery**:
   - Primary: Semantic Scholar, OpenAlex, arXiv
   - Venue-specific: OpenReview, ACL, PMLR
   - Deduplication: Multi-level matching

2. **PDF Download**:
   - Simple requests-based downloader
   - Retry logic with exponential backoff
   - Local caching to avoid re-downloads

3. **PDF Parsing**:
   - PyMuPDF: Basic text extraction (all pages)
   - EasyOCR: First 2 pages for affiliations
   - GROBID: Academic structure (first 2 pages)
   - Cloud APIs: Fallback for difficult cases

## Implementation Timeline

### Phase 1: Tier 1 Sources + Core (Days 1-2)
**Parallel Tasks**:
- Developer 1: PDF Discovery Framework + Deduplication Engine
- Developer 2: arXiv Enhanced + Semantic Scholar API
- Developer 3: OpenReview + PMLR + ACL Anthology
- Developer 4: PDF Download + Optimized Parser

**Expected Coverage**: 75-85% of papers

### Phase 2: Tier 2 Sources (Day 3)
**Parallel Tasks**:
- Developer 1: PubMed Central + Medical journals
- Developer 2: CrossRef/Unpaywall + OpenAlex
- Developer 3: CVF + AAAI scrapers
- Developer 4: Integration testing + monitoring

**Expected Coverage**: 90-95% of papers

### Phase 3: Tier 3 Sources + Polish (Day 4)
**Parallel Tasks**:
- Developer 1: IEEE/Nature/JMLR scrapers
- Developer 2: CORE/HAL integration
- Developer 3: Full pipeline testing
- Developer 4: Dashboard + documentation

**Expected Coverage**: 95-99% of papers

## Test Papers for Pipeline Validation

### Test Set (Diverse Sources & Formats):
1. **Attention Is All You Need** - https://arxiv.org/pdf/1706.03762
   - Source: arXiv
   - Challenge: Multi-institution affiliations (Google Brain, Google Research, University of Toronto)
   - Computational specs: TPU training details

2. **Network Dissection** - https://papers.baulab.info/papers/Senior-2020.pdf
   - Source: Direct URL (non-standard)
   - Challenge: Non-arXiv PDF, complex author list
   - Computational specs: GPU cluster details

3. **Training language models to follow instructions** - https://papers.baulab.info/papers/Ouyang-2022.pdf
   - Source: Direct URL
   - Challenge: OpenAI paper, extensive computational details
   - Computational specs: Large-scale GPU training

4. **Learning Transferable Visual Models** (CLIP) - https://papers.baulab.info/papers/Radford-2021.pdf
   - Source: Direct URL
   - Challenge: Dense formatting, multiple experiments
   - Computational specs: 256 V100 GPUs training

5. **How transferable are features** - https://papers.baulab.info/papers/Yosinksi-2014.pdf
   - Source: Direct URL
   - Challenge: Older paper format
   - Computational specs: Historical GPU usage

6. **Neural Machine Translation** - https://papers.baulab.info/papers/Bahdanau-2015.pdf
   - Source: Direct URL
   - Challenge: Early deep learning paper
   - Computational specs: Training time on GPUs

## Coverage Analysis for Top 15 Mila Venues

### Top 15 Mila Publication Venues (2019-2024):
1. **NeurIPS**: 152 papers → OpenReview, NeurIPS Proceedings, arXiv
2. **ICML**: 122 papers → PMLR, arXiv
3. **ICLR**: 94 papers → OpenReview, arXiv
4. **TMLR**: 54 papers → JMLR/TMLR site, arXiv
5. **AAAI**: 49 papers → AAAI Digital Library, arXiv
6. **EMNLP**: 41 papers → ACL Anthology, arXiv
7. **EACL**: 31 papers → ACL Anthology, arXiv
8. **Radiotherapy and Oncology**: 18 papers → Elsevier, PubMed Central
9. **Journal of Pediatric Surgery**: 17 papers → Elsevier, PubMed Central
10. **CVPR**: 16 papers → CVF Open Access, arXiv
11. **Nature Communications**: 15 papers → Nature.com, PubMed Central
12. **ICRA**: 12 papers → IEEE Xplore, arXiv
13. **Scientific Reports**: 11 papers → Nature.com, PubMed Central
14. **COLM**: 11 papers → OpenReview
15. **Trans. Mach. Learn. Res.**: 11 papers → JMLR site

### PDF Source Distribution Estimate:
- **arXiv**: ~40% of papers (cross-venue preprints)
- **Conference sites**: ~35% (OpenReview, PMLR, ACL, etc.)
- **Journal publishers**: ~15% (Elsevier, Nature, IEEE)
- **Other sources**: ~10% (institutional repos, author pages)

## GitHub Issues Summary

### Core Infrastructure:
1. **#75**: PDF Discovery Framework with Multi-Source Orchestration (L, 6-8h)
2. **#76**: Deduplication Engine with Version Management (L, 6-8h)

### Tier 1 Sources (Critical Path):
3. **#77**: arXiv Enhanced Discovery (M, 4-6h)
4. **#78**: OpenReview API Integration (M, 4-6h)
5. **#79**: PMLR Direct Scraper (S, 2-3h)
6. **#80**: ACL Anthology Scraper (S, 2-3h)
7. **#81**: Semantic Scholar Collector (M, 4-6h)

### Tier 2 Sources (High Value):
8. **#82**: PubMed Central Harvester (M, 4-6h)
9. **#83**: CrossRef/Unpaywall Resolver (S, 2-3h)
10. **#84**: OpenAlex Integration (S, 2-3h)
11. **#85**: CVF Open Access Scraper (S, 2-3h)
12. **#86**: AAAI Proceedings Scraper (M, 4-6h)

### Tier 3 Sources (Extended Coverage):
13. **#87**: IEEE Xplore Metadata Extractor (M, 4-6h)
14. **#88**: Nature.com Scraper (M, 4-6h)
15. **#89**: JMLR/TMLR Site Scraper (S, 2-3h)
16. **#90**: CORE/HAL API Integration (S, 2-3h)

### System Components:
17. **#91**: Simple PDF Download Manager (S, 2-3h)
18. **#92**: Optimized PDF Parser (Split Strategy) (M, 4-6h)
19. **#93**: Monitoring Dashboard (M, 4-6h)

### Total Effort:
- 4 developers × 4 days = 16 developer-days
- ~45-55 hours of implementation work

## Success Metrics

### Coverage Targets:
- **Top 8 ML venues**: 95%+ PDF discovery
- **Top 15 all venues**: 90%+ PDF discovery
- **Overall Mila papers**: 85%+ PDF discovery
- **Affiliation extraction**: 70%+ accuracy
- **Computational specs**: 80%+ extraction rate

### Performance Targets:
- Discovery: <3s per paper (15 sources checked)
- Download: <5s per paper
- Parsing: 5-15s per paper
- Total pipeline: <25s per paper

### Cost Targets:
- Average cost: $0.002-0.010 per paper
- Maximum cost: $0.02 per paper (cloud services)
- 90%+ papers processed with free tools only

### Source Effectiveness:
- Phase 1 (5 sources): 75-85% coverage
- Phase 2 (10 sources): 90-95% coverage
- Phase 3 (15 sources): 95-99% coverage
