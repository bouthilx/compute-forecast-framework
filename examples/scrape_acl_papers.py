#!/usr/bin/env python3
"""
Example script for scraping papers from ACL Anthology

This script demonstrates how to use the ACLAnthologyScraper to collect
papers from a specific ACL conference year.

Usage:
    python scrape_acl_papers.py [year] [--limit N] [--display N]
    
Examples:
    python scrape_acl_papers.py 2023                    # Scrape all papers from 2023
    python scrape_acl_papers.py 2023 --limit 50         # Scrape only first 50 papers from 2023
    python scrape_acl_papers.py 2023 --limit 100 --display 10  # Scrape 100, display 10
    python scrape_acl_papers.py                         # Uses current year - 1, scrape all
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute_forecast.data.sources.scrapers.conference_scrapers.acl_anthology_scraper import (
    ACLAnthologyScraper
)
from compute_forecast.data.sources.scrapers import ScrapingConfig


def scrape_limited_papers(scraper, venue: str, year: int, max_papers: int):
    """
    Scrape papers with early stopping when limit is reached
    
    Args:
        scraper: ACL Anthology scraper instance
        venue: Venue name (e.g., "ACL")
        year: Year to scrape
        max_papers: Maximum number of papers to collect
        
    Returns:
        List of papers or None if failed
    """
    try:
        # Get the event URL and try to extract volume URLs
        event_url = scraper.get_proceedings_url(venue, year)
        event_response = scraper._make_request(event_url)
        volume_urls = scraper._extract_volume_urls(event_response.text, venue, year)
        
        collected_papers = []
        
        if volume_urls:
            # Scrape volumes one by one until we reach the limit
            for vol_name, vol_url in volume_urls.items():
                if len(collected_papers) >= max_papers:
                    break
                    
                try:
                    print(f"   📖 Scraping {vol_name} volume... ({len(collected_papers)}/{max_papers} papers)")
                    vol_papers = scraper._scrape_volume_page(vol_url, venue, year)
                    
                    # Add papers until we reach the limit
                    remaining = max_papers - len(collected_papers)
                    collected_papers.extend(vol_papers[:remaining])
                    
                    if len(collected_papers) >= max_papers:
                        print(f"   ✅ Reached limit of {max_papers} papers")
                        break
                        
                except Exception as e:
                    print(f"   ⚠️  Failed to scrape {vol_name}: {e}")
                    continue
        else:
            # Fallback: try direct volume URLs and stop when limit reached
            print(f"   📖 Trying direct volume URLs...")
            vol_papers = scraper._try_direct_volume_urls(venue, year)
            collected_papers = vol_papers[:max_papers]
            
        return collected_papers[:max_papers]  # Ensure we don't exceed limit
        
    except Exception as e:
        print(f"   ❌ Error during limited scraping: {e}")
        return None


def scrape_acl_papers(year: int, max_papers: int = None, display_limit: int = 10):
    """
    Scrape papers from ACL for a given year
    
    Args:
        year: The year to scrape papers from
        max_papers: Maximum number of papers to scrape (None for all)
        display_limit: Maximum number of papers to display in terminal (default: 10)
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
    if max_papers:
        print(f"\n📚 Scraping up to {max_papers} papers from ACL {year}...")
        papers = scrape_limited_papers(scraper, "ACL", year, max_papers)
        if papers is None:
            print("❌ Failed to scrape papers")
            return
        print(f"✅ Successfully scraped {len(papers)} papers from ACL {year}")
    else:
        print(f"\n📚 Scraping all papers from ACL {year}...")
        result = scraper.scrape_venue_year("ACL", year)
        
        if not result.success:
            print(f"❌ Failed to scrape papers: {result.errors}")
            return
        
        papers = result.metadata.get("papers", [])
        if not papers:
            print("⚠️  No papers found in results")
            return
        print(f"✅ Successfully scraped {len(papers)} papers from ACL {year}")
        
    print(f"\n📄 Showing first {min(display_limit, len(papers))} papers:\n")
    
    for i, paper in enumerate(papers[:display_limit], 1):
        print(f"{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        if len(paper.authors) > 3:
            print(f"            ... and {len(paper.authors) - 3} more")
        print(f"   Paper ID: {paper.paper_id}")
        print(f"   Source URL: {paper.source_url}")
        if paper.pdf_urls:
            print(f"   PDF URL: {paper.pdf_urls[0]}")
        else:
            print(f"   PDF URL: ❌ Not found")
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
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Scrape papers from ACL Anthology",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_acl_papers.py 2023                    # Scrape all papers from 2023
  python scrape_acl_papers.py 2023 --limit 50         # Scrape only first 50 papers
  python scrape_acl_papers.py 2023 --limit 100 --display 10  # Scrape 100, display 10
  python scrape_acl_papers.py                         # Use previous year, scrape all
        """
    )
    
    parser.add_argument(
        'year', 
        type=int, 
        nargs='?',
        default=datetime.now().year - 1,
        help='Year to scrape papers from (default: previous year)'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        metavar='N',
        help='Maximum number of papers to scrape (default: all papers)'
    )
    
    parser.add_argument(
        '--display', 
        type=int, 
        default=10,
        metavar='N',
        help='Maximum number of papers to display in terminal (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Validate year
    current_year = datetime.now().year
    if args.year < 1979 or args.year > current_year:
        print(f"❌ Invalid year: {args.year}. ACL started in 1979 and we're in {current_year}")
        sys.exit(1)
        
    # Validate limits
    if args.limit is not None and args.limit <= 0:
        print(f"❌ Invalid limit: {args.limit}. Must be positive.")
        sys.exit(1)
        
    if args.display <= 0:
        print(f"❌ Invalid display limit: {args.display}. Must be positive.")
        sys.exit(1)
    
    if args.year == datetime.now().year - 1:
        print(f"ℹ️  No year specified, using {args.year}")
    
    try:
        scrape_acl_papers(args.year, args.limit, args.display)
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()