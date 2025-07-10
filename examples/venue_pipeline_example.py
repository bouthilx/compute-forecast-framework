#!/usr/bin/env python3
"""Example of using the venue-specific scraper pipeline"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compute_forecast.data.collection.venue_scraper_pipeline import (
    create_venue_pipeline,
    scrape_venue,
)
from compute_forecast.data.sources.scrapers import ScrapingConfig


def main():
    """Demonstrate venue-specific scraping with metadata enrichment"""

    # Create pipeline
    config = ScrapingConfig(rate_limit_delay=1.0, max_retries=3, timeout=30)

    pipeline = create_venue_pipeline(config)

    # Show available venues
    print("📚 Venues with dedicated scrapers:")
    for venue in pipeline.list_supported_venues():
        scraper = pipeline.get_scraper_for_venue(venue)
        print(f"  - {venue} → {scraper.__class__.__name__}")

    # Example 1: Scrape without enrichment (fast, scraper data only)
    print("\n🔍 Example 1: Scraping IJCAI 2023 (no enrichment)...")
    papers, result = pipeline.scrape_venue_year("IJCAI", 2023, enrich=False)

    if result.success:
        print(f"✅ Scraped {len(papers)} papers from IJCAI 2023")
        print("📄 Sample paper (scraper data only):")
        if papers:
            p = papers[0]
            print(f"  Title: {p.title}")
            print(f"  Authors: {', '.join(p.authors[:3])}")
            print(f"  PDF: {p.pdf_urls[0] if p.pdf_urls else 'None'}")
            print(f"  Has abstract: {'abstract' in p.__dict__ and bool(p.abstract)}")
            print(f"  Has DOI: {'doi' in p.__dict__ and bool(p.doi)}")

    # Example 2: Scrape with enrichment (slower, but more metadata)
    print("\n🔍 Example 2: Scraping ACL 2024 (with enrichment)...")
    papers, result = pipeline.scrape_venue_year("ACL", 2024, enrich=True)

    if result.success:
        print(f"✅ Scraped {len(papers)} papers from ACL 2024")
        print("📄 Sample paper (enriched with OpenAlex):")
        if papers:
            p = papers[0]
            print(f"  Title: {p.title}")
            print(f"  Authors: {', '.join(p.authors[:3])}")
            print(f"  PDF: {p.pdf_urls[0] if p.pdf_urls else 'None'}")
            print(f"  Has abstract: {hasattr(p, 'abstract') and bool(p.abstract)}")
            print(f"  Has DOI: {hasattr(p, 'doi') and bool(p.doi)}")
            print(f"  Citations: {getattr(p, 'citations_count', 'N/A')}")

    # Example 3: Try unsupported venue
    print("\n🔍 Example 3: Trying unsupported venue...")
    papers, result = pipeline.scrape_venue_year("ICML", 2023, enrich=False)

    if not result.success:
        print(f"❌ Expected failure: {result.errors[0]}")
        print(
            "💡 Supported venues:",
            ", ".join(pipeline.list_supported_venues()[:5]),
            "...",
        )

    # Example 4: Quick scraping function
    print("\n🔍 Example 4: Using quick scrape function...")
    try:
        papers = scrape_venue("EMNLP", 2023, enrich=False)
        print(f"✅ Quick scraped {len(papers)} papers from EMNLP 2023")
    except RuntimeError as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
