#!/usr/bin/env python3
"""
Visualize primary venue paper trends from 2019-2024 with merged duplicates.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict


def load_venue_data():
    """Load strategic venue collection, mila venue statistics, and duplicate mapping."""

    # Load strategic venue collection (primary venues list)
    strategic_file = Path("data/strategic_venue_collection.json")
    with open(strategic_file, "r") as f:
        strategic_data = json.load(f)

    # Load mila venue statistics (actual paper counts)
    mila_stats_file = Path("data/mila_venue_statistics.json")
    with open(mila_stats_file, "r") as f:
        mila_data = json.load(f)

    # Load venue duplicate mapping
    mapping_file = Path("venue_duplicate_mapping.json")
    with open(mapping_file, "r") as f:
        mapping_data = json.load(f)

    return strategic_data, mila_data, mapping_data


def apply_venue_merging(venue_counts, mapping_data):
    """Apply venue merging based on duplicate mapping."""

    venue_mapping = mapping_data["venue_mapping"]
    merged_venues = mapping_data["merged_venues"]

    # Create new venue counts with merged data
    new_venue_counts = {}

    # Add venues that are canonical (not duplicates)
    for venue, data in venue_counts.items():
        if venue not in venue_mapping:
            new_venue_counts[venue] = data

    # Add merged venues
    for canonical_venue, merge_info in merged_venues.items():
        new_venue_counts[canonical_venue] = merge_info["merged_data"]

    return new_venue_counts


def get_venue_year_data_merged(primary_venues, merged_venue_counts):
    """Extract year-wise paper counts for primary venues using merged data."""

    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    venue_trends = {}

    # Additional manual mappings for primary venues
    primary_mappings = {
        "NeurIPS.cc/2024/Conference": "NeurIPS",
        "NeurIPS.cc/2023/Conference": "NeurIPS",
        "ICLR.cc/2024/Conference": "ICLR",
        "ICLR.cc/2023/Conference": "ICLR",
        "Proceedings of the 41st International Conference on Machine Learning": "ICML",
        "Proceedings of the 40th International Conference on Machine Learning": "ICML",
        "ICML.cc/2024/Conference": "ICML",
        "Proceedings of the AAAI Conference on Artificial Intelligence": "AAAI",
        "Advances in Neural Information Processing Systems 35  (NeurIPS 2022)": "NeurIPS",
    }

    # Process each primary venue
    for venue_info in primary_venues[:20]:  # Top 20 primary venues
        venue_name = venue_info["venue"]

        # Apply manual mapping first
        canonical_name = primary_mappings.get(venue_name, venue_name)

        # Initialize year counts
        year_counts = {year: 0 for year in years}
        found_data = False

        # Look for exact match in merged data
        if canonical_name in merged_venue_counts:
            venue_data = merged_venue_counts[canonical_name]
            by_year = venue_data.get("by_year", {})
            for year in years:
                year_counts[year] = by_year.get(year, 0)
            found_data = True

        # If not found, try original venue name
        elif venue_name in merged_venue_counts:
            venue_data = merged_venue_counts[venue_name]
            by_year = venue_data.get("by_year", {})
            for year in years:
                year_counts[year] = by_year.get(year, 0)
            found_data = True

        # Only include venues with some papers
        if found_data and sum(year_counts.values()) > 0:
            display_name = (
                canonical_name if canonical_name != venue_name else venue_name
            )
            venue_trends[display_name] = year_counts

    return venue_trends, years


def create_merged_venue_trends_plot(venue_trends, years):
    """Create visualization of merged venue paper trends."""

    # Set up the plot
    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(14, 10))

    # Sort venues by total papers for better legend ordering
    sorted_venues = sorted(
        venue_trends.items(), key=lambda x: sum(x[1].values()), reverse=True
    )

    # Color palette
    colors = plt.cm.Set3(np.linspace(0, 1, len(sorted_venues)))

    # Plot each venue
    for i, (venue, year_counts) in enumerate(sorted_venues):
        counts = [year_counts[year] for year in years]

        ax.plot(
            years,
            counts,
            marker="o",
            linewidth=2.5,
            markersize=6,
            label=venue,
            color=colors[i],
            alpha=0.8,
        )

    # Customize the plot
    ax.set_xlabel("Year", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of Papers", fontsize=12, fontweight="bold")
    ax.set_title(
        "Mila Paper Publications by Primary Venue (2019-2024)\n[After Merging Duplicates]",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Grid and styling
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_facecolor("#f8f9fa")

    # Legend
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=10)

    # Y-axis starts at 0
    ax.set_ylim(bottom=0)

    # Rotate x-axis labels
    plt.xticks(rotation=45)

    plt.tight_layout()
    return fig


def create_merged_venue_heatmap(venue_trends, years):
    """Create a heatmap showing merged venue activity over years."""

    fig, ax = plt.subplots(figsize=(10, 12))

    # Sort venues by total papers
    sorted_venues = sorted(
        venue_trends.items(), key=lambda x: sum(x[1].values()), reverse=True
    )

    venues = [venue for venue, _ in sorted_venues]
    data_matrix = []

    for venue, year_counts in sorted_venues:
        counts = [year_counts[year] for year in years]
        data_matrix.append(counts)

    data_matrix = np.array(data_matrix)

    # Create heatmap
    im = ax.imshow(data_matrix, cmap="YlOrRd", aspect="auto")

    # Set ticks and labels
    ax.set_xticks(np.arange(len(years)))
    ax.set_yticks(np.arange(len(venues)))
    ax.set_xticklabels(years)
    ax.set_yticklabels(venues)

    # Rotate the tick labels and set their alignment
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Number of Papers", rotation=-90, va="bottom")

    # Add text annotations
    for i in range(len(venues)):
        for j in range(len(years)):
            text = ax.text(
                j,
                i,
                int(data_matrix[i, j]),
                ha="center",
                va="center",
                color="black",
                fontsize=9,
            )

    ax.set_title(
        "Venue Publication Heatmap (2019-2024)\n[After Merging Duplicates]",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    return fig


def print_merged_summary(venue_trends, years, mapping_data):
    """Print summary of merged venue data."""

    print("=== MERGED VENUE TRENDS SUMMARY ===")

    # Sort venues by total papers
    sorted_venues = sorted(
        venue_trends.items(), key=lambda x: sum(x[1].values()), reverse=True
    )

    total_papers_by_year = defaultdict(int)

    for venue, year_counts in sorted_venues:
        total_papers = sum(year_counts.values())
        print(f"{venue:30s} | Total: {total_papers:3d} papers")

        for year in years:
            total_papers_by_year[year] += year_counts[year]

    print("\n=== YEARLY TOTALS ACROSS TOP VENUES (MERGED) ===")
    for year in years:
        print(f"{year}: {total_papers_by_year[year]:3d} papers")

    print("\n=== MERGER IMPACT ===")
    print(f"Venues merged: {len(mapping_data['merged_venues'])}")
    print(
        f"Original venues eliminated: {mapping_data['analysis_summary']['venues_after_merge']}"
    )

    # Show major mergers
    print("\n=== MAJOR VENUE MERGERS ===")
    merged_venues = mapping_data["merged_venues"]
    major_mergers = [
        (k, v) for k, v in merged_venues.items() if v["merged_data"]["total"] > 10
    ]
    major_mergers.sort(key=lambda x: x[1]["merged_data"]["total"], reverse=True)

    for canonical, info in major_mergers[:10]:
        total_papers = info["merged_data"]["total"]
        original_count = len(info["original_venues"])
        print(
            f"{canonical:30s} | {total_papers:3d} papers from {original_count} venues"
        )


def main():
    """Main visualization function."""
    print("Loading venue data with duplicate mapping...")

    try:
        strategic_data, mila_data, mapping_data = load_venue_data()
        primary_venues = strategic_data["primary_venues"]

        print(f"Found {len(primary_venues)} primary venues")

        # Apply venue merging
        print("Applying venue merging...")
        original_venue_counts = mila_data.get("venue_counts", {})
        merged_venue_counts = apply_venue_merging(original_venue_counts, mapping_data)

        print(f"Venues before merge: {len(original_venue_counts)}")
        print(f"Venues after merge: {len(merged_venue_counts)}")

        # Get venue trend data with merging
        venue_trends, years = get_venue_year_data_merged(
            primary_venues, merged_venue_counts
        )

        print(f"Analyzing trends for {len(venue_trends)} venues with data")

        if venue_trends:
            # Print summary
            print_merged_summary(venue_trends, years, mapping_data)

            # Create line plot
            print("\nCreating merged venue trends line plot...")
            fig1 = create_merged_venue_trends_plot(venue_trends, years)
            fig1.savefig(
                "venue_trends_merged_line_plot.png", dpi=300, bbox_inches="tight"
            )
            plt.close(fig1)

            # Create heatmap
            print("Creating merged venue trends heatmap...")
            fig2 = create_merged_venue_heatmap(venue_trends, years)
            fig2.savefig(
                "venue_trends_merged_heatmap.png", dpi=300, bbox_inches="tight"
            )
            plt.close(fig2)

            print("\nMerged visualizations saved:")
            print("- venue_trends_merged_line_plot.png")
            print("- venue_trends_merged_heatmap.png")

        else:
            print("No venue trend data found!")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the required data files exist:")
        print("- data/strategic_venue_collection.json")
        print("- data/mila_venue_statistics.json")
        print("- venue_duplicate_mapping.json")


if __name__ == "__main__":
    main()
