#!/usr/bin/env python3
"""
Investigate specific paper c42203fba5ce89562e2d0c8e21f5f2b0 to understand its analysis status.
"""

import json
import sys
import os
from pathlib import Path

def find_paper_in_dataset(target_paper_id):
    """Find the specific paper in the dataset."""
    
    print(f"INVESTIGATING PAPER: {target_paper_id}")
    print("="*60)
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    print(f"Searching through {len(papers_data)} papers...")
    
    # Find the target paper
    target_paper = None
    for paper_json in papers_data:
        paper_id = paper_json.get('paper_id', '')
        if paper_id == target_paper_id:
            target_paper = paper_json
            break
    
    if target_paper is None:
        print(f"❌ Paper {target_paper_id} NOT FOUND in dataset")
        return None
    
    print(f"✅ Paper FOUND in dataset")
    
    # Extract basic information
    title = target_paper.get('title', 'Unknown')
    abstract = target_paper.get('abstract', '')
    
    print(f"\nBASIC INFORMATION:")
    print(f"  Title: {title}")
    print(f"  Abstract length: {len(abstract)} characters")
    
    # Extract year
    year = None
    for release in target_paper.get('releases', []):
        venue = release.get('venue', {})
        venue_date = venue.get('date', {})
        if isinstance(venue_date, dict) and 'text' in venue_date:
            try:
                year = int(venue_date['text'][:4])
                break
            except:
                continue
    
    if year:
        print(f"  Year: {year}")
    else:
        print(f"  Year: Could not extract")
    
    # Show abstract preview
    if abstract:
        print(f"\nABSTRACT PREVIEW:")
        print(f"  {abstract[:200]}...")
    
    return target_paper

def check_paper_queries(target_paper_id, paper_json):
    """Check if the paper has query analysis files."""
    
    print(f"\nQUERY ANALYSIS CHECK:")
    print("-" * 40)
    
    sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
    from paperext.utils import Paper
    
    try:
        paper = Paper(paper_json)
        if paper.queries:
            print(f"✅ Paper has {len(paper.queries)} query file(s)")
            
            # Check each query file
            for i, query_path in enumerate(paper.queries):
                print(f"\nQuery {i+1}: {query_path}")
                
                # Check if file exists
                if os.path.exists(query_path):
                    print(f"  ✅ File exists")
                    
                    # Check file size
                    file_size = os.path.getsize(query_path)
                    print(f"  File size: {file_size} bytes")
                    
                    # Try to load and examine content
                    try:
                        with open(query_path, 'r') as f:
                            analysis_data = json.load(f)
                        
                        print(f"  ✅ Valid JSON file")
                        
                        # Examine structure
                        print(f"  Top-level keys: {list(analysis_data.keys())}")
                        
                        # Look at extractions
                        extractions = analysis_data.get('extractions', {})
                        print(f"  Extraction fields: {len(extractions)}")
                        
                        if len(extractions) > 0:
                            print(f"  Extraction keys: {list(extractions.keys())}")
                            
                            # Check specific important fields
                            description = extractions.get('description')
                            if description:
                                print(f"  Description field: Present")
                                if isinstance(description, dict):
                                    desc_data = description.get('data', '')
                                    if desc_data:
                                        print(f"    Description length: {len(desc_data)} chars")
                                        print(f"    Description preview: {desc_data[:100]}...")
                                    else:
                                        print(f"    Description data: EMPTY")
                                else:
                                    print(f"    Description type: {type(description)}")
                            else:
                                print(f"  Description field: MISSING")
                            
                            # Check for research fields
                            research_field = extractions.get('primary_research_field')
                            if research_field:
                                print(f"  Primary research field: Present")
                                if isinstance(research_field, dict):
                                    field_data = research_field.get('data', '')
                                    print(f"    Field data: {field_data}")
                                else:
                                    print(f"    Field type: {type(research_field)}")
                            else:
                                print(f"  Primary research field: MISSING")
                        
                        else:
                            print(f"  ❌ NO extraction fields found")
                        
                        # Look at query/response structure
                        if 'query' in analysis_data:
                            query_text = analysis_data['query']
                            print(f"  Query length: {len(query_text)} chars")
                        
                        if 'response' in analysis_data:
                            response_text = analysis_data['response']
                            print(f"  Response length: {len(response_text)} chars")
                        
                    except json.JSONDecodeError as e:
                        print(f"  ❌ Invalid JSON: {e}")
                    except Exception as e:
                        print(f"  ❌ Error reading file: {e}")
                        
                else:
                    print(f"  ❌ File does not exist")
                    
                    # Check if directory exists
                    query_dir = os.path.dirname(query_path)
                    if os.path.exists(query_dir):
                        print(f"  Directory exists: {query_dir}")
                        # List files in directory
                        try:
                            files = os.listdir(query_dir)
                            print(f"  Files in directory: {files[:10]}")  # Show first 10 files
                        except Exception as e:
                            print(f"  Error listing directory: {e}")
                    else:
                        print(f"  Directory does not exist: {query_dir}")
        else:
            print(f"❌ Paper has NO query files")
            
    except Exception as e:
        print(f"❌ Error creating Paper object: {e}")

def check_in_domain_data(target_paper_id):
    """Check if paper appears in domain classification data."""
    
    print(f"\nDOMAIN CLASSIFICATION CHECK:")
    print("-" * 40)
    
    try:
        with open('all_domains_full.json', 'r') as f:
            raw_domains = json.load(f)
        
        # Find entries for this paper
        paper_domains = []
        for domain_entry in raw_domains:
            if domain_entry.get('paper_id') == target_paper_id:
                paper_domains.append(domain_entry)
        
        if paper_domains:
            print(f"✅ Paper found in domain data with {len(paper_domains)} domain entries")
            for i, entry in enumerate(paper_domains):
                print(f"  Domain {i+1}: {entry.get('domain_name', 'Unknown')}")
                print(f"    Title: {entry.get('title', 'Unknown')[:60]}...")
                print(f"    Year: {entry.get('year', 'Unknown')}")
        else:
            print(f"❌ Paper NOT found in domain classification data")
            
    except FileNotFoundError:
        print(f"❌ Domain data file not found")
    except Exception as e:
        print(f"❌ Error checking domain data: {e}")

def main():
    """Main investigation function."""
    
    target_paper_id = "c42203fba5ce89562e2d0c8e21f5f2b0"
    
    # Step 1: Find paper in main dataset
    paper_json = find_paper_in_dataset(target_paper_id)
    
    if paper_json is None:
        return
    
    # Step 2: Check query analysis files
    check_paper_queries(target_paper_id, paper_json)
    
    # Step 3: Check if it's in domain classification data
    check_in_domain_data(target_paper_id)
    
    # Summary
    print(f"\n" + "="*60)
    print("INVESTIGATION SUMMARY")
    print("="*60)
    print(f"Paper ID: {target_paper_id}")
    print(f"Found in main dataset: ✅")
    print(f"Title: {paper_json.get('title', 'Unknown')}")
    
    # Determine year category
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
    
    if year:
        if 2019 <= year <= 2022:
            category = "Early years (likely affected by system failure)"
        elif year >= 2023:
            category = "Recent years (should have good analysis)"
        else:
            category = "Outside target range"
        
        print(f"Year: {year} ({category})")
    
    print(f"\nThis investigation helps understand the analysis pipeline status for this specific paper.")

if __name__ == "__main__":
    main()