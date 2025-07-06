#!/usr/bin/env python3
"""
Create focused research domains chart using the fixed domain extraction data.
"""

import json
import matplotlib.pyplot as plt
import numpy as np


def create_research_domains_focus_chart_fixed():
    """Create a focused chart showing only research domain categories using fixed data."""

    # Load fixed temporal data
    with open("temporal_analysis_data_FIXED.json", "r") as f:
        temporal_data = json.load(f)

    years = temporal_data["years"]
    year_data = temporal_data["year_data"]

    print("CREATING RESEARCH DOMAINS FOCUS CHART (FIXED)")
    print("=" * 50)

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
        total_research = sum(year_data[str(year)][cat] for cat in research_categories)

        for j, category in enumerate(research_categories):
            count = year_data[str(year)][category]
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
        "Research Domain Proportions Over Time (FIXED)\n(Excluding unclassified papers)",
        fontsize=14,
        fontweight="bold",
    )
    ax1.set_ylabel("Percentage of Research Papers (%)")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Add percentage labels for major categories
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(research_categories):
            pct = research_props[j, i]
            if pct > 8:  # Only label if >8%
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

    # Absolute counts for research domains
    ax2.stackplot(
        years,
        research_data,
        labels=research_categories,
        colors=research_colors,
        alpha=0.8,
    )
    ax2.set_title(
        "Research Domain Counts Over Time (FIXED)", fontsize=14, fontweight="bold"
    )
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Number of Papers")
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Add count labels for major stacks
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(research_categories):
            count = research_data[j, i]
            if count > 15:  # Only label if >15 papers
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
        "research_domains_temporal_analysis_FIXED.png", dpi=300, bbox_inches="tight"
    )
    plt.show()

    # Research domain trends
    print("\nRESEARCH DOMAIN TRENDS (FIXED):")
    print("=" * 40)

    for i, year in enumerate(years):
        total_research = sum(year_data[str(year)][cat] for cat in research_categories)
        print(f"\n{year}: {total_research} research papers")
        for category in research_categories:
            count = year_data[str(year)][category]
            pct = count / total_research * 100 if total_research > 0 else 0
            print(f"  {category}: {count} ({pct:.1f}%)")

    print("\nGrowth trends (2019 → 2024):")
    for category in research_categories:
        count_2019 = year_data[str(2019)][category]
        count_2024 = year_data[str(2024)][category]

        if count_2019 > 0:
            growth = (count_2024 / count_2019 - 1) * 100
            print(f"{category}: {count_2019} → {count_2024} ({growth:+.1f}%)")
        else:
            print(f"{category}: 0 → {count_2024} papers")


def create_comparison_chart():
    """Create side-by-side comparison of original vs fixed data."""

    print("\nCREATING COMPARISON CHART")
    print("=" * 30)

    # Load original and fixed data
    try:
        with open("temporal_analysis_data.json", "r") as f:
            original_data = json.load(f)
    except:
        print("Original data not found, skipping comparison")
        return

    with open("temporal_analysis_data_FIXED.json", "r") as f:
        fixed_data = json.load(f)

    years = fixed_data["years"]
    research_categories = [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
        "Other research domains",
    ]

    # Calculate research papers only for each dataset
    original_research_counts = []
    fixed_research_counts = []

    for year in years:
        orig_count = sum(
            original_data["year_data"][str(year)][cat] for cat in research_categories
        )
        fixed_count = sum(
            fixed_data["year_data"][str(year)][cat] for cat in research_categories
        )
        original_research_counts.append(orig_count)
        fixed_research_counts.append(fixed_count)

    # Create comparison chart
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    width = 0.35
    x = np.arange(len(years))

    bars1 = ax.bar(
        x - width / 2,
        original_research_counts,
        width,
        label="Original (broken)",
        color="#ff7f7f",
        alpha=0.8,
    )
    bars2 = ax.bar(
        x + width / 2,
        fixed_research_counts,
        width,
        label="Fixed",
        color="#2ca02c",
        alpha=0.8,
    )

    ax.set_title(
        "Research Papers with Domain Classification\n(Original vs Fixed)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Papers")
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels on bars
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 1,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

    add_value_labels(bars1)
    add_value_labels(bars2)

    plt.tight_layout()
    plt.savefig(
        "research_papers_comparison_original_vs_fixed.png", dpi=300, bbox_inches="tight"
    )
    plt.show()

    # Print improvement summary
    total_original = sum(original_research_counts)
    total_fixed = sum(fixed_research_counts)
    improvement = total_fixed - total_original
    improvement_pct = improvement / total_original * 100 if total_original > 0 else 0

    print("\nIMPROVEMENT SUMMARY:")
    print(f"Original research papers: {total_original:,}")
    print(f"Fixed research papers: {total_fixed:,}")
    print(f"Improvement: +{improvement:,} papers ({improvement_pct:+.1f}%)")


def main():
    """Create all updated charts."""

    print("CREATING UPDATED STACKED AREA CHARTS")
    print("=" * 60)

    # Create research domains focus chart
    create_research_domains_focus_chart_fixed()

    # Create comparison chart
    create_comparison_chart()

    print("\nFiles generated:")
    print("- research_domains_temporal_analysis_FIXED.png")
    print("- research_papers_comparison_original_vs_fixed.png")


if __name__ == "__main__":
    main()
