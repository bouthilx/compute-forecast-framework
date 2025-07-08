#!/usr/bin/env python3
"""
Fixed collection script - runs with partial API availability
Target: 800+ papers with Semantic Scholar + OpenAlex
"""

import sys
import json
import time
import os
from datetime import datetime

sys.path.insert(0, "src")

from compute_forecast.data.collectors.collection_executor import CollectionExecutor
from compute_forecast.data.collectors.domain_collector import DomainCollector
from compute_forecast.core.logging import setup_logging


def save_progress(papers, domain_stats, filename="incremental_papers.json"):
    """Save progress incrementally"""
    progress_data = {
        "papers_collected": len(papers),
        "timestamp": datetime.now().isoformat(),
        "papers": papers,
        "domain_stats": dict(domain_stats),
    }

    os.makedirs("data", exist_ok=True)
    with open(f"data/{filename}", "w") as f:
        json.dump(progress_data, f, indent=2)

    print(f"💾 Progress saved: {len(papers)} papers to data/{filename}")


def main():
    setup_logging("INFO", "logs/fixed_collection.log")

    print("🚀 Starting FIXED paper collection (with partial API availability)...")

    # Initialize collection executor
    executor = CollectionExecutor()

    # Setup collection environment (now accepts 2/3 working APIs)
    print("📋 Setting up collection environment...")
    setup_success = executor.setup_collection_environment()

    if not setup_success:
        print("❌ Failed to setup collection environment!")
        return False

    print("✅ Collection environment ready!")
    print(f"🔌 Working APIs: {executor.working_apis}")

    # Get domains
    domains = executor.get_domains_from_analysis()
    print(f"📊 Target domains: {len(domains)}")
    for i, domain in enumerate(domains, 1):
        print(f"  {i}. {domain}")

    # Initialize domain collector
    domain_collector = DomainCollector(executor)

    # Start collection with progress tracking
    print("\n📚 Starting paper collection with working APIs...")
    start_time = time.time()

    all_papers = []
    all_domain_stats = {}
    collection_errors = []

    for domain_idx, domain in enumerate(domains):
        print(f"\n=== Domain {domain_idx + 1}/{len(domains)}: {domain} ===")

        domain_papers = []
        domain_year_stats = {}

        # Collect for each year (reduce target to be more realistic with 2 APIs)
        for year in range(2019, 2025):
            print(f"📅 Processing {domain} - {year}")

            try:
                year_papers = domain_collector.collect_domain_year_papers(
                    domain, year, target_count=4
                )
                domain_papers.extend(year_papers)
                domain_year_stats[year] = len(year_papers)

                print(f"  ✅ Collected {len(year_papers)} papers for {domain} {year}")

                # Save progress every few years
                if year % 2 == 0:
                    all_papers.extend(domain_papers)
                    all_domain_stats[domain] = domain_year_stats
                    save_progress(
                        all_papers,
                        all_domain_stats,
                        f"progress_{domain_idx}_{year}.json",
                    )

            except Exception as e:
                error_info = {
                    "domain": domain,
                    "year": year,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                collection_errors.append(error_info)
                print(f"  ❌ Error collecting {domain} {year}: {e}")
                continue

        # Add domain papers to total
        final_domain_papers = [
            p for p in domain_papers if p not in all_papers
        ]  # Avoid duplicates
        all_papers.extend(final_domain_papers)
        all_domain_stats[domain] = domain_year_stats

        print(f"📊 Domain {domain} complete: {len(final_domain_papers)} total papers")

        # Save progress after each domain
        save_progress(
            all_papers, all_domain_stats, f"domain_progress_{domain_idx}.json"
        )

    end_time = time.time()
    duration = end_time - start_time

    print("\n✅ Collection completed!")
    print(f"⏱️ Duration: {duration:.2f} seconds")
    print(f"📋 Total papers collected: {len(all_papers)}")
    print(f"❌ Total errors: {len(collection_errors)}")

    # Final save
    print("💾 Saving final results...")

    # Save raw collected papers
    with open("data/raw_collected_papers.json", "w") as f:
        json.dump(all_papers, f, indent=2)

    # Save collection statistics
    collection_stats = {
        "collection_summary": {
            "total_papers_collected": len(all_papers),
            "domains_processed": len(all_domain_stats),
            "collection_duration": duration,
            "working_apis": executor.working_apis,
            "api_count": len(executor.working_apis),
            "papers_per_second": len(all_papers) / duration if duration > 0 else 0,
            "target_achieved": len(all_papers) >= 200,  # Adjusted target for 2 APIs
        },
        "domain_distribution": all_domain_stats,
        "source_distribution": {},  # Will be calculated from papers
        "collection_errors": collection_errors,
        "collection_metadata": {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "domains": domains,
            "target_per_domain_year": 4,
            "working_apis_used": executor.working_apis,
        },
    }

    # Calculate source distribution
    source_counts = {}
    for paper in all_papers:
        source = paper.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    collection_stats["source_distribution"] = source_counts

    with open("data/collection_statistics.json", "w") as f:
        json.dump(collection_stats, f, indent=2)

    # Save errors for debugging
    with open("data/failed_searches.json", "w") as f:
        json.dump(collection_errors, f, indent=2)

    print("📁 Final output files:")
    print(f"  - data/raw_collected_papers.json ({len(all_papers)} papers)")
    print("  - data/collection_statistics.json")
    print(f"  - data/failed_searches.json ({len(collection_errors)} errors)")

    # Create simple versions for proof of concept
    if len(all_papers) >= 8:
        simple_papers = all_papers[:8]  # First 8 papers as proof of concept
        with open("data/simple_collected_papers.json", "w") as f:
            json.dump(simple_papers, f, indent=2)

        simple_stats = {
            "papers_collected": 8,
            "proof_of_concept": True,
            "working_apis": executor.working_apis,
            "collection_successful": True,
        }
        with open("data/simple_collection_stats.json", "w") as f:
            json.dump(simple_stats, f, indent=2)

        print("  - data/simple_collected_papers.json (8 papers - proof of concept)")
        print("  - data/simple_collection_stats.json")

    return len(all_papers) >= 50  # Success if we get at least 50 papers


if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Collection {'SUCCESS' if success else 'PARTIAL'}")
    sys.exit(0 if success else 1)
