# PDF Extraction Infrastructure Analysis

**Timestamp**: 2025-07-01 18:05
**Title**: Analysis of Current State and PDF Infrastructure Requirements

## Executive Summary

The current benchmark extraction pipeline has a **1.9% success rate** due to:
1. **Missing affiliations**: Only 7.7% of papers have affiliation data
2. **Limited text content**: Many papers have None/empty abstracts
3. **No full-text access**: Extraction relies only on metadata, not paper content

To achieve the required 30-50% extraction success rate for M3-2, we need full paper content through PDF extraction.

## Current Infrastructure Analysis

### Available Data
- **804 total papers** in corpus
- **617 papers (77%)** have Semantic Scholar URLs
- **362 papers** identified as benchmarks (SOTA or from target institutions)
- **Current extraction**: 7 successful out of 362 (1.9%)

### URL Analysis
```json
{
  "url_availability": {
    "papers_with_urls": 617,
    "url_format": "https://www.semanticscholar.org/paper/{paper_id}",
    "direct_pdf_links": 0,
    "requires_pdf_discovery": true
  }
}
```

### Existing Infrastructure Gaps
1. **No PDF download capability**
2. **No PDF parsing infrastructure**
3. **Extraction expects text but gets only metadata**
4. **No affiliation extraction from full text**

## Semantic Scholar PDF Access Options

### 1. Direct API Enhancement
The Semantic Scholar API v2 supports an `openAccessPdf` field:
```python
params = {
    'fields': 'paperId,title,authors,venue,year,citationCount,abstract,url,openAccessPdf',
    'limit': 100
}
```

### 2. Web Scraping Approach
From the Semantic Scholar landing page, extract:
- PDF links from the page
- ArXiv IDs for direct ArXiv access
- DOI for Unpaywall lookup

### 3. Alternative Sources
- **ArXiv**: ~40% of ML papers have ArXiv versions
- **Unpaywall**: Open access versions via DOI
- **OpenAlex**: May have full-text links

## Recommended Implementation Strategy

### Phase 1: Quick Win with API Enhancement (2-3 hours)
```python
# 1. Update Semantic Scholar client to request openAccessPdf
def get_paper_with_pdf(paper_id: str) -> dict:
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {
        'fields': 'paperId,title,authors,venue,year,openAccessPdf,externalIds'
    }
    response = requests.get(url, params=params)
    return response.json()

# 2. Download PDFs where available
def download_pdf(pdf_url: str, paper_id: str) -> Path:
    pdf_path = Path(f"data/pdfs/{paper_id}.pdf")
    response = requests.get(pdf_url, stream=True)
    with open(pdf_path, 'wb') as f:
        f.write(response.content)
    return pdf_path
```

### Phase 2: Basic PDF Extraction (4-6 hours)
```python
# 1. Simple PDF text extraction
import pymupdf  # PyMuPDF

def extract_text_from_pdf(pdf_path: Path) -> dict:
    doc = pymupdf.open(pdf_path)
    sections = {
        'full_text': '',
        'abstract': '',
        'authors': '',
        'methodology': '',
        'experiments': ''
    }
    
    for page in doc:
        text = page.get_text()
        sections['full_text'] += text
        
        # Basic section detection
        if 'abstract' in text.lower() and not sections['abstract']:
            sections['abstract'] = extract_section(text, 'abstract')
        # ... similar for other sections
    
    return sections

# 2. Enhanced affiliation extraction
def extract_affiliations_from_pdf(sections: dict) -> List[dict]:
    # Look for author section
    author_section = sections.get('authors', '')
    # Apply enhanced affiliation parser
    return affiliation_parser.parse_author_section(author_section)
```

### Phase 3: Integration with Existing Pipeline (2-3 hours)
```python
# Update execute_benchmark_extraction.py
def enhanced_extraction_pipeline(papers):
    for paper in papers:
        # 1. Try to get PDF URL
        pdf_url = get_pdf_url(paper)
        
        if pdf_url:
            # 2. Download PDF
            pdf_path = download_pdf(pdf_url, paper.paper_id)
            
            # 3. Extract full text
            full_content = extract_text_from_pdf(pdf_path)
            
            # 4. Run extraction on full content
            paper.full_text = full_content['full_text']
            paper.extracted_affiliations = extract_affiliations_from_pdf(full_content)
        
        # 5. Run existing extraction (now with more content)
        extraction_result = extractor.extract(paper)
```

## Expected Improvements

### With PDF Extraction
- **Affiliation coverage**: 7.7% → 70%+
- **Full abstracts**: 60% → 95%+
- **Computational details**: 1.9% → 30-40%
- **Extraction confidence**: Low → Medium/High

### Success Metrics
1. **PDF acquisition rate**: 50-60% of papers
2. **Text extraction success**: 90%+ of PDFs
3. **Affiliation extraction**: 80%+ of PDFs
4. **Computational requirement extraction**: 30%+ of PDFs

## Risk Mitigation

### Technical Risks
1. **Rate limiting**: Implement polite crawling (2-3 sec delays)
2. **PDF parsing failures**: Use multiple parsers as fallback
3. **Storage**: ~50MB per PDF × 400 papers = 20GB (manageable)

### Access Risks
1. **Paywalled content**: Focus on open access papers
2. **Missing PDFs**: Use multiple sources (ArXiv, Unpaywall)
3. **Legal concerns**: Only access open access content

## Immediate Next Steps

1. **Test PDF availability** (30 min)
   ```bash
   # Quick test on 10 papers
   python test_pdf_availability.py
   ```

2. **Implement basic PDF pipeline** (2-3 hours)
   - Add openAccessPdf to API requests
   - Download available PDFs
   - Extract text with PyMuPDF

3. **Run enhanced extraction** (1 hour)
   - Process benchmark papers with PDFs
   - Compare extraction rates

4. **Iterate based on results**
   - Add more PDF sources if needed
   - Enhance parsing for specific sections

## Alternative: Minimum Viable Approach

If PDF extraction proves too complex:

1. **Use Semantic Scholar API v2** for better abstracts
2. **Manual annotation** of top 50-100 papers
3. **Focus on papers with existing full abstracts**
4. **Lower extraction targets** for M3-2

## Recommendation

**Proceed with Phase 1 immediately** - the API enhancement is low-risk and can provide quick improvements. Based on results, decide whether to invest in full PDF infrastructure or pivot to alternative approaches.

The 1.9% extraction rate is unacceptable for meaningful analysis. With PDF access, we can realistically achieve 30-40% extraction rates, making M3-2 analysis viable.