#!/usr/bin/env python3
"""
Example script demonstrating how to scrape IJCAI papers using the conference scraper.

This script shows how to:
1. Use the IJCAIScraper to collect papers from IJCAI proceedings
2. Scrape papers from a specific year
3. Limit the number of papers collected
4. Handle scraping errors gracefully
5. Save collected papers to JSON for further analysis

Usage:
    uv run python scrape_ijcai_papers.py 2024
    uv run python scrape_ijcai_papers.py 2023 --limit 20
    uv run python scrape_ijcai_papers.py 2022 --output custom_output.json
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Import the IJCAI scraper
from compute_forecast.data.sources.scrapers.conference_scrapers import IJCAIScraper
from compute_forecast.data.sources.scrapers import ScrapingConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IJCAIPaperCollector:
    """Simple collector for IJCAI papers with limiting capability."""
    
    def __init__(self, year: int, limit: int = 10):
        """Initialize the IJCAI paper collector.
        
        Args:
            year: Year to scrape papers from
            limit: Maximum number of papers to collect (default: 10)
        """
        self.year = year
        self.limit = limit
        
        # Configure scraper with reasonable settings
        config = ScrapingConfig(
            rate_limit_delay=1.0,  # 1 second between requests
            max_retries=3,
            timeout=30
        )
        self.scraper = IJCAIScraper(config)
        
        logger.info(f"Initialized IJCAI scraper for year {year} with limit {limit}")
    
    def collect_papers(self) -> List[Dict[str, Any]]:
        """Collect papers from IJCAI proceedings.
        
        Returns:
            List of paper dictionaries with metadata
        """
        logger.info(f"Starting to scrape IJCAI {self.year} proceedings...")
        
        try:
            # Scrape the venue/year
            result = self.scraper.scrape_venue_year("IJCAI", self.year)
            
            if not result.success:
                logger.error(f"Scraping failed: {result.errors}")
                return []
            
            # Extract papers from result metadata
            all_papers = result.metadata.get("papers", [])
            logger.info(f"Found {len(all_papers)} total papers")
            
            # Limit the number of papers
            limited_papers = all_papers[:self.limit]
            logger.info(f"Limiting to {len(limited_papers)} papers")
            
            # Convert SimplePaper objects to dictionaries
            paper_dicts = []
            for paper in limited_papers:
                paper_dict = {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "venue": paper.venue,
                    "year": paper.year,
                    "pdf_urls": paper.pdf_urls,
                    "abstract": paper.abstract,
                    "doi": paper.doi,
                    "arxiv_id": paper.arxiv_id,
                    "source_scraper": paper.source_scraper,
                    "source_url": paper.source_url,
                    "scraped_at": paper.scraped_at.isoformat(),
                    "extraction_confidence": paper.extraction_confidence,
                    "metadata_completeness": paper.metadata_completeness
                }
                paper_dicts.append(paper_dict)
            
            return paper_dicts
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []
    
    def save_to_json(self, papers: List[Dict[str, Any]], output_file: str):
        """Save collected papers to JSON file.
        
        Args:
            papers: List of paper dictionaries
            output_file: Output filename
        """
        output_path = Path(output_file)
        
        # Create metadata for the collection
        collection_metadata = {
            "venue": "IJCAI",
            "year": self.year,
            "collection_date": datetime.now().isoformat(),
            "total_papers": len(papers),
            "scraper": "IJCAIScraper",
            "limit_applied": self.limit
        }
        
        # Combine metadata and papers
        output_data = {
            "metadata": collection_metadata,
            "papers": papers
        }
        
        # Save to JSON with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(papers)} papers to {output_path}")


def main():
    """Main function to run the IJCAI paper scraper."""
    parser = argparse.ArgumentParser(
        description="Scrape IJCAI papers for a specific year",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "year",
        type=int,
        help="Year to scrape IJCAI papers from (e.g., 2024)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of papers to collect (default: 10)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON filename (default: ijcai_YEAR_papers.json)"
    )
    
    args = parser.parse_args()
    
    # Validate year
    current_year = datetime.now().year
    if args.year < 2018 or args.year > current_year:
        logger.error(f"Year {args.year} is out of range. Please use a year between 2018 and {current_year}")
        sys.exit(1)
    
    # Set default output filename if not provided
    if not args.output:
        args.output = f"ijcai_{args.year}_papers.json"
    
    # Create collector and run
    collector = IJCAIPaperCollector(args.year, args.limit)
    
    # Collect papers
    papers = collector.collect_papers()
    
    if papers:
        # Save to JSON
        collector.save_to_json(papers, args.output)
        
        # Print summary
        print("\nCollection Summary:")
        print(f"- Venue: IJCAI {args.year}")
        print(f"- Papers collected: {len(papers)}")
        print(f"- Output file: {args.output}")
        
        # Show first few paper titles as preview
        print(f"\nFirst {min(3, len(papers))} papers:")
        for i, paper in enumerate(papers[:3], 1):
            print(f"{i}. {paper['title']}")
            if paper['authors']:
                print(f"   Authors: {', '.join(paper['authors'])}")
    else:
        logger.error("No papers were collected. Check the logs for errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()