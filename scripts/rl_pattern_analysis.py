#!/usr/bin/env python3
"""
Analyze patterns in RL papers: those with research domains but no datasets/environments
vs those with both. Look at other research domains and theoretical vs empirical nature.
"""

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def load_required_data():
    """Load all required analysis data."""

    # Load research domain data
    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    # Load critical agreement analysis
    with open("critical_agreement_analysis.json", "r") as f:
        agreement_data = json.load(f)

    return raw_domains, research_data, agreement_data


def identify_rl_paper_groups():
    """Identify RL papers with and without datasets/environments."""

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    raw_domains, research_data, agreement_data = load_required_data()

    print("=== IDENTIFYING RL PAPER GROUPS ===\n")

    # Get all papers with RL research domains
    rl_research_papers = set()
    paper_research_domains = defaultdict(set)

    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        domain_name = domain_entry["domain_name"]

        # Find category for this domain
        for class_domain, info in research_data["classification"].items():
            if class_domain == domain_name:
                category = info["category"]
                paper_research_domains[paper_id].add(category)
                if category == "Reinforcement Learning & Robotics":
                    rl_research_papers.add(paper_id)
                break

    print(f"Papers with RL research domains: {len(rl_research_papers)}")

    # Now check which of these have datasets/environments
    rl_with_datasets_envs = set()
    rl_without_datasets_envs = set()

    # Keywords for RL environments/datasets
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

    papers_processed = 0

    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(f"Processing paper {i}/{len(papers_data)}")

        paper_id = paper_json.get("paper_id", "")
        if paper_id not in rl_research_papers:
            continue

        try:
            paper = Paper(paper_json)
            if not paper.queries:
                rl_without_datasets_envs.add(paper_id)
                continue

            papers_processed += 1

            # Load analysis
            with open(paper.queries[0], "r") as f:
                analysis_data = json.load(f)

            extractions = analysis_data.get("extractions", {})
            if not extractions:
                rl_without_datasets_envs.add(paper_id)
                continue

            # Check for datasets
            has_rl_data = False
            datasets = extractions.get("datasets", [])

            # Check datasets
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
                rl_with_datasets_envs.add(paper_id)
            else:
                rl_without_datasets_envs.add(paper_id)

        except Exception:
            rl_without_datasets_envs.add(paper_id)
            continue

    print("\nRL PAPER GROUPS:")
    print(f"RL with datasets/environments: {len(rl_with_datasets_envs)}")
    print(f"RL without datasets/environments: {len(rl_without_datasets_envs)}")
    print(
        f"Total RL papers: {len(rl_with_datasets_envs) + len(rl_without_datasets_envs)}"
    )

    return rl_with_datasets_envs, rl_without_datasets_envs, paper_research_domains


def analyze_other_research_domains(
    rl_with_data, rl_without_data, paper_research_domains
):
    """Analyze what other research domains these RL papers have."""

    print("\n=== OTHER RESEARCH DOMAINS ANALYSIS ===\n")

    # Analyze other domains for each group
    other_domains_with_data = defaultdict(int)
    other_domains_without_data = defaultdict(int)

    for paper_id in rl_with_data:
        domains = paper_research_domains.get(paper_id, set())
        for domain in domains:
            if domain != "Reinforcement Learning & Robotics":
                other_domains_with_data[domain] += 1

    for paper_id in rl_without_data:
        domains = paper_research_domains.get(paper_id, set())
        for domain in domains:
            if domain != "Reinforcement Learning & Robotics":
                other_domains_without_data[domain] += 1

    print("RL papers WITH datasets/environments - Other research domains:")
    print("-" * 60)
    total_with_data = len(rl_with_data)
    for domain, count in sorted(
        other_domains_with_data.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / total_with_data * 100
        print(f"  {domain}: {count} papers ({pct:.1f}%)")

    print("\nRL papers WITHOUT datasets/environments - Other research domains:")
    print("-" * 60)
    total_without_data = len(rl_without_data)
    for domain, count in sorted(
        other_domains_without_data.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / total_without_data * 100
        print(f"  {domain}: {count} papers ({pct:.1f}%)")

    # Compare patterns
    print("\nCOMPARISON - Domain co-occurrence patterns:")
    print("=" * 70)
    print(f"{'Domain':<35} {'With Data':<12} {'Without Data':<12} {'Difference':<12}")
    print("=" * 70)

    all_other_domains = set(other_domains_with_data.keys()) | set(
        other_domains_without_data.keys()
    )

    for domain in sorted(all_other_domains):
        with_pct = other_domains_with_data.get(domain, 0) / total_with_data * 100
        without_pct = (
            other_domains_without_data.get(domain, 0) / total_without_data * 100
        )
        diff = with_pct - without_pct

        print(f"{domain:<35} {with_pct:<11.1f}% {without_pct:<11.1f}% {diff:+<11.1f}%")

    return other_domains_with_data, other_domains_without_data


def analyze_theoretical_vs_empirical(rl_with_data, rl_without_data):
    """Analyze theoretical vs empirical nature of papers in each group."""

    print("\n=== THEORETICAL VS EMPIRICAL ANALYSIS ===\n")

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    # Create paper lookup
    paper_lookup = {paper["paper_id"]: paper for paper in papers_data}

    theoretical_indicators = [
        "theoretical",
        "theory",
        "mathematical",
        "proof",
        "theorem",
        "lemma",
        "analysis",
        "convergence",
        "bound",
        "complexity",
        "optimal",
        "optimality",
        "regret",
        "sample complexity",
        "pac",
        "probably approximately correct",
    ]

    empirical_indicators = [
        "experiment",
        "empirical",
        "evaluation",
        "benchmark",
        "performance",
        "results",
        "comparison",
        "ablation",
        "baseline",
        "state-of-the-art",
        "dataset",
        "training",
        "testing",
        "validation",
    ]

    def classify_paper_type(paper_id):
        """Classify paper as theoretical, empirical, or mixed."""

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

            # Get all text
            text_sources = []

            # Description
            description = extractions.get("description", {})
            if isinstance(description, dict):
                text_sources.append(description.get("value", ""))
                text_sources.append(description.get("justification", ""))

            # Models
            models = extractions.get("models", [])
            for model in models:
                if isinstance(model, dict) and "name" in model:
                    name_data = model["name"]
                    if isinstance(name_data, dict):
                        text_sources.append(name_data.get("value", ""))
                        text_sources.append(name_data.get("justification", ""))

            # Methods
            methods = extractions.get("methods", [])
            for method in methods:
                if isinstance(method, dict) and "name" in method:
                    name_data = method["name"]
                    if isinstance(name_data, dict):
                        text_sources.append(name_data.get("value", ""))
                        text_sources.append(name_data.get("justification", ""))

            full_text = " ".join(text_sources).lower()

            theoretical_matches = sum(
                1 for indicator in theoretical_indicators if indicator in full_text
            )
            empirical_matches = sum(
                1 for indicator in empirical_indicators if indicator in full_text
            )

            if theoretical_matches > empirical_matches and theoretical_matches >= 2:
                return "theoretical"
            elif empirical_matches > theoretical_matches and empirical_matches >= 2:
                return "empirical"
            elif theoretical_matches >= 2 and empirical_matches >= 2:
                return "mixed"
            else:
                return "unclear"

        except Exception:
            return "error"

    # Classify papers in each group
    print("Classifying papers by theoretical vs empirical nature...")

    with_data_types = defaultdict(int)
    without_data_types = defaultdict(int)

    for paper_id in rl_with_data:
        paper_type = classify_paper_type(paper_id)
        with_data_types[paper_type] += 1

    for paper_id in rl_without_data:
        paper_type = classify_paper_type(paper_id)
        without_data_types[paper_type] += 1

    print("\nRL papers WITH datasets/environments:")
    print("-" * 40)
    total_with = len(rl_with_data)
    for paper_type, count in sorted(
        with_data_types.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / total_with * 100
        print(f"  {paper_type}: {count} papers ({pct:.1f}%)")

    print("\nRL papers WITHOUT datasets/environments:")
    print("-" * 40)
    total_without = len(rl_without_data)
    for paper_type, count in sorted(
        without_data_types.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / total_without * 100
        print(f"  {paper_type}: {count} papers ({pct:.1f}%)")

    # Statistical comparison
    print("\nCOMPARISON - Paper type distribution:")
    print("=" * 50)
    print(f"{'Type':<12} {'With Data':<12} {'Without Data':<12} {'Difference':<12}")
    print("=" * 50)

    all_types = set(with_data_types.keys()) | set(without_data_types.keys())

    for paper_type in sorted(all_types):
        with_pct = with_data_types.get(paper_type, 0) / total_with * 100
        without_pct = without_data_types.get(paper_type, 0) / total_without * 100
        diff = with_pct - without_pct

        print(
            f"{paper_type:<12} {with_pct:<11.1f}% {without_pct:<11.1f}% {diff:+<11.1f}%"
        )

    return with_data_types, without_data_types


def analyze_sample_papers(rl_with_data, rl_without_data, paper_research_domains):
    """Show sample papers from each group to illustrate patterns."""

    print("\n=== SAMPLE PAPER ANALYSIS ===\n")

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    paper_lookup = {paper["paper_id"]: paper for paper in papers_data}

    def get_paper_info(paper_id):
        """Get basic info about a paper."""
        paper_json = paper_lookup.get(paper_id)
        if not paper_json:
            return None

        title = paper_json.get("title", "Unknown")
        year = None
        for release in paper_json.get("releases", []):
            venue = release.get("venue", {})
            venue_date = venue.get("date", {})
            if isinstance(venue_date, dict) and "text" in venue_date:
                year = venue_date["text"][:4]
                break

        other_domains = [
            d
            for d in paper_research_domains.get(paper_id, set())
            if d != "Reinforcement Learning & Robotics"
        ]

        return {"title": title, "year": year, "other_domains": other_domains}

    print("Sample RL papers WITH datasets/environments:")
    print("-" * 50)

    sample_with = list(rl_with_data)[:5]
    for i, paper_id in enumerate(sample_with):
        info = get_paper_info(paper_id)
        if info:
            print(f"  {i + 1}. {info['title'][:70]}... ({info['year']})")
            if info["other_domains"]:
                print(f"      Other domains: {', '.join(info['other_domains'][:3])}")
            print()

    print("Sample RL papers WITHOUT datasets/environments:")
    print("-" * 50)

    sample_without = list(rl_without_data)[:5]
    for i, paper_id in enumerate(sample_without):
        info = get_paper_info(paper_id)
        if info:
            print(f"  {i + 1}. {info['title'][:70]}... ({info['year']})")
            if info["other_domains"]:
                print(f"      Other domains: {', '.join(info['other_domains'][:3])}")
            print()


def final_pattern_analysis():
    """Provide final analysis of patterns discovered."""

    print("\n=== PATTERN ANALYSIS CONCLUSIONS ===\n")

    rl_with_data, rl_without_data, paper_research_domains = identify_rl_paper_groups()

    other_domains_with, other_domains_without = analyze_other_research_domains(
        rl_with_data, rl_without_data, paper_research_domains
    )

    paper_types_with, paper_types_without = analyze_theoretical_vs_empirical(
        rl_with_data, rl_without_data
    )

    analyze_sample_papers(rl_with_data, rl_without_data, paper_research_domains)

    print("KEY PATTERNS DISCOVERED:")
    print("=" * 40)

    # Pattern 1: Domain co-occurrence
    total_with = len(rl_with_data)
    total_without = len(rl_without_data)

    dl_with_pct = (
        other_domains_with.get("Deep Learning & Neural Architectures", 0)
        / total_with
        * 100
    )
    dl_without_pct = (
        other_domains_without.get("Deep Learning & Neural Architectures", 0)
        / total_without
        * 100
    )

    theory_with_pct = (
        other_domains_with.get("Machine Learning Theory & Methods", 0)
        / total_with
        * 100
    )
    theory_without_pct = (
        other_domains_without.get("Machine Learning Theory & Methods", 0)
        / total_without
        * 100
    )

    print("\n1. DOMAIN CO-OCCURRENCE PATTERNS:")
    print(f"   - RL with data: {dl_with_pct:.1f}% also Deep Learning")
    print(f"   - RL without data: {dl_without_pct:.1f}% also Deep Learning")
    print(f"   - RL with data: {theory_with_pct:.1f}% also ML Theory")
    print(f"   - RL without data: {theory_without_pct:.1f}% also ML Theory")

    # Pattern 2: Theoretical vs empirical
    empirical_with_pct = paper_types_with.get("empirical", 0) / total_with * 100
    empirical_without_pct = (
        paper_types_without.get("empirical", 0) / total_without * 100
    )

    theoretical_with_pct = paper_types_with.get("theoretical", 0) / total_with * 100
    theoretical_without_pct = (
        paper_types_without.get("theoretical", 0) / total_without * 100
    )

    print("\n2. THEORETICAL VS EMPIRICAL:")
    print(
        f"   - RL with data: {empirical_with_pct:.1f}% empirical, {theoretical_with_pct:.1f}% theoretical"
    )
    print(
        f"   - RL without data: {empirical_without_pct:.1f}% empirical, {theoretical_without_pct:.1f}% theoretical"
    )

    # Hypothesis about the gap
    print("\n3. HYPOTHESIS ABOUT RL RESEARCH DOMAIN INFLATION:")
    if theoretical_without_pct > theoretical_with_pct:
        print("   ✅ CONFIRMED: RL research domains include more theoretical work")
        print("   → Theoretical RL papers don't mention datasets/environments")
        print("   → This inflates RL research domain count vs computational workload")
    else:
        print(
            "   ❌ NOT CONFIRMED: Pattern doesn't support theoretical bias hypothesis"
        )

    if dl_with_pct > dl_without_pct:
        print("   ✅ CONFIRMED: Computational RL work overlaps more with Deep Learning")
        print("   → Empirical RL papers use neural networks (datasets + compute)")
        print("   → Pure RL theory papers don't require computational infrastructure")

    # Final computational implications
    print("\n4. COMPUTATIONAL RESOURCE IMPLICATIONS:")
    print(
        f"   - RL papers with datasets/envs: {len(rl_with_data)} ({len(rl_with_data) / (total_with + total_without) * 100:.1f}%)"
    )
    print(
        f"   - RL papers without datasets/envs: {len(rl_without_data)} ({len(rl_without_data) / (total_with + total_without) * 100:.1f}%)"
    )
    print(
        f"   → For compute projections, focus on the {len(rl_with_data)} papers with actual computational work"
    )

    # Save results
    results = {
        "rl_with_data_count": len(rl_with_data),
        "rl_without_data_count": len(rl_without_data),
        "other_domains_with_data": dict(other_domains_with),
        "other_domains_without_data": dict(other_domains_without),
        "paper_types_with_data": dict(paper_types_with),
        "paper_types_without_data": dict(paper_types_without),
        "key_patterns": {
            "deep_learning_with_pct": dl_with_pct,
            "deep_learning_without_pct": dl_without_pct,
            "theory_with_pct": theory_with_pct,
            "theory_without_pct": theory_without_pct,
            "empirical_with_pct": empirical_with_pct,
            "empirical_without_pct": empirical_without_pct,
            "theoretical_with_pct": theoretical_with_pct,
            "theoretical_without_pct": theoretical_without_pct,
        },
    }

    with open("rl_pattern_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to rl_pattern_analysis.json")

    return results


def main():
    """Run complete RL pattern analysis."""

    print("RL PATTERN ANALYSIS: Research domains vs Datasets/Environments\n")

    results = final_pattern_analysis()

    return results


if __name__ == "__main__":
    results = main()
