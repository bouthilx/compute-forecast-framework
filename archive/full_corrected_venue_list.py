#!/usr/bin/env python3
"""
Generate a comprehensive list of all venues after corrected merging.
"""

import json
from pathlib import Path


def load_corrected_data():
    """Load the corrected venue merger data."""

    corrected_file = Path("corrected_venue_mergers.json")
    with open(corrected_file, "r") as f:
        corrected_data = json.load(f)

    return corrected_data


def print_full_corrected_venue_list(corrected_data):
    """Print complete venue list sorted by total papers."""

    merged_venues = corrected_data["merged_venues"]

    # Sort by total papers (descending)
    sorted_venues = sorted(
        merged_venues.items(), key=lambda x: x[1]["total_papers"], reverse=True
    )

    print("=" * 80)
    print("COMPLETE VENUE LIST AFTER CORRECTED MERGING")
    print("Ranked by Total Papers (Highest to Lowest)")
    print("=" * 80)

    rank = 1
    merged_count = 0
    standalone_count = 0

    for venue, info in sorted_venues:
        papers = info["total_papers"]
        is_merged = info["is_merged"]
        merged_from = info["merged_from"]
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

        if is_merged and len(merged_from) > 1:
            print(f"     🔗 Merged from {len(merged_from)} venues:")
            for i, constituent in enumerate(merged_from, 1):
                print(f"        {i:2d}. {constituent}")
            merged_count += 1
        else:
            standalone_count += 1

        rank += 1

    # Print summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")

    total_venues = len(sorted_venues)
    total_papers = sum(info["total_papers"] for _, info in sorted_venues)

    print(f"Total venues after corrected merging: {total_venues}")
    print(f"Merged venues: {merged_count}")
    print(f"Standalone venues: {standalone_count}")
    print(f"Total papers across all venues: {total_papers}")

    # Top venues stats
    top_10_papers = sum(info["total_papers"] for _, info in sorted_venues[:10])
    top_20_papers = sum(info["total_papers"] for _, info in sorted_venues[:20])
    top_50_papers = sum(info["total_papers"] for _, info in sorted_venues[:50])

    print(
        f"\nTop 10 venues represent: {top_10_papers} papers ({top_10_papers/total_papers:.1%})"
    )
    print(
        f"Top 20 venues represent: {top_20_papers} papers ({top_20_papers/total_papers:.1%})"
    )
    print(
        f"Top 50 venues represent: {top_50_papers} papers ({top_50_papers/total_papers:.1%})"
    )

    # Merged venue impact
    total_constituent_venues = sum(
        len(info["merged_from"]) for _, info in sorted_venues if info["is_merged"]
    )
    venues_eliminated = total_constituent_venues - merged_count

    print("\nCorrected merging impact:")
    print(f"Constituent venues in mergers: {total_constituent_venues}")
    print(f"Merged into: {merged_count} venues")
    print(f"Venues eliminated: {venues_eliminated}")

    # Top merged venues
    print(f"\n{'='*80}")
    print("TOP MERGED VENUES")
    print(f"{'='*80}")

    merged_venues_only = [
        (venue, info) for venue, info in sorted_venues if info["is_merged"]
    ]
    merged_venues_only.sort(key=lambda x: x[1]["total_papers"], reverse=True)

    for i, (venue, info) in enumerate(merged_venues_only[:10], 1):
        papers = info["total_papers"]
        constituent_count = len(info["merged_from"])
        print(
            f"{i:2d}. {venue:30s} | {papers:3d} papers from {constituent_count} variants"
        )

    # High-impact standalone venues
    print(f"\n{'='*80}")
    print("TOP STANDALONE VENUES (NOT MERGED)")
    print(f"{'='*80}")

    standalone_venues_only = [
        (venue, info) for venue, info in sorted_venues if not info["is_merged"]
    ]
    standalone_venues_only.sort(key=lambda x: x[1]["total_papers"], reverse=True)

    for i, (venue, info) in enumerate(standalone_venues_only[:20], 1):
        papers = info["total_papers"]
        print(f"{i:2d}. {venue:50s} | {papers:3d} papers")


def save_full_corrected_list(corrected_data):
    """Save the complete corrected venue list to JSON."""

    merged_venues = corrected_data["merged_venues"]

    # Sort by total papers for the saved file
    sorted_venues = sorted(
        merged_venues.items(), key=lambda x: x[1]["total_papers"], reverse=True
    )

    output_data = {
        "venues": [
            {
                "rank": i + 1,
                "venue_name": venue,
                "total_papers": info["total_papers"],
                "by_year": info["by_year"],
                "is_merged": info["is_merged"],
                "merged_from": info["merged_from"],
            }
            for i, (venue, info) in enumerate(sorted_venues)
        ],
        "summary": corrected_data["summary"],
        "corrected_mergers_applied": True,
    }

    with open("complete_corrected_venue_list.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print(
        "\nComplete corrected venue list saved to: complete_corrected_venue_list.json"
    )


def create_venue_mapping_for_worker6(corrected_data):
    """Create a venue mapping file for Worker 6 to use during collection."""

    corrected_mergers = corrected_data["corrected_mergers"]

    # Create a mapping from any variant name to canonical name
    venue_normalization_map = {}

    for canonical_venue, variants in corrected_mergers.items():
        for variant in variants:
            venue_normalization_map[variant] = canonical_venue

    # Add some common additional mappings that might appear during collection
    additional_mappings = {
        # ICML variants that might appear
        "Proceedings of the 42nd International Conference on Machine Learning": "ICML",
        "Proceedings of the 39th International Conference on Machine Learning": "ICML",
        "ICML.cc/2025/Conference": "ICML",
        # NeurIPS variants that might appear
        "NeurIPS.cc/2025/Conference": "NeurIPS",
        "Advances in Neural Information Processing Systems 37  (NeurIPS 2024)": "NeurIPS",
        # ICLR variants that might appear
        "ICLR.cc/2025/Conference": "ICLR",
        # Other common variants
        "EMNLP/2024/Conference": "EMNLP",
        "EMNLP/2025/Conference": "EMNLP",
        "auai.org/UAI/2025/Conference": "UAI",
        "2025 IEEE International Conference on Robotics and Automation (ICRA)": "ICRA",
        "2025 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)": "IROS",
        "ICASSP 2025 - 2025 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)": "ICASSP",
        "Interspeech 2025": "INTERSPEECH",
        "ICC 2025 - IEEE International Conference on Communications": "ICC",
    }

    venue_normalization_map.update(additional_mappings)

    worker6_mapping = {
        "venue_normalization_map": venue_normalization_map,
        "canonical_venues": list(corrected_mergers.keys()),
        "instructions": {
            "usage": "Use this mapping to normalize venue names during paper collection",
            "process": "For each collected paper, check if venue name exists in venue_normalization_map and replace with canonical name",
            "fallback": "If venue not found in map, use original venue name but log for potential future mapping",
        },
    }

    with open("worker6_venue_mapping.json", "w") as f:
        json.dump(worker6_mapping, f, indent=2)

    print("Worker 6 venue mapping saved to: worker6_venue_mapping.json")


def main():
    """Main function to generate complete corrected venue list."""
    print("Loading corrected venue merger data...")

    try:
        corrected_data = load_corrected_data()

        print(f"Total venues: {corrected_data['summary']['total_venues_after_merge']}")
        print(f"Legitimate mergers: {corrected_data['summary']['legitimate_mergers']}")

        # Print the complete list
        print_full_corrected_venue_list(corrected_data)

        # Save to files
        save_full_corrected_list(corrected_data)
        create_venue_mapping_for_worker6(corrected_data)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure corrected_venue_mergers.json exists")


if __name__ == "__main__":
    main()
