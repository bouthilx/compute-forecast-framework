#!/usr/bin/env python3
"""
Find and analyze venue name duplicates that should be merged.
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

def load_venue_data():
    """Load venue statistics data."""
    mila_stats_file = Path('data/mila_venue_statistics.json')
    with open(mila_stats_file, 'r') as f:
        mila_data = json.load(f)
    return mila_data.get('venue_counts', {})

def normalize_venue_name(venue):
    """Extract the core venue name by removing common variations."""
    if not venue:
        return ""
    
    # Convert to lowercase for analysis
    venue_lower = venue.lower().strip()
    
    # Remove year-specific patterns
    venue_clean = re.sub(r'\b(19|20)\d{2}\b', '', venue_lower)
    
    # Remove common conference URL patterns
    venue_clean = re.sub(r'\.cc/\d{4}/conference', '', venue_clean)
    venue_clean = re.sub(r'\.org/\d{4}', '', venue_clean)
    
    # Remove "proceedings of the" prefix
    venue_clean = re.sub(r'^proceedings of the\s+', '', venue_clean)
    
    # Remove ordinal numbers (40th, 41st, etc.)
    venue_clean = re.sub(r'\b\d+(st|nd|rd|th)\s+', '', venue_clean)
    
    # Remove "international conference on" and similar patterns
    venue_clean = re.sub(r'\binternational conference on\s+', '', venue_clean)
    venue_clean = re.sub(r'\bconference on\s+', '', venue_clean)
    venue_clean = re.sub(r'\bworkshop on\s+', '', venue_clean)
    
    # Remove extra whitespace
    venue_clean = ' '.join(venue_clean.split())
    
    return venue_clean

def find_potential_duplicates(venue_counts):
    """Find venues that are likely duplicates based on normalized names."""
    
    # Group venues by normalized names
    normalized_groups = defaultdict(list)
    
    for venue, data in venue_counts.items():
        normalized = normalize_venue_name(venue)
        if normalized:  # Skip empty normalized names
            normalized_groups[normalized].append((venue, data))
    
    # Find groups with multiple venues (potential duplicates)
    duplicates = {}
    for normalized, venues in normalized_groups.items():
        if len(venues) > 1:
            duplicates[normalized] = venues
    
    return duplicates

def analyze_known_patterns(venue_counts):
    """Analyze specific known patterns like NeurIPS, ICML, etc."""
    
    known_patterns = {
        'neurips': ['neurips', 'neural information processing systems'],
        'icml': ['icml', 'machine learning'],
        'iclr': ['iclr', 'learning representations'],
        'aaai': ['aaai', 'artificial intelligence'],
        'ijcai': ['ijcai'],
        'cvpr': ['cvpr', 'computer vision and pattern recognition'],
        'iccv': ['iccv', 'computer vision'],
        'eccv': ['eccv', 'european conference on computer vision'],
        'emnlp': ['emnlp', 'empirical methods'],
        'acl': ['acl', 'computational linguistics'],
        'naacl': ['naacl'],
        'icra': ['icra', 'robotics and automation'],
        'iros': ['iros', 'intelligent robots'],
        'rss': ['rss', 'robotics science and systems']
    }
    
    pattern_groups = defaultdict(list)
    
    for venue, data in venue_counts.items():
        venue_lower = venue.lower()
        
        for pattern_name, keywords in known_patterns.items():
            if any(keyword in venue_lower for keyword in keywords):
                pattern_groups[pattern_name].append((venue, data))
                break
    
    return pattern_groups

def create_venue_mapping(duplicates, pattern_groups):
    """Create a mapping from duplicate venues to canonical names."""
    
    venue_mapping = {}
    merged_venues = {}
    
    # Handle pattern-based groups (NeurIPS, ICML, etc.)
    for pattern_name, venues in pattern_groups.items():
        if len(venues) > 1:
            # Find the shortest/simplest name as canonical
            canonical_venue = min(venues, key=lambda x: (len(x[0]), x[0]))[0]
            
            # If there's a simple acronym, prefer that
            for venue, data in venues:
                if venue.upper() == pattern_name.upper():
                    canonical_venue = venue
                    break
            
            # Create merged data
            merged_data = {
                'total': 0,
                'by_year': defaultdict(int),
                'domains': set(),
                'paper_count': 0,
                'unique_paper_count': 0
            }
            
            original_venues = []
            for venue, data in venues:
                venue_mapping[venue] = canonical_venue
                original_venues.append(venue)
                
                # Merge the data
                merged_data['total'] += data.get('total', 0)
                merged_data['paper_count'] += data.get('paper_count', 0)
                merged_data['unique_paper_count'] += data.get('unique_paper_count', 0)
                
                # Merge by_year data
                for year, count in data.get('by_year', {}).items():
                    merged_data['by_year'][year] += count
                
                # Merge domains
                merged_data['domains'].update(data.get('domains', []))
            
            # Convert back to regular dict/list
            merged_data['by_year'] = dict(merged_data['by_year'])
            merged_data['domains'] = list(merged_data['domains'])
            
            merged_venues[canonical_venue] = {
                'merged_data': merged_data,
                'original_venues': original_venues,
                'pattern': pattern_name
            }
    
    # Handle other duplicates
    for normalized, venues in duplicates.items():
        if len(venues) > 1:
            # Skip if already handled by pattern matching
            already_handled = False
            for venue, data in venues:
                if venue in venue_mapping:
                    already_handled = True
                    break
            
            if not already_handled:
                # Find the shortest name as canonical
                canonical_venue = min(venues, key=lambda x: (len(x[0]), x[0]))[0]
                
                merged_data = {
                    'total': 0,
                    'by_year': defaultdict(int),
                    'domains': set(),
                    'paper_count': 0,
                    'unique_paper_count': 0
                }
                
                original_venues = []
                for venue, data in venues:
                    venue_mapping[venue] = canonical_venue
                    original_venues.append(venue)
                    
                    # Merge the data
                    merged_data['total'] += data.get('total', 0)
                    merged_data['paper_count'] += data.get('paper_count', 0)
                    merged_data['unique_paper_count'] += data.get('unique_paper_count', 0)
                    
                    # Merge by_year data
                    for year, count in data.get('by_year', {}).items():
                        merged_data['by_year'][year] += count
                    
                    # Merge domains
                    merged_data['domains'].update(data.get('domains', []))
                
                # Convert back to regular dict/list
                merged_data['by_year'] = dict(merged_data['by_year'])
                merged_data['domains'] = list(merged_data['domains'])
                
                merged_venues[canonical_venue] = {
                    'merged_data': merged_data,
                    'original_venues': original_venues,
                    'pattern': 'other'
                }
    
    return venue_mapping, merged_venues

def print_analysis(duplicates, pattern_groups, merged_venues):
    """Print detailed analysis of found duplicates."""
    
    print("=== VENUE DUPLICATE ANALYSIS ===\n")
    
    # Pattern-based duplicates
    print("=== KNOWN CONFERENCE PATTERNS ===")
    for pattern_name, venues in pattern_groups.items():
        if len(venues) > 1:
            print(f"\n{pattern_name.upper()} variants:")
            total_papers = 0
            for venue, data in venues:
                papers = data.get('total', 0)
                total_papers += papers
                years = sorted(data.get('by_year', {}).keys())
                year_range = f"{years[0]}-{years[-1]}" if len(years) > 1 else years[0] if years else "no years"
                print(f"  - {venue:50s} | {papers:3d} papers | {year_range}")
            print(f"  → Total combined: {total_papers} papers")
    
    # Other duplicates
    print(f"\n=== OTHER POTENTIAL DUPLICATES ===")
    other_duplicates = {k: v for k, v in duplicates.items() 
                       if not any(venue[0] in [v2[0] for venues in pattern_groups.values() for v2 in venues] 
                                 for venue in v)}
    
    for normalized, venues in other_duplicates.items():
        if len(venues) > 1:
            print(f"\nNormalized: '{normalized}'")
            total_papers = 0
            for venue, data in venues:
                papers = data.get('total', 0)
                total_papers += papers
                years = sorted(data.get('by_year', {}).keys())
                year_range = f"{years[0]}-{years[-1]}" if len(years) > 1 else years[0] if years else "no years"
                print(f"  - {venue:50s} | {papers:3d} papers | {year_range}")
            print(f"  → Total combined: {total_papers} papers")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total venue merges to apply: {len(merged_venues)}")
    
    total_original_venues = sum(len(info['original_venues']) for info in merged_venues.values())
    total_after_merge = len(merged_venues)
    
    print(f"Venues before merge: {total_original_venues}")
    print(f"Venues after merge: {total_after_merge}")
    print(f"Venues eliminated: {total_original_venues - total_after_merge}")

def main():
    """Main analysis function."""
    print("Loading venue data...")
    
    venue_counts = load_venue_data()
    print(f"Found {len(venue_counts)} unique venue names")
    
    # Find duplicates
    duplicates = find_potential_duplicates(venue_counts)
    pattern_groups = analyze_known_patterns(venue_counts)
    
    # Create mappings
    venue_mapping, merged_venues = create_venue_mapping(duplicates, pattern_groups)
    
    # Print analysis
    print_analysis(duplicates, pattern_groups, merged_venues)
    
    # Save the mapping for later use
    output_data = {
        'venue_mapping': venue_mapping,
        'merged_venues': {k: {
            'merged_data': v['merged_data'],
            'original_venues': v['original_venues'],
            'pattern': v['pattern']
        } for k, v in merged_venues.items()},
        'analysis_summary': {
            'total_original_venues': len(venue_counts),
            'total_duplicates_found': len(merged_venues),
            'venues_after_merge': len(venue_counts) - sum(len(info['original_venues']) - 1 for info in merged_venues.values())
        }
    }
    
    with open('venue_duplicate_mapping.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nVenue mapping saved to: venue_duplicate_mapping.json")

if __name__ == "__main__":
    main()