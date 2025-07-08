#!/usr/bin/env python3
"""
Continue collection to reach 800+ paper target with Rich Dashboard

A comprehensive dashboard for monitoring paper collection progress across research domains
with real-time statistics, progress bars, and structured logging using Rich.
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import (
    Progress,
    TaskID,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.table import Table
from rich.live import Live
from rich.logging import RichHandler
from rich.align import Align
from rich.columns import Columns
from rich.text import Text
import logging

# Configure logging with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("collection")

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


@dataclass
class DomainProgress:
    """Progress tracking for a specific domain."""

    name: str
    papers_by_year: Dict[int, int] = field(default_factory=dict)
    target_per_year: int = 12
    total_papers: int = 0
    new_papers_added: int = 0
    current_year: Optional[int] = None
    current_keyword: str = ""
    keywords_processed: int = 0
    total_keywords: int = 8

    @property
    def total_target(self) -> int:
        return self.target_per_year * len(YEARS)

    @property
    def completion_percentage(self) -> float:
        return (
            (self.total_papers / self.total_target) * 100
            if self.total_target > 0
            else 0
        )


@dataclass
class CollectionStats:
    """Overall collection statistics."""

    total_papers: int = CURRENT_COUNT
    new_papers_collected: int = 0
    target_papers: int = TARGET_TOTAL
    domains_completed: int = 0
    total_domains: int = len(DOMAINS)
    start_time: datetime = field(default_factory=datetime.now)
    api_calls_made: int = 0
    rate_limit_hits: int = 0
    source_distribution: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )

    @property
    def overall_percentage(self) -> float:
        return (
            (self.total_papers / self.target_papers) * 100
            if self.target_papers > 0
            else 0
        )

    @property
    def papers_remaining(self) -> int:
        return max(0, self.target_papers - self.total_papers)


class CollectionDashboard:
    """Rich-based dashboard for paper collection monitoring."""

    def __init__(self):
        self.console = Console()
        self.layout = Layout()

        # Progress tracking
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        # Initialize stats
        self.stats = CollectionStats()
        self.domain_progress: Dict[str, DomainProgress] = {
            name: DomainProgress(name=name) for name in DOMAINS.keys()
        }

        # Progress task IDs
        self.main_task_id: Optional[TaskID] = None
        self.domain_task_ids: Dict[str, TaskID] = {}

        # Log messages
        self.log_messages: List[str] = []

        self._setup_layout()
        self._load_existing_data()
        self._initialize_progress_tasks()

    def _setup_layout(self):
        """Setup the Rich layout structure."""
        self.layout.split_column(
            Layout(name="header", size=4),
            Layout(name="progress", size=8),
            Layout(name="stats", size=12),
            Layout(name="logs", minimum_size=8),
        )

        # Split stats into domain boxes and summary
        self.layout["stats"].split_row(
            Layout(name="domain_stats", ratio=3), Layout(name="summary_stats", ratio=1)
        )

    def _load_existing_data(self):
        """Load existing papers and statistics."""
        try:
            # Load existing papers
            papers_file = Path("data/raw_collected_papers.json")
            if papers_file.exists():
                with open(papers_file) as f:
                    papers = json.load(f)
                self.stats.total_papers = len(papers)
                self.add_log(f"Loaded {len(papers)} existing papers", "info")

            # Load existing statistics
            stats_file = Path("data/collection_statistics.json")
            if stats_file.exists():
                with open(stats_file) as f:
                    existing_stats = json.load(f)

                domain_stats = existing_stats.get("domain_distribution", {})
                for domain_name, years_data in domain_stats.items():
                    if domain_name in self.domain_progress:
                        for year_str, count in years_data.items():
                            if year_str.isdigit():
                                year = int(year_str)
                                self.domain_progress[domain_name].papers_by_year[
                                    year
                                ] = count

                        # Calculate total papers for domain
                        self.domain_progress[domain_name].total_papers = sum(
                            years_data.values()
                        )

                # Load source distribution
                source_dist = existing_stats.get("source_distribution", {})
                self.stats.source_distribution.update(source_dist)

                self.add_log("Loaded existing collection statistics", "info")

        except Exception as e:
            self.add_log(f"Error loading existing data: {e}", "error")

    def _initialize_progress_tasks(self):
        """Initialize progress tracking tasks."""
        # Main collection progress
        self.main_task_id = self.progress.add_task(
            "Overall Collection Progress", total=self.stats.target_papers
        )

        # Domain progress tasks
        for domain_name in DOMAINS.keys():
            task_id = self.progress.add_task(
                f"{domain_name[:20]}...",
                total=self.domain_progress[domain_name].total_target,
            )
            self.domain_task_ids[domain_name] = task_id

        self._update_progress_tasks()

    def _update_progress_tasks(self):
        """Update all progress task values."""
        # Update main progress
        if self.main_task_id is not None:
            self.progress.update(self.main_task_id, completed=self.stats.total_papers)

        # Update domain progress
        for domain_name, progress_data in self.domain_progress.items():
            if domain_name in self.domain_task_ids:
                self.progress.update(
                    self.domain_task_ids[domain_name],
                    completed=progress_data.total_papers,
                )

    def create_header(self) -> Panel:
        """Create the header panel."""
        elapsed = datetime.now() - self.stats.start_time

        header_text = Text()
        header_text.append(
            "Paper Collection Dashboard - Continue Collection\n", style="bold cyan"
        )
        header_text.append(
            f"Target: {self.stats.target_papers} papers | ", style="white"
        )
        header_text.append(
            f"Current: {self.stats.total_papers} | ",
            style="green" if self.stats.total_papers >= TARGET_TOTAL else "yellow",
        )
        header_text.append(
            f"Remaining: {self.stats.papers_remaining}\n",
            style="red" if self.stats.papers_remaining > 0 else "green",
        )
        header_text.append(
            f"Runtime: {elapsed} | API Calls: {self.stats.api_calls_made} | Rate Limits: {self.stats.rate_limit_hits}",
            style="dim",
        )

        return Panel(Align.center(header_text), style="bold blue")

    def create_progress_panel(self) -> Panel:
        """Create the progress panel."""
        self._update_progress_tasks()
        return Panel(
            self.progress, title="[bold green]Collection Progress", border_style="green"
        )

    def create_domain_stats_panel(self) -> Panel:
        """Create domain statistics panels."""
        domain_panels = []

        for domain_name, progress_data in self.domain_progress.items():
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            # Status indicator
            if progress_data.current_year:
                status = f"Processing {progress_data.current_year}"
                if progress_data.current_keyword:
                    status += f"\n'{progress_data.current_keyword[:15]}...'"
                style = "yellow"
            elif progress_data.completion_percentage >= 100:
                status = "Completed"
                style = "green"
            else:
                status = "Pending"
                style = "red"

            table.add_row("Status", status)
            table.add_row(
                "Papers", f"{progress_data.total_papers}/{progress_data.total_target}"
            )
            table.add_row("Progress", f"{progress_data.completion_percentage:.1f}%")
            table.add_row("New Added", f"+{progress_data.new_papers_added}")

            if progress_data.current_year and progress_data.total_keywords > 0:
                kw_progress = (
                    f"{progress_data.keywords_processed}/{progress_data.total_keywords}"
                )
                table.add_row("Keywords", kw_progress)

            # Recent years
            recent_years = (
                sorted(progress_data.papers_by_year.keys())[-2:]
                if progress_data.papers_by_year
                else []
            )
            for year in recent_years:
                table.add_row(f"{year}", f"{progress_data.papers_by_year[year]}")

            # Short domain name for display
            short_name = domain_name.split()[0]
            if len(domain_name.split()) > 1:
                short_name += f" {domain_name.split()[1][:4]}"

            panel = Panel(
                table, title=f"[{style}]{short_name}[/{style}]", border_style=style
            )
            domain_panels.append(panel)

        return Panel(
            Columns(domain_panels, equal=True, expand=True),
            title="[bold blue]Domain Progress",
            border_style="blue",
        )

    def create_summary_panel(self) -> Panel:
        """Create overall summary statistics panel."""
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="bold white")

        # Collection statistics
        table.add_row("Total Papers", f"{self.stats.total_papers:,}")
        table.add_row("New Collected", f"+{self.stats.new_papers_collected:,}")
        table.add_row("Target Progress", f"{self.stats.overall_percentage:.1f}%")
        table.add_row("Papers Needed", f"{self.stats.papers_remaining:,}")

        # API statistics
        table.add_row("API Calls", f"{self.stats.api_calls_made:,}")
        table.add_row("Rate Limits", f"{self.stats.rate_limit_hits}")

        # Source distribution
        total_sources = sum(self.stats.source_distribution.values())
        if total_sources > 0:
            for source, count in sorted(self.stats.source_distribution.items()):
                pct = (count / total_sources) * 100
                table.add_row(source.title(), f"{count} ({pct:.0f}%)")

        # Time estimates
        elapsed = datetime.now() - self.stats.start_time
        if self.stats.new_papers_collected > 0 and elapsed.total_seconds() > 0:
            rate = self.stats.new_papers_collected / (
                elapsed.total_seconds() / 60
            )  # papers per minute
            if rate > 0 and self.stats.papers_remaining > 0:
                eta_minutes = self.stats.papers_remaining / rate
                table.add_row("ETA", f"{eta_minutes:.0f}m")

        return Panel(table, title="[bold magenta]Summary Stats", border_style="magenta")

    def create_logs_panel(self) -> Panel:
        """Create the logs panel."""
        recent_logs = (
            self.log_messages[-12:]
            if self.log_messages
            else ["[dim]No logs yet...[/dim]"]
        )
        log_text = "\n".join(recent_logs)

        return Panel(
            log_text, title="[bold yellow]Collection Logs", border_style="yellow"
        )

    def add_log(self, message: str, level: str = "info"):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        level_colors = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "success": "green",
            "api": "cyan",
        }

        color = level_colors.get(level, "white")
        formatted_message = (
            f"[dim]{timestamp}[/dim] [{color}]{level.upper()}[/{color}] {message}"
        )

        self.log_messages.append(formatted_message)
        logger.info(message)

    def update_domain_progress(self, domain: str, **kwargs):
        """Update progress for a specific domain."""
        if domain in self.domain_progress:
            progress_data = self.domain_progress[domain]

            for key, value in kwargs.items():
                if hasattr(progress_data, key):
                    setattr(progress_data, key, value)

    def update_stats(self, **kwargs):
        """Update overall collection statistics."""
        for key, value in kwargs.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, value)

    def update_display(self):
        """Update all dashboard components."""
        self.layout["header"].update(self.create_header())
        self.layout["progress"].update(self.create_progress_panel())
        self.layout["domain_stats"].update(self.create_domain_stats_panel())
        self.layout["summary_stats"].update(self.create_summary_panel())
        self.layout["logs"].update(self.create_logs_panel())


# API Functions with dashboard integration
def semantic_scholar_search(query, year, limit=10, dashboard=None):
    """Search Semantic Scholar API with enhanced error handling and dashboard updates"""
    if dashboard:
        dashboard.update_stats(api_calls_made=dashboard.stats.api_calls_made + 1)
        dashboard.add_log(
            f"Querying Semantic Scholar: '{query[:30]}...' for {year}", "api"
        )

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
            if dashboard:
                dashboard.update_stats(
                    rate_limit_hits=dashboard.stats.rate_limit_hits + 1
                )
                dashboard.add_log(
                    "Rate limited by Semantic Scholar, waiting 10s...", "warning"
                )
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
                    "venue_type": "conference"
                    if any(
                        kw in paper.get("venue", "").lower()
                        for kw in ["conference", "proceedings", "workshop"]
                    )
                    else "journal",
                    "url": paper.get("url", ""),
                    "source": "semantic_scholar",
                }
            )

        if dashboard:
            dashboard.add_log(
                f"Semantic Scholar returned {len(papers)} papers", "success"
            )

        return papers
    except Exception as e:
        if dashboard:
            dashboard.add_log(f"Semantic Scholar error: {e}", "error")
        return []


def openalex_search(query, year, limit=10, dashboard=None):
    """Search OpenAlex API with enhanced error handling and dashboard updates"""
    if dashboard:
        dashboard.update_stats(api_calls_made=dashboard.stats.api_calls_made + 1)
        dashboard.add_log(f"Querying OpenAlex: '{query[:30]}...' for {year}", "api")

    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "filter": f"publication_year:{year}",
        "per-page": limit,
        "select": "id,title,abstract,authorships,publication_year,cited_by_count,primary_location",
        "mailto": "research@mila.quebec",  # Add email for better rate limits
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 403:
            if dashboard:
                dashboard.add_log("OpenAlex access limited, skipping...", "warning")
            return []

        response.raise_for_status()
        data = response.json()

        papers = []
        for work in data.get("results", []):
            venue = ""
            venue_type = "unknown"
            if work.get("primary_location"):
                source_info = work["primary_location"].get("source", {})
                if source_info:
                    venue = source_info.get("display_name", "")
                    # Determine venue type from OpenAlex source type
                    source_type = source_info.get("type", "").lower()
                    if source_type in ["journal"]:
                        venue_type = "journal"
                    elif source_type in ["conference", "proceedings"]:
                        venue_type = "conference"
                    elif "workshop" in venue.lower():
                        venue_type = "workshop"

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
                    "venue_type": venue_type,
                    "url": work.get("id", ""),
                    "source": "openalex",
                }
            )

        if dashboard:
            dashboard.add_log(f"OpenAlex returned {len(papers)} papers", "success")

        return papers
    except Exception as e:
        if dashboard:
            dashboard.add_log(f"OpenAlex error: {e}", "error")
        return []


def openalex_batched_search(keywords, year, limit_per_keyword=15, dashboard=None):
    """Batch multiple keyword searches in a single OpenAlex API call using OR syntax"""
    if not keywords:
        return []

    if dashboard:
        dashboard.update_stats(api_calls_made=dashboard.stats.api_calls_made + 1)
        dashboard.add_log(
            f"Batched OpenAlex query for {len(keywords)} keywords in {year}", "api"
        )

    # Create OR query with up to 8 keywords (OpenAlex recommendation for performance)
    keywords_batch = keywords[:8]
    or_query = " OR ".join([f'"{keyword}"' for keyword in keywords_batch])

    url = "https://api.openalex.org/works"
    params = {
        "search": or_query,
        "filter": f"publication_year:{year}",
        "per-page": min(
            100, limit_per_keyword * len(keywords_batch)
        ),  # Max 100 per request
        "select": "id,title,abstract,authorships,publication_year,cited_by_count,primary_location",
        "mailto": "research@mila.quebec",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 403:
            if dashboard:
                dashboard.add_log(
                    "OpenAlex access limited, skipping batch...", "warning"
                )
            return []

        response.raise_for_status()
        data = response.json()

        papers = []
        for work in data.get("results", []):
            venue = ""
            venue_type = "unknown"
            if work.get("primary_location"):
                source_info = work["primary_location"].get("source", {})
                if source_info:
                    venue = source_info.get("display_name", "")
                    # Determine venue type from OpenAlex source type
                    source_type = source_info.get("type", "").lower()
                    if source_type in ["journal"]:
                        venue_type = "journal"
                    elif source_type in ["conference", "proceedings"]:
                        venue_type = "conference"
                    elif "workshop" in venue.lower():
                        venue_type = "workshop"

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
                    "venue_type": venue_type,
                    "url": work.get("id", ""),
                    "source": "openalex_batched",
                    "matched_keywords": keywords_batch,  # Track which keywords were batched
                }
            )

        if dashboard:
            dashboard.add_log(
                f"Batched OpenAlex returned {len(papers)} papers for {len(keywords_batch)} keywords",
                "success",
            )

        return papers
    except Exception as e:
        if dashboard:
            dashboard.add_log(f"Batched OpenAlex error: {e}", "error")
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
    domain_name, keywords, year, target_count, existing_titles, dashboard=None
):
    """Collect additional papers for a domain/year with dashboard updates and API batching"""
    collected_papers = []

    if dashboard:
        dashboard.update_domain_progress(
            domain_name,
            current_year=year,
            keywords_processed=0,
            total_keywords=min(8, len(keywords)),
        )
        dashboard.add_log(
            f"Starting collection for {domain_name} - {year} (target: {target_count})",
            "info",
        )

    # Strategy 1: Batched OpenAlex search (much more efficient)
    if dashboard:
        dashboard.update_domain_progress(
            domain_name, current_keyword="Batched OpenAlex Search"
        )
        dashboard.update_display()

    batched_oa_papers = openalex_batched_search(
        keywords[:8], year, limit_per_keyword=15, dashboard=dashboard
    )
    for paper in batched_oa_papers:
        title = paper.get("title", "").lower().strip()
        if title and title not in existing_titles:
            existing_titles.add(title)
            collected_papers.append(paper)
            if dashboard:
                dashboard.stats.source_distribution["openalex_batched"] += 1

    time.sleep(2)  # Brief pause between API calls

    # Strategy 2: Individual Semantic Scholar searches (fallback for additional coverage)
    # Only if we need more papers after batched search
    if len(collected_papers) < target_count:
        remaining_needed = target_count - len(collected_papers)
        keywords_to_search = min(4, len(keywords))  # Reduced individual searches

        if dashboard:
            dashboard.add_log(
                f"Need {remaining_needed} more papers, doing individual Semantic Scholar searches",
                "info",
            )

        for i, keyword in enumerate(keywords[:keywords_to_search]):
            if len(collected_papers) >= target_count:
                break

            if dashboard:
                dashboard.update_domain_progress(
                    domain_name,
                    current_keyword=f"SS: {keyword}",
                    keywords_processed=i + 1,
                )
                dashboard.update_display()

            # Semantic Scholar individual search
            ss_papers = semantic_scholar_search(
                keyword, year, limit=10, dashboard=dashboard
            )
            for paper in ss_papers:
                title = paper.get("title", "").lower().strip()
                if title and title not in existing_titles:
                    existing_titles.add(title)
                    collected_papers.append(paper)
                    if dashboard:
                        dashboard.stats.source_distribution["semantic_scholar"] += 1

            time.sleep(2)  # Reduced rate limiting since we're doing fewer calls

    # Strategy 3: Additional individual OpenAlex searches if still needed
    if len(collected_papers) < target_count:
        remaining_needed = target_count - len(collected_papers)

        if dashboard:
            dashboard.add_log(
                f"Still need {remaining_needed} papers, doing individual OpenAlex searches",
                "info",
            )

        # Use different keywords for individual searches to avoid duplicates
        additional_keywords = keywords[8:12] if len(keywords) > 8 else keywords[4:8]

        for i, keyword in enumerate(additional_keywords):
            if len(collected_papers) >= target_count:
                break

            if dashboard:
                dashboard.update_domain_progress(
                    domain_name,
                    current_keyword=f"OA: {keyword}",
                    keywords_processed=keywords_to_search + i + 1,
                )
                dashboard.update_display()

            oa_papers = openalex_search(keyword, year, limit=10, dashboard=dashboard)
            for paper in oa_papers:
                title = paper.get("title", "").lower().strip()
                if title and title not in existing_titles:
                    existing_titles.add(title)
                    collected_papers.append(paper)
                    if dashboard:
                        dashboard.stats.source_distribution["openalex"] += 1

            time.sleep(2)

    # Add collection metadata
    for paper in collected_papers:
        paper["mila_domain"] = domain_name
        paper["collection_year"] = year
        paper["collection_timestamp"] = datetime.now().isoformat()

    # Sort by citations and return top papers
    collected_papers.sort(key=lambda x: x.get("citations", 0), reverse=True)
    final_papers = collected_papers[:target_count]

    if dashboard:
        dashboard.update_domain_progress(
            domain_name,
            new_papers_added=dashboard.domain_progress[domain_name].new_papers_added
            + len(final_papers),
            current_year=None,
            current_keyword="",
        )

        # Log API efficiency stats
        efficiency_msg = f"Collected {len(final_papers)} papers with reduced API calls (batching used)"
        dashboard.add_log(efficiency_msg, "success")

    return final_papers


def main():
    """Main collection function with dashboard"""
    dashboard = CollectionDashboard()

    with Live(dashboard.layout, refresh_per_second=2, screen=True):
        try:
            dashboard.add_log(
                "Starting continued collection to reach 800+ target", "info"
            )
            dashboard.add_log(
                f"Current: {CURRENT_COUNT} papers | Target: {TARGET_TOTAL} | Need: {NEEDED}+",
                "info",
            )

            # Load existing papers
            existing_papers, existing_titles = load_existing_papers()
            dashboard.add_log(
                f"Loaded {len(existing_papers)} existing papers", "success"
            )

            # Load existing stats
            try:
                with open("data/collection_statistics.json", "r") as f:
                    existing_stats = json.load(f)
                domain_stats = existing_stats.get("domain_distribution", {})
            except Exception:
                domain_stats = defaultdict(lambda: defaultdict(int))

            all_papers = existing_papers.copy()
            new_papers_collected = 0

            # Continue collection for each domain/year that needs more papers
            for domain_name, keywords in DOMAINS.items():
                dashboard.add_log(f"Expanding {domain_name}", "info")

                for year in YEARS:
                    current_count = domain_stats.get(domain_name, {}).get(str(year), 0)
                    target_per_year = max(
                        12, current_count + 5
                    )  # Target at least 12 papers per domain/year
                    additional_needed = target_per_year - current_count

                    if additional_needed > 0:
                        dashboard.add_log(
                            f"{domain_name} - {year}: have {current_count}, need +{additional_needed}",
                            "info",
                        )

                        new_papers = collect_additional_papers_for_domain(
                            domain_name,
                            keywords,
                            year,
                            additional_needed,
                            existing_titles,
                            dashboard,
                        )

                        all_papers.extend(new_papers)
                        new_papers_collected += len(new_papers)

                        # Update statistics
                        dashboard.update_stats(
                            total_papers=len(all_papers),
                            new_papers_collected=new_papers_collected,
                        )

                        # Update domain progress
                        domain_progress = dashboard.domain_progress[domain_name]
                        domain_progress.papers_by_year[year] = current_count + len(
                            new_papers
                        )
                        domain_progress.total_papers = sum(
                            domain_progress.papers_by_year.values()
                        )

                        dashboard.add_log(
                            f"Added {len(new_papers)} papers for {domain_name} {year}",
                            "success",
                        )
                        dashboard.update_display()

                        # Save progress periodically
                        if new_papers_collected % 20 == 0:
                            with open("data/raw_collected_papers.json", "w") as f:
                                json.dump(all_papers, f, indent=2)
                            dashboard.add_log("Progress saved", "info")

                    # Stop if we've reached target
                    if len(all_papers) >= TARGET_TOTAL:
                        dashboard.add_log(
                            f"🎯 Target reached! Total papers: {len(all_papers)}",
                            "success",
                        )
                        break

                if len(all_papers) >= TARGET_TOTAL:
                    break

            # Final save and statistics
            final_count = len(all_papers)
            dashboard.add_log("Collection completed!", "success")
            dashboard.add_log(f"Total papers: {final_count}", "info")
            dashboard.add_log(f"New papers added: {new_papers_collected}", "info")
            dashboard.add_log(
                f"Target achieved: {final_count >= TARGET_TOTAL}",
                "success" if final_count >= TARGET_TOTAL else "warning",
            )

            # Update final stats
            dashboard.update_stats(
                total_papers=final_count,
                new_papers_collected=new_papers_collected,
                domains_completed=len(DOMAINS),
            )
            dashboard.update_display()

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

            dashboard.add_log("Final statistics saved", "success")

            # Keep dashboard open for a few seconds to show final state
            time.sleep(5)

            return final_count >= TARGET_TOTAL

        except KeyboardInterrupt:
            dashboard.add_log("Collection interrupted by user", "warning")
            return False
        except Exception as e:
            dashboard.add_log(f"Collection error: {e}", "error")
            return False


if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("🎉 Collection target achieved!")
    else:
        print("⚠️ Collection improved but target not fully reached")
    print("=" * 60)
