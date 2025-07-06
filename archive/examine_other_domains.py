#!/usr/bin/env python3
"""
Examine what domains are actually classified as "Other research domains"
"""

import json
from collections import defaultdict, Counter


def examine_other_domains():
    """Examine what's in the Other research domains category."""

    print("EXAMINING 'OTHER RESEARCH DOMAINS' CATEGORY")
    print("=" * 50)

    # Load domain data
    with open("all_domains_actual_fix.json", "r") as f:
        raw_domains = json.load(f)

    # Load taxonomy
    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    # Create domain mappings
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    # Add automatic categorization for unmapped domains
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

            # Auto-categorize based on keywords
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

    # Define main research categories
    main_research_categories = {
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
    }

    # Get papers with only "Other" domains
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

    # Find papers with ONLY other domains
    papers_with_only_other = []
    for paper_id, other_cats in paper_to_other_categories.items():
        if paper_id not in paper_to_main_categories:
            papers_with_only_other.append(paper_id)

    print(f"Papers with ONLY other domains: {len(papers_with_only_other)}")

    # Get the actual domain names that map to "Other"
    other_domain_names = []
    for domain_entry in raw_domains:
        domain_name = domain_entry["domain_name"]
        if (
            domain_name in domain_to_category
            and domain_to_category[domain_name] == "Other research domains"
        ):
            other_domain_names.append(domain_name)

    other_domain_counts = Counter(other_domain_names)

    print("\nActual domains classified as 'Other research domains':")
    print(f"Total unique 'Other' domains: {len(other_domain_counts)}")
    print(f"Total 'Other' domain assignments: {sum(other_domain_counts.values())}")

    print("\nTop 20 'Other' domains by frequency:")
    for domain_name, count in other_domain_counts.most_common(20):
        print(f"  {domain_name}: {count} papers")

    # Sample some papers that have ONLY other domains
    print("\nSample papers with ONLY 'Other' domains:")
    print("-" * 40)

    # Load papers data to get titles
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    paper_id_to_title = {}
    for paper_json in papers_data:
        paper_id = paper_json.get("paper_id", "")
        title = paper_json.get("title", "No title")
        paper_id_to_title[paper_id] = title

    # Show sample papers
    sample_count = 0
    for paper_id in papers_with_only_other[:10]:  # Show first 10
        title = paper_id_to_title.get(paper_id, "Unknown title")

        # Get this paper's domains
        paper_domains = []
        for domain_entry in raw_domains:
            if domain_entry["paper_id"] == paper_id:
                paper_domains.append(domain_entry["domain_name"])

        print(f"\nPaper: {title}")
        print(f"Domains: {', '.join(paper_domains)}")
        sample_count += 1

    # Check if there are any unmapped domains
    unmapped_domains = []
    for domain_entry in raw_domains:
        domain_name = domain_entry["domain_name"]
        if domain_name not in domain_to_category:
            unmapped_domains.append(domain_name)

    unmapped_counts = Counter(unmapped_domains)

    if unmapped_counts:
        print("\nUnmapped domains (should not exist):")
        for domain_name, count in unmapped_counts.most_common(10):
            print(f"  {domain_name}: {count}")
    else:
        print("\nAll domains are mapped ✓")

    return other_domain_counts, papers_with_only_other


if __name__ == "__main__":
    other_domains, other_papers = examine_other_domains()
