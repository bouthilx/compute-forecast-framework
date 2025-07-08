# Scraper Architecture Analysis

## Overview

The scraper architecture introduces a new data collection system that complements the existing citation sources. This analysis explains the purpose of different components and how they fit together.

## Key Components

### 1. Data Models

#### SimplePaper (scrapers/models.py)
- **Purpose**: Minimal paper representation that can be created from any web scraping source
- **Design Philosophy**: Keep it simple, capture only essential fields that are commonly available
- **Key Fields**:
  - Core: title, authors (list of names), venue, year
  - Optional: abstract, pdf_url, doi
  - Tracking: source_scraper, source_url, scraped_at
  - Quality: extraction_confidence
- **Integration**: Has `to_package_paper()` method to convert to the full Paper model

#### ScrapedPaper
- **Note**: This model is NOT implemented in the codebase. It appears to be a conceptual model that was replaced by SimplePaper.

#### Paper (data/models.py) 
- **Purpose**: The comprehensive paper model used throughout the analysis pipeline
- **Contains**:
  - Full author objects with affiliations
  - Multiple ID systems (Semantic Scholar, OpenAlex, ArXiv)
  - Analysis results (computational, authorship, venue)
  - Processing metadata
  - Citation information

### 2. Scraper Base Classes (scrapers/base.py)

#### BaseScaper
- **Purpose**: Abstract foundation for all scrapers
- **Features**:
  - HTTP session management with retries
  - Rate limiting
  - Caching support
  - Consistent error handling
- **Required Methods**:
  - `get_supported_venues()`: List venues this scraper can handle
  - `get_available_years()`: Years available for a venue
  - `scrape_venue_year()`: Main scraping method

#### ConferenceProceedingsScaper
- **Purpose**: For scraping conference websites (e.g., NeurIPS, ICML)
- **Approach**: Navigate to proceedings page, parse HTML
- **Additional Methods**:
  - `get_proceedings_url()`: Build URL for venue/year
  - `parse_proceedings_page()`: Extract papers from HTML

#### JournalPublisherScaper  
- **Purpose**: For journal publisher sites
- **Approach**: Search-based rather than enumeration
- **Additional Methods**:
  - `search_papers()`: Search by journal, keywords, year range

#### APIEnhancedScaper
- **Purpose**: For API-based sources requiring authentication
- **Features**:
  - Authentication handling
  - Pagination support
  - Batch processing
- **Additional Methods**:
  - `authenticate()`: Handle API authentication
  - `make_api_request()`: Make authenticated requests

### 3. Adapters

#### PaperoniAdapter (scrapers/models.py)
- **Purpose**: Convert papers from the existing Paperoni scraper system to SimplePaper
- **Handles**: Complex Paperoni data structures → SimplePaper
- **Key Feature**: Safe extraction with proper null checking

## Data Flow

```
1. Web Scraping Flow:
   Website/API → Scraper → SimplePaper → to_package_paper() → Paper → Analysis Pipeline

2. Citation Source Flow (existing):
   API → CitationSource → Paper → Analysis Pipeline

3. Paperoni Integration:
   Paperoni System → PaperoniAdapter → SimplePaper → Paper
```

## Architecture Distinctions

### CitationSources vs Scrapers

**CitationSources** (existing system):
- Purpose: Search across multiple venues using academic APIs
- Examples: Google Scholar, Semantic Scholar, OpenAlex
- Use Case: "Find all papers about transformers from 2020-2024"
- Returns: Papers matching search criteria from any venue

**Scrapers** (new system):
- Purpose: Complete extraction from specific venue/year
- Examples: Scraping all NeurIPS 2024 papers
- Use Case: "Get ALL papers from ICML 2023"
- Returns: Complete set of papers from that venue/year

### Why Both Systems?

1. **Coverage**: Some venues aren't well-indexed by citation APIs
2. **Completeness**: Scrapers ensure we get ALL papers from a venue
3. **Data Quality**: Direct scraping can capture venue-specific metadata
4. **Flexibility**: Different approaches for different data sources

## Unified Collection Pipeline (Issue #152)

Based on the architecture, the unified collection pipeline would likely:

1. **Input**: List of venues and years to collect
2. **Router**: Determine best collection method per venue:
   - Use CitationSource if venue is well-indexed
   - Use Scraper for complete venue extraction
   - Use Paperoni for legacy venues
3. **Deduplication**: Merge results from different sources
4. **Normalization**: Convert all to Paper model
5. **Output**: Unified dataset for analysis

## Implementation Status

### Completed:
- Base scraper classes framework (Issue #140)
- SimplePaper model and adapters
- Error handling infrastructure
- Test suite for base classes

### Not Implemented:
- ScrapedPaper model (replaced by SimplePaper)
- Concrete scraper implementations
- Unified collection orchestrator
- Integration with main pipeline

## Key Design Decisions

1. **Simplicity First**: SimplePaper has minimal fields to work with any source
2. **Separation of Concerns**: Scrapers are independent of citation sources
3. **Adapter Pattern**: Convert between different paper representations
4. **Error Resilience**: Comprehensive error handling and retry logic
5. **Rate Limiting**: Built into base classes to respect server limits

## Next Steps

To complete the unified collection pipeline:

1. Implement concrete scrapers for key venues
2. Create collection orchestrator that routes to appropriate source
3. Build deduplication engine for merged results
4. Integrate with existing analysis pipeline
5. Add monitoring and quality checks