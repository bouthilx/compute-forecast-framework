# GROBID Academic Structure Extractor Setup

This document explains how to set up and use the GROBID Academic Structure Extractor for PDF parsing.

## Overview

GROBID (GeneRation Of BIbliographic Data) is a machine learning library designed for extracting bibliographic information from scholarly documents. It excels at parsing academic paper structure and extracting affiliations.

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Start GROBID service
docker-compose up -d grobid

# Check service health
curl http://localhost:8070/api/isalive

# Stop service
docker-compose down
```

### Option 2: Using Docker directly

```bash
# Run GROBID service
docker run -d --name grobid -p 8070:8070 lfoppiano/grobid:0.7.3

# Check if running
docker ps

# Stop service
docker stop grobid
docker rm grobid
```

## Using the GROBID Extractor

### Basic Usage

```python
from pathlib import Path
from src.pdf_parser.extractors.grobid_extractor import GROBIDExtractor

# Initialize extractor
extractor = GROBIDExtractor()

# Extract affiliations from first 2 pages
pdf_path = Path('path/to/paper.pdf')
result = extractor.extract_first_pages(pdf_path, [0, 1])

print(f"Found {len(result['affiliations'])} affiliations:")
for aff in result['affiliations']:
    print(f"  - {aff['name']}")

# Extract full text
full_text = extractor.extract_full_text(pdf_path)
```

### Integration with PDF Processor

```python
from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.grobid_extractor import GROBIDExtractor

# Setup processor with GROBID
processor = OptimizedPDFProcessor({})
grobid_extractor = GROBIDExtractor()

# Register GROBID as high-priority extractor
processor.register_extractor('grobid', grobid_extractor, level=1)

# Process PDF
result = processor.process_pdf(pdf_path, paper_metadata)
```

## Configuration

### Custom GROBID URL

```python
extractor = GROBIDExtractor({
    'grobid_url': 'http://custom-host:9000',
    'timeout': 60
})
```

### Service Manager Configuration

```python
from src.pdf_parser.services.grobid_manager import GROBIDManager

manager = GROBIDManager({
    'url': 'http://localhost:8070',
    'container_name': 'my-grobid',
    'image': 'lfoppiano/grobid:0.7.3',
    'port': 8070,
    'timeout': 30
})

# Start service programmatically
manager.start_service()

# Check health
is_healthy = manager.check_service_health()

# Stop service
manager.stop_service()
```

## Output Format

### Affiliation Extraction Result

```python
{
    'affiliations': [
        {'name': 'University of Example, Department of Computer Science'},
        {'name': 'Research Institute of Technology'}
    ],
    'authors_with_affiliations': [
        {
            'name': 'John Doe',
            'affiliations': ['University of Example, Department of Computer Science']
        }
    ],
    'title': 'Example Paper Title',
    'abstract': 'This is the abstract...',
    'text': '<?xml version="1.0"...',  # Raw TEI XML
    'method': 'grobid',
    'confidence': 0.8
}
```

## Troubleshooting

### Service Not Starting

1. **Check Docker is running:**
   ```bash
   docker --version
   docker ps
   ```

2. **Check port availability:**
   ```bash
   netstat -an | grep 8070
   ```

3. **View GROBID logs:**
   ```bash
   docker logs grobid
   ```

### Low Quality Extractions

1. **PDF Quality:** GROBID works best with text-based PDFs, not scanned images
2. **Paper Format:** Academic papers in standard formats work better
3. **Language:** GROBID is optimized for English-language papers

### Service Health Issues

1. **Wait for startup:** GROBID takes 30-60 seconds to fully initialize
2. **Memory:** Ensure Docker has enough memory allocated (4GB recommended)
3. **Check endpoint:** Test with `curl http://localhost:8070/api/isalive`

## Advanced Features

### Cost Tracking

```python
# Get cost summary (GROBID is free but tracks usage)
processor = OptimizedPDFProcessor({})
# ... process PDFs ...
cost_summary = processor.get_cost_summary()
print(f"GROBID operations: {cost_summary['operation_counts']['affiliation_extraction']}")
```

### Error Handling

```python
from src.pdf_parser.extractors.grobid_extractor import GROBIDExtractionError
from src.pdf_parser.services.grobid_manager import GROBIDServiceError

try:
    result = extractor.extract_first_pages(pdf_path, [0, 1])
except GROBIDServiceError:
    print("GROBID service is not available")
except GROBIDExtractionError as e:
    print(f"Extraction failed: {e}")
```

## Performance Notes

- **Startup Time:** GROBID takes 30-60 seconds to initialize
- **Processing Speed:** ~2-5 seconds per paper for header extraction
- **Memory Usage:** ~2-4GB RAM for the service
- **Concurrency:** GROBID can handle multiple concurrent requests

## Supported Formats

- **Input:** PDF files (text-based preferred over scanned)
- **Output:** TEI XML with structured bibliographic data
- **Languages:** Primarily English, limited support for other languages
- **Paper Types:** Academic papers, conference proceedings, journal articles