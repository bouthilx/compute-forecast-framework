#!/usr/bin/env python3
"""
Test OpenAlex coverage by comparing with official conference paper lists
"""

import json
import requests
import time
from typing import List, Dict, Set
import re

def fetch_neurips_2024_official():
    """Fetch official NeurIPS 2024 paper list"""
    url = "https://neurips.cc/static/virtual/data/neurips-2024-orals-posters.json"
    print("Fetching official NeurIPS 2024 paper list...")
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} papers in official list")
        return data
    else:
        print(f"Error fetching NeurIPS data: {response.status_code}")
        return []

def get_openalex_paper_count(venue_id: str, year: int, email: str = None):
    """Get total paper count from OpenAlex for a venue and year"""
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'coverage-test/1.0'}
    if email:
        headers['User-Agent'] += f' (mailto:{email})'
    
    filter_str = f"primary_location.source.id:{venue_id},publication_year:{year}"
    
    print(f"\nGetting paper count from OpenAlex (venue: {venue_id}, year: {year})...")
    
    params = {
        'filter': filter_str,
        'per-page': 1  # We only need the count
    }
    
    response = requests.get(base_url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('meta', {}).get('count', 0)
        print(f"Total papers from OpenAlex: {count}")
        return count
    else:
        print(f"  Error: {response.status_code}")
        return 0

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    # Convert to lowercase
    title = title.lower()
    # Remove special characters and extra spaces
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def compare_coverage(official_count: int, openalex_count: int, conference: str):
    """Compare coverage between official count and OpenAlex count"""
    print("\n" + "="*60)
    print(f"COVERAGE ANALYSIS - {conference}")
    print("="*60)
    
    print(f"\nOfficial papers: {official_count}")
    print(f"OpenAlex papers: {openalex_count}")
    
    if official_count > 0:
        coverage_rate = (openalex_count / official_count) * 100
        print(f"Coverage rate: {coverage_rate:.1f}%")
    else:
        coverage_rate = 0
        print("Coverage rate: N/A (no official papers)")
    
    if openalex_count == 0:
        print("⚠️  WARNING: OpenAlex has 0 papers - venue ID might be incorrect")
    elif coverage_rate < 50:
        print("⚠️  WARNING: Low coverage - many papers may be missing")
    elif coverage_rate > 150:
        print("⚠️  WARNING: High coverage - may include duplicate years or wrong venue")
    else:
        print("✅ Coverage looks reasonable")
    
    return {
        'official_count': official_count,
        'openalex_count': openalex_count,
        'coverage_rate': coverage_rate
    }

def test_icml_coverage():
    """Test ICML coverage - would need official ICML paper list"""
    print("\n" + "="*60)
    print("ICML Coverage Test")
    print("="*60)
    print("Note: Would need official ICML paper list URL to test")
    print("ICML typically publishes proceedings at: https://proceedings.mlr.press/")
    
    # For now, just show what OpenAlex has
    with open('data/openalex_venue_ids.json', 'r') as f:
        venue_data = json.load(f)
    
    icml_id = venue_data['ICML']['id']
    
    for year in [2023, 2024]:
        count = get_openalex_paper_count(icml_id, year)
        print(f"\nICML {year}: {count} papers in OpenAlex")

def main():
    # Load venue IDs
    with open('data/openalex_venue_ids.json', 'r') as f:
        venue_data = json.load(f)
    
    neurips_id = venue_data['NeurIPS']['id']
    
    # Test NeurIPS 2024 coverage
    print("Testing NeurIPS 2024 coverage...")
    official_neurips = fetch_neurips_2024_official()
    openalex_count = get_openalex_paper_count(neurips_id, 2024)
    
    if official_neurips:
        coverage_stats = compare_coverage(len(official_neurips), openalex_count, "NeurIPS 2024")
        
        # Save results
        results = {
            'conference': 'NeurIPS 2024',
            'venue_id': neurips_id,
            'coverage_stats': coverage_stats,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open('data/openalex_coverage_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to data/openalex_coverage_test_results.json")
    
    # Also test ICML
    test_icml_coverage()

if __name__ == "__main__":
    main()