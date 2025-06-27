#!/usr/bin/env python3
"""
Check a recent paper's query file to understand why there's no analysis data.
"""

import json
import sys
import os

def check_recent_paper_query():
    """Find a 2024 paper and examine its query file structure."""
    
    print("CHECKING RECENT PAPER QUERY FILE")
    print("="*50)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    # Find a 2024 paper with queries
    recent_paper = None
    
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
        
        if year == 2024:
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    recent_paper = {
                        'paper_json': paper_json,
                        'paper_id': paper_id,
                        'title': paper_json.get('title', 'Unknown'),
                        'year': year,
                        'queries': paper.queries
                    }
                    break
            except:
                continue
    
    if not recent_paper:
        print("No 2024 paper with queries found!")
        return
    
    print(f"Found 2024 paper:")
    print(f"  ID: {recent_paper['paper_id']}")
    print(f"  Title: {recent_paper['title'][:80]}...")
    print(f"  Queries: {len(recent_paper['queries'])} files")
    
    # Examine the first query file
    query_path = recent_paper['queries'][0]
    print(f"\nExamining query file: {query_path}")
    
    if not os.path.exists(query_path):
        print("ERROR: Query file does not exist!")
        return
    
    try:
        with open(query_path, 'r') as f:
            query_data = json.load(f)
        
        print(f"\nQuery file structure:")
        print(f"  File size: {os.path.getsize(query_path)} bytes")
        print(f"  Top-level keys: {list(query_data.keys())}")
        
        # Check each top-level field
        for key, value in query_data.items():
            if isinstance(value, dict):
                print(f"  {key}: dict with {len(value)} keys - {list(value.keys())}")
            elif isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, str):
                print(f"  {key}: string ({len(value)} chars)")
            else:
                print(f"  {key}: {type(value)} - {value}")
        
        # Check for analysis fields specifically
        print(f"\nAnalysis field checks:")
        
        if 'extractions' in query_data:
            extractions = query_data['extractions']
            print(f"  Has 'extractions' field: {type(extractions)}")
            if isinstance(extractions, dict):
                print(f"    Extractions keys: {list(extractions.keys())}")
                for k, v in extractions.items():
                    print(f"      {k}: {type(v)} - {v}")
            else:
                print(f"    Extractions content: {extractions}")
        else:
            print(f"  Has 'extractions' field: NO")
        
        if 'analysis' in query_data:
            analysis = query_data['analysis']
            print(f"  Has 'analysis' field: {type(analysis)}")
            if isinstance(analysis, dict):
                print(f"    Analysis keys: {list(analysis.keys())}")
                for k, v in analysis.items()[:5]:  # Show first 5 keys
                    print(f"      {k}: {type(v)}")
            else:
                print(f"    Analysis content: {analysis}")
        else:
            print(f"  Has 'analysis' field: NO")
        
        # Show full content if small file
        if os.path.getsize(query_path) < 2000:
            print(f"\nFull file content (small file):")
            print(json.dumps(query_data, indent=2))
        
    except Exception as e:
        print(f"ERROR reading query file: {e}")

def main():
    """Run the check."""
    check_recent_paper_query()

if __name__ == "__main__":
    main()