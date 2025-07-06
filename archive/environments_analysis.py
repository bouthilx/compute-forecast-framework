#!/usr/bin/env python3
"""
Re-analyze including both datasets AND environments to properly capture
RL computational work. This addresses the critical oversight in RL classification.
"""

import json
import sys
from collections import defaultdict, Counter

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def create_enhanced_taxonomy():
    """Create enhanced taxonomy including both datasets and environments."""

    enhanced_taxonomy = {
        "Computer Vision & Medical Imaging": {
            "keywords": [
                # Image datasets
                "imagenet",
                "cifar",
                "mnist",
                "coco",
                "pascal voc",
                "voc",
                "celeba",
                "flickr",
                "places",
                "ade20k",
                "cityscapes",
                "open images",
                "visual genome",
                "kinetics",
                "ucf",
                # Medical imaging datasets
                "mimic",
                "isic",
                "brats",
                "luna",
                "lidc",
                "adni",
                "ukbiobank",
                "hcp",
                "abide",
                "oasis",
                "ixi",
                "mri",
                "ct scan",
                "x-ray",
                "ultrasound",
                "mammography",
                "retinal",
                "fundus",
                "oct",
                "pathology",
                "histology",
                # Computer vision specific
                "face",
                "detection",
                "segmentation",
                "tracking",
                "recognition",
                "video",
                "image",
                "visual",
                "photo",
                "picture",
            ]
        },
        "Natural Language Processing": {
            "keywords": [
                # Text datasets
                "glue",
                "superglue",
                "squad",
                "commonsenseqa",
                "hellaswag",
                "winogrande",
                "copa",
                "wsc",
                "rte",
                "wnli",
                "stsb",
                "cola",
                "sst",
                "mrpc",
                "qqp",
                "qnli",
                "mnli",
                "xnli",
                "xtreme",
                "multilingual",
                "wmt",
                "opus",
                "opensubtitles",
                "bookscorpus",
                "common crawl",
                "wikipedia",
                "reddit",
                "twitter",
                "news",
                "pubmed",
                "arxiv",
                "conll",
                "penn treebank",
                "ontonotes",
                "wikitext",
                # NLP tasks
                "text",
                "language",
                "dialogue",
                "conversation",
                "qa",
                "translation",
                "sentiment",
                "classification",
                "ner",
                "pos tagging",
                "parsing",
                "summarization",
                "generation",
            ]
        },
        "Reinforcement Learning & Robotics": {
            "keywords": [
                # RL environments (CRITICAL ADDITION)
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
                "coinrun",
                "montezuma",
                "breakout",
                "pong",
                "pacman",
                "pac-man",
                "space invaders",
                "halfcheetah",
                "hopper",
                "walker",
                "ant",
                "humanoid",
                "reacher",
                "pusher",
                "swimmer",
                "inverted pendulum",
                "cartpole",
                "cart-pole",
                "mountain car",
                "acrobot",
                "lunar lander",
                "bipedal walker",
                "car racing",
                "freeway",
                "seaquest",
                "enduro",
                "qbert",
                "asterix",
                # Environment suites
                "atari 2600",
                "arcade learning environment",
                "ale",
                "deepmind control suite",
                "dm_control",
                "meta-world",
                "robotics suite",
                "hand manipulation",
                "shadow hand",
                "fetch",
                "baxter",
                "sawyer",
                "calvin",
                "robosuite",
                # RL-specific terms
                "environment",
                "env",
                "simulation",
                "simulator",
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
                "rainbow",
                "dqn",
                # Robotics datasets/environments
                "robotic",
                "manipulation",
                "grasping",
                "navigation",
                "locomotion",
                "bipedal",
                "quadruped",
                "arm",
                "gripper",
                "pick and place",
                "push",
                "reach",
                "tactile",
                "sensing",
                "control",
            ]
        },
        "Graph Learning & Network Analysis": {
            "keywords": [
                # Graph datasets
                "cora",
                "citeseer",
                "pubmed",
                "reddit",
                "ppi",
                "qm7",
                "qm8",
                "qm9",
                "zinc",
                "tox21",
                "toxcast",
                "muv",
                "hiv",
                "bace",
                "bbbp",
                "clintox",
                "sider",
                "freesolv",
                "esol",
                "lipophilicity",
                # Social networks
                "facebook",
                "twitter",
                "social network",
                "citation",
                "collaboration",
                "friendship",
                "interaction",
                # Molecular/chemical
                "molecular",
                "chemical",
                "drug",
                "protein",
                "compound",
                "smiles",
                "graph",
                "network",
                "node",
                "edge",
            ]
        },
        "Scientific Computing & Applications": {
            "keywords": [
                # Scientific datasets
                "climate",
                "weather",
                "temperature",
                "precipitation",
                "atmospheric",
                "oceanographic",
                "satellite",
                "remote sensing",
                "astronomy",
                "astrophysics",
                "cosmology",
                "galaxy",
                "star",
                "planet",
                "telescope",
                "hubble",
                "sloan",
                # Biology/chemistry
                "protein",
                "dna",
                "rna",
                "genome",
                "genetic",
                "molecular dynamics",
                "simulation",
                "quantum",
                "physics",
                "chemistry",
                "materials",
            ]
        },
        "Speech & Audio": {
            "keywords": [
                # Audio datasets
                "librispeech",
                "common voice",
                "voxceleb",
                "timit",
                "switchboard",
                "fisher",
                "wsj",
                "tedlium",
                "musicnet",
                "nsynth",
                "gtzan",
                "fma",
                "million song",
                "speech",
                "audio",
                "voice",
                "sound",
                "acoustic",
                "music",
                "song",
                "instrument",
                "phoneme",
                "asr",
            ]
        },
        "Machine Learning Benchmarks": {
            "keywords": [
                # General ML datasets
                "uci",
                "adult",
                "housing",
                "wine",
                "iris",
                "diabetes",
                "breast cancer",
                "titanic",
                "heart disease",
                "mushroom",
                "abalone",
                "car evaluation",
                # Benchmark suites
                "openml",
                "sklearn",
                "benchmark",
                "synthetic",
                "regression",
                "classification",
                "clustering",
            ]
        },
    }

    return enhanced_taxonomy


def extract_datasets_and_environments():
    """Extract both datasets and environments from all Mila papers."""

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    print(f"Analyzing datasets AND environments from {len(papers_data)} papers...")

    papers_with_data = []
    all_data_entries = []
    papers_processed = 0

    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(
                f"Processing paper {i}/{len(papers_data)} ({len(papers_with_data)} with data)"
            )

        try:
            paper = Paper(paper_json)
            if not paper.queries:
                continue

            papers_processed += 1

            # Load analysis
            with open(paper.queries[0], "r") as f:
                analysis_data = json.load(f)

            extractions = analysis_data.get("extractions", {})
            if not extractions:
                continue

            # Extract paper metadata
            paper_id = paper_json.get("paper_id", "")
            title = paper_json.get("title", "")

            # Extract year
            year = None
            for release in paper_json.get("releases", []):
                venue = release.get("venue", {})
                venue_date = venue.get("date", {})
                if isinstance(venue_date, dict) and "text" in venue_date:
                    year = venue_date["text"][:4]
                    break

            # Extract datasets AND look for environments in text
            paper_data = []

            # Get datasets from extractions
            datasets = extractions.get("datasets", [])
            for dataset in datasets:
                if isinstance(dataset, dict) and "name" in dataset:
                    name_data = dataset["name"]
                    if isinstance(name_data, dict) and name_data.get("value"):
                        paper_data.append(
                            {
                                "data_name": name_data.get("value", ""),
                                "data_type": "dataset",
                                "justification": name_data.get("justification", ""),
                                "quote": name_data.get("quote", ""),
                            }
                        )

            # ALSO search for environments in the entire text
            description = extractions.get("description", {})
            if isinstance(description, dict):
                desc_text = (
                    description.get("value", "")
                    + " "
                    + description.get("justification", "")
                )
            else:
                desc_text = str(description)

            # Look for RL environment keywords in text
            env_keywords = [
                "atari",
                "gym",
                "mujoco",
                "dm control",
                "openai gym",
                "environment",
                "simulator",
                "cartpole",
                "mountain car",
                "halfcheetah",
                "hopper",
                "walker",
                "ant",
                "humanoid",
                "procgen",
                "deepmind lab",
                "starcraft",
                "minecraft",
            ]

            found_envs = []
            desc_lower = desc_text.lower()
            for keyword in env_keywords:
                if keyword in desc_lower:
                    found_envs.append(keyword)

            if found_envs:
                paper_data.append(
                    {
                        "data_name": ", ".join(found_envs),
                        "data_type": "environment",
                        "justification": desc_text[:200] + "...",
                        "quote": "",
                    }
                )

            if paper_data:
                papers_with_data.append(
                    {
                        "paper_id": paper_id,
                        "title": title,
                        "year": year,
                        "data_entries": paper_data,
                    }
                )

                for data_entry in paper_data:
                    all_data_entries.append(
                        {
                            "paper_id": paper_id,
                            "title": title,
                            "year": year,
                            "data_name": data_entry["data_name"],
                            "data_type": data_entry["data_type"],
                            "justification": data_entry["justification"],
                            "quote": data_entry["quote"],
                        }
                    )

        except Exception:
            continue

    print("\\nEnhanced extraction results:")
    print(f"Papers processed: {papers_processed}")
    print(f"Papers with datasets/environments: {len(papers_with_data)}")
    print(f"Total data entries: {len(all_data_entries)}")

    # Count by data type
    data_type_counts = Counter(entry["data_type"] for entry in all_data_entries)
    print("\\nData type breakdown:")
    for data_type, count in data_type_counts.items():
        print(f"  {data_type}: {count} entries")

    return papers_with_data, all_data_entries


def classify_papers_enhanced(papers_with_data):
    """Classify papers using enhanced taxonomy including environments."""

    enhanced_taxonomy = create_enhanced_taxonomy()

    paper_classifications = {}
    domain_stats = defaultdict(int)

    print("\\n=== ENHANCED CLASSIFICATION (Datasets + Environments) ===\\n")

    for paper in papers_with_data:
        paper_id = paper["paper_id"]
        title = paper["title"]
        data_entries = paper["data_entries"]

        # Combine all data text for classification
        data_text = []
        for entry in data_entries:
            data_text.append(entry["data_name"].lower())
            if entry["justification"]:
                data_text.append(entry["justification"].lower())
            if entry["quote"]:
                data_text.append(entry["quote"].lower())

        full_text = " ".join(data_text)

        # Find best matching domain
        best_match = None
        max_matches = 0
        matched_keywords = []

        for domain, info in enhanced_taxonomy.items():
            matches = 0
            domain_matched_keywords = []
            for keyword in info["keywords"]:
                if keyword in full_text:
                    matches += 1
                    domain_matched_keywords.append(keyword)

            if matches > max_matches:
                max_matches = matches
                best_match = domain
                matched_keywords = domain_matched_keywords

        if best_match and max_matches > 0:
            paper_classifications[paper_id] = {
                "title": title,
                "domain": best_match,
                "match_strength": max_matches,
                "matched_keywords": matched_keywords,
                "data_entries": [entry["data_name"] for entry in data_entries],
                "data_types": [entry["data_type"] for entry in data_entries],
            }
            domain_stats[best_match] += 1

    print("Enhanced classification results:")
    print("-" * 50)

    total_classified = sum(domain_stats.values())

    for domain, count in sorted(domain_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_classified) * 100
        print(f"{domain}: {count} papers ({percentage:.1f}%)")

    print(f"\\nTotal papers classified: {total_classified}")

    return paper_classifications, domain_stats


def compare_original_vs_enhanced():
    """Compare original dataset-only vs enhanced dataset+environment classification."""

    print("\\n=== ORIGINAL VS ENHANCED COMPARISON ===\\n")

    # Load original dataset-only results
    with open("dataset_domain_comparison.json", "r") as f:
        original_data = json.load(f)

    original_stats = original_data["dataset_domain_stats"]

    # Get enhanced results
    papers_with_data, all_data_entries = extract_datasets_and_environments()
    enhanced_classifications, enhanced_stats = classify_papers_enhanced(
        papers_with_data
    )

    print("Detailed comparison:")
    print("=" * 80)
    print(
        f"{'Domain':<35} {'Original':<12} {'Enhanced':<12} {'Difference':<12} {'% Change':<10}"
    )
    print("=" * 80)

    all_domains = set(original_stats.keys()) | set(enhanced_stats.keys())

    for domain in sorted(all_domains):
        original_count = original_stats.get(domain, 0)
        enhanced_count = enhanced_stats.get(domain, 0)
        difference = enhanced_count - original_count

        if original_count > 0:
            pct_change = (difference / original_count) * 100
        else:
            pct_change = float("inf") if enhanced_count > 0 else 0

        print(
            f"{domain:<35} {original_count:<12} {enhanced_count:<12} {difference:+<12} {pct_change:+<10.1f}%"
        )

    print("=" * 80)
    print(
        f"{'TOTAL':<35} {sum(original_stats.values()):<12} {sum(enhanced_stats.values()):<12}"
    )

    # Analyze the RL improvement specifically
    print("\\n=== REINFORCEMENT LEARNING ANALYSIS ===")
    print("-" * 50)

    rl_original = original_stats.get("Reinforcement Learning & Robotics", 0)
    rl_enhanced = enhanced_stats.get("Reinforcement Learning & Robotics", 0)
    rl_improvement = rl_enhanced - rl_original

    print(f"Original RL papers (datasets only): {rl_original}")
    print(f"Enhanced RL papers (datasets + environments): {rl_enhanced}")
    print(
        f"Improvement: +{rl_improvement} papers ({(rl_improvement / rl_original) * 100:+.1f}%)"
    )

    # Show sample RL papers with environments
    rl_papers = [
        info
        for info in enhanced_classifications.values()
        if info["domain"] == "Reinforcement Learning & Robotics"
    ]

    print("\\nSample RL papers found with enhanced method:")
    for i, paper in enumerate(rl_papers[:5]):
        print(f"  {i + 1}. {paper['title'][:60]}...")
        print(f"      Data: {', '.join(paper['data_entries'][:3])}...")
        print(f"      Types: {', '.join(set(paper['data_types']))}")
        print(f"      Keywords: {', '.join(paper['matched_keywords'][:5])}...")
        print()

    return {
        "original_stats": original_stats,
        "enhanced_stats": enhanced_stats,
        "rl_improvement": rl_improvement,
        "enhanced_classifications": enhanced_classifications,
    }


def analyze_environment_vs_dataset_split():
    """Analyze the split between environment-based and dataset-based classifications."""

    print("\\n=== ENVIRONMENT VS DATASET ANALYSIS ===\\n")

    papers_with_data, all_data_entries = extract_datasets_and_environments()

    # Analyze by data type
    papers_by_data_type = defaultdict(set)
    for entry in all_data_entries:
        papers_by_data_type[entry["data_type"]].add(entry["paper_id"])

    print("Papers by data type:")
    for data_type, papers in papers_by_data_type.items():
        print(f"  {data_type}: {len(papers)} papers")

    # Papers with both
    dataset_papers = papers_by_data_type.get("dataset", set())
    environment_papers = papers_by_data_type.get("environment", set())
    both = dataset_papers & environment_papers

    print(f"\\nPapers with both datasets and environments: {len(both)}")
    print(f"Dataset-only papers: {len(dataset_papers - environment_papers)}")
    print(f"Environment-only papers: {len(environment_papers - dataset_papers)}")

    # Analyze environment detection in RL domain
    enhanced_classifications, enhanced_stats = classify_papers_enhanced(
        papers_with_data
    )

    rl_papers = {
        pid: info
        for pid, info in enhanced_classifications.items()
        if info["domain"] == "Reinforcement Learning & Robotics"
    }

    rl_with_envs = 0
    rl_with_datasets = 0

    for paper_id, info in rl_papers.items():
        if "environment" in info["data_types"]:
            rl_with_envs += 1
        if "dataset" in info["data_types"]:
            rl_with_datasets += 1

    print("\\nRL domain analysis:")
    print(f"  Total RL papers: {len(rl_papers)}")
    print(
        f"  RL papers with environments: {rl_with_envs} ({rl_with_envs / len(rl_papers) * 100:.1f}%)"
    )
    print(
        f"  RL papers with datasets: {rl_with_datasets} ({rl_with_datasets / len(rl_papers) * 100:.1f}%)"
    )


def final_enhanced_recommendation():
    """Provide final recommendation based on enhanced analysis."""

    print("\\n=== FINAL RECOMMENDATION WITH ENVIRONMENTS ===\\n")

    comparison = compare_original_vs_enhanced()

    # Load research domain stats for comparison
    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    research_stats = research_data["category_stats"]
    enhanced_stats = comparison["enhanced_stats"]

    print("Three-way comparison:")
    print("=" * 90)
    print(
        f"{'Domain':<35} {'Research':<12} {'Enhanced':<12} {'Agreement':<15} {'Conclusion':<15}"
    )
    print("=" * 90)

    total_research = sum(research_stats.values())
    total_enhanced = sum(enhanced_stats.values())

    for domain in [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis",
    ]:
        research_count = research_stats.get(domain, 0)
        enhanced_count = enhanced_stats.get(domain, 0)

        research_pct = research_count / total_research * 100
        enhanced_pct = enhanced_count / total_enhanced * 100

        agreement = (
            min(research_pct, enhanced_pct) / max(research_pct, enhanced_pct) * 100
        )

        if agreement > 80:
            conclusion = "Strong agreement"
        elif agreement > 60:
            conclusion = "Moderate agreement"
        else:
            conclusion = "High disagreement"

        print(
            f"{domain:<35} {research_pct:<12.1f}% {enhanced_pct:<11.1f}% {agreement:<14.1f}% {conclusion:<15}"
        )

    print("=" * 90)

    # Final verdict
    rl_research_pct = (
        research_stats.get("Reinforcement Learning & Robotics", 0)
        / total_research
        * 100
    )
    rl_enhanced_pct = (
        enhanced_stats.get("Reinforcement Learning & Robotics", 0)
        / total_enhanced
        * 100
    )

    print("\\nKEY FINDING - RL Analysis:")
    print(f"Research domains: {rl_research_pct:.1f}%")
    print(f"Enhanced (datasets + environments): {rl_enhanced_pct:.1f}%")

    if abs(rl_research_pct - rl_enhanced_pct) < 5:
        print(
            "\\n✅ VINDICATION: Enhanced analysis supports research domain proportions"
        )
        print("   Including environments largely resolves the RL discrepancy")
    else:
        print(
            "\\n❌ DISCREPANCY REMAINS: Even with environments, significant disagreement"
        )
        print("   Further investigation needed")

    # Save results
    results = {
        "enhanced_stats": enhanced_stats,
        "comparison_with_research": {
            domain: {
                "research_pct": research_stats.get(domain, 0) / total_research * 100,
                "enhanced_pct": enhanced_stats.get(domain, 0) / total_enhanced * 100,
            }
            for domain in enhanced_stats.keys()
        },
        "rl_improvement": comparison["rl_improvement"],
    }

    with open("enhanced_environments_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\\nResults saved to enhanced_environments_analysis.json")

    return results


def main():
    """Run complete enhanced analysis including environments."""

    print("ENHANCED ANALYSIS: Including RL Environments with Datasets\\n")

    # 1. Extract both datasets and environments
    papers_with_data, all_data_entries = extract_datasets_and_environments()

    # 2. Enhanced classification
    enhanced_classifications, enhanced_stats = classify_papers_enhanced(
        papers_with_data
    )

    # 3. Compare with original dataset-only approach
    compare_original_vs_enhanced()

    # 4. Analyze environment vs dataset split
    analyze_environment_vs_dataset_split()

    # 5. Final recommendation
    final_recommendation = final_enhanced_recommendation()

    return final_recommendation


if __name__ == "__main__":
    results = main()
