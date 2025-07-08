# CF Collect Implementation

**Date**: 2025-01-08  
**Time**: 19:00  
**Task**: Implementation of `cf collect` command

## Summary

Successfully implemented the `cf collect` command as specified in the design documents. The implementation provides a unified interface for collecting papers from multiple venues using both custom scrapers and simplified adapters.

## Implementation Details

### 1. CLI Structure
- Migrated from argparse to Typer for better CLI experience
- Created proper module structure under `compute_forecast/cli/`
- Commands are now modular and can be easily extended

### 2. Scraper Registry
- Implemented `ScraperRegistry` class to manage available scrapers
- Supports dynamic scraper discovery and loading
- Maps venues to appropriate scrapers with fallback support
- Case-insensitive venue matching for better usability

### 3. Paperoni Adapters
- Created simplified adapters that don't require full paperoni integration:
  - **NeurIPSAdapter**: Direct web scraping from proceedings.neurips.cc
  - **SemanticScholarAdapter**: Uses the semanticscholar Python package
  - **MLRAdapter**: Stub implementation (fallback to Semantic Scholar)
  - **OpenReviewAdapter**: Uses openreview-py package

### 4. Collect Command Features
- ✅ Single venue/year collection
- ✅ Multiple venues support
- ✅ Year range parsing (2020-2024 format)
- ✅ Maximum papers limit
- ✅ Progress bars with Rich
- ✅ Resume capability with checkpoints
- ✅ JSON output with metadata
- ✅ Case-insensitive venue names

### 5. Output Format
```json
{
  "collection_metadata": {
    "timestamp": "2025-01-08T18:50:35.725085",
    "venues": ["NeurIPS"],
    "years": [2023],
    "total_papers": 3,
    "scrapers_used": ["paperoni_neurips"]
  },
  "papers": [
    {
      "title": "Paper Title",
      "authors": ["Author 1", "Author 2"],
      "venue": "NeurIPS",
      "year": 2023,
      "pdf_urls": ["https://..."],
      "source_scraper": "paperoni_neurips",
      "source_url": "https://..."
    }
  ]
}
```

## Testing Results

1. **NeurIPS Collection**: ✅ Working
   - Successfully scraped papers from proceedings.neurips.cc
   - Extracted titles, authors, and PDF URLs

2. **IJCAI Collection**: ✅ Working  
   - Uses existing IJCAIScraper implementation
   - Case-insensitive venue matching added

3. **Multiple Venues**: ⚠️ Intermittent issues
   - Individual venues work fine
   - Some state issues when collecting multiple venues in sequence

## Known Limitations

1. **Semantic Scholar**: Not tested (as requested)
2. **MLR/PMLR venues**: Stub implementation only
3. **OpenReview**: Basic implementation, may need refinement
4. **Rate limiting**: Basic delay implemented, could be more sophisticated
5. **Error recovery**: Basic retry logic, could be enhanced

## Usage Examples

```bash
# Basic collection
cf collect --venue neurips --year 2023

# With limits
cf collect --venue ijcai --year 2023 --max-papers 100

# Multiple venues
cf collect --venues neurips,ijcai --year 2023

# Year range
cf collect --venue neurips --years 2020-2024

# Resume interrupted collection
cf collect --venue neurips --year 2023 --resume
```

## Next Steps

1. Implement proper PMLR scraping for ICML/AISTATS/UAI
2. Enhance error handling and retry logic
3. Add parallel collection support
4. Implement venue file support
5. Add more comprehensive testing
6. Optimize for large-scale collections

## Technical Decisions

1. **Typer over Click**: Better type hints and modern CLI experience
2. **Simplified adapters**: Avoided complex paperoni integration for faster implementation
3. **Direct API usage**: Used official Python clients where available
4. **Case-insensitive venues**: Better user experience
5. **Rich progress bars**: Clear feedback during long operations

The implementation successfully provides the core functionality needed for paper collection while maintaining flexibility for future enhancements.
