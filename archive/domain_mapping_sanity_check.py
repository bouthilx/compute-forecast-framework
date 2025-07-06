#!/usr/bin/env python3
"""
Sanity check for domain mappings - find potentially incorrect automatic classifications.
"""

import json
from collections import defaultdict, Counter


def analyze_domain_mappings():
    """Analyze domain mappings to find potentially incorrect classifications."""

    print("DOMAIN MAPPING SANITY CHECK")
    print("=" * 50)

    # Load domain data
    with open("all_domains_actual_fix.json", "r") as f:
        raw_domains = json.load(f)

    # Load taxonomy
    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    # Recreate the mapping logic from create_final_temporal_analysis.py
    domain_to_category = {}
    for domain_name, info in research_data["classification"].items():
        domain_to_category[domain_name] = info["category"]

    # Keywords for automatic categorization
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

    # Track which domains were auto-mapped
    manually_mapped = set(domain_to_category.keys())
    auto_mapped = defaultdict(list)
    domain_frequencies = Counter()

    # Apply the same logic as the main analysis
    unique_domains = set()
    for domain_entry in raw_domains:
        domain_name = domain_entry["domain_name"]
        unique_domains.add(domain_name)
        domain_frequencies[domain_name] += 1

        if domain_name not in domain_to_category:
            domain_lower = domain_name.lower()

            # Auto-categorize based on keywords
            if any(kw in domain_lower for kw in cv_keywords):
                category = "Computer Vision & Medical Imaging"
                domain_to_category[domain_name] = category
                auto_mapped[category].append(
                    (domain_name, [kw for kw in cv_keywords if kw in domain_lower])
                )
            elif any(kw in domain_lower for kw in nlp_keywords):
                category = "Natural Language Processing"
                domain_to_category[domain_name] = category
                auto_mapped[category].append(
                    (domain_name, [kw for kw in nlp_keywords if kw in domain_lower])
                )
            elif any(kw in domain_lower for kw in rl_keywords):
                category = "Reinforcement Learning & Robotics"
                domain_to_category[domain_name] = category
                auto_mapped[category].append(
                    (domain_name, [kw for kw in rl_keywords if kw in domain_lower])
                )
            elif any(kw in domain_lower for kw in graph_keywords):
                category = "Graph Learning & Network Analysis"
                domain_to_category[domain_name] = category
                auto_mapped[category].append(
                    (domain_name, [kw for kw in graph_keywords if kw in domain_lower])
                )
            else:
                domain_to_category[domain_name] = "Other research domains"

    print(f"Total unique domains: {len(unique_domains)}")
    print(f"Manually mapped domains: {len(manually_mapped)}")
    print(f"Auto-mapped domains: {len(unique_domains) - len(manually_mapped)}")

    # Analyze auto-mapped domains for potential issues
    print("\nAUTO-MAPPED DOMAINS BY CATEGORY:")
    print("=" * 40)

    suspicious_mappings = []

    for category, domains_and_keywords in auto_mapped.items():
        print(f"\n{category}: {len(domains_and_keywords)} domains")
        print("-" * len(category))

        # Sort by frequency to see most common potentially wrong mappings
        domains_sorted = sorted(
            domains_and_keywords, key=lambda x: domain_frequencies[x[0]], reverse=True
        )

        for domain_name, matched_keywords in domains_sorted:
            freq = domain_frequencies[domain_name]
            print(f"  {domain_name} ({freq} papers) - matched: {matched_keywords}")

            # Flag suspicious mappings
            if category == "Computer Vision & Medical Imaging":
                # Check for non-CV domains that got CV keywords
                if any(
                    suspicious in domain_name.lower()
                    for suspicious in [
                        "language",
                        "text",
                        "nlp",
                        "linguistic",
                        "dialogue",
                        "speech",
                        "reinforcement",
                        "policy",
                        "agent",
                        "graph",
                        "network",
                        "node",
                    ]
                ):
                    suspicious_mappings.append(
                        (domain_name, category, matched_keywords, freq)
                    )

            elif category == "Natural Language Processing":
                # Check for non-NLP domains
                if any(
                    suspicious in domain_name.lower()
                    for suspicious in [
                        "vision",
                        "image",
                        "visual",
                        "segmentation",
                        "detection",
                        "reinforcement",
                        "policy",
                        "agent",
                        "robotics",
                        "control",
                        "graph",
                        "network",
                        "node",
                        "edge",
                    ]
                ):
                    suspicious_mappings.append(
                        (domain_name, category, matched_keywords, freq)
                    )

            elif category == "Reinforcement Learning & Robotics":
                # Check for non-RL domains
                if any(
                    suspicious in domain_name.lower()
                    for suspicious in [
                        "vision",
                        "image",
                        "visual",
                        "language",
                        "text",
                        "nlp",
                        "graph",
                        "network",
                        "node",
                        "edge",
                    ]
                ):
                    suspicious_mappings.append(
                        (domain_name, category, matched_keywords, freq)
                    )

            elif category == "Graph Learning & Network Analysis":
                # Check for non-graph domains
                if any(
                    suspicious in domain_name.lower()
                    for suspicious in [
                        "vision",
                        "image",
                        "visual",
                        "language",
                        "text",
                        "nlp",
                        "reinforcement",
                        "policy",
                        "agent",
                        "robotics",
                    ]
                ):
                    suspicious_mappings.append(
                        (domain_name, category, matched_keywords, freq)
                    )

    # Report suspicious mappings
    print("\nSUSPICIOUS DOMAIN MAPPINGS:")
    print("=" * 30)

    if suspicious_mappings:
        suspicious_mappings.sort(key=lambda x: x[3], reverse=True)  # Sort by frequency
        for domain_name, category, matched_keywords, freq in suspicious_mappings:
            print(f"⚠️  {domain_name} ({freq} papers)")
            print(f"    → Mapped to: {category}")
            print(f"    → Matched keywords: {matched_keywords}")
            print()
    else:
        print("No obviously suspicious mappings detected.")

    # Check for potential ambiguous domains
    print("\nAMBIGUOUS DOMAINS (multiple keyword matches):")
    print("=" * 45)

    ambiguous_domains = []
    all_keywords = {
        "CV": cv_keywords,
        "NLP": nlp_keywords,
        "RL": rl_keywords,
        "Graph": graph_keywords,
    }

    for domain_name in unique_domains:
        if domain_name not in manually_mapped:
            domain_lower = domain_name.lower()
            matches = []

            for area, keywords in all_keywords.items():
                if any(kw in domain_lower for kw in keywords):
                    matched_kws = [kw for kw in keywords if kw in domain_lower]
                    matches.append((area, matched_kws))

            if len(matches) > 1:
                freq = domain_frequencies[domain_name]
                current_category = domain_to_category[domain_name]
                ambiguous_domains.append((domain_name, matches, current_category, freq))

    if ambiguous_domains:
        ambiguous_domains.sort(key=lambda x: x[3], reverse=True)
        for domain_name, matches, current_category, freq in ambiguous_domains:
            print(f"🤔 {domain_name} ({freq} papers)")
            print(f"    → Currently mapped to: {current_category}")
            print(f"    → Potential matches: {matches}")
            print()
    else:
        print("No ambiguous domains found.")

    # Save results
    results = {
        "total_domains": len(unique_domains),
        "manually_mapped": len(manually_mapped),
        "auto_mapped": len(unique_domains) - len(manually_mapped),
        "suspicious_mappings": [
            {
                "domain": domain,
                "mapped_to": category,
                "matched_keywords": keywords,
                "frequency": freq,
            }
            for domain, category, keywords, freq in suspicious_mappings
        ],
        "ambiguous_domains": [
            {
                "domain": domain,
                "potential_matches": matches,
                "current_category": category,
                "frequency": freq,
            }
            for domain, matches, category, freq in ambiguous_domains
        ],
    }

    with open("domain_mapping_sanity_check_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to: domain_mapping_sanity_check_results.json")

    return suspicious_mappings, ambiguous_domains


if __name__ == "__main__":
    suspicious, ambiguous = analyze_domain_mappings()
