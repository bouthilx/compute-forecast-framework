#!/usr/bin/env python3
"""
Create a plain text diagram showing how papers get filtered through our analysis pipeline.
"""

import json
import sys
from collections import defaultdict


def load_all_data():
    """Load all analysis data to get exact numbers."""

    # Load basic paper data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    # Load analysis results
    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    with open("empirical_correction_analysis.json", "r") as f:
        correction_data = json.load(f)

    return papers_data, raw_domains, research_data, dataset_data, correction_data


def calculate_filtering_stats():
    """Calculate exact numbers for each filtering step."""

    papers_data, raw_domains, research_data, dataset_data, correction_data = (
        load_all_data()
    )

    # Step 1: Total papers
    total_papers = len(papers_data)

    # Step 2: Papers with analysis (have query files)
    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    papers_with_analysis = 0
    papers_with_domains = set()
    papers_with_datasets = set()

    for paper_json in papers_data:
        try:
            paper = Paper(paper_json)
            if paper.queries:
                papers_with_analysis += 1
        except:
            continue

    # Step 3: Papers with research domains
    for domain_entry in raw_domains:
        papers_with_domains.add(domain_entry["paper_id"])

    # Step 4: Papers with datasets/environments
    for paper_id in dataset_data["dataset_classifications"].keys():
        papers_with_datasets.add(paper_id)

    # Step 5: Research domain categories
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    papers_by_category = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            papers_by_category[category].add(paper_id)

    # Step 6: Dataset/environment categories
    dataset_categories = defaultdict(int)
    for paper_id, info in dataset_data["dataset_classifications"].items():
        domain = info["domain"]
        dataset_categories[domain] += 1

    return {
        "total_papers": total_papers,
        "papers_with_analysis": papers_with_analysis,
        "papers_with_domains": len(papers_with_domains),
        "papers_with_datasets": len(papers_with_datasets),
        "papers_by_category": {k: len(v) for k, v in papers_by_category.items()},
        "dataset_categories": dict(dataset_categories),
        "correction_data": correction_data,
    }


def create_filtering_diagram():
    """Create a comprehensive plain text diagram of the filtering process."""

    stats = calculate_filtering_stats()

    print("MILA PAPERS FILTERING & ANALYSIS PIPELINE")
    print("=" * 80)
    print()

    # Level 1: Total papers
    print("                    ALL MILA PAPERS")
    print("                   ┌─────────────────┐")
    print(f"                   │   {stats['total_papers']:,} papers    │")
    print("                   │   (2019-2024)    │")
    print("                   └─────────────────┘")
    print("                           │")
    print("                           ▼")

    # Level 2: Analysis availability split
    papers_with_analysis = stats["papers_with_analysis"]
    papers_without_analysis = stats["total_papers"] - papers_with_analysis

    print("              ┌─────────────────────────┐")
    print("              │     ANALYSIS FILTER     │")
    print("              │  (Have AI extractions)  │")
    print("              └─────────────────────────┘")
    print("                     │           │")
    print("                     ▼           ▼")
    print("           ┌───────────────┐   ┌───────────────┐")
    print("           │ WITH ANALYSIS │   │   NO ANALYSIS │")
    print(
        f"           │  {papers_with_analysis:,} papers   │   │   {papers_without_analysis:,} papers   │"
    )
    print(
        f"           │   ({papers_with_analysis/stats['total_papers']*100:.1f}%)      │   │    ({papers_without_analysis/stats['total_papers']*100:.1f}%)       │"
    )
    print("           └───────────────┘   └───────────────┘")
    print("                     │               │")
    print("                     ▼               ▼")
    print("               [CONTINUE]        [EXCLUDED]")
    print()

    # Level 3: Domain classification split
    papers_with_domains = stats["papers_with_domains"]
    papers_with_datasets = stats["papers_with_datasets"]

    print("              ┌─────────────────────────┐")
    print("              │   DOMAIN CLASSIFICATION │")
    print("              │      APPROACHES         │")
    print("              └─────────────────────────┘")
    print("                     │           │")
    print("                     ▼           ▼")
    print("         ┌─────────────────┐   ┌─────────────────┐")
    print("         │ RESEARCH DOMAINS│   │ DATASET/ENV     │")
    print(
        f"         │   {papers_with_domains:,} papers    │   │   {papers_with_datasets:,} papers     │"
    )
    print(
        f"         │    ({papers_with_domains/papers_with_analysis*100:.1f}%)        │   │    ({papers_with_datasets/papers_with_analysis*100:.1f}%)         │"
    )
    print("         └─────────────────┘   └─────────────────┘")
    print()

    # Level 4: Research domain breakdown
    print("RESEARCH DOMAIN BREAKDOWN:")
    print("┌────────────────────────────────────────┐")

    categories = stats["papers_by_category"]
    total_domain_papers = sum(categories.values())

    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if count >= 100:  # Show major categories
            pct = count / total_domain_papers * 100
            print(f"│ {category:<30} │ {count:>4} ({pct:>4.1f}%) │")

    print("└────────────────────────────────────────┘")
    print()

    # Level 5: Dataset/Environment breakdown
    print("DATASET/ENVIRONMENT BREAKDOWN:")
    print("┌────────────────────────────────────────┐")

    dataset_cats = stats["dataset_categories"]
    total_dataset_papers = sum(dataset_cats.values())

    for category, count in sorted(
        dataset_cats.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / total_dataset_papers * 100
        print(f"│ {category:<30} │ {count:>4} ({pct:>4.1f}%) │")

    print("└────────────────────────────────────────┘")
    print()

    # Level 6: Empirical correction process
    print("EMPIRICAL-BASED CORRECTION PROCESS:")
    print("═" * 80)
    print()

    correction_recs = stats["correction_data"]["correction_recommendations"]

    print(
        "┌─────────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "│                           CORRECTION METHODOLOGY                            │"
    )
    print(
        "│                                                                             │"
    )
    print(
        "│  1. Classify all papers as Empirical vs Theoretical                        │"
    )
    print(
        "│  2. Measure how well Dataset/Env method captures empirical work            │"
    )
    print(
        "│  3. Adjust counts upward based on empirical coverage gaps                  │"
    )
    print(
        "└─────────────────────────────────────────────────────────────────────────────┘"
    )
    print()

    print("DOMAIN-SPECIFIC CORRECTIONS:")
    print(
        "┌────────────────────────────────────┬─────────┬─────────┬─────────┬─────────┐"
    )
    print(
        "│ Domain                             │Research │Dataset  │Coverage │Corrected│"
    )
    print(
        "├────────────────────────────────────┼─────────┼─────────┼─────────┼─────────┤"
    )

    main_domains = [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
        "Machine Learning Theory & Methods",
    ]

    for domain in main_domains:
        if domain in correction_recs:
            rec = correction_recs[domain]
            research_count = rec["original_research"]
            dataset_count = rec["original_dataset"]
            coverage = rec["empirical_coverage"]
            corrected = rec["corrected_count"]

            domain_short = domain[:30] + "..." if len(domain) > 30 else domain
            print(
                f"│ {domain_short:<34} │ {research_count:>7} │ {dataset_count:>7} │ {coverage:>6.1f}% │ {corrected:>7} │"
            )

    print(
        "└────────────────────────────────────┴─────────┴─────────┴─────────┴─────────┘"
    )
    print()

    # Final summary
    total_original = sum(rec["original_research"] for rec in correction_recs.values())
    total_corrected = sum(rec["corrected_count"] for rec in correction_recs.values())

    print("FINAL COMPUTATIONAL WORKLOAD ESTIMATES:")
    print(
        "┌─────────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "│                                                                             │"
    )
    print(
        f"│  Original Research Domain Total:     {total_original:,} papers                         │"
    )
    print(
        f"│  Empirical-Corrected Total:          {total_corrected:,} papers                         │"
    )
    print(
        f"│  Net Change:                         {total_corrected - total_original:+,} papers                           │"
    )
    print(
        "│                                                                             │"
    )
    print(
        "│  → Accounts for empirical work missed by dataset/environment detection     │"
    )
    print(
        "│  → Preserves all research while correcting for computational relevance     │"
    )
    print(
        "└─────────────────────────────────────────────────────────────────────────────┘"
    )


def create_simple_flow_diagram():
    """Create a simpler flow-focused diagram."""

    stats = calculate_filtering_stats()

    print("\n" + "=" * 80)
    print("SIMPLIFIED PAPER FLOW DIAGRAM")
    print("=" * 80)
    print()

    total = stats["total_papers"]
    analyzed = stats["papers_with_analysis"]
    domains = stats["papers_with_domains"]
    datasets = stats["papers_with_datasets"]

    print(f"    {total:,} Total Papers")
    print("         │")
    print("         ▼")
    print("    ┌─────────────┐")
    print("    │ AI Analysis │")
    print("    │   Filter    │")
    print("    └─────────────┘")
    print("         │")
    print("         ▼")
    print(f"    {analyzed:,} Papers with Analysis")
    print("         │")
    print("    ┌────┴────┐")
    print("    ▼         ▼")
    print("┌─────────┐ ┌─────────┐")
    print("│Research │ │Dataset/ │")
    print("│Domains  │ │Environ  │")
    print("│Method   │ │Method   │")
    print("└─────────┘ └─────────┘")
    print("    │         │")
    print("    ▼         ▼")
    print(f"  {domains:,}      {datasets:,}")
    print("  papers    papers")
    print("    │         │")
    print("    └────┬────┘")
    print("         ▼")
    print("   ┌─────────────┐")
    print("   │ Empirical   │")
    print("   │ Correction  │")
    print("   │ Analysis    │")
    print("   └─────────────┘")
    print("         │")
    print("         ▼")
    print("   Final Counts")
    print("   (Corrected)")


def main():
    """Generate both detailed and simple diagrams."""

    create_filtering_diagram()
    create_simple_flow_diagram()


if __name__ == "__main__":
    main()
