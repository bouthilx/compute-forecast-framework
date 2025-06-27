#!/usr/bin/env python3
"""
Visualize primary venue paper trends from 2019-2024.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_venue_data():
    """Load strategic venue collection and mila venue statistics data."""
    
    # Load strategic venue collection (primary venues list)
    strategic_file = Path('data/strategic_venue_collection.json')
    with open(strategic_file, 'r') as f:
        strategic_data = json.load(f)
    
    # Load mila venue statistics (actual paper counts)
    mila_stats_file = Path('data/mila_venue_statistics.json')
    with open(mila_stats_file, 'r') as f:
        mila_data = json.load(f)
    
    return strategic_data, mila_data

def normalize_venue_mapping():
    """Create mapping for venue name normalization."""
    return {
        'Proceedings of the 41st International Conference on Machine Learning': 'ICML',
        'Proceedings of the 40th International Conference on Machine Learning': 'ICML', 
        'ICML.cc/2024/Conference': 'ICML',
        'NeurIPS.cc/2024/Conference': 'NeurIPS',
        'NeurIPS.cc/2023/Conference': 'NeurIPS', 
        'Advances in Neural Information Processing Systems 35  (NeurIPS 2022)': 'NeurIPS',
        'ICLR.cc/2024/Conference': 'ICLR',
        'ICLR.cc/2023/Conference': 'ICLR',
        'Proceedings of the AAAI Conference on Artificial Intelligence': 'AAAI'
    }

def get_venue_year_data(primary_venues, mila_data):
    """Extract year-wise paper counts for primary venues."""
    
    venue_mapping = normalize_venue_mapping()
    venue_counts = mila_data.get('venue_counts', {})
    years = ['2019', '2020', '2021', '2022', '2023', '2024']
    
    venue_trends = {}
    
    for venue_info in primary_venues[:15]:  # Top 15 primary venues
        venue_name = venue_info['venue']
        
        # Initialize year counts
        year_counts = {year: 0 for year in years}
        
        # Look for exact match first
        if venue_name in venue_counts:
            venue_data = venue_counts[venue_name]
            by_year = venue_data.get('by_year', {})
            for year in years:
                year_counts[year] = by_year.get(year, 0)
        
        # Try normalized mapping
        elif venue_name in venue_mapping:
            normalized_name = venue_mapping[venue_name]
            if normalized_name in venue_counts:
                venue_data = venue_counts[normalized_name]
                by_year = venue_data.get('by_year', {})
                for year in years:
                    year_counts[year] = by_year.get(year, 0)
        
        # Try partial matching for complex venue names
        else:
            # Find venues that contain key parts of the venue name
            key_parts = venue_name.lower().split()[:2]  # First two words
            
            for mila_venue, venue_data in venue_counts.items():
                mila_lower = mila_venue.lower()
                if any(part in mila_lower for part in key_parts if len(part) > 2):
                    by_year = venue_data.get('by_year', {})
                    for year in years:
                        year_counts[year] += by_year.get(year, 0)
                    break
        
        # Only include venues with some papers
        if sum(year_counts.values()) > 0:
            venue_trends[venue_name] = year_counts
    
    return venue_trends, years

def create_venue_trends_plot(venue_trends, years):
    """Create visualization of venue paper trends."""
    
    # Set up the plot
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Color palette
    colors = plt.cm.Set3(np.linspace(0, 1, len(venue_trends)))
    
    # Plot each venue
    for i, (venue, year_counts) in enumerate(venue_trends.items()):
        counts = [year_counts[year] for year in years]
        
        # Shorten venue names for display
        display_name = venue
        if len(venue) > 30:
            if 'ICML' in venue:
                display_name = 'ICML'
            elif 'NeurIPS' in venue:
                display_name = 'NeurIPS'
            elif 'ICLR' in venue:
                display_name = 'ICLR'
            elif 'AAAI' in venue:
                display_name = 'AAAI'
            else:
                display_name = venue[:30] + '...'
        
        ax.plot(years, counts, marker='o', linewidth=2.5, markersize=6, 
               label=display_name, color=colors[i], alpha=0.8)
    
    # Customize the plot
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Papers', fontsize=12, fontweight='bold')
    ax.set_title('Mila Paper Publications by Primary Venue (2019-2024)', 
                fontsize=14, fontweight='bold', pad=20)
    
    # Grid and styling
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_facecolor('#f8f9fa')
    
    # Legend
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    
    # Y-axis starts at 0
    ax.set_ylim(bottom=0)
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45 if len(years) > 6 else 0)
    
    plt.tight_layout()
    return fig

def create_venue_heatmap(venue_trends, years):
    """Create a heatmap showing venue activity over years."""
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Prepare data matrix
    venues = list(venue_trends.keys())
    data_matrix = []
    
    for venue in venues:
        year_counts = venue_trends[venue]
        counts = [year_counts[year] for year in years]
        data_matrix.append(counts)
    
    data_matrix = np.array(data_matrix)
    
    # Create heatmap
    im = ax.imshow(data_matrix, cmap='YlOrRd', aspect='auto')
    
    # Set ticks and labels
    ax.set_xticks(np.arange(len(years)))
    ax.set_yticks(np.arange(len(venues)))
    ax.set_xticklabels(years)
    
    # Shorten venue names for y-axis
    short_venues = []
    for venue in venues:
        if len(venue) > 30:
            if 'ICML' in venue:
                short_venues.append('ICML')
            elif 'NeurIPS' in venue:
                short_venues.append('NeurIPS')
            elif 'ICLR' in venue:
                short_venues.append('ICLR')
            elif 'AAAI' in venue:
                short_venues.append('AAAI')
            else:
                short_venues.append(venue[:20] + '...')
        else:
            short_venues.append(venue)
    
    ax.set_yticklabels(short_venues)
    
    # Rotate the tick labels and set their alignment
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Number of Papers', rotation=-90, va="bottom")
    
    # Add text annotations
    for i in range(len(venues)):
        for j in range(len(years)):
            text = ax.text(j, i, int(data_matrix[i, j]),
                         ha="center", va="center", color="black", fontsize=9)
    
    ax.set_title("Venue Publication Heatmap (2019-2024)", fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig

def main():
    """Main visualization function."""
    print("Loading venue data...")
    
    try:
        strategic_data, mila_data = load_venue_data()
        primary_venues = strategic_data['primary_venues']
        
        print(f"Found {len(primary_venues)} primary venues")
        
        # Get venue trend data
        venue_trends, years = get_venue_year_data(primary_venues, mila_data)
        
        print(f"Analyzing trends for {len(venue_trends)} venues with data")
        
        if venue_trends:
            # Create line plot
            print("Creating venue trends line plot...")
            fig1 = create_venue_trends_plot(venue_trends, years)
            fig1.savefig('venue_trends_line_plot.png', dpi=300, bbox_inches='tight')
            plt.close(fig1)
            
            # Create heatmap
            print("Creating venue trends heatmap...")
            fig2 = create_venue_heatmap(venue_trends, years)
            fig2.savefig('venue_trends_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close(fig2)
            
            print("Visualizations saved:")
            print("- venue_trends_line_plot.png")
            print("- venue_trends_heatmap.png")
            
            # Print summary statistics
            print("\n=== VENUE TRENDS SUMMARY ===")
            total_papers_by_year = defaultdict(int)
            
            for venue, year_counts in venue_trends.items():
                total_papers = sum(year_counts.values())
                print(f"{venue[:40]:40s} | Total: {total_papers:3d} papers")
                
                for year in years:
                    total_papers_by_year[year] += year_counts[year]
            
            print(f"\n=== YEARLY TOTALS ACROSS TOP VENUES ===")
            for year in years:
                print(f"{year}: {total_papers_by_year[year]:3d} papers")
            
        else:
            print("No venue trend data found!")
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the required data files exist:")
        print("- data/strategic_venue_collection.json")
        print("- data/mila_venue_statistics.json")

if __name__ == "__main__":
    main()