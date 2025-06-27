#!/usr/bin/env python3

import sys
import json
import os

# Add paperext src to Python path
sys.path.insert(0, '/home/bouthilx/projects/paperext/src')

from paperext.paper import Paper

def main():
    # Load the dataset
    dataset_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    
    print("Loading dataset...")
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    # Find papers from 2024
    papers_2024 = []
    for paper_data in data:
        for release in paper_data.get('releases', []):
            venue = release.get('venue', {})
            date = venue.get('date', {})
            date_text = date.get('text', '')
            if '2024' in date_text:
                papers_2024.append(paper_data)
                break
    
    print(f"Found {len(papers_2024)} papers from 2024")
    
    if not papers_2024:
        print("No 2024 papers found!")
        return
    
    # Take the first 2024 paper
    paper_data = papers_2024[0]
    paper_id = paper_data['paper_id']
    title = paper_data['title']
    
    print(f"\nSelected paper:")
    print(f"ID: {paper_id}")
    print(f"Title: {title}")
    
    # Create Paper instance
    paper = Paper(paper_id)
    
    # Get query file path
    query_file_path = paper.get_query_file_path()
    print(f"\nQuery file path: {query_file_path}")
    
    # Check if query file exists
    if os.path.exists(query_file_path):
        print("Query file exists!")
        
        # Read and display the query file structure
        with open(query_file_path, 'r') as f:
            query_data = json.load(f)
        
        print(f"\nQuery file structure:")
        print(f"Keys: {list(query_data.keys())}")
        
        # Check for extractions and analysis fields
        if 'extractions' in query_data:
            print(f"\n'extractions' field found:")
            extractions = query_data['extractions']
            print(f"  Type: {type(extractions)}")
            if isinstance(extractions, dict):
                print(f"  Keys: {list(extractions.keys())}")
            elif isinstance(extractions, list):
                print(f"  Length: {len(extractions)}")
                if extractions:
                    print(f"  First item type: {type(extractions[0])}")
                    if isinstance(extractions[0], dict):
                        print(f"  First item keys: {list(extractions[0].keys())}")
        else:
            print("\n'extractions' field NOT found")
            
        if 'analysis' in query_data:
            print(f"\n'analysis' field found:")
            analysis = query_data['analysis']
            print(f"  Type: {type(analysis)}")
            if isinstance(analysis, dict):
                print(f"  Keys: {list(analysis.keys())}")
            elif isinstance(analysis, list):
                print(f"  Length: {len(analysis)}")
        else:
            print("\n'analysis' field NOT found")
            
        # Show full structure (pretty printed, but limited)
        print("\n=== FULL QUERY FILE STRUCTURE ===")
        print(json.dumps(query_data, indent=2)[:2000] + "..." if len(json.dumps(query_data, indent=2)) > 2000 else json.dumps(query_data, indent=2))
        
    else:
        print("Query file does NOT exist!")

if __name__ == "__main__":
    main()