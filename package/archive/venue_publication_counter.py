#!/usr/bin/env python3
"""
Count Mila publications by venue and analyze venue distribution.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

def load_mila_domain_data():
    """Load the processed Mila domain data that includes venue information."""
    data_file = Path('all_domains_full.json')
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    with open(data_file, 'r') as f:
        return json.load(f)

def count_publications_by_venue(data):
    """Count publications by venue and analyze distribution."""
    venue_counts = Counter()
    venue_by_domain = defaultdict(lambda: defaultdict(int))
    venue_by_year = defaultdict(lambda: defaultdict(int))
    
    papers_with_venues = 0
    total_papers = len(data)
    
    # Process each domain entry (there can be multiple entries per paper)
    unique_papers = set()
    
    for entry in data:
        paper_id = entry.get('paper_id', '')
        venue = entry.get('venue', '').strip()
        domain = entry.get('domain_name', 'Unknown')
        year = entry.get('year')
        
        # Track unique papers
        unique_papers.add(paper_id)
        
        if venue and venue.lower() not in ['unknown', 'n/a', '']:
            # Count venue occurrences (each domain classification counts)
            venue_counts[venue] += 1
            venue_by_domain[venue][domain] += 1
            
            if year:
                venue_by_year[venue][str(year)] += 1
    
    # Count unique papers with venues
    paper_venues = defaultdict(set)
    for entry in data:
        paper_id = entry.get('paper_id', '')
        venue = entry.get('venue', '').strip()
        if venue and venue.lower() not in ['unknown', 'n/a', '']:
            paper_venues[paper_id].add(venue)
    
    papers_with_venues = len([pid for pid, venues in paper_venues.items() if venues])
    
    return {
        'venue_counts': venue_counts,
        'venue_by_domain': dict(venue_by_domain),
        'venue_by_year': dict(venue_by_year),
        'total_domain_entries': total_papers,
        'unique_papers': len(unique_papers),
        'papers_with_venues': papers_with_venues,
        'papers_without_venues': len(unique_papers) - papers_with_venues,
        'venue_coverage_rate': papers_with_venues / len(unique_papers) if unique_papers else 0
    }

def analyze_venue_patterns(venue_stats):
    """Analyze patterns in venue publication data."""
    venue_counts = venue_stats['venue_counts']
    venue_by_domain = venue_stats['venue_by_domain']
    
    print("=== MILA PUBLICATION VENUE ANALYSIS ===\n")
    
    # Overall statistics
    print(f"Total domain entries: {venue_stats['total_domain_entries']}")
    print(f"Unique papers: {venue_stats['unique_papers']}")
    print(f"Papers with venue info: {venue_stats['papers_with_venues']}")
    print(f"Papers without venue info: {venue_stats['papers_without_venues']}")
    print(f"Venue coverage rate: {venue_stats['venue_coverage_rate']:.1%}")
    print(f"Total unique venues: {len(venue_counts)}")
    print()
    
    # Top venues by publication count
    print("=== TOP 20 VENUES BY DOMAIN CLASSIFICATION COUNT ===")
    for i, (venue, count) in enumerate(venue_counts.most_common(20), 1):
        domains = venue_by_domain[venue]
        top_domain = max(domains.items(), key=lambda x: x[1])
        print(f"{i:2d}. {venue:40s} | {count:3d} entries | Top domain: {top_domain[0]} ({top_domain[1]})")
    print()
    
    # Venue distribution analysis
    total_venues = len(venue_counts)
    single_pub_venues = sum(1 for count in venue_counts.values() if count == 1)
    prolific_venues = sum(1 for count in venue_counts.values() if count >= 10)
    
    print("=== VENUE DISTRIBUTION ANALYSIS ===")
    print(f"Venues with single domain entry: {single_pub_venues} ({single_pub_venues/total_venues:.1%})")
    print(f"Venues with 2-4 entries: {sum(1 for c in venue_counts.values() if 2 <= c <= 4)}")
    print(f"Venues with 5-9 entries: {sum(1 for c in venue_counts.values() if 5 <= c <= 9)}")
    print(f"Venues with 10+ entries: {prolific_venues} ({prolific_venues/total_venues:.1%})")
    print()
    
    # Multi-domain venues
    multi_domain_venues = {venue: domains for venue, domains in venue_by_domain.items() 
                          if len(domains) > 1}
    
    print("=== TOP MULTI-DOMAIN VENUES ===")
    multi_domain_sorted = sorted(multi_domain_venues.items(), 
                                key=lambda x: len(x[1]), reverse=True)
    
    for venue, domains in multi_domain_sorted[:10]:
        total_count = sum(domains.values())
        domain_list = ", ".join(f"{d}({c})" for d, c in sorted(domains.items(), 
                                                                key=lambda x: x[1], reverse=True))
        print(f"{venue:40s} | {len(domains)} domains, {total_count} total | {domain_list}")
    print()
    
    return venue_stats

def analyze_venue_categories():
    """Categorize venues by type (conference, journal, etc.)."""
    venue_stats = count_publications_by_venue(load_mila_domain_data())
    venue_counts = venue_stats['venue_counts']
    
    # Simple venue categorization based on common patterns
    conferences = []
    journals = []
    workshops = []
    other = []
    
    conference_keywords = ['conference', 'conf', 'symposium', 'workshop', 'proceedings', 'international', 'acm', 'ieee']
    journal_keywords = ['journal', 'transactions', 'letters', 'review', 'quarterly', 'annual']
    
    for venue, count in venue_counts.items():
        venue_lower = venue.lower()
        
        if any(kw in venue_lower for kw in ['workshop', 'wksp']):
            workshops.append((venue, count))
        elif any(kw in venue_lower for kw in conference_keywords):
            conferences.append((venue, count))
        elif any(kw in venue_lower for kw in journal_keywords):
            journals.append((venue, count))
        else:
            other.append((venue, count))
    
    print("=== VENUE CATEGORIES ===")
    print(f"Conferences: {len(conferences)} venues, {sum(c for _, c in conferences)} entries")
    print(f"Journals: {len(journals)} venues, {sum(c for _, c in journals)} entries")
    print(f"Workshops: {len(workshops)} venues, {sum(c for _, c in workshops)} entries")
    print(f"Other/Unclear: {len(other)} venues, {sum(c for _, c in other)} entries")
    print()
    
    # Top venues by category
    print("=== TOP 10 CONFERENCES ===")
    for venue, count in sorted(conferences, key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {venue:50s} | {count:3d} entries")
    print()
    
    print("=== TOP 10 JOURNALS ===")
    for venue, count in sorted(journals, key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {venue:50s} | {count:3d} entries")
    print()
    
    return venue_stats

def main():
    """Main analysis function."""
    try:
        data = load_mila_domain_data()
        venue_stats = count_publications_by_venue(data)
        
        # Perform comprehensive venue analysis
        analyze_venue_patterns(venue_stats)
        analyze_venue_categories()
        
        # Save detailed results
        output_file = 'mila_venue_analysis.json'
        with open(output_file, 'w') as f:
            # Convert Counter objects to regular dicts for JSON serialization
            serializable_stats = {}
            for key, value in venue_stats.items():
                if isinstance(value, Counter):
                    serializable_stats[key] = dict(value)
                else:
                    serializable_stats[key] = value
            
            json.dump(serializable_stats, f, indent=2)
        
        print(f"Detailed venue analysis saved to: {output_file}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure you have the 'all_domains_full.json' file in the current directory.")
        print("This file should contain the processed Mila paper domain data with venue information.")

if __name__ == "__main__":
    main()