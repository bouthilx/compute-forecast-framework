# CF Collect Implementation Plan

**Date**: 2025-01-08
**Time**: 16:45
**Task**: Design and implement `cf collect` command for unified paper collection

## Executive Summary

Implement `cf collect` as a unified interface to multiple paper scrapers, leveraging existing scrapers from paperoni and custom implementations from issue_140. This provides comprehensive venue coverage through a single CLI command with consistent output format.

## Current State Analysis

### Available Scrapers

**Custom Scrapers (issue_140 branch)**:
- `IJCAIScraper` - IJCAI proceedings scraper
- `ACLAnthologyScraper` - ACL Anthology (covers ACL, EMNLP, NAACL, COLING)

**Paperoni Scrapers**:
- `NeurIPS` - Direct proceedings scraper
- `MLR` - PMLR scrapers (covers ICML, AISTATS, UAI)
- `OpenReview` - ICLR and OpenReview-hosted conferences
- `JMLR` - Journal of Machine Learning Research
- `SemanticScholar` - Cross-venue API search
- `OpenAlex` - Alternative cross-venue API

### Existing Infrastructure

**Not Reusing**:
- `VenueCollectionOrchestrator` - Too complex for our needs
- `VenueCollectionEngine` - Designed for API batching, not scraping
- Rich dashboard monitoring - Will use simple progress bars instead

**Will Reuse**:
- `SimplePaper` data model from scrapers package
- Rate limiting patterns from scrapers
- Basic configuration structure

## Implementation Design

### 1. Venue-to-Scraper Mapping

```python
VENUE_SCRAPER_MAPPING = {
    # Direct scrapers with dedicated implementations
    "neurips": "NeurIPSScraper",
    "icml": "MLRScraper",
    "iclr": "OpenReviewScraper",
    "ijcai": "IJCAIScraper",
    "acl": "ACLAnthologyScraper",
    "emnlp": "ACLAnthologyScraper",
    "naacl": "ACLAnthologyScraper",
    "coling": "ACLAnthologyScraper",
    "jmlr": "JMLRScraper",
    "aistats": "MLRScraper",
    "uai": "MLRScraper",

    # Venues that require API search
    "cvpr": "SemanticScholarScraper",
    "iccv": "SemanticScholarScraper",
    "eccv": "SemanticScholarScraper",
    "aaai": "SemanticScholarScraper",
    "miccai": "SemanticScholarScraper",
    "kdd": "SemanticScholarScraper",
    "www": "SemanticScholarScraper",

    # Default fallback
    "*": "SemanticScholarScraper"
}
```

### 2. Configuration Structure (.env)

```bash
# API Credentials
SEMANTIC_SCHOLAR_API_KEY=your_key_here
OPENALEX_EMAIL=your_email@example.com

# Scraper Settings
SCRAPER_MAX_PAPERS_PER_VENUE=500
SCRAPER_TIMEOUT_SECONDS=300
SCRAPER_RETRY_ATTEMPTS=3
SCRAPER_RATE_LIMIT_DELAY=1.0

# Output Configuration
COLLECTION_OUTPUT_DIR=data/collected_papers/
COLLECTION_CHECKPOINT_DIR=.cf_state/collect/
COLLECTION_OUTPUT_FORMAT=json

# Progress Settings
COLLECTION_CHECKPOINT_INTERVAL=50  # Papers
COLLECTION_SHOW_PROGRESS=true
```

### 3. Unified Output Format

All scrapers output `SimplePaper` objects with these fields:

```python
@dataclass
class SimplePaper:
    # Required fields
    title: str
    authors: List[str]  # Simple author names
    venue: str
    year: int

    # Optional identifiers
    paper_id: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Content
    abstract: Optional[str] = None
    pdf_urls: List[str] = field(default_factory=list)

    # Tracking
    source_scraper: str = ""
    source_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)
    extraction_confidence: float = 1.0
```

### 4. File Structure

```
compute_forecast/
├── cli/
│   └── commands/
│       └── collect.py              # Main CLI command
├── data/
│   └── sources/
│       └── scrapers/
│           ├── registry.py         # Scraper registry
│           ├── paperoni_adapters/  # Adapters for paperoni scrapers
│           │   ├── __init__.py
│           │   ├── neurips.py
│           │   ├── mlr.py
│           │   ├── openreview.py
│           │   └── semantic_scholar.py
│           └── conference_scrapers/  # Existing custom scrapers
│               ├── ijcai_scraper.py
│               └── acl_anthology_scraper.py
```

### 5. Implementation Steps

#### Phase 1: Scraper Registry (4 hours)
- [ ] Create `ScraperRegistry` class
- [ ] Implement scraper discovery and loading
- [ ] Add venue-to-scraper mapping logic
- [ ] Handle fallback to Semantic Scholar

#### Phase 2: Paperoni Adapters (6 hours)
- [ ] Create base `PaperoniAdapter` class
- [ ] Implement `NeurIPSAdapter`
- [ ] Implement `MLRAdapter` for ICML/AISTATS/UAI
- [ ] Implement `OpenReviewAdapter` for ICLR
- [ ] Implement `SemanticScholarAdapter` as fallback

#### Phase 3: CLI Command (3 hours)
- [ ] Create `collect` command with Click
- [ ] Add venue/year parsing logic
- [ ] Implement progress tracking
- [ ] Add output formatting and saving

#### Phase 4: Resume & Checkpointing (3 hours)
- [ ] Implement checkpoint saving
- [ ] Add resume from checkpoint logic
- [ ] Handle partial collection recovery
- [ ] Test interruption scenarios

#### Phase 5: Integration & Testing (2 hours)
- [ ] Add unit tests for adapters
- [ ] Add integration tests for CLI
- [ ] Test with real venues
- [ ] Update documentation

### 6. CLI Usage Examples

```bash
# Collect single venue/year
cf collect neurips --year 2024

# Collect with paper limit
cf collect icml --year 2023 --max-papers 100

# Collect year range
cf collect iclr --years 2020-2024

# Collect multiple venues from file
cf collect --venue-file venues.txt --year 2024

# Resume interrupted collection
cf collect neurips --year 2024 --resume

# Custom output location
cf collect acl --year 2024 --output papers/acl_2024.json

# Disable progress bar (for scripts)
cf collect --venue-file venues.txt --years 2020-2024 --no-progress
```

### 7. Output Format

JSON output with consistent structure:

```json
{
  "collection_metadata": {
    "timestamp": "2025-01-08T16:45:00Z",
    "venues": ["neurips"],
    "years": [2024],
    "total_papers": 1532,
    "scrapers_used": ["NeurIPSScraper"]
  },
  "papers": [
    {
      "title": "Scaling Language Models...",
      "authors": ["John Doe", "Jane Smith"],
      "venue": "NeurIPS",
      "year": 2024,
      "abstract": "...",
      "pdf_urls": ["https://..."],
      "doi": "10.1234/...",
      "source_scraper": "NeurIPSScraper",
      "source_url": "https://proceedings.neurips.cc/...",
      "scraped_at": "2025-01-08T16:45:00Z"
    }
  ]
}
```

### 8. Error Handling Strategy

1. **Scraper Failures**: Log error, continue with next venue
2. **Rate Limiting**: Exponential backoff with configurable delays
3. **Network Errors**: Retry with configurable attempts
4. **Parse Errors**: Log and skip individual papers
5. **API Limits**: Warn user and suggest alternatives

### 9. Quality Considerations

- Papers must have minimum required fields (title, authors, venue, year)
- Confidence scoring based on field completeness
- Deduplication within collection batch
- Validation of year/venue consistency

### 10. Future Enhancements

1. **Parallel Collection**: Multiple venues simultaneously
2. **Smart Caching**: Avoid re-scraping recent collections
3. **Quality Filters**: Citation count, keyword matching
4. **Export Formats**: CSV, Parquet for direct analysis
5. **Collection Stats**: Summary statistics and quality metrics

## Success Criteria

1. **Coverage**: Support for all major ML/AI venues
2. **Reliability**: Robust error handling and resume capability
3. **Performance**: Collect 1000+ papers in under 5 minutes
4. **Consistency**: Uniform output regardless of source scraper
5. **Usability**: Simple CLI with sensible defaults

## Risk Mitigation

1. **Scraper Breakage**: API-based fallbacks for all venues
2. **Rate Limiting**: Configurable delays and retry logic
3. **Large Collections**: Checkpointing and batch processing
4. **Missing Scrapers**: Semantic Scholar as universal fallback
5. **Data Quality**: Validation and confidence scoring

## Timeline

- **Day 1**: Scraper registry and paperoni adapters
- **Day 2**: CLI implementation and testing
- **Day 3**: Resume capability and integration
- **Total**: 18 hours estimated

This implementation provides a clean, unified interface to paper collection while maximizing reuse of existing scrapers and maintaining flexibility for future enhancements.
