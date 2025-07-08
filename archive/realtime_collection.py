#!/usr/bin/env python3
"""
Real-time collection with visible progress - NO Rich Live, just clear prints
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict

# Collection configuration
DOMAINS = {
    "Computer Vision & Medical Imaging": [
        "computer vision",
        "medical imaging",
        "image processing",
        "deep learning",
        "CNN",
    ],
    "Natural Language Processing": [
        "natural language processing",
        "NLP",
        "language model",
        "text analysis",
        "transformer",
    ],
    "Reinforcement Learning & Robotics": [
        "reinforcement learning",
        "robotics",
        "RL",
        "policy gradient",
        "robot learning",
    ],
    "Graph Learning & Network Analysis": [
        "graph neural network",
        "network analysis",
        "graph learning",
        "GNN",
        "social network",
    ],
    "Scientific Computing & Applications": [
        "computational biology",
        "scientific computing",
        "numerical methods",
        "simulation",
    ],
}

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
TARGET_TOTAL = 800


class RealTimeTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.stats = {
            "total_papers": 0,
            "new_papers": 0,
            "api_calls": 0,
            "rate_limits": 0,
            "errors": 0,
        }
        self.domain_stats = defaultdict(lambda: defaultdict(int))
        self.recent_logs = []

    def load_existing_papers(self):
        """Load existing papers"""
        try:
            with open("data/raw_collected_papers.json", "r") as f:
                papers = json.load(f)
            self.stats["total_papers"] = len(papers)

            # Calculate domain stats
            for paper in papers:
                domain = paper.get("mila_domain", "unknown")
                year = paper.get("collection_year", paper.get("year", "unknown"))
                if domain != "unknown" and year != "unknown":
                    self.domain_stats[domain][str(year)] += 1

            return papers, {
                paper.get("title", "").lower().strip()
                for paper in papers
                if paper.get("title")
            }
        except FileNotFoundError:
            return [], set()

    def log(self, message):
        """Add log message and print immediately"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.recent_logs.append(log_entry)
        if len(self.recent_logs) > 10:  # Keep last 10 logs
            self.recent_logs = self.recent_logs[-10:]
        print(log_entry)

    def print_status(self):
        """Print current status - you'll see this in real-time!"""
        elapsed = datetime.now() - self.start_time
        progress_pct = (self.stats["total_papers"] / TARGET_TOTAL) * 100

        print("\n" + "=" * 80)
        print("🚀 WORKER 6 PAPER COLLECTION - REAL-TIME STATUS")
        print(f"⏱️  Runtime: {elapsed}")
        print(
            f"📊 Progress: {self.stats['total_papers']}/{TARGET_TOTAL} papers ({progress_pct:.1f}%)"
        )
        print(f"📈 New this session: {self.stats['new_papers']} papers")
        print(
            f"🔧 API calls: {self.stats['api_calls']} | Rate limits: {self.stats['rate_limits']} | Errors: {self.stats['errors']}"
        )

        # Show domain breakdown
        print("\n📂 DOMAIN BREAKDOWN:")
        for domain, years in self.domain_stats.items():
            total = sum(years.values())
            print(f"  {domain}: {total} papers")
            year_str = " | ".join(
                [f"{year}:{count}" for year, count in sorted(years.items())]
            )
            print(f"    {year_str}")

        # Show recent activity
        print("\n📝 RECENT ACTIVITY:")
        for log in self.recent_logs[-5:]:  # Show last 5 logs
            print(f"  {log}")

        print("=" * 80 + "\n")


class PaperCollector:
    def __init__(self, tracker):
        self.tracker = tracker

    def semantic_scholar_search(self, query, year, limit=10):
        """Search Semantic Scholar with real-time logging"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "year": f"{year}-{year}",
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,citationCount,venue,url",
        }

        self.tracker.log(f"🔍 Searching Semantic Scholar: '{query}' ({year})")
        self.tracker.stats["api_calls"] += 1

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                self.tracker.log("⚠️ Rate limited - waiting 10 seconds...")
                self.tracker.stats["rate_limits"] += 1
                for i in range(10, 0, -1):
                    print(f"⏳ Rate limit cooldown: {i}s remaining...")
                    time.sleep(1)
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
                        "authors": [
                            a.get("name", "") for a in paper.get("authors", [])
                        ],
                        "year": paper.get("year", year),
                        "citations": paper.get("citationCount", 0),
                        "venue": paper.get("venue", ""),
                        "url": paper.get("url", ""),
                        "source": "semantic_scholar",
                    }
                )

            self.tracker.log(f"✅ Found {len(papers)} papers from Semantic Scholar")
            return papers

        except Exception as e:
            self.tracker.log(f"❌ Semantic Scholar error: {str(e)}")
            self.tracker.stats["errors"] += 1
            return []

    def openalex_search(self, query, year, limit=10):
        """Search OpenAlex with real-time logging"""
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "filter": f"publication_year:{year}",
            "per-page": limit,
            "select": "id,title,abstract,authorships,publication_year,cited_by_count,primary_location",
        }

        self.tracker.log(f"🔍 Searching OpenAlex: '{query}' ({year})")
        self.tracker.stats["api_calls"] += 1

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 403:
                self.tracker.log("⚠️ OpenAlex access limited - skipping")
                return []

            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                venue = "Unknown venue"
                if work.get("primary_location"):
                    source_info = work["primary_location"].get("source", {})
                    if source_info:
                        venue = source_info.get("display_name", "Unknown venue")

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

            self.tracker.log(f"✅ Found {len(papers)} papers from OpenAlex")
            return papers

        except Exception as e:
            self.tracker.log(f"❌ OpenAlex error: {str(e)}")
            self.tracker.stats["errors"] += 1
            return []


def main():
    print("🚀 STARTING WORKER 6 - REAL-TIME PAPER COLLECTION")
    print("📊 You will see live updates every few seconds!")
    print("⌨️ Press Ctrl+C to stop at any time")
    print("\n" + "=" * 80)

    # Initialize
    tracker = RealTimeTracker()
    collector = PaperCollector(tracker)

    # Load existing data
    existing_papers, existing_titles = tracker.load_existing_papers()

    print(f"📂 Loaded {len(existing_papers)} existing papers")
    tracker.print_status()

    # Start collection
    all_papers = existing_papers.copy()

    try:
        domain_count = 0
        for domain_name, keywords in DOMAINS.items():
            domain_count += 1

            tracker.log(f"🏗️ STARTING DOMAIN {domain_count}/5: {domain_name}")
            tracker.print_status()

            for year in YEARS:
                current_count = tracker.domain_stats[domain_name][str(year)]
                target = max(
                    12, current_count + 5
                )  # Target at least 12 per domain/year
                needed = target - current_count

                if needed > 0:
                    tracker.log(
                        f"📅 {year}: need {needed} more papers (have {current_count}, target {target})"
                    )

                    year_papers = []

                    # Use top 3 keywords for this domain/year
                    for keyword in keywords[:3]:
                        if len(year_papers) >= needed:
                            break

                        tracker.log(f"🔑 Searching keyword: '{keyword}'")

                        # Semantic Scholar
                        ss_papers = collector.semantic_scholar_search(
                            keyword, year, limit=8
                        )

                        # Process results
                        for paper in ss_papers:
                            title = paper.get("title", "").lower().strip()
                            if (
                                title
                                and title not in existing_titles
                                and len(year_papers) < needed
                            ):
                                existing_titles.add(title)
                                paper["mila_domain"] = domain_name
                                paper["collection_year"] = year
                                paper["collection_timestamp"] = (
                                    datetime.now().isoformat()
                                )
                                year_papers.append(paper)

                                tracker.log(
                                    f'➕ Added: "{paper.get("title", "")[:50]}..." ({paper.get("citations", 0)} cites)'
                                )

                        # Rate limiting
                        tracker.log("⏱️ Rate limiting: 3 seconds...")
                        time.sleep(3)

                        # OpenAlex
                        oa_papers = collector.openalex_search(keyword, year, limit=8)

                        # Process results
                        for paper in oa_papers:
                            title = paper.get("title", "").lower().strip()
                            if (
                                title
                                and title not in existing_titles
                                and len(year_papers) < needed
                            ):
                                existing_titles.add(title)
                                paper["mila_domain"] = domain_name
                                paper["collection_year"] = year
                                paper["collection_timestamp"] = (
                                    datetime.now().isoformat()
                                )
                                year_papers.append(paper)

                                tracker.log(
                                    f'➕ Added: "{paper.get("title", "")[:50]}..." ({paper.get("citations", 0)} cites)'
                                )

                        # Rate limiting
                        tracker.log("⏱️ Rate limiting: 3 seconds...")
                        time.sleep(3)

                    # Update stats
                    all_papers.extend(year_papers)
                    tracker.stats["new_papers"] += len(year_papers)
                    tracker.stats["total_papers"] = len(all_papers)
                    tracker.domain_stats[domain_name][str(year)] = current_count + len(
                        year_papers
                    )

                    tracker.log(
                        f"✅ {domain_name} {year}: collected {len(year_papers)} papers"
                    )

                    # Save progress every 20 new papers
                    if (
                        tracker.stats["new_papers"] % 20 == 0
                        and tracker.stats["new_papers"] > 0
                    ):
                        tracker.log("💾 Saving progress...")
                        with open("data/raw_collected_papers.json", "w") as f:
                            json.dump(all_papers, f, indent=2)
                        tracker.log("✅ Progress saved!")

                else:
                    tracker.log(
                        f"✅ {domain_name} {year}: target already met ({current_count} papers)"
                    )

                # Show status every few iterations
                if (domain_count * 6 + YEARS.index(year)) % 3 == 0:
                    tracker.print_status()

                # Check if target reached
                if len(all_papers) >= TARGET_TOTAL:
                    tracker.log(
                        f"🎯 TARGET REACHED! {len(all_papers)} papers collected!"
                    )
                    break

            tracker.log(f"🏁 COMPLETED DOMAIN {domain_count}: {domain_name}")
            tracker.print_status()

            if len(all_papers) >= TARGET_TOTAL:
                break

        # Final save and summary
        tracker.log("💾 Saving final results...")

        with open("data/raw_collected_papers.json", "w") as f:
            json.dump(all_papers, f, indent=2)

        # Generate final statistics
        final_stats = {
            "collection_summary": {
                "total_papers_collected": len(all_papers),
                "new_papers_this_session": tracker.stats["new_papers"],
                "target_achieved": len(all_papers) >= TARGET_TOTAL,
                "api_calls_made": tracker.stats["api_calls"],
                "rate_limits_hit": tracker.stats["rate_limits"],
                "errors_encountered": tracker.stats["errors"],
                "collection_duration": str(datetime.now() - tracker.start_time),
            },
            "domain_distribution": {
                domain: dict(years) for domain, years in tracker.domain_stats.items()
            },
            "collection_metadata": {
                "session_timestamp": datetime.now().isoformat(),
                "target_papers": TARGET_TOTAL,
                "final_count": len(all_papers),
            },
        }

        with open("data/collection_statistics.json", "w") as f:
            json.dump(final_stats, f, indent=2)

        # Update worker status
        final_status = {
            "worker_id": "worker6",
            "last_update": datetime.now().isoformat(),
            "overall_status": "completed",
            "completion_percentage": 100,
            "current_task": f"Collection complete - {len(all_papers)} papers collected",
            "collection_progress": {
                "domains_completed": len(DOMAINS),
                "domains_total": len(DOMAINS),
                "papers_collected": len(all_papers),
                "target_achieved": len(all_papers) >= TARGET_TOTAL,
            },
            "ready_for_handoff": True,
            "outputs_available": [
                "data/raw_collected_papers.json",
                "data/collection_statistics.json",
            ],
        }

        with open("status/worker6-overall.json", "w") as f:
            json.dump(final_status, f, indent=2)

        tracker.log("✅ All files saved successfully!")
        tracker.print_status()

        print("\n" + "🎉" * 20)
        print("🎉 COLLECTION COMPLETED!")
        print(f"📊 Final count: {len(all_papers)} papers")
        print(f"📈 New papers this session: {tracker.stats['new_papers']}")
        print(f"🎯 Target achieved: {len(all_papers) >= TARGET_TOTAL}")
        print(f"⏱️ Total runtime: {datetime.now() - tracker.start_time}")
        print("🎉" * 20)

        return len(all_papers) >= TARGET_TOTAL

    except KeyboardInterrupt:
        tracker.log("⚠️ Collection interrupted by user")
        tracker.print_status()

        # Save partial progress
        with open("data/raw_collected_papers.json", "w") as f:
            json.dump(all_papers, f, indent=2)
        tracker.log("💾 Partial progress saved")

        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Worker 6 collection completed successfully!")
    else:
        print("\n⚠️ Collection stopped - progress saved")
