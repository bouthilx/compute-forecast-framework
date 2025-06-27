#!/usr/bin/env python3
"""
Visualization script for primary venue paper counts from 2019-2024.

This script creates a line plot showing the number of papers per year for each
primary venue identified in the strategic venue collection.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import pandas as pd
from typing import Dict, List, Tuple


def normalize_venue_name(venue_name: str) -> str:
    """
    Normalize venue names to handle variations between datasets.
    
    Args:
        venue_name: Original venue name
        
    Returns:
        Normalized venue name for matching
    """
    # Common normalizations
    normalizations = {
        # ICML variations
        "Proceedings of the 41st International Conference on Machine Learning": "ICML",
        "Proceedings of the 40th International Conference on Machine Learning": "ICML", 
        "ICML.cc/2024/Conference": "ICML",
        
        # NeurIPS variations
        "NeurIPS.cc/2024/Conference": "NeurIPS",
        "NeurIPS.cc/2023/Conference": "NeurIPS",
        "Advances in Neural Information Processing Systems 35  (NeurIPS 2022)": "NeurIPS",
        
        # ICLR variations
        "ICLR.cc/2024/Conference": "ICLR",
        "ICLR.cc/2023/Conference": "ICLR",
        
        # AAAI variations
        "Proceedings of the AAAI Conference on Artificial Intelligence": "AAAI",
    }
    
    return normalizations.get(venue_name, venue_name)


def load_strategic_venues(filepath: Path) -> List[str]:
    """
    Load the list of primary venues from strategic venue collection.
    
    Args:
        filepath: Path to strategic venue collection JSON
        
    Returns:
        List of primary venue names
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    primary_venues = []
    for venue_info in data['primary_venues']:
        venue_name = venue_info['venue']
        normalized_name = normalize_venue_name(venue_name)
        primary_venues.append(normalized_name)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_venues = []
    for venue in primary_venues:
        if venue not in seen:
            seen.add(venue)
            unique_venues.append(venue)
    
    return unique_venues


def load_venue_statistics(filepath: Path) -> Dict:
    """
    Load Mila venue statistics data.
    
    Args:
        filepath: Path to venue statistics JSON
        
    Returns:
        Dictionary with venue statistics
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return data['venue_counts']


def extract_venue_data(primary_venues: List[str], venue_stats: Dict, 
                      years: List[int]) -> Dict[str, Dict[int, int]]:
    """
    Extract paper counts by year for primary venues.
    
    Args:
        primary_venues: List of primary venue names
        venue_stats: Venue statistics dictionary
        years: List of years to extract data for
        
    Returns:
        Dictionary mapping venue names to year-count dictionaries
    """
    venue_data = {}
    
    for venue in primary_venues:
        # Initialize with zeros for all years
        venue_data[venue] = {year: 0 for year in years}
        
        # Look for the venue in the statistics (exact match first)
        if venue in venue_stats:
            by_year = venue_stats[venue].get('by_year', {})
            for year_str, count in by_year.items():
                year = int(year_str)
                if year in years:
                    venue_data[venue][year] = count
        else:
            # Try to find variations or partial matches
            found = False
            for stat_venue, stats in venue_stats.items():
                normalized_stat_venue = normalize_venue_name(stat_venue)
                if normalized_stat_venue == venue:
                    by_year = stats.get('by_year', {})
                    for year_str, count in by_year.items():
                        year = int(year_str)
                        if year in years:
                            venue_data[venue][year] += count  # Add in case of multiple matches
                    found = True
            
            if not found:
                print(f"Warning: No data found for venue '{venue}'")
    
    return venue_data


def create_venue_visualization(venue_data: Dict[str, Dict[int, int]], 
                              years: List[int], output_path: Path):
    """
    Create line plot visualization of papers per venue by year.
    
    Args:
        venue_data: Dictionary mapping venues to year-count data
        years: List of years
        output_path: Path to save the plot
    """
    # Filter out venues with no data
    active_venues = {venue: data for venue, data in venue_data.items() 
                    if sum(data.values()) > 0}
    
    if not active_venues:
        print("Warning: No active venues found with data")
        return
    
    # Sort venues by total papers (descending)
    sorted_venues = sorted(active_venues.items(), 
                          key=lambda x: sum(x[1].values()), reverse=True)
    
    # Set up the plot
    plt.figure(figsize=(14, 10))
    
    # Color palette - use a colorblind-friendly palette
    colors = plt.cm.tab20(np.linspace(0, 1, len(sorted_venues)))
    
    # Plot each venue
    for i, (venue, data) in enumerate(sorted_venues):
        counts = [data[year] for year in years]
        total_papers = sum(counts)
        
        if total_papers > 0:  # Only plot venues with data
            plt.plot(years, counts, marker='o', linewidth=2.5, markersize=6,
                    color=colors[i], label=f'{venue} (total: {total_papers})')
    
    # Customize the plot
    plt.title('Mila Papers by Primary Venue (2019-2024)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Year', fontsize=14, fontweight='bold')
    plt.ylabel('Number of Papers', fontsize=14, fontweight='bold')
    
    # Set x-axis ticks
    plt.xticks(years, fontsize=12)
    plt.yticks(fontsize=12)
    
    # Add grid
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    
    # Adjust layout to prevent legend cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to: {output_path}")
    
    # Also show summary statistics
    print("\nSummary Statistics:")
    print("==================")
    for venue, data in sorted_venues:
        total = sum(data.values())
        if total > 0:
            avg_per_year = total / len([y for y in years if data[y] > 0])
            print(f"{venue:25} | Total: {total:3d} | Avg/Year: {avg_per_year:.1f}")


def create_top_venues_bar_chart(venue_data: Dict[str, Dict[int, int]], 
                               output_path: Path, top_n: int = 15):
    """
    Create bar chart of top N venues by total papers.
    
    Args:
        venue_data: Dictionary mapping venues to year-count data
        output_path: Path to save the plot
        top_n: Number of top venues to show
    """
    # Calculate total papers per venue
    venue_totals = {venue: sum(data.values()) for venue, data in venue_data.items()}
    
    # Filter out venues with no papers and sort by total
    active_venues = {venue: total for venue, total in venue_totals.items() if total > 0}
    sorted_venues = sorted(active_venues.items(), key=lambda x: x[1], reverse=True)
    
    # Take top N venues
    top_venues = sorted_venues[:top_n]
    
    if not top_venues:
        print("Warning: No venues found with data for bar chart")
        return
    
    # Create bar chart
    plt.figure(figsize=(12, 8))
    venues, counts = zip(*top_venues)
    
    bars = plt.bar(range(len(venues)), counts, color='steelblue', alpha=0.8)
    
    # Customize the plot
    plt.title(f'Top {top_n} Primary Venues by Total Mila Papers (2019-2024)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Venue', fontsize=14, fontweight='bold')
    plt.ylabel('Total Number of Papers', fontsize=14, fontweight='bold')
    
    # Set x-axis labels
    plt.xticks(range(len(venues)), venues, rotation=45, ha='right', fontsize=11)
    plt.yticks(fontsize=12)
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(count), ha='center', va='bottom', fontweight='bold')
    
    # Add grid
    plt.grid(True, axis='y', alpha=0.3, linestyle='--')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Bar chart saved to: {output_path}")


def main():
    """Main function to create venue visualizations."""
    
    # Define paths
    package_dir = Path(__file__).parent
    strategic_venues_path = package_dir / "data" / "strategic_venue_collection.json"
    venue_stats_path = package_dir / "data" / "mila_venue_statistics.json"
    
    # Output paths
    line_plot_path = package_dir / "primary_venues_timeline.png"
    bar_chart_path = package_dir / "primary_venues_totals.png"
    
    # Check if data files exist
    if not strategic_venues_path.exists():
        print(f"Error: Strategic venues file not found: {strategic_venues_path}")
        return
    
    if not venue_stats_path.exists():
        print(f"Error: Venue statistics file not found: {venue_stats_path}")
        return
    
    # Years to analyze
    years = list(range(2019, 2025))  # 2019-2024
    
    print("Loading strategic venues...")
    primary_venues = load_strategic_venues(strategic_venues_path)
    print(f"Found {len(primary_venues)} primary venues")
    
    print("Loading venue statistics...")
    venue_stats = load_venue_statistics(venue_stats_path)
    print(f"Loaded statistics for {len(venue_stats)} venues")
    
    print("Extracting venue data...")
    venue_data = extract_venue_data(primary_venues, venue_stats, years)
    
    print("Creating line plot visualization...")
    create_venue_visualization(venue_data, years, line_plot_path)
    
    print("Creating bar chart visualization...")
    create_top_venues_bar_chart(venue_data, bar_chart_path)
    
    print("\nVisualization complete!")


if __name__ == "__main__":
    main()