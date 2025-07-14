#!/usr/bin/env python3
"""
Detailed analysis of RL papers looking at actual subdomains (not just main categories)
and better theoretical vs empirical classification.
"""

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def load_data():
    """Load required data."""

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    return raw_domains, research_data


def identify_rl_papers_with_subdomains():
    """Identify RL papers and their specific subdomains."""

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    raw_domains, research_data = load_data()

    print("=== IDENTIFYING RL PAPERS WITH DETAILED SUBDOMAINS ===\n")

    # Get all papers with RL research domains and their actual subdomains
    rl_papers = {}  # paper_id -> {title, year, subdomains: []}

    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]

        # Find category for this domain
        for class_domain, info in research_data["classification"].items():
            if class_domain == domain_name:
                category = info["category"]
                if category == "Reinforcement Learning & Robotics":
                    if paper_id not in rl_papers:
                        rl_papers[paper_id] = {
                            "title": domain_entry["title"],
                            "year": domain_entry["year"],
                            "subdomains": [],
                        }
                    rl_papers[paper_id]["subdomains"].append(domain_name)
                break

    print(f"Found {len(rl_papers)} papers with RL research domains")

    # Check which have datasets/environments using enhanced detection
    rl_keywords = [
        "atari",
        "gym",
        "openai gym",
        "gymnasium",
        "mujoco",
        "dm control",
        "deepmind lab",
        "starcraft",
        "dota",
        "minecraft",
        "procgen",
        "halfcheetah",
        "hopper",
        "walker",
        "ant",
        "humanoid",
        "cartpole",
        "cart-pole",
        "mountain car",
        "acrobot",
        "lunar lander",
        "bipedal walker",
        "car racing",
        "environment",
        "simulator",
        "simulation",
        "policy",
        "reward",
        "agent",
        "episode",
        "trajectory",
        "q-learning",
        "policy gradient",
        "actor-critic",
        "ppo",
        "sac",
        "ddpg",
        "td3",
        "dqn",
    ]

    # Create paper lookup
    paper_lookup = {paper["paper_id"]: paper for paper in papers_data}

    rl_with_data = {}
    rl_without_data = {}

    for paper_id, rl_info in rl_papers.items():
        paper_json = paper_lookup.get(paper_id)
        if not paper_json:
            rl_without_data[paper_id] = rl_info
            continue

        try:
            paper = Paper(paper_json)
            if not paper.queries:
                rl_without_data[paper_id] = rl_info
                continue

            # Load analysis
            with open(paper.queries[0], "r") as f:
                analysis_data = json.load(f)

            extractions = analysis_data.get("extractions", {})
            if not extractions:
                rl_without_data[paper_id] = rl_info
                continue

            # Check for datasets and environments
            has_rl_data = False

            # Check datasets
            datasets = extractions.get("datasets", [])
            for dataset in datasets:
                if isinstance(dataset, dict) and "name" in dataset:
                    name_data = dataset["name"]
                    if isinstance(name_data, dict):
                        dataset_text = (
                            name_data.get("value", "")
                            + " "
                            + name_data.get("justification", "")
                        ).lower()
                        if any(keyword in dataset_text for keyword in rl_keywords):
                            has_rl_data = True
                            break

            # Check description for environments
            if not has_rl_data:
                description = extractions.get("description", {})
                if isinstance(description, dict):
                    desc_text = (
                        description.get("value", "")
                        + " "
                        + description.get("justification", "")
                    ).lower()

                    rl_matches = sum(
                        1 for keyword in rl_keywords if keyword in desc_text
                    )
                    if rl_matches >= 2:  # Require at least 2 RL keywords
                        has_rl_data = True

            if has_rl_data:
                rl_with_data[paper_id] = rl_info
            else:
                rl_without_data[paper_id] = rl_info

        except Exception:
            rl_without_data[paper_id] = rl_info
            continue

    print(f"RL with datasets/environments: {len(rl_with_data)}")
    print(f"RL without datasets/environments: {len(rl_without_data)}")

    return rl_with_data, rl_without_data, paper_lookup


def analyze_rl_subdomains(rl_with_data, rl_without_data):
    """Analyze specific RL subdomains to see patterns."""

    print("\n=== RL SUBDOMAIN ANALYSIS ===\n")

    # Count subdomains for each group
    subdomains_with_data = defaultdict(int)
    subdomains_without_data = defaultdict(int)

    for paper_id, info in rl_with_data.items():
        for subdomain in info["subdomains"]:
            subdomains_with_data[subdomain] += 1

    for paper_id, info in rl_without_data.items():
        for subdomain in info["subdomains"]:
            subdomains_without_data[subdomain] += 1

    # Get all unique subdomains
    all_subdomains = set(subdomains_with_data.keys()) | set(
        subdomains_without_data.keys()
    )

    print("RL SUBDOMAINS - With vs Without Datasets/Environments:")
    print("=" * 90)
    print(
        f"{'Subdomain':<40} {'With Data':<12} {'Without Data':<12} {'Total':<8} {'% With Data':<12}"
    )
    print("=" * 90)

    subdomain_analysis = []

    for subdomain in sorted(all_subdomains):
        with_count = subdomains_with_data.get(subdomain, 0)
        without_count = subdomains_without_data.get(subdomain, 0)
        total_count = with_count + without_count

        if total_count > 0:
            pct_with_data = (with_count / total_count) * 100
        else:
            pct_with_data = 0

        subdomain_analysis.append(
            {
                "subdomain": subdomain,
                "with_data": with_count,
                "without_data": without_count,
                "total": total_count,
                "pct_with_data": pct_with_data,
            }
        )

        print(
            f"{subdomain:<40} {with_count:<12} {without_count:<12} {total_count:<8} {pct_with_data:<11.1f}%"
        )

    print("=" * 90)

    # Identify patterns - which subdomains are more likely to use datasets/environments?
    print("\nPATTERNS - RL Subdomains Most Likely to Use Datasets/Environments:")
    print("-" * 70)

    # Sort by percentage with data (for subdomains with at least 5 papers)
    significant_subdomains = [s for s in subdomain_analysis if s["total"] >= 5]
    significant_subdomains.sort(key=lambda x: x["pct_with_data"], reverse=True)

    for i, sub in enumerate(significant_subdomains[:10]):
        print(
            f"  {i + 1}. {sub['subdomain']}: {sub['pct_with_data']:.1f}% ({sub['with_data']}/{sub['total']} papers)"
        )

    print("\nPATTERNS - RL Subdomains Least Likely to Use Datasets/Environments:")
    print("-" * 70)

    for i, sub in enumerate(significant_subdomains[-10:]):
        print(
            f"  {i + 1}. {sub['subdomain']}: {sub['pct_with_data']:.1f}% ({sub['with_data']}/{sub['total']} papers)"
        )

    return subdomain_analysis


def improved_theoretical_empirical_classification(
    rl_with_data, rl_without_data, paper_lookup
):
    """Improved classification of theoretical vs empirical papers."""

    print("\n=== IMPROVED THEORETICAL VS EMPIRICAL ANALYSIS ===\n")

    # Enhanced keyword lists
    strong_theoretical_indicators = [
        "theorem",
        "lemma",
        "proof",
        "corollary",
        "proposition",
        "convergence analysis",
        "regret bound",
        "sample complexity",
        "pac learning",
        "probably approximately correct",
        "theoretical analysis",
        "theoretical guarantee",
        "mathematical framework",
        "formal analysis",
    ]

    weak_theoretical_indicators = [
        "theoretical",
        "theory",
        "mathematical",
        "analysis",
        "bound",
        "complexity",
        "optimal",
        "optimality",
        "regret",
        "convergence",
    ]

    strong_empirical_indicators = [
        "experiment",
        "evaluation",
        "benchmark",
        "dataset",
        "training",
        "testing",
        "validation",
        "results",
        "performance",
        "comparison",
        "ablation",
        "baseline",
    ]

    weak_empirical_indicators = [
        "empirical",
        "experimental",
        "evaluate",
        "train",
        "test",
        "validate",
        "compare",
        "measure",
    ]

    def classify_paper_enhanced(paper_id):
        """Enhanced classification using multiple criteria."""

        try:
            paper_json = paper_lookup.get(paper_id)
            if not paper_json:
                return "unknown"

            paper = Paper(paper_json)
            if not paper.queries:
                return "unknown"

            with open(paper.queries[0], "r") as f:
                analysis_data = json.load(f)

            extractions = analysis_data.get("extractions", {})

            # Get all text sources
            text_sources = []

            # Title
            title = paper_json.get("title", "").lower()
            text_sources.append(title)

            # Description
            description = extractions.get("description", {})
            if isinstance(description, dict):
                text_sources.append(description.get("value", "").lower())
                text_sources.append(description.get("justification", "").lower())

            # Methods
            methods = extractions.get("methods", [])
            for method in methods:
                if isinstance(method, dict) and "name" in method:
                    name_data = method["name"]
                    if isinstance(name_data, dict):
                        text_sources.append(name_data.get("value", "").lower())
                        text_sources.append(name_data.get("justification", "").lower())

            full_text = " ".join(text_sources)

            # Count strong indicators
            strong_theoretical = sum(
                1
                for indicator in strong_theoretical_indicators
                if indicator in full_text
            )
            strong_empirical = sum(
                1 for indicator in strong_empirical_indicators if indicator in full_text
            )

            # Count weak indicators
            weak_theoretical = sum(
                1 for indicator in weak_theoretical_indicators if indicator in full_text
            )
            weak_empirical = sum(
                1 for indicator in weak_empirical_indicators if indicator in full_text
            )

            # Scoring system
            theoretical_score = strong_theoretical * 3 + weak_theoretical * 1
            empirical_score = strong_empirical * 3 + weak_empirical * 1

            # Check for datasets (strong empirical indicator)
            datasets = extractions.get("datasets", [])
            if datasets:
                empirical_score += 5

            # Classification logic
            if theoretical_score >= 6 and theoretical_score > empirical_score:
                return "theoretical"
            elif empirical_score >= 6 and empirical_score > theoretical_score:
                return "empirical"
            elif (
                abs(theoretical_score - empirical_score) <= 2
                and max(theoretical_score, empirical_score) >= 4
            ):
                return "mixed"
            elif theoretical_score >= 3 or empirical_score >= 3:
                return (
                    "theoretical"
                    if theoretical_score > empirical_score
                    else "empirical"
                )
            else:
                return "unclear"

        except Exception:
            return "error"

    # Classify papers in each group
    with_data_classification = defaultdict(int)
    without_data_classification = defaultdict(int)

    print("Classifying papers with enhanced method...")

    for paper_id in rl_with_data.keys():
        classification = classify_paper_enhanced(paper_id)
        with_data_classification[classification] += 1

    for paper_id in rl_without_data.keys():
        classification = classify_paper_enhanced(paper_id)
        without_data_classification[classification] += 1

    print(f"\nRL papers WITH datasets/environments ({len(rl_with_data)} total):")
    print("-" * 50)
    for paper_type, count in sorted(
        with_data_classification.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / len(rl_with_data) * 100
        print(f"  {paper_type}: {count} papers ({pct:.1f}%)")

    print(f"\nRL papers WITHOUT datasets/environments ({len(rl_without_data)} total):")
    print("-" * 50)
    for paper_type, count in sorted(
        without_data_classification.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / len(rl_without_data) * 100
        print(f"  {paper_type}: {count} papers ({pct:.1f}%)")

    # Verify totals add up
    total_with = sum(with_data_classification.values())
    total_without = sum(without_data_classification.values())

    print("\nVERIFICATION:")
    print(
        f"  Papers with data classified: {total_with} (should be {len(rl_with_data)})"
    )
    print(
        f"  Papers without data classified: {total_without} (should be {len(rl_without_data)})"
    )

    # Compare patterns
    print("\nCOMPARISON:")
    print("=" * 60)
    print(f"{'Type':<12} {'With Data':<15} {'Without Data':<15} {'Difference':<12}")
    print("=" * 60)

    all_types = set(with_data_classification.keys()) | set(
        without_data_classification.keys()
    )

    for paper_type in sorted(all_types):
        with_pct = with_data_classification.get(paper_type, 0) / len(rl_with_data) * 100
        without_pct = (
            without_data_classification.get(paper_type, 0) / len(rl_without_data) * 100
        )
        diff = with_pct - without_pct

        print(
            f"{paper_type:<12} {with_pct:<14.1f}% {without_pct:<14.1f}% {diff:+<11.1f}%"
        )

    return with_data_classification, without_data_classification


def sample_papers_by_subdomain(rl_with_data, rl_without_data, subdomain_analysis):
    """Show sample papers from key subdomains."""

    print("\n=== SAMPLE PAPERS BY SUBDOMAIN ===\n")

    # Get subdomains with interesting patterns
    significant_subdomains = [s for s in subdomain_analysis if s["total"] >= 5]
    top_computational = [s for s in significant_subdomains if s["pct_with_data"] > 50]
    top_theoretical = [s for s in significant_subdomains if s["pct_with_data"] < 20]

    print("Sample papers from COMPUTATIONAL-HEAVY subdomains:")
    print("-" * 60)

    for subdomain_info in top_computational[:3]:
        subdomain = subdomain_info["subdomain"]
        print(f"\n{subdomain} ({subdomain_info['pct_with_data']:.1f}% with data):")

        sample_papers = []
        for paper_id, info in rl_with_data.items():
            if subdomain in info["subdomains"]:
                sample_papers.append(info)
                if len(sample_papers) >= 3:
                    break

        for i, paper in enumerate(sample_papers):
            print(f"  {i + 1}. {paper['title'][:70]}... ({paper['year']})")

    print("\n\nSample papers from THEORETICAL-HEAVY subdomains:")
    print("-" * 60)

    for subdomain_info in top_theoretical[:3]:
        subdomain = subdomain_info["subdomain"]
        print(f"\n{subdomain} ({subdomain_info['pct_with_data']:.1f}% with data):")

        sample_papers = []
        for paper_id, info in rl_without_data.items():
            if subdomain in info["subdomains"]:
                sample_papers.append(info)
                if len(sample_papers) >= 3:
                    break

        for i, paper in enumerate(sample_papers):
            print(f"  {i + 1}. {paper['title'][:70]}... ({paper['year']})")


def main():
    """Run detailed RL subdomain analysis."""

    print("DETAILED RL SUBDOMAIN ANALYSIS\n")

    # 1. Identify RL papers with detailed subdomains
    rl_with_data, rl_without_data, paper_lookup = identify_rl_papers_with_subdomains()

    # 2. Analyze specific RL subdomains
    subdomain_analysis = analyze_rl_subdomains(rl_with_data, rl_without_data)

    # 3. Improved theoretical vs empirical classification
    with_data_classification, without_data_classification = (
        improved_theoretical_empirical_classification(
            rl_with_data, rl_without_data, paper_lookup
        )
    )

    # 4. Show sample papers by subdomain
    sample_papers_by_subdomain(rl_with_data, rl_without_data, subdomain_analysis)

    # Save results
    results = {
        "rl_with_data_count": len(rl_with_data),
        "rl_without_data_count": len(rl_without_data),
        "subdomain_analysis": subdomain_analysis,
        "enhanced_classification": {
            "with_data": dict(with_data_classification),
            "without_data": dict(without_data_classification),
        },
    }

    with open("detailed_rl_subdomain_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n\nResults saved to detailed_rl_subdomain_analysis.json")

    return results


if __name__ == "__main__":
    results = main()
