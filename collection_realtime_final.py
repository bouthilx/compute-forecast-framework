#!/usr/bin/env python3
"""
Paper collection with real-time streaming dashboard - FINAL VERSION
Integrates streaming logs into collection_with_progress.py structure
"""

import requests
import json
import time
import threading
import collections
import sys
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table

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


class StreamingLogCapture:
    """Thread-safe streaming log capture with circular buffer"""

    def __init__(self, max_lines=50):
        self.lines = collections.deque(maxlen=max_lines)  # Thread-safe circular buffer
        self.lock = threading.Lock()  # Thread safety for concurrent access

    def write(self, text):
        """Write text to log buffer with timestamp"""
        with self.lock:
            if text.strip():
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[
                    :-3
                ]  # Millisecond precision
                self.lines.append(f"[{timestamp}] {text.strip()}")

    def flush(self):
        """Required for stdout/stderr compatibility"""
        pass

    def get_recent_lines(self):
        """Get copy of recent lines for thread safety"""
        with self.lock:
            return list(self.lines)  # Return copy for thread safety


class CollectionTracker:
    """Tracks collection progress and statistics with streaming logs"""

    def __init__(self):
        self.console = Console()
        self.log_capture = StreamingLogCapture(max_lines=50)
        self.stats = {
            "total_papers": 0,
            "new_papers": 0,
            "api_calls": 0,
            "rate_limits": 0,
            "errors": 0,
            "domains_completed": 0,
            "domain_stats": {},
        }

    def update_stats(self, **kwargs):
        """Update statistics"""
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value


class PaperCollector:
    """Handles paper collection from APIs with real-time logging"""

    def __init__(self, tracker):
        self.tracker = tracker

    def semantic_scholar_search(self, query, year, limit=10):
        """Search Semantic Scholar API with detailed tracking"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "year": f"{year}-{year}",
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,citationCount,venue,url",
        }

        print(f"🔍 Searching Semantic Scholar: '{query}' ({year}) - limit {limit}")
        self.tracker.update_stats(api_calls=self.tracker.stats["api_calls"] + 1)

        try:
            print("📡 Making API request to Semantic Scholar...")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                print("⚠️ Rate limited by Semantic Scholar - waiting 10 seconds...")
                self.tracker.update_stats(
                    rate_limits=self.tracker.stats["rate_limits"] + 1
                )
                for i in range(10, 0, -1):
                    print(f"⏱️ Rate limit cooldown: {i}s remaining...")
                    time.sleep(1)
                return []

            response.raise_for_status()
            data = response.json()

            print(
                f"✅ API response received - processing {len(data.get('data', []))} results"
            )

            papers = []
            for i, paper in enumerate(data.get("data", [])):
                title = paper.get("title", "No title")[:50] + (
                    "..." if len(paper.get("title", "")) > 50 else ""
                )
                citations = paper.get("citationCount", 0)
                venue = paper.get("venue", "Unknown venue")[:30] + (
                    "..." if len(paper.get("venue", "")) > 30 else ""
                )

                print(f'📄 Paper {i+1}: "{title}" ({citations} citations) - {venue}')

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

            print(
                f"✅ Semantic Scholar completed: {len(papers)} papers extracted for '{query}' ({year})"
            )
            return papers

        except Exception as e:
            print(f"❌ Semantic Scholar error: {str(e)}")
            self.tracker.update_stats(errors=self.tracker.stats["errors"] + 1)
            return []

    def openalex_search(self, query, year, limit=10):
        """Search OpenAlex API with detailed tracking"""
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "filter": f"publication_year:{year}",
            "per-page": limit,
            "select": "id,title,abstract,authorships,publication_year,cited_by_count,primary_location",
        }

        print(f"🔍 Searching OpenAlex: '{query}' ({year}) - limit {limit}")
        self.tracker.update_stats(api_calls=self.tracker.stats["api_calls"] + 1)

        try:
            print("📡 Making API request to OpenAlex...")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 403:
                print("⚠️ OpenAlex access limited (403) - skipping this search")
                return []

            response.raise_for_status()
            data = response.json()

            print(
                f"✅ API response received - processing {len(data.get('results', []))} results"
            )

            papers = []
            for i, work in enumerate(data.get("results", [])):
                title = work.get("title", "No title")[:50] + (
                    "..." if len(work.get("title", "")) > 50 else ""
                )
                citations = work.get("cited_by_count", 0)

                venue = "Unknown venue"
                if work.get("primary_location"):
                    source_info = work["primary_location"].get("source", {})
                    if source_info:
                        venue = source_info.get("display_name", "Unknown venue")[
                            :30
                        ] + (
                            "..."
                            if len(source_info.get("display_name", "")) > 30
                            else ""
                        )

                print(f'📄 Paper {i+1}: "{title}" ({citations} citations) - {venue}')

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
                        "venue": venue.replace("...", ""),  # Clean venue name
                        "url": work.get("id", ""),
                        "source": "openalex",
                    }
                )

            print(
                f"✅ OpenAlex completed: {len(papers)} papers extracted for '{query}' ({year})"
            )
            return papers

        except Exception as e:
            print(f"❌ OpenAlex error: {str(e)}")
            self.tracker.update_stats(errors=self.tracker.stats["errors"] + 1)
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


def create_layout(tracker):
    """Create Rich layout with domain stats and streaming logs"""
    layout = Layout()

    # Create domain statistics layout
    domain_stats_layout = Layout()

    # Create individual domain boxes
    domain_boxes = []

    # Summary box
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="cyan", width=12)
    summary_table.add_column("Value", style="green bold", width=8)

    summary_table.add_row("Total Papers", str(tracker.stats["total_papers"]))
    summary_table.add_row("Target", "800")
    summary_table.add_row("Progress", f"{(tracker.stats['total_papers']/800)*100:.1f}%")
    summary_table.add_row("New Papers", str(tracker.stats["new_papers"]))
    summary_table.add_row("API Calls", str(tracker.stats["api_calls"]))
    summary_table.add_row("Rate Limits", str(tracker.stats["rate_limits"]))
    summary_table.add_row("Errors", str(tracker.stats["errors"]))

    summary_panel = Panel(
        summary_table, title="📊 Summary", border_style="green", width=25
    )
    domain_boxes.append(summary_panel)

    # Domain-specific boxes
    domain_names = {
        "Computer Vision & Medical Imaging": "🖼️ CV & Medical",
        "Natural Language Processing": "💬 NLP",
        "Reinforcement Learning & Robotics": "🤖 RL & Robotics",
        "Graph Learning & Network Analysis": "🕸️ Graph Learning",
        "Scientific Computing & Applications": "🔬 Sci Computing",
    }

    for domain_full, domain_short in domain_names.items():
        domain_table = Table(show_header=False, box=None, padding=(0, 1))
        domain_table.add_column("Year", style="cyan", width=6)
        domain_table.add_column("Papers", style="green", width=6)

        domain_total = 0
        for year in YEARS:
            count = (
                tracker.stats.get("domain_stats", {})
                .get(domain_full, {})
                .get(str(year), 0)
            )
            domain_total += count
            domain_table.add_row(str(year), str(count))

        domain_table.add_row("─────", "─────")
        domain_table.add_row("Total", f"[bold]{domain_total}[/bold]")

        domain_panel = Panel(
            domain_table, title=domain_short, border_style="blue", width=16
        )
        domain_boxes.append(domain_panel)

    # Arrange domain boxes horizontally
    if len(domain_boxes) > 1:
        domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])
    else:
        domain_stats_layout = Layout(domain_boxes[0])

    # Create real-time logs panel with streaming content
    recent_lines = tracker.log_capture.get_recent_lines()

    # Show last 25 lines of streaming logs
    log_text = Text(
        "\\n".join(recent_lines[-25:])
        if recent_lines
        else "Waiting for collection activity..."
    )
    logs_panel = Panel(
        log_text, title="📝 Real-time Activity Log", border_style="yellow"
    )

    # Layout arrangement
    layout.split_column(Layout(domain_stats_layout, size=12), Layout(logs_panel))

    return layout


def update_domain_stats(tracker, all_papers):
    """Update domain statistics in tracker"""
    domain_stats = defaultdict(lambda: defaultdict(int))

    for paper in all_papers:
        domain = paper.get("mila_domain", "unknown")
        year = paper.get("collection_year", paper.get("year", "unknown"))
        if domain != "unknown" and year != "unknown":
            domain_stats[domain][str(year)] += 1

    tracker.update_stats(domain_stats=dict(domain_stats))


def main():
    # Initialize tracking
    tracker = CollectionTracker()
    collector = PaperCollector(tracker)

    # Load existing data
    existing_papers, existing_titles = load_existing_papers()
    current_count = len(existing_papers)
    needed = TARGET_TOTAL - current_count

    print("🚀 Starting Worker 6 paper collection with real-time streaming...")
    print(f"📊 Current status: {current_count} papers collected")
    print(f"🎯 Target: {TARGET_TOTAL} papers")
    print(f"📈 Need to collect: {needed} more papers")
    print(f"🔍 Will search {len(DOMAINS)} domains across {len(YEARS)} years")
    tracker.update_stats(total_papers=current_count)

    # Load existing stats for domain tracking
    try:
        with open("data/collection_statistics.json", "r") as f:
            existing_stats = json.load(f)
        domain_stats = existing_stats.get("domain_distribution", {})
    except Exception:
        domain_stats = defaultdict(lambda: defaultdict(int))

    all_papers = existing_papers.copy()
    new_papers_collected = 0

    # Update initial domain stats
    update_domain_stats(tracker, all_papers)

    # Create separate progress display
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )

    # Main progress task
    main_task = progress.add_task("📈 Overall Progress", total=TARGET_TOTAL)
    progress.update(main_task, completed=current_count)

    # Domain progress task
    domain_task = progress.add_task("🎯 Current Domain", total=100)

    # Create combined layout with progress at top
    def create_full_layout():
        main_layout = Layout()

        # Progress panel
        progress_panel = Panel(
            progress, title="Collection Progress", border_style="bright_blue"
        )

        # Stats and logs layout
        stats_logs_layout = create_layout(tracker)

        # Combine vertically
        main_layout.split_column(
            Layout(progress_panel, size=6), Layout(stats_logs_layout)
        )

        return main_layout

    # Redirect stdout to capture print statements in real-time
    original_stdout = sys.stdout
    sys.stdout = tracker.log_capture

    try:
        # Initial streaming log messages
        print("🚀 Real-time streaming dashboard initialized successfully")
        print(f"📊 Starting with {current_count} existing papers")
        print(f"🎯 Target: {TARGET_TOTAL} papers")
        print(f"📈 Need: {needed} more papers")
        print("🔄 All collection activity will stream live below...")

        with Live(
            create_full_layout(), refresh_per_second=6
        ):  # High refresh rate for real-time feel
            domain_count = 0
            for domain_name, keywords in DOMAINS.items():
                domain_count += 1
                print(f"🏗️ Processing domain {domain_count}/5: {domain_name}")
                print(f"🔑 Keywords for this domain: {', '.join(keywords[:6])}")

                progress.update(
                    domain_task, description=f"{domain_name[:20]}...", completed=0
                )
                year_count = 0

                for year in YEARS:
                    year_count += 1
                    current_domain_count = domain_stats.get(domain_name, {}).get(
                        str(year), 0
                    )
                    target_per_year = max(
                        15, current_domain_count + 8
                    )  # Target 15+ papers per domain/year
                    additional_needed = target_per_year - current_domain_count

                    if additional_needed > 0:
                        print(
                            f"📊 {domain_name} {year}: have {current_domain_count}, targeting {additional_needed} more papers"
                        )

                        year_papers = []

                        # Use multiple keywords for better coverage
                        for i, keyword in enumerate(keywords[:6]):  # Use top 6 keywords
                            if len(year_papers) >= additional_needed:
                                print(
                                    f"🎯 Target reached for {domain_name} {year} with {len(year_papers)} papers"
                                )
                                break

                            print(
                                f"🔍 Keyword {i+1}/6: Searching for '{keyword}' in {domain_name} {year}"
                            )

                            # Semantic Scholar
                            ss_papers = collector.semantic_scholar_search(
                                keyword, year, limit=10
                            )

                            # Process Semantic Scholar results
                            new_papers_from_ss = 0
                            for paper in ss_papers:
                                title = paper.get("title", "").lower().strip()
                                if (
                                    title
                                    and title not in existing_titles
                                    and len(year_papers) < additional_needed
                                ):
                                    existing_titles.add(title)
                                    paper["mila_domain"] = domain_name
                                    paper["collection_year"] = year
                                    paper["collection_timestamp"] = (
                                        datetime.now().isoformat()
                                    )
                                    year_papers.append(paper)
                                    new_papers_from_ss += 1
                                    print(
                                        f"➕ Added paper: \"{paper.get('title', 'No title')[:40]}...\" ({paper.get('citations', 0)} citations)"
                                    )
                                elif title in existing_titles:
                                    print(
                                        f"🔄 Duplicate skipped: \"{paper.get('title', 'No title')[:40]}...\""
                                    )

                            print(
                                f"📈 Semantic Scholar: {new_papers_from_ss} new papers added from {len(ss_papers)} results"
                            )

                            # Rate limiting with countdown
                            print(
                                "⏱️ Rate limiting: waiting 3 seconds before next API call..."
                            )
                            for countdown in range(3, 0, -1):
                                print(f"⏳ Countdown: {countdown}s...")
                                time.sleep(1)

                            # OpenAlex
                            oa_papers = collector.openalex_search(
                                keyword, year, limit=10
                            )

                            # Process OpenAlex results
                            new_papers_from_oa = 0
                            for paper in oa_papers:
                                title = paper.get("title", "").lower().strip()
                                if (
                                    title
                                    and title not in existing_titles
                                    and len(year_papers) < additional_needed
                                ):
                                    existing_titles.add(title)
                                    paper["mila_domain"] = domain_name
                                    paper["collection_year"] = year
                                    paper["collection_timestamp"] = (
                                        datetime.now().isoformat()
                                    )
                                    year_papers.append(paper)
                                    new_papers_from_oa += 1
                                    print(
                                        f"➕ Added paper: \"{paper.get('title', 'No title')[:40]}...\" ({paper.get('citations', 0)} citations)"
                                    )
                                elif title in existing_titles:
                                    print(
                                        f"🔄 Duplicate skipped: \"{paper.get('title', 'No title')[:40]}...\""
                                    )

                            print(
                                f"📈 OpenAlex: {new_papers_from_oa} new papers added from {len(oa_papers)} results"
                            )

                            # Rate limiting with countdown
                            print(
                                "⏱️ Rate limiting: waiting 3 seconds before next keyword..."
                            )
                            for countdown in range(3, 0, -1):
                                print(f"⏳ Countdown: {countdown}s...")
                                time.sleep(1)

                        # Add collected papers
                        all_papers.extend(year_papers)
                        new_papers_collected += len(year_papers)

                        print(
                            f"✅ {domain_name} {year} completed: {len(year_papers)} papers collected this year"
                        )

                        # Update domain stats
                        update_domain_stats(tracker, all_papers)
                        print("📊 Domain statistics updated")

                        # Update progress
                        current_total = len(all_papers)
                        tracker.update_stats(
                            total_papers=current_total, new_papers=new_papers_collected
                        )

                        progress.update(main_task, completed=current_total)
                        print(
                            f"🎯 Session total: {len(year_papers)} new papers | Overall total: {current_total}/800 ({(current_total/800)*100:.1f}%)"
                        )

                        # Save progress periodically
                        if new_papers_collected % 25 == 0 and new_papers_collected > 0:
                            print(
                                f"💾 Saving progress: {current_total} papers collected so far..."
                            )
                            with open("data/raw_collected_papers.json", "w") as f:
                                json.dump(all_papers, f, indent=2)
                            print("✅ Progress saved to data/raw_collected_papers.json")
                    else:
                        print(
                            f"✅ {domain_name} {year}: Already has {current_domain_count} papers (target met)"
                        )

                    # Update domain progress
                    domain_progress = (year_count / len(YEARS)) * 100
                    progress.update(domain_task, completed=domain_progress)

                    # Check if target reached
                    if len(all_papers) >= TARGET_TOTAL:
                        print(f"🎯 TARGET REACHED! Total: {len(all_papers)} papers")
                        progress.update(main_task, completed=TARGET_TOTAL)
                        break

                tracker.update_stats(domains_completed=domain_count)
                print(f"🏁 Domain {domain_count} ({domain_name}) completed!")

                if len(all_papers) >= TARGET_TOTAL:
                    print(
                        f"🎯 TARGET ACHIEVED! Collected {len(all_papers)} papers - stopping collection"
                    )
                    break

            # Final processing
            final_count = len(all_papers)
            print("🏁 Collection session complete!")
            print(f"📊 Final count: {final_count} papers")
            print(f"📈 New papers this session: {new_papers_collected}")
            print(
                f"🎯 Target achievement: {(final_count/TARGET_TOTAL)*100:.1f}% ({final_count}/{TARGET_TOTAL})"
            )

            # Save final results
            print("💾 Saving final results to data/raw_collected_papers.json...")
            with open("data/raw_collected_papers.json", "w") as f:
                json.dump(all_papers, f, indent=2)
            print("✅ Papers saved successfully")

            # Update statistics
            print("📊 Generating final collection statistics...")
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
                    "api_calls_made": tracker.stats["api_calls"],
                    "rate_limits_hit": tracker.stats["rate_limits"],
                    "errors_encountered": tracker.stats["errors"],
                },
                "domain_distribution": {
                    domain: dict(years) for domain, years in final_domain_stats.items()
                },
                "source_distribution": dict(source_distribution),
                "collection_metadata": {
                    "session_timestamp": datetime.now().isoformat(),
                    "target_papers": TARGET_TOTAL,
                    "final_count": final_count,
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

            print("✅ All files saved successfully!")
            print("🎉 Real-time streaming collection completed!")

            return final_count >= TARGET_TOTAL

    except KeyboardInterrupt:
        print("⚠️ Collection interrupted by user")
        # Save partial progress
        with open("data/raw_collected_papers.json", "w") as f:
            json.dump(all_papers, f, indent=2)
        print("💾 Partial progress saved")
        return False

    finally:
        # Restore original stdout
        sys.stdout = original_stdout


if __name__ == "__main__":
    success = main()
    if success:
        print("\\n✅ Real-time collection completed successfully!")
    else:
        print("\\n⚠️ Collection improved but target not fully met")
