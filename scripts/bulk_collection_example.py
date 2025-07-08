#!/usr/bin/env python3
"""
Example of bulk collection from OpenAlex using venue IDs
"""

import json
import requests
from typing import List, Dict

def bulk_collect_by_venues(venue_ids: List[str], years: List[int], email: str = None):
    """
    Bulk collect papers from specific venues and years using OpenAlex
    
    Args:
        venue_ids: List of OpenAlex venue IDs (e.g., ['S4306420609', 'S4306419644'])
        years: List of years to collect (e.g., [2019, 2020, 2021, 2022, 2023, 2024])
        email: Optional email for polite API usage
    """
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'research-paper-collector/1.0'}
    if email:
        headers['User-Agent'] += f' (mailto:{email})'
    
    all_papers = []
    
    for venue_id in venue_ids:
        for year in years:
            print(f"\nCollecting from venue {venue_id} for year {year}")
            
            # Construct filter
            filter_str = f"primary_location.source.id:{venue_id},publication_year:{year}"
            
            # For pagination
            cursor = "*"
            page_count = 0
            
            while cursor:
                params = {
                    'filter': filter_str,
                    'per-page': 200,  # Max allowed
                    'cursor': cursor,
                    'select': 'id,doi,title,publication_year,authorships,primary_location,cited_by_count'
                }
                
                response = requests.get(base_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    all_papers.extend(results)
                    
                    page_count += 1
                    print(f"  Page {page_count}: {len(results)} papers (total so far: {len(all_papers)})")
                    
                    # Get next cursor
                    cursor = data.get('meta', {}).get('next_cursor')
                else:
                    print(f"  Error: {response.status_code}")
                    break
    
    return all_papers


def bulk_collect_by_institution(institution_id: str, years: List[int], email: str = None):
    """
    Bulk collect papers from a specific institution
    
    Mila's OpenAlex ID: I141472210
    MIT: I63966007
    Stanford: I97018004
    CMU: I78577930
    """
    base_url = "https://api.openalex.org/works"
    headers = {'User-Agent': 'research-paper-collector/1.0'}
    if email:
        headers['User-Agent'] += f' (mailto:{email})'
    
    all_papers = []
    year_range = f"{min(years)}-{max(years)}"
    
    print(f"\nCollecting papers from institution {institution_id} for years {year_range}")
    
    # Construct filter
    filter_str = f"authorships.institutions.id:{institution_id},publication_year:{year_range}"
    
    # For pagination
    cursor = "*"
    page_count = 0
    
    while cursor:
        params = {
            'filter': filter_str,
            'per-page': 200,
            'cursor': cursor,
            'select': 'id,doi,title,publication_year,authorships,primary_location,cited_by_count'
        }
        
        response = requests.get(base_url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            all_papers.extend(results)
            
            page_count += 1
            print(f"  Page {page_count}: {len(results)} papers (total so far: {len(all_papers)})")
            
            # Get next cursor
            cursor = data.get('meta', {}).get('next_cursor')
        else:
            print(f"  Error: {response.status_code}")
            break
    
    return all_papers


def main():
    # Load venue IDs
    with open('data/openalex_venue_ids.json', 'r') as f:
        venue_data = json.load(f)
    
    # Extract just the IDs for top venues
    top_venues = ['NeurIPS', 'ICML', 'ICLR', 'CVPR', 'AAAI']
    venue_ids = [venue_data[v]['id'] for v in top_venues if v in venue_data]
    
    print("Venue IDs to collect:")
    for venue in top_venues:
        if venue in venue_data:
            print(f"  {venue}: {venue_data[venue]['id']}")
    
    # Example: Collect papers from 2022-2024
    years = [2022, 2023, 2024]
    
    # Bulk collect by venues
    papers = bulk_collect_by_venues(venue_ids, years)
    print(f"\nTotal papers collected: {len(papers)}")
    
    # Example: Filter for Mila papers
    mila_papers = []
    for paper in papers:
        for authorship in paper.get('authorships', []):
            institutions = authorship.get('institutions', [])
            for inst in institutions:
                if inst.get('id') == 'https://openalex.org/I141472210':  # Mila
                    mila_papers.append(paper)
                    break
    
    print(f"Mila papers found: {len(mila_papers)}")
    
    # Alternative: Direct collection by institution
    print("\n" + "="*60)
    print("Alternative: Direct collection by institution")
    mila_papers_direct = bulk_collect_by_institution('I141472210', years)
    print(f"Mila papers (direct): {len(mila_papers_direct)}")


if __name__ == "__main__":
    main()