#!/usr/bin/env python3
"""
Implement multi-domain support for papers - allowing papers to belong to multiple research domains.
This addresses the issue that research domains are not mutually exclusive.
"""

import json
import sys
from collections import defaultdict, Counter

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")


def extract_multi_domain_classifications():
    """Re-extract classifications allowing multiple domains per paper."""

    # Load the raw domain data
    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    # Load existing taxonomy for classification
    with open("mila_domain_taxonomy.json", "r") as f:
        taxonomy_data = json.load(f)

    taxonomy = taxonomy_data["taxonomy"]

    print("=== MULTI-DOMAIN CLASSIFICATION ANALYSIS ===\\n")

    # Group domains by paper
    papers_domains = defaultdict(list)
    for domain_entry in raw_domains:
        papers_domains[domain_entry["paper_id"]].append(domain_entry)

    # Classify each paper allowing multiple domains
    multi_domain_classifications = {}
    domain_combinations = Counter()

    for paper_id, domain_entries in papers_domains.items():
        paper_domains = set()

        # Get paper info
        paper_info = {
            "title": domain_entries[0]["title"],
            "year": domain_entries[0]["year"],
            "domain_entries": [],
        }

        # Classify each domain entry
        for domain_entry in domain_entries:
            domain_name = domain_entry["domain_name"]
            domain_text = domain_name.lower()

            # Add context from justifications
            if domain_entry.get("justification"):
                domain_text += " " + domain_entry["justification"].lower()
            if domain_entry.get("quote"):
                domain_text += " " + domain_entry["quote"].lower()

            # Find matching categories
            matched_categories = []
            for category, info in taxonomy.items():
                matches = sum(
                    1 for keyword in info["keywords"] if keyword in domain_text
                )
                if matches > 0:
                    matched_categories.append((category, matches))

            # Sort by match strength and take top matches
            matched_categories.sort(key=lambda x: x[1], reverse=True)

            # Add top matching categories (allow multiple if strong matches)
            for category, matches in matched_categories:
                if matches >= 1:  # At least 1 keyword match
                    paper_domains.add(category)
                    paper_info["domain_entries"].append(
                        {
                            "domain_name": domain_name,
                            "category": category,
                            "matches": matches,
                            "type": domain_entry["domain_type"],
                        }
                    )

        if paper_domains:
            multi_domain_classifications[paper_id] = {
                "title": paper_info["title"],
                "year": paper_info["year"],
                "domains": list(paper_domains),
                "domain_count": len(paper_domains),
                "domain_entries": paper_info["domain_entries"],
            }

            # Track domain combinations
            domain_combo = tuple(sorted(paper_domains))
            domain_combinations[domain_combo] += 1

    print(
        f"Papers with multi-domain classification: {len(multi_domain_classifications)}"
    )

    # Analyze domain distributions
    domain_counts = defaultdict(int)
    for paper_id, info in multi_domain_classifications.items():
        for domain in info["domains"]:
            domain_counts[domain] += 1

    print("\\nDomain distribution (allowing multiple domains per paper):")
    total_domain_assignments = sum(domain_counts.values())
    for domain, count in sorted(
        domain_counts.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = count / len(multi_domain_classifications) * 100
        print(f"  {domain}: {count} papers ({percentage:.1f}% of papers)")

    print(f"\\nTotal domain assignments: {total_domain_assignments}")
    print(
        f"Average domains per paper: {total_domain_assignments / len(multi_domain_classifications):.2f}"
    )

    # Analyze multi-domain papers
    multi_domain_papers = {
        pid: info
        for pid, info in multi_domain_classifications.items()
        if info["domain_count"] > 1
    }

    print(
        f"\\nPapers with multiple domains: {len(multi_domain_papers)} ({len(multi_domain_papers) / len(multi_domain_classifications) * 100:.1f}%)"
    )

    # Show most common domain combinations
    print("\\nMost common domain combinations:")
    for combo, count in domain_combinations.most_common(15):
        if len(combo) > 1:  # Only show multi-domain combinations
            combo_str = " + ".join(combo)
            print(f"  {combo_str}: {count} papers")

    return multi_domain_classifications, domain_counts, multi_domain_papers


def analyze_interdisciplinary_patterns():
    """Analyze patterns in interdisciplinary research."""

    multi_classifications, domain_counts, multi_papers = (
        extract_multi_domain_classifications()
    )

    print("\\n=== INTERDISCIPLINARY RESEARCH PATTERNS ===\\n")

    # Analyze co-occurrence patterns
    cooccurrence = defaultdict(lambda: defaultdict(int))

    for paper_id, info in multi_papers.items():
        domains = info["domains"]
        for i, domain1 in enumerate(domains):
            for domain2 in domains[i + 1 :]:
                cooccurrence[domain1][domain2] += 1
                cooccurrence[domain2][domain1] += 1

    # Find strongest interdisciplinary connections
    print("Strongest interdisciplinary connections:")
    connection_strengths = []
    for domain1, connections in cooccurrence.items():
        for domain2, count in connections.items():
            if domain1 < domain2:  # Avoid duplicates
                strength = (
                    count / min(domain_counts[domain1], domain_counts[domain2]) * 100
                )
                connection_strengths.append((domain1, domain2, count, strength))

    connection_strengths.sort(key=lambda x: x[3], reverse=True)

    for domain1, domain2, count, strength in connection_strengths[:10]:
        print(
            f"  {domain1} ↔ {domain2}: {count} papers ({strength:.1f}% connection rate)"
        )

    # Analyze by year to see evolution of interdisciplinary work
    yearly_multi_domain = defaultdict(list)
    for paper_id, info in multi_papers.items():
        if info["year"]:
            yearly_multi_domain[info["year"]].append(info["domain_count"])

    print("\\nEvolution of interdisciplinary research:")
    for year in sorted(yearly_multi_domain.keys()):
        papers = yearly_multi_domain[year]
        avg_domains = sum(papers) / len(papers)
        print(
            f"  {year}: {len(papers)} multi-domain papers, avg {avg_domains:.2f} domains/paper"
        )

    return cooccurrence, connection_strengths


def compare_single_vs_multi_domain():
    """Compare single-domain vs multi-domain classification results."""

    print("\\n=== SINGLE VS MULTI-DOMAIN COMPARISON ===\\n")

    # Load original single-domain results
    with open("mila_domain_taxonomy.json", "r") as f:
        original_data = json.load(f)

    original_stats = original_data["category_stats"]

    # Get multi-domain results
    multi_classifications, multi_domain_counts, multi_papers = (
        extract_multi_domain_classifications()
    )

    print("Comparison of classification methods:")
    print("-" * 80)
    print(
        f"{'Domain':<35} {'Single':<10} {'Multi':<10} {'Difference':<12} {'Multi %':<10}"
    )
    print("-" * 80)

    total_papers_multi = len(multi_classifications)
    total_papers_single = sum(original_stats.values())

    for domain in sorted(multi_domain_counts.keys()):
        single_count = original_stats.get(domain, 0)
        multi_count = multi_domain_counts[domain]
        difference = multi_count - single_count
        multi_pct = multi_count / total_papers_multi * 100

        print(
            f"{domain:<35} {single_count:<10} {multi_count:<10} {difference:+<12} {multi_pct:<10.1f}%"
        )

    print("-" * 80)
    print(
        f"{'TOTAL':<35} {total_papers_single:<10} {sum(multi_domain_counts.values()):<10}"
    )

    # Calculate inflation factor
    inflation_factor = sum(multi_domain_counts.values()) / total_papers_single
    print(f"\\nDomain assignment inflation factor: {inflation_factor:.2f}")
    print(
        f"This means multi-domain classification assigns {inflation_factor:.1f}x more domain labels"
    )

    return {
        "single_domain_stats": original_stats,
        "multi_domain_stats": dict(multi_domain_counts),
        "inflation_factor": inflation_factor,
        "total_papers": total_papers_multi,
    }


def create_corrected_multi_domain_stats():
    """Create final corrected statistics combining multi-domain + dataset corrections."""

    print("\\n=== FINAL CORRECTED STATISTICS ===\\n")

    # Load correction factors
    with open("correction_factors.json", "r") as f:
        correction_data = json.load(f)

    # Get multi-domain stats
    comparison = compare_single_vs_multi_domain()
    multi_stats = comparison["multi_domain_stats"]
    inflation_factor = comparison["inflation_factor"]

    # Apply dataset-based corrections to multi-domain stats
    method2_corrections = correction_data["corrected_method2"]

    print("Final corrected domain statistics:")
    print("=" * 100)
    print(
        f"{'Domain':<35} {'Original':<12} {'Multi-Only':<12} {'Dataset+Multi':<15} {'Final %':<10}"
    )
    print("=" * 100)

    final_corrected_stats = {}

    for domain in method2_corrections.keys():
        original = correction_data["original_stats"].get(domain, 0)
        multi_only = multi_stats.get(domain, 0)

        # Apply both multi-domain and dataset corrections
        # Use the dataset correction factor but account for multi-domain inflation
        dataset_corrected = method2_corrections[domain]
        multi_adjusted = (
            dataset_corrected * (multi_only / original) if original > 0 else multi_only
        )

        final_corrected_stats[domain] = multi_adjusted

    total_final = sum(final_corrected_stats.values())

    for domain in sorted(
        final_corrected_stats.keys(),
        key=lambda x: final_corrected_stats[x],
        reverse=True,
    ):
        original = correction_data["original_stats"].get(domain, 0)
        multi_only = multi_stats.get(domain, 0)
        final_count = final_corrected_stats[domain]
        final_pct = final_count / total_final * 100

        print(
            f"{domain:<35} {original:<12} {multi_only:<12} {final_count:<15.0f} {final_pct:<10.1f}%"
        )

    print("=" * 100)
    print(
        f"{'TOTAL':<35} {sum(correction_data['original_stats'].values()):<12} {sum(multi_stats.values()):<12} {total_final:<15.0f} {'100.0':<10}%"
    )

    # Save final results
    final_results = {
        "final_corrected_stats": final_corrected_stats,
        "methodology": "Multi-domain classification + Dataset-based corrections",
        "inflation_factor": inflation_factor,
        "total_papers": total_final,
        "corrections_applied": [
            "Multi-domain support",
            "Dataset detection rate adjustment",
            "Proportional scaling",
        ],
    }

    with open("final_corrected_domain_stats.json", "w") as f:
        json.dump(final_results, f, indent=2)

    print("\\nFinal results saved to final_corrected_domain_stats.json")

    return final_results


def main():
    """Run complete multi-domain analysis."""

    print("Implementing multi-domain support for research domain classification...\\n")

    # 1. Extract multi-domain classifications
    multi_classifications, domain_counts, multi_papers = (
        extract_multi_domain_classifications()
    )

    # 2. Analyze interdisciplinary patterns
    cooccurrence, connections = analyze_interdisciplinary_patterns()

    # 3. Compare single vs multi-domain approaches
    comparison = compare_single_vs_multi_domain()

    # 4. Create final corrected statistics
    final_results = create_corrected_multi_domain_stats()

    print("\\n=== KEY INSIGHTS ===")
    print(
        f"1. {len(multi_papers)} papers ({len(multi_papers) / len(multi_classifications) * 100:.1f}%) are interdisciplinary"
    )
    print(
        f"2. Average domains per paper: {sum(domain_counts.values()) / len(multi_classifications):.2f}"
    )
    print(f"3. Domain assignment inflation: {comparison['inflation_factor']:.2f}x")
    print(
        "4. Multi-domain approach provides more accurate representation of research breadth"
    )

    return final_results


if __name__ == "__main__":
    results = main()
