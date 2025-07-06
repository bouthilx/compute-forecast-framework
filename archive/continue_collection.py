#!/usr/bin/env python3
"""
Continue collection to reach 800+ paper target
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict

# Expanded keywords per domain for better coverage
DOMAINS = {
    "Computer Vision & Medical Imaging": [
        "computer vision",
        "medical imaging",
        "image processing",
        "deep learning",
        "CNN",
        "convolutional neural network",
        "image segmentation",
        "object detection",
        "medical AI",
        "radiology",
        "diagnostic imaging",
        "image classification",
        "feature extraction",
    ],
    "Natural Language Processing": [
        "natural language processing",
        "NLP",
        "language model",
        "text analysis",
        "machine translation",
        "transformer",
        "BERT",
        "GPT",
        "text mining",
        "sentiment analysis",
        "named entity recognition",
        "question answering",
        "text generation",
        "language understanding",
    ],
    "Reinforcement Learning & Robotics": [
        "reinforcement learning",
        "robotics",
        "RL",
        "policy gradient",
        "robot learning",
        "deep reinforcement learning",
        "Q-learning",
        "actor-critic",
        "robot control",
        "autonomous systems",
        "multi-agent",
        "robotic manipulation",
        "navigation",
    ],
    "Graph Learning & Network Analysis": [
        "graph neural network",
        "network analysis",
        "graph learning",
        "GNN",
        "social network",
        "graph convolutional network",
        "node classification",
        "link prediction",
        "graph embedding",
        "network topology",
        "complex networks",
        "graph mining",
        "knowledge graph",
    ],
    "Scientific Computing & Applications": [
        "computational biology",
        "computational physics",
        "scientific computing",
        "numerical methods",
        "simulation",
        "bioinformatics",
        "molecular dynamics",
        "finite element",
        "high performance computing",
        "computational chemistry",
        "climate modeling",
        "computational fluid dynamics",
    ],
}

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
TARGET_TOTAL = 800
CURRENT_COUNT = 187
NEEDED = TARGET_TOTAL - CURRENT_COUNT


def semantic_scholar_search(query, year, limit=10):
    """Search Semantic Scholar API with enhanced error handling"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "year": f"{year}-{year}",
        "limit": limit,
        "fields": "paperId,title,abstract,authors,year,citationCount,venue,url",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 429:
            print("    Rate limited, waiting 10 seconds...")
            time.sleep(10)
            return []

        response.raise_for_status()
        data = response.json()

        papers = []
        for paper in data.get("data", []):
            papers.append(
                {
                    "id": paper.get("paperId", ""),
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": [a.get("name", "") for a in paper.get("authors", [])],
                    "year": paper.get("year", year),
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "url": paper.get("url", ""),
                    "source": "semantic_scholar",
                }
            )

        return papers
    except Exception as e:
        print(f"    Semantic Scholar error: {e}")
        return []


def openalex_search(query, year, limit=10):
    """Search OpenAlex API with enhanced error handling"""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "filter": f"publication_year:{year}",
        "per-page": limit,
        "select": "id,title,abstract,authorships,publication_year,cited_by_count,primary_location",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 403:
            print("    OpenAlex access limited, skipping...")
            return []

        response.raise_for_status()
        data = response.json()

        papers = []
        for work in data.get("results", []):
            venue = ""
            if work.get("primary_location"):
                source_info = work["primary_location"].get("source", {})
                if source_info:
                    venue = source_info.get("display_name", "")

            papers.append(
                {
                    "id": work.get("id", ""),
                    "title": work.get("title", ""),
                    "abstract": work.get("abstract", ""),
                    "authors": [
                        a["author"]["display_name"]
                        for a in work.get("authorships", [])
                        if a.get("author")
                    ],
                    "year": work.get("publication_year", year),
                    "citations": work.get("cited_by_count", 0),
                    "venue": venue,
                    "url": work.get("id", ""),
                    "source": "openalex",
                }
            )

        return papers
    except Exception as e:
        print(f"    OpenAlex error: {e}")
        return []


def load_existing_papers():
    """Load existing papers to avoid duplicates"""
    try:
        with open("data/raw_collected_papers.json", "r") as f:
            papers = json.load(f)

        existing_titles = set()
        for paper in papers:
            title = paper.get("title", "").lower().strip()
            if title:
                existing_titles.add(title)

        return papers, existing_titles
    except FileNotFoundError:
        return [], set()


def collect_additional_papers_for_domain(
    domain_name, keywords, year, target_count, existing_titles
):
    """Collect additional papers for a domain/year with more aggressive search"""
    collected_papers = []

    # Use more keywords for better coverage
    for keyword in keywords[:8]:  # Use top 8 keywords instead of 3
        if len(collected_papers) >= target_count:
            break

        print(f"    Searching for '{keyword}' in {year}...")

        # Semantic Scholar with higher limit
        ss_papers = semantic_scholar_search(keyword, year, limit=15)
        for paper in ss_papers:
            title = paper.get("title", "").lower().strip()
            if title and title not in existing_titles:
                existing_titles.add(title)
                collected_papers.append(paper)

        time.sleep(3)  # Conservative rate limiting

        # OpenAlex with higher limit
        oa_papers = openalex_search(keyword, year, limit=15)
        for paper in oa_papers:
            title = paper.get("title", "").lower().strip()
            if title and title not in existing_titles:
                existing_titles.add(title)
                collected_papers.append(paper)

        time.sleep(3)  # Conservative rate limiting

    # Add collection metadata
    for paper in collected_papers:
        paper["mila_domain"] = domain_name
        paper["collection_year"] = year
        paper["collection_timestamp"] = datetime.now().isoformat()

    # Sort by citations and return top papers
    collected_papers.sort(key=lambda x: x.get("citations", 0), reverse=True)
    return collected_papers[:target_count]


def main():
    print("=== Worker 6: Continuing Collection to Reach 800+ Target ===")
    print(f"Current: 187 papers | Target: 800+ papers | Need: {NEEDED}+ papers")

    # Load existing papers
    existing_papers, existing_titles = load_existing_papers()
    print(f"Loaded {len(existing_papers)} existing papers")

    # Load existing stats
    try:
        with open("data/collection_statistics.json", "r") as f:
            existing_stats = json.load(f)
        domain_stats = existing_stats.get("domain_distribution", {})
    except Exception:
        domain_stats = defaultdict(lambda: defaultdict(int))

    all_papers = existing_papers.copy()
    new_papers_collected = 0

    # Update status - continuing collection
    status = {
        "worker_id": "worker6",
        "last_update": datetime.now().isoformat(),
        "overall_status": "in_progress",
        "completion_percentage": 30,
        "current_task": f"Continuing collection - need {NEEDED}+ more papers",
        "collection_progress": {
            "domains_completed": 0,
            "domains_total": 5,
            "papers_collected": len(existing_papers),
            "target_papers": TARGET_TOTAL,
        },
        "ready_for_handoff": False,
    }

    with open("status/worker6-overall.json", "w") as f:
        json.dump(status, f, indent=2)

    # Continue collection for each domain/year that needs more papers
    for domain_name, keywords in DOMAINS.items():
        print(f"\n=== Expanding {domain_name} ===")

        for year in YEARS:
            current_count = domain_stats.get(domain_name, {}).get(str(year), 0)
            target_per_year = max(
                12, current_count + 5
            )  # Target at least 12 papers per domain/year
            additional_needed = target_per_year - current_count

            if additional_needed > 0:
                print(
                    f"  {domain_name} - {year}: have {current_count}, targeting {target_per_year} (+{additional_needed})"
                )

                new_papers = collect_additional_papers_for_domain(
                    domain_name, keywords, year, additional_needed, existing_titles
                )

                all_papers.extend(new_papers)
                new_papers_collected += len(new_papers)

                print(f"    Added {len(new_papers)} new papers")

                # Update progress periodically
                if new_papers_collected % 20 == 0:
                    current_total = len(existing_papers) + new_papers_collected
                    completion_pct = min(95, 30 + (current_total / TARGET_TOTAL) * 60)

                    status["completion_percentage"] = int(completion_pct)
                    status["current_task"] = (
                        f"Collected {new_papers_collected} new papers - total {current_total}"
                    )
                    status["collection_progress"]["papers_collected"] = current_total

                    with open("status/worker6-overall.json", "w") as f:
                        json.dump(status, f, indent=2)

                    # Save progress
                    with open("data/raw_collected_papers.json", "w") as f:
                        json.dump(all_papers, f, indent=2)

            # Stop if we've reached target
            if len(all_papers) >= TARGET_TOTAL:
                print(f"\n🎯 Target reached! Total papers: {len(all_papers)}")
                break

        if len(all_papers) >= TARGET_TOTAL:
            break

    # Final save and statistics
    final_count = len(all_papers)
    print("\n=== Collection Complete ===")
    print(f"Total papers: {final_count}")
    print(f"New papers added: {new_papers_collected}")
    print(f"Target met: {final_count >= TARGET_TOTAL}")

    # Save final results
    with open("data/raw_collected_papers.json", "w") as f:
        json.dump(all_papers, f, indent=2)

    # Update final statistics
    final_domain_stats = defaultdict(lambda: defaultdict(int))
    source_distribution = defaultdict(int)

    for paper in all_papers:
        domain = paper.get("mila_domain", "unknown")
        year = paper.get("collection_year", paper.get("year", "unknown"))
        source = paper.get("source", "unknown")

        final_domain_stats[domain][str(year)] += 1
        source_distribution[source] += 1

    final_stats = {
        "collection_summary": {
            "total_papers_collected": final_count,
            "new_papers_this_session": new_papers_collected,
            "target_achieved": final_count >= TARGET_TOTAL,
            "domains_processed": len(DOMAINS),
        },
        "domain_distribution": {
            domain: dict(years) for domain, years in final_domain_stats.items()
        },
        "source_distribution": dict(source_distribution),
        "collection_metadata": {
            "continuation_timestamp": datetime.now().isoformat(),
            "target_papers": TARGET_TOTAL,
            "final_count": final_count,
        },
    }

    with open("data/collection_statistics.json", "w") as f:
        json.dump(final_stats, f, indent=2)

    # Final status update
    final_status = {
        "worker_id": "worker6",
        "last_update": datetime.now().isoformat(),
        "overall_status": "completed",
        "completion_percentage": 100,
        "current_task": f"Collection complete - {final_count} papers collected",
        "collection_progress": {
            "domains_completed": 5,
            "domains_total": 5,
            "papers_collected": final_count,
            "target_achieved": final_count >= TARGET_TOTAL,
        },
        "ready_for_handoff": True,
        "outputs_available": [
            "data/raw_collected_papers.json",
            "data/collection_statistics.json",
        ],
    }

    with open("status/worker6-overall.json", "w") as f:
        json.dump(final_status, f, indent=2)

    return final_count >= TARGET_TOTAL


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Collection target achieved!")
    else:
        print("\n⚠️ Collection improved but target not fully reached")
