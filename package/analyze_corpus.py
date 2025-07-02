#!/usr/bin/env python3
"""Analyze the paper corpus to understand data structure and affiliation availability."""

import json
from collections import Counter

# Load the paper corpus
with open("data/raw_collected_papers.json", "r") as f:
    papers = json.load(f)

print(f"Total papers: {len(papers)}")

# Analyze affiliations
papers_with_affiliations = 0
affiliation_counts = Counter()
papers_by_year = Counter()

for paper in papers:
    papers_by_year[paper.get("year", "Unknown")] += 1
    
    if "authors" in paper and isinstance(paper["authors"], list):
        has_affiliation = False
        for author in paper["authors"]:
            if isinstance(author, dict) and author.get("affiliation", "").strip():
                has_affiliation = True
                affiliation_counts[author["affiliation"]] += 1
        
        if has_affiliation:
            papers_with_affiliations += 1

print(f"\nPapers with affiliations: {papers_with_affiliations} ({papers_with_affiliations/len(papers)*100:.1f}%)")
print(f"\nPapers by year:")
for year in sorted(papers_by_year.keys()):
    print(f"  {year}: {papers_by_year[year]}")

# Check for target benchmark institutions
target_orgs = ['DeepMind', 'Google Research', 'MIT', 'Stanford', 
               'Berkeley', 'CMU', 'Oxford', 'Meta AI', 'Facebook AI']

print(f"\nTop 20 affiliations:")
for affiliation, count in affiliation_counts.most_common(20):
    print(f"  {affiliation}: {count}")

# Check for papers from target institutions
target_papers = 0
for paper in papers:
    if "authors" in paper and isinstance(paper["authors"], list):
        for author in paper["authors"]:
            if isinstance(author, dict):
                affiliation = author.get("affiliation", "").lower()
                for target in target_orgs:
                    if target.lower() in affiliation:
                        target_papers += 1
                        break
                else:
                    continue
                break

print(f"\nPapers from target benchmark institutions: {target_papers}")

# Check title and abstract patterns
sota_count = 0
sota_patterns = ["state-of-the-art", "sota", "new record", "outperform", "best performance"]

for paper in papers:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    if any(pattern in text for pattern in sota_patterns):
        sota_count += 1

print(f"\nPapers with SOTA indicators: {sota_count}")