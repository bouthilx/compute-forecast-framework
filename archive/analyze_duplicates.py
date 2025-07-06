#!/usr/bin/env python3
"""
Analyze duplicates in collected papers data
"""

import json
import re
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from typing import List, Dict, Set
import hashlib


def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    if not title:
        return ""

    # Convert to lowercase
    title = title.lower()

    # Remove extra whitespace
    title = re.sub(r"\s+", " ", title).strip()

    # Remove common punctuation that might vary
    title = re.sub(r"[^\w\s]", "", title)

    # Remove common prefixes/suffixes that might be inconsistent
    title = re.sub(r"^(the|a|an)\s+", "", title)
    title = re.sub(r"\s+(paper|study|analysis|approach|method)$", "", title)

    return title


def normalize_authors(authors: List) -> Set[str]:
    """Normalize author list for comparison"""
    if not authors:
        return set()

    normalized = set()
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name", "")
        else:
            name = str(author)

        if name:
            # Normalize name: lowercase, remove extra spaces
            name = re.sub(r"\s+", " ", name.lower().strip())
            # Remove common prefixes/suffixes
            name = re.sub(r"^(dr|prof|professor)\s+", "", name)
            normalized.add(name)

    return normalized


def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles"""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    if not norm1 or not norm2:
        return 0.0

    return SequenceMatcher(None, norm1, norm2).ratio()


def author_overlap(authors1: List, authors2: List) -> float:
    """Calculate author overlap between two papers"""
    set1 = normalize_authors(authors1)
    set2 = normalize_authors(authors2)

    if not set1 or not set2:
        return 0.0

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def generate_paper_hash(paper: Dict) -> str:
    """Generate a hash for a paper based on key fields"""
    title = normalize_title(paper.get("title", ""))
    year = str(paper.get("year", ""))

    # Create hash from normalized title + year
    content = f"{title}|{year}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def analyze_duplicates():
    """Analyze duplicates in the collected papers"""

    print("🔍 Analyzing Duplicates in Collected Papers")
    print("=" * 60)

    # Load the data
    try:
        with open(
            "/home/bouthilx/projects/preliminary_report/package/data/raw_collected_papers.json",
            "r",
        ) as f:
            papers = json.load(f)

        print(f"📊 Loaded {len(papers)} papers from raw_collected_papers.json")

    except FileNotFoundError:
        print("❌ File data/raw_collected_papers.json not found")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return

    if not papers:
        print("⚠️  No papers found in file")
        return

    # Analysis 1: Exact title matches (case-insensitive)
    print("\n📋 Analysis 1: Exact Title Matches")
    print("-" * 40)

    title_groups = defaultdict(list)
    for i, paper in enumerate(papers):
        title = paper.get("title", "")
        if title:
            normalized = normalize_title(title)
            if normalized:  # Only count non-empty titles
                title_groups[normalized].append((i, paper))

    exact_duplicates = {
        title: papers_list
        for title, papers_list in title_groups.items()
        if len(papers_list) > 1
    }

    print(f"   Unique normalized titles: {len(title_groups)}")
    print(f"   Titles with duplicates: {len(exact_duplicates)}")
    print(
        f"   Total duplicate papers: {sum(len(papers_list) - 1 for papers_list in exact_duplicates.values())}"
    )

    # Show examples of exact duplicates
    if exact_duplicates:
        print("\n   📝 Examples of exact title duplicates:")
        for i, (title, papers_list) in enumerate(list(exact_duplicates.items())[:3]):
            print(f"   {i+1}. \"{papers_list[0][1].get('title', 'N/A')[:60]}...\"")
            print(f"      Found {len(papers_list)} times:")
            for j, (idx, paper) in enumerate(papers_list[:3]):
                source = paper.get("source", "unknown")
                year = paper.get("year", "unknown")
                print(f"         - Paper {idx}: {source} ({year})")
            if len(papers_list) > 3:
                print(f"         - ... and {len(papers_list) - 3} more")
            print()

    # Analysis 2: Hash-based duplicates
    print("\n📋 Analysis 2: Hash-based Duplicates (Title + Year)")
    print("-" * 50)

    hash_groups = defaultdict(list)
    for i, paper in enumerate(papers):
        paper_hash = generate_paper_hash(paper)
        hash_groups[paper_hash].append((i, paper))

    hash_duplicates = {
        h: papers_list for h, papers_list in hash_groups.items() if len(papers_list) > 1
    }

    print(f"   Unique hashes: {len(hash_groups)}")
    print(f"   Hashes with duplicates: {len(hash_duplicates)}")
    print(
        f"   Total hash duplicate papers: {sum(len(papers_list) - 1 for papers_list in hash_duplicates.values())}"
    )

    # Analysis 3: Similar titles (fuzzy matching)
    print("\n📋 Analysis 3: Similar Titles (>90% similarity)")
    print("-" * 45)

    similar_pairs = []
    processed = set()

    # Only check first 1000 papers to avoid performance issues
    sample_size = min(1000, len(papers))
    print(f"   Checking similarity for first {sample_size} papers...")

    for i in range(sample_size):
        for j in range(i + 1, sample_size):
            if (i, j) in processed:
                continue

            paper1 = papers[i]
            paper2 = papers[j]

            title1 = paper1.get("title", "")
            title2 = paper2.get("title", "")

            if title1 and title2:
                similarity = title_similarity(title1, title2)
                if similarity > 0.9:  # 90% similarity threshold
                    similar_pairs.append((i, j, similarity, paper1, paper2))
                    processed.add((i, j))

    print(f"   Found {len(similar_pairs)} similar title pairs (>90% similarity)")

    if similar_pairs:
        print("\n   📝 Examples of similar titles:")
        for i, (idx1, idx2, sim, p1, p2) in enumerate(similar_pairs[:3]):
            print(f"   {i+1}. Similarity: {sim:.2%}")
            print(f"      Paper {idx1}: \"{p1.get('title', 'N/A')[:50]}...\"")
            print(f"      Paper {idx2}: \"{p2.get('title', 'N/A')[:50]}...\"")
            print(
                f"      Sources: {p1.get('source', 'unknown')} vs {p2.get('source', 'unknown')}"
            )
            print()

    # Analysis 4: Source distribution
    print("\n📋 Analysis 4: Source Distribution")
    print("-" * 35)

    source_counts = Counter()
    for paper in papers:
        source = paper.get("source", "unknown")
        source_counts[source] += 1

    print("   Papers by source:")
    for source, count in source_counts.most_common():
        percentage = (count / len(papers)) * 100
        print(f"      {source}: {count:,} papers ({percentage:.1f}%)")

    # Analysis 5: Cross-source duplicates
    print("\n📋 Analysis 5: Cross-Source Duplicates")
    print("-" * 38)

    cross_source_duplicates = 0
    same_source_duplicates = 0

    for title, papers_list in exact_duplicates.items():
        sources = set(paper.get("source", "unknown") for _, paper in papers_list)
        if len(sources) > 1:
            cross_source_duplicates += len(papers_list) - 1
        else:
            same_source_duplicates += len(papers_list) - 1

    print(f"   Cross-source duplicates: {cross_source_duplicates}")
    print(f"   Same-source duplicates: {same_source_duplicates}")

    # Analysis 6: Year distribution of duplicates
    print("\n📋 Analysis 6: Year Distribution of Duplicates")
    print("-" * 42)

    duplicate_years = Counter()
    for title, papers_list in exact_duplicates.items():
        for _, paper in papers_list:
            year = paper.get("year")
            if year:
                duplicate_years[year] += 1

    if duplicate_years:
        print("   Duplicates by year (top 5):")
        for year, count in duplicate_years.most_common(5):
            print(f"      {year}: {count} duplicate papers")

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 20)
    print(f"Total papers analyzed: {len(papers):,}")
    print(
        f"Exact title duplicates: {sum(len(papers_list) - 1 for papers_list in exact_duplicates.values()):,}"
    )
    print(
        f"Hash duplicates: {sum(len(papers_list) - 1 for papers_list in hash_duplicates.values()):,}"
    )
    print(f"Similar title pairs: {len(similar_pairs):,}")
    print(f"Cross-source duplicates: {cross_source_duplicates:,}")
    print(f"Same-source duplicates: {same_source_duplicates:,}")

    duplication_rate = (
        sum(len(papers_list) - 1 for papers_list in exact_duplicates.values())
        / len(papers)
    ) * 100
    print(f"Overall duplication rate: {duplication_rate:.1f}%")

    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 18)
    if duplication_rate > 10:
        print("⚠️  High duplication rate detected!")
        print("   - Consider implementing deduplication before analysis")
        print("   - Check collection logic for potential over-collection")
    elif duplication_rate > 5:
        print("⚠️  Moderate duplication detected")
        print("   - Consider light deduplication")
    else:
        print("✅ Low duplication rate - acceptable for analysis")

    if cross_source_duplicates > same_source_duplicates:
        print("   - Good: Most duplicates are cross-source (expected)")
    else:
        print("   - Review: Many same-source duplicates (potential collection issue)")


if __name__ == "__main__":
    analyze_duplicates()
