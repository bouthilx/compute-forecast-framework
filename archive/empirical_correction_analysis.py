#!/usr/bin/env python3
"""
Analyze what proportion of empirical papers are missing from research domains
when using dataset/environment detection. Use this to create proper correction factors.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
from paperext.utils import Paper

def load_data():
    """Load required data."""
    
    with open('all_domains_full.json', 'r') as f:
        raw_domains = json.load(f)
    
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    with open('dataset_domain_comparison.json', 'r') as f:
        dataset_data = json.load(f)
    
    return raw_domains, research_data, dataset_data

def classify_all_papers_theoretical_empirical():
    """Classify all papers in dataset as theoretical vs empirical."""
    
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    print("=== CLASSIFYING ALL PAPERS AS THEORETICAL VS EMPIRICAL ===\n")
    
    # Enhanced indicators for classification
    strong_theoretical_indicators = [
        'theorem', 'lemma', 'proof', 'corollary', 'proposition',
        'convergence analysis', 'regret bound', 'sample complexity',
        'pac learning', 'probably approximately correct',
        'theoretical analysis', 'theoretical guarantee',
        'mathematical framework', 'formal analysis'
    ]
    
    weak_theoretical_indicators = [
        'theoretical', 'theory', 'mathematical', 'analysis',
        'bound', 'complexity', 'optimal', 'optimality',
        'regret', 'convergence'
    ]
    
    strong_empirical_indicators = [
        'experiment', 'evaluation', 'benchmark', 'dataset',
        'training', 'testing', 'validation', 'results',
        'performance', 'comparison', 'ablation', 'baseline'
    ]
    
    weak_empirical_indicators = [
        'empirical', 'experimental', 'evaluate', 'train',
        'test', 'validate', 'compare', 'measure'
    ]
    
    def classify_paper(paper_json):
        """Classify a paper as theoretical, empirical, mixed, or unclear."""
        
        try:
            paper = Paper(paper_json)
            if not paper.queries:
                return 'unknown'
            
            with open(paper.queries[0], 'r') as f:
                analysis_data = json.load(f)
            
            extractions = analysis_data.get('extractions', {})
            
            # Get all text sources
            text_sources = []
            
            # Title
            title = paper_json.get('title', '').lower()
            text_sources.append(title)
            
            # Description
            description = extractions.get('description', {})
            if isinstance(description, dict):
                text_sources.append(description.get('value', '').lower())
                text_sources.append(description.get('justification', '').lower())
            
            # Methods
            methods = extractions.get('methods', [])
            for method in methods:
                if isinstance(method, dict) and 'name' in method:
                    name_data = method['name']
                    if isinstance(name_data, dict):
                        text_sources.append(name_data.get('value', '').lower())
                        text_sources.append(name_data.get('justification', '').lower())
            
            full_text = ' '.join(text_sources)
            
            # Count indicators
            strong_theoretical = sum(1 for indicator in strong_theoretical_indicators if indicator in full_text)
            strong_empirical = sum(1 for indicator in strong_empirical_indicators if indicator in full_text)
            weak_theoretical = sum(1 for indicator in weak_theoretical_indicators if indicator in full_text)
            weak_empirical = sum(1 for indicator in weak_empirical_indicators if indicator in full_text)
            
            # Scoring system
            theoretical_score = strong_theoretical * 3 + weak_theoretical * 1
            empirical_score = strong_empirical * 3 + weak_empirical * 1
            
            # Check for datasets (strong empirical indicator)
            datasets = extractions.get('datasets', [])
            if datasets:
                empirical_score += 5
            
            # Classification logic
            if theoretical_score >= 6 and theoretical_score > empirical_score:
                return 'theoretical'
            elif empirical_score >= 6 and empirical_score > theoretical_score:
                return 'empirical'
            elif abs(theoretical_score - empirical_score) <= 2 and max(theoretical_score, empirical_score) >= 4:
                return 'mixed'
            elif theoretical_score >= 3 or empirical_score >= 3:
                return 'theoretical' if theoretical_score > empirical_score else 'empirical'
            else:
                return 'unclear'
                
        except Exception as e:
            return 'error'
    
    # Classify all papers
    print("Classifying all papers...")
    
    paper_classifications = {}
    classification_counts = defaultdict(int)
    
    processed = 0
    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(f"Processed {i}/{len(papers_data)} papers")
        
        paper_id = paper_json.get('paper_id', '')
        classification = classify_paper(paper_json)
        
        paper_classifications[paper_id] = classification
        classification_counts[classification] += 1
        
        if classification != 'error' and classification != 'unknown':
            processed += 1
    
    print(f"\nOverall paper classification results ({processed} papers classified):")
    print("-" * 50)
    
    for classification, count in sorted(classification_counts.items(), key=lambda x: x[1], reverse=True):
        if classification not in ['error', 'unknown']:
            pct = count / processed * 100
            print(f"  {classification}: {count} papers ({pct:.1f}%)")
    
    return paper_classifications

def analyze_empirical_coverage_by_domain():
    """Analyze how well dataset/environment detection captures empirical papers by domain."""
    
    raw_domains, research_data, dataset_data = load_data()
    paper_classifications = classify_all_papers_theoretical_empirical()
    
    print(f"\n=== EMPIRICAL COVERAGE ANALYSIS BY DOMAIN ===\n")
    
    # Create mapping from research domain to main category
    domain_to_category = {}
    for domain_name, info in research_data['classification'].items():
        domain_to_category[domain_name] = info['category']
    
    # Group papers by research domain category
    papers_by_category = defaultdict(set)
    
    for domain_entry in raw_domains:
        paper_id = domain_entry['paper_id']
        domain_name = domain_entry['domain_name']
        
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            papers_by_category[category].add(paper_id)
    
    # Get papers classified by datasets/environments
    dataset_papers_by_category = defaultdict(set)
    
    for paper_id, info in dataset_data['dataset_classifications'].items():
        domain = info['domain']
        dataset_papers_by_category[domain].add(paper_id)
    
    # Map dataset domains to research categories
    dataset_to_research_mapping = {
        'Computer Vision & Medical Imaging': 'Computer Vision & Medical Imaging',
        'Natural Language Processing': 'Natural Language Processing',
        'Reinforcement Learning & Robotics': 'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis': 'Graph Learning & Network Analysis',
        'Scientific Computing & Applications': 'Scientific Computing & Applications',
        'Speech & Audio': 'Natural Language Processing',  # Map to NLP
        'Machine Learning Benchmarks': 'Machine Learning Theory & Methods'
    }
    
    # Convert dataset classifications to research categories
    dataset_research_papers = defaultdict(set)
    for dataset_domain, papers in dataset_papers_by_category.items():
        if dataset_domain in dataset_to_research_mapping:
            research_category = dataset_to_research_mapping[dataset_domain]
            dataset_research_papers[research_category].update(papers)
    
    print("EMPIRICAL COVERAGE ANALYSIS:")
    print("=" * 80)
    print(f"{'Category':<35} {'Research':<8} {'Dataset':<8} {'Empirical':<8} {'Coverage':<8} {'Miss Rate':<10}")
    print("=" * 80)
    
    coverage_analysis = {}
    
    main_categories = [
        'Computer Vision & Medical Imaging',
        'Natural Language Processing', 
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis',
        'Machine Learning Theory & Methods',
        'Deep Learning & Neural Architectures'
    ]
    
    for category in main_categories:
        research_papers = papers_by_category.get(category, set())
        dataset_papers = dataset_research_papers.get(category, set())
        
        # Count empirical papers in each group
        research_empirical = sum(1 for pid in research_papers 
                               if paper_classifications.get(pid) == 'empirical')
        
        dataset_empirical = sum(1 for pid in dataset_papers 
                              if paper_classifications.get(pid) == 'empirical')
        
        # Calculate coverage of empirical papers
        if research_empirical > 0:
            empirical_in_both = sum(1 for pid in (research_papers & dataset_papers)
                                  if paper_classifications.get(pid) == 'empirical')
            
            coverage_rate = empirical_in_both / research_empirical * 100
            miss_rate = (research_empirical - empirical_in_both) / research_empirical * 100
        else:
            coverage_rate = 0
            miss_rate = 0
        
        coverage_analysis[category] = {
            'research_total': len(research_papers),
            'dataset_total': len(dataset_papers),
            'research_empirical': research_empirical,
            'dataset_empirical': dataset_empirical,
            'coverage_rate': coverage_rate,
            'miss_rate': miss_rate
        }
        
        print(f"{category:<35} {len(research_papers):<8} {len(dataset_papers):<8} {research_empirical:<8} {coverage_rate:<7.1f}% {miss_rate:<9.1f}%")
    
    return coverage_analysis

def calculate_correction_factors():
    """Calculate correction factors based on empirical coverage analysis."""
    
    print(f"\n=== CALCULATING CORRECTION FACTORS ===\n")
    
    coverage_analysis = analyze_empirical_coverage_by_domain()
    
    print("CORRECTION FACTOR METHODOLOGY:")
    print("-" * 50)
    print("1. If datasets/env capture most empirical work (>80% coverage): Use dataset counts")
    print("2. If datasets/env miss significant empirical work (>20% miss): Adjust upward")
    print("3. If research domains include too much non-empirical work: Adjust downward")
    print()
    
    correction_recommendations = {}
    
    for category, stats in coverage_analysis.items():
        research_total = stats['research_total']
        dataset_total = stats['dataset_total']
        research_empirical = stats['research_empirical']
        coverage_rate = stats['coverage_rate']
        miss_rate = stats['miss_rate']
        
        # Calculate what proportion of research domain papers are empirical
        empirical_rate_in_research = research_empirical / research_total * 100 if research_total > 0 else 0
        
        print(f"{category}:")
        print(f"  Research domain papers: {research_total}")
        print(f"  Dataset/env papers: {dataset_total}")
        print(f"  Empirical papers in research domains: {research_empirical} ({empirical_rate_in_research:.1f}%)")
        print(f"  Coverage of empirical work by datasets: {coverage_rate:.1f}%")
        print(f"  Missing empirical work: {miss_rate:.1f}%")
        
        # Determine correction strategy
        if coverage_rate >= 80:
            # Good coverage - use dataset counts but check for theoretical inflation
            if empirical_rate_in_research < 70:
                # Research domains include significant theoretical work
                recommendation = f"Use dataset count ({dataset_total}) - research domains inflated by theory"
                corrected_count = dataset_total
            else:
                # Research domains are mostly empirical
                recommendation = f"Use dataset count ({dataset_total}) - good empirical alignment"
                corrected_count = dataset_total
        
        elif miss_rate >= 20:
            # Missing significant empirical work - adjust dataset count upward
            adjustment_factor = 100 / coverage_rate if coverage_rate > 0 else 1
            corrected_count = int(dataset_total * adjustment_factor)
            recommendation = f"Adjust dataset count upward: {dataset_total} → {corrected_count} (×{adjustment_factor:.2f})"
        
        else:
            # Moderate coverage - use weighted average
            weight_dataset = coverage_rate / 100
            weight_research = (100 - coverage_rate) / 100
            corrected_count = int(dataset_total * weight_dataset + research_empirical * weight_research)
            recommendation = f"Weighted average: {corrected_count} papers"
        
        correction_recommendations[category] = {
            'original_research': research_total,
            'original_dataset': dataset_total,
            'corrected_count': corrected_count,
            'recommendation': recommendation,
            'empirical_coverage': coverage_rate,
            'empirical_rate': empirical_rate_in_research
        }
        
        print(f"  → RECOMMENDATION: {recommendation}")
        print()
    
    return correction_recommendations

def analyze_specific_domains_empirical_gaps():
    """Analyze specific cases where datasets miss empirical work."""
    
    print(f"=== SPECIFIC EMPIRICAL GAPS ANALYSIS ===\n")
    
    raw_domains, research_data, dataset_data = load_data()
    paper_classifications = classify_all_papers_theoretical_empirical()
    
    # Focus on RL as example
    print("REINFORCEMENT LEARNING - Detailed Gap Analysis:")
    print("-" * 60)
    
    # Get RL papers from research domains
    rl_research_papers = set()
    for domain_entry in raw_domains:
        paper_id = domain_entry['paper_id']
        domain_name = domain_entry['domain_name']
        
        for class_domain, info in research_data['classification'].items():
            if class_domain == domain_name and info['category'] == 'Reinforcement Learning & Robotics':
                rl_research_papers.add(paper_id)
                break
    
    # Get RL papers from dataset classification
    rl_dataset_papers = set()
    for paper_id, info in dataset_data['dataset_classifications'].items():
        if info['domain'] == 'Reinforcement Learning & Robotics':
            rl_dataset_papers.add(paper_id)
    
    # Analyze empirical papers
    rl_research_empirical = {pid for pid in rl_research_papers 
                            if paper_classifications.get(pid) == 'empirical'}
    
    rl_dataset_empirical = {pid for pid in rl_dataset_papers 
                           if paper_classifications.get(pid) == 'empirical'}
    
    # Find empirical papers missed by dataset method
    missed_empirical = rl_research_empirical - rl_dataset_papers
    
    print(f"RL research domain papers: {len(rl_research_papers)}")
    print(f"RL dataset/env papers: {len(rl_dataset_papers)}")
    print(f"Empirical RL in research domains: {len(rl_research_empirical)}")
    print(f"Empirical RL in dataset method: {len(rl_dataset_empirical)}")
    print(f"Empirical RL papers missed by dataset method: {len(missed_empirical)}")
    
    if len(rl_research_empirical) > 0:
        coverage = len(rl_research_empirical & rl_dataset_papers) / len(rl_research_empirical) * 100
        print(f"Dataset method empirical coverage: {coverage:.1f}%")
    
    # Show sample missed papers
    print(f"\nSample empirical RL papers missed by dataset method:")
    print("-" * 50)
    
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    paper_lookup = {paper['paper_id']: paper for paper in papers_data}
    
    for i, paper_id in enumerate(list(missed_empirical)[:5]):
        paper_json = paper_lookup.get(paper_id)
        if paper_json:
            title = paper_json.get('title', 'Unknown')[:80]
            print(f"  {i+1}. {title}...")

def final_empirical_based_recommendations():
    """Provide final recommendations based on empirical work analysis."""
    
    print(f"\n=== FINAL EMPIRICAL-BASED RECOMMENDATIONS ===\n")
    
    correction_recommendations = calculate_correction_factors()
    analyze_specific_domains_empirical_gaps()
    
    print("SUMMARY OF EMPIRICAL-BASED CORRECTIONS:")
    print("=" * 60)
    
    total_research = 0
    total_corrected = 0
    
    for category, rec in correction_recommendations.items():
        total_research += rec['original_research']
        total_corrected += rec['corrected_count']
        
        print(f"{category}:")
        print(f"  Original research count: {rec['original_research']}")
        print(f"  Dataset/env count: {rec['original_dataset']}")
        print(f"  Corrected count: {rec['corrected_count']}")
        print(f"  Empirical coverage: {rec['empirical_coverage']:.1f}%")
        print()
    
    print(f"OVERALL IMPACT:")
    print(f"  Original research domain total: {total_research}")
    print(f"  Empirical-corrected total: {total_corrected}")
    print(f"  Net change: {total_corrected - total_research:+d} papers")
    
    # Save results
    results = {
        'correction_recommendations': correction_recommendations,
        'methodology': 'empirical_work_preservation',
        'summary': {
            'original_total': total_research,
            'corrected_total': total_corrected,
            'net_change': total_corrected - total_research
        }
    }
    
    with open('empirical_correction_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to empirical_correction_analysis.json")
    
    return results

def main():
    """Run complete empirical-based correction analysis."""
    
    print("EMPIRICAL-BASED CORRECTION ANALYSIS\n")
    print("Methodology: Include all works, but correct based on empirical work coverage\n")
    
    results = final_empirical_based_recommendations()
    
    return results

if __name__ == "__main__":
    results = main()