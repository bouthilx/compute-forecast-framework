# Scraper Models Clarification

**Timestamp**: 2025-07-07
**Title**: Understanding SimplePaper vs ScrapedPaper Purpose

## Key Finding: ScrapedPaper Does Not Exist

After examining the codebase and related issues, I discovered:

1. **ScrapedPaper is NOT a real model** - it only appears in issue #144's specification
2. **SimplePaper is the actual implemented model** from issue #141
3. The issue author likely made an error when writing #144, using "ScrapedPaper" instead of "SimplePaper"

## Purpose of Each Model

### SimplePaper (Actually Implemented)
**Purpose**: Minimal intermediate representation for scraped papers

- **Design Goal**: Simple adapter between various scraper outputs and the package's Paper model
- **Key Features**:
  - Minimal fields that all scrapers can provide
  - Simple author representation (just names as strings)
  - Easy conversion to full Paper model
  - Source tracking for provenance
  
**Usage Flow**:
```
Website → Scraper → SimplePaper → to_package_paper() → Paper → Analysis
```

### ScrapedPaper (Mentioned in Issue #144 Only)
**Purpose**: Does not exist - appears to be a mistake

- The issue author likely meant to use SimplePaper
- The enhanced features mentioned (ScrapedAuthor, multiple PDFs, etc.) were NOT part of the approved design
- Issue #141 explicitly chose a simplified approach over complex models

## Architecture Context

From examining the milestone issues:

1. **Issue #140**: Defines base scraper classes (typo: BaseScaper instead of BaseScraper)
2. **Issue #141**: Defines SimplePaper as the adapter model
3. **Issue #144**: Incorrectly references "ScrapedPaper" which doesn't exist

## Recommendation

**Do NOT create ScrapedPaper or ScrapedAuthor models**. Instead:

1. Fix the typos in base classes (BaseScaper → BaseScraper)
2. Use SimplePaper as designed in issue #141
3. Adapt the IJCAI scraper implementation to use SimplePaper
4. If needed, enhance SimplePaper minimally (e.g., change pdf_url to pdf_urls)

This approach:
- Maintains consistency with the approved design
- Avoids creating redundant models
- Keeps the codebase simple
- Focuses on delivering the report rather than over-engineering