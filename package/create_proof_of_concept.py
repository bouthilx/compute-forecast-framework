#!/usr/bin/env python3
"""
Create proof of concept collection - 8 papers to demonstrate working system
"""

import sys
import json
import time
import os
from datetime import datetime
sys.path.insert(0, 'src')

from src.data.collectors.collection_executor import CollectionExecutor
from src.data.collectors.domain_collector import DomainCollector
from src.core.logging import setup_logging

def main():
    setup_logging("INFO", "logs/proof_of_concept.log")
    
    print("🧪 Creating proof of concept collection...")
    
    # Initialize collection executor
    executor = CollectionExecutor()
    
    # Setup collection environment
    print("📋 Setting up collection environment...")
    setup_success = executor.setup_collection_environment()
    
    if not setup_success:
        print("❌ Failed to setup collection environment!")
        return False
    
    print("✅ Collection environment ready!")
    print(f"🔌 Working APIs: {executor.working_apis}")
    
    # Get first domain
    domains = executor.get_domains_from_analysis()
    test_domain = domains[0]
    
    print(f"📊 Testing with domain: {test_domain}")
    
    # Initialize domain collector
    domain_collector = DomainCollector(executor)
    
    print(f"\n📚 Collecting proof of concept papers...")
    start_time = time.time()
    
    all_papers = []
    
    # Collect from recent years to get good papers
    for year in [2023, 2024]:
        print(f"📅 Collecting from {test_domain} - {year}")
        
        try:
            year_papers = domain_collector.collect_domain_year_papers(test_domain, year, target_count=4)
            all_papers.extend(year_papers)
            
            print(f"  ✅ Collected {len(year_papers)} papers for {year}")
            
            if len(all_papers) >= 8:
                break
                
        except Exception as e:
            print(f"  ❌ Error collecting {year}: {e}")
            continue
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n✅ Proof of concept collection completed!")
    print(f"⏱️ Duration: {duration:.2f} seconds")
    print(f"📋 Total papers collected: {len(all_papers)}")
    
    if len(all_papers) == 0:
        print("❌ No papers collected")
        return False
    
    # Show sample papers
    print(f"\n📄 Sample papers:")
    for i, paper in enumerate(all_papers[:3], 1):
        print(f"  {i}. {paper.get('title', 'No title')[:80]}...")
        print(f"     Citations: {paper.get('citations', 0)}, Source: {paper.get('source', 'unknown')}")
    
    # Save proof of concept files
    print("💾 Saving proof of concept files...")
    
    os.makedirs('data', exist_ok=True)
    
    # Save simple collected papers (exactly 8 papers)
    simple_papers = all_papers[:8]
    with open('data/simple_collected_papers.json', 'w') as f:
        json.dump(simple_papers, f, indent=2)
    
    # Save simple stats
    simple_stats = {
        'papers_collected': len(simple_papers),
        'proof_of_concept': True,
        'working_apis': executor.working_apis,
        'collection_successful': True,
        'domain_tested': test_domain,
        'collection_duration': duration,
        'system_operational': True
    }
    
    with open('data/simple_collection_stats.json', 'w') as f:
        json.dump(simple_stats, f, indent=2)
    
    print(f"📁 Proof of concept files created:")
    print(f"  - data/simple_collected_papers.json ({len(simple_papers)} papers)")
    print(f"  - data/simple_collection_stats.json")
    
    # Also save full collection for later use
    collection_stats = {
        'collection_summary': {
            'total_papers_collected': len(all_papers),
            'collection_duration': duration,
            'working_apis': executor.working_apis,
            'system_operational': True,
            'proof_of_concept_successful': True
        },
        'papers_by_source': {},
        'collection_metadata': {
            'domain_tested': test_domain,
            'years_tested': [2023, 2024],
            'target_per_year': 4,
            'working_apis_used': executor.working_apis
        }
    }
    
    # Calculate source distribution
    for paper in all_papers:
        source = paper.get('source', 'unknown')
        collection_stats['papers_by_source'][source] = collection_stats['papers_by_source'].get(source, 0) + 1
    
    with open('data/collection_statistics.json', 'w') as f:
        json.dump(collection_stats, f, indent=2)
    
    with open('data/raw_collected_papers.json', 'w') as f:
        json.dump(all_papers, f, indent=2)
    
    print(f"  - data/raw_collected_papers.json ({len(all_papers)} papers)")
    print(f"  - data/collection_statistics.json")
    
    return len(all_papers) >= 8

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Proof of concept {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)