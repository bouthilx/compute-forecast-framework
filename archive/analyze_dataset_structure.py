#!/usr/bin/env python3
"""
Analyze the structure of dataset/environment information in papers
to understand what data is available for corrections.
"""

import json
import sys
from collections import defaultdict, Counter

def analyze_dataset_structure():
    """Analyze what dataset/environment data is available in papers."""
    
    print("ANALYZING DATASET/ENVIRONMENT STRUCTURE")
    print("="*50)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    print(f"Loaded {len(papers_data)} papers")
    
    # Add paperext to path
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    # Track different types of data availability
    papers_with_analysis = 0
    papers_with_datasets = 0
    papers_with_environments = 0
    papers_with_both = 0
    papers_with_domains_only = 0
    
    dataset_examples = []
    environment_examples = []
    analysis_structure_examples = []
    
    # Sample papers for detailed analysis
    sample_count = 0
    max_samples = 10
    
    for paper_json in papers_data[:1000]:  # Analyze first 1000 papers for speed
        try:
            paper = Paper(paper_json)
            
            if paper.queries:
                papers_with_analysis += 1
                
                # Check what data is available in queries
                has_datasets = False
                has_environments = False
                has_domains = False
                
                for query_file in paper.queries:
                    try:
                        with open(query_file, 'r') as f:
                            query_data = json.load(f)
                        
                        # Look for datasets
                        if 'extractions' in query_data:
                            extractions = query_data['extractions']
                            
                            # Check for datasets
                            if 'datasets' in extractions:
                                has_datasets = True
                                if len(dataset_examples) < 5:
                                    dataset_examples.append({
                                        'paper_id': paper_json.get('paper_id', ''),
                                        'title': paper_json.get('title', ''),
                                        'datasets': extractions['datasets']
                                    })
                            
                            # Check for environments
                            if 'environments' in extractions:
                                has_environments = True
                                if len(environment_examples) < 5:
                                    environment_examples.append({
                                        'paper_id': paper_json.get('paper_id', ''),
                                        'title': paper_json.get('title', ''),
                                        'environments': extractions['environments']
                                    })
                            
                            # Check for domains
                            if 'primary_research_field' in extractions:
                                has_domains = True
                            
                            # Store structure example
                            if sample_count < max_samples:
                                analysis_structure_examples.append({
                                    'paper_id': paper_json.get('paper_id', ''),
                                    'title': paper_json.get('title', ''),
                                    'available_fields': list(extractions.keys()),
                                    'has_datasets': 'datasets' in extractions,
                                    'has_environments': 'environments' in extractions,
                                    'has_domains': 'primary_research_field' in extractions
                                })
                                sample_count += 1
                        
                        break  # Only need to check one query file per paper
                    except:
                        continue
                
                # Count combinations
                if has_datasets:
                    papers_with_datasets += 1
                if has_environments:
                    papers_with_environments += 1
                if has_datasets and has_environments:
                    papers_with_both += 1
                if has_domains and not has_datasets and not has_environments:
                    papers_with_domains_only += 1
        
        except Exception as e:
            continue
    
    print(f"\nDATA AVAILABILITY ANALYSIS:")
    print("="*30)
    print(f"Papers with AI analysis: {papers_with_analysis}")
    print(f"Papers with datasets: {papers_with_datasets}")
    print(f"Papers with environments: {papers_with_environments}")
    print(f"Papers with both datasets & environments: {papers_with_both}")
    print(f"Papers with domains only (no datasets/envs): {papers_with_domains_only}")
    
    if papers_with_analysis > 0:
        print(f"\nCOVERAGE PERCENTAGES:")
        print(f"Dataset coverage: {papers_with_datasets/papers_with_analysis*100:.1f}%")
        print(f"Environment coverage: {papers_with_environments/papers_with_analysis*100:.1f}%")
        print(f"Empirical work coverage (datasets OR environments): {(papers_with_datasets + papers_with_environments - papers_with_both)/papers_with_analysis*100:.1f}%")
        print(f"Theoretical only (domains without datasets/envs): {papers_with_domains_only/papers_with_analysis*100:.1f}%")
    
    print(f"\nDATASET EXAMPLES:")
    print("-" * 20)
    for example in dataset_examples:
        print(f"Paper: {example['title'][:80]}...")
        print(f"Datasets: {example['datasets']}")
        print()
    
    print(f"ENVIRONMENT EXAMPLES:")
    print("-" * 20)
    for example in environment_examples:
        print(f"Paper: {example['title'][:80]}...")
        print(f"Environments: {example['environments']}")
        print()
    
    print(f"ANALYSIS STRUCTURE EXAMPLES:")
    print("-" * 30)
    for example in analysis_structure_examples:
        print(f"Paper: {example['title'][:80]}...")
        print(f"Available fields: {example['available_fields']}")
        print(f"Has datasets: {example['has_datasets']}")
        print(f"Has environments: {example['has_environments']}")
        print(f"Has domains: {example['has_domains']}")
        print()
    
    return {
        'papers_with_analysis': papers_with_analysis,
        'papers_with_datasets': papers_with_datasets,
        'papers_with_environments': papers_with_environments,
        'papers_with_both': papers_with_both,
        'papers_with_domains_only': papers_with_domains_only,
        'dataset_examples': dataset_examples,
        'environment_examples': environment_examples,
        'analysis_structure_examples': analysis_structure_examples
    }

if __name__ == "__main__":
    results = analyze_dataset_structure()