#!/usr/bin/env python3
"""
Create a complete paper accounting diagram showing overlaps and excluded papers at each step.
"""

import json
import sys
from collections import defaultdict


def calculate_complete_paper_flow():
    """Calculate exact numbers with overlaps and exclusions at each step."""

    # Load all data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    print("COMPLETE PAPER ACCOUNTING ANALYSIS")
    print("=" * 80)

    # Step 1: Total papers
    total_papers = len(papers_data)
    {paper["paper_id"] for paper in papers_data}

    print("\nSTEP 1: Starting Universe")
    print(f"Total Mila papers (2019-2024): {total_papers:,}")

    # Step 2: Papers with AI analysis
    papers_with_analysis = set()
    papers_without_analysis = set()

    for paper_json in papers_data:
        paper_id = paper_json.get("paper_id", "")
        try:
            paper = Paper(paper_json)
            if paper.queries:
                papers_with_analysis.add(paper_id)
            else:
                papers_without_analysis.add(paper_id)
        except Exception:
            papers_without_analysis.add(paper_id)

    print("\nSTEP 2: AI Analysis Filter")
    print(
        f"Papers WITH analysis: {len(papers_with_analysis):,} ({len(papers_with_analysis) / total_papers * 100:.1f}%)"
    )
    print(
        f"Papers WITHOUT analysis: {len(papers_without_analysis):,} ({len(papers_without_analysis) / total_papers * 100:.1f}%)"
    )
    print(
        f"Total accounted: {len(papers_with_analysis) + len(papers_without_analysis):,}"
    )

    # Verify step 2
    assert len(papers_with_analysis) + len(papers_without_analysis) == total_papers

    # Step 3: Domain classification methods (only on papers WITH analysis)
    papers_with_research_domains = set()
    for domain_entry in raw_domains:
        papers_with_research_domains.add(domain_entry["paper_id"])

    papers_with_datasets = set()
    for paper_id in dataset_data["dataset_classifications"].keys():
        papers_with_datasets.add(paper_id)

    # Calculate overlaps within the "WITH analysis" universe
    both_methods = papers_with_research_domains & papers_with_datasets
    research_only = papers_with_research_domains - papers_with_datasets
    dataset_only = papers_with_datasets - papers_with_research_domains
    neither_method = (
        papers_with_analysis - papers_with_research_domains - papers_with_datasets
    )

    print(
        f"\nSTEP 3: Domain Classification (within {len(papers_with_analysis):,} analyzed papers)"
    )
    print(f"Research domains only: {len(research_only):,}")
    print(f"Dataset/env only: {len(dataset_only):,}")
    print(f"BOTH methods: {len(both_methods):,}")
    print(f"NEITHER method: {len(neither_method):,}")
    print(
        f"Sub-total classified: {len(research_only) + len(dataset_only) + len(both_methods):,}"
    )
    print(f"Sub-total analyzed: {len(papers_with_analysis):,}")

    # Verify step 3
    classified_total = (
        len(research_only) + len(dataset_only) + len(both_methods) + len(neither_method)
    )
    assert classified_total == len(papers_with_analysis), (
        f"Mismatch: {classified_total} vs {len(papers_with_analysis)}"
    )

    # Totals for each method
    total_research_domains = len(papers_with_research_domains)
    total_datasets = len(papers_with_datasets)

    print("\nMethod totals:")
    print(f"Total with research domains: {total_research_domains:,}")
    print(f"Total with datasets/env: {total_datasets:,}")
    print(
        f"Union of both methods: {len(papers_with_research_domains | papers_with_datasets):,}"
    )

    return {
        "total_papers": total_papers,
        "papers_with_analysis": len(papers_with_analysis),
        "papers_without_analysis": len(papers_without_analysis),
        "research_only": len(research_only),
        "dataset_only": len(dataset_only),
        "both_methods": len(both_methods),
        "neither_method": len(neither_method),
        "total_research_domains": total_research_domains,
        "total_datasets": total_datasets,
        "research_domains_set": papers_with_research_domains,
        "datasets_set": papers_with_datasets,
        "both_methods_set": both_methods,
    }


def create_complete_accounting_diagram():
    """Create the complete accounting diagram."""

    stats = calculate_complete_paper_flow()

    print("\n" + "=" * 80)
    print("COMPLETE PAPER FLOW DIAGRAM WITH FULL ACCOUNTING")
    print("=" * 80)

    total = stats["total_papers"]
    with_analysis = stats["papers_with_analysis"]
    without_analysis = stats["papers_without_analysis"]

    print(f"""
                           ALL MILA PAPERS
                          ┌─────────────────┐
                          │   {total:,} papers    │
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
          │   {with_analysis:,} papers   │           │   {without_analysis:,} papers    │
          │    ({with_analysis / total * 100:.1f}%)        │           │    ({without_analysis / total * 100:.1f}%)         │
          └─────────────────┘           └─────────────────┘
                    │                           │
                    ▼                           ▼
               [CONTINUE]                  [EXCLUDED]
    """)

    # Step 3: Domain classification breakdown
    research_only = stats["research_only"]
    dataset_only = stats["dataset_only"]
    both_methods = stats["both_methods"]
    neither_method = stats["neither_method"]
    total_research = stats["total_research_domains"]
    total_datasets = stats["total_datasets"]

    print(f"""
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
    """)

    print(f"""
    DETAILED BREAKDOWN OF {with_analysis:,} ANALYZED PAPERS:
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  Research Domains ONLY:     {research_only:,} papers                         │
    │  Dataset/Environment ONLY:  {dataset_only:,} papers                          │
    │  BOTH methods:              {both_methods:,} papers                           │
    │  NEITHER method:            {neither_method:,} papers                          │
    │                                           ────────                   │
    │  TOTAL:                     {research_only + dataset_only + both_methods + neither_method:,} papers                         │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)

    print(f"""
    METHOD TOTALS (with overlap):
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  Research Domains method:   {total_research:,} papers                         │
    │  Dataset/Environment method: {total_datasets:,} papers                          │
    │  Overlap (both methods):    {both_methods:,} papers                           │
    │  Union of both methods:     {research_only + dataset_only + both_methods:,} papers                         │
    │  Neither method:            {neither_method:,} papers                          │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
    """)


def analyze_domain_breakdown_with_accounting():
    """Show domain breakdown while maintaining paper accounting."""

    stats = calculate_complete_paper_flow()

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    print("\n" + "=" * 80)
    print("DOMAIN BREAKDOWN WITH PAPER ACCOUNTING")
    print("=" * 80)

    # Research domain breakdown
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    papers_by_research_category = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            papers_by_research_category[category].add(paper_id)

    # Dataset breakdown
    papers_by_dataset_category = defaultdict(set)
    for paper_id, info in dataset_data["dataset_classifications"].items():
        domain = info["domain"]
        papers_by_dataset_category[domain].add(paper_id)

    print(f"RESEARCH DOMAINS METHOD ({stats['total_research_domains']:,} papers):")
    print("┌────────────────────────────────────────┐")
    total_research_assigned = 0
    for category, papers in sorted(
        papers_by_research_category.items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(papers)
        total_research_assigned += count
        pct = count / stats["total_research_domains"] * 100
        print(f"│ {category:<30} │ {count:>4} ({pct:>4.1f}%) │")
    print("└────────────────────────────────────────┘")
    print(f"Total research domain assignments: {total_research_assigned:,}")
    print("(Note: Papers can have multiple domains)")

    print(f"\nDATASET/ENVIRONMENT METHOD ({stats['total_datasets']:,} papers):")
    print("┌────────────────────────────────────────┐")
    total_dataset_assigned = 0
    for category, papers in sorted(
        papers_by_dataset_category.items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(papers)
        total_dataset_assigned += count
        pct = count / stats["total_datasets"] * 100
        print(f"│ {category:<30} │ {count:>4} ({pct:>4.1f}%) │")
    print("└────────────────────────────────────────┘")
    print(f"Total dataset/env assignments: {total_dataset_assigned:,}")
    print("(Note: Each paper has exactly one primary domain)")

    # Show overlap analysis for major domains
    print("\nOVERLAP ANALYSIS FOR MAJOR DOMAINS:")
    print(
        "┌────────────────────────────────────┬─────────┬─────────┬─────────┬─────────┐"
    )
    print(
        "│ Domain                             │Research │Dataset  │ Overlap │ Union   │"
    )
    print(
        "├────────────────────────────────────┼─────────┼─────────┼─────────┼─────────┤"
    )

    # Map dataset domains to research domains
    domain_mapping = {
        "Computer Vision & Medical Imaging": "Computer Vision & Medical Imaging",
        "Natural Language Processing": "Natural Language Processing",
        "Reinforcement Learning & Robotics": "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis": "Graph Learning & Network Analysis",
    }

    for dataset_domain, research_domain in domain_mapping.items():
        research_papers = papers_by_research_category.get(research_domain, set())
        dataset_papers = papers_by_dataset_category.get(dataset_domain, set())

        overlap = research_papers & dataset_papers
        union = research_papers | dataset_papers

        print(
            f"│ {dataset_domain[:30]:<30} │ {len(research_papers):>7} │ {len(dataset_papers):>7} │ {len(overlap):>7} │ {len(union):>7} │"
        )

    print(
        "└────────────────────────────────────┴─────────┴─────────┴─────────┴─────────┘"
    )


def final_paper_flow_summary():
    """Provide final summary showing complete paper flow."""

    stats = calculate_complete_paper_flow()

    print("\n" + "=" * 80)
    print("FINAL PAPER FLOW SUMMARY")
    print("=" * 80)

    total = stats["total_papers"]
    analyzed = stats["papers_with_analysis"]
    not_analyzed = stats["papers_without_analysis"]
    classified = stats["research_only"] + stats["dataset_only"] + stats["both_methods"]
    not_classified = stats["neither_method"]

    print(f"""
    COMPLETE PAPER ACCOUNTING:

    Starting papers:                    {total:,}
    ├─ WITH AI analysis:                {analyzed:,} ({analyzed / total * 100:.1f}%)
    │  ├─ Classified by domain methods: {classified:,} ({classified / analyzed * 100:.1f}% of analyzed)
    │  │  ├─ Research domains only:     {stats["research_only"]:,}
    │  │  ├─ Dataset/env only:          {stats["dataset_only"]:,}
    │  │  └─ Both methods:              {stats["both_methods"]:,}
    │  └─ NOT classified:               {not_classified:,} ({not_classified / analyzed * 100:.1f}% of analyzed)
    └─ WITHOUT AI analysis:             {not_analyzed:,} ({not_analyzed / total * 100:.1f}%)

    METHOD COVERAGE:
    ├─ Research domains method:         {stats["total_research_domains"]:,} papers
    ├─ Dataset/environment method:      {stats["total_datasets"]:,} papers
    ├─ Overlap between methods:         {stats["both_methods"]:,} papers
    └─ Union of both methods:           {classified:,} papers

    PAPERS EXCLUDED AT EACH STEP:
    ├─ No AI analysis available:        {not_analyzed:,} papers
    ├─ Analysis but no domains found:   {not_classified:,} papers
    └─ Total excluded from analysis:    {not_analyzed + not_classified:,} papers
    """)


def main():
    """Run complete paper accounting analysis."""

    calculate_complete_paper_flow()
    create_complete_accounting_diagram()
    analyze_domain_breakdown_with_accounting()
    final_paper_flow_summary()


if __name__ == "__main__":
    main()
