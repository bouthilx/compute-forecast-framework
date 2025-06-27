#!/usr/bin/env python3
"""
Test script to validate collection environment setup
"""

import json
import sys
import os
sys.path.insert(0, 'src')

from src.data.collectors.collection_executor import CollectionExecutor

def main():
    print("Testing collection environment setup...")
    
    executor = CollectionExecutor()
    
    # Test setup
    setup_success = executor.setup_collection_environment()
    
    if setup_success:
        print("✓ Collection environment setup successful!")
        
        # Test API connectivity
        api_status = executor.test_api_connectivity()
        print(f"API Status: {api_status}")
        
        # Test domain loading
        domains = executor.get_domains_from_analysis()
        print(f"Domains loaded: {len(domains)} domains")
        for domain in domains:
            print(f"  - {domain}")
        
        # Create setup status
        status = executor.create_setup_status(setup_success, api_status)
        
        # Save status
        os.makedirs('status', exist_ok=True)
        with open('status/worker6-setup.json', 'w') as f:
            json.dump(status, f, indent=2)
        
        print(f"\nSetup status saved to status/worker6-setup.json")
        print(f"Collection targets: {status['collection_targets']['total_papers_target']} papers")
        
    else:
        print("✗ Collection environment setup failed!")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)