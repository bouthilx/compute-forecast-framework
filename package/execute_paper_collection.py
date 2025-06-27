#!/usr/bin/env python3
"""
Main script to execute comprehensive paper collection across all research domains
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

def update_collection_status(status_data):
    """Update collection progress status"""
    os.makedirs('status', exist_ok=True)
    with open('status/worker6-collection.json', 'w') as f:
        json.dump(status_data, f, indent=2)

def update_overall_status(status_data):
    """Update overall worker status"""
    os.makedirs('status', exist_ok=True)
    with open('status/worker6-overall.json', 'w') as f:
        json.dump(status_data, f, indent=2)

def main():
    # Setup logging
    setup_logging("INFO", "logs/collection_execution.log")
    
    print("🚀 Starting comprehensive paper collection...")
    
    # Initialize collection executor
    executor = CollectionExecutor()
    
    # Setup collection environment
    print("📋 Setting up collection environment...")
    setup_success = executor.setup_collection_environment()
    
    if not setup_success:
        print("❌ Failed to setup collection environment!")
        return False
    
    print("✅ Collection environment ready!")
    
    # Get domains
    domains = executor.get_domains_from_analysis()
    print(f"📊 Target domains: {len(domains)}")
    for i, domain in enumerate(domains, 1):
        print(f"  {i}. {domain}")
    
    # Initialize domain collector
    domain_collector = DomainCollector(executor)
    
    # Execute collection
    print(f"\n📚 Starting paper collection (target: 8 papers per domain/year)...")
    start_time = time.time()
    
    # Update initial status
    initial_status = {
        "worker_id": "worker6",
        "last_update": datetime.now().isoformat(),
        "overall_status": "in_progress",
        "completion_percentage": 0,
        "current_task": "Starting paper collection",
        "estimated_completion": "Unknown",
        "blocking_issues": [],
        "collection_progress": {
            "domains_completed": 0,
            "domains_total": len(domains),
            "papers_collected": 0,
            "current_domain": domains[0] if domains else "None",
            "current_year": 2019
        },
        "ready_for_handoff": False,
        "outputs_available": []
    }
    update_overall_status(initial_status)
    
    try:
        # Execute the collection
        collection_results = domain_collector.execute_domain_collection(target_per_domain_year=8)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Collection completed in {duration:.2f} seconds!")
        print(f"📋 Total papers collected: {len(collection_results['raw_papers'])}")
        print(f"📊 Failed searches: {len(collection_results['failed_searches'])}")
        
        # Save results
        print("💾 Saving collection results...")
        
        os.makedirs('data', exist_ok=True)
        
        # Save raw collected papers
        with open('data/raw_collected_papers.json', 'w') as f:
            json.dump(collection_results['raw_papers'], f, indent=2)
        
        # Save collection statistics
        collection_stats = {
            'collection_summary': {
                'total_papers_collected': len(collection_results['raw_papers']),
                'domains_processed': len(collection_results['collection_stats']),
                'collection_duration': duration,
                'papers_per_second': len(collection_results['raw_papers']) / duration if duration > 0 else 0
            },
            'domain_distribution': dict(collection_results['collection_stats']),
            'source_distribution': dict(collection_results['source_distribution']),
            'failed_searches_count': len(collection_results['failed_searches']),
            'collection_metadata': {
                'start_time': datetime.now().isoformat(),
                'domains': domains,
                'target_per_domain_year': 8
            }
        }
        
        with open('data/collection_statistics.json', 'w') as f:
            json.dump(collection_stats, f, indent=2)
        
        # Save failed searches for debugging
        with open('data/failed_searches.json', 'w') as f:
            json.dump(collection_results['failed_searches'], f, indent=2)
        
        # Update final status
        final_status = {
            "worker_id": "worker6",
            "last_update": datetime.now().isoformat(),
            "overall_status": "completed",
            "completion_percentage": 100,
            "current_task": "Collection completed successfully",
            "estimated_completion": datetime.now().isoformat(),
            "blocking_issues": [],
            "collection_progress": {
                "domains_completed": len(domains),
                "domains_total": len(domains),
                "papers_collected": len(collection_results['raw_papers']),
                "current_domain": "All completed",
                "current_year": "All completed"
            },
            "ready_for_handoff": True,
            "outputs_available": [
                "data/raw_collected_papers.json",
                "data/collection_statistics.json",
                "data/failed_searches.json"
            ]
        }
        update_overall_status(final_status)
        
        print(f"✅ All results saved successfully!")
        print(f"📁 Output files:")
        print(f"  - data/raw_collected_papers.json ({len(collection_results['raw_papers'])} papers)")
        print(f"  - data/collection_statistics.json")
        print(f"  - data/failed_searches.json ({len(collection_results['failed_searches'])} failed searches)")
        
        return True
        
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        
        # Update error status
        error_status = {
            "worker_id": "worker6",
            "last_update": datetime.now().isoformat(),
            "overall_status": "failed",
            "completion_percentage": 0,
            "current_task": f"Collection failed: {str(e)}",
            "estimated_completion": "Failed",
            "blocking_issues": [str(e)],
            "collection_progress": {
                "domains_completed": 0,
                "domains_total": len(domains),
                "papers_collected": 0,
                "current_domain": "Failed",
                "current_year": "Failed"
            },
            "ready_for_handoff": False,
            "outputs_available": []
        }
        update_overall_status(error_status)
        
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)