# NeurIPS URL Pattern Analysis

**Date**: 2025-01-22  
**Title**: Investigation of NeurIPS PDF URL Pattern Changes

## Summary

The user reported that NeurIPS papers from 2022+ have different PDF URLs than those from 2019-2021, and the current scraper was inferring URLs based on a frequent pattern rather than finding the actual PDF URLs. This investigation aimed to understand the URL pattern changes across years and propose a solution.

## Investigation Process

### 1. Located the Correct Scraper
- Initially examined the wrong scraper in `paperoni/src/paperoni/sources/scrapers/neurips.py`
- User corrected me to look at `compute_forecast/pipeline/metadata_collection/sources/scrapers/paperoni_adapters/neurips.py`

### 2. Analyzed Current Implementation
The current scraper uses a hardcoded pattern to construct PDF URLs:
```python
pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"
```

This assumes all papers follow the pattern: `{hash}-Paper.pdf`

### 3. Tested URL Patterns Across Years

Created test scripts to fetch actual PDF URLs from NeurIPS proceedings pages for years 2019-2024.

#### Key Findings:

**HTML URL Patterns:**
- 2019-2021: `/paper_files/paper/{year}/hash/{hash}-Abstract.html`
- 2022-2024: `/paper_files/paper/{year}/hash/{hash}-Abstract-Conference.html`

**PDF URL Patterns:**
- 2019-2020: Primary PDF is `-Paper.pdf`, but `-AuthorFeedback.pdf` appears first in some cases
- 2021: `-Paper.pdf` (matches current scraper)
- 2022-2024: `-Paper-Conference.pdf` (doesn't match current scraper)

**Available PDF Types by Year:**
- 2019-2020: Both `-AuthorFeedback.pdf` and `-Paper.pdf` available
  - Important: `-AuthorFeedback.pdf` contains reviews/feedback, NOT the main paper
  - The main paper is always `-Paper.pdf`
- 2021+: `-Paper.pdf` (or `-Paper-Conference.pdf`) and `-Supplemental.pdf` available
  - `-Supplemental.pdf` contains only supplementary materials, not the main paper

### 4. Pattern Summary

| Year | HTML Pattern | PDF Pattern | Scraper Works? |
|------|-------------|-------------|----------------|
| 2019 | -Abstract.html | -Paper.pdf | ✓ |
| 2020 | -Abstract.html | -Paper.pdf | ✓ |
| 2021 | -Abstract.html | -Paper.pdf | ✓ |
| 2022 | -Abstract-Conference.html | -Paper-Conference.pdf | ✗ |
| 2023 | -Abstract-Conference.html | -Paper-Conference.pdf | ✗ |
| 2024 | -Abstract-Conference.html | -Paper-Conference.pdf | ✗ |

### 5. HTML Structure Analysis

Analyzed the HTML structure of PDF links and found a consistent pattern:
- All PDF download links are styled as buttons with class `btn`
- The button text clearly identifies the PDF type:
  - "Paper" = Main paper PDF
  - "Supplemental" = Supplementary materials
  - "AuthorFeedback" = Review feedback (2019-2020 only)
- Button classes:
  - Main paper: `['btn', 'btn-primary', 'btn-spacer']` (2022+) or `['btn', 'btn-light', 'btn-spacer']` (2019-2021)
  - Others: `['btn', 'btn-light', 'btn-spacer']`

This provides a much safer and more reliable way to identify PDF links than searching all `<a>` tags.

## Root Cause

The scraper was written assuming a fixed pattern that worked for papers up to 2021. Starting in 2022, NeurIPS changed their URL structure to include "-Conference" in both HTML and PDF URLs, breaking the hardcoded pattern.

## Recommendation

Implement dynamic PDF discovery by fetching each paper's HTML page and extracting the actual PDF link. This approach is more robust and will handle future pattern changes automatically.

## Impact

- Papers from 2022-2024 are currently getting incorrect PDF URLs
- This affects approximately 11,000+ papers (2,834 in 2022 + 3,540 in 2023 + 4,494 in 2024)
- The scraper may fail to download PDFs or download the wrong content