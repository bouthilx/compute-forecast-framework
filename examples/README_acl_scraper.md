# ACL Anthology Scraper Example

This example demonstrates how to use the `ACLAnthologyScraper` to collect papers from ACL conferences.

## Overview

The `scrape_acl_papers.py` script shows how to:
- Initialize the ACL Anthology scraper with proper configuration
- Check available years for a venue
- Scrape papers from a specific conference year
- Extract and display paper metadata
- Save results to a JSON file
- Generate statistics about the scraped data

## Usage

```bash
# Scrape papers from ACL 2023
python examples/scrape_acl_papers.py 2023

# Scrape papers from the previous year (default)
python examples/scrape_acl_papers.py
```

## Output

The script will:
1. Display the first 10 papers with their metadata
2. Save all scraped papers to `acl_YEAR_papers.json`
3. Show statistics about the collection

### Example Output

```
🔍 Initializing ACL Anthology scraper...
📅 Checking available years for ACL...

📚 Scraping ACL 2023 papers...
✅ Successfully scraped 684 papers from ACL 2023

📄 Showing first 10 papers:

1. Tweetorial: Detecting Hateful Memes Using Contrastive Learning
   Authors: Alice Chen, Bob Smith, Carol Jones
   Paper ID: acl_2023.acl-main.1
   PDF: https://aclanthology.org/2023.acl-main.1.pdf
   Metadata completeness: 100%

...

💾 Saving all 684 papers to acl_2023_papers.json...
✅ Results saved to acl_2023_papers.json

📊 Statistics:
   Total papers: 684
   Papers with PDF: 684 (100.0%)
   Average metadata completeness: 95%
   Papers with authors: 684 (100.0%)
```

## JSON Output Format

The generated JSON file contains:

```json
{
  "venue": "ACL",
  "year": 2023,
  "total_papers": 684,
  "scraped_at": "2024-01-15T10:30:45.123456",
  "papers": [
    {
      "title": "Paper Title",
      "authors": ["Author One", "Author Two"],
      "paper_id": "acl_2023.acl-main.1",
      "venue": "ACL",
      "year": 2023,
      "pdf_urls": ["https://aclanthology.org/2023.acl-main.1.pdf"],
      "source_url": "https://aclanthology.org/2023.acl-main.1/",
      "metadata_completeness": 1.0,
      "extraction_confidence": 0.95
    },
    ...
  ]
}
```

## Customization

You can modify the script to:
- Scrape different venues (EMNLP, NAACL, COLING, etc.)
- Adjust the rate limiting delay
- Filter papers by specific criteria
- Export to different formats (CSV, etc.)

## Supported Venues

The ACL Anthology scraper supports:
- ACL (Association for Computational Linguistics)
- EMNLP (Empirical Methods in Natural Language Processing)
- NAACL (North American Chapter of the ACL)
- COLING (International Conference on Computational Linguistics)
- EACL (European Chapter of the ACL)
- CoNLL (Conference on Computational Natural Language Learning)
- And many more...

## Rate Limiting

The script uses a 1-second delay between requests to be respectful to the ACL Anthology servers. Please maintain this delay to avoid overloading their infrastructure.

## Error Handling

The scraper includes:
- Retry logic for failed requests (up to 3 attempts)
- Graceful handling of missing data
- Fallback mechanisms for different page structures
- Clear error messages when scraping fails