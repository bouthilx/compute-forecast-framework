#!/usr/bin/env python3
"""
Detailed analysis of agreement rates per domain to critically examine
whether dataset-based corrections are justified.
"""

import json
from collections import defaultdict


def load_all_data():
    """Load all relevant analysis data."""

    with open("overlap_analysis.json", "r") as f:
        overlap_data = json.load(f)

    with open("dataset_domain_comparison.json", "r") as f:
        dataset_data = json.load(f)

    with open("mila_domain_taxonomy.json", "r") as f:
        research_data = json.load(f)

    with open("all_domains_full.json", "r") as f:
        raw_domains = json.load(f)

    return overlap_data, dataset_data, research_data, raw_domains


def analyze_domain_specific_agreement():
    """Analyze agreement rates broken down by domain."""

    overlap_data, dataset_data, research_data, raw_domains = load_all_data()

    print("=== DOMAIN-SPECIFIC AGREEMENT ANALYSIS ===\\n")

    # Get papers with both classifications
    overlap_papers = set(overlap_data["overlap_analysis"]["overlap"])

    # Create mapping
    domain_mapping = {
        "Computer Vision & Medical Imaging": "Computer Vision & Medical Imaging",
        "Natural Language Processing": "Natural Language Processing",
        "Reinforcement Learning & Robotics": "Reinforcement Learning & Robotics",
        "Graph Learning & Network Analysis": "Graph Learning & Network Analysis",
        "Scientific Computing & Applications": "Scientific Computing & Applications",
        "Speech & Audio": "Natural Language Processing",
        "Machine Learning Benchmarks": "Machine Learning Theory & Methods",
    }

    # Get research domains for each paper
    paper_research_domains = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        if paper_id in overlap_papers:
            for domain_name, info in research_data["classification"].items():
                if domain_entry["domain_name"] == domain_name:
                    paper_research_domains[paper_id].add(info["category"])
                    break

    # Analyze agreement by domain
    domain_agreement_stats = {}

    for dataset_domain, research_domain in domain_mapping.items():
        # Get papers classified as this domain by datasets
        dataset_papers = {
            pid
            for pid, info in dataset_data["dataset_classifications"].items()
            if info["domain"] == dataset_domain and pid in overlap_papers
        }

        # Get papers classified as this domain by research classification
        research_papers = {
            pid
            for pid, domains in paper_research_domains.items()
            if research_domain in domains
        }

        # Calculate agreement metrics
        both_agree = dataset_papers & research_papers
        dataset_only = dataset_papers - research_papers
        research_only = research_papers - dataset_papers

        # Calculate rates
        if len(dataset_papers) > 0:
            dataset_precision = len(both_agree) / len(dataset_papers) * 100
        else:
            dataset_precision = 0

        if len(research_papers) > 0:
            research_precision = len(both_agree) / len(research_papers) * 100
        else:
            research_precision = 0

        if len(dataset_papers | research_papers) > 0:
            overall_agreement = (
                len(both_agree) / len(dataset_papers | research_papers) * 100
            )
        else:
            overall_agreement = 0

        domain_agreement_stats[dataset_domain] = {
            "dataset_papers": len(dataset_papers),
            "research_papers": len(research_papers),
            "both_agree": len(both_agree),
            "dataset_only": len(dataset_only),
            "research_only": len(research_only),
            "dataset_precision": dataset_precision,
            "research_precision": research_precision,
            "overall_agreement": overall_agreement,
        }

        print(f"{dataset_domain}:")
        print(f"  Dataset classification: {len(dataset_papers)} papers")
        print(f"  Research classification: {len(research_papers)} papers")
        print(f"  Both agree: {len(both_agree)} papers")
        print(f"  Dataset-only: {len(dataset_only)} papers")
        print(f"  Research-only: {len(research_only)} papers")
        print(
            f"  Dataset precision: {dataset_precision:.1f}% (how often dataset is confirmed by research)"
        )
        print(
            f"  Research precision: {research_precision:.1f}% (how often research is confirmed by dataset)"
        )
        print(f"  Overall agreement: {overall_agreement:.1f}%")
        print()

    return domain_agreement_stats


def analyze_false_positives_negatives():
    """Analyze what types of papers are misclassified by each method."""

    overlap_data, dataset_data, research_data, raw_domains = load_all_data()

    print("=== FALSE POSITIVE/NEGATIVE ANALYSIS ===\\n")

    overlap_papers = set(overlap_data["overlap_analysis"]["overlap"])

    # Create paper lookup for research domains
    paper_research_domains = defaultdict(set)
    paper_info = {}
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        if paper_id in overlap_papers:
            paper_info[paper_id] = {
                "title": domain_entry["title"],
                "year": domain_entry["year"],
            }
            for domain_name, info in research_data["classification"].items():
                if domain_entry["domain_name"] == domain_name:
                    paper_research_domains[paper_id].add(info["category"])
                    break

    # Analyze Computer Vision disagreements (highest correction factor)
    print("COMPUTER VISION & MEDICAL IMAGING - Disagreement Analysis:")
    print("-" * 60)

    cv_dataset_papers = {
        pid
        for pid, info in dataset_data["dataset_classifications"].items()
        if info["domain"] == "Computer Vision & Medical Imaging"
        and pid in overlap_papers
    }

    cv_research_papers = {
        pid
        for pid, domains in paper_research_domains.items()
        if "Computer Vision & Medical Imaging" in domains
    }

    # Dataset says CV, Research says not CV (Dataset False Positives?)
    dataset_fp = cv_dataset_papers - cv_research_papers
    print(f"\\nDataset classifies as CV, Research doesn't ({len(dataset_fp)} papers):")
    for i, paper_id in enumerate(list(dataset_fp)[:5]):  # Show first 5
        if paper_id in dataset_data["dataset_classifications"]:
            title = paper_info.get(paper_id, {}).get("title", "Unknown")[:80]
            datasets = dataset_data["dataset_classifications"][paper_id]["datasets"][:3]
            research_domains = list(paper_research_domains[paper_id])[:3]
            print(f"  {i+1}. {title}...")
            print(f"      Datasets: {datasets}")
            print(f"      Research domains: {research_domains}")
            print()

    # Research says CV, Dataset says not CV (Research False Positives?)
    research_fp = cv_research_papers - cv_dataset_papers
    print(f"Research classifies as CV, Dataset doesn't ({len(research_fp)} papers):")
    for i, paper_id in enumerate(list(research_fp)[:5]):  # Show first 5
        title = paper_info.get(paper_id, {}).get("title", "Unknown")[:80]
        research_domains = list(paper_research_domains[paper_id])[:3]
        print(f"  {i+1}. {title}...")
        print(f"      Research domains: {research_domains}")
        print()

    # Same analysis for RL (highest disagreement)
    print("\\nREINFORCEMENT LEARNING & ROBOTICS - Disagreement Analysis:")
    print("-" * 60)

    rl_dataset_papers = {
        pid
        for pid, info in dataset_data["dataset_classifications"].items()
        if info["domain"] == "Reinforcement Learning & Robotics"
        and pid in overlap_papers
    }

    rl_research_papers = {
        pid
        for pid, domains in paper_research_domains.items()
        if "Reinforcement Learning & Robotics" in domains
    }

    rl_research_fp = rl_research_papers - rl_dataset_papers
    print(f"Research classifies as RL, Dataset doesn't ({len(rl_research_fp)} papers):")
    for i, paper_id in enumerate(list(rl_research_fp)[:5]):
        title = paper_info.get(paper_id, {}).get("title", "Unknown")[:80]
        research_domains = list(paper_research_domains[paper_id])[:3]
        print(f"  {i+1}. {title}...")
        print(f"      Research domains: {research_domains}")
        print()

    return {
        "cv_dataset_only": len(dataset_fp),
        "cv_research_only": len(research_fp),
        "rl_research_only": len(rl_research_fp),
    }


def challenge_dataset_bias():
    """Challenge the assumption that datasets are more reliable."""

    print("\\n=== CHALLENGING DATASET-BASED CORRECTIONS ===\\n")

    print("POTENTIAL BIASES IN DATASET-BASED CLASSIFICATION:")
    print("=" * 60)

    print("\\n1. DATASET AVAILABILITY BIAS:")
    print("   - CV/NLP have standard, well-known datasets (ImageNet, GLUE)")
    print("   - RL often uses custom environments, not 'datasets'")
    print("   - Theory papers may not mention datasets at all")
    print("   - This could INFLATE CV/NLP and DEFLATE RL/Theory")

    print("\\n2. TEMPORAL BIAS:")
    print("   - Older papers less likely to mention modern dataset names")
    print("   - Newer domains may not have established dataset naming conventions")
    print("   - Could systematically undercount established vs emerging fields")

    print("\\n3. REPORTING BIAS:")
    print("   - Applied papers more likely to mention datasets")
    print(
        "   - Theoretical/methodological papers less likely to mention specific datasets"
    )
    print("   - Could skew toward applied vs fundamental research")

    print("\\n4. GRANULARITY MISMATCH:")
    print("   - Datasets are very specific (ImageNet = Computer Vision)")
    print("   - Research domains are broader (could be CV + ML Theory)")
    print("   - May miss interdisciplinary nature of modern AI")

    # Analyze dataset vs research domain specificity
    overlap_data, dataset_data, research_data, raw_domains = load_all_data()

    # Check if research classification captures more nuance
    papers_with_multiple_research_domains = 0
    total_research_domain_assignments = 0

    paper_research_counts = defaultdict(int)
    for domain_entry in raw_domains:
        paper_id = domain_entry["paper_id"]
        paper_research_counts[paper_id] += 1
        total_research_domain_assignments += 1

    for count in paper_research_counts.values():
        if count > 1:
            papers_with_multiple_research_domains += 1

    avg_research_domains = total_research_domain_assignments / len(
        paper_research_counts
    )

    print("\\n5. MULTI-DOMAIN EVIDENCE:")
    print(
        f"   - Research classification: {avg_research_domains:.2f} domains per paper on average"
    )
    print(
        f"   - {papers_with_multiple_research_domains}/{len(paper_research_counts)} papers have multiple research domains"
    )
    print("   - Dataset classification: typically 1 primary domain")
    print("   - Research domains may capture interdisciplinary nature better")


def examine_research_domain_quality():
    """Examine the quality and reliability of research domain classifications."""

    print("\\n=== RESEARCH DOMAIN CLASSIFICATION QUALITY ===\\n")

    overlap_data, dataset_data, research_data, raw_domains = load_all_data()

    # Analyze the strength of research domain classifications
    domain_strength_analysis = defaultdict(list)

    for domain_entry in raw_domains:
        domain_name = domain_entry["domain_name"]
        justification = domain_entry.get("justification", "")
        quote = domain_entry.get("quote", "")

        # Find the classification for this domain
        for class_domain_name, info in research_data["classification"].items():
            if domain_entry["domain_name"] == class_domain_name:
                category = info["category"]
                match_strength = info["match_strength"]

                domain_strength_analysis[category].append(
                    {
                        "domain_name": domain_name,
                        "match_strength": match_strength,
                        "justification_length": len(justification),
                        "quote_length": len(quote),
                    }
                )
                break

    print("Research Domain Classification Strength by Category:")
    print("-" * 60)

    for category, entries in domain_strength_analysis.items():
        if entries:
            avg_match_strength = sum(e["match_strength"] for e in entries) / len(
                entries
            )
            avg_justification_length = sum(
                e["justification_length"] for e in entries
            ) / len(entries)
            avg_quote_length = sum(e["quote_length"] for e in entries) / len(entries)

            print(f"\\n{category}:")
            print(f"  Average match strength: {avg_match_strength:.1f} keywords")
            print(
                f"  Average justification length: {avg_justification_length:.0f} chars"
            )
            print(f"  Average quote length: {avg_quote_length:.0f} chars")
            print(f"  Number of classifications: {len(entries)}")


def final_recommendation():
    """Provide final evidence-based recommendation."""

    print("\\n=== EVIDENCE-BASED RECOMMENDATION ===\\n")

    # Analyze the agreement statistics
    domain_stats = analyze_domain_specific_agreement()

    print("CRITICAL ANALYSIS OF CORRECTION APPROACH:")
    print("=" * 50)

    # Calculate average precision rates
    dataset_precisions = [stats["dataset_precision"] for stats in domain_stats.values()]
    research_precisions = [
        stats["research_precision"] for stats in domain_stats.values()
    ]

    avg_dataset_precision = sum(dataset_precisions) / len(dataset_precisions)
    avg_research_precision = sum(research_precisions) / len(research_precisions)

    print(f"\\nAverage Dataset Precision: {avg_dataset_precision:.1f}%")
    print(f"Average Research Precision: {avg_research_precision:.1f}%")

    if avg_dataset_precision > avg_research_precision:
        print("→ Dataset classifications are more often confirmed by research domains")
    else:
        print("→ Research classifications are more often confirmed by datasets")

    # Look at specific domains with high disagreement
    high_disagreement_domains = []
    for domain, stats in domain_stats.items():
        if stats["overall_agreement"] < 50:
            high_disagreement_domains.append((domain, stats["overall_agreement"]))

    if high_disagreement_domains:
        print("\\nDomains with <50% agreement:")
        for domain, agreement in high_disagreement_domains:
            print(f"  {domain}: {agreement:.1f}% agreement")

    print("\\nRECOMMENDATION:")
    print("-" * 20)

    if avg_dataset_precision > 70 and avg_research_precision < 60:
        print("✅ SUPPORT dataset-based corrections")
        print(
            "   Evidence: Datasets show higher precision when validated against research domains"
        )
    elif avg_research_precision > avg_dataset_precision:
        print("❌ CHALLENGE dataset-based corrections")
        print(
            "   Evidence: Research domains show higher precision when validated against datasets"
        )
    else:
        print("⚖️  MIXED EVIDENCE - Use hybrid approach")
        print("   Evidence: Both methods have comparable precision")

    return {
        "avg_dataset_precision": avg_dataset_precision,
        "avg_research_precision": avg_research_precision,
        "high_disagreement_domains": high_disagreement_domains,
    }


def main():
    """Run complete critical analysis of dataset-based corrections."""

    print("CRITICAL ANALYSIS: Should we correct research domains based on datasets?\\n")

    # 1. Detailed agreement analysis
    domain_agreement = analyze_domain_specific_agreement()

    # 2. False positive/negative analysis
    misclassification_analysis = analyze_false_positives_negatives()

    # 3. Challenge dataset bias assumptions
    challenge_dataset_bias()

    # 4. Examine research domain quality
    examine_research_domain_quality()

    # 5. Final evidence-based recommendation
    recommendation = final_recommendation()

    # Save detailed analysis
    results = {
        "domain_agreement_stats": domain_agreement,
        "misclassification_analysis": misclassification_analysis,
        "recommendation": recommendation,
    }

    with open("critical_agreement_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\\nDetailed analysis saved to critical_agreement_analysis.json")

    return results


if __name__ == "__main__":
    results = main()
