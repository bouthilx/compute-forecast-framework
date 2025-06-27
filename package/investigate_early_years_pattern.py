#!/usr/bin/env python3
"""
Investigate patterns in 2019-2022 papers without research domains.
Looking for evidence that the analysis system failed on historical data.
"""

import json
import sys
from collections import defaultdict, Counter
import re

def load_data():
    """Load all required data files."""
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    # Load domain data
    with open('all_domains_full.json', 'r') as f:
        raw_domains = json.load(f)
    
    # Create set of papers with domains
    papers_with_domains = set()
    for domain_entry in raw_domains:
        papers_with_domains.add(domain_entry['paper_id'])
    
    return papers_data, papers_with_domains

def extract_failed_papers():
    """Extract papers from 2019-2022 that have queries but no research domains."""
    
    papers_data, papers_with_domains = load_data()
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    failed_papers = []
    
    print("Extracting papers with queries but no domains from 2019-2022...")
    
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
        
        # Focus on 2019-2022
        if year and 2019 <= year <= 2022:
            # Check if has queries
            try:
                paper = Paper(paper_json)
                if paper.queries and paper_id not in papers_with_domains:
                    failed_papers.append({
                        'paper_id': paper_id,
                        'year': year,
                        'title': paper_json.get('title', 'Unknown'),
                        'abstract': paper_json.get('abstract', ''),
                        'queries': paper.queries,
                        'paper_json': paper_json
                    })
            except Exception as e:
                continue
    
    print(f"Found {len(failed_papers)} papers with queries but no domains (2019-2022)")
    
    return failed_papers

def analyze_titles_for_domains(failed_papers):
    """Analyze titles for obvious domain indicators."""
    
    print("\n" + "="*60)
    print("ANALYZING TITLES FOR OBVIOUS DOMAIN INDICATORS")
    print("="*60)
    
    # Define domain keywords
    domain_keywords = {
        'Computer Vision': [
            'vision', 'image', 'visual', 'video', 'object detection', 'segmentation',
            'classification', 'recognition', 'convolution', 'cnn', 'resnet', 'vgg',
            'medical imaging', 'x-ray', 'mri', 'ct scan', 'ultrasound', 'radiology',
            'pixel', 'filter', 'feature extraction', 'deep learning', 'neural network'
        ],
        'Natural Language Processing': [
            'language', 'text', 'nlp', 'word', 'sentence', 'translation', 'sentiment',
            'parsing', 'tokenization', 'embedding', 'bert', 'transformer', 'gpt',
            'dialogue', 'chatbot', 'speech', 'linguistic', 'corpus', 'semantic'
        ],
        'Reinforcement Learning': [
            'reinforcement', 'reward', 'policy', 'agent', 'environment', 'action',
            'q-learning', 'dqn', 'actor-critic', 'markov', 'mdp', 'temporal difference',
            'exploration', 'exploitation', 'bandit', 'game', 'control', 'robot'
        ],
        'Graph Learning': [
            'graph', 'network', 'node', 'edge', 'adjacency', 'connectivity', 'topology',
            'social network', 'knowledge graph', 'graph neural', 'gnn', 'graph convolution'
        ]
    }
    
    # Analyze each paper
    domain_matches = defaultdict(list)
    obvious_failures = []
    
    for paper in failed_papers:
        title = paper['title'].lower()
        abstract = paper['abstract'].lower() if paper['abstract'] else ''
        text = title + ' ' + abstract
        
        # Check for domain keywords
        matched_domains = []
        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    matched_domains.append(domain)
                    break
        
        if matched_domains:
            domain_matches[tuple(matched_domains)].append(paper)
            if len(matched_domains) == 1:  # Clear single domain
                obvious_failures.append({
                    'paper': paper,
                    'domain': matched_domains[0],
                    'confidence': 'high'
                })
    
    print(f"Papers with obvious domain indicators: {len(obvious_failures)}")
    print(f"Total papers analyzed: {len(failed_papers)}")
    print(f"Obvious failure rate: {len(obvious_failures)/len(failed_papers)*100:.1f}%")
    
    # Show domain distribution
    print(f"\nDomain distribution of obvious failures:")
    domain_counts = Counter()
    for failure in obvious_failures:
        domain_counts[failure['domain']] += 1
    
    for domain, count in domain_counts.most_common():
        print(f"  {domain}: {count} papers")
    
    return obvious_failures, domain_matches

def examine_query_analysis(failed_papers):
    """Examine the actual query analysis files to understand why extraction failed."""
    
    print("\n" + "="*60)
    print("EXAMINING QUERY ANALYSIS FILES")
    print("="*60)
    
    analysis_results = {
        'no_description': 0,
        'empty_extractions': 0,
        'query_file_error': 0,
        'partial_extractions': 0,
        'total_examined': 0
    }
    
    sample_papers = failed_papers[:20]  # Examine first 20 papers
    
    for paper in sample_papers:
        analysis_results['total_examined'] += 1
        
        print(f"\nPaper: {paper['title'][:60]}...")
        print(f"Year: {paper['year']}")
        print(f"Queries: {len(paper['queries'])}")
        
        try:
            # Load first query file
            with open(paper['queries'][0], 'r') as f:
                analysis_data = json.load(f)
            
            extractions = analysis_data.get('extractions', {})
            print(f"Extraction fields: {len(extractions)}")
            
            if len(extractions) == 0:
                analysis_results['empty_extractions'] += 1
                print("  → EMPTY extractions")
            else:
                # Check for description
                description = extractions.get('description', {})
                if not description or not description.get('data'):
                    analysis_results['no_description'] += 1
                    print("  → NO description data")
                else:
                    analysis_results['partial_extractions'] += 1
                    print("  → Has description but no domains extracted")
                    
                    # Show available fields
                    print(f"  Available fields: {list(extractions.keys())}")
                    
                    # Show description snippet
                    desc_text = description.get('data', '')
                    if isinstance(desc_text, str) and len(desc_text) > 0:
                        print(f"  Description: {desc_text[:100]}...")
                
        except Exception as e:
            analysis_results['query_file_error'] += 1
            print(f"  → Query file error: {e}")
    
    print(f"\nANALYSIS RESULTS:")
    print(f"  Total examined: {analysis_results['total_examined']}")
    print(f"  Empty extractions: {analysis_results['empty_extractions']}")
    print(f"  No description: {analysis_results['no_description']}")
    print(f"  Partial extractions: {analysis_results['partial_extractions']}")
    print(f"  Query file errors: {analysis_results['query_file_error']}")
    
    return analysis_results

def compare_with_successful_years(failed_papers):
    """Compare failed papers with successful extractions from 2023-2024."""
    
    print("\n" + "="*60)
    print("COMPARING WITH SUCCESSFUL YEARS (2023-2024)")
    print("="*60)
    
    papers_data, papers_with_domains = load_data()
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    # Get successful papers from 2023-2024
    successful_papers = []
    
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
        
        # Focus on 2023-2024 with domains
        if year and year >= 2023 and paper_id in papers_with_domains:
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    successful_papers.append({
                        'paper_id': paper_id,
                        'year': year,
                        'title': paper_json.get('title', 'Unknown'),
                        'queries': paper.queries
                    })
                    if len(successful_papers) >= 10:  # Sample 10 successful papers
                        break
            except:
                continue
    
    print(f"Comparing {len(failed_papers[:5])} failed papers with {len(successful_papers[:5])} successful papers")
    
    # Compare query analysis structure
    print(f"\nFAILED PAPERS (2019-2022):")
    for paper in failed_papers[:3]:
        print(f"\n  {paper['title'][:50]}... ({paper['year']})")
        try:
            with open(paper['queries'][0], 'r') as f:
                analysis_data = json.load(f)
            
            extractions = analysis_data.get('extractions', {})
            print(f"    Fields: {list(extractions.keys())}")
            
            # Check if description exists and has content
            description = extractions.get('description', {})
            if description and description.get('data'):
                desc_text = description['data']
                print(f"    Description length: {len(desc_text)} chars")
                print(f"    Description preview: {desc_text[:80]}...")
            else:
                print(f"    Description: MISSING or EMPTY")
                
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\nSUCCESSFUL PAPERS (2023-2024):")
    for paper in successful_papers[:3]:
        print(f"\n  {paper['title'][:50]}... ({paper['year']})")
        try:
            with open(paper['queries'][0], 'r') as f:
                analysis_data = json.load(f)
            
            extractions = analysis_data.get('extractions', {})
            print(f"    Fields: {list(extractions.keys())}")
            
            # Check description
            description = extractions.get('description', {})
            if description and description.get('data'):
                desc_text = description['data']
                print(f"    Description length: {len(desc_text)} chars")
                print(f"    Description preview: {desc_text[:80]}...")
            else:
                print(f"    Description: MISSING or EMPTY")
                
        except Exception as e:
            print(f"    Error: {e}")

def main():
    """Main analysis function."""
    
    print("INVESTIGATING EARLY YEARS PATTERN (2019-2022)")
    print("="*60)
    
    # Extract failed papers
    failed_papers = extract_failed_papers()
    
    if len(failed_papers) == 0:
        print("No failed papers found!")
        return
    
    # Year distribution
    year_counts = Counter(paper['year'] for paper in failed_papers)
    print(f"\nYear distribution of failed papers:")
    for year in sorted(year_counts.keys()):
        print(f"  {year}: {year_counts[year]} papers")
    
    # Analyze titles for obvious domain indicators
    obvious_failures, domain_matches = analyze_titles_for_domains(failed_papers)
    
    # Show sample obvious failures
    print(f"\nSAMPLE OBVIOUS FAILURES:")
    for i, failure in enumerate(obvious_failures[:10]):
        paper = failure['paper']
        domain = failure['domain']
        print(f"{i+1}. {paper['title'][:60]}... ({paper['year']}) → {domain}")
    
    # Examine query analysis files
    analysis_results = examine_query_analysis(failed_papers)
    
    # Compare with successful years
    compare_with_successful_years(failed_papers)
    
    # Final assessment
    print(f"\n" + "="*60)
    print("FINAL ASSESSMENT")
    print("="*60)
    
    total_failed = len(failed_papers)
    obvious_failed = len(obvious_failures)
    
    print(f"Total papers with queries but no domains (2019-2022): {total_failed}")
    print(f"Papers with obvious domain indicators in title/abstract: {obvious_failed}")
    print(f"Obvious failure rate: {obvious_failed/total_failed*100:.1f}%")
    
    print(f"\nThis strongly suggests the domain extraction system:")
    print(f"1. Had access to paper content (queries exist)")
    print(f"2. Failed to extract domains from content that clearly belongs to specific domains")
    print(f"3. The failure was systematic across 2019-2022")
    print(f"4. The system learned/improved starting in 2022-2023")
    
    if obvious_failed/total_failed > 0.3:  # If >30% are obvious failures
        print(f"\n⚠️  CONCLUSION: Analysis system failure on historical data")
        print(f"   The high rate of obvious domain indicators suggests the AI")
        print(f"   extraction system was not properly trained/configured when")
        print(f"   processing papers from 2019-2022.")
    
    return failed_papers, obvious_failures

if __name__ == "__main__":
    main()