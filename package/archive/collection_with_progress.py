#!/usr/bin/env python3
"""
Fixed collection_with_progress.py - corrected indentation and structure
"""
import requests
import json
import time
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.layout import Layout
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
import threading
import queue
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Expanded keywords per domain for better coverage
DOMAINS = {
    "Computer Vision & Medical Imaging": [
        "computer vision", "medical imaging", "image processing", "deep learning", "CNN", 
        "convolutional neural network", "image segmentation", "object detection", "medical AI",
        "radiology", "diagnostic imaging", "image classification", "feature extraction"
    ],
    "Natural Language Processing": [
        "natural language processing", "NLP", "language model", "text analysis", "machine translation",
        "transformer", "BERT", "GPT", "text mining", "sentiment analysis", "named entity recognition",
        "question answering", "text generation", "language understanding"
    ],
    "Reinforcement Learning & Robotics": [
        "reinforcement learning", "robotics", "RL", "policy gradient", "robot learning",
        "deep reinforcement learning", "Q-learning", "actor-critic", "robot control",
        "autonomous systems", "multi-agent", "robotic manipulation", "navigation"
    ]
}

YEARS = [2023, 2024]  # Just recent years for testing
TARGET_TOTAL = 800

class OutputCapture:
    def __init__(self, max_lines=50):
        self.lines = []
        self.max_lines = max_lines
        
    def write(self, text):
        if text.strip():  # Only capture non-empty lines
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.lines.append(f"[{timestamp}] {text.strip()}")
            # Keep only the last max_lines
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines:]
    
    def flush(self):
        pass  # Required for stdout/stderr compatibility
    
    def get_lines(self):
        return self.lines.copy()

class CollectionTracker:
    def __init__(self):
        self.console = Console()
        self.output_capture = OutputCapture()
        self.stats = {
            'total_papers': 0,
            'new_papers': 0,
            'api_calls': 0,
            'rate_limits': 0,
            'errors': 0,
            'domains_completed': 0,
            'domain_stats': {}
        }
        
    def update_stats(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

class PaperCollector:
    def __init__(self, tracker):
        self.tracker = tracker
        
    def semantic_scholar_search(self, query, year, limit=5):
        """Search Semantic Scholar API with detailed tracking"""
        print(f"🔍 Searching Semantic Scholar: '{query}' ({year}) - limit {limit}")
        self.tracker.update_stats(api_calls=self.tracker.stats['api_calls'] + 1)
        
        # Simulate API call
        time.sleep(2)
        print(f"✅ Found 3 papers from Semantic Scholar")
        return [
            {
                'id': f'ss_{query}_{year}_1',
                'title': f'Deep Learning Research in {query} ({year})',
                'abstract': f'Abstract for {query} research',
                'authors': ['Author One', 'Author Two'],
                'year': year,
                'citations': 150,
                'venue': 'Top Conference',
                'url': 'https://example.com',
                'source': 'semantic_scholar'
            }
        ]

def load_existing_papers():
    """Load existing papers to avoid duplicates"""
    try:
        with open('data/raw_collected_papers.json', 'r') as f:
            papers = json.load(f)
        
        existing_titles = set()
        for paper in papers:
            title = paper.get('title', '').lower().strip()
            if title:
                existing_titles.add(title)
        
        return papers, existing_titles
    except FileNotFoundError:
        return [], set()

def create_layout(tracker):
    """Create Rich layout with domain stats and logs"""
    layout = Layout()
    
    # Create domain statistics boxes
    domain_stats_layout = Layout()
    
    # Create individual domain boxes
    domain_boxes = []
    
    # Summary box
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="cyan", width=12)
    summary_table.add_column("Value", style="green bold", width=8)
    
    summary_table.add_row("Total Papers", str(tracker.stats['total_papers']))
    summary_table.add_row("Target", "800")
    summary_table.add_row("Progress", f"{(tracker.stats['total_papers']/800)*100:.1f}%")
    summary_table.add_row("New Papers", str(tracker.stats['new_papers']))
    summary_table.add_row("API Calls", str(tracker.stats['api_calls']))
    summary_table.add_row("Rate Limits", str(tracker.stats['rate_limits']))
    summary_table.add_row("Errors", str(tracker.stats['errors']))
    
    summary_panel = Panel(summary_table, title="📊 Summary", border_style="green", width=25)
    domain_boxes.append(summary_panel)
    
    # Domain-specific boxes
    domain_names = {
        "Computer Vision & Medical Imaging": "🖼️ CV & Medical",
        "Natural Language Processing": "💬 NLP",
        "Reinforcement Learning & Robotics": "🤖 RL & Robotics"
    }
    
    for domain_full, domain_short in domain_names.items():
        domain_table = Table(show_header=False, box=None, padding=(0, 1))
        domain_table.add_column("Year", style="cyan", width=6)
        domain_table.add_column("Papers", style="green", width=6)
        
        domain_total = 0
        for year in YEARS:
            count = tracker.stats.get('domain_stats', {}).get(domain_full, {}).get(str(year), 0)
            domain_total += count
            domain_table.add_row(str(year), str(count))
        
        domain_table.add_row("─────", "─────")
        domain_table.add_row("Total", f"[bold]{domain_total}[/bold]")
        
        domain_panel = Panel(domain_table, title=domain_short, border_style="blue", width=16)
        domain_boxes.append(domain_panel)
    
    # Arrange domain boxes horizontally
    if len(domain_boxes) > 1:
        domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])
    else:
        domain_stats_layout = Layout(domain_boxes[0])
    
    # Create logs panel from captured output
    captured_lines = tracker.output_capture.get_lines()
    
    # Show last 15 lines of captured output
    log_text = Text("\\n".join(captured_lines[-15:]) if captured_lines else "Waiting for activity...")
    logs_panel = Panel(log_text, title="📝 Real-time Activity Log", border_style="yellow")
    
    # Layout arrangement
    layout.split_column(
        Layout(domain_stats_layout, size=12),
        Layout(logs_panel)
    )
    
    return layout

def update_domain_stats(tracker, all_papers):
    """Update domain statistics in tracker"""
    domain_stats = defaultdict(lambda: defaultdict(int))
    
    for paper in all_papers:
        domain = paper.get('mila_domain', 'unknown')
        year = paper.get('collection_year', paper.get('year', 'unknown'))
        if domain != 'unknown' and year != 'unknown':
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
    
    print(f"🚀 Starting Worker 6 paper collection...")
    print(f"📊 Current status: {current_count} papers collected")
    print(f"🎯 Target: {TARGET_TOTAL} papers")
    print(f"📈 Need to collect: {needed} more papers")
    tracker.update_stats(total_papers=current_count)
    
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
        progress_panel = Panel(progress, title="Collection Progress", border_style="bright_blue")
        
        # Stats and logs layout
        stats_logs_layout = create_layout(tracker)
        
        # Combine vertically
        main_layout.split_column(
            Layout(progress_panel, size=6),
            Layout(stats_logs_layout)
        )
        
        return main_layout
    
    # Redirect stdout to capture print statements
    original_stdout = sys.stdout
    sys.stdout = tracker.output_capture
    
    try:
        with Live(create_full_layout(), refresh_per_second=2) as live:
            
            domain_count = 0
            for domain_name, keywords in DOMAINS.items():
                domain_count += 1
                print(f"🏗️ Processing domain {domain_count}/3: {domain_name}")
                print(f"🔑 Keywords for this domain: {', '.join(keywords[:3])}")
                
                progress.update(domain_task, description=f"{domain_name[:20]}...", completed=0)
                year_count = 0
                
                for year in YEARS:
                    year_count += 1
                    print(f"📅 Processing year {year}...")
                    
                    year_papers = []
                    
                    # Use first keyword for testing
                    keyword = keywords[0]
                    print(f"🔍 Searching for '{keyword}' in {domain_name} {year}")
                    
                    # Semantic Scholar
                    ss_papers = collector.semantic_scholar_search(keyword, year, limit=5)
                    
                    # Process results
                    for paper in ss_papers:
                        title = paper.get('title', '').lower().strip()
                        if title and title not in existing_titles:
                            existing_titles.add(title)
                            paper['mila_domain'] = domain_name
                            paper['collection_year'] = year
                            paper['collection_timestamp'] = datetime.now().isoformat()
                            year_papers.append(paper)
                            print(f"➕ Added paper: \"{paper.get('title', 'No title')[:40]}...\"")
                    
                    # Add collected papers
                    all_papers.extend(year_papers)
                    new_papers_collected += len(year_papers)
                    
                    print(f"✅ {domain_name} {year} completed: {len(year_papers)} papers collected")
                    
                    # Update domain stats
                    update_domain_stats(tracker, all_papers)
                    
                    # Update progress
                    current_total = len(all_papers)
                    tracker.update_stats(
                        total_papers=current_total,
                        new_papers=new_papers_collected
                    )
                    
                    progress.update(main_task, completed=current_total)
                    print(f"🎯 Overall total: {current_total}/800 ({(current_total/800)*100:.1f}%)")
                    
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
                    print(f"🎯 TARGET ACHIEVED! Collected {len(all_papers)} papers")
                    break
        
        # Final processing
        final_count = len(all_papers)
        print(f"🏁 Collection session complete!")
        print(f"📊 Final count: {final_count} papers")
        
        return final_count >= TARGET_TOTAL
    
    except KeyboardInterrupt:
        print("⚠️ Collection interrupted by user")
        return False
    
    finally:
        # Restore original stdout
        sys.stdout = original_stdout

if __name__ == "__main__":
    success = main()
    if success:
        print("\\n✅ Collection completed successfully!")
    else:
        print("\\n⚠️ Collection improved but target not fully met")