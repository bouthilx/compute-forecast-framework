# Consolidate Command Implementation Plan (Revised)

**Date**: 2025-07-10
**Time**: 11:00 
**Task**: Revised plan for `cf consolidate` command based on discussion feedback

## Executive Summary

The `cf consolidate` command will enrich paper metadata collected via `cf collect` by adding citations, abstracts, and affiliations from multiple sources (OpenAlex, Semantic Scholar, Crossref). Since PDF URLs are now well-handled by direct venue collection, the focus shifts to citation counts, abstracts, and potentially affiliations (though affiliations may be better suited for the extraction phase). The implementation will maintain provenance by storing all collected values with source and timestamp information.

## Analysis Performed

### Current State Assessment

Examined the existing codebase structure to understand:
1. **Metadata models**: `Paper` model with existing fields for enrichment (SimplePaper is used only for scrapers)
2. **PDF discovery module**: Originally designed for consolidation, should be migrated
3. **Available enrichment sources**: Enhanced API clients for OpenAlex and Semantic Scholar
4. **Existing utilities**: Affiliation parsers, deduplication logic, and batch processing

### Key Findings

1. **Module Migration**: The `pdf_acquisition/discovery/` module was meant for consolidation and should be moved
2. **Data Model**: Use `Paper` model throughout consolidation (no need for SimplePaper)
3. **Provenance Tracking**: Need to store all values from different sources with timestamps
4. **Affiliation Question**: Need to test if affiliations are available via API queries

## Detailed Implementation Plan

### 1. Module Architecture

```
compute_forecast/pipeline/consolidation/
├── orchestrator.py              # Main consolidation orchestrator
├── deduplication/
│   ├── paper_matcher.py        # Paper matching logic
│   ├── similarity.py           # Similarity metrics (Levenshtein, token-based)
│   └── strategies.py           # Matching strategies (DOI, title, author)
├── sources/
│   ├── base.py                 # BaseConsolidationSource abstract class
│   ├── openalex.py            # OpenAlex enrichment
│   ├── semantic_scholar.py     # Semantic Scholar enrichment
│   ├── crossref.py            # Crossref for DOIs and citation counts
│   └── registry.py            # Source registry and configuration
├── enrichment/
│   ├── citation_enricher.py    # Citation count consolidation
│   ├── abstract_enricher.py   # Abstract selection and quality checks
│   ├── affiliation_enricher.py # Author affiliation enrichment (if available via API)
│   └── keyword_enricher.py    # Keyword extraction and normalization
└── models.py                   # ConsolidationResult, EnrichmentMetadata

compute_forecast/cli/commands/
└── consolidate.py              # CLI command implementation
```

### 2. Refactoring Plan

#### Module Migration:
- Move `compute_forecast/pipeline/pdf_acquisition/discovery/` → `compute_forecast/pipeline/consolidation/discovery/`
- Rename `compute_forecast/pipeline/pdf_acquisition/` → `compute_forecast/pipeline/download/`
- Integrate discovery sources into consolidation sources

#### Code to Reuse:
- Rate limiting from PDF collectors
- Batch API handling from enhanced metadata sources  
- Retry logic and error handling patterns
- Existing affiliation parser (if affiliations available via API)

### 3. Model Revisions

#### Author Model Update
The Author model needs revision to better support consolidation:
```python
@dataclass
class Author:
    name: str
    affiliations: List[str] = field(default_factory=list)  # Changed from single affiliation
    email: str = ""
    # Removed: author_id (not needed)
    # Removed: normalize_affiliation() method (handled externally)
```

- Authors exist only within Paper objects (no separate storage)
- Affiliations are now a list to handle multiple affiliations
- Normalization will be handled by external services/modules

### 4. Enrichment Strategy with Provenance

All enriched fields will be stored as lists with source tracking:
```python
# Example structure for citations (total count only)
"citations": [
    {
        "source": "semantic_scholar",
        "timestamp": "2025-01-09T10:30:00Z",
        "data": {"count": 45}
    },
    {
        "source": "openalex",
        "timestamp": "2025-01-09T10:31:00Z", 
        "data": {"count": 43}
    }
]
```

#### Citations (High Priority):
- **Sources**: Semantic Scholar, OpenAlex, Crossref
- **Storage**: List of citation records with source/timestamp
- **Access**: Property getter returns max citation count from all sources

#### Abstracts (High Priority):
- **Sources**: Original + all API sources
- **Selection**: Keep original if present, otherwise first found
- **Storage**: List of abstract records with source/timestamp

#### Affiliations (Test First):
- **Sources**: OpenAlex, Semantic Scholar (need to verify availability)
- **Decision**: If not readily available via API, defer to extraction phase
- **Storage**: List of affiliation records per author if available

#### PDF URLs (Low Priority):
- **Sources**: Original URLs + ArXiv + any additional from APIs
- **Note**: Since venue collection handles most PDFs, this is low priority

#### Keywords:
- **Storage**: Separate lists for:
  - `keywords_original`: From paper metadata
  - `keywords_api`: From API sources  
  - `keywords_inferred`: Extracted from title/abstract
- **Processing**: Keep source separation for analysis

### 5. Deduplication Strategy

```python
# Create duplicate entries with sorted IDs to avoid duplication
# Always sort IDs: paper_id_1, paper_id_2 = sorted([some_paper_id, some_other_paper_id])
"duplicates": [
    {
        "paper_id_1": "abc123",  # Always the smaller ID
        "paper_id_2": "def456",  # Always the larger ID
        "similarity_score": 0.95,
        "match_details": {
            "doi_match": True,
            "title_similarity": 0.98,
            "author_overlap": 0.85,
            "venue_match": True
        }
    }
]
```

#### Deduplication Algorithm

```python
# Hierarchical matching with confidence scores
MATCHING_STRATEGIES = [
    (match_by_doi, 0.99),          # Exact DOI match
    (match_by_arxiv_id, 0.98),     # Exact ArXiv ID
    (match_by_ss_id, 0.95),        # Semantic Scholar ID
    (match_by_title_year, 0.90),   # Fuzzy title + exact year
    (match_by_title_authors, 0.85), # Fuzzy title + author overlap
    (match_by_venue_title, 0.80),  # Same venue + fuzzy title
]
```

### 6. CLI Interface Design

```bash
# Basic usage
cf consolidate --input collected_papers.json --output consolidated_papers.json

# Selective enrichment
cf consolidate --input data.json --enrich citations,abstracts

# Source selection
cf consolidate --input data.json --sources openalex,semantic_scholar

# Confidence threshold for deduplication
cf consolidate --input data.json --min-confidence 0.8

# Dry run mode
cf consolidate --input data.json --dry-run

# Resume from checkpoint
cf consolidate --input data.json --resume

# Parallel processing
cf consolidate --input data.json --parallel 4
```

### 7. Data Flow

1. **Load Phase**: Read collected papers JSON, validate schema
2. **Deduplication Phase**: Identify duplicates, create duplicate entries with similarity metrics
3. **Enrichment Phase**: 
   - Batch papers for API efficiency (minimize total queries)
   - Query sources in parallel
   - Store all results with provenance
4. **Output Phase**: Save enriched dataset with complete provenance

### 8. Checkpointing Implementation

```python
# Checkpoint structure
{
    "progress": {
        "total_papers": 10000,
        "processed_papers": 5000,
        "last_paper_id": "xyz789"
    },
    "enrichment_status": {
        "citations": {"completed": ["paper1", "paper2"], "failed": []},
        "abstracts": {"completed": ["paper1"], "failed": ["paper3"]}
    },
    "timestamp": "2025-01-09T11:00:00Z"
}
```

Save checkpoints:
- Every N papers (configurable, default 100)
- After each source completes
- On graceful shutdown (SIGINT handler)

### 9. Quality Metrics

Track and report:
- Enrichment coverage per field (% papers enriched)
- API query efficiency (papers per query)
- Duplicate detection statistics
- Processing time per source
- Data completeness improvements

## Implementation Priorities

1. **Phase 1** (High Priority):
   - Author model revision
   - Citation enrichment with provenance
   - Abstract enrichment

2. **Phase 2** (Medium Priority):
   - Test affiliation availability via APIs
   - Crossref integration
   - Checkpoint/resume capability

3. **Phase 3** (Lower Priority):
   - Keyword separation and tracking
   - Paper deduplication system (creating duplicate entries)
   - PDF URL enrichment (if gaps found)
   - Performance optimizations

## Risk Mitigation

1. **API Rate Limits**: Implement adaptive rate limiting with backoff
2. **Large Datasets**: Checkpointing every 100 papers, ability to resume
3. **Inconsistent Data**: Store all values with provenance for later analysis
4. **Source Failures**: Graceful degradation, partial enrichment allowed

## Success Criteria

- Enrich 80%+ of papers with citations
- Enrich 70%+ of papers with abstracts
- Process 10K papers in under 30 minutes
- Zero data loss with checkpoint/resume
- Complete provenance tracking for all enriched data

## Next Steps

1. Test affiliation availability via OpenAlex/Semantic Scholar APIs
2. Create base consolidation source interface with provenance
3. Implement duplicate detection (not merging)
4. Build CLI command in correct location
5. Design checkpoint format and recovery logic

This revised plan focuses on high-priority enrichments while maintaining complete data provenance and preparing for robust production use.
