# AAAI Scraper Research

**Date**: 2025-01-09
**Analysis**: AAAI venues scraping feasibility and implementation approach

## Overview

This research investigates how to implement a scraper for AAAI (Association for the Advancement of Artificial Intelligence) venues following the OpenReview adapter pattern. The goal is to collect papers from AAAI conferences programmatically.

## AAAI Venues in Dataset

Based on `venue_mapping_final.csv`, the following AAAI-related venues are mapped:
- **AAAI** (main conference) - 14 occurrences
- **AAAI.org/2023/Bridge/CCBridge** - 3 occurrences
- **Proceedings of the 2023 AAAI/ACM Conference on AI, Ethics, and Society** - 8 occurrences
- **Proceedings of the AAAI Conference on Artificial Intelligence** - 42 occurrences

Total: 67 papers mapped to AAAI venues (1.58% of dataset)

## Publishing Infrastructure

AAAI uses **Open Journal Systems (OJS)** for their publications:
- **URL**: https://ojs.aaai.org/
- **Version**: OJS 3.2.1.1 (some instances use 3.1.2.1)
- **Conferences hosted**:
  - AAAI Conference on Artificial Intelligence
  - AAAI Conference on Human Computation and Crowdsourcing (HCOMP)
  - International AAAI Conference on Web and Social Media (ICWSM)
  - AAAI Symposium Series
  - And others

## Programmatic Access Options

### 1. OAI-PMH Protocol (Recommended)

OJS natively supports OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting):

- **Typical endpoint**: `https://ojs.aaai.org/index.php/AAAI/oai`
- **Available verbs**:
  - `Identify` - Get repository information
  - `ListMetadataFormats` - See available metadata formats (Dublin Core, possibly JATS)
  - `ListSets` - Get available sets/collections
  - `ListRecords` - Harvest all records
  - `GetRecord` - Get a specific record

**Advantages**:
- Standard protocol, well-documented
- Provides structured metadata
- Can filter by date ranges
- Batch harvesting support

**Limitations**:
- Only provides metadata, not full PDFs
- PDF access may require additional authentication

### 2. Direct Web Scraping

Alternative approach using the OJS web interface:
- Browse proceedings by year at https://ojs.aaai.org/index.php/AAAI/issue/archive
- Parse HTML pages to extract paper metadata
- Follow links to individual paper pages
- Extract PDF URLs when available

**Challenges**:
- More fragile (HTML structure changes)
- Rate limiting considerations
- Need to handle pagination

### 3. DBLP Integration

DBLP provides comprehensive AAAI indexing:
- **URL**: https://dblp.org/db/conf/aaai/index.html
- Contains proceedings back to 1997
- Provides DOIs and links to papers
- Could be used as a supplementary data source

## Implementation Recommendation

Based on the research, I recommend implementing an **OAI-PMH-based scraper** for AAAI venues:

### Architecture

```python
class AAIScraper(BasePaperoniAdapter):
    """Adapter for AAAI proceedings using OAI-PMH protocol."""

    def get_supported_venues(self) -> List[str]:
        return ["aaai", "aies", "hcomp", "icwsm"]

    def get_available_years(self, venue: str) -> List[int]:
        # AAAI: 1980-present
        # AIES: 2018-present
        # HCOMP: 2013-present
        # ICWSM: 2007-present

    def _call_paperoni_scraper(self, scraper, venue: str, year: int):
        # Use OAI-PMH to harvest metadata
        # Filter by date range for specific year
        # Parse returned XML records
        # Convert to SimplePaper objects
```

### Key Features

1. **OAI-PMH Client**: Use `sickle` or `pyoai` library for OAI-PMH harvesting
2. **Date Filtering**: Use OAI-PMH's `from` and `until` parameters to filter by year
3. **Metadata Parsing**: Extract title, authors, abstract from Dublin Core or JATS format
4. **PDF Discovery**: Parse OAI-PMH records for PDF links, or construct from paper IDs
5. **Rate Limiting**: Implement polite delays between requests

### Challenges to Address

1. **PDF Access**: OAI-PMH provides metadata but not necessarily PDF URLs
   - May need to construct PDF URLs from paper IDs
   - Some PDFs may be behind authentication

2. **Venue Mapping**: Need to map our venue names to OJS journal names
   - "aaai" → "AAAI"
   - "aies" → "AIES"
   - etc.

3. **Year Filtering**: OAI-PMH date filtering may not perfectly align with conference years
   - May need to parse dates from individual records

## Alternative: GitHub Aggregations

Found community-maintained repositories like:
- https://github.com/DmitryRyumin/AAAI-2024-Papers

These could provide supplementary data or validation but shouldn't be primary sources.

## Next Steps

1. Test OAI-PMH endpoint availability:
   ```bash
   curl "https://ojs.aaai.org/index.php/AAAI/oai?verb=Identify"
   ```

2. Explore metadata formats:
   ```bash
   curl "https://ojs.aaai.org/index.php/AAAI/oai?verb=ListMetadataFormats"
   ```

3. Sample record harvest:
   ```bash
   curl "https://ojs.aaai.org/index.php/AAAI/oai?verb=ListRecords&metadataPrefix=oai_dc&from=2024-01-01&until=2024-12-31"
   ```

4. Implement OAI-PMH client in Python using existing libraries

## Conclusion

AAAI scraping is feasible using their OJS platform's OAI-PMH interface. This approach is more robust than HTML scraping and aligns with open archive standards. The main challenge will be obtaining PDF URLs, which may require additional logic beyond what OAI-PMH provides.
