#!/usr/bin/env python3
"""Example of using the unified paper collection pipeline"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compute_forecast.data.collection.unified_pipeline import (
    CollectionRequest,
    create_global_collector,
)
from compute_forecast.data.sources.scrapers import ScrapingConfig


def main():
    """Demonstrate unified collection from multiple sources"""

    # Create collector with custom config
    config = ScrapingConfig(rate_limit_delay=1.0, max_retries=3, timeout=30)

    collector = create_global_collector(config)

    # List available sources
    print("📚 Available paper sources:")
    for source in collector.list_sources():
        print(f"  - {source}")

    # Example 1: Collect from all sources for specific venues/years
    print("\n🔍 Example 1: Collecting IJCAI 2023 from all sources...")
    request = CollectionRequest(venues=["IJCAI"], years=[2023], deduplicate=True)

    result = collector.collect(request)

    print(f"\n✅ Collected {len(result.papers)} unique papers")
    print("📊 Papers by source:")
    for source, count in result.papers_by_source.items():
        print(f"  - {source}: {count} papers")
    print(f"🔁 Duplicates removed: {result.duplicates_removed}")

    # Example 2: Collect from specific sources only
    print("\n🔍 Example 2: Collecting ACL 2024 from scrapers only...")
    request = CollectionRequest(
        venues=["ACL"],
        years=[2024],
        sources=["scraper_acl_anthology"],  # Only use ACL scraper
        max_papers_per_venue=50,  # Limit for demo
    )

    result = collector.collect(request)
    print(f"\n✅ Collected {len(result.papers)} papers from scrapers")

    # Example 3: Multi-venue, multi-year collection
    print("\n🔍 Example 3: Collecting multiple venues/years...")
    request = CollectionRequest(
        venues=["IJCAI", "ACL", "NeurIPS"], years=[2022, 2023], deduplicate=True
    )

    result = collector.collect(request)
    print(f"\n✅ Collected {len(result.papers)} total papers")
    print("📊 Distribution:")

    # Count by venue/year
    venue_year_counts = {}
    for paper in result.papers:
        key = f"{paper.venue} {paper.year}"
        venue_year_counts[key] = venue_year_counts.get(key, 0) + 1

    for key, count in sorted(venue_year_counts.items()):
        print(f"  - {key}: {count} papers")

    # Show some example papers
    print("\n📄 Sample papers collected:")
    for paper in result.papers[:5]:
        print(f"  - {paper.title}")
        print(f"    Authors: {', '.join(paper.authors[:3])}")
        print(f"    Source: {paper.source}")
        print()

    # Report any errors
    if result.errors:
        print("\n⚠️  Errors encountered:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
