#!/usr/bin/env python3
"""
Investigate why recent papers (2023-2024) have no analysis data.
"""

import json
import sys
from collections import defaultdict
import os

def investigate_missing_analysis():
    """Investigate papers that have no analysis data."""
    
    print("INVESTIGATING MISSING ANALYSIS DATA")
    print("="*50)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    # Categorize papers by year and analysis status
    year_analysis_status = defaultdict(lambda: {
        'total': 0,
        'no_queries': 0,
        'queries_no_analysis': 0,
        'old_format': 0,
        'new_format': 0,
        'empty_queries': 0
    })
    
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
        
        if not year or not (2019 <= year <= 2024):
            continue
        
        year_analysis_status[year]['total'] += 1
        
        # Check for queries
        try:
            paper = Paper(paper_json)
            if not paper.queries:
                year_analysis_status[year]['no_queries'] += 1
                continue
            
            # Check each query file
            has_any_analysis = False
            
            for query_path in paper.queries:
                if not os.path.exists(query_path):
                    year_analysis_status[year]['empty_queries'] += 1
                    continue
                
                try:
                    with open(query_path, 'r') as f:
                        query_data = json.load(f)
                    
                    # Check for analysis data
                    has_old = 'analysis' in query_data and query_data['analysis']
                    has_new = 'extractions' in query_data and query_data['extractions']
                    
                    if has_old:
                        has_any_analysis = True
                        year_analysis_status[year]['old_format'] += 1
                        break
                    elif has_new:
                        has_any_analysis = True
                        year_analysis_status[year]['new_format'] += 1
                        break
                        
                except Exception as e:
                    continue
            
            if not has_any_analysis:
                year_analysis_status[year]['queries_no_analysis'] += 1
                
        except Exception as e:
            year_analysis_status[year]['no_queries'] += 1
    
    # Print results
    print("\nANALYSIS STATUS BY YEAR:")
    print("="*50)
    
    for year in sorted(year_analysis_status.keys()):
        stats = year_analysis_status[year]
        print(f"\n{year}: {stats['total']} total papers")
        print(f"  No queries: {stats['no_queries']} ({stats['no_queries']/stats['total']*100:.1f}%)")
        print(f"  Queries but no analysis: {stats['queries_no_analysis']} ({stats['queries_no_analysis']/stats['total']*100:.1f}%)")
        print(f"  Old format analysis: {stats['old_format']} ({stats['old_format']/stats['total']*100:.1f}%)")
        print(f"  New format analysis: {stats['new_format']} ({stats['new_format']/stats['total']*100:.1f}%)")
        print(f"  Empty query files: {stats['empty_queries']} ({stats['empty_queries']/stats['total']*100:.1f}%)")

def sample_recent_papers():
    """Sample some recent papers to understand the issue."""
    
    print("\n" + "="*50)
    print("SAMPLING RECENT PAPERS (2023-2024)")
    print("="*50)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    # Get sample papers from 2023-2024
    recent_papers = []
    
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
        
        if year and year >= 2023:
            recent_papers.append(paper_json)
            if len(recent_papers) >= 10:
                break
    
    print(f"Examining {len(recent_papers)} recent papers...")
    
    for i, paper_json in enumerate(recent_papers):
        paper_id = paper_json.get('paper_id', '')
        title = paper_json.get('title', 'Unknown')
        
        print(f"\n{i+1}. {title[:60]}...")
        print(f"   ID: {paper_id}")
        
        try:
            paper = Paper(paper_json)
            
            if paper.queries:
                print(f"   Queries: {len(paper.queries)} files")
                
                # Check first query file
                query_path = paper.queries[0]
                print(f"   Query path: {query_path}")
                
                if os.path.exists(query_path):
                    try:
                        with open(query_path, 'r') as f:
                            query_data = json.load(f)
                        
                        print(f"   File exists: YES")
                        print(f"   Top-level keys: {list(query_data.keys())}")
                        
                        # Check for analysis fields
                        has_analysis = 'analysis' in query_data and query_data['analysis']
                        has_extractions = 'extractions' in query_data and query_data['extractions']
                        
                        print(f"   Has analysis field: {has_analysis}")
                        print(f"   Has extractions field: {has_extractions}")
                        
                        if 'extractions' in query_data:
                            extractions = query_data['extractions']
                            print(f"   Extractions content: {type(extractions)} - {extractions}")
                        
                    except Exception as e:
                        print(f"   Error reading file: {e}")
                else:
                    print(f"   File exists: NO")
            else:
                print(f"   Queries: None")
                
        except Exception as e:
            print(f"   Error creating Paper: {e}")

def main():
    """Run the investigation."""
    
    investigate_missing_analysis()
    sample_recent_papers()

if __name__ == "__main__":
    main()