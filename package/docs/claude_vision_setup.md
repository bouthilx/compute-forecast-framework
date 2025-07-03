# Claude Vision Extractor Setup

This document describes how to set up and use the Claude Vision extractor for affiliation extraction from research papers.

## Overview

The Claude Vision extractor uses Anthropic's Claude 3 Haiku model with vision capabilities to extract author affiliations from the first 2 pages of PDF documents. It's particularly effective for complex layouts where traditional text extraction methods fail.

## Prerequisites

### Dependencies

The following packages are required and should already be installed if you followed the project setup:

```bash
uv add anthropic>=0.25.0
uv add opencv-python>=4.8.0  
uv add pillow>=10.0.0
uv add pymupdf>=1.23.0
```

### API Access

You need an Anthropic API key to use Claude Vision:

1. Sign up at [https://console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Set the API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or store it in a `.env` file:

```
ANTHROPIC_API_KEY=your-api-key-here
```

## Usage

### Basic Usage

```python
from pathlib import Path
from src.pdf_parser.extractors.claude_vision_extractor import ClaudeVisionExtractor

# Initialize the extractor
extractor = ClaudeVisionExtractor(api_key="your-api-key")

# Extract affiliations from first 2 pages
pdf_path = Path("research_paper.pdf")
result = extractor.extract_first_pages(pdf_path, pages=[0, 1])

print(f"Found {len(result['affiliations'])} affiliations")
print(f"Confidence: {result['confidence']}")
print(f"Cost: ${result['cost']:.4f}")

for author_info in result['authors_with_affiliations']:
    print(f"- {author_info['name']}: {author_info['affiliation']}")
```

### Integration with PDF Processor

```python
from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.claude_vision_extractor import ClaudeVisionExtractor

# Set up processor
config = {"max_cost_per_paper": 0.50}
processor = OptimizedPDFProcessor(config)

# Register Claude Vision as high-priority extractor for affiliations
claude_extractor = ClaudeVisionExtractor(api_key="your-api-key")
processor.register_extractor("claude_vision", claude_extractor, level=1)  # High priority

# Process a paper
paper_metadata = {
    "title": "Example Paper",
    "authors": ["John Doe", "Jane Smith"]
}

result = processor.process_pdf(pdf_path, paper_metadata)
print(f"Extraction method used: {result['method']}")
```

## Features

### Targeted Affiliation Extraction

- **Focus**: Specifically designed for author-affiliation mapping
- **Coverage**: Processes first 2 pages where affiliations typically appear
- **Layout Understanding**: Handles complex formatting, superscripts, footnotes
- **Email Extraction**: Also captures email addresses when visible

### Cost Management

- **Model**: Uses Claude 3 Haiku (cheaper model, sufficient for this task)
- **Fixed Cost**: $0.10 per 2-page extraction
- **Tracking**: Automatic cost tracking and reporting
- **Limits**: Processes maximum 2 pages to control costs

### Quality Assurance

- **Confidence Scoring**: Returns confidence score (0.0-1.0)
- **Validation**: Structured JSON output with validation
- **Fallback**: Graceful handling of unclear or missing information
- **Error Handling**: Comprehensive error handling and logging

## Response Format

The extractor returns a dictionary with the following structure:

```python
{
    "affiliations": [
        "Massachusetts Institute of Technology",
        "Stanford University"
    ],
    "authors_with_affiliations": [
        {
            "name": "John Doe",
            "affiliation": "Massachusetts Institute of Technology",
            "email": "john@mit.edu"
        },
        {
            "name": "Jane Smith", 
            "affiliation": "Stanford University",
            "email": "jane@stanford.edu"
        }
    ],
    "method": "claude_vision",
    "confidence": 0.9,
    "cost": 0.10
}
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Required API key for Claude access
- `CLAUDE_MODEL`: Optional model override (default: claude-3-haiku-20240307)

### Cost Control

- Maximum 2 pages processed per document
- Fixed cost model: $0.10 per extraction
- Cost tracking integrated with PDF processor

## Troubleshooting

### Common Issues

**Import Error: anthropic package not found**
```bash
uv add anthropic>=0.25.0
```

**Import Error: fitz (PyMuPDF) not found**
```bash
uv add pymupdf>=1.23.0
```

**API Authentication Error**
- Verify your API key is correct
- Check environment variable is set
- Ensure you have API credits

**Low Confidence Scores**
- Check if PDF contains clear author/affiliation information
- Verify first 2 pages contain the relevant content
- Consider if document has unusual formatting

### Logging

Enable debug logging to see detailed extraction process:

```python
import logging
logging.getLogger("src.pdf_parser.extractors.claude_vision_extractor").setLevel(logging.DEBUG)
```

## Performance Characteristics

- **Speed**: ~2-5 seconds per extraction (depends on API response time)
- **Accuracy**: 80%+ success rate on papers with clear affiliation information
- **Cost**: $0.10 per paper (fixed rate for 2-page extraction)
- **Limitations**: Only processes first 2 pages; requires good quality PDF

## Integration with Other Extractors

Claude Vision works best as part of a fallback hierarchy:

1. **Level 1**: Claude Vision (high accuracy, costs money)
2. **Level 2**: GROBID (good accuracy, free)  
3. **Level 3**: PyMuPDF (basic extraction, free)
4. **Level 4**: EasyOCR (OCR fallback, free but slow)

The PDF processor will try extractors in priority order and use the first successful result.