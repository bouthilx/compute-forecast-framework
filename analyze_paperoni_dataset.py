#!/usr/bin/env python3
"""Analyze the paperoni dataset to understand Mila papers."""

import json
from collections import defaultdict


def is_mila_paper(paper):
    """Check if a paper has Mila affiliation."""
    for author in paper.get("authors", []):
        # Check author links for Mila email
        author_links = author.get("author", {}).get("links", [])
        for link in author_links:
            if link.get("type") == "email.mila":
                return True

        # Check affiliations
        for affiliation in author.get("affiliations", []):
            name = affiliation.get("name", "").lower()
            if "mila" in name or "montreal institute" in name:
                return True
    return False


def extract_year(paper):
    """Extract publication year from paper."""
    for release in paper.get("releases", []):
        date_text = release.get("venue", {}).get("date", {}).get("text", "")
        if date_text:
            try:
                return int(date_text[:4])
            except Exception:
                pass
    return None


def main():
    # Load dataset
    with open(
        "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json",
        "r",
    ) as f:
        papers = json.load(f)

    print(f"Total papers in dataset: {len(papers)}")

    # Filter Mila papers
    mila_papers = [p for p in papers if is_mila_paper(p)]
    print(f"\nMila-affiliated papers: {len(mila_papers)}")

    # Analyze by year
    papers_by_year = defaultdict(list)
    for paper in mila_papers:
        year = extract_year(paper)
        if year and 2019 <= year <= 2024:
            papers_by_year[year].append(paper)

    print("\nPapers by year:")
    for year in sorted(papers_by_year.keys()):
        print(f"  {year}: {len(papers_by_year[year])} papers")

    # Analyze topics
    topic_counts = defaultdict(int)
    for paper in mila_papers:
        for topic in paper.get("topics", []):
            topic_counts[topic.get("name", "Unknown")] += 1

    print("\nTop topics:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"  {topic}: {count} papers")

    # Check for ML/AI papers
    ml_papers = []
    for paper in mila_papers:
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()

        ml_keywords = [
            "neural",
            "learning",
            "deep",
            "reinforcement",
            "transformer",
            "gan",
            "vae",
            "bert",
            "gpt",
            "vision",
            "nlp",
            "machine learning",
            "artificial intelligence",
            "classification",
            "detection",
        ]

        if any(kw in title or kw in abstract for kw in ml_keywords):
            ml_papers.append(paper)

    print(
        f"\nML/AI-related papers: {len(ml_papers)} ({len(ml_papers)/len(mila_papers)*100:.1f}%)"
    )

    # Sample papers with links
    print("\nSample papers with PDF links:")
    count = 0
    for paper in mila_papers[:50]:
        for link in paper.get("links", []):
            if "pdf" in link.get("type", "") or link.get("url", "").endswith(".pdf"):
                print(f"\n{paper.get('title')[:80]}...")
                print(f"  Year: {extract_year(paper)}")
                print(f"  PDF: {link.get('url', link.get('link', ''))}")
                count += 1
                if count >= 5:
                    break
        if count >= 5:
            break


if __name__ == "__main__":
    main()
