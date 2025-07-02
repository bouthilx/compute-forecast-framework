# PDF Infrastructure Plan for Benchmark Paper Extraction

**Timestamp**: 2025-07-01 18:01
**Title**: Comprehensive Plan for PDF Download and Extraction Infrastructure

## Current State Analysis

### Data Availability
- **Total papers**: 804
- **Papers with URLs**: 617 (76.7%)
- **URL type**: Semantic Scholar landing pages (not direct PDF links)
- **Affiliations**: Only 7.7% have affiliation data
- **Abstracts**: Many papers have None/empty abstracts

### Existing Infrastructure
- `ExtractionProtocol` expects full paper content but no PDF parsing exists
- `ComputationalAnalyzer` works on text content
- No PDF download or parsing infrastructure

## Infrastructure Requirements

### 1. PDF Acquisition Layer
```python
class PDFAcquisitionManager:
    """Manages PDF acquisition from multiple sources"""
    
    def __init__(self):
        self.sources = [
            SemanticScholarPDFSource(),
            ArxivPDFSource(),
            UnpaywallPDFSource(),
            OpenAlexPDFSource()
        ]
        self.cache_dir = Path("data/pdf_cache")
        self.metadata_db = Path("data/pdf_metadata.json")
    
    def acquire_pdf(self, paper: Paper) -> Optional[Path]:
        """Try multiple sources to get PDF"""
        # Check cache first
        if cached_pdf := self.check_cache(paper):
            return cached_pdf
            
        # Try each source
        for source in self.sources:
            if pdf_path := source.download(paper):
                self.cache_pdf(paper, pdf_path)
                return pdf_path
        
        return None
```

### 2. PDF Parsing Layer
```python
class PDFParser:
    """Extract text and structure from PDFs"""
    
    def __init__(self):
        self.parsers = [
            PyMuPDFParser(),      # Fast, good for most PDFs
            PDFPlumberParser(),   # Better for tables
            GrobidParser(),       # Academic paper structure
            OCRParser()           # Fallback for scanned PDFs
        ]
    
    def parse_pdf(self, pdf_path: Path) -> ParsedPaper:
        """Extract structured content from PDF"""
        # Try parsers in order of preference
        for parser in self.parsers:
            try:
                return parser.parse(pdf_path)
            except ParsingError:
                continue
        
        raise PDFParsingError(f"All parsers failed for {pdf_path}")
```

### 3. Content Extraction Layer
```python
class EnhancedComputationalExtractor:
    """Extract computational requirements from full papers"""
    
    def __init__(self):
        self.section_detector = AcademicSectionDetector()
        self.table_extractor = TableExtractor()
        self.affiliation_parser = EnhancedAffiliationParser()
        
    def extract_from_paper(self, parsed_paper: ParsedPaper) -> ExtractionResult:
        # Extract affiliations from author section
        affiliations = self.affiliation_parser.extract_from_full_text(
            parsed_paper.author_section
        )
        
        # Extract computational details from relevant sections
        comp_details = self.extract_computational_details(
            parsed_paper.methodology,
            parsed_paper.experiments,
            parsed_paper.appendix
        )
        
        # Extract from tables
        table_data = self.table_extractor.extract_computational_tables(
            parsed_paper.tables
        )
        
        return ExtractionResult(
            affiliations=affiliations,
            computational_requirements=comp_details,
            table_data=table_data
        )
```

## Implementation Plan

### Phase 1: Core Infrastructure (8-10 hours)
1. **PDF Download Manager**
   - Implement Semantic Scholar PDF fetcher
   - Add ArXiv integration for papers with ArXiv IDs
   - Implement caching and rate limiting
   - Add progress tracking and resume capability

2. **Basic PDF Parser**
   - PyMuPDF for text extraction
   - Section detection (abstract, intro, methods, etc.)
   - Basic table extraction

### Phase 2: Enhanced Parsing (6-8 hours)
1. **Academic Structure Parser**
   - Grobid integration for academic paper structure
   - Author/affiliation extraction
   - Reference parsing

2. **Table and Figure Parser**
   - PDFPlumber for complex tables
   - Computational requirement table detection
   - GPU/TPU specification extraction

### Phase 3: Integration (4-6 hours)
1. **Pipeline Integration**
   - Integrate with existing `ExtractionProtocol`
   - Update `execute_benchmark_extraction.py`
   - Add PDF status to tracking

2. **Quality Assurance**
   - Validation of extracted content
   - Comparison with existing abstracts
   - Success rate monitoring

## Technical Stack

### Required Libraries
```toml
[dependency-groups]
pdf = [
    "pymupdf>=1.23.0",      # PDF text extraction
    "pdfplumber>=0.10.0",   # Table extraction
    "requests>=2.31.0",     # PDF downloads
    "aiohttp>=3.9.0",       # Async downloads
    "beautifulsoup4>=4.12", # HTML parsing for landing pages
    "lxml>=5.0",            # XML parsing
    "pytesseract>=0.3.10",  # OCR fallback
    "pillow>=10.0.0",       # Image processing
]
```

### Optional Advanced Tools
- **Grobid**: REST API for academic paper parsing
- **Science Parse**: Allen AI's paper parser
- **Layout Parser**: Deep learning based layout detection

## Expected Outcomes

### Success Metrics
- **PDF acquisition rate**: Target 60-70% of papers
- **Parsing success rate**: Target 90%+ of acquired PDFs
- **Affiliation extraction**: Increase from 7.7% to 70%+
- **Computational detail extraction**: Increase from 1.9% to 30%+

### Risk Mitigation
1. **Access restrictions**: Use Unpaywall for open access versions
2. **PDF quality**: OCR fallback for scanned papers
3. **Rate limiting**: Implement polite crawling with delays
4. **Storage**: Compress and deduplicate PDFs

## Execution Timeline

### Immediate Actions (Today)
1. Create PDF acquisition infrastructure
2. Implement basic Semantic Scholar PDF fetcher
3. Test on sample of 50 papers

### Short Term (2-3 days)
1. Complete all PDF sources
2. Implement full parsing pipeline
3. Process all 362 benchmark papers

### Validation
1. Compare extracted affiliations with known data
2. Validate computational requirements against manual checks
3. Generate quality reports

## Code Structure
```
package/
├── src/
│   ├── data/
│   │   └── pdf/
│   │       ├── __init__.py
│   │       ├── acquisition.py      # PDF download management
│   │       ├── sources.py          # Different PDF sources
│   │       ├── parser.py           # PDF parsing
│   │       ├── extractors.py       # Content extraction
│   │       └── cache.py            # Caching logic
│   └── analysis/
│       └── benchmark/
│           └── pdf_extractor.py    # Integration with benchmark extraction
├── scripts/
│   ├── download_pdfs.py            # Bulk PDF download
│   └── parse_pdfs.py               # Bulk PDF parsing
└── data/
    ├── pdf_cache/                  # Downloaded PDFs
    ├── parsed_papers/              # Parsed content
    └── pdf_metadata.json           # Download/parse status
```

## Alternative Approaches

If PDF acquisition proves challenging:
1. **API Enhancement**: Use Semantic Scholar API v2 for fuller abstracts
2. **Manual Annotation**: Focus on high-value papers
3. **Hybrid Approach**: Combine automated + manual for key papers
4. **Community Datasets**: Look for existing parsed paper datasets

## Next Steps

1. Approve infrastructure plan
2. Implement Phase 1 (PDF acquisition)
3. Test on sample papers
4. Iterate based on results
5. Scale to full corpus

This infrastructure will dramatically improve extraction quality by accessing full paper content rather than just abstracts.