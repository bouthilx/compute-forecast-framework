#!/usr/bin/env python3
"""
Analyze overlap between papers with datasets vs research domains
to understand missing classifications and potential correction factors.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

def load_existing_data():
    """Load both dataset and research domain classification results."""
    
    # Load dataset classifications
    with open('dataset_domain_comparison.json', 'r') as f:
        dataset_data = json.load(f)
    
    # Load research domain classifications  
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    # Load raw domain data
    with open('all_domains_full.json', 'r') as f:
        raw_domains = json.load(f)
    
    return dataset_data, research_data, raw_domains

def analyze_paper_overlap():
    """Analyze which papers have datasets vs research domains."""
    
    dataset_data, research_data, raw_domains = load_existing_data()
    
    # Get paper IDs from each classification
    papers_with_datasets = set(dataset_data['dataset_classifications'].keys())
    
    # Get paper IDs from research domain classification
    papers_with_research_domains = set()
    for domain_entry in raw_domains:
        papers_with_research_domains.add(domain_entry['paper_id'])
    
    print("=== PAPER OVERLAP ANALYSIS ===\\n")
    
    print(f"Papers with datasets: {len(papers_with_datasets)}")
    print(f"Papers with research domains: {len(papers_with_research_domains)}")
    
    # Analyze overlap
    overlap = papers_with_datasets & papers_with_research_domains
    only_datasets = papers_with_datasets - papers_with_research_domains
    only_research_domains = papers_with_research_domains - papers_with_datasets
    
    print(f"\\nOverlap analysis:")
    print(f"  Papers with both: {len(overlap)} ({len(overlap)/len(papers_with_datasets)*100:.1f}% of dataset papers)")
    print(f"  Only datasets: {len(only_datasets)} ({len(only_datasets)/len(papers_with_datasets)*100:.1f}% of dataset papers)")
    print(f"  Only research domains: {len(only_research_domains)} ({len(only_research_domains)/len(papers_with_research_domains)*100:.1f}% of research papers)")
    
    total_papers = len(papers_with_datasets | papers_with_research_domains)
    print(f"\\nTotal papers with any classification: {total_papers}")
    
    # Coverage analysis
    dataset_coverage = len(papers_with_datasets) / total_papers * 100
    research_coverage = len(papers_with_research_domains) / total_papers * 100
    
    print(f"\\nCoverage analysis:")
    print(f"  Dataset classification coverage: {dataset_coverage:.1f}%")
    print(f"  Research domain classification coverage: {research_coverage:.1f}%")
    
    return {
        'papers_with_datasets': papers_with_datasets,
        'papers_with_research_domains': papers_with_research_domains,
        'overlap': overlap,
        'only_datasets': only_datasets,
        'only_research_domains': only_research_domains,
        'total_papers': total_papers,
        'dataset_coverage': dataset_coverage,
        'research_coverage': research_coverage
    }

def analyze_domain_agreement(overlap_analysis):
    """For papers with both classifications, analyze domain agreement."""
    
    dataset_data, research_data, raw_domains = load_existing_data()
    
    overlap_papers = overlap_analysis['overlap']
    
    print("\\n=== DOMAIN AGREEMENT ANALYSIS ===\\n")
    
    # Create mapping from dataset domains to research domains
    domain_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing', 
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications',
        'Speech & Audio': 'Natural Language Processing',
        'Machine Learning Benchmarks': 'Machine Learning Theory & Methods'
    }
    
    # Get research domains for each paper (allow multiple)
    paper_research_domains = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry['paper_id']
        if paper_id in overlap_papers:
            # Map to standard taxonomy
            primary_domain = None
            for domain_name, info in research_data['classification'].items():
                if domain_entry['domain_name'] == domain_name:
                    primary_domain = info['category']
                    break
            
            if primary_domain:
                paper_research_domains[paper_id].add(primary_domain)
    
    # Compare classifications
    agreements = 0
    disagreements = 0
    agreement_details = defaultdict(int)
    disagreement_details = defaultdict(int)
    
    for paper_id in overlap_papers:
        if paper_id in dataset_data['dataset_classifications']:
            dataset_domain = dataset_data['dataset_classifications'][paper_id]['domain']
            research_domains = paper_research_domains.get(paper_id, set())
            
            # Map dataset domain to research domain
            mapped_dataset_domain = domain_mapping.get(dataset_domain, dataset_domain)
            
            if mapped_dataset_domain in research_domains:
                agreements += 1
                agreement_details[mapped_dataset_domain] += 1
            else:
                disagreements += 1
                disagreement_key = f"{dataset_domain} vs {', '.join(research_domains)}"
                disagreement_details[disagreement_key] += 1
    
    total_comparisons = agreements + disagreements
    agreement_rate = agreements / total_comparisons * 100 if total_comparisons > 0 else 0
    
    print(f"Total papers for comparison: {total_comparisons}")
    print(f"Agreements: {agreements} ({agreement_rate:.1f}%)")
    print(f"Disagreements: {disagreements} ({100-agreement_rate:.1f}%)")
    
    print("\\nAgreement breakdown:")
    for domain, count in sorted(agreement_details.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count} papers")
    
    print("\\nTop disagreements:")
    for disagreement, count in sorted(disagreement_details.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {disagreement}: {count} papers")
    
    return {
        'agreement_rate': agreement_rate,
        'agreements': agreements,
        'disagreements': disagreements,
        'agreement_details': dict(agreement_details),
        'disagreement_details': dict(disagreement_details)
    }

def calculate_missing_proportions(overlap_analysis):
    """Calculate what proportion of research domain papers are missing dataset classification."""
    
    dataset_data, research_data, raw_domains = load_existing_data()
    
    print("\\n=== MISSING CLASSIFICATION ANALYSIS ===\\n")
    
    # Group research domain papers by domain
    research_domain_papers = defaultdict(set)
    for domain_entry in raw_domains:
        paper_id = domain_entry['paper_id']
        for domain_name, info in research_data['classification'].items():
            if domain_entry['domain_name'] == domain_name:
                research_domain_papers[info['category']].add(paper_id)
                break
    
    # Group dataset papers by domain
    dataset_domain_papers = defaultdict(set)
    for paper_id, info in dataset_data['dataset_classifications'].items():
        dataset_domain_papers[info['domain']].add(paper_id)
    
    # Calculate missing proportions
    domain_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing', 
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications'
    }
    
    missing_analysis = {}
    
    for research_domain, dataset_domain in domain_mapping.items():
        research_papers = research_domain_papers.get(research_domain, set())
        dataset_papers = dataset_domain_papers.get(dataset_domain, set())
        
        research_with_datasets = research_papers & overlap_analysis['papers_with_datasets']
        research_missing_datasets = research_papers - overlap_analysis['papers_with_datasets']
        
        missing_rate = len(research_missing_datasets) / len(research_papers) * 100 if research_papers else 0
        
        missing_analysis[research_domain] = {
            'total_research_papers': len(research_papers),
            'with_datasets': len(research_with_datasets),
            'missing_datasets': len(research_missing_datasets),
            'missing_rate': missing_rate,
            'dataset_papers': len(dataset_papers)
        }
        
        print(f"{research_domain}:")
        print(f"  Research domain papers: {len(research_papers)}")
        print(f"  With datasets: {len(research_with_datasets)} ({100-missing_rate:.1f}%)")
        print(f"  Missing datasets: {len(research_missing_datasets)} ({missing_rate:.1f}%)")
        print(f"  Dataset-only papers: {len(dataset_papers)}")
        print()
    
    return missing_analysis

def main():
    """Run complete overlap analysis."""
    
    print("Starting overlap analysis between dataset and research domain classifications...\\n")
    
    # 1. Basic overlap analysis
    overlap_analysis = analyze_paper_overlap()
    
    # 2. Domain agreement analysis
    agreement_analysis = analyze_domain_agreement(overlap_analysis)
    
    # 3. Missing classification analysis
    missing_analysis = calculate_missing_proportions(overlap_analysis)
    
    # Save results
    results = {
        'overlap_analysis': overlap_analysis,
        'agreement_analysis': agreement_analysis,
        'missing_analysis': missing_analysis,
        'summary': {
            'total_papers_analyzed': overlap_analysis['total_papers'],
            'dataset_coverage': overlap_analysis['dataset_coverage'],
            'research_coverage': overlap_analysis['research_coverage'],
            'domain_agreement_rate': agreement_analysis['agreement_rate']
        }
    }
    
    # Convert sets to lists for JSON serialization
    for key, value in results['overlap_analysis'].items():
        if isinstance(value, set):
            results['overlap_analysis'][key] = list(value)
    
    with open('overlap_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\nResults saved to overlap_analysis.json")
    
    print("\\n=== SUMMARY ===")
    print(f"Total papers analyzed: {overlap_analysis['total_papers']}")
    print(f"Dataset classification coverage: {overlap_analysis['dataset_coverage']:.1f}%")
    print(f"Research domain classification coverage: {overlap_analysis['research_coverage']:.1f}%")
    print(f"Domain agreement rate: {agreement_analysis['agreement_rate']:.1f}%")
    
    return results

if __name__ == "__main__":
    results = main()