#!/usr/bin/env python3
"""
Debug the temporal classification logic to understand the difference between:
- WITHOUT AI analysis (no Paper().queries)
- NO domain classification (has queries but no research domains found)
"""

import json
import sys
from collections import defaultdict

def debug_classification_logic():
    """Debug the exact classification logic step by step."""
    
    # Load data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    with open('all_domains_full.json', 'r') as f:
        raw_domains = json.load(f)
    
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    print("DEBUGGING TEMPORAL CLASSIFICATION LOGIC")
    print("=" * 60)
    
    # Create sets for analysis
    papers_with_queries = set()
    papers_with_research_domains = set()
    paper_to_year = {}
    
    # Step 1: Identify papers with queries
    print("Step 1: Checking for AI analysis (queries)...")
    
    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(f"  Processed {i}/{len(papers_data)} papers")
            
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
            
            # Check if has queries
            try:
                paper = Paper(paper_json)
                if paper.queries:
                    papers_with_queries.add(paper_id)
            except Exception as e:
                # No queries available
                pass
    
    print(f"  Found {len(papers_with_queries)} papers with AI analysis (queries)")
    
    # Step 2: Identify papers with research domains
    print("\nStep 2: Checking for research domain classification...")
    
    for domain_entry in raw_domains:
        papers_with_research_domains.add(domain_entry['paper_id'])
    
    print(f"  Found {len(papers_with_research_domains)} papers with research domains")
    
    # Step 3: Analyze the overlap
    print("\nStep 3: Analyzing overlaps...")
    
    papers_with_years = set(paper_to_year.keys())
    
    # Check if all papers with research domains have queries
    domains_without_queries = papers_with_research_domains - papers_with_queries
    domains_with_queries = papers_with_research_domains & papers_with_queries
    
    print(f"  Papers with research domains that DON'T have queries: {len(domains_without_queries)}")
    print(f"  Papers with research domains that DO have queries: {len(domains_with_queries)}")
    
    if len(domains_without_queries) > 0:
        print(f"  ERROR: Research domains should only exist for papers WITH queries!")
        print(f"  Sample papers with domains but no queries:")
        for i, paper_id in enumerate(list(domains_without_queries)[:5]):
            print(f"    {paper_id}")
    
    # Step 4: Year-by-year breakdown
    print(f"\nStep 4: Year-by-year analysis...")
    
    for year in range(2019, 2025):
        year_papers = {pid for pid, y in paper_to_year.items() if y == year}
        year_with_queries = year_papers & papers_with_queries
        year_without_queries = year_papers - papers_with_queries
        year_with_domains = year_papers & papers_with_research_domains
        year_queries_no_domains = year_with_queries - papers_with_research_domains
        
        print(f"\n  {year}:")
        print(f"    Total papers: {len(year_papers)}")
        print(f"    WITH queries: {len(year_with_queries)} ({len(year_with_queries)/len(year_papers)*100:.1f}%)")
        print(f"    WITHOUT queries: {len(year_without_queries)} ({len(year_without_queries)/len(year_papers)*100:.1f}%)")
        print(f"    WITH research domains: {len(year_with_domains)} ({len(year_with_domains)/len(year_papers)*100:.1f}%)")
        print(f"    WITH queries but NO domains: {len(year_queries_no_domains)} ({len(year_queries_no_domains)/len(year_papers)*100:.1f}%)")
        
        # Verify logic
        total_classified = len(year_without_queries) + len(year_with_domains) + len(year_queries_no_domains)
        if total_classified != len(year_papers):
            print(f"    ERROR: Classification doesn't add up! {total_classified} vs {len(year_papers)}")

def investigate_sample_papers():
    """Investigate sample papers from early years to understand the issue."""
    
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    print("\n" + "=" * 60)
    print("INVESTIGATING SAMPLE PAPERS FROM EARLY YEARS")
    print("=" * 60)
    
    # Look at 2019 papers specifically
    papers_2019 = []
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
        
        if year == 2019:
            papers_2019.append(paper_json)
    
    print(f"Found {len(papers_2019)} papers from 2019")
    
    # Analyze first 10 papers from 2019
    for i, paper_json in enumerate(papers_2019[:10]):
        paper_id = paper_json.get('paper_id', '')
        title = paper_json.get('title', 'Unknown')[:60]
        
        print(f"\nPaper {i+1}: {title}...")
        print(f"  ID: {paper_id}")
        
        # Check for queries
        try:
            paper = Paper(paper_json)
            if paper.queries:
                print(f"  Queries: YES ({len(paper.queries)} found)")
                
                # Try to load first query
                try:
                    with open(paper.queries[0], 'r') as f:
                        analysis_data = json.load(f)
                    
                    extractions = analysis_data.get('extractions', {})
                    print(f"  Extractions: {len(extractions)} fields")
                    
                    # Look for description
                    description = extractions.get('description', {})
                    if description:
                        print(f"  Description available: YES")
                    else:
                        print(f"  Description available: NO")
                        
                except Exception as e:
                    print(f"  Query file error: {e}")
                    
            else:
                print(f"  Queries: NO")
        except Exception as e:
            print(f"  Paper loading error: {e}")

def check_research_domains_availability():
    """Check when research domains start appearing in the data."""
    
    with open('all_domains_full.json', 'r') as f:
        raw_domains = json.load(f)
    
    print("\n" + "=" * 60)
    print("RESEARCH DOMAINS AVAILABILITY BY YEAR")
    print("=" * 60)
    
    domains_by_year = defaultdict(list)
    
    for domain_entry in raw_domains:
        year = domain_entry.get('year')
        if year:
            try:
                year_int = int(year)
                if 2019 <= year_int <= 2024:
                    domains_by_year[year_int].append(domain_entry)
            except:
                continue
    
    for year in range(2019, 2025):
        count = len(domains_by_year[year])
        print(f"{year}: {count} domain entries")
        
        if count > 0 and count < 10:
            print("  Sample domains:")
            for entry in domains_by_year[year][:5]:
                print(f"    {entry['domain_name']} - {entry['title'][:50]}...")

def main():
    """Run all debugging analyses."""
    
    debug_classification_logic()
    investigate_sample_papers()
    check_research_domains_availability()

if __name__ == "__main__":
    main()