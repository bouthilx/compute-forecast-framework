#!/usr/bin/env python3
"""
Complete domain analysis of ALL Mila papers to create final taxonomy.
"""

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def extract_all_domains():
    """Extract domains from ALL Mila papers."""

    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    print(f"Processing ALL {len(papers_data)} papers...")

    all_domains = []
    papers_processed = 0
    papers_with_analysis = 0

    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(
                f"Processing paper {i}/{len(papers_data)} ({papers_with_analysis} with analysis)"
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

            papers_with_analysis += 1

            # Extract metadata
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

            # Extract venue
            venue_name = None
            for release in paper_json.get("releases", []):
                venue = release.get("venue", {})
                if venue.get("name"):
                    venue_name = venue["name"]
                    break

            # Extract primary domain
            primary_field = extractions.get("primary_research_field", {})
            if isinstance(primary_field, dict) and "name" in primary_field:
                name_data = primary_field["name"]
                if isinstance(name_data, dict) and name_data.get("value"):
                    all_domains.append(
                        {
                            "paper_id": paper_id,
                            "title": title,
                            "year": year,
                            "venue": venue_name,
                            "domain_type": "primary",
                            "domain_name": name_data.get("value", ""),
                            "justification": name_data.get("justification", ""),
                            "quote": name_data.get("quote", ""),
                        }
                    )

            # Extract sub domains
            sub_fields = extractions.get("sub_research_fields", [])
            for sub_field in sub_fields:
                if isinstance(sub_field, dict) and "name" in sub_field:
                    name_data = sub_field["name"]
                    if isinstance(name_data, dict) and name_data.get("value"):
                        all_domains.append(
                            {
                                "paper_id": paper_id,
                                "title": title,
                                "year": year,
                                "venue": venue_name,
                                "domain_type": "sub",
                                "domain_name": name_data.get("value", ""),
                                "justification": name_data.get("justification", ""),
                                "quote": name_data.get("quote", ""),
                            }
                        )

        except Exception:
            continue

    print("\\nFinal results:")
    print(f"Papers processed: {papers_processed}")
    print(f"Papers with analysis: {papers_with_analysis}")
    print(f"Domain entries extracted: {len(all_domains)}")

    return all_domains


def create_final_taxonomy(all_domains):
    """Create final research domain taxonomy."""

    # Enhanced taxonomy based on ML/AI standards and Mila focus
    mila_taxonomy = {
        "Computer Vision & Medical Imaging": {
            "keywords": [
                "computer vision",
                "vision",
                "image",
                "visual",
                "medical imaging",
                "segmentation",
                "detection",
                "classification",
                "mri",
                "ultrasound",
                "spinal cord",
                "medical",
                "healthcare",
                "radiology",
                "tomography",
                "microscopy",
                "pathology",
                "diagnostic",
                "clinical",
            ],
            "description": "Visual understanding, medical image analysis, diagnostic imaging",
        },
        "Natural Language Processing": {
            "keywords": [
                "nlp",
                "natural language",
                "language",
                "text",
                "linguistic",
                "translation",
                "sentiment",
                "dialogue",
                "conversation",
                "chatbot",
                "question answering",
                "summarization",
                "parsing",
                "generation",
                "bert",
                "transformer",
                "gpt",
                "llm",
                "large language model",
            ],
            "description": "Language understanding, text processing, conversational AI",
        },
        "Reinforcement Learning & Robotics": {
            "keywords": [
                "reinforcement learning",
                "rl",
                "policy",
                "reward",
                "agent",
                "robotics",
                "robotic",
                "manipulation",
                "control",
                "locomotion",
                "bipedal",
                "imitation learning",
                "autonomous",
                "navigation",
                "tactile",
                "sensing",
                "actuator",
                "motor",
            ],
            "description": "Learning through interaction, robotic control, autonomous systems",
        },
        "Deep Learning & Neural Architectures": {
            "keywords": [
                "deep learning",
                "neural network",
                "cnn",
                "rnn",
                "lstm",
                "gru",
                "transformer",
                "attention",
                "autoencoder",
                "generative",
                "adversarial",
                "gan",
                "vae",
                "diffusion",
                "architecture",
                "backpropagation",
                "gradient",
                "optimization",
            ],
            "description": "Deep neural networks, novel architectures, training methods",
        },
        "Graph Learning & Network Analysis": {
            "keywords": [
                "graph",
                "network",
                "node",
                "edge",
                "graph neural network",
                "gnn",
                "graph transformer",
                "graph signal processing",
                "temporal graph",
                "social network",
                "knowledge graph",
                "molecular graph",
                "graph embedding",
                "network analysis",
            ],
            "description": "Learning on graph-structured data, network analysis",
        },
        "Optimization & Operations Research": {
            "keywords": [
                "optimization",
                "combinatorial optimization",
                "scheduling",
                "linear programming",
                "integer programming",
                "constraint satisfaction",
                "metaheuristic",
                "genetic algorithm",
                "simulated annealing",
                "operations research",
                "logistics",
                "planning",
            ],
            "description": "Mathematical optimization, algorithmic problem solving",
        },
        "Machine Learning Theory & Methods": {
            "keywords": [
                "machine learning",
                "learning theory",
                "statistical learning",
                "bayesian",
                "probabilistic",
                "uncertainty",
                "active learning",
                "transfer learning",
                "meta learning",
                "few shot",
                "zero shot",
                "generalization",
                "bias",
                "fairness",
                "interpretability",
            ],
            "description": "ML foundations, theoretical analysis, learning paradigms",
        },
        "Software Engineering & Systems": {
            "keywords": [
                "software engineering",
                "software",
                "system",
                "distributed",
                "parallel",
                "scalability",
                "performance",
                "testing",
                "debugging",
                "reproducibility",
                "deployment",
                "mlops",
                "infrastructure",
                "cloud",
                "edge computing",
            ],
            "description": "ML systems, software quality, deployment infrastructure",
        },
        "Scientific Computing & Applications": {
            "keywords": [
                "astrophysics",
                "astronomy",
                "physics",
                "chemistry",
                "biology",
                "bioinformatics",
                "computational biology",
                "drug discovery",
                "climate",
                "weather",
                "materials science",
                "quantum",
                "simulation",
                "scientific computing",
                "numerical methods",
            ],
            "description": "AI for scientific discovery, computational science applications",
        },
        "Social & Economic Applications": {
            "keywords": [
                "social",
                "economic",
                "finance",
                "trading",
                "market",
                "recommendation",
                "personalization",
                "advertising",
                "social media",
                "human behavior",
                "psychology",
                "education",
                "learning analytics",
                "game theory",
            ],
            "description": "AI for social sciences, economics, human-centered applications",
        },
    }

    # Classify domains
    domain_classification = {}
    unclassified_domains = []

    # Group domains by name
    domain_groups = defaultdict(list)
    for domain in all_domains:
        domain_groups[domain["domain_name"]].append(domain)

    print(f"\\nClassifying {len(domain_groups)} unique domain names...")

    for domain_name, instances in domain_groups.items():
        classified = False
        domain_text = domain_name.lower()

        # Add context from justifications and quotes
        context_texts = []
        for instance in instances[:3]:  # Use first 3 instances for context
            if instance.get("justification"):
                context_texts.append(instance["justification"].lower())
            if instance.get("quote"):
                context_texts.append(instance["quote"].lower())

        full_text = domain_text + " " + " ".join(context_texts)

        # Find best matching category
        best_match = None
        max_matches = 0

        for category, info in mila_taxonomy.items():
            matches = sum(1 for keyword in info["keywords"] if keyword in full_text)
            if matches > max_matches:
                max_matches = matches
                best_match = category

        if max_matches > 0:
            domain_classification[domain_name] = {
                "category": best_match,
                "paper_count": len(instances),
                "match_strength": max_matches,
                "sample_papers": [inst["title"][:60] + "..." for inst in instances[:2]],
            }
            classified = True

        if not classified:
            unclassified_domains.append(
                {
                    "domain_name": domain_name,
                    "paper_count": len(instances),
                    "sample_text": full_text[:200] + "...",
                }
            )

    return domain_classification, unclassified_domains, mila_taxonomy


def main():
    """Run complete domain analysis."""

    print("=== COMPLETE MILA DOMAIN ANALYSIS ===\\n")

    # Extract all domains
    all_domains = extract_all_domains()

    # Create taxonomy
    classification, unclassified, taxonomy = create_final_taxonomy(all_domains)

    # Analyze results
    print("\\n=== FINAL DOMAIN TAXONOMY ===\\n")

    category_stats = defaultdict(int)
    for domain_name, info in classification.items():
        category_stats[info["category"]] += info["paper_count"]

    total_classified = sum(category_stats.values())

    for category, paper_count in sorted(
        category_stats.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"{category}: {paper_count} papers")

        # Show top domains in this category
        category_domains = [
            (name, info)
            for name, info in classification.items()
            if info["category"] == category
        ]
        category_domains.sort(key=lambda x: x[1]["paper_count"], reverse=True)

        for domain_name, info in category_domains[:5]:  # Top 5 domains
            print(f"  - {domain_name}: {info['paper_count']} papers")

        if len(category_domains) > 5:
            remaining = sum(info["paper_count"] for _, info in category_domains[5:])
            print(
                f"  - ... and {len(category_domains) - 5} more domains ({remaining} papers)"
            )
        print()

    print(f"Total classified papers: {total_classified}")
    print(f"Unclassified domains: {len(unclassified)}")

    if unclassified:
        print("\\nUnclassified domains:")
        for domain in sorted(
            unclassified, key=lambda x: x["paper_count"], reverse=True
        )[:10]:
            print(f"  - {domain['domain_name']}: {domain['paper_count']} papers")

    # Save results
    results = {
        "taxonomy": taxonomy,
        "classification": classification,
        "unclassified": unclassified,
        "category_stats": dict(category_stats),
        "total_papers": len(all_domains),
        "total_classified": total_classified,
    }

    with open("mila_domain_taxonomy.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save domains data
    with open("all_domains_full.json", "w") as f:
        json.dump(all_domains, f, indent=2)

    print("\\nResults saved to:")
    print("  - mila_domain_taxonomy.json")
    print("  - all_domains_full.json")

    return results


if __name__ == "__main__":
    results = main()
