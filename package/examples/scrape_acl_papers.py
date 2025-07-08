#!/usr/bin/env python3
"""
Example script for scraping papers from ACL Anthology

This script demonstrates how to use the ACLAnthologyScraper to collect
papers from a specific ACL conference year.

Usage:
    python scrape_acl_papers.py [year]
    
Example:
    python scrape_acl_papers.py 2023
    python scrape_acl_papers.py  # Uses current year - 1
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute_forecast.data.sources.scrapers.conference_scrapers.acl_anthology_scraper import (
    ACLAnthologyScraper
)
from compute_forecast.data.sources.scrapers import ScrapingConfig


def scrape_acl_papers(year: int, limit: int = 10):
    """
    Scrape papers from ACL for a given year
    
    Args:
        year: The year to scrape papers from
        limit: Maximum number of papers to display (default: 10)
    """
    print(f"🔍 Initializing ACL Anthology scraper...")
    
    # Configure scraper with reasonable rate limiting
    config = ScrapingConfig(
        rate_limit_delay=1.0,  # 1 second between requests
        max_retries=3,
        timeout=30
    )
    
    scraper = ACLAnthologyScraper(config)
    
    # Check if the year is available
    print(f"📅 Checking available years for ACL...")
    available_years = scraper.get_available_years("ACL")
    
    if available_years and year not in available_years:
        print(f"⚠️  Warning: Year {year} might not be available. Available years: {available_years[:5]}...")
    
    # Scrape papers
    print(f"\n📚 Scraping ACL {year} papers...")
    result = scraper.scrape_venue_year("ACL", year)
    
    if not result.success:
        print(f"❌ Failed to scrape papers: {result.errors}")
        return
    
    print(f"✅ Successfully scraped {result.papers_collected} papers from ACL {year}")
    
    # Display first N papers
    papers = result.metadata.get("papers", [])
    if not papers:
        print("⚠️  No papers found in results")
        return
        
    print(f"\n📄 Showing first {min(limit, len(papers))} papers:\n")
    
    for i, paper in enumerate(papers[:limit], 1):
        print(f"{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        if len(paper.authors) > 3:
            print(f"            ... and {len(paper.authors) - 3} more")
        print(f"   Paper ID: {paper.paper_id}")
        if paper.pdf_urls:
            print(f"   PDF: {paper.pdf_urls[0]}")
        print(f"   Metadata completeness: {paper.metadata_completeness:.0%}")
        print()
    
    # Save results to file
    output_file = f"acl_{year}_papers.json"
    print(f"💾 Saving all {len(papers)} papers to {output_file}...")
    
    # Convert papers to serializable format
    papers_data = []
    for paper in papers:
        papers_data.append({
            "title": paper.title,
            "authors": paper.authors,
            "paper_id": paper.paper_id,
            "venue": paper.venue,
            "year": paper.year,
            "pdf_urls": paper.pdf_urls,
            "source_url": paper.source_url,
            "metadata_completeness": paper.metadata_completeness,
            "extraction_confidence": paper.extraction_confidence
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "venue": "ACL",
            "year": year,
            "total_papers": len(papers_data),
            "scraped_at": datetime.now().isoformat(),
            "papers": papers_data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Results saved to {output_file}")
    
    # Show statistics
    print(f"\n📊 Statistics:")
    print(f"   Total papers: {len(papers)}")
    
    papers_with_pdf = sum(1 for p in papers if p.pdf_urls)
    print(f"   Papers with PDF: {papers_with_pdf} ({papers_with_pdf/len(papers)*100:.1f}%)")
    
    avg_completeness = sum(p.metadata_completeness for p in papers) / len(papers)
    print(f"   Average metadata completeness: {avg_completeness:.0%}")
    
    papers_with_authors = sum(1 for p in papers if p.authors)
    print(f"   Papers with authors: {papers_with_authors} ({papers_with_authors/len(papers)*100:.1f}%)")


def main():
    """Main entry point"""
    # Get year from command line or use default
    if len(sys.argv) > 1:
        try:
            year = int(sys.argv[1])
        except ValueError:
            print(f"❌ Invalid year: {sys.argv[1]}")
            print("Usage: python scrape_acl_papers.py [year]")
            sys.exit(1)
    else:
        # Default to last year
        year = datetime.now().year - 1
        print(f"ℹ️  No year specified, using {year}")
    
    # Validate year
    current_year = datetime.now().year
    if year < 1979 or year > current_year:
        print(f"❌ Invalid year: {year}. ACL started in 1979 and we're in {current_year}")
        sys.exit(1)
    
    try:
        scrape_acl_papers(year)
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()