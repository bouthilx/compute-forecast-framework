#!/usr/bin/env python3
"""
Enhanced paper collection with real stdout/stderr logs in UI
"""

import requests
import json
import time
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


class OutputCapture:
    def __init__(self, max_lines=30):
        self.lines = []
        self.max_lines = max_lines

    def write(self, text):
        if text.strip():  # Only capture non-empty lines
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.lines.append(f"[{timestamp}] {text.strip()}")
            # Keep only the last max_lines
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines :]

    def flush(self):
        pass

    def get_lines(self):
        return self.lines.copy()


class CollectionTracker:
    def __init__(self):
        self.console = Console()
        self.output_capture = OutputCapture()
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
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value


class PaperCollector:
    def __init__(self, tracker):
        self.tracker = tracker

    def semantic_scholar_search(self, query, year, limit=10):
        """Search Semantic Scholar API with detailed logging"""
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

            print(f"✅ Semantic Scholar completed: {len(papers)} papers extracted")
            return papers

        except Exception as e:
            print(f"❌ Semantic Scholar error: {str(e)}")
            self.tracker.update_stats(errors=self.tracker.stats["errors"] + 1)
            return []

    def openalex_search(self, query, year, limit=10):
        """Search OpenAlex API with detailed logging"""
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
                        "venue": venue.replace("...", ""),
                        "url": work.get("id", ""),
                        "source": "openalex",
                    }
                )

            print(f"✅ OpenAlex completed: {len(papers)} papers extracted")
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


def update_domain_stats(tracker, all_papers):
    """Update domain statistics in tracker"""
    domain_stats = defaultdict(lambda: defaultdict(int))

    for paper in all_papers:
        domain = paper.get("mila_domain", "unknown")
        year = paper.get("collection_year", paper.get("year", "unknown"))
        if domain != "unknown" and year != "unknown":
            domain_stats[domain][str(year)] += 1

    tracker.update_stats(domain_stats=dict(domain_stats))


def create_layout(tracker):
    """Create Rich layout with domain stats and real-time logs"""
    layout = Layout()

    # Create domain statistics boxes
    domain_stats_layout = Layout()
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

    # Create logs panel from captured stdout
    captured_lines = tracker.output_capture.get_lines()
    log_text = Text(
        "\n".join(captured_lines[-20:]) if captured_lines else "Waiting for activity..."
    )
    logs_panel = Panel(
        log_text, title="📝 Real-time Activity Log", border_style="yellow"
    )

    # Layout arrangement
    layout.split_column(Layout(domain_stats_layout, size=12), Layout(logs_panel))

    return layout


def main():
    # Initialize tracking
    tracker = CollectionTracker()
    collector = PaperCollector(tracker)

    # Load existing data
    existing_papers, existing_titles = load_existing_papers()
    current_count = len(existing_papers)
    needed = TARGET_TOTAL - current_count

    # Redirect stdout to capture print statements
    original_stdout = sys.stdout
    sys.stdout = tracker.output_capture

    try:
        print("🚀 Starting Worker 6 paper collection continuation...")
        print(f"📊 Current status: {current_count} papers collected")
        print(f"🎯 Target: {TARGET_TOTAL} papers")
        print(f"📈 Need to collect: {needed} more papers")

        tracker.update_stats(total_papers=current_count)

        # Load existing stats
        try:
            with open("data/collection_statistics.json", "r") as f:
                existing_stats = json.load(f)
            domain_stats = existing_stats.get("domain_distribution", {})
        except:
            domain_stats = defaultdict(lambda: defaultdict(int))

        all_papers = existing_papers.copy()
        new_papers_collected = 0

        # Update initial domain stats
        update_domain_stats(tracker, all_papers)

        # Create progress display
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        )

        main_task = progress.add_task("📈 Overall Progress", total=TARGET_TOTAL)
        progress.update(main_task, completed=current_count)

        domain_task = progress.add_task("🎯 Current Domain", total=100)

        # Create combined layout
        def create_full_layout():
            main_layout = Layout()
            progress_panel = Panel(
                progress, title="Collection Progress", border_style="bright_blue"
            )
            stats_logs_layout = create_layout(tracker)

            main_layout.split_column(
                Layout(progress_panel, size=6), Layout(stats_logs_layout)
            )
            return main_layout

        with Live(create_full_layout(), refresh_per_second=2):
            domain_count = 0
            for domain_name, keywords in DOMAINS.items():
                domain_count += 1
                print(f"🏗️ Processing domain {domain_count}/5: {domain_name}")
                print(f"🔑 Keywords: {', '.join(keywords[:6])}")

                progress.update(
                    domain_task, description=f"{domain_name[:20]}...", completed=0
                )
                year_count = 0

                for year in YEARS:
                    year_count += 1
                    current_domain_count = domain_stats.get(domain_name, {}).get(
                        str(year), 0
                    )
                    additional_needed = (
                        max(8, current_domain_count + 3) - current_domain_count
                    )

                    if additional_needed > 0:
                        print(
                            f"📊 {domain_name} {year}: need {additional_needed} more papers"
                        )

                        year_papers = []

                        # Use first 3 keywords for faster testing
                        for i, keyword in enumerate(keywords[:3]):
                            if len(year_papers) >= additional_needed:
                                print(
                                    f"🎯 Target reached with {len(year_papers)} papers"
                                )
                                break

                            print(f"🔍 Keyword {i+1}/3: '{keyword}'")

                            # Semantic Scholar
                            ss_papers = collector.semantic_scholar_search(
                                keyword, year, limit=5
                            )

                            # Process results
                            new_papers = 0
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
                                    new_papers += 1
                                    print(
                                        f"➕ Added: \"{paper.get('title', '')[:40]}...\""
                                    )
                                elif title in existing_titles:
                                    print(
                                        f"🔄 Duplicate: \"{paper.get('title', '')[:40]}...\""
                                    )

                            print(f"📈 Semantic Scholar: {new_papers} new papers")

                            # Rate limiting
                            print("⏱️ Rate limiting: 3 seconds...")
                            for countdown in range(3, 0, -1):
                                print(f"⏳ {countdown}s...")
                                time.sleep(1)

                            # OpenAlex
                            oa_papers = collector.openalex_search(
                                keyword, year, limit=5
                            )

                            new_papers = 0
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
                                    new_papers += 1
                                    print(
                                        f"➕ Added: \"{paper.get('title', '')[:40]}...\""
                                    )

                            print(f"📈 OpenAlex: {new_papers} new papers")
                            print("⏱️ Rate limiting: 3 seconds...")
                            for countdown in range(3, 0, -1):
                                print(f"⏳ {countdown}s...")
                                time.sleep(1)

                        # Add papers and update stats
                        all_papers.extend(year_papers)
                        new_papers_collected += len(year_papers)

                        print(
                            f"✅ {domain_name} {year}: {len(year_papers)} papers collected"
                        )

                        update_domain_stats(tracker, all_papers)
                        current_total = len(all_papers)
                        tracker.update_stats(
                            total_papers=current_total, new_papers=new_papers_collected
                        )

                        progress.update(main_task, completed=current_total)
                        print(
                            f"🎯 Total: {current_total}/800 ({(current_total/800)*100:.1f}%)"
                        )

                        # Save progress periodically
                        if new_papers_collected % 10 == 0 and new_papers_collected > 0:
                            print("💾 Saving progress...")
                            with open("data/raw_collected_papers.json", "w") as f:
                                json.dump(all_papers, f, indent=2)
                            print("✅ Progress saved")
                    else:
                        print(f"✅ {domain_name} {year}: Target already met")

                    # Update domain progress
                    domain_progress = (year_count / len(YEARS)) * 100
                    progress.update(domain_task, completed=domain_progress)

                    # Check if target reached
                    if len(all_papers) >= TARGET_TOTAL:
                        print(f"🎯 TARGET REACHED! {len(all_papers)} papers")
                        progress.update(main_task, completed=TARGET_TOTAL)
                        break

                tracker.update_stats(domains_completed=domain_count)
                print(f"🏁 Domain {domain_count} completed!")

                if len(all_papers) >= TARGET_TOTAL:
                    print("🎉 COLLECTION TARGET ACHIEVED!")
                    break

            # Final processing
            final_count = len(all_papers)
            print(f"🏁 Collection complete: {final_count} papers")
            print(f"📈 New papers this session: {new_papers_collected}")

            # Save final results
            print("💾 Saving final results...")
            with open("data/raw_collected_papers.json", "w") as f:
                json.dump(all_papers, f, indent=2)

            # Generate final statistics
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

            if final_count >= TARGET_TOTAL:
                print("🎉 COLLECTION TARGET ACHIEVED!")
                return True
            else:
                print(f"⚠️ Target not fully reached: {final_count}/{TARGET_TOTAL}")
                return False

    finally:
        # Restore original stdout
        sys.stdout = original_stdout


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Collection completed successfully!")
    else:
        print("\n⚠️ Collection improved but target not fully met")
