#!/usr/bin/env python3
"""
Generate a comprehensive list of all merged venues with their constituent venues.
"""

import json
from pathlib import Path


def load_venue_data():
    """Load venue statistics and duplicate mapping."""

    # Load mila venue statistics
    mila_stats_file = Path("data/mila_venue_statistics.json")
    with open(mila_stats_file, "r") as f:
        mila_data = json.load(f)

    # Load venue duplicate mapping
    mapping_file = Path("venue_duplicate_mapping.json")
    with open(mapping_file, "r") as f:
        mapping_data = json.load(f)

    return mila_data.get("venue_counts", {}), mapping_data


def create_full_merged_list(venue_counts, mapping_data):
    """Create a complete list of all venues after merging."""

    venue_mapping = mapping_data["venue_mapping"]
    merged_venues = mapping_data["merged_venues"]

    # Start with venues that were merged
    final_venues = {}

    # Add merged venues
    for canonical_venue, merge_info in merged_venues.items():
        final_venues[canonical_venue] = {
            "total_papers": merge_info["merged_data"]["total"],
            "by_year": merge_info["merged_data"]["by_year"],
            "constituent_venues": merge_info["original_venues"],
            "is_merged": True,
            "pattern": merge_info["pattern"],
        }

    # Add venues that were not merged (standalone venues)
    for venue, data in venue_counts.items():
        if venue not in venue_mapping:  # Not a duplicate
            final_venues[venue] = {
                "total_papers": data.get("total", 0),
                "by_year": data.get("by_year", {}),
                "constituent_venues": [venue],
                "is_merged": False,
                "pattern": "standalone",
            }

    return final_venues


def print_full_venue_list(final_venues):
    """Print complete venue list sorted by total papers."""

    # Sort by total papers (descending)
    sorted_venues = sorted(
        final_venues.items(), key=lambda x: x[1]["total_papers"], reverse=True
    )

    print("=" * 80)
    print("COMPLETE VENUE LIST AFTER MERGING")
    print("Ranked by Total Papers (Highest to Lowest)")
    print("=" * 80)

    rank = 1
    for venue, info in sorted_venues:
        papers = info["total_papers"]
        is_merged = info["is_merged"]
        constituent_venues = info["constituent_venues"]
        by_year = info["by_year"]

        # Get year range
        years = (
            sorted([int(y) for y in by_year.keys() if y.isdigit()]) if by_year else []
        )
        year_range = (
            f"{years[0]}-{years[-1]}"
            if len(years) > 1
            else str(years[0])
            if years
            else "no years"
        )

        # Print main venue info
        merge_indicator = "🔗" if is_merged else "📄"
        print(f"\n{rank:3d}. {merge_indicator} {venue}")
        print(f"     📊 Total Papers: {papers}")
        print(f"     📅 Years: {year_range}")

        if by_year:
            year_breakdown = ", ".join(
                [f"{y}:{c}" for y, c in sorted(by_year.items()) if c > 0]
            )
            print(f"     📈 By Year: {year_breakdown}")

        if is_merged and len(constituent_venues) > 1:
            print(f"     🔗 Merged from {len(constituent_venues)} venues:")
            for i, constituent in enumerate(constituent_venues, 1):
                print(f"        {i:2d}. {constituent}")

        rank += 1

    # Print summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")

    total_venues = len(sorted_venues)
    merged_venues = sum(1 for _, info in sorted_venues if info["is_merged"])
    standalone_venues = total_venues - merged_venues
    total_papers = sum(info["total_papers"] for _, info in sorted_venues)

    print(f"Total venues after merging: {total_venues}")
    print(f"Merged venues: {merged_venues}")
    print(f"Standalone venues: {standalone_venues}")
    print(f"Total papers across all venues: {total_papers}")

    # Top venues stats
    top_10_papers = sum(info["total_papers"] for _, info in sorted_venues[:10])
    top_20_papers = sum(info["total_papers"] for _, info in sorted_venues[:20])

    print(
        f"\nTop 10 venues represent: {top_10_papers} papers ({top_10_papers/total_papers:.1%})"
    )
    print(
        f"Top 20 venues represent: {top_20_papers} papers ({top_20_papers/total_papers:.1%})"
    )

    # Merged venue impact
    total_original_venues = sum(
        len(info["constituent_venues"])
        for _, info in sorted_venues
        if info["is_merged"]
    )
    venues_eliminated = total_original_venues - merged_venues

    print("\nMerging impact:")
    print(
        f"Original venues before merging: {total_original_venues + standalone_venues}"
    )
    print(f"Venues eliminated through merging: {venues_eliminated}")
    print(
        f"Reduction: {venues_eliminated/(total_original_venues + standalone_venues):.1%}"
    )


def save_venue_list(final_venues):
    """Save the complete venue list to JSON."""

    # Sort by total papers for the saved file
    sorted_venues = sorted(
        final_venues.items(), key=lambda x: x[1]["total_papers"], reverse=True
    )

    output_data = {
        "venues": [
            {
                "rank": i + 1,
                "venue_name": venue,
                "total_papers": info["total_papers"],
                "by_year": info["by_year"],
                "is_merged": info["is_merged"],
                "constituent_venues": info["constituent_venues"],
                "pattern": info["pattern"],
            }
            for i, (venue, info) in enumerate(sorted_venues)
        ],
        "summary": {
            "total_venues": len(sorted_venues),
            "merged_venues": sum(1 for _, info in sorted_venues if info["is_merged"]),
            "standalone_venues": sum(
                1 for _, info in sorted_venues if not info["is_merged"]
            ),
            "total_papers": sum(info["total_papers"] for _, info in sorted_venues),
        },
    }

    with open("complete_merged_venue_list.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print("\nComplete venue list saved to: complete_merged_venue_list.json")


def main():
    """Main function to generate complete venue list."""
    print("Loading venue data and merging information...")

    try:
        venue_counts, mapping_data = load_venue_data()

        print(f"Original venues: {len(venue_counts)}")
        print(f"Merging rules: {len(mapping_data['merged_venues'])}")

        # Create complete merged list
        final_venues = create_full_merged_list(venue_counts, mapping_data)

        # Print the complete list
        print_full_venue_list(final_venues)

        # Save to file
        save_venue_list(final_venues)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the required data files exist:")
        print("- data/mila_venue_statistics.json")
        print("- venue_duplicate_mapping.json")


if __name__ == "__main__":
    main()
