#!/usr/bin/env python3
"""Analyze Mila papers in detail to understand selection issues."""

import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from compute_forecast.analysis.mila.paper_selector import (
    MilaPaperSelector,
    ComputationalContentFilter,
    DomainClassifier
)


def main():
    # Load papers
    with open("/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json", 'r') as f:
        papers = json.load(f)
    
    selector = MilaPaperSelector()
    content_filter = ComputationalContentFilter()
    domain_classifier = DomainClassifier()
    
    # Filter by year
    papers_2019_2024 = selector.filter_by_year(papers, 2019, 2024)
    print(f"Papers 2019-2024: {len(papers_2019_2024)}")
    
    # Analyze computational richness
    richness_scores = []
    for paper in papers_2019_2024[:100]:  # Sample first 100
        score = content_filter.compute_richness_score(paper)
        richness_scores.append(score)
    
    print(f"\nComputational richness (first 100 papers):")
    print(f"  >= 0.4: {sum(1 for s in richness_scores if s >= 0.4)} papers")
    print(f"  >= 0.3: {sum(1 for s in richness_scores if s >= 0.3)} papers")
    print(f"  >= 0.2: {sum(1 for s in richness_scores if s >= 0.2)} papers")
    print(f"  >= 0.1: {sum(1 for s in richness_scores if s >= 0.1)} papers")
    print(f"  == 0.0: {sum(1 for s in richness_scores if s == 0.0)} papers")
    
    # Check some papers with abstracts
    print("\nSample papers with computational content:")
    count = 0
    for paper in papers_2019_2024:
        if paper.get("abstract", "").strip() and count < 5:
            score = content_filter.compute_richness_score(paper)
            if score > 0:
                print(f"\nTitle: {paper['title'][:80]}...")
                print(f"Abstract: {paper['abstract'][:200]}...")
                print(f"Richness score: {score:.3f}")
                domain = domain_classifier.classify(paper)
                print(f"Domain: {domain}")
                count += 1
    
    # Check domain classification
    domains = {}
    for paper in papers_2019_2024[:200]:  # Sample first 200
        domain = domain_classifier.classify(paper)
        domains[domain] = domains.get(domain, 0) + 1
    
    print("\nDomain classification (first 200 papers):")
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count} papers")


if __name__ == "__main__":
    main()