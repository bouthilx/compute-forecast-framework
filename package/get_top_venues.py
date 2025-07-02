#!/usr/bin/env python3
"""Extract top venues from Mila papers using merged data."""

import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from visualize_venue_trends_merged import load_venue_data, apply_venue_merging, get_venue_year_data_merged

def get_top_mila_venues():
    """Get top venues by total paper count."""
    
    # Load data
    strategic_data, mila_data, mapping_data = load_venue_data()
    
    # Get merged venue counts
    merged_venue_counts = apply_venue_merging(mila_data['venue_counts'], mapping_data)
    
    # Get primary venues
    primary_venues = strategic_data['primary_venues']
    
    # Get venue trends
    venue_trends = get_venue_year_data_merged(primary_venues, merged_venue_counts)
    
    # Calculate total papers per venue
    venue_totals = []
    for venue, year_data in venue_trends.items():
        total = sum(year_data.values())
        venue_totals.append((venue, total, year_data))
    
    # Sort by total papers
    venue_totals.sort(key=lambda x: x[1], reverse=True)
    
    # Print top venues
    print("Top Mila Venues by Paper Count (2019-2024)")
    print("=" * 60)
    
    for i, (venue, total, year_data) in enumerate(venue_totals[:30]):
        print(f"{i+1:2d}. {venue:40s} {total:4d} papers")
        # Show year breakdown for top 10
        if i < 10:
            years = ['2019', '2020', '2021', '2022', '2023', '2024']
            year_str = " ".join([f"{y[-2:]}:{year_data.get(y, 0)}" for y in years])
            print(f"    {year_str}")
    
    # Also show raw venue counts for verification
    print("\n\nTop Raw Venues (not merged):")
    print("=" * 60)
    
    raw_venues = []
    for venue, data in mila_data['venue_counts'].items():
        total = data['total']
        raw_venues.append((venue, total))
    
    raw_venues.sort(key=lambda x: x[1], reverse=True)
    
    for i, (venue, total) in enumerate(raw_venues[:20]):
        print(f"{i+1:2d}. {venue:60s} {total:4d} papers")
    
    return venue_totals, raw_venues

if __name__ == "__main__":
    venue_totals, raw_venues = get_top_mila_venues()