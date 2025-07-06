#!/usr/bin/env python3
"""
Implement dataset-based corrections to domain classification.
Use empirical work coverage (papers with datasets) as correction factors.
"""

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict


def analyze_empirical_vs_theoretical():
    """Analyze empirical vs theoretical research distribution by domain."""

    print("DATASET-BASED CORRECTION ANALYSIS")
    print("=" * 50)

    # Load papers data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    # Load domain data
    with open("all_domains_actual_fix.json", "r") as f:
        raw_domains = json.load(f)

    # Load taxonomy
    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    print(f"Loaded {len(papers_data)} papers and {len(raw_domains)} domain entries")

    # Add paperext to path
    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    # Create paper to year mapping and track empirical vs theoretical
    paper_to_year = {}
    papers_with_analysis = set()
    papers_with_datasets = set()
    paper_to_dataset_count = {}

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

            # Check if has analysis and datasets
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    papers_with_analysis.add(paper_id)

                    # Check for datasets in query data
                    dataset_count = 0
                    for query_file in paper.queries:
                        try:
                            with open(query_file, "r") as f:
                                query_data = json.load(f)

                            if "extractions" in query_data:
                                extractions = query_data["extractions"]
                                if "datasets" in extractions:
                                    datasets = extractions["datasets"]
                                    if isinstance(datasets, list) and len(datasets) > 0:
                                        # Count non-empty datasets
                                        for dataset in datasets:
                                            if isinstance(
                                                dataset, dict
                                            ) and dataset.get("name", {}).get("value"):
                                                dataset_count += 1
                            break
                        except Exception:
                            continue

                    paper_to_dataset_count[paper_id] = dataset_count
                    if dataset_count > 0:
                        papers_with_datasets.add(paper_id)
            except Exception:
                pass

    # Create domain mappings (same as before)
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    # Add automatic categorization
    cv_keywords = [
        "computer vision",
        "vision",
        "image",
        "visual",
        "medical imaging",
        "segmentation",
        "object detection",
    ]
    nlp_keywords = [
        "natural language",
        "nlp",
        "language",
        "text",
        "linguistic",
        "dialogue",
        "conversational",
    ]
    rl_keywords = [
        "reinforcement learning",
        "rl",
        "robotics",
        "agent",
        "policy",
        "control",
    ]
    graph_keywords = ["graph", "network", "node", "edge", "social network"]

    for domain_entry in raw_domains:
        domain_name = domain_entry["domain_name"]
        if domain_name not in domain_to_category:
            domain_lower = domain_name.lower()

            if any(kw in domain_lower for kw in cv_keywords):
                domain_to_category[domain_name] = "Computer Vision & Medical Imaging"
            elif any(kw in domain_lower for kw in nlp_keywords):
                domain_to_category[domain_name] = "Natural Language Processing"
            elif any(kw in domain_lower for kw in rl_keywords):
                domain_to_category[domain_name] = "Reinforcement Learning & Robotics"
            elif any(kw in domain_lower for kw in graph_keywords):
                domain_to_category[domain_name] = "Graph Learning & Network Analysis"
            else:
                domain_to_category[domain_name] = "Other research domains"

    # Define categories
    main_research_categories = [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
    ]

    all_research_categories = main_research_categories + ["Other research domains"]

    # Get papers by domain category
    paper_to_main_categories = defaultdict(set)
    paper_to_other_categories = defaultdict(set)

    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            if category in main_research_categories:
                paper_to_main_categories[paper_id].add(category)
            else:
                paper_to_other_categories[paper_id].add(category)

    return {
        "papers_with_analysis": papers_with_analysis,
        "papers_with_datasets": papers_with_datasets,
        "paper_to_dataset_count": paper_to_dataset_count,
        "paper_to_year": paper_to_year,
        "paper_to_main_categories": paper_to_main_categories,
        "paper_to_other_categories": paper_to_other_categories,
        "main_research_categories": main_research_categories,
        "all_research_categories": all_research_categories,
    }


def calculate_empirical_coverage_by_domain(data):
    """Calculate empirical coverage (dataset availability) by research domain."""

    print("EMPIRICAL COVERAGE BY DOMAIN:")
    print("=" * 35)

    # Extract data
    papers_with_analysis = data["papers_with_analysis"]
    papers_with_datasets = data["papers_with_datasets"]
    paper_to_main_categories = data["paper_to_main_categories"]
    paper_to_other_categories = data["paper_to_other_categories"]
    main_research_categories = data["main_research_categories"]

    # Calculate coverage by domain
    domain_coverage = {}

    for category in main_research_categories + ["Other research domains"]:
        # Find papers in this domain
        domain_papers = set()

        if category == "Other research domains":
            # Papers with ONLY other domains
            for paper_id in paper_to_other_categories:
                if paper_id not in paper_to_main_categories:
                    domain_papers.add(paper_id)
        else:
            # Papers with this main domain
            for paper_id, categories in paper_to_main_categories.items():
                if category in categories:
                    domain_papers.add(paper_id)

        # Filter to papers with AI analysis
        domain_papers_with_analysis = domain_papers & papers_with_analysis
        domain_papers_with_datasets = domain_papers & papers_with_datasets

        if len(domain_papers_with_analysis) > 0:
            coverage = len(domain_papers_with_datasets) / len(
                domain_papers_with_analysis
            )
            domain_coverage[category] = {
                "total_papers": len(domain_papers_with_analysis),
                "empirical_papers": len(domain_papers_with_datasets),
                "theoretical_papers": len(domain_papers_with_analysis)
                - len(domain_papers_with_datasets),
                "empirical_coverage": coverage,
            }

            print(f"{category}:")
            print(f"  Total papers: {len(domain_papers_with_analysis)}")
            print(
                f"  Empirical (with datasets): {len(domain_papers_with_datasets)} ({coverage*100:.1f}%)"
            )
            print(
                f"  Theoretical (domains only): {len(domain_papers_with_analysis) - len(domain_papers_with_datasets)} ({(1-coverage)*100:.1f}%)"
            )
            print()

    return domain_coverage


def calculate_correction_factors(domain_coverage):
    """Calculate correction factors based on empirical coverage gaps."""

    print("CORRECTION FACTOR CALCULATION:")
    print("=" * 35)

    # Calculate overall empirical coverage
    total_papers = sum(stats["total_papers"] for stats in domain_coverage.values())
    total_empirical = sum(
        stats["empirical_papers"] for stats in domain_coverage.values()
    )
    overall_coverage = total_empirical / total_papers if total_papers > 0 else 0

    print(f"Overall empirical coverage: {overall_coverage*100:.1f}%")
    print(f"Overall theoretical gap: {(1-overall_coverage)*100:.1f}%")
    print()

    # Calculate correction factors
    correction_factors = {}

    for category, stats in domain_coverage.items():
        domain_coverage_rate = stats["empirical_coverage"]

        # Correction factor methodology:
        # If a domain has lower empirical coverage than average,
        # it may be over-represented in raw counts
        # Correction factor = domain_coverage / overall_coverage

        if overall_coverage > 0:
            correction_factor = domain_coverage_rate / overall_coverage
        else:
            correction_factor = 1.0

        correction_factors[category] = {
            "raw_coverage": domain_coverage_rate,
            "correction_factor": correction_factor,
            "interpretation": "under-represented"
            if correction_factor > 1
            else "over-represented"
            if correction_factor < 1
            else "balanced",
        }

        print(f"{category}:")
        print(f"  Raw empirical coverage: {domain_coverage_rate*100:.1f}%")
        print(f"  Correction factor: {correction_factor:.3f}")
        print(f"  Interpretation: {correction_factors[category]['interpretation']}")
        print()

    return correction_factors, overall_coverage


def apply_dataset_corrections(data, correction_factors):
    """Apply dataset-based corrections to the temporal analysis."""

    print("APPLYING DATASET-BASED CORRECTIONS:")
    print("=" * 40)

    # Extract data
    paper_to_year = data["paper_to_year"]
    papers_with_analysis = data["papers_with_analysis"]
    paper_to_main_categories = data["paper_to_main_categories"]
    paper_to_other_categories = data["paper_to_other_categories"]
    all_research_categories = data["all_research_categories"]

    # Organize papers by year and category (same as before)
    years = list(range(2019, 2025))
    categories = [
        "WITHOUT AI analysis",
        "NO domain classification",
    ] + all_research_categories

    # Calculate RAW counts first (uncorrected)
    raw_year_data = {year: {cat: 0 for cat in categories} for year in years}
    total_papers_by_year = {year: 0 for year in years}

    for paper_id, year in paper_to_year.items():
        if year not in years:
            continue

        total_papers_by_year[year] += 1

        if paper_id not in papers_with_analysis:
            raw_year_data[year]["WITHOUT AI analysis"] += 1
            continue

        # Get paper's categories
        main_categories = paper_to_main_categories.get(paper_id, set())
        other_categories = paper_to_other_categories.get(paper_id, set())

        if not main_categories and not other_categories:
            raw_year_data[year]["NO domain classification"] += 1
        elif main_categories:
            # Multi-label for main categories
            for category in main_categories:
                raw_year_data[year][category] += 1
        else:
            # Other category (mutually exclusive)
            raw_year_data[year]["Other research domains"] += 1

    # Apply corrections to research domain counts
    corrected_year_data = {year: {cat: 0 for cat in categories} for year in years}

    for year in years:
        # Copy non-research categories as-is
        corrected_year_data[year]["WITHOUT AI analysis"] = raw_year_data[year][
            "WITHOUT AI analysis"
        ]
        corrected_year_data[year]["NO domain classification"] = raw_year_data[year][
            "NO domain classification"
        ]

        # Apply correction factors to research domains
        for category in all_research_categories:
            raw_count = raw_year_data[year][category]
            correction_factor = correction_factors.get(category, {}).get(
                "correction_factor", 1.0
            )
            corrected_count = raw_count * correction_factor
            corrected_year_data[year][category] = corrected_count

            print(
                f"{year} {category}: {raw_count:.0f} → {corrected_count:.1f} (factor: {correction_factor:.3f})"
            )

    return raw_year_data, corrected_year_data, total_papers_by_year


def create_comparison_visualization(
    raw_year_data, corrected_year_data, total_papers_by_year
):
    """Create visualization comparing raw vs corrected domain distributions."""

    years = list(range(2019, 2025))
    research_categories = [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
        "Other research domains",
    ]

    # Prepare data for plotting
    raw_data = np.zeros((len(research_categories), len(years)))
    corrected_data = np.zeros((len(research_categories), len(years)))

    for i, year in enumerate(years):
        total_research_raw = sum(
            raw_year_data[year][cat] for cat in research_categories
        )
        total_research_corrected = sum(
            corrected_year_data[year][cat] for cat in research_categories
        )

        for j, category in enumerate(research_categories):
            raw_count = raw_year_data[year][category]
            corrected_count = corrected_year_data[year][category]

            raw_data[j, i] = (
                raw_count / total_research_raw * 100 if total_research_raw > 0 else 0
            )
            corrected_data[j, i] = (
                corrected_count / total_research_corrected * 100
                if total_research_corrected > 0
                else 0
            )

    # Colors
    colors = [
        "#2ca02c",  # Green - Computer Vision
        "#1f77b4",  # Blue - Natural Language Processing
        "#9467bd",  # Purple - Reinforcement Learning
        "#8c564b",  # Brown - Graph Learning
        "#e377c2",  # Pink - Other research domains
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Raw data
    ax1.stackplot(years, raw_data, labels=research_categories, colors=colors, alpha=0.8)
    ax1.set_title(
        "Raw Domain Distribution (No Corrections)", fontsize=14, fontweight="bold"
    )
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Percentage of Research Papers (%)")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Corrected data
    ax2.stackplot(
        years, corrected_data, labels=research_categories, colors=colors, alpha=0.8
    )
    ax2.set_title(
        "Dataset-Corrected Domain Distribution", fontsize=14, fontweight="bold"
    )
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Percentage of Research Papers (%)")
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.tight_layout()
    plt.savefig("dataset_corrections_comparison.png", dpi=300, bbox_inches="tight")
    plt.show()

    return raw_data, corrected_data


def main():
    """Execute the complete dataset-based correction process."""

    print("DATASET-BASED CORRECTION PROCESS")
    print("=" * 50)

    # Step 1: Analyze empirical vs theoretical distribution
    data = analyze_empirical_vs_theoretical()

    # Step 2: Calculate empirical coverage by domain
    domain_coverage = calculate_empirical_coverage_by_domain(data)

    # Step 3: Calculate correction factors
    correction_factors, overall_coverage = calculate_correction_factors(domain_coverage)

    # Step 4: Apply corrections
    raw_year_data, corrected_year_data, total_papers_by_year = (
        apply_dataset_corrections(data, correction_factors)
    )

    # Step 5: Create comparison visualization
    raw_data, corrected_data = create_comparison_visualization(
        raw_year_data, corrected_year_data, total_papers_by_year
    )

    # Save results
    results = {
        "domain_coverage": domain_coverage,
        "correction_factors": correction_factors,
        "overall_coverage": overall_coverage,
        "raw_year_data": raw_year_data,
        "corrected_year_data": corrected_year_data,
        "total_papers_by_year": total_papers_by_year,
    }

    with open("dataset_based_corrections_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nDataset-based correction process completed!")
    print("Results saved to: dataset_based_corrections_results.json")
    print("Comparison chart saved to: dataset_corrections_comparison.png")

    return results


if __name__ == "__main__":
    results = main()
