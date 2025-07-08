# NeurIPS Pipeline Example

This example demonstrates the complete paper collection and PDF processing pipeline with real NeurIPS papers.

## Overview

The `example_neurips_pipeline.py` script shows the proper workflow separation:

1. **Paper Collection**: Uses `CitationCollector` to gather paper metadata from multiple sources:
   - OpenAlex
   - Semantic Scholar  
   - Google Scholar
   
2. **PDF Discovery**: Uses PDF discovery modules to find downloadable URLs:
   - OpenReviewPDFCollector for papers on OpenReview
   - ArXiv URLs for papers with arXiv IDs
   
3. **PDF Download**: Downloads PDFs using the discovered URLs

4. **Text Extraction**: Uses PyMuPDF to extract text from the PDFs

5. **Results Analysis**: Analyzes extraction quality and generates metrics

## Key Features

- **Real Data**: Collects actual NeurIPS papers from citation sources
- **Proper Architecture**: Shows the separation between paper collection and PDF discovery
- **Multiple Sources**: Leverages multiple APIs for comprehensive coverage
- **Fallback Handling**: Includes multiple fallback strategies
- **Complete Pipeline**: Demonstrates the full workflow from collection to extraction
- **Metrics Collection**: Tracks success rates, extraction times, and content quality

## Usage

```bash
cd package
uv run python examples/example_neurips_pipeline.py
```

The script will:
- Collect up to 5 NeurIPS papers from OpenReview
- Download the PDFs to a cache directory
- Extract text using PyMuPDF
- Generate a summary report with extraction metrics
- Save detailed results to JSON files

## Architecture

The example demonstrates the proper separation of concerns:

### Paper Collection Layer
- Uses `CitationCollector` to orchestrate multiple citation sources
- Each source (OpenAlex, Semantic Scholar, Google Scholar) provides paper metadata
- Returns `Paper` objects with title, authors, venue, year, etc.

### PDF Discovery Layer  
- Takes `Paper` objects and finds downloadable PDF URLs
- Uses specialized collectors like `OpenReviewPDFCollector`
- Falls back to constructing URLs from identifiers (e.g., arXiv IDs)

### PDF Processing Layer
- Downloads PDFs from discovered URLs
- Extracts text using PyMuPDF
- Analyzes extraction quality

## Notes

- The script includes proper rate limiting for all APIs
- Results are cached to avoid re-downloading papers
- Multiple fallback strategies ensure robustness
- Citation sources may have different coverage for NeurIPS papers

## Extending the Example

To collect papers from other venues:
- Modify the `CollectionQuery` to specify different venues
- The citation sources will automatically search for papers from those venues
- PDF discovery will use appropriate collectors based on where papers are hosted