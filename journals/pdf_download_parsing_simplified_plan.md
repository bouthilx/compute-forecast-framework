# Simplified PDF Download & Parsing Plan

**Timestamp**: 2025-01-01 11:00
**Title**: Streamlined Implementation for PDF Download and Parsing

## 2. PDF Download (Simplified)

### Recommended Approach: Simple & Robust

```python
import requests
from urllib.parse import urlparse
import time
from pathlib import Path

class SimplePDFDownloader:
    def __init__(self, cache_dir="./pdf_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Academic PDF Collector)'
        })

    def download_pdf(self, url: str, paper_id: str) -> Path:
        """Simple, reliable PDF download with caching"""
        # Check cache first
        pdf_path = self.cache_dir / f"{paper_id}.pdf"
        if pdf_path.exists():
            return pdf_path

        # Download with retries
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Verify it's actually a PDF
                if 'application/pdf' in response.headers.get('content-type', ''):
                    pdf_path.write_bytes(response.content)
                    return pdf_path

            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
```

**Why this approach**:
- Uses standard `requests` library (already in dependencies)
- Simple retry logic with exponential backoff
- Built-in caching to avoid re-downloads
- No complex dependencies or frameworks

## 3. PDF Parsing - Technology Options

### Option 1: OCR Solutions for Scanned PDFs

**Please choose one:**

1. **Tesseract + pytesseract** (Open Source)
   - Pros: Free, well-maintained, good accuracy
   - Cons: Requires system install of Tesseract
   - Install: `apt install tesseract-ocr` + `pip install pytesseract`

2. **EasyOCR** (Deep Learning)
   - Pros: Better accuracy, pure Python, GPU support
   - Cons: Larger download (~500MB models), slower on CPU
   - Install: `pip install easyocr`

3. **PaddleOCR** (Lightweight)
   - Pros: Fast, accurate, small models
   - Cons: Less documentation, Chinese origin
   - Install: `pip install paddlepaddle paddleocr`

4. **OCRmyPDF** (PDF-specific)
   - Pros: Designed for PDFs, preserves structure
   - Cons: Another system dependency
   - Install: `apt install ocrmypdf`

### Option 2: Cloud Services for Difficult Cases

**Please choose one or more:**

1. **Google Cloud Vision API**
   - Pros: Excellent accuracy, handles complex layouts
   - Cons: Requires API key, costs money
   - Price: $1.50 per 1000 pages

2. **AWS Textract**
   - Pros: Good for tables/forms, reliable
   - Cons: AWS setup complexity
   - Price: $1.50 per 1000 pages

3. **Azure Computer Vision**
   - Pros: Good OCR, integrates with other Azure services
   - Cons: Azure complexity
   - Price: $1.00 per 1000 pages

4. **OpenAI Vision API**
   - Pros: Can understand context, handle complex layouts
   - Cons: More expensive, rate limits
   - Price: ~$0.01 per page

5. **Claude Vision API**
   - Pros: Excellent understanding, can extract specific fields
   - Cons: Higher cost, rate limits
   - Price: ~$0.01-0.02 per page

### Option 3: LLM Extraction for Complex Layouts

**Please choose approach:**

1. **Direct LLM Processing**
   ```python
   # Convert PDF to images, send to LLM
   - PDF → Images → Claude/GPT-4V → Structured extraction
   ```

2. **Hybrid Approach**
   ```python
   # Traditional extraction + LLM for difficult parts
   - PyMuPDF for clean text
   - LLM only for tables/complex sections
   ```

3. **Specialized Tools + LLM**
   ```python
   # Use GROBID/ScienceParse + LLM refinement
   - GROBID for structure
   - LLM for missing/complex fields
   ```

## Recommended Implementation Path

### Phase 1: Basic Pipeline
```python
class PDFProcessor:
    def __init__(self):
        self.downloader = SimplePDFDownloader()
        self.parser = PyMuPDFParser()  # Already proven to work

    def process_paper(self, paper: Paper, pdf_url: str) -> ExtractedContent:
        # Download
        pdf_path = self.downloader.download_pdf(pdf_url, paper.paper_id)

        # Parse
        text = self.parser.extract_text(pdf_path)

        # If text is too short/empty, trigger OCR
        if len(text) < 1000:
            text = self.ocr_fallback(pdf_path)

        return ExtractedContent(text=text, source="pdf")
```

### Phase 2: Add Fallbacks
- OCR for scanned PDFs (your choice from Option 1)
- Cloud service for failed OCR (your choice from Option 2)
- LLM for specific extraction tasks (your choice from Option 3)

### Simple Issue Breakdown

**Issue #86: [PDF-Download] Simple PDF Downloader**
- Implement basic downloader with caching
- Add retry logic
- Test with 100 PDFs
- Effort: S (2-3h)

**Issue #87: [PDF-Parse-Basic] PyMuPDF Text Extraction**
- Use PyMuPDF for standard PDFs
- Extract text preserving structure
- Handle multi-column layouts
- Effort: S (2-3h)

**Issue #88: [PDF-Parse-OCR] OCR Fallback Pipeline**
- Implement chosen OCR solution
- Trigger when text extraction fails
- Cache OCR results
- Effort: M (4-6h)

**Issue #89: [PDF-Parse-Cloud] Cloud Service Integration**
- Add cloud service for difficult PDFs
- Implement cost controls
- Only use when local methods fail
- Effort: M (4-6h)

**Issue #90: [PDF-Parse-LLM] LLM Extraction for Complex Cases**
- Implement chosen LLM approach
- Focus on computational requirements extraction
- Handle tables and complex layouts
- Effort: M (4-6h)

## Decision Points Needed

Please indicate your preferences:

1. **OCR Solution**: Which option (1-4) for OCR?
2. **Cloud Service**: Which service(s) for difficult cases?
3. **LLM Approach**: Which strategy (1-3) for complex layouts?
4. **Cost Budget**: Acceptable cost per paper for cloud/LLM services?

Based on your choices, I'll create the final implementation plan with specific technologies.
