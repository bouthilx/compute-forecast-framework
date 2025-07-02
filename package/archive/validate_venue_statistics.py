#!/usr/bin/env python3
"""
Validation script for venue statistics output
"""

import json
from pathlib import Path
from collections import Counter

def validate_venue_statistics():
    """Validate the generated venue statistics"""
    
    # Load the generated data
    with open('data/mila_venue_statistics.json', 'r') as f:
        data = json.load(f)
    
    print("=== VENUE STATISTICS VALIDATION ===\n")
    
    # 1. Check required structure
    required_keys = ['venue_counts', 'venue_by_domain', 'venue_metadata', 'analysis_summary']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        print(f"❌ Missing required keys: {missing_keys}")
    else:
        print("✅ All required top-level keys present")
    
    # 2. Check analysis summary
    summary = data['analysis_summary']
    print(f"\n📊 Analysis Summary:")
    print(f"   Total venues: {summary['total_venues']}")
    print(f"   Total papers: {summary['total_papers']}")
    print(f"   Years covered: {summary['years_covered'][0]} - {summary['years_covered'][-1]}")
    print(f"   Active venues: {summary['active_venues']}")
    print(f"   Total domains: {summary['total_domains']}")
    
    # 3. Check venue normalization issues
    venue_names = list(data['venue_counts'].keys())
    
    # Find venues that should be normalized
    normalization_issues = []
    for venue in venue_names:
        if 'NeurIPS.cc' in venue:
            normalization_issues.append(venue)
        elif 'ICLR.cc' in venue:
            normalization_issues.append(venue)
        elif 'Proceedings of the' in venue and 'International Conference on Machine Learning' in venue:
            normalization_issues.append(venue)
    
    if normalization_issues:
        print(f"\n⚠️  Venue normalization issues found ({len(normalization_issues)} venues):")
        for venue in normalization_issues[:5]:  # Show first 5
            print(f"   - {venue}")
        if len(normalization_issues) > 5:
            print(f"   ... and {len(normalization_issues) - 5} more")
    else:
        print("\n✅ No obvious venue normalization issues")
    
    # 4. Top venues analysis
    venue_counts = data['venue_counts']
    top_venues = sorted(venue_counts.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    
    print(f"\n📈 Top 10 Venues by Paper Count:")
    for i, (venue, info) in enumerate(top_venues, 1):
        print(f"   {i:2d}. {venue:<40} ({info['total']:2d} papers)")
    
    # 5. Domain coverage
    domain_counts = {}
    for domain, venues in data['venue_by_domain'].items():
        domain_counts[domain] = sum(venues.values())
    
    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\n🏷️  Top 10 Domains by Paper Count:")
    for i, (domain, count) in enumerate(top_domains, 1):
        print(f"   {i:2d}. {domain:<50} ({count:3d} papers)")
    
    # 6. Temporal coverage
    all_years = set()
    for venue_info in venue_counts.values():
        all_years.update(venue_info['by_year'].keys())
    
    year_counts = {}
    for venue_info in venue_counts.values():
        for year, count in venue_info['by_year'].items():
            year_counts[year] = year_counts.get(year, 0) + count
    
    print(f"\n📅 Papers by Year:")
    for year in sorted(year_counts.keys()):
        print(f"   {year}: {year_counts[year]:4d} papers")
    
    # 7. Check computational scores coverage
    venues_with_scores = len(data['venue_metadata']['computational_scores'])
    print(f"\n🔬 Computational Scores Coverage:")
    print(f"   Venues with scores: {venues_with_scores}/{summary['total_venues']} ({venues_with_scores/summary['total_venues']*100:.1f}%)")
    
    # 8. Check citation averages coverage
    venues_with_citations = len(data['venue_metadata']['citation_averages'])
    print(f"\n📖 Citation Averages Coverage:")
    print(f"   Venues with citations: {venues_with_citations}/{summary['total_venues']} ({venues_with_citations/summary['total_venues']*100:.1f}%)")
    
    # 9. Venue type distribution
    venue_types = data['venue_metadata']['venue_types']
    type_counts = Counter(venue_types.values())
    print(f"\n📝 Venue Type Distribution:")
    for venue_type, count in type_counts.most_common():
        print(f"   {venue_type:<12}: {count:3d} venues")
    
    print(f"\n{'='*50}")
    print("VALIDATION COMPLETE")
    print(f"{'='*50}")
    
    return data

if __name__ == "__main__":
    validate_venue_statistics()