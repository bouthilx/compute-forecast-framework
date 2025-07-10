# IJCAI Paper Scraper Example

This example demonstrates how to use the IJCAI conference scraper to collect papers from IJCAI proceedings.

## Features

- Scrapes papers directly from IJCAI proceedings website
- Limits the number of papers collected (default: 10)
- Saves results to JSON format
- Includes proper error handling and logging
- Extracts paper metadata including:
  - Paper ID
  - Title
  - Authors
  - PDF URLs
  - Metadata completeness scores

## Usage

Basic usage (scrape 10 papers from IJCAI 2024):
```bash
uv run python scrape_ijcai_papers.py 2024
```

Scrape 20 papers from IJCAI 2023:
```bash
uv run python scrape_ijcai_papers.py 2023 --limit 20
```

Save to custom output file:
```bash
uv run python scrape_ijcai_papers.py 2022 --output my_ijcai_papers.json
```

## Output Format

The script generates a JSON file with the following structure:

```json
{
  "metadata": {
    "venue": "IJCAI",
    "year": 2024,
    "collection_date": "2025-01-08T...",
    "total_papers": 10,
    "scraper": "IJCAIScraper",
    "limit_applied": 10
  },
  "papers": [
    {
      "paper_id": "ijcai_2024_0001",
      "title": "Paper Title",
      "authors": ["Author One", "Author Two"],
      "venue": "IJCAI",
      "year": 2024,
      "pdf_urls": ["https://..."],
      "extraction_confidence": 0.9,
      "metadata_completeness": 0.8,
      ...
    }
  ]
}
```

## Notes

- The scraper respects rate limiting (1 second between requests)
- Includes retry logic for network errors
- Papers are limited to prevent excessive scraping
- The script validates that the year is between 2018 and the current year

## Requirements

- The `compute_forecast` package must be installed
- Internet connection to access IJCAI proceedings
