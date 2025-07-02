#!/usr/bin/env python3
"""
Execute full-scale paper collection for Worker 6
"""
import json
import time
from datetime import datetime
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data.collectors.collection_executor import CollectionExecutor

def main():
    print("=== Worker 6: Full-Scale Paper Collection ===")
    print(f"Starting at: {datetime.now()}")
    
    # Initialize collection executor
    print("\n1. Setting up collection environment...")
    executor = CollectionExecutor()
    
    try:
        setup_result = executor.setup_collection_environment()
        print(f"Setup result: {setup_result}")
    except Exception as e:
        print(f"Setup failed: {e}")
        return False
    
    # Update status - setup complete
    status = {
        'worker_id': 'worker6',
        'last_update': datetime.now().isoformat(),
        'overall_status': 'in_progress',
        'completion_percentage': 15,
        'current_task': 'Environment setup complete - starting collection',
        'collection_progress': {
            'domains_completed': 0,
            'domains_total': 5,
            'papers_collected': 0,
            'setup_complete': True
        },
        'ready_for_handoff': False,
        'outputs_available': []
    }
    
    with open('status/worker6-overall.json', 'w') as f:
        json.dump(status, f, indent=2)
    
    print("Setup complete! Starting full collection...")
    
    # Execute domain collection
    print("\n2. Executing domain-based collection...")
    try:
        collection_results = executor.execute_domain_collection(target_per_domain_year=8)
        
        total_papers = len(collection_results['raw_papers'])
        print(f"\nCollection completed! Total papers: {total_papers}")
        
        # Save results
        with open('data/raw_collected_papers.json', 'w') as f:
            json.dump(collection_results['raw_papers'], f, indent=2)
        
        with open('data/collection_statistics.json', 'w') as f:
            json.dump(collection_results['collection_stats'], f, indent=2)
        
        # Update final status
        final_status = {
            'worker_id': 'worker6',
            'last_update': datetime.now().isoformat(),
            'overall_status': 'completed',
            'completion_percentage': 100,
            'current_task': f'Collection complete - {total_papers} papers collected',
            'collection_progress': {
                'domains_completed': len(collection_results['collection_stats']),
                'domains_total': 5,
                'papers_collected': total_papers,
                'setup_complete': True
            },
            'ready_for_handoff': total_papers >= 800,
            'outputs_available': [
                'data/raw_collected_papers.json',
                'data/collection_statistics.json'
            ]
        }
        
        with open('status/worker6-overall.json', 'w') as f:
            json.dump(final_status, f, indent=2)
        
        print(f"\n=== Collection Summary ===")
        print(f"Total papers collected: {total_papers}")
        print(f"Domains covered: {len(collection_results['collection_stats'])}")
        print(f"Ready for Worker 7 handoff: {total_papers >= 800}")
        
        return True
        
    except Exception as e:
        print(f"Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Worker 6 collection completed successfully!")
    else:
        print("\n❌ Worker 6 collection failed!")