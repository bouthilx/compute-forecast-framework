# PDF Parsing Final Implementation Plan

**Timestamp**: 2025-01-01 11:15
**Title**: Final Technology Stack and Implementation for PDF Parsing

## Selected Technology Stack

1. **Primary OCR**: EasyOCR (deep learning-based, pure Python)
2. **Cloud Fallbacks**: Google Cloud Vision + Claude Vision API
3. **Academic Parser**: GROBID + LLM refinement approach

## Implementation Architecture

```
PDF Processing Pipeline
├── Level 1: PyMuPDF (standard text extraction)
├── Level 2: EasyOCR (for scanned/image PDFs)
├── Level 3: GROBID (academic structure extraction)
├── Level 4: Cloud Services (for difficult cases)
│   ├── Google Cloud Vision (better for pure OCR)
│   └── Claude Vision (better for understanding)
└── Level 5: LLM Refinement (missing fields)
```

## Detailed Implementation

### Core PDF Processing Class

```python
import fitz  # PyMuPDF
import easyocr
from typing import Dict, Any, Optional
import requests
from pathlib import Path
import json

class ComprehensivePDFProcessor:
    def __init__(self, config: Dict[str, Any]):
        # Initialize components
        self.cache_dir = Path(config.get('cache_dir', './pdf_cache'))
        self.cache_dir.mkdir(exist_ok=True)
        
        # EasyOCR initialization (download models on first use)
        self.ocr_reader = easyocr.Reader(['en'], gpu=True)  # Use GPU if available
        
        # GROBID endpoint
        self.grobid_url = config.get('grobid_url', 'http://localhost:8070')
        
        # Cloud service configs
        self.google_vision_key = config.get('google_vision_api_key')
        self.anthropic_api_key = config.get('anthropic_api_key')
        
        # Thresholds
        self.min_text_length = 1000  # Minimum chars to consider valid
        self.confidence_threshold = 0.7
        
    def process_pdf(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
        """Main processing pipeline with fallback hierarchy"""
        
        # Try Level 1: Standard text extraction
        text, confidence = self._try_pymupdf(pdf_path)
        if confidence > self.confidence_threshold:
            return self._create_result(text, "pymupdf", confidence)
        
        # Try Level 2: EasyOCR
        text, confidence = self._try_easyocr(pdf_path)
        if confidence > self.confidence_threshold:
            return self._create_result(text, "easyocr", confidence)
        
        # Try Level 3: GROBID for structure
        structured_data = self._try_grobid(pdf_path)
        if structured_data and structured_data.get('confidence', 0) > 0.5:
            return structured_data
        
        # Try Level 4: Cloud services
        text, confidence = self._try_cloud_services(pdf_path, paper_metadata)
        if confidence > 0.5:
            return self._create_result(text, "cloud", confidence)
        
        # Level 5: LLM refinement on whatever we got
        return self._llm_refinement(text, structured_data, paper_metadata)
```

### Level 1: PyMuPDF Implementation

```python
def _try_pymupdf(self, pdf_path: Path) -> Tuple[str, float]:
    """Fast text extraction for standard PDFs"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            text += f"\n[Page {page_num + 1}]\n{page_text}"
        
        doc.close()
        
        # Calculate confidence based on text quality
        confidence = self._calculate_text_confidence(text)
        return text, confidence
        
    except Exception as e:
        return "", 0.0
        
def _calculate_text_confidence(self, text: str) -> float:
    """Estimate extraction quality"""
    if len(text) < self.min_text_length:
        return 0.0
    
    # Check for common extraction issues
    garbage_ratio = len([c for c in text if ord(c) < 32]) / len(text)
    if garbage_ratio > 0.1:
        return 0.3
    
    # Check for academic paper markers
    has_abstract = "abstract" in text.lower()
    has_references = "references" in text.lower() or "bibliography" in text.lower()
    has_sections = any(marker in text.lower() for marker in ["introduction", "methodology", "results"])
    
    confidence = 0.4
    if has_abstract: confidence += 0.2
    if has_references: confidence += 0.2
    if has_sections: confidence += 0.2
    
    return min(confidence, 1.0)
```

### Level 2: EasyOCR Implementation

```python
def _try_easyocr(self, pdf_path: Path) -> Tuple[str, float]:
    """OCR for scanned PDFs using deep learning"""
    try:
        # Convert PDF to images first
        images = self._pdf_to_images(pdf_path)
        
        all_text = []
        all_confidences = []
        
        for idx, image in enumerate(images):
            # EasyOCR returns list of (bbox, text, confidence)
            results = self.ocr_reader.readtext(image)
            
            page_text = []
            page_confidences = []
            
            for (bbox, text, confidence) in results:
                page_text.append(text)
                page_confidences.append(confidence)
            
            all_text.append(f"\n[Page {idx + 1}]\n" + " ".join(page_text))
            all_confidences.extend(page_confidences)
        
        combined_text = "\n".join(all_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        
        return combined_text, avg_confidence
        
    except Exception as e:
        return "", 0.0

def _pdf_to_images(self, pdf_path: Path) -> List[np.ndarray]:
    """Convert PDF pages to images for OCR"""
    import pdf2image
    
    images = pdf2image.convert_from_path(
        pdf_path,
        dpi=300,  # High quality for better OCR
        fmt='png'
    )
    
    # Convert PIL images to numpy arrays for EasyOCR
    return [np.array(img) for img in images]
```

### Level 3: GROBID Implementation

```python
def _try_grobid(self, pdf_path: Path) -> Dict[str, Any]:
    """Extract structured academic paper data"""
    try:
        # Start GROBID service if not running
        if not self._check_grobid_health():
            self._start_grobid_docker()
        
        # Send PDF to GROBID
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(
                f"{self.grobid_url}/api/processFulltextDocument",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            # Parse GROBID XML response
            structured_data = self._parse_grobid_xml(response.text)
            structured_data['confidence'] = 0.8  # GROBID is generally reliable
            return structured_data
            
    except Exception as e:
        return {}

def _parse_grobid_xml(self, xml_content: str) -> Dict[str, Any]:
    """Parse GROBID TEI XML to extract key fields"""
    from lxml import etree
    
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = etree.fromstring(xml_content.encode('utf-8'))
    
    # Extract structured data
    data = {
        'title': root.xpath('//tei:titleStmt/tei:title/text()', namespaces=ns),
        'abstract': root.xpath('//tei:abstract//text()', namespaces=ns),
        'authors': self._extract_authors(root, ns),
        'sections': self._extract_sections(root, ns),
        'references': self._extract_references(root, ns)
    }
    
    # Look for computational requirements in specific sections
    comp_sections = ['experimental setup', 'implementation details', 'experiments']
    data['computational_sections'] = {}
    
    for section in data['sections']:
        if any(comp in section['title'].lower() for comp in comp_sections):
            data['computational_sections'][section['title']] = section['text']
    
    return data

def _start_grobid_docker(self):
    """Start GROBID service using Docker"""
    import subprocess
    subprocess.run([
        'docker', 'run', '-d',
        '-p', '8070:8070',
        '--name', 'grobid',
        'lfoppiano/grobid:0.7.3'
    ])
```

### Level 4: Cloud Services Implementation

```python
def _try_cloud_services(self, pdf_path: Path, paper_metadata: Dict) -> Tuple[str, float]:
    """Use cloud services for difficult PDFs"""
    
    # Try Google Cloud Vision first (better for pure OCR)
    if self.google_vision_key:
        text, confidence = self._try_google_vision(pdf_path)
        if confidence > 0.7:
            return text, confidence
    
    # Try Claude Vision for understanding complex layouts
    if self.anthropic_api_key:
        text, confidence = self._try_claude_vision(pdf_path, paper_metadata)
        if confidence > 0.5:
            return text, confidence
    
    return "", 0.0

def _try_google_vision(self, pdf_path: Path) -> Tuple[str, float]:
    """Google Cloud Vision API for OCR"""
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    
    # Convert PDF to images
    images = self._pdf_to_images(pdf_path)
    all_text = []
    
    for idx, image in enumerate(images[:10]):  # Limit to first 10 pages for cost
        # Convert numpy array to bytes
        _, buffer = cv2.imencode('.png', image)
        image_bytes = buffer.tobytes()
        
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        
        if response.text_annotations:
            all_text.append(f"\n[Page {idx + 1}]\n{response.text_annotations[0].description}")
    
    combined_text = "\n".join(all_text)
    return combined_text, 0.8  # Google Vision is generally reliable

def _try_claude_vision(self, pdf_path: Path, paper_metadata: Dict) -> Tuple[str, float]:
    """Claude Vision API for complex understanding"""
    import anthropic
    
    client = anthropic.Anthropic(api_key=self.anthropic_api_key)
    
    # Convert first few pages to images
    images = self._pdf_to_images(pdf_path)[:5]  # Limit for cost
    
    # Prepare prompt
    prompt = f"""
    This is a research paper titled: {paper_metadata.get('title', 'Unknown')}
    Authors: {paper_metadata.get('authors', 'Unknown')}
    
    Please extract the following information:
    1. Full abstract
    2. Computational requirements (GPUs, training time, model size)
    3. Experimental setup details
    4. Any tables containing resource specifications
    
    Focus on finding computational specifications and experimental details.
    """
    
    # Send to Claude
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            *[{"type": "image", "source": {"type": "base64", "media_type": "image/png", 
              "data": self._image_to_base64(img)}} for img in images]
        ]
    }]
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        messages=messages
    )
    
    return response.content[0].text, 0.9
```

### Level 5: LLM Refinement Implementation

```python
def _llm_refinement(self, raw_text: str, grobid_data: Dict, 
                    paper_metadata: Dict) -> Dict[str, Any]:
    """Use LLM to extract specific computational requirements"""
    
    # Combine all available data
    context = {
        'raw_text': raw_text[:10000],  # Limit context size
        'grobid_sections': grobid_data.get('computational_sections', {}),
        'paper_metadata': paper_metadata
    }
    
    # Prepare targeted prompt
    prompt = """
    Extract computational requirements from this research paper.
    
    Paper: {title}
    
    Available text sections:
    {sections}
    
    Extract:
    1. GPU/TPU type and count
    2. Training time (hours/days)
    3. Model parameters count
    4. Dataset size
    5. Batch size
    6. Memory requirements
    7. Any other computational specifications
    
    Return as JSON with confidence scores for each field.
    """
    
    # Send to LLM
    response = self._query_llm(prompt.format(
        title=paper_metadata.get('title'),
        sections=self._format_sections(context)
    ))
    
    # Parse and validate response
    try:
        extracted_data = json.loads(response)
        extracted_data['extraction_method'] = 'llm_refinement'
        return extracted_data
    except:
        return {
            'extraction_method': 'failed',
            'raw_text': raw_text[:5000],
            'error': 'LLM extraction failed'
        }
```

## GitHub Issues for Implementation

### Issue #91: [PDF-Parse-Core] Implement Multi-Level PDF Processor
**Effort**: L (6-8h)
**Description**: Implement the core PDF processing class with fallback hierarchy
**Dependencies**: PyMuPDF, pdf2image

### Issue #92: [PDF-Parse-EasyOCR] Integrate EasyOCR for Scanned PDFs
**Effort**: M (4-6h)
**Description**: Implement EasyOCR with GPU support and confidence scoring
**Dependencies**: easyocr, pdf2image

### Issue #93: [PDF-Parse-GROBID] Set up GROBID Service and Parser
**Effort**: M (4-6h)
**Description**: Docker setup for GROBID and XML parsing for academic papers
**Dependencies**: Docker, lxml

### Issue #94: [PDF-Parse-Cloud] Implement Cloud Service Fallbacks
**Effort**: M (4-6h)
**Description**: Google Cloud Vision + Claude Vision API integration
**Dependencies**: google-cloud-vision, anthropic

### Issue #95: [PDF-Parse-LLM] LLM Refinement for Computational Requirements
**Effort**: M (4-6h)
**Description**: Targeted extraction using LLM for missing/complex fields
**Dependencies**: Existing LLM integration

## Cost Estimation

Per paper processing costs (worst case, all levels):
- EasyOCR: Free (local GPU)
- GROBID: Free (self-hosted)
- Google Cloud Vision: ~$0.015 (10 pages)
- Claude Vision: ~$0.05 (5 pages)
- LLM Refinement: ~$0.01

**Maximum cost per paper**: ~$0.075
**Expected average cost**: ~$0.02 (most papers won't need cloud services)

## Performance Expectations

Processing time per paper:
- Level 1 (PyMuPDF): 1-2 seconds
- Level 2 (EasyOCR): 30-60 seconds
- Level 3 (GROBID): 5-10 seconds
- Level 4 (Cloud): 10-20 seconds
- Level 5 (LLM): 5-10 seconds

**Average processing time**: 5-10 seconds (most papers use Level 1-3)