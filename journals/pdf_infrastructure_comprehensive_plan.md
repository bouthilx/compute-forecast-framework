# Comprehensive PDF Infrastructure Plan

**Timestamp**: 2025-01-01 10:15
**Title**: Exhaustive PDF Discovery, Download, and Parsing Alternatives

## Context

Issue #74 is blocked due to lack of PDF infrastructure. The existing corpus (804 papers) only contains metadata, preventing execution of benchmark extraction. This document provides comprehensive alternatives for implementing PDF handling capabilities.

## 1. PDF Discovery (Finding PDF URLs/Locations)

### Option 1: **Academic API Direct Links**
- **Semantic Scholar**: `openAccessPdf` field provides direct PDF URLs
- **OpenAlex**: `open_access.oa_url` field for open access papers
- **CrossRef**: DOI resolution to publisher sites
- **CORE API**: 200M+ open access papers with direct PDF links
- **BASE (Bielefeld)**: 300M+ documents from 8000+ repositories

### Option 2: **Venue-Specific Scrapers**
- **OpenReview API**: ICLR, NeurIPS (2023+), complete PDF access
- **ACL Anthology**: Direct URL construction (`aclanthology.org/{venue}{year}.{paper_id}.pdf`)
- **PMLR**: Machine learning proceedings (`proceedings.mlr.press/v{volume}/{paper}.pdf`)
- **CVF Open Access**: CVPR/ICCV (`openaccess.thecvf.com/{venue}{year}/papers/*.pdf`)
- **AAAI Digital Library**: Direct proceedings access

### Option 3: **Preprint & Repository Mining**
- **arXiv API**: Search by title/author, construct PDF URL from ID
- **bioRxiv/medRxiv**: Life sciences preprints with metadata API
- **HAL**: French research archive with 1M+ documents
- **SSRN**: Social sciences repository
- **OSF Preprints**: Multi-disciplinary preprint aggregator

### Option 4: **Web Search & Scraping**
- **Google Scholar**: Using `scholarly` Python library + custom scrapers
- **Microsoft Academic**: Graph API for paper metadata and links
- **ResearchGate**: Profile scraping for author uploads
- **Academia.edu**: Similar academic social network mining
- **DuckDuckGo API**: Privacy-friendly web search for PDFs

### Option 5: **DOI Resolution Services**
- **Unpaywall**: 30M+ free papers via DOI
- **DOAJ (Directory of Open Access Journals)**: 17k+ journals
- **PubMed Central**: Biomedical papers with OAI-PMH
- **Europe PMC**: European mirror with REST API
- **Zenodo**: CERN's repository for research outputs

### Option 6: **Institutional Repositories**
- **OAI-PMH Protocol**: Harvest metadata from 4000+ repositories
- **DSpace/EPrints**: Common repository software with APIs
- **University IR crawlers**: MIT DSpace, Stanford Digital Repository
- **Lab websites**: Direct scraping of research group pages
- **Author homepages**: Personal publication lists

### Option 7: **Aggregator Services**
- **Paperscape**: arXiv visualization with download links
- **Papers With Code**: ML papers linked to implementations
- **Connected Papers**: Graph-based paper discovery
- **Semantic Reader**: Allen AI's enhanced paper reader
- **Lens.org**: 225M+ scholarly works

## 2. PDF Download (Fetching Files)

### Option 1: **requests + Enhanced Headers**
```python
import requests
from fake_useragent import UserAgent

headers = {
    'User-Agent': UserAgent().random,
    'Accept': 'application/pdf',
    'Referer': 'https://scholar.google.com'
}
response = requests.get(url, headers=headers, timeout=30)
```

### Option 2: **httpx (Async Support)**
```python
import httpx

async with httpx.AsyncClient() as client:
    tasks = [client.get(url) for url in pdf_urls]
    responses = await asyncio.gather(*tasks)
```

### Option 3: **Selenium/Playwright (JavaScript Required)**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    # Handle JavaScript redirects, captchas
    pdf_content = page.pdf()
```

### Option 4: **wget/curl Subprocess**
```python
import subprocess

subprocess.run([
    'wget', 
    '--user-agent="Mozilla/5.0"',
    '--no-check-certificate',
    '--timeout=30',
    '-O', output_path,
    pdf_url
])
```

### Option 5: **Specialized Libraries**
- **newspaper3k**: Article extraction with PDF support
- **trafilatura**: Web scraping focused on text extraction
- **PyPDF2**: Can fetch PDFs from URLs directly
- **pdfkit**: HTML to PDF conversion (for HTML papers)
- **weasyprint**: Another HTML to PDF converter

### Option 6: **Cloud Services**
- **ScraperAPI**: Handles proxies, browsers, CAPTCHAs
- **Crawlera**: Smart proxy rotation by Scrapinghub
- **ProxyCrawl**: PDF-specific extraction API
- **ScrapeOwl**: JavaScript rendering support
- **Apify**: Actor-based web scraping platform

### Option 7: **CDN & Cache Services**
- **Wayback Machine API**: Historical PDF versions
- **Archive.today**: Alternative web archive
- **Google Cache**: Cached PDF versions
- **Cloudflare Workers**: Edge computing for PDF fetch
- **IPFS Gateways**: Decentralized PDF storage

## 3. PDF Parsing (Text Extraction)

### Option 1: **PyMuPDF (fitz)**
```python
import fitz  # PyMuPDF

doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()
```
- **Pros**: Fast, handles complex layouts, extracts images
- **Cons**: Large dependency

### Option 2: **pdfplumber**
```python
import pdfplumber

with pdfplumber.open(pdf_path) as pdf:
    text = ''
    for page in pdf.pages:
        text += page.extract_text()
        # Also: extract_tables(), extract_words()
```
- **Pros**: Excellent table extraction, precise layout
- **Cons**: Slower than PyMuPDF

### Option 3: **OCR Solutions**
- **Tesseract + pytesseract**: Open source OCR for scanned PDFs
- **EasyOCR**: Deep learning based, 80+ languages
- **PaddleOCR**: High accuracy, lightweight
- **Azure Computer Vision**: Cloud OCR API
- **Google Cloud Vision**: Another cloud option

### Option 4: **Academic-Specific Parsers**
- **GROBID**: Machine learning for scholarly PDFs
  ```bash
  # Run as service
  docker run -p 8070:8070 lfoppiano/grobid:0.7.3
  ```
- **Science Parse**: Allen AI's paper parser
- **CERMINE**: Content ExtRactor for Machine INterpretation
- **pdffigures2**: Extract figures and tables
- **doc2text**: Scholarly document parser

### Option 5: **LLM-Based Extraction**
- **Unstructured.io**: LLM-powered document parsing
- **LlamaIndex**: PDF parsing with semantic chunking
- **Docugami**: ML-based document understanding
- **ChatPDF**: API for PDF Q&A and extraction
- **Claude/GPT-4**: Direct PDF parsing capability

### Option 6: **Traditional Libraries**
- **PyPDF2**: Basic text extraction
- **pdfminer.six**: Low-level PDF parsing
- **Tika**: Apache's document parsing toolkit
- **Camelot**: Table extraction focus
- **Tabula-py**: Java tabula wrapper for tables

### Option 7: **Hybrid & Pipeline Approaches**
- **pdf2image + OCR**: Convert to images first
- **pdftotext (Linux)**: Command line tool
- **MuPDF CLI tools**: mutool extract
- **Poppler utils**: pdftotext, pdfinfo, pdftocairo
- **LibreOffice headless**: PDF to text conversion

## Recommended Implementation Strategy

### Phase 1: Quick Wins (1 day)
1. **PyMuPDF** for parsing (fast, reliable)
2. **Semantic Scholar + ArXiv** for discovery (40-50% coverage)
3. **requests** with retry logic for downloads

### Phase 2: Conference Sources (2 days)
1. **OpenReview API** for ICLR/NeurIPS
2. **ACL Anthology** scraper
3. **PMLR** direct URL construction
4. **pdfplumber** for better table extraction

### Phase 3: Enhanced Coverage (2 days)
1. **Unpaywall + CORE** for DOI resolution
2. **Google Scholar** via scholarly library
3. **GROBID** service for academic parsing
4. **Playwright** for JavaScript-heavy sites

### Phase 4: Advanced Features (optional)
1. **OCR pipeline** for scanned PDFs
2. **Cloud services** for difficult cases
3. **LLM extraction** for complex layouts

## Critical Path Impact

Without PDF infrastructure:
- **Current extraction rate**: 1.9% (7/362 papers)
- **Affiliation coverage**: 7.7%
- **Computational specs**: ~0%

With PDF infrastructure:
- **Expected extraction rate**: 95%+
- **Affiliation coverage**: 70%+
- **Computational specs**: 80%+

This represents a **50x improvement** in data availability, unblocking:
- Issue #74 (E0: Execute M3-1 Benchmark Extraction)
- Issue #58 (M3-2: Benchmark Paper Suppression Metrics)
- Issue #30 (M4-1: Mila Paper Processing)
- All downstream analysis and report generation

## Time Investment Justification

Despite time constraints, this infrastructure is critical because:
1. **All analysis depends on it** - Without PDFs, we have no computational requirements data
2. **One-time investment** - Built once, used for all papers
3. **Multiplicative impact** - Enables 50x more data extraction
4. **No alternatives** - Can't extract GPU hours from abstracts alone

Recommended time budget: **5-7 days** for full implementation, or **2-3 days** for Phase 1-2 covering 70-80% of papers.