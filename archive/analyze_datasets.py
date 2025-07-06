#!/usr/bin/env python3
"""
Analyze datasets used in Mila papers to classify research domains
and compare with extracted research domain classifications.
"""

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def load_existing_taxonomy():
    """Load the existing research domain taxonomy."""
    with open("mila_domain_taxonomy.json", "r") as f:
        return json.load(f)


def create_dataset_taxonomy():
    """Create taxonomy for classifying papers based on datasets used."""

    dataset_taxonomy = {
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
                # RL environments
                "atari",
                "gym",
                "openai gym",
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
                "pac-man",
                "space invaders",
                # Robotics datasets
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
                # Control environments
                "control",
                "continuous control",
                "cart pole",
                "pendulum",
                "acrobot",
                "mountain car",
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

    return dataset_taxonomy


def extract_datasets_from_papers():
    """Extract datasets from all Mila papers with analysis."""

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    print(f"Analyzing datasets from {len(papers_data)} papers...")

    papers_with_datasets = []
    all_datasets = []
    papers_processed = 0

    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(
                f"Processing paper {i}/{len(papers_data)} ({len(papers_with_datasets)} with datasets)"
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

            # Extract datasets
            datasets = extractions.get("datasets", [])
            if datasets:
                paper_datasets = []
                for dataset in datasets:
                    if isinstance(dataset, dict) and "name" in dataset:
                        name_data = dataset["name"]
                        if isinstance(name_data, dict) and name_data.get("value"):
                            dataset_info = {
                                "dataset_name": name_data.get("value", ""),
                                "justification": name_data.get("justification", ""),
                                "quote": name_data.get("quote", ""),
                            }
                            paper_datasets.append(dataset_info)
                            all_datasets.append(
                                {
                                    "paper_id": paper_id,
                                    "title": title,
                                    "year": year,
                                    "dataset_name": dataset_info["dataset_name"],
                                    "justification": dataset_info["justification"],
                                    "quote": dataset_info["quote"],
                                }
                            )

                if paper_datasets:
                    papers_with_datasets.append(
                        {
                            "paper_id": paper_id,
                            "title": title,
                            "year": year,
                            "datasets": paper_datasets,
                        }
                    )

        except Exception:
            continue

    print("\\nDataset extraction results:")
    print(f"Papers processed: {papers_processed}")
    print(f"Papers with datasets: {len(papers_with_datasets)}")
    print(f"Total dataset entries: {len(all_datasets)}")

    return papers_with_datasets, all_datasets


def classify_papers_by_datasets(papers_with_datasets, dataset_taxonomy):
    """Classify papers into research domains based on their datasets."""

    paper_classifications = {}
    domain_stats = defaultdict(int)

    for paper in papers_with_datasets:
        paper_id = paper["paper_id"]
        title = paper["title"]
        datasets = paper["datasets"]

        # Combine all dataset text for classification
        dataset_text = []
        for dataset in datasets:
            dataset_text.append(dataset["dataset_name"].lower())
            if dataset["justification"]:
                dataset_text.append(dataset["justification"].lower())
            if dataset["quote"]:
                dataset_text.append(dataset["quote"].lower())

        full_text = " ".join(dataset_text)

        # Find best matching domain
        best_match = None
        max_matches = 0
        matched_keywords = []

        for domain, info in dataset_taxonomy.items():
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
                "datasets": [d["dataset_name"] for d in datasets],
            }
            domain_stats[best_match] += 1

    return paper_classifications, domain_stats


def compare_classifications():
    """Compare dataset-based vs research domain-based classifications."""

    # Load existing research domain classifications
    existing_taxonomy = load_existing_taxonomy()

    # Extract datasets and classify
    papers_with_datasets, all_datasets = extract_datasets_from_papers()
    dataset_taxonomy = create_dataset_taxonomy()
    dataset_classifications, dataset_domain_stats = classify_papers_by_datasets(
        papers_with_datasets, dataset_taxonomy
    )

    print("\\n=== DATASET-BASED DOMAIN CLASSIFICATION ===\\n")

    total_classified_by_datasets = sum(dataset_domain_stats.values())

    for domain, count in sorted(
        dataset_domain_stats.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / total_classified_by_datasets) * 100
        print(f"{domain}: {count} papers ({percentage:.1f}%)")

    print(f"\\nTotal papers classified by datasets: {total_classified_by_datasets}")

    # Compare with research domain classifications
    print("\\n=== COMPARISON WITH RESEARCH DOMAIN CLASSIFICATION ===\\n")

    research_domain_stats = existing_taxonomy["category_stats"]
    total_research_domains = sum(research_domain_stats.values())

    # Create mapping between domain names (they might be slightly different)
    domain_mapping = {
        "Computer Vision & Medical Imaging": "Computer Vision & Medical Imaging",
        "Natural Language Processing": "Natural Language Processing",
        "Reinforcement Learning & Robotics": "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis": "Graph Learning & Network Analysis",
        "Scientific Computing & Applications": "Scientific Computing & Applications",
        "Speech & Audio": "Natural Language Processing",  # Map to NLP for comparison
        "Machine Learning Benchmarks": "Machine Learning Theory & Methods",
    }

    print("Domain Comparison (Dataset-based vs Research Domain-based):")
    print("-" * 80)

    for dataset_domain, research_domain in domain_mapping.items():
        dataset_count = dataset_domain_stats.get(dataset_domain, 0)
        research_count = research_domain_stats.get(research_domain, 0)

        dataset_pct = (
            (dataset_count / total_classified_by_datasets) * 100
            if total_classified_by_datasets > 0
            else 0
        )
        research_pct = (
            (research_count / total_research_domains) * 100
            if total_research_domains > 0
            else 0
        )

        difference = dataset_count - research_count
        diff_sign = "+" if difference > 0 else ""

        print(f"{research_domain}:")
        print(f"  Dataset-based:     {dataset_count:4d} papers ({dataset_pct:5.1f}%)")
        print(f"  Research-based:    {research_count:4d} papers ({research_pct:5.1f}%)")
        print(f"  Difference:        {diff_sign}{difference:4d} papers")
        print()

    # Show some examples of dataset classifications
    print("=== SAMPLE DATASET CLASSIFICATIONS ===\\n")

    for domain in [
        "Computer Vision & Medical Imaging",
        "Natural Language Processing",
        "Reinforcement Learning & Robotics",
    ]:
        domain_papers = [
            (pid, info)
            for pid, info in dataset_classifications.items()
            if info["domain"] == domain
        ]
        domain_papers.sort(key=lambda x: x[1]["match_strength"], reverse=True)

        print(f"{domain} (showing top 3):")
        for i, (paper_id, info) in enumerate(domain_papers[:3]):
            print(f"  {i+1}. {info['title'][:60]}...")
            print(f"     Datasets: {', '.join(info['datasets'][:3])}...")
            print(
                f"     Keywords matched: {', '.join(info['matched_keywords'][:5])}..."
            )
            print()

    # Save results
    results = {
        "dataset_classifications": dataset_classifications,
        "dataset_domain_stats": dict(dataset_domain_stats),
        "research_domain_stats": research_domain_stats,
        "comparison": {
            "total_dataset_classified": total_classified_by_datasets,
            "total_research_classified": total_research_domains,
            "domain_mapping": domain_mapping,
        },
        "all_datasets": all_datasets,
    }

    with open("dataset_domain_comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Results saved to dataset_domain_comparison.json")

    return results


if __name__ == "__main__":
    results = compare_classifications()
