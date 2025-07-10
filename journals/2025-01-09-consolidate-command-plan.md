# Consolidate Command Implementation Plan

**Date**: 2025-01-09  
**Time**: 10:30  
**Task**: Design comprehensive plan for `cf consolidate` command to enrich collected paper metadata

## Executive Summary

The `cf consolidate` command will enrich paper metadata collected via `cf collect` by adding citations, PDF URLs, author affiliations, abstracts, and keywords from multiple sources (OpenAlex, Semantic Scholar, Crossref). The implementation requires restructuring existing modules to avoid duplication, implementing robust paper deduplication, and creating a unified enrichment pipeline.

[@bouthilx Actually, since we now rely on metadata collection directly from venues we should have
the PDF urls well handled. This part should be low priority. The high priority now would be
citations, abstracts and affiliations. The affiliations is a bit more tricky because we will need to
download the PDF and extract them. We should perhaps move affiliation to the extraction phase of the
pipeline instead of consolidation.]

## Analysis Performed

### Current State Assessment

Examined the existing codebase structure to understand:
[@bouthilx Why would we need `SimplePaper` instead of using `Paper` only?]
1. **Metadata models**: `Paper` and `SimplePaper` models with existing fields for enrichment
2. **Duplicate functionality**: PDF discovery sources overlap with consolidation needs
3. **Available enrichment sources**: Enhanced API clients for OpenAlex and Semantic Scholar
4. **Existing utilities**: Affiliation parsers, deduplication logic, and batch processing

### Key Findings

1. **Module Duplication**: PDF acquisition sources (`openalex_collector.py`, `semantic_scholar_collector.py`) duplicate functionality needed for consolidation
2. **Existing Infrastructure**: Enhanced API clients already support batch queries and error handling
3. **Data Models**: `SimplePaper` from scrapers lacks some fields (affiliations, citations) that exist in the full `Paper` model
4. **Deduplication Needs**: Multiple matching strategies required (DOI, title fuzzy matching, author overlap)

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
│   ├── openalex.py            # OpenAlex enrichment (merge with PDF collector)
│   ├── semantic_scholar.py     # Semantic Scholar enrichment
│   ├── crossref.py            # Crossref for DOIs and citation counts
│   └── registry.py            # Source registry and configuration
├── enrichment/
│   ├── citation_enricher.py    # Citation count consolidation
│   ├── pdf_enricher.py        # PDF URL discovery and validation
│   ├── affiliation_enricher.py # Author affiliation enrichment
│   ├── abstract_enricher.py   # Abstract selection and quality checks
│   └── keyword_enricher.py    # Keyword extraction and normalization
├── models.py                   # ConsolidationResult, EnrichmentMetadata
[@bouthilx No, the CLI should be implemented in compute_forecast/cli/commands/consolidate.py]
└── cli.py                      # CLI command implementation
```

### 2. Refactoring Plan

[@bouthilx The module compute_forecast/pipeline/pdf_acquisition/discovery/ was strickly meant for consolidation. We should migrate it to the consolidation module, and turn compute_forecast/pipeline/pdf_acquisition/discovery/ into compute_forecast/pipeline/download]
#### Modules to Merge/Remove:
- `pdf_acquisition/discovery/sources/openalex_collector.py` → Merge into `consolidation/sources/openalex.py`
- `pdf_acquisition/discovery/sources/semantic_scholar_collector.py` → Merge into `consolidation/sources/semantic_scholar.py`
- Keep venue-specific PDF collectors as they serve different purpose

#### Code to Reuse:
- Rate limiting from PDF collectors
- Batch API handling from enhanced metadata sources  
- Retry logic and error handling patterns
- Existing affiliation parser and normalizer

### 3. Enrichment Strategy

[@bouthilx All fields we will gather for consolidation should be in the form of a list with dict
entries for each sources we gather in the form of {source: <>, timestamp: <>, data: <>}. I want to
have a trace of all values we may gather over time, even from the same source.]

#### Citations:
- **Sources**: Semantic Scholar (primary), OpenAlex, Crossref
[@bouthilx This will be implemented as a getter on the paper. But the data itself in the paper
record will contain all citations count we have found (see previous comment)]
- **Resolution**: Take maximum count with timestamp
- **Storage**: Add `citation_count` and `citation_updated_at` fields

#### PDF URLs:
[@bouthilx Many will be on arxiv as well.]
- **Sources**: Original URLs + OpenAlex + Semantic Scholar + Unpaywall
- **Validation**: HEAD request to verify accessibility
- **Deduplication**: Hash-based duplicate detection

#### Affiliations:
[@bouthilx if we can have them from simple queries then yes, affiliations should be part of
consolidation. And we can try improve during extraction. Let's test if this info is available.]
- **Sources**: OpenAlex (best coverage), Semantic Scholar
- **Matching**: Fuzzy author name matching
- **Normalization**: Use existing `enhanced_affiliation_parser.py`

#### Abstracts:
- **Sources**: Original + all API sources
- **Selection**: Original or first found
- **Validation**: Language detection, minimum length (100 chars)

#### Keywords:
- **Sources**: Original + API sources + extracted from title/abstract
[@bouthilx We should separate original keywords from API sourcesd and infered ones.]
- **Processing**: Deduplication, normalization, relevance scoring

### 4. Deduplication Algorithm

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

### 5. CLI Interface Design

```bash
# Basic usage
cf consolidate --input collected_papers.json --output consolidated_papers.json

# Selective enrichment
cf consolidate --input data.json --enrich citations,pdfs,affiliations

# Source selection
cf consolidate --input data.json --sources openalex,semantic_scholar

# Confidence threshold
cf consolidate --input data.json --min-confidence 0.8

# Dry run mode
cf consolidate --input data.json --dry-run

# Resume from checkpoint
cf consolidate --input data.json --resume

# Parallel processing
cf consolidate --input data.json --parallel 4
```

### 6. Data Flow

1. **Load Phase**: Read collected papers JSON, validate schema
[@bouthilx We won't merge duplicate papers but rather create duplicates entries which refer to both
papers with a similarity score and detailed metrics for computing that similarity score]
2. **Deduplication Phase**: Identify and merge duplicate papers
3. **Enrichment Phase**: 
   - Batch papers by venue/year for efficiency
   [@bouthilx try to batch papers in queries to reduce the number of overall queries]
   - Query sources in parallel
   - Aggregate results with confidence scores
[@bouthilx No need to]
4. **Resolution Phase**: Resolve conflicts, select best data
5. **Output Phase**: Save enriched dataset with provenance

### 7. Quality Metrics

Track and report:
- Enrichment coverage per field (% papers enriched)
- Confidence distribution for matches
- API calls and costs per source
- Conflicts resolved and strategies used
- Processing time and throughput

## Implementation Priorities

1. **Phase 1** (High Priority):
   - Paper deduplication system
   - OpenAlex and Semantic Scholar sources
   - Citation and PDF enrichment

2. **Phase 2** (Medium Priority):
   - Affiliation and abstract enrichment
   - Crossref integration
   - Checkpoint/resume capability

3. **Phase 3** (Lower Priority):
   - Keyword extraction
   [@bouthilx no need to]
   - Advanced conflict resolution
   - Performance optimizations

## Risk Mitigation

1. **API Rate Limits**: Implement adaptive rate limiting with backoff
[@bouthilx How will the checkpointing be implemented?]
2. **Large Datasets**: Streaming processing, checkpointing
3. **Inconsistent Data**: Confidence scoring, manual review flags
4. **Source Failures**: Graceful degradation, partial enrichment

## Success Criteria

- Enrich 80%+ of papers with citations
- Find PDFs for 60%+ of papers
- Process 10K papers in under 30 minutes
- Maintain 95%+ deduplication accuracy
- Zero data loss with checkpoint/resume

## Next Steps

1. Create base consolidation source interface
2. Implement paper deduplication module
3. Adapt existing API clients for consolidation
4. Build CLI command with basic enrichment
5. Add comprehensive testing suite

This plan provides a solid foundation for implementing the consolidate command while maximizing code reuse and maintaining data quality.
