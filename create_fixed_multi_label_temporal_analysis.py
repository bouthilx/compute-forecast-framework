#!/usr/bin/env python3
"""
Create temporal analysis with proper multi-label domain classification.
Papers can belong to multiple research domains simultaneously, but 'Other research domains'
is mutually exclusive with main categories.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def create_fixed_multi_label_temporal_analysis():
    """Create temporal analysis with corrected multi-label domain classification."""
    
    print("FIXED MULTI-LABEL TEMPORAL ANALYSIS")
    print("="*50)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    # Load domain data
    with open('all_domains_actual_fix.json', 'r') as f:
        raw_domains = json.load(f)
    
    # Load taxonomy
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    print(f"Loaded {len(papers_data)} papers and {len(raw_domains)} domain entries")
    
    # Create paper to year mapping
    import sys
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    paper_to_year = {}
    papers_with_analysis = set()
    
    for paper_json in papers_data:
        paper_id = paper_json.get('paper_id', '')
        
        # Extract year
        year = None
        for release in paper_json.get('releases', []):
            venue = release.get('venue', {})
            venue_date = venue.get('date', {})
            if isinstance(venue_date, dict) and 'text' in venue_date:
                try:
                    year = int(venue_date['text'][:4])
                    break
                except:
                    continue
        
        if year and 2019 <= year <= 2024:
            paper_to_year[paper_id] = year
            
            # Check if has analysis
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    papers_with_analysis.add(paper_id)
            except:
                pass
    
    # Create domain mappings (expand taxonomy to include all domains found)
    domain_to_category = {}
    for domain_name, info in research_data['classification'].items():
        domain_to_category[domain_name] = info['category']
    
    # Add automatic categorization for unmapped domains
    cv_keywords = ['computer vision', 'vision', 'image', 'visual', 'medical imaging', 'segmentation', 'object detection']
    nlp_keywords = ['natural language', 'nlp', 'language', 'text', 'linguistic', 'dialogue', 'conversational']
    rl_keywords = ['reinforcement learning', 'rl', 'robotics', 'agent', 'policy', 'control']
    graph_keywords = ['graph', 'network', 'node', 'edge', 'social network']
    
    for domain_entry in raw_domains:
        domain_name = domain_entry['domain_name']
        if domain_name not in domain_to_category:
            domain_lower = domain_name.lower()
            
            # Auto-categorize based on keywords
            if any(kw in domain_lower for kw in cv_keywords):
                domain_to_category[domain_name] = 'Computer Vision & Medical Imaging'
            elif any(kw in domain_lower for kw in nlp_keywords):
                domain_to_category[domain_name] = 'Natural Language Processing'
            elif any(kw in domain_lower for kw in rl_keywords):
                domain_to_category[domain_name] = 'Reinforcement Learning & Robotics'
            elif any(kw in domain_lower for kw in graph_keywords):
                domain_to_category[domain_name] = 'Graph Learning & Network Analysis'
            else:
                domain_to_category[domain_name] = 'Other research domains'
    
    # Define main research categories (mutually exclusive with "Other")
    main_research_categories = {
        'Computer Vision & Medical Imaging',
        'Natural Language Processing',
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis'
    }
    
    # FIXED MULTI-LABEL: Get categories for each paper with proper "Other" handling
    paper_to_main_categories = defaultdict(set)
    paper_to_other_categories = defaultdict(set)
    
    for domain_entry in raw_domains:
        paper_id = domain_entry['paper_id']
        domain_name = domain_entry['domain_name']
        if domain_name in domain_to_category:
            category = domain_to_category[domain_name]
            if category in main_research_categories:
                paper_to_main_categories[paper_id].add(category)
            else:
                paper_to_other_categories[paper_id].add(category)
    
    # Organize papers by year and category (FIXED MULTI-LABEL)
    years = list(range(2019, 2025))
    categories = [
        'WITHOUT AI analysis',
        'NO domain classification', 
        'Computer Vision & Medical Imaging',
        'Natural Language Processing',
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis',
        'Other research domains'
    ]
    
    year_data = {year: {cat: 0 for cat in categories} for year in years}
    
    # Track multi-label statistics
    multi_label_stats = {year: defaultdict(int) for year in years}
    total_papers_by_year = {year: 0 for year in years}
    other_only_papers = {year: 0 for year in years}
    
    # Classify each paper (FIXED MULTI-LABEL)
    for paper_id, year in paper_to_year.items():
        if year not in years:
            continue
        
        total_papers_by_year[year] += 1
        
        # Check if has AI analysis
        if paper_id not in papers_with_analysis:
            year_data[year]['WITHOUT AI analysis'] += 1
            continue
        
        # Get paper's categories
        main_categories = paper_to_main_categories.get(paper_id, set())
        other_categories = paper_to_other_categories.get(paper_id, set())
        
        if not main_categories and not other_categories:
            year_data[year]['NO domain classification'] += 1
        elif main_categories:
            # Paper has main categories - add to ALL applicable main categories
            for category in main_categories:
                year_data[year][category] += 1
            
            # Track multi-label statistics for main categories only
            num_main_labels = len(main_categories)
            multi_label_stats[year][num_main_labels] += 1
        else:
            # Paper ONLY has "Other" categories - mutually exclusive
            year_data[year]['Other research domains'] += 1
            other_only_papers[year] += 1
            multi_label_stats[year]['other_only'] += 1
    
    return years, categories, year_data, multi_label_stats, total_papers_by_year, other_only_papers

def create_fixed_multi_label_visualizations():
    """Create visualizations with corrected multi-label domain classification."""
    
    years, categories, year_data, multi_label_stats, total_papers_by_year, other_only_papers = create_fixed_multi_label_temporal_analysis()
    
    # Calculate research domain statistics (excluding WITHOUT/NO categories)
    all_research_categories = [
        'Computer Vision & Medical Imaging',
        'Natural Language Processing',
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis',
        'Other research domains'
    ]
    
    main_research_categories = [
        'Computer Vision & Medical Imaging',
        'Natural Language Processing',
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis'
    ]
    
    # Calculate research domain data (ALL research categories including Other)
    research_data = np.zeros((len(all_research_categories), len(years)))
    research_props = np.zeros((len(all_research_categories), len(years)))
    
    for i, year in enumerate(years):
        # Total research papers with domain classification (main + other)
        total_research_papers = sum(year_data[year][cat] for cat in all_research_categories)
        
        for j, category in enumerate(all_research_categories):
            count = year_data[year][category]
            research_data[j, i] = count
            research_props[j, i] = count / total_research_papers * 100 if total_research_papers > 0 else 0
    
    # Colors for research categories
    research_colors = [
        '#2ca02c',  # Green - Computer Vision
        '#1f77b4',  # Blue - Natural Language Processing
        '#9467bd',  # Purple - Reinforcement Learning
        '#8c564b',  # Brown - Graph Learning
        '#e377c2'   # Pink - Other research domains
    ]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Chart 1: Proportions within ALL research domains (multi-label aware)
    ax1.stackplot(years, research_props, labels=all_research_categories, colors=research_colors, alpha=0.8)
    ax1.set_title('Research Domain Proportions Over Time (MULTI-LABEL)\n(All research domains including Other)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Percentage of Research Papers (%)')
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add percentage labels
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(all_research_categories):
            pct = research_props[j, i]
            if pct > 8:  # Only label if >8%
                y_pos += pct/2
                ax1.text(year, y_pos, f'{pct:.0f}%', ha='center', va='center', 
                        fontsize=8, fontweight='bold', color='white')
                y_pos += pct/2
            else:
                y_pos += pct
    
    # Chart 2: Absolute counts for research domains (multi-label)
    ax2.stackplot(years, research_data, labels=all_research_categories, colors=research_colors, alpha=0.8)
    ax2.set_title('Research Domain Paper Counts Over Time (MULTI-LABEL)\n(Main domains can have multiple assignments, Other is mutually exclusive)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Number of Papers')
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add count labels
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(all_research_categories):
            count = research_data[j, i]
            if count > 20:  # Only label if >20 papers
                y_pos += count/2
                ax2.text(year, y_pos, f'{int(count)}', ha='center', va='center', 
                        fontsize=8, fontweight='bold', color='white')
                y_pos += count/2
            else:
                y_pos += count
    
    plt.tight_layout()
    plt.savefig('all_research_domains_temporal_analysis_FIXED.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print detailed multi-label statistics
    print(f"\nFIXED MULTI-LABEL DOMAIN STATISTICS:")
    print("="*45)
    
    for i, year in enumerate(years):
        total_papers = total_papers_by_year[year]
        papers_with_analysis = total_papers - year_data[year]['WITHOUT AI analysis']
        papers_with_domains = papers_with_analysis - year_data[year]['NO domain classification']
        main_assignments = sum(year_data[year][cat] for cat in main_research_categories)
        other_papers = other_only_papers[year]
        papers_with_main_domains = papers_with_domains - other_papers
        
        print(f"\n{year}:")
        print(f"  Total papers: {total_papers}")
        print(f"  Papers with AI analysis: {papers_with_analysis}")
        print(f"  Papers with domain classification: {papers_with_domains}")
        print(f"    - Papers with main domain(s): {papers_with_main_domains}")
        print(f"    - Papers with ONLY other domains: {other_papers}")
        print(f"  Main domain assignments: {main_assignments}")
        if papers_with_main_domains > 0:
            avg_main_domains = main_assignments / papers_with_main_domains
            print(f"  Average main domains per paper (with main domains): {avg_main_domains:.2f}")
        
        print(f"  Main domain assignment breakdown:")
        for category in main_research_categories:
            count = year_data[year][category]
            pct = count / main_assignments * 100 if main_assignments > 0 else 0
            print(f"    {category}: {count} ({pct:.1f}%)")
        
        print(f"  Other research domains: {other_papers} papers")
        
        # Multi-label distribution for main categories
        print(f"  Multi-label distribution (main domains only):")
        # Separate numeric and string keys, sort only the numeric ones
        numeric_items = [(k, v) for k, v in multi_label_stats[year].items() if isinstance(k, int)]
        for num_labels, paper_count in sorted(numeric_items):
            if paper_count > 0:
                pct = paper_count / papers_with_main_domains * 100 if papers_with_main_domains > 0 else 0
                print(f"    {num_labels} main domain(s): {paper_count} papers ({pct:.1f}%)")
    
    # Growth analysis
    print(f"\nGROWTH ANALYSIS (FIXED MULTI-LABEL):")
    print("="*40)
    
    total_2019 = total_papers_by_year[2019]
    total_2024 = total_papers_by_year[2024]
    print(f"Overall paper growth: {total_2019} → {total_2024} ({(total_2024/total_2019-1)*100:+.1f}%)")
    
    main_assignments_2019 = sum(year_data[2019][cat] for cat in main_research_categories)
    main_assignments_2024 = sum(year_data[2024][cat] for cat in main_research_categories)
    print(f"Main domain assignment growth: {main_assignments_2019} → {main_assignments_2024} ({(main_assignments_2024/main_assignments_2019-1)*100:+.1f}%)")
    
    other_2019 = other_only_papers[2019]
    other_2024 = other_only_papers[2024]
    if other_2019 > 0:
        other_growth = (other_2024/other_2019-1)*100
        print(f"Other-only papers growth: {other_2019} → {other_2024} ({other_growth:+.1f}%)")
    else:
        print(f"Other-only papers growth: {other_2019} → {other_2024} (N/A)")
    
    print(f"\nMain category trends (2019 → 2024):")
    for category in main_research_categories:
        count_2019 = year_data[2019][category]
        count_2024 = year_data[2024][category]
        
        if count_2019 > 0:
            growth = (count_2024/count_2019-1)*100
            print(f"  {category}:")
            print(f"    Assignments: {count_2019} → {count_2024} ({growth:+.1f}%)")
        else:
            print(f"  {category}: 0 → {count_2024} assignments")
    
    # Save complete multi-label data
    fixed_multi_label_data = {
        'years': years,
        'categories': categories,
        'all_research_categories': all_research_categories,
        'main_research_categories': main_research_categories,
        'year_data': year_data,
        'multi_label_stats': dict(multi_label_stats),
        'total_papers_by_year': total_papers_by_year,
        'other_only_papers': other_only_papers,
        'main_data_matrix': research_data.tolist(),
        'main_prop_matrix': research_props.tolist()
    }
    
    with open('temporal_analysis_data_FIXED_MULTI_LABEL.json', 'w') as f:
        json.dump(fixed_multi_label_data, f, indent=2)
    
    return fixed_multi_label_data

def create_complete_paper_classification_chart():
    """Create complete paper classification chart including proper Other category."""
    
    years, categories, year_data, multi_label_stats, total_papers_by_year, other_only_papers = create_fixed_multi_label_temporal_analysis()
    
    # Prepare data for complete paper classification
    classification_categories = [
        'WITHOUT AI analysis',
        'NO domain classification',
        'WITH main domains',
        'WITH other domains only'
    ]
    
    classification_data = np.zeros((len(classification_categories), len(years)))
    classification_props = np.zeros((len(classification_categories), len(years)))
    
    main_research_categories = [
        'Computer Vision & Medical Imaging',
        'Natural Language Processing',
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis'
    ]
    
    for i, year in enumerate(years):
        total_papers = total_papers_by_year[year]
        without_analysis = year_data[year]['WITHOUT AI analysis']
        no_classification = year_data[year]['NO domain classification']
        other_only = other_only_papers[year]
        with_main = total_papers - without_analysis - no_classification - other_only
        
        counts = [without_analysis, no_classification, with_main, other_only]
        
        for j, count in enumerate(counts):
            classification_data[j, i] = count
            classification_props[j, i] = count / total_papers * 100 if total_papers > 0 else 0
    
    # Colors for classification
    classification_colors = [
        '#d62728',  # Red - WITHOUT AI analysis
        '#ff7f0e',  # Orange - NO domain classification  
        '#2ca02c',  # Green - WITH main domains
        '#e377c2'   # Pink - WITH other domains only
    ]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Chart 1: Paper classification proportions
    ax1.stackplot(years, classification_props, labels=classification_categories, colors=classification_colors, alpha=0.8)
    ax1.set_title('Paper Classification Proportions Over Time (FIXED MULTI-LABEL)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Percentage of Papers (%)')
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add percentage labels
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(classification_categories):
            pct = classification_props[j, i]
            if pct > 5:  # Only label if >5%
                y_pos += pct/2
                ax1.text(year, y_pos, f'{pct:.0f}%', ha='center', va='center', 
                        fontsize=8, fontweight='bold', color='white')
                y_pos += pct/2
            else:
                y_pos += pct
    
    # Chart 2: Paper classification counts
    ax2.stackplot(years, classification_data, labels=classification_categories, colors=classification_colors, alpha=0.8)
    ax2.set_title('Paper Classification Counts Over Time (FIXED MULTI-LABEL)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Number of Papers')
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add count labels
    for i, year in enumerate(years):
        y_pos = 0
        for j, category in enumerate(classification_categories):
            count = classification_data[j, i]
            if count > 30:  # Only label if >30 papers
                y_pos += count/2
                ax2.text(year, y_pos, f'{int(count)}', ha='center', va='center', 
                        fontsize=8, fontweight='bold', color='white')
                y_pos += count/2
            else:
                y_pos += count
    
    plt.tight_layout()
    plt.savefig('paper_classification_temporal_analysis_FIXED.png', dpi=300, bbox_inches='tight')
    plt.show()

def main():
    """Create fixed multi-label temporal analysis."""
    
    print("CREATING FIXED MULTI-LABEL TEMPORAL ANALYSIS")
    print("="*55)
    
    # Create fixed multi-label domain analysis
    fixed_multi_label_data = create_fixed_multi_label_visualizations()
    
    # Create complete paper classification chart
    create_complete_paper_classification_chart()
    
    print(f"\nFixed multi-label charts saved as:")
    print(f"- all_research_domains_temporal_analysis_FIXED.png")
    print(f"- paper_classification_temporal_analysis_FIXED.png") 
    print(f"- temporal_analysis_data_FIXED_MULTI_LABEL.json")
    
    print(f"\nKey corrections:")
    print(f"- 'Other research domains' is now mutually exclusive with main categories")
    print(f"- Papers with main domains can have multiple main domain labels")
    print(f"- Papers with ONLY other domains go to 'Other research domains'")
    print(f"- Other research domains now included in stacked area charts")
    print(f"- Statistics properly separate main vs other domain distributions")

if __name__ == "__main__":
    main()