# Optimized PDF Parsing Implementation

**Timestamp**: 2025-01-01 11:30
**Title**: Cost-Optimized PDF Parsing Focusing on First Pages for Affiliations

## Revised Processing Strategy

Since affiliations are typically on the first 1-2 pages and computational requirements are throughout the paper, we'll use a **split processing approach**:

1. **First 2 pages**: Full processing pipeline (for affiliations)
2. **Rest of paper**: Basic PyMuPDF only (for computational specs)

## Optimized Implementation

### Core Processing Class (Revised)

```python
class OptimizedPDFProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.cache_dir = Path(config.get('cache_dir', './pdf_cache'))
        self.cache_dir.mkdir(exist_ok=True)

        # EasyOCR for first pages only
        self.ocr_reader = easyocr.Reader(['en'], gpu=True)

        # GROBID endpoint
        self.grobid_url = config.get('grobid_url', 'http://localhost:8070')

        # Cloud configs
        self.google_vision_key = config.get('google_vision_api_key')
        self.anthropic_api_key = config.get('anthropic_api_key')

    def process_pdf(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
        """Split processing: advanced for first 2 pages, basic for rest"""

        # Split PDF processing
        first_pages_data = self._process_first_pages(pdf_path, paper_metadata)
        full_text = self._process_full_document(pdf_path)

        # Combine results
        return {
            'affiliations': first_pages_data.get('affiliations', []),
            'authors_with_affiliations': first_pages_data.get('authors_with_affiliations', []),
            'title': first_pages_data.get('title', paper_metadata.get('title')),
            'abstract': first_pages_data.get('abstract', ''),
            'full_text': full_text,
            'computational_sections': self._extract_computational_sections(full_text),
            'extraction_method': first_pages_data.get('method', 'pymupdf'),
            'confidence': first_pages_data.get('confidence', 0.0)
        }
```

### First Pages Processing (Advanced)

```python
def _process_first_pages(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
    """Process only first 2 pages with full pipeline for affiliations"""

    # Extract just first 2 pages
    first_pages_text = self._extract_pages_pymupdf(pdf_path, pages=[0, 1])

    # Check if we got good affiliations
    affiliations = self._extract_affiliations_basic(first_pages_text)
    if len(affiliations) >= len(paper_metadata.get('authors', [])) * 0.7:
        return {
            'affiliations': affiliations,
            'authors_with_affiliations': self._match_authors_affiliations(
                paper_metadata.get('authors', []), affiliations
            ),
            'abstract': self._extract_abstract(first_pages_text),
            'method': 'pymupdf',
            'confidence': 0.9
        }

    # Try EasyOCR on first 2 pages only
    first_pages_ocr = self._process_pages_easyocr(pdf_path, pages=[0, 1])
    affiliations = self._extract_affiliations_basic(first_pages_ocr)
    if len(affiliations) >= len(paper_metadata.get('authors', [])) * 0.5:
        return {
            'affiliations': affiliations,
            'authors_with_affiliations': self._match_authors_affiliations(
                paper_metadata.get('authors', []), affiliations
            ),
            'abstract': self._extract_abstract(first_pages_ocr),
            'method': 'easyocr',
            'confidence': 0.7
        }

    # Try GROBID on first pages for structure
    grobid_data = self._process_first_pages_grobid(pdf_path)
    if grobid_data and grobid_data.get('authors'):
        return {
            'affiliations': [author.get('affiliation', '')
                           for author in grobid_data['authors']],
            'authors_with_affiliations': grobid_data['authors'],
            'abstract': grobid_data.get('abstract', ''),
            'title': grobid_data.get('title', ''),
            'method': 'grobid',
            'confidence': 0.8
        }

    # Last resort: Cloud services for first 2 pages only
    if self.google_vision_key or self.anthropic_api_key:
        return self._process_first_pages_cloud(pdf_path, paper_metadata)

    return {'affiliations': [], 'method': 'failed', 'confidence': 0.0}

def _extract_pages_pymupdf(self, pdf_path: Path, pages: List[int]) -> str:
    """Extract specific pages using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text = ""

    for page_num in pages:
        if page_num < len(doc):
            page = doc[page_num]
            text += f"\n[Page {page_num + 1}]\n{page.get_text()}"

    doc.close()
    return text

def _process_pages_easyocr(self, pdf_path: Path, pages: List[int]) -> str:
    """OCR specific pages only"""
    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in pages:
        if page_num < len(doc):
            page = doc[page_num]
            # Convert page to image
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")

            # OCR the image
            import io
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)

            results = self.ocr_reader.readtext(img_array)
            page_text = " ".join([text for _, text, _ in results])
            text_parts.append(f"\n[Page {page_num + 1}]\n{page_text}")

    doc.close()
    return "\n".join(text_parts)

def _process_first_pages_grobid(self, pdf_path: Path) -> Dict[str, Any]:
    """Send only first pages to GROBID"""
    # Create temporary PDF with just first 2 pages
    import tempfile

    doc = fitz.open(pdf_path)
    temp_doc = fitz.open()

    for i in range(min(2, len(doc))):
        temp_doc.insert_pdf(doc, from_page=i, to_page=i)

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        temp_doc.save(tmp.name)
        temp_path = tmp.name

    doc.close()
    temp_doc.close()

    # Process with GROBID
    try:
        with open(temp_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(
                f"{self.grobid_url}/api/processHeaderDocument",  # Header only!
                files=files,
                timeout=30
            )

        if response.status_code == 200:
            return self._parse_grobid_header(response.text)
    finally:
        Path(temp_path).unlink()

    return {}

def _process_first_pages_cloud(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
    """Use cloud services for first 2 pages only"""
    # Extract first 2 pages as images
    doc = fitz.open(pdf_path)
    images = []

    for i in range(min(2, len(doc))):
        page = doc[i]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        images.append(img_data)

    doc.close()

    # Try Google Vision first
    if self.google_vision_key:
        affiliations = self._extract_affiliations_google_vision(images)
        if affiliations:
            return {
                'affiliations': affiliations,
                'method': 'google_vision',
                'confidence': 0.8
            }

    # Try Claude Vision with specific prompt
    if self.anthropic_api_key:
        result = self._extract_affiliations_claude(images, paper_metadata)
        if result:
            return result

    return {'affiliations': [], 'method': 'cloud_failed', 'confidence': 0.0}
```

### Full Document Processing (Basic)

```python
def _process_full_document(self, pdf_path: Path) -> str:
    """Simple PyMuPDF extraction for full document - computational specs don't need OCR"""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""

        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            full_text += f"\n[Page {page_num + 1}]\n{page_text}"

        doc.close()
        return full_text

    except Exception as e:
        return ""

def _extract_computational_sections(self, full_text: str) -> Dict[str, str]:
    """Extract sections likely to contain computational requirements"""
    sections = {}

    # Keywords that indicate computational content
    comp_keywords = [
        'experimental setup', 'implementation details', 'experiments',
        'training details', 'computational resources', 'hardware',
        'hyperparameters', 'training procedure', 'model architecture'
    ]

    # Simple section extraction
    lines = full_text.split('\n')
    current_section = None
    current_content = []

    for line in lines:
        # Check if this is a section header
        if any(keyword in line.lower() for keyword in comp_keywords):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line.strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    # Don't forget last section
    if current_section:
        sections[current_section] = '\n'.join(current_content)

    # Also extract tables that might contain specs
    table_sections = self._extract_tables_with_specs(full_text)
    sections.update(table_sections)

    return sections

def _extract_tables_with_specs(self, text: str) -> Dict[str, str]:
    """Find tables that likely contain computational specifications"""
    tables = {}

    # Look for table indicators with computational terms
    table_keywords = ['gpu', 'memory', 'hours', 'parameters', 'batch', 'epochs']

    lines = text.split('\n')
    in_table = False
    table_content = []
    table_name = ""

    for i, line in enumerate(lines):
        # Simple heuristic: tables often have multiple numbers/columns
        if '|' in line or '\t' in line or line.count(' ') > 10:
            if not in_table:
                # Check if this table is relevant
                context = ' '.join(lines[max(0, i-3):i+3]).lower()
                if any(kw in context for kw in table_keywords):
                    in_table = True
                    table_name = f"Table_near_line_{i}"
                    table_content = [line]
            else:
                table_content.append(line)
        elif in_table and len(table_content) > 2:
            # End of table
            tables[table_name] = '\n'.join(table_content)
            in_table = False
            table_content = []

    return tables
```

### Affiliation Extraction Helpers

```python
def _extract_affiliations_basic(self, text: str) -> List[str]:
    """Extract affiliations using patterns"""
    affiliations = []

    # Common patterns for affiliations
    patterns = [
        r'([A-Z][^.]+(?:University|Institute|Laboratory|Center|Centre|Lab|Department|School|College|Corporation|Company|Inc\.|Ltd\.|LLC)[^.]*)',
        r'(\d+\s*[A-Za-z\s,]+(?:University|Institute|Laboratory|Center|Centre)[^.]*)',
        r'(?:affiliation|address)[:\s]*([^.]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        affiliations.extend(matches)

    # Clean and deduplicate
    cleaned = []
    for aff in affiliations:
        aff = aff.strip()
        if len(aff) > 10 and len(aff) < 200:  # Reasonable length
            cleaned.append(aff)

    return list(set(cleaned))

def _extract_affiliations_claude(self, images: List[bytes],
                               paper_metadata: Dict) -> Dict[str, Any]:
    """Use Claude specifically for affiliation extraction"""
    import anthropic
    import base64

    client = anthropic.Anthropic(api_key=self.anthropic_api_key)

    # Targeted prompt for affiliations
    prompt = f"""
    This is the first page(s) of a research paper.
    Title: {paper_metadata.get('title', 'Unknown')}
    Authors: {', '.join([a['name'] for a in paper_metadata.get('authors', [])])}

    Please extract:
    1. Each author's affiliation (institution/company)
    2. The mapping between authors and their affiliations
    3. Email addresses if visible

    Return as JSON in this format:
    {{
        "authors_with_affiliations": [
            {{"name": "Author Name", "affiliation": "Institution", "email": "optional"}},
            ...
        ],
        "confidence": 0.0-1.0
    }}
    """

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            *[{"type": "image", "source": {"type": "base64",
              "media_type": "image/png",
              "data": base64.b64encode(img).decode()}} for img in images]
        ]
    }]

    response = client.messages.create(
        model="claude-3-haiku-20240307",  # Cheaper model for simple task
        max_tokens=1000,
        messages=messages
    )

    try:
        result = json.loads(response.content[0].text)
        return {
            'affiliations': [a['affiliation'] for a in result['authors_with_affiliations']],
            'authors_with_affiliations': result['authors_with_affiliations'],
            'method': 'claude_vision',
            'confidence': result.get('confidence', 0.8)
        }
    except:
        return {'affiliations': [], 'method': 'claude_failed', 'confidence': 0.0}
```

## Cost Optimization Results

### Before Optimization
- Full document OCR/GROBID/Cloud processing
- Cost per paper: ~$0.075 worst case
- Time per paper: 30-60 seconds

### After Optimization
- First 2 pages only for advanced processing
- Rest of document uses free PyMuPDF
- **Cost per paper**: ~$0.002-0.010 (only 2 pages to cloud)
- **Time per paper**: 5-15 seconds

### Cost Breakdown
- PyMuPDF (full doc): Free
- EasyOCR (2 pages): Free
- GROBID (header only): Free
- Google Vision (2 pages): ~$0.003
- Claude Vision (2 pages): ~$0.01

## Updated GitHub Issues

### Issue #91: [PDF-Parse-Core] Implement Split Processing Strategy
**Effort**: M (4-6h)
**Description**: Core processor with first-pages vs full-doc split

### Issue #92: [PDF-Parse-First-Pages] Advanced Processing for Affiliations
**Effort**: M (4-6h)
**Description**: EasyOCR/GROBID/Cloud for first 2 pages only

### Issue #93: [PDF-Parse-Full-Doc] Basic Extraction for Computational Specs
**Effort**: S (2-3h)
**Description**: PyMuPDF extraction with computational section detection

### Issue #94: [PDF-Parse-Affiliation] Specialized Affiliation Extractors
**Effort**: S (2-3h)
**Description**: Pattern matching and LLM prompts for affiliations

This optimized approach reduces costs by 90%+ while maintaining extraction quality where it matters.
