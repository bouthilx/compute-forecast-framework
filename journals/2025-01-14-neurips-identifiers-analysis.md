# Analysis: Adding ArXiv ID, S2 ID, and CorpusId to NeurIPS Scraper

**Date**: 2025-01-14
**Task**: Investigate feasibility of extracting ArXiv ID, S2 ID, and CorpusId from NeurIPS scraper sources

## Executive Summary

After analyzing the NeurIPS scraper implementation and its data sources, I found that **these identifiers are NOT available from the primary NeurIPS proceedings website**. The scrapers would need to be enhanced with cross-referencing capabilities to obtain these identifiers from external sources.

## Current NeurIPS Scraper Architecture

### 1. Primary Implementation (`paperoni/src/paperoni/sources/scrapers/neurips.py`)
- Scrapes directly from `https://proceedings.neurips.cc`
- Extracts from two sources:
  - **Metadata JSON**: `{base_url}/paper_files/paper/{year}/file/{hash}-Metadata.json`
  - **BibTeX file**: `{base_url}/paper_files/paper/{year}/file/{hash}-Bibtex.bib` (fallback)
- Fields currently extracted:
  - Title, authors, affiliations
  - Abstract (from metadata only)
  - PDF/HTML links
  - Pages, volume, publisher info

### 2. Simplified Adapter (`compute_forecast/pipeline/metadata_collection/sources/scrapers/paperoni_adapters/neurips.py`)
- Direct HTML scraping implementation
- Extracts basic information from proceedings page
- No external API calls or cross-referencing

## Data Source Analysis

### What the NeurIPS Proceedings Website Provides:
1. **Metadata JSON** fields:
   - `title`, `abstract`, `authors` (with affiliations)
   - `book`, `publisher`, `volume`
   - `page_first`, `page_last`
   - **NO external identifiers**

2. **BibTeX** fields:
   - Standard publication metadata
   - **NO ArXiv ID, DOI, or external identifiers**

3. **HTML pages**:
   - Contains meta tags for citation purposes
   - **NO links to ArXiv, Semantic Scholar, or DOI**

### What's Missing:
- ❌ ArXiv ID
- ❌ Semantic Scholar paper ID (S2 ID)
- ❌ Semantic Scholar corpus ID
- ❌ DOI (Digital Object Identifier)
- ❌ OpenAlex ID

## Cross-Reference Evidence

From the codebase analysis, I found that many NeurIPS papers DO have these identifiers, but they come from external sources:

1. **Test data examples** show NeurIPS papers with:
   - ArXiv IDs (e.g., "Attention Is All You Need" → `1706.03762`)
   - Semantic Scholar IDs (e.g., `204e3073870fae3d05bcbc2f6a8e263d9b72e776`)
   - DOIs (e.g., `10.48550/arXiv.1706.03762`)

2. **Data models** already support these fields:
   - `SimplePaper.arxiv_id`
   - `Paper.arxiv_id`
   - `Paper.paper_id` (for S2 ID)
   - `Paper.openalex_id`

## Implementation Recommendations

To add these identifiers to the NeurIPS scraper, we would need to:

### Option 1: Post-Processing Enhancement (Recommended)
1. Keep the current scraper as-is for initial data collection
2. Use the existing cross-reference infrastructure:
   - `enhanced_semantic_scholar.py` for S2 ID and CorpusId
   - `enhanced_crossref.py` for DOI lookup
   - ArXiv API for ArXiv ID matching
3. Match papers by title/authors during consolidation phase

### Option 2: Inline Cross-Referencing
1. Modify the scraper to make additional API calls during scraping
2. For each paper, query:
   - Semantic Scholar API by title
   - CrossRef API for DOI
   - ArXiv API for potential matches
3. **Drawbacks**: Slower, more complex, rate limit concerns

### Option 3: Hybrid Approach
1. Add optional cross-reference capability to scraper
2. Store potential matches as "hints"
3. Validate during consolidation phase

## Technical Considerations

1. **Rate Limits**: External APIs have rate limits that could slow scraping
2. **Matching Accuracy**: Title/author matching isn't 100% reliable
3. **Performance**: Cross-referencing during scraping would significantly slow the process
4. **Architecture**: The current design separates scraping from enrichment, which is cleaner

## Conclusion

The NeurIPS proceedings website does not provide ArXiv IDs, S2 IDs, or CorpusIds. These identifiers must be obtained through cross-referencing with external sources. The existing architecture already supports this through the consolidation pipeline, making Option 1 (post-processing enhancement) the most practical approach.

The scraper models already have the necessary fields to store these identifiers once obtained, so the main work would be ensuring the consolidation pipeline properly enriches NeurIPS papers with data from Semantic Scholar, CrossRef, and ArXiv.