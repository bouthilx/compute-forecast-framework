#!/usr/bin/env python3
"""
Calculate correction factors for research domain proportions 
based on dataset analysis and missing classification patterns.
"""

import json
import numpy as np
from collections import defaultdict

def load_analysis_data():
    """Load overlap and classification data."""
    
    with open('overlap_analysis.json', 'r') as f:
        overlap_data = json.load(f)
    
    with open('dataset_domain_comparison.json', 'r') as f:
        dataset_data = json.load(f)
    
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    return overlap_data, dataset_data, research_data

def calculate_detection_rates():
    """Calculate how likely each domain is to have detectable datasets."""
    
    overlap_data, dataset_data, research_data = load_analysis_data()
    
    print("=== DATASET DETECTION RATES BY DOMAIN ===\\n")
    
    # Calculate detection rates from missing analysis
    detection_rates = {}
    
    for domain, stats in overlap_data['missing_analysis'].items():
        detection_rate = stats['with_datasets'] / stats['total_research_papers'] if stats['total_research_papers'] > 0 else 0
        detection_rates[domain] = detection_rate
        
        print(f"{domain}:")
        print(f"  Research papers: {stats['total_research_papers']}")
        print(f"  With datasets: {stats['with_datasets']}")
        print(f"  Detection rate: {detection_rate:.1%}")
        print()
    
    return detection_rates

def calculate_correction_factors():
    """Calculate correction factors based on dataset vs research domain proportions."""
    
    overlap_data, dataset_data, research_data = load_analysis_data()
    
    print("=== CORRECTION FACTOR CALCULATION ===\\n")
    
    # Get proportions from each method
    dataset_stats = dataset_data['dataset_domain_stats']
    research_stats = research_data['category_stats']
    
    total_dataset_papers = sum(dataset_stats.values())
    total_research_papers = sum(research_stats.values())
    
    # Domain mapping for comparison
    domain_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing', 
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications'
    }
    
    correction_factors = {}
    corrected_proportions = {}
    
    print("Domain-by-domain correction analysis:")
    print("-" * 80)
    
    for research_domain, dataset_domain in domain_mapping.items():
        research_count = research_stats.get(research_domain, 0)
        dataset_count = dataset_stats.get(dataset_domain, 0)
        
        research_prop = research_count / total_research_papers * 100
        dataset_prop = dataset_count / total_dataset_papers * 100
        
        # Calculate correction factor
        # This represents how much we should adjust the research domain proportion
        # based on the dataset evidence
        if research_prop > 0:
            correction_factor = dataset_prop / research_prop
        else:
            correction_factor = 1.0
        
        correction_factors[research_domain] = correction_factor
        
        print(f"{research_domain}:")
        print(f"  Research proportion: {research_prop:.1f}% ({research_count} papers)")
        print(f"  Dataset proportion:  {dataset_prop:.1f}% ({dataset_count} papers)")
        print(f"  Correction factor:   {correction_factor:.2f}")
        
        if correction_factor > 1.2:
            print(f"  → UNDERESTIMATED by research domains ({correction_factor:.1f}x)")
        elif correction_factor < 0.8:
            print(f"  → OVERESTIMATED by research domains ({1/correction_factor:.1f}x)")
        else:
            print(f"  → Reasonable agreement")
        print()
    
    return correction_factors

def apply_corrections_method1():
    """Apply corrections using weighted combination of both signals."""
    
    overlap_data, dataset_data, research_data = load_analysis_data()
    
    print("=== METHOD 1: WEIGHTED COMBINATION ===\\n")
    
    # Get base statistics
    dataset_stats = dataset_data['dataset_domain_stats']
    research_stats = research_data['category_stats']
    detection_rates = calculate_detection_rates()
    
    # Calculate weights based on detection rates and coverage
    dataset_weight = 0.7  # Higher weight for dataset evidence (more reliable)
    research_weight = 0.3  # Lower weight for research domain evidence
    
    corrected_counts = {}
    
    domain_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing', 
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications'
    }
    
    print("Weighted combination results:")
    print("-" * 50)
    
    for research_domain, dataset_domain in domain_mapping.items():
        research_count = research_stats.get(research_domain, 0)
        dataset_count = dataset_stats.get(dataset_domain, 0)
        detection_rate = detection_rates.get(research_domain, 0.6)
        
        # Estimate true count by adjusting dataset count for detection rate
        estimated_true_count = dataset_count / detection_rate if detection_rate > 0 else dataset_count
        
        # Weighted combination
        corrected_count = (dataset_weight * estimated_true_count + 
                          research_weight * research_count)
        
        corrected_counts[research_domain] = corrected_count
        
        print(f"{research_domain}:")
        print(f"  Research count: {research_count}")
        print(f"  Dataset count: {dataset_count}")
        print(f"  Detection rate: {detection_rate:.1%}")
        print(f"  Estimated true: {estimated_true_count:.0f}")
        print(f"  Corrected count: {corrected_count:.0f}")
        print()
    
    return corrected_counts

def apply_corrections_method2():
    """Apply corrections using proportional scaling based on detection rates."""
    
    overlap_data, dataset_data, research_data = load_analysis_data()
    
    print("=== METHOD 2: PROPORTIONAL SCALING ===\\n")
    
    dataset_stats = dataset_data['dataset_domain_stats']
    total_dataset_papers = sum(dataset_stats.values())
    detection_rates = calculate_detection_rates()
    
    # Scale up dataset proportions based on detection rates
    corrected_counts = {}
    
    domain_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing', 
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications'
    }
    
    # First, calculate scaled counts
    scaled_counts = {}
    for research_domain, dataset_domain in domain_mapping.items():
        dataset_count = dataset_stats.get(dataset_domain, 0)
        detection_rate = detection_rates.get(research_domain, 0.6)
        
        # Scale up by detection rate
        scaled_count = dataset_count / detection_rate if detection_rate > 0 else dataset_count
        scaled_counts[research_domain] = scaled_count
    
    # Normalize to total papers analyzed (1444)
    total_scaled = sum(scaled_counts.values())
    target_total = 1444  # Total papers with research domain classification
    
    print("Proportional scaling results:")
    print("-" * 50)
    
    for research_domain in domain_mapping.keys():
        dataset_count = dataset_stats.get(domain_mapping[research_domain], 0)
        detection_rate = detection_rates.get(research_domain, 0.6)
        scaled_count = scaled_counts[research_domain]
        
        # Normalize to target total
        normalized_count = (scaled_count / total_scaled) * target_total
        corrected_counts[research_domain] = normalized_count
        
        print(f"{research_domain}:")
        print(f"  Dataset count: {dataset_count}")
        print(f"  Detection rate: {detection_rate:.1%}")
        print(f"  Scaled count: {scaled_count:.0f}")
        print(f"  Final corrected: {normalized_count:.0f}")
        print()
    
    return corrected_counts

def compare_all_methods():
    """Compare original, corrected method 1, and corrected method 2."""
    
    overlap_data, dataset_data, research_data = load_analysis_data()
    
    print("=== COMPARISON OF ALL METHODS ===\\n")
    
    # Get original research domain stats
    original_stats = research_data['category_stats']
    total_original = sum(original_stats.values())
    
    # Get corrected stats
    corrected1 = apply_corrections_method1()
    corrected2 = apply_corrections_method2()
    
    # Compare
    domains = ['Computer Vision & Medical Imaging', 'Natural Language Processing', 
               'Reinforcement Learning & Robotics', 'Graph Learning & Network Analysis',
               'Scientific Computing & Applications']
    
    print("\\nFinal comparison:")
    print("=" * 100)
    print(f"{'Domain':<35} {'Original':<12} {'Method 1':<12} {'Method 2':<12} {'Dataset':<12}")
    print("=" * 100)
    
    dataset_stats = dataset_data['dataset_domain_stats']
    
    for domain in domains:
        original = original_stats.get(domain, 0)
        method1 = corrected1.get(domain, 0)
        method2 = corrected2.get(domain, 0)
        dataset = dataset_stats.get(domain, 0)
        
        print(f"{domain:<35} {original:<12} {method1:<12.0f} {method2:<12.0f} {dataset:<12}")
    
    print("=" * 100)
    
    # Calculate percentages
    total1 = sum(corrected1.values())
    total2 = sum(corrected2.values())
    
    print("\\nPercentage breakdown:")
    print("=" * 100)
    print(f"{'Domain':<35} {'Original':<12} {'Method 1':<12} {'Method 2':<12} {'Dataset':<12}")
    print("=" * 100)
    
    total_dataset = sum(dataset_stats.values())
    
    for domain in domains:
        original_pct = original_stats.get(domain, 0) / total_original * 100
        method1_pct = corrected1.get(domain, 0) / total1 * 100
        method2_pct = corrected2.get(domain, 0) / total2 * 100
        dataset_pct = dataset_stats.get(domain, 0) / total_dataset * 100
        
        print(f"{domain:<35} {original_pct:<12.1f}% {method1_pct:<11.1f}% {method2_pct:<11.1f}% {dataset_pct:<11.1f}%")
    
    print("=" * 100)
    
    # Save results
    results = {
        'original_stats': original_stats,
        'corrected_method1': {k: float(v) for k, v in corrected1.items()},
        'corrected_method2': {k: float(v) for k, v in corrected2.items()},
        'dataset_stats': dataset_stats,
        'comparison_summary': {
            'original_total': total_original,
            'method1_total': total1,
            'method2_total': total2,
            'dataset_total': total_dataset
        }
    }
    
    with open('correction_factors.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\nResults saved to correction_factors.json")
    
    return results

def main():
    """Run complete correction factor analysis."""
    
    print("Calculating correction factors for research domain proportions...\\n")
    
    # 1. Calculate detection rates
    detection_rates = calculate_detection_rates()
    
    # 2. Calculate basic correction factors
    correction_factors = calculate_correction_factors()
    
    # 3. Apply corrections using both methods
    results = compare_all_methods()
    
    print("\\n=== RECOMMENDATIONS ===")
    print("Based on the analysis:")
    print("1. Computer Vision & Medical Imaging is significantly underestimated in research domains")
    print("2. NLP shows similar underestimation pattern")  
    print("3. Reinforcement Learning may be overestimated in research domains")
    print("4. Method 2 (proportional scaling) provides most balanced estimates")
    
    return results

if __name__ == "__main__":
    results = main()