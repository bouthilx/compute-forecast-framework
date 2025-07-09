# Paper Collection Guide

This guide explains how to use the paper collection infrastructure to gather research papers from various sources.

## Overview

The package provides several paper collectors that can retrieve paper metadata (not PDFs) from different academic sources:

1. **Citation Data Sources** (for metadata):
   - **OpenAlex**: Open database of scholarly works with good API limits
   - **Semantic Scholar**: AI-focused paper database with comprehensive metadata
   - **Google Scholar**: Comprehensive but rate-limited, requires careful handling

2. **PDF Discovery Sources** (for finding PDF URLs):
   - **OpenReview**: For recent conference papers (NeurIPS 2023+, ICLR, etc.)
   - **ArXiv**: For preprints and technical reports
   - **PMLR**: For machine learning conference proceedings
   - **ACL Anthology**: For NLP papers
   - And many more specialized collectors

## Basic Usage

### 1. Collecting Papers from Multiple Sources

```python
from src.data.collectors.citation_collector import CitationCollector
from src.data.models import CollectionQuery

# Initialize the collector
collector = CitationCollector()

# Test which APIs are working
api_status = collector.test_all_sources()
print(f"API Status: {api_status}")

# Create a query
query = CollectionQuery(
    domain="Machine Learning",
    year=2023,
    venue="NeurIPS",
    keywords=["deep learning", "neural networks"],
    max_results=50,
    min_citations=0
)

# Collect from all sources
results = collector.collect_from_all_sources(query)

# Process results
for source_name, result in results.items():
    print(f"{source_name}: {len(result.papers)} papers found")
    for paper in result.papers[:5]:  # Show first 5
        print(f"  - {paper.title} ({paper.citations} citations)")
```

### 2. Collecting from Specific Venues

```python
# Method 1: Direct venue search
papers = collector.collect_from_venue_year(
    venue="ICML",
    year=2022,
    citation_threshold=10,
    working_apis=["openalex", "semantic_scholar"]
)

# Method 2: Venue + keywords search
papers = collector.collect_from_venue_year_with_keywords(
    venue="ICLR",
    year=2023,
    keywords=["transformer", "attention"],
    domain="Natural Language Processing",
    working_apis=["semantic_scholar"]
)

# Method 3: Pure keyword search
papers = collector.collect_from_keywords(
    keywords=["reinforcement learning", "robotics"],
    year=2023,
    domain="Robotics",
    working_apis=["openalex", "semantic_scholar"]
)
```

### 3. Using Individual Source APIs

```python
from src.data.sources.openalex import OpenAlexSource
from src.data.sources.semantic_scholar import SemanticScholarSource
from src.data.models import CollectionQuery

# Use OpenAlex directly
openalex = OpenAlexSource()
query = CollectionQuery(
    domain="Computer Vision",
    year=2023,
    venue="CVPR",
    max_results=100
)
result = openalex.search_papers(query)
print(f"OpenAlex found {len(result.papers)} papers")

# Use Semantic Scholar directly
s2 = SemanticScholarSource()
result = s2.search_papers(query)
print(f"Semantic Scholar found {len(result.papers)} papers")
```

## Collecting NeurIPS Papers

See `collect_neurips_papers.py` for a complete example. Here's a quick snippet:

```python
from examples.collect_neurips_papers import NeurIPSCollector

# Initialize collector
collector = NeurIPSCollector(output_dir="neurips_data")

# Collect single year
papers_2023 = collector.collect_neurips_by_year(2023, max_papers=100)

# Collect multiple years
results = collector.collect_multiple_years(
    start_year=2019,
    end_year=2023,
    papers_per_year=50
)

# Generate report
collector.generate_summary_report(results)
```

## Understanding the Data Models

### CollectionQuery
```python
CollectionQuery(
    domain: str,           # Research domain (e.g., "Machine Learning")
    year: int,            # Publication year
    venue: str = None,    # Venue name (e.g., "NeurIPS")
    keywords: List[str] = [], # Search keywords
    max_results: int = 50,    # Maximum papers to retrieve
    min_citations: int = 0    # Minimum citation count
)
```

### Paper Object
```python
Paper(
    title: str,
    authors: List[Author],
    venue: str,
    year: int,
    citations: int,
    abstract: str,
    doi: str,
    urls: List[str],
    source: str,  # Which API provided this paper
    collection_timestamp: str
)
```

## Tips for Effective Collection

### 1. API Rate Limits
- **OpenAlex**: Most generous limits, good for bulk collection
- **Semantic Scholar**: Moderate limits, use API key for better rates
- **Google Scholar**: Very restrictive, use sparingly

### 2. Venue Name Variations
Different sources use different venue names:
- NeurIPS: "NeurIPS", "Neural Information Processing Systems", "NIPS"
- ICML: "ICML", "International Conference on Machine Learning"
- ICLR: "ICLR", "International Conference on Learning Representations"

### 3. Handling Failures
```python
# Always check API status first
api_status = collector.test_all_sources()
working_apis = [api for api, status in api_status.items() if status]

# Use only working APIs
papers = collector.collect_from_venue_year(
    venue="NeurIPS",
    year=2023,
    working_apis=working_apis  # Only use APIs that are working
)
```

### 4. Deduplication
Papers often appear in multiple sources. Simple deduplication:
```python
def deduplicate_papers(papers):
    seen_titles = set()
    unique_papers = []
    
    for paper in papers:
        normalized_title = paper['title'].lower().strip()
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_papers.append(paper)
    
    return unique_papers
```

## Advanced Usage

### Using Enhanced Collectors

The package also provides enhanced versions with better error handling:

```python
from src.data.sources.enhanced_openalex import EnhancedOpenAlexClient
from src.data.sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient

# These have additional features like:
# - Better rate limiting
# - Automatic retries
# - Progress tracking
# - Checkpoint support
```

### Collecting with PDF Discovery

To find PDF URLs for collected papers:

```python
from src.pdf_discovery.sources.openreview_collector import OpenReviewPDFCollector
from src.data.models import Paper

# Create a Paper object
paper = Paper(
    title="Your Paper Title",
    venue="NeurIPS",
    year=2023,
    # ... other fields
)

# Try to find PDF
collector = OpenReviewPDFCollector()
pdf_records = collector.collect([paper])

if pdf_records:
    print(f"Found PDF at: {pdf_records[0].pdf_url}")
```

## Common Issues and Solutions

1. **Rate Limiting**: Add delays between requests, use working_apis parameter
2. **Venue Not Found**: Try different venue name variations or use keyword search
3. **Low Paper Count**: Reduce min_citations, increase max_results
4. **API Failures**: Check connectivity, use fallback sources

## Next Steps

- See `example_neurips_pipeline.py` for complete PDF download pipeline
- Check `computational_filtering_usage.py` for filtering papers by computational requirements
- Review test files in `tests/integration/` for more usage examples