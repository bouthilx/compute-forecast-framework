#!/usr/bin/env python3
"""Extract top venues from Mila papers using properly merged data."""

import json
from pathlib import Path
from collections import defaultdict

def load_venue_data():
    """Load strategic venue collection, mila venue statistics, and duplicate mapping."""
    
    # Load strategic venue collection (primary venues list)
    strategic_file = Path('data/strategic_venue_collection.json')
    with open(strategic_file, 'r') as f:
        strategic_data = json.load(f)
    
    # Load mila venue statistics (actual paper counts)
    mila_stats_file = Path('data/mila_venue_statistics.json')
    with open(mila_stats_file, 'r') as f:
        mila_data = json.load(f)
    
    # Load venue duplicate mapping
    mapping_file = Path('venue_duplicate_mapping.json')
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    return strategic_data, mila_data, mapping_data

def apply_venue_merging(venue_counts, mapping_data):
    """Apply venue merging based on duplicate mapping."""
    
    venue_mapping = mapping_data['venue_mapping']
    merged_venues = mapping_data['merged_venues']
    
    # Create new venue counts with merged data
    new_venue_counts = {}
    
    # Add venues that are canonical (not duplicates)
    for venue, data in venue_counts.items():
        if venue not in venue_mapping:
            new_venue_counts[venue] = data
    
    # Add merged venues
    for canonical_venue, merge_info in merged_venues.items():
        new_venue_counts[canonical_venue] = merge_info['merged_data']
    
    return new_venue_counts

def get_venue_year_data_merged(primary_venues, merged_venue_counts):
    """Extract year-wise paper counts for primary venues using merged data."""
    
    years = ['2019', '2020', '2021', '2022', '2023', '2024']
    venue_trends = {}
    
    # Additional manual mappings for primary venues
    primary_mappings = {
        'NeurIPS.cc/2024/Conference': 'NeurIPS',
        'NeurIPS.cc/2023/Conference': 'NeurIPS', 
        'ICLR.cc/2024/Conference': 'ICLR',
        'ICLR.cc/2023/Conference': 'ICLR',
        'Proceedings of the 41st International Conference on Machine Learning': 'ICML',
        'Proceedings of the 40th International Conference on Machine Learning': 'ICML',
        'ICML.cc/2024/Conference': 'ICML',
        'Proceedings of the AAAI Conference on Artificial Intelligence': 'AAAI',
        'Advances in Neural Information Processing Systems 35  (NeurIPS 2022)': 'NeurIPS'
    }
    
    # Process each primary venue
    for venue_info in primary_venues[:50]:  # Get more venues
        venue_name = venue_info['venue']
        
        # Apply manual mapping first
        canonical_name = primary_mappings.get(venue_name, venue_name)
        
        # Initialize year counts
        year_counts = {year: 0 for year in years}
        found_data = False
        
        # Look for exact match in merged data
        if canonical_name in merged_venue_counts:
            venue_data = merged_venue_counts[canonical_name]
            by_year = venue_data.get('by_year', {})
            for year in years:
                year_counts[year] = by_year.get(year, 0)
            found_data = True
        
        # If not found, try original venue name
        elif venue_name in merged_venue_counts:
            venue_data = merged_venue_counts[venue_name]
            by_year = venue_data.get('by_year', {})
            for year in years:
                year_counts[year] = by_year.get(year, 0)
            found_data = True
        
        # Only include venues with some papers
        if found_data and sum(year_counts.values()) > 0:
            display_name = canonical_name if canonical_name != venue_name else venue_name
            # Truncate very long venue names
            if len(display_name) > 60:
                display_name = display_name[:57] + '...'
            venue_trends[display_name] = year_counts
    
    return venue_trends

def get_all_merged_venues():
    """Get all venues with their paper counts after merging."""
    
    # Load data
    strategic_data, mila_data, mapping_data = load_venue_data()
    
    # Get merged venue counts
    merged_venue_counts = apply_venue_merging(mila_data['venue_counts'], mapping_data)
    
    # Create list of all venues with totals
    all_venues = []
    for venue, data in merged_venue_counts.items():
        total = data.get('total', 0)
        by_year = data.get('by_year', {})
        all_venues.append({
            'venue': venue,
            'total': total,
            'by_year': by_year
        })
    
    # Sort by total papers
    all_venues.sort(key=lambda x: x['total'], reverse=True)
    
    return all_venues

def main():
    """Extract and display top venues."""
    
    # Get all merged venues
    print("Extracting merged venue data...")
    all_venues = get_all_merged_venues()
    
    # Print top venues
    print("\nTop Mila Venues (After Merging Duplicates)")
    print("=" * 80)
    print(f"{'Rank':>4} {'Venue':<50} {'Total':>8} {'2019':>6} {'2020':>6} {'2021':>6} {'2022':>6} {'2023':>6} {'2024':>6}")
    print("-" * 80)
    
    top_venues = []
    for i, venue_data in enumerate(all_venues[:40]):
        venue = venue_data['venue']
        total = venue_data['total']
        by_year = venue_data['by_year']
        
        # Truncate long venue names
        display_venue = venue if len(venue) <= 48 else venue[:45] + '...'
        
        print(f"{i+1:>4} {display_venue:<50} {total:>8}", end='')
        
        for year in ['2019', '2020', '2021', '2022', '2023', '2024']:
            count = by_year.get(year, 0)
            print(f" {count:>6}", end='')
        print()
        
        # Store top venues for PDF planning
        top_venues.append({
            'rank': i+1,
            'venue': venue,
            'total': total,
            'by_year': by_year
        })
    
    # Calculate totals
    total_papers = sum(v['total'] for v in all_venues)
    top_20_papers = sum(v['total'] for v in all_venues[:20])
    
    print(f"\nTotal papers across all venues: {total_papers}")
    print(f"Papers in top 20 venues: {top_20_papers} ({top_20_papers/total_papers*100:.1f}%)")
    
    # Save top venues for PDF acquisition planning
    output_file = Path('data/top_merged_venues.json')
    with open(output_file, 'w') as f:
        json.dump({
            'total_papers': total_papers,
            'top_venues': top_venues,
            'extraction_date': '2025-07-01'
        }, f, indent=2)
    
    print(f"\nTop venues saved to: {output_file}")
    
    # Group by venue type for PDF strategy
    print("\n\nVenue Categories for PDF Acquisition:")
    print("=" * 60)
    
    categories = {
        'conferences': [],
        'journals': [],
        'workshops': [],
        'arxiv': []
    }
    
    for venue_data in all_venues[:30]:
        venue = venue_data['venue']
        venue_lower = venue.lower()
        
        if 'arxiv' in venue_lower:
            categories['arxiv'].append(venue_data)
        elif any(conf in venue_lower for conf in ['neurips', 'icml', 'iclr', 'cvpr', 'aaai', 'emnlp', 'acl', 'conference', 'proceedings']):
            categories['conferences'].append(venue_data)
        elif any(journal in venue_lower for journal in ['journal', 'nature', 'science', 'ieee', 'trans.', 'review']):
            categories['journals'].append(venue_data)
        else:
            categories['workshops'].append(venue_data)
    
    for category, venues in categories.items():
        total = sum(v['total'] for v in venues)
        print(f"\n{category.upper()}: {len(venues)} venues, {total} papers")
        for v in venues[:5]:
            print(f"  - {v['venue'][:60]}: {v['total']} papers")

if __name__ == "__main__":
    main()