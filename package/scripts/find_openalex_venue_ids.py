#!/usr/bin/env python3
"""
Find OpenAlex venue IDs for conferences and journals
"""

import requests
import json
from typing import Dict, List

def find_venue_id(venue_name: str, email: str = None) -> Dict:
    """Find OpenAlex venue ID by name"""
    url = "https://api.openalex.org/sources"  # Changed from /venues to /sources
    headers = {'User-Agent': 'venue-id-finder/1.0'}
    if email:
        headers['User-Agent'] += f' (mailto:{email})'
    
    params = {
        "search": venue_name,
        "per-page": 5
    }
    
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        results = []
        for venue in data.get('results', []):
            results.append({
                'id': venue.get('id', '').replace('https://openalex.org/', ''),
                'display_name': venue.get('display_name'),
                'type': venue.get('type'),
                'publisher': venue.get('publisher'),
                'works_count': venue.get('works_count', 0)
            })
        return {'query': venue_name, 'results': results}
    else:
        return {'query': venue_name, 'error': f"Status {response.status_code}"}

def main():
    # Top Mila publication venues from the analysis
    # Using more specific search terms to get correct venues
    venues_to_find = [
        # Core ML conferences (use full names for better matches)
        ("NeurIPS", "Neural Information Processing Systems"),
        ("ICML", "International Conference on Machine Learning"),
        ("ICLR", "International Conference on Learning Representations"),
        ("TMLR", "Transactions on Machine Learning Research"),
        
        # Computer Vision
        ("CVPR", "Computer Vision and Pattern Recognition"),
        ("ECCV", "European Conference on Computer Vision"),
        ("ICCV", "International Conference on Computer Vision"),
        
        # AI/ML conferences
        ("AAAI", "AAAI Conference on Artificial Intelligence"),
        
        # NLP conferences
        ("ACL", "Annual Meeting of the Association for Computational Linguistics"),
        ("EMNLP", "Conference on Empirical Methods in Natural Language Processing"),
        ("NAACL", "North American Chapter of the Association for Computational Linguistics"),
        
        # Journals
        ("Nature Communications", "Nature Communications"),
        ("JMLR", "Journal of Machine Learning Research"),
        ("Machine Learning", "Machine Learning journal"),
        
        # Additional venues from Mila analysis
        ("AISTATS", "Artificial Intelligence and Statistics"),
        ("UAI", "Uncertainty in Artificial Intelligence"),
        ("COLING", "International Conference on Computational Linguistics"),
    ]
    
    venue_ids = {}
    
    print("Finding OpenAlex venue IDs...\n")
    
    for short_name, search_term in venues_to_find:
        print(f"Searching for: {short_name} (query: '{search_term}')")
        result = find_venue_id(search_term)
        
        if 'error' in result:
            print(f"  Error: {result['error']}")
        elif result['results']:
            print(f"  Found {len(result['results'])} matches:")
            for i, match in enumerate(result['results'][:3]):  # Show top 3
                print(f"    {i+1}. {match['display_name']} ({match['type']})")
                print(f"       ID: {match['id']}")
                print(f"       Works: {match['works_count']:,}")
                if match['publisher']:
                    print(f"       Publisher: {match['publisher']}")
            
            # Store the top match
            if result['results']:
                venue_ids[short_name] = result['results'][0]
        else:
            print("  No results found")
        
        print()
    
    # Save results
    output_file = "data/openalex_venue_ids.json"
    with open(output_file, 'w') as f:
        json.dump(venue_ids, f, indent=2)
    
    print(f"\nVenue IDs saved to {output_file}")
    
    # Print summary of found IDs
    print("\nSummary of OpenAlex Venue IDs:")
    print("-" * 60)
    for venue, info in venue_ids.items():
        if isinstance(info, dict) and 'id' in info:
            print(f"{venue}: {info['id']}")

if __name__ == "__main__":
    main()