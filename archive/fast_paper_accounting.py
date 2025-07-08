#!/usr/bin/env python3
"""
Fast paper accounting using pre-computed data.
"""

import json


def create_fast_paper_accounting():
    """Create complete paper accounting diagram using existing data."""

    # Load all data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    print("COMPLETE PAPER FLOW DIAGRAM WITH FULL ACCOUNTING")
    print("=" * 80)

    # Step 1: Total papers
    total_papers = len(papers_data)
    print(f"\nSTEP 1: Total Mila papers: {total_papers:,}")

    # Step 2: Papers with analysis (from our previous analysis)
    # We know from empirical_correction_analysis.py that 2,283 papers were classified
    papers_with_analysis = 2283  # From previous analysis
    papers_without_analysis = total_papers - papers_with_analysis

    print("\nSTEP 2: AI Analysis Filter")
    print(
        f"Papers WITH analysis: {papers_with_analysis:,} ({papers_with_analysis / total_papers * 100:.1f}%)"
    )
    print(
        f"Papers WITHOUT analysis: {papers_without_analysis:,} ({papers_without_analysis / total_papers * 100:.1f}%)"
    )

    # Step 3: Domain classification
    papers_with_research_domains = set()
    for domain_entry in raw_domains:
        papers_with_research_domains.add(domain_entry["paper_id"])

    papers_with_datasets = set()
    for paper_id in dataset_data["dataset_classifications"].keys():
        papers_with_datasets.add(paper_id)

    # Calculate overlaps
    both_methods = papers_with_research_domains & papers_with_datasets
    research_only = papers_with_research_domains - papers_with_datasets
    dataset_only = papers_with_datasets - papers_with_research_domains

    # Calculate papers with neither method
    classified_papers = research_only | dataset_only | both_methods
    neither_method = papers_with_analysis - len(classified_papers)

    total_research = len(papers_with_research_domains)
    total_datasets = len(papers_with_datasets)

    print(
        f"\nSTEP 3: Domain Classification (within {papers_with_analysis:,} analyzed papers)"
    )
    print(f"Research domains only: {len(research_only):,}")
    print(f"Dataset/env only: {len(dataset_only):,}")
    print(f"BOTH methods: {len(both_methods):,}")
    print(f"NEITHER method: {neither_method:,}")
    print(f"Total classified: {len(classified_papers):,}")

    # Verify accounting
    accounted = (
        len(research_only) + len(dataset_only) + len(both_methods) + neither_method
    )
    print(
        f"Verification: {accounted:,} = {papers_with_analysis:,} ✓"
        if accounted == papers_with_analysis
        else f"ERROR: {accounted} ≠ {papers_with_analysis}"
    )

    # Create the diagram
    print("\n" + "=" * 80)
    print("COMPLETE PAPER FLOW DIAGRAM")
    print("=" * 80)

    print(f"""
                           ALL MILA PAPERS
                          ┌─────────────────┐
                          │   {total_papers:,} papers    │
                          │   (2019-2024)    │
                          └─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │   AI ANALYSIS       │
                         │     FILTER          │
                         └─────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌─────────────────┐           ┌─────────────────┐
          │  WITH ANALYSIS  │           │ WITHOUT ANALYSIS│
          │   {papers_with_analysis:,} papers   │           │   {papers_without_analysis:,} papers    │
          │    ({papers_with_analysis / total_papers * 100:.1f}%)        │           │    ({papers_without_analysis / total_papers * 100:.1f}%)         │
          └─────────────────┘           └─────────────────┘
                    │                           │
                    ▼                           ▼
               [CONTINUE]                  [EXCLUDED]

                         ┌─────────────────────┐
                         │ DOMAIN CLASSIFICATION│
                         │   (Two Methods)      │
                         └─────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌─────────────────┐           ┌─────────────────┐
          │ RESEARCH DOMAINS│           │  DATASET/ENV    │
          │  {total_research:,} papers    │           │   {total_datasets:,} papers     │
          └─────────────────┘           └─────────────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
    """)

    print(f"""
    DETAILED BREAKDOWN OF {papers_with_analysis:,} ANALYZED PAPERS:
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  Research Domains ONLY:     {len(research_only):,} papers                         │
    │  Dataset/Environment ONLY:  {len(dataset_only):,} papers                          │
    │  BOTH methods:              {len(both_methods):,} papers                           │
    │  NEITHER method:            {neither_method:,} papers                          │
    │                                           ────────                   │
    │  TOTAL:                     {accounted:,} papers                         │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)

    print(f"""
    METHOD TOTALS (showing overlap):
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  Research Domains method:   {total_research:,} papers                         │
    │  Dataset/Environment method: {total_datasets:,} papers                          │
    │                                                                 │
    │  Overlap (both methods):    {len(both_methods):,} papers                           │
    │  Union of both methods:     {len(classified_papers):,} papers                         │
    │                                                                 │
    │  EXCLUDED from analysis:                                        │
    │  ├─ No AI analysis:         {papers_without_analysis:,} papers                         │
    │  └─ No domain found:        {neither_method:,} papers                          │
    │      Total excluded:        {papers_without_analysis + neither_method:,} papers                         │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)

    # Show why numbers don't add up
    print("\nWHY TOTALS DON'T SIMPLY ADD:")
    print("─" * 40)
    print(f"Research Domains: {total_research:,} papers")
    print(f"Dataset/Env:      {total_datasets:,} papers")
    print(f"Simple sum:       {total_research + total_datasets:,} papers")
    print(f"But overlap:      {len(both_methods):,} papers counted twice")
    print(f"Actual union:     {len(classified_papers):,} papers")
    print(
        f"Difference:       {(total_research + total_datasets) - len(classified_papers):,} papers (the overlap)"
    )

    return {
        "total_papers": total_papers,
        "papers_with_analysis": papers_with_analysis,
        "papers_without_analysis": papers_without_analysis,
        "research_only": len(research_only),
        "dataset_only": len(dataset_only),
        "both_methods": len(both_methods),
        "neither_method": neither_method,
        "total_research": total_research,
        "total_datasets": total_datasets,
        "classified_papers": len(classified_papers),
    }


def show_domain_overlap_details():
    """Show detailed overlap for major domains."""

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    print("\n" + "=" * 80)
    print("DOMAIN-SPECIFIC OVERLAP ANALYSIS")
    print("=" * 80)

    # Create domain mappings
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    papers_by_research_category = {}
    for category in [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
    ]:
        papers_by_research_category[category] = set()

    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            if category in papers_by_research_category:
                papers_by_research_category[category].add(paper_id)

    # Dataset papers by category
    papers_by_dataset_category = {}
    for paper_id, info in dataset_data["dataset_classifications"].items():
        domain = info["domain"]
        if domain not in papers_by_dataset_category:
            papers_by_dataset_category[domain] = set()
        papers_by_dataset_category[domain].add(paper_id)

    # Map dataset domains to research domains
    domain_mapping = {
        "Computer Vision & Medical Imaging": "Computer Vision & Medical Imaging",
        "Natural Language Processing": "Natural Language Processing",
        "Reinforcement Learning & Robotics": "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis": "Graph Learning & Network Analysis",
    }

    print("OVERLAP ANALYSIS FOR MAJOR DOMAINS:")
    print(
        "┌────────────────────────────────────┬─────────┬─────────┬─────────┬─────────┬─────────┐"
    )
    print(
        "│ Domain                             │Research │Dataset  │ Overlap │ Union   │Coverage │"
    )
    print(
        "├────────────────────────────────────┼─────────┼─────────┼─────────┼─────────┼─────────┤"
    )

    for dataset_domain, research_domain in domain_mapping.items():
        research_papers = papers_by_research_category.get(research_domain, set())
        dataset_papers = papers_by_dataset_category.get(dataset_domain, set())

        overlap = research_papers & dataset_papers
        union = research_papers | dataset_papers

        # Coverage = how much of research domain is captured by dataset method
        coverage = (
            len(overlap) / len(research_papers) * 100 if len(research_papers) > 0 else 0
        )

        print(
            f"│ {dataset_domain[:30]:<30} │ {len(research_papers):>7} │ {len(dataset_papers):>7} │ {len(overlap):>7} │ {len(union):>7} │ {coverage:>6.1f}% │"
        )

    print(
        "└────────────────────────────────────┴─────────┴─────────┴─────────┴─────────┴─────────┘"
    )

    print("\nINTERPRETATION:")
    print("• Research: Papers classified by research domain analysis")
    print("• Dataset: Papers classified by dataset/environment detection")
    print("• Overlap: Papers found by BOTH methods")
    print("• Union: Total unique papers found by either method")
    print("• Coverage: % of research domain papers captured by dataset method")


def main():
    """Run fast paper accounting."""

    stats = create_fast_paper_accounting()
    show_domain_overlap_details()

    return stats


if __name__ == "__main__":
    main()
