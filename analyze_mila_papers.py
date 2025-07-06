#!/usr/bin/env python3
"""
Analyze Mila papers to extract research domains, models, and computational requirements.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

# Add paperext to path
sys.path.insert(0, '/home/bouthilx/projects/paperext/src')

from paperext.utils import Paper

def load_mila_papers():
    """Load the Mila papers dataset."""
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        return json.load(f)

def extract_analysis_data(paper_json):
    """Extract analysis data from a paper JSON."""
    try:
        paper = Paper(paper_json)
        if not paper.queries:
            return None
            
        query_path = paper.queries[0]
        with open(query_path, 'r') as f:
            analysis_data = json.load(f)
        
        return analysis_data.get('extractions', {})
    except Exception as e:
        print(f"Error processing paper {paper_json.get('paper_id', 'unknown')}: {e}")
        return None

def analyze_papers():
    """Analyze all Mila papers and extract key information."""
    papers_data = load_mila_papers()
    print(f"Loaded {len(papers_data)} papers")
    
    # Containers for analysis
    research_domains = Counter()
    sub_domains = Counter()
    models_used = Counter()
    datasets_used = Counter()
    libraries_used = Counter()
    paper_types = Counter()
    
    papers_with_analysis = 0
    papers_by_year = defaultdict(list)
    
    # Process each paper
    for i, paper_json in enumerate(papers_data):
        if i % 100 == 0:
            print(f"Processing paper {i}/{len(papers_data)}")
        
        # Extract year from releases
        year = None
        for release in paper_json.get('releases', []):
            venue = release.get('venue', {})
            venue_date = venue.get('date', {})
            if isinstance(venue_date, dict) and 'text' in venue_date:
                year = venue_date['text'][:4]
                break
        
        # Get analysis data
        extractions = extract_analysis_data(paper_json)
        if extractions is None:
            continue
            
        papers_with_analysis += 1
        
        # Extract information
        paper_info = {
            'paper_id': paper_json.get('paper_id'),
            'title': paper_json.get('title'),
            'year': year,
            'extractions': extractions
        }
        
        if year:
            papers_by_year[year].append(paper_info)
        
        # Count primary research field
        primary_field = extractions.get('primary_research_field', {})
        if isinstance(primary_field, dict) and 'name' in primary_field:
            field_name = primary_field['name'].get('value', '')
            if field_name:
                research_domains[field_name] += 1
        
        # Count sub research fields
        sub_fields = extractions.get('sub_research_fields', [])
        for sub_field in sub_fields:
            if isinstance(sub_field, dict) and 'name' in sub_field:
                sub_name = sub_field['name'].get('value', '')
                if sub_name:
                    sub_domains[sub_name] += 1
        
        # Count models
        models = extractions.get('models', [])
        for model in models:
            if isinstance(model, dict) and 'name' in model:
                model_name = model['name'].get('value', '')
                if model_name:
                    models_used[model_name] += 1
        
        # Count datasets
        datasets = extractions.get('datasets', [])
        for dataset in datasets:
            if isinstance(dataset, dict) and 'name' in dataset:
                dataset_name = dataset['name'].get('value', '')
                if dataset_name:
                    datasets_used[dataset_name] += 1
        
        # Count libraries
        libraries = extractions.get('libraries', [])
        for library in libraries:
            if isinstance(library, dict) and 'name' in library:
                library_name = library['name'].get('value', '')
                if library_name:
                    libraries_used[library_name] += 1
        
        # Count paper types
        paper_type = extractions.get('type', {})
        if isinstance(paper_type, dict) and 'value' in paper_type:
            type_value = paper_type['value']
            if type_value:
                paper_types[type_value] += 1
    
    # Print summary statistics
    print(f"\n=== ANALYSIS SUMMARY ===")
    print(f"Total papers: {len(papers_data)}")
    print(f"Papers with analysis: {papers_with_analysis} ({papers_with_analysis/len(papers_data)*100:.1f}%)")
    
    print(f"\n=== TOP RESEARCH DOMAINS ===")
    for domain, count in research_domains.most_common(10):
        print(f"  {domain}: {count} papers")
    
    print(f"\n=== TOP SUB-DOMAINS ===")
    for subdomain, count in sub_domains.most_common(15):
        print(f"  {subdomain}: {count} papers")
    
    print(f"\n=== TOP MODELS ===")
    for model, count in models_used.most_common(15):
        print(f"  {model}: {count} papers")
    
    print(f"\n=== TOP DATASETS ===")
    for dataset, count in datasets_used.most_common(15):
        print(f"  {dataset}: {count} papers")
    
    print(f"\n=== TOP LIBRARIES ===")
    for library, count in libraries_used.most_common(15):
        print(f"  {library}: {count} papers")
    
    print(f"\n=== PAPER TYPES ===")
    for ptype, count in paper_types.most_common():
        print(f"  {ptype}: {count} papers")
    
    print(f"\n=== PAPERS BY YEAR ===")
    for year in sorted(papers_by_year.keys()):
        print(f"  {year}: {len(papers_by_year[year])} papers")
    
    return {
        'research_domains': research_domains,
        'sub_domains': sub_domains,
        'models_used': models_used,
        'datasets_used': datasets_used,
        'libraries_used': libraries_used,
        'paper_types': paper_types,
        'papers_by_year': papers_by_year,
        'total_papers': len(papers_data),
        'papers_with_analysis': papers_with_analysis
    }

if __name__ == "__main__":
    results = analyze_papers()
    
    # Save results to JSON
    output_file = "mila_papers_analysis.json"
    
    # Convert Counter objects to regular dicts for JSON serialization
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, Counter):
            serializable_results[key] = dict(value)
        elif key == 'papers_by_year':
            # Convert to just counts for now
            serializable_results[key] = {year: len(papers) for year, papers in value.items()}
        else:
            serializable_results[key] = value
    
    with open(output_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")