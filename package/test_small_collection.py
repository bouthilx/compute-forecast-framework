#!/usr/bin/env python3
"""
Test script to validate collection with a small sample
"""

import sys
import json
sys.path.insert(0, 'src')

from src.data.collectors.collection_executor import CollectionExecutor
from src.data.collectors.domain_collector import DomainCollector

def test_single_domain_collection():
    print("Testing collection for single domain...")
    
    # Setup executor
    executor = CollectionExecutor()
    setup_success = executor.setup_collection_environment()
    
    if not setup_success:
        print("❌ Setup failed!")
        return False
    
    # Get first domain
    domains = executor.get_domains_from_analysis()
    test_domain = domains[0] if domains else "Computer Vision"
    
    print(f"Testing with domain: {test_domain}")
    
    # Initialize domain collector
    domain_collector = DomainCollector(executor)
    
    # Test collection for single domain, single year, small target
    print(f"Collecting papers for {test_domain} in 2023...")
    
    try:
        papers = domain_collector.collect_domain_year_papers(test_domain, 2023, 2)
        print(f"✅ Successfully collected {len(papers)} papers")
        
        if papers:
            print("Sample paper:")
            sample = papers[0]
            print(f"  Title: {sample.get('title', 'N/A')}")
            print(f"  Authors: {sample.get('authors', 'N/A')}")
            print(f"  Year: {sample.get('year', 'N/A')}")
            print(f"  Citations: {sample.get('citations', 'N/A')}")
            print(f"  Source: {sample.get('source', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_domain_collection()
    sys.exit(0 if success else 1)