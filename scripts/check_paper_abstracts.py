#!/usr/bin/env python3
"""Check abstract availability in Mila papers."""

import json

with open(
    "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json",
    "r",
) as f:
    papers = json.load(f)

# Count papers with/without abstracts
total = len(papers)
with_abstract = sum(1 for p in papers if p.get("abstract", "").strip())
without_abstract = total - with_abstract

print(f"Total papers: {total}")
print(f"With abstract: {with_abstract} ({with_abstract / total * 100:.1f}%)")
print(f"Without abstract: {without_abstract} ({without_abstract / total * 100:.1f}%)")

# Check papers with PDF links
with_pdf = 0
arxiv_pdf = 0
for paper in papers:
    for link in paper.get("links", []):
        if "pdf" in link.get("type", "") or link.get("url", "").endswith(".pdf"):
            with_pdf += 1
            if "arxiv" in link.get("url", ""):
                arxiv_pdf += 1
            break

print(f"\nWith PDF links: {with_pdf} ({with_pdf / total * 100:.1f}%)")
print(f"With ArXiv PDF: {arxiv_pdf} ({arxiv_pdf / total * 100:.1f}%)")
