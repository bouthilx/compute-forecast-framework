#!/usr/bin/env python3
"""
Create stacked area charts showing paper progression over years.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict


def extract_year_data():
    """Extract papers by year with their classifications."""

    # Load all data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    print("Extracting temporal data...")

    # Create mapping from paper ID to year
    paper_to_year = {}
    papers_with_analysis = set()

    # Extract years and check for analysis
    import sys

    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    for paper_json in papers_data:
        paper_id = paper_json.get("paper_id", "")

        # Extract year
        year = None
        for release in paper_json.get("releases", []):
            venue = release.get("venue", {})
            venue_date = venue.get("date", {})
            if isinstance(venue_date, dict) and "text" in venue_date:
                try:
                    year = int(venue_date["text"][:4])
                    break
                except Exception:
                    continue

        if year and 2019 <= year <= 2024:
            paper_to_year[paper_id] = year

            # Check if has analysis
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    papers_with_analysis.add(paper_id)
            except Exception:
                pass

    print(f"Found {len(paper_to_year)} papers with valid years (2019-2024)")
    print(f"Found {len(papers_with_analysis)} papers with AI analysis")

    # Create domain mappings
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    # Get papers by research domain category
    papers_by_research_category = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            papers_by_research_category[category].add(paper_id)

    # Organize papers by year and category
    years = list(range(2019, 2025))
    categories = [
        "WITHOUT AI analysis",
        "NO domain classification",
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
        "Other research domains",
    ]

    year_data = {year: {cat: 0 for cat in categories} for year in years}

    # Classify each paper
    for paper_id, year in paper_to_year.items():
        if year not in years:
            continue

        # Check if has AI analysis
        if paper_id not in papers_with_analysis:
            year_data[year]["WITHOUT AI analysis"] += 1
            continue

        # Check if has domain classification
        has_domain = False
        assigned_category = None

        for category, papers in papers_by_research_category.items():
            if paper_id in papers:
                has_domain = True
                if category in [
                    "Computer Vision & Medical Imaging",
                    "Natural Language Processing",
                    "Reinforcement Learning & Robotics",
                    "Graph Learning & Network Analysis",
                ]:
                    assigned_category = category
                    break
                else:
                    assigned_category = "Other research domains"

        if not has_domain:
            year_data[year]["NO domain classification"] += 1
        else:
            year_data[year][assigned_category] += 1

    return years, categories, year_data


def create_stacked_area_charts():
    """Create both proportion and absolute count stacked area charts."""

    years, categories, year_data = extract_year_data()

    # Prepare data for plotting
    data_matrix = np.zeros((len(categories), len(years)))
    prop_matrix = np.zeros((len(categories), len(years)))

    for i, year in enumerate(years):
        total_year = sum(year_data[year].values())
        for j, category in enumerate(categories):
            count = year_data[year][category]
            data_matrix[j, i] = count
            prop_matrix[j, i] = count / total_year * 100 if total_year > 0 else 0

    # Print summary
    print("\nYearly paper counts:")
    for i, year in enumerate(years):
        total = sum(year_data[year].values())
        print(f"{year}: {total} papers")
        for category in categories:
            count = year_data[year][category]
            pct = count / total * 100 if total > 0 else 0
            print(f"  {category}: {count} ({pct:.1f}%)")
        print()

    # Create color scheme
    colors = [
        "#d62728",  # Red - WITHOUT AI analysis
        "#ff7f0e",  # Orange - NO domain classification
        "#2ca02c",  # Green - Computer Vision
        "#1f77b4",  # Blue - Natural Language Processing
        "#9467bd",  # Purple - Reinforcement Learning
        "#8c564b",  # Brown - Graph Learning
        "#e377c2",  # Pink - Other research domains
    ]

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Chart 1: Proportions
    ax1.stackplot(years, prop_matrix, labels=categories, colors=colors, alpha=0.8)
    ax1.set_title(
        "Paper Classification Proportions Over Time", fontsize=14, fontweight="bold"
    )
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Percentage of Papers (%)")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Add percentage labels for major categories
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(categories):
            pct = prop_matrix[j, i]
            if pct > 5:  # Only label if >5%
                y_pos += pct / 2
                ax1.text(
                    year,
                    y_pos,
                    f"{pct:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="white",
                )
                y_pos += pct / 2
            else:
                y_pos += pct

    # Chart 2: Absolute counts
    ax2.stackplot(years, data_matrix, labels=categories, colors=colors, alpha=0.8)
    ax2.set_title(
        "Paper Classification Counts Over Time", fontsize=14, fontweight="bold"
    )
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Number of Papers")
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Add count labels for major stacks
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(categories):
            count = data_matrix[j, i]
            if count > 20:  # Only label if >20 papers
                y_pos += count / 2
                ax2.text(
                    year,
                    y_pos,
                    f"{int(count)}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="white",
                )
                y_pos += count / 2
            else:
                y_pos += count

    plt.tight_layout()
    plt.savefig(
        "paper_classification_temporal_analysis.png", dpi=300, bbox_inches="tight"
    )
    plt.show()

    # Print trend analysis
    print("\nTREND ANALYSIS:")
    print("=" * 50)

    total_2019 = sum(year_data[2019].values())
    total_2024 = sum(year_data[2024].values())
    print(f"Overall growth: {total_2019} papers (2019) → {total_2024} papers (2024)")
    print(f"Growth rate: {(total_2024 / total_2019 - 1) * 100:+.1f}%")

    print("\nCategory trends (2019 → 2024):")
    for category in categories:
        count_2019 = year_data[2019][category]
        count_2024 = year_data[2024][category]
        pct_2019 = count_2019 / total_2019 * 100
        pct_2024 = count_2024 / total_2024 * 100

        if count_2019 > 0:
            growth = (count_2024 / count_2019 - 1) * 100
            print(f"  {category}:")
            print(f"    Count: {count_2019} → {count_2024} ({growth:+.1f}%)")
            print(
                f"    Proportion: {pct_2019:.1f}% → {pct_2024:.1f}% ({pct_2024 - pct_2019:+.1f}pp)"
            )
        else:
            print(f"  {category}: 0 → {count_2024} papers")

    return years, categories, year_data, data_matrix, prop_matrix


def create_research_domains_focus_chart():
    """Create a focused chart showing only research domain categories."""

    years, categories, year_data = extract_year_data()

    # Focus only on research domain categories
    research_categories = [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
        "Other research domains",
    ]

    # Create data matrix for research domains only
    research_data = np.zeros((len(research_categories), len(years)))
    research_props = np.zeros((len(research_categories), len(years)))

    for i, year in enumerate(years):
        # Calculate total research domain papers for this year
        total_research = sum(year_data[year][cat] for cat in research_categories)

        for j, category in enumerate(research_categories):
            count = year_data[year][category]
            research_data[j, i] = count
            research_props[j, i] = (
                count / total_research * 100 if total_research > 0 else 0
            )

    # Colors for research categories
    research_colors = [
        "#2ca02c",  # Green - Computer Vision
        "#1f77b4",  # Blue - Natural Language Processing
        "#9467bd",  # Purple - Reinforcement Learning
        "#8c564b",  # Brown - Graph Learning
        "#e377c2",  # Pink - Other research domains
    ]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Proportions within research domains
    ax1.stackplot(
        years,
        research_props,
        labels=research_categories,
        colors=research_colors,
        alpha=0.8,
    )
    ax1.set_title(
        "Research Domain Proportions Over Time\n(Excluding unclassified papers)",
        fontsize=14,
        fontweight="bold",
    )
    ax1.set_ylabel("Percentage of Research Papers (%)")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Absolute counts for research domains
    ax2.stackplot(
        years,
        research_data,
        labels=research_categories,
        colors=research_colors,
        alpha=0.8,
    )
    ax2.set_title("Research Domain Counts Over Time", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Number of Papers")
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.tight_layout()
    plt.savefig("research_domains_temporal_analysis.png", dpi=300, bbox_inches="tight")
    plt.show()

    # Research domain trends
    print("\nRESEARCH DOMAIN TRENDS:")
    print("=" * 40)

    for category in research_categories:
        count_2019 = year_data[2019][category]
        count_2024 = year_data[2024][category]

        if count_2019 > 0:
            growth = (count_2024 / count_2019 - 1) * 100
            print(f"{category}: {count_2019} → {count_2024} ({growth:+.1f}%)")
        else:
            print(f"{category}: 0 → {count_2024} papers")


def main():
    """Create all temporal analysis charts."""

    print("TEMPORAL STACKED AREA CHART ANALYSIS")
    print("=" * 50)

    # Create main charts
    years, categories, year_data, data_matrix, prop_matrix = (
        create_stacked_area_charts()
    )

    # Create focused research domains chart
    create_research_domains_focus_chart()

    # Save data for reference
    temporal_data = {
        "years": years,
        "categories": categories,
        "year_data": year_data,
        "data_matrix": data_matrix.tolist(),
        "prop_matrix": prop_matrix.tolist(),
    }

    with open("temporal_analysis_data.json", "w") as f:
        json.dump(temporal_data, f, indent=2)

    print("\nCharts saved as:")
    print("- paper_classification_temporal_analysis.png")
    print("- research_domains_temporal_analysis.png")
    print("- temporal_analysis_data.json")


if __name__ == "__main__":
    main()
