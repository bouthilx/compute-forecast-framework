# Paperoni Scraper Analysis

## Overview

Paperoni is a comprehensive paper scraping framework with 10 scrapers covering various academic sources. The codebase is complex with a sophisticated data model and database backend.

## Available Scrapers

### 1. **NeurIPS Scraper** (`neurips.py` - 187 lines)
- **Coverage**: NeurIPS conference papers
- **Source**: proceedings.neurips.cc
- **Features**: 
  - Fetches papers by volume
  - Supports both JSON metadata and BibTeX formats
  - Extracts authors, affiliations, abstracts
- **Complexity**: Medium - straightforward proceedings scraper

### 2. **OpenReview Scraper** (`openreview.py` - 696 lines) ⭐
- **Coverage**: Multiple conferences that use OpenReview platform
  - ICLR (main conference)
  - Many workshops and smaller conferences
  - Can query by venue pattern (e.g., "ICLR.cc/*")
- **Features**:
  - Supports both API v1 and v2
  - Can fetch papers, venues, and author profiles
  - Handles complex decision tracking (accepted/rejected/withdrawn)
  - Supports venue wildcards for bulk collection
- **Complexity**: High - most complex scraper with multiple classes

### 3. **JMLR Scraper** (`jmlr.py` - 117 lines)
- **Coverage**: Journal of Machine Learning Research
- **Source**: jmlr.org
- **Features**: Basic proceedings scraper with BibTeX parsing
- **Complexity**: Low - simplest scraper

### 4. **MLR Scraper** (`mlr.py` - 131 lines) ⭐
- **Coverage**: Proceedings of Machine Learning Research (PMLR)
  - Includes ICML papers
  - Many other ML conferences published through PMLR
- **Source**: proceedings.mlr.press
- **Features**: YAML-based metadata extraction
- **Complexity**: Low - simple and efficient

### 5. **Semantic Scholar Scraper** (`semantic_scholar.py` - 509 lines) ⭐
- **Coverage**: Cross-venue search engine
  - Can search any conference/journal indexed by S2
  - Includes most major CS conferences
- **Features**:
  - Full-text search by author, title
  - Author profile fetching
  - Citation tracking
  - Requires API key
- **Complexity**: High - comprehensive API integration

### 6. **OpenAlex Scraper** (`openalex.py` - 409 lines) ⭐
- **Coverage**: Cross-venue academic search engine
  - Similar to Semantic Scholar but different coverage
  - Good for interdisciplinary papers
- **Features**: Not examined in detail
- **Complexity**: High

### 7. **Zeta-Alpha Scraper** (`zeta-alpha.py` - 154 lines)
- **Coverage**: Limited academic search engine
- **Features**: Basic search functionality
- **Complexity**: Medium

### 8. **PDF Affiliations Scraper** (`pdf_affiliations.py` - 178 lines)
- **Purpose**: Extract affiliations from PDF files
- **Not a venue scraper**

### 9. **Refine Scraper** (`refine.py` - 1002 lines)
- **Purpose**: Post-processing and data refinement
- **Not a primary data collector**

## Target Venue Coverage

From our milestone targets:
- **NeurIPS**: ✅ Direct scraper available
- **ICML**: ✅ Available through MLR scraper (PMLR)
- **ICLR**: ✅ Available through OpenReview scraper
- **CVPR**: ❌ No direct scraper (might be in OpenAlex/S2)
- **AAAI**: ❌ No direct scraper
- **IJCAI**: ❌ No direct scraper
- **ACL**: ❌ No direct scraper

## Shared Utilities

### Base Classes (`base.py`)
- `BaseScraper`: Common functionality for all scrapers
- `ProceedingsScraper`: Base for conference proceedings scrapers
- Database integration and query generation

### Helpers (`helpers.py`)
- Paper filtering by date range
- Author disambiguation
- Interactive prompts for validation

### Data Model (`model.py`)
- Complex object model: Paper, Author, Venue, Institution, etc.
- Database schema integration
- Quality scoring system

## Complexity Assessment

### Simple to Reuse (Low Effort):
1. **JMLR pattern** - Direct HTML/BibTeX scraping
2. **MLR pattern** - YAML metadata fetching
3. **NeurIPS pattern** - JSON/BibTeX with proceedings structure

### Complex but Powerful (High Value):
1. **OpenReview** - Covers many venues, good API
2. **Semantic Scholar** - Universal search, requires API key
3. **OpenAlex** - Alternative universal search

### Integration Challenges:
- Heavy database dependency (SQLAlchemy models)
- Complex data model with many relationships
- Quality scoring and deduplication logic
- Authentication/API key management

## Recommendations

### For Quick Implementation:
1. **Adapt the simple scrapers** (JMLR/MLR pattern) for missing venues
2. **Use Semantic Scholar API** directly for cross-venue search
3. **Focus on OpenReview** for ICLR and related conferences

### What to Avoid:
1. The full paperoni data model (too complex for our needs)
2. The database integration (unnecessary overhead)
3. The interactive validation flows

### What to Reuse:
1. URL fetching patterns with rate limiting
2. BibTeX/JSON parsing logic
3. Basic paper data extraction patterns
4. API integration patterns for S2 and OpenReview

### Missing Venues Strategy:
- **CVPR**: Usually has proceedings website, could adapt NeurIPS pattern
- **AAAI**: Has digital library, might need custom scraper
- **IJCAI**: Similar to AAAI
- **ACL**: Has ACL Anthology with good API

## Code Examples to Study:
1. `neurips.py` lines 29-84: Clean paper extraction
2. `mlr.py` lines 25-68: Simple YAML parsing
3. `semantic_scholar.py` lines 160-186: API field management
4. `openreview.py` lines 40-58: Venue parsing patterns