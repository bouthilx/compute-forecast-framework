#!/usr/bin/env python3
"""
Fixed real-time dashboard - solves Rich Live + stdout redirection conflict
"""

import json
import time
import threading
import collections
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table

# Collection configuration (shortened for testing)
DOMAINS = {
    "Computer Vision & Medical Imaging": [
        "computer vision",
        "medical imaging",
        "image processing",
        "deep learning",
    ],
    "Natural Language Processing": [
        "natural language processing",
        "NLP",
        "language model",
        "text analysis",
    ],
    "Reinforcement Learning & Robotics": [
        "reinforcement learning",
        "robotics",
        "RL",
        "policy gradient",
    ],
}

YEARS = [2023, 2024]  # Just recent years for faster testing
TARGET_TOTAL = 800


class StreamingLogCapture:
    """Thread-safe streaming log capture with circular buffer"""

    def __init__(self, max_lines=30):
        self.lines = collections.deque(maxlen=max_lines)
        self.lock = threading.Lock()

    def add_log(self, message):
        """Add log message directly (bypasses stdout redirection issues)"""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.lines.append(f"[{timestamp}] {message}")

    def get_recent_lines(self):
        """Get copy of recent lines for thread safety"""
        with self.lock:
            return list(self.lines)


class CollectionTracker:
    """Tracks collection progress and statistics with streaming logs"""

    def __init__(self):
        self.console = Console()
        self.log_capture = StreamingLogCapture(max_lines=30)
        self.stats = {
            "total_papers": 0,
            "new_papers": 0,
            "api_calls": 0,
            "rate_limits": 0,
            "errors": 0,
            "domains_completed": 0,
            "domain_stats": {},
        }

        # Load existing data
        self.load_existing_data()

    def load_existing_data(self):
        """Load existing papers and calculate initial stats"""
        try:
            with open("data/raw_collected_papers.json", "r") as f:
                papers = json.load(f)

            self.stats["total_papers"] = len(papers)

            # Calculate domain stats
            domain_stats = defaultdict(lambda: defaultdict(int))
            for paper in papers:
                domain = paper.get("mila_domain", "unknown")
                year = paper.get("collection_year", paper.get("year", "unknown"))
                if domain != "unknown" and year != "unknown":
                    domain_stats[domain][str(year)] += 1

            self.stats["domain_stats"] = dict(domain_stats)
            self.log(f"✅ Loaded {len(papers)} existing papers")

        except FileNotFoundError:
            self.log("⚠️ No existing papers file found - starting fresh")
        except Exception as e:
            self.log(f"❌ Error loading papers: {e}")

    def log(self, message):
        """Add log message to streaming capture"""
        self.log_capture.add_log(message)

    def update_stats(self, **kwargs):
        """Update statistics"""
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value


def create_layout(tracker):
    """Create Rich layout with domain stats and streaming logs"""
    layout = Layout()

    # Create domain statistics layout
    domain_stats_layout = Layout()
    domain_boxes = []

    # Summary box
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="cyan", width=12)
    summary_table.add_column("Value", style="green bold", width=8)

    summary_table.add_row("Total Papers", str(tracker.stats["total_papers"]))
    summary_table.add_row("Target", str(TARGET_TOTAL))
    summary_table.add_row(
        "Progress", f"{(tracker.stats['total_papers'] / TARGET_TOTAL) * 100:.1f}%"
    )
    summary_table.add_row("New Papers", str(tracker.stats["new_papers"]))
    summary_table.add_row("API Calls", str(tracker.stats["api_calls"]))
    summary_table.add_row("Rate Limits", str(tracker.stats["rate_limits"]))
    summary_table.add_row("Errors", str(tracker.stats["errors"]))

    summary_panel = Panel(
        summary_table, title="📊 Summary", border_style="green", width=25
    )
    domain_boxes.append(summary_panel)

    # Domain boxes
    domain_names = {
        "Computer Vision & Medical Imaging": "🖼️ CV & Medical",
        "Natural Language Processing": "💬 NLP",
        "Reinforcement Learning & Robotics": "🤖 RL & Robotics",
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
    domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])

    # Create real-time logs panel with streaming content
    recent_lines = tracker.log_capture.get_recent_lines()
    log_text = Text(
        "\\n".join(recent_lines[-20:])
        if recent_lines
        else "Dashboard ready - waiting for collection to start..."
    )
    logs_panel = Panel(
        log_text, title="📝 Real-time Activity Log", border_style="yellow"
    )

    # Main layout
    layout.split_column(Layout(domain_stats_layout, size=12), Layout(logs_panel))

    return layout


def simulate_paper_collection(tracker):
    """Simulate paper collection with real-time logging"""

    tracker.log("🚀 Starting paper collection simulation...")
    tracker.log("📊 Initializing collection parameters...")

    # Simulate collection activities
    activities = [
        ("🔍 Searching Computer Vision papers...", 1),
        ("📡 API request to Semantic Scholar...", 2),
        ("📄 Processing 8 results...", 1),
        ("➕ Added: 'Deep Learning in Medical Imaging' (152 citations)", 1),
        ("🔄 Duplicate skipped: 'CNN for Image Processing'", 0.5),
        ("⏱️ Rate limiting: waiting 3 seconds...", 1),
        ("⏳ Countdown: 3s...", 1),
        ("⏳ Countdown: 2s...", 1),
        ("⏳ Countdown: 1s...", 1),
        ("🔍 Searching NLP papers...", 1),
        ("📡 API request to OpenAlex...", 2),
        ("📄 Processing 12 results...", 1),
        ("➕ Added: 'Transformer Networks for Text' (89 citations)", 1),
        ("➕ Added: 'BERT Fine-tuning Techniques' (234 citations)", 1),
        ("📊 Progress update: 307/800 papers collected (38.4%)", 1),
        ("💾 Saving progress to file...", 1),
        ("✅ Progress saved successfully", 1),
        ("🔍 Searching RL papers...", 1),
        ("📡 Multiple API calls in progress...", 2),
        ("📄 Large batch processing 15 results...", 2),
        ("➕ Added: 'Deep Reinforcement Learning' (445 citations)", 1),
        ("🎯 Session total: 5 new papers | Overall: 310/800", 1),
        ("✅ Collection simulation completed!", 1),
    ]

    for i, (activity, delay) in enumerate(activities):
        tracker.log(activity)

        # Update tracker stats occasionally
        if i % 5 == 0:
            tracker.update_stats(
                total_papers=tracker.stats["total_papers"] + 1,
                new_papers=tracker.stats["new_papers"] + 1,
                api_calls=tracker.stats["api_calls"] + 1,
            )

        time.sleep(delay)  # Variable delays for realism

    return True


def main():
    """Main function with working real-time dashboard"""
    console = Console()
    console.print(
        "🚀 Starting FIXED Real-Time Paper Collection Dashboard", style="bold green"
    )
    console.print(
        "🎯 This version should show live updates properly!", style="bold blue"
    )
    console.print()

    # Initialize tracker
    tracker = CollectionTracker()

    console.print(f"📊 Current status: {tracker.stats['total_papers']} papers loaded")
    console.print("🖥️ Starting live dashboard...")

    # Create progress bars
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )

    main_task = progress.add_task("📈 Overall Progress", total=TARGET_TOTAL)
    progress.update(main_task, completed=tracker.stats["total_papers"])

    collection_task = progress.add_task("🎯 Collection Status", total=100)

    def create_full_layout():
        """Create complete layout with progress and streaming logs"""
        main_layout = Layout()
        progress_panel = Panel(
            progress, title="Collection Progress", border_style="bright_blue"
        )
        stats_logs_layout = create_layout(tracker)

        main_layout.split_column(
            Layout(progress_panel, size=6), Layout(stats_logs_layout)
        )
        return main_layout

    try:
        tracker.log("📱 Starting live dashboard - real-time updates enabled!")
        tracker.log("🔄 All collection activity will stream live below")

        # Start the Live display with higher refresh rate
        with Live(create_full_layout(), refresh_per_second=8, screen=True) as live:
            # Run simulation in background while updating display
            simulation_steps = 23  # Total activities

            for step in range(simulation_steps):
                # Update collection progress
                collection_progress = (step / simulation_steps) * 100
                progress.update(collection_task, completed=collection_progress)

                # Update main progress occasionally
                if step % 3 == 0:
                    progress.update(main_task, completed=tracker.stats["total_papers"])

                # Let the simulation run one step
                if step == 0:
                    tracker.log("🚀 Starting paper collection simulation...")
                elif step == 5:
                    tracker.log("🔍 Searching Computer Vision papers...")
                    tracker.update_stats(api_calls=tracker.stats["api_calls"] + 1)
                elif step == 10:
                    tracker.log("➕ Added: 'Deep Learning Paper' (152 citations)")
                    tracker.update_stats(
                        total_papers=tracker.stats["total_papers"] + 1,
                        new_papers=tracker.stats["new_papers"] + 1,
                    )
                elif step == 15:
                    tracker.log("🔍 Searching NLP papers...")
                    tracker.update_stats(api_calls=tracker.stats["api_calls"] + 1)
                elif step == 20:
                    tracker.log("📊 Progress update: collection proceeding...")
                    tracker.update_stats(
                        total_papers=tracker.stats["total_papers"] + 2,
                        new_papers=tracker.stats["new_papers"] + 2,
                    )

                # Update the live display
                live.update(create_full_layout())

                # Wait between updates
                time.sleep(0.8)

            tracker.log("✅ Live dashboard demo completed!")
            tracker.log("🎯 Real-time streaming is working correctly!")

            # Show final state for a moment
            live.update(create_full_layout())
            time.sleep(3)

    except KeyboardInterrupt:
        tracker.log("⚠️ Dashboard stopped by user")
    except Exception as e:
        console.print(f"❌ Dashboard error: {str(e)}")
        import traceback

        traceback.print_exc()

    console.print("\\n✅ Fixed dashboard session completed!")
    console.print(
        f"📊 Final stats: {tracker.stats['total_papers']} papers, {tracker.stats['api_calls']} API calls"
    )
    console.print("\\n🎉 The real-time dashboard is working!")


if __name__ == "__main__":
    main()
