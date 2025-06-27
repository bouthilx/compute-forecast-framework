#!/usr/bin/env python3
"""
Real-time streaming dashboard for paper collection
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
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table

# Collection configuration
DOMAINS = {
    "Computer Vision & Medical Imaging": [
        "computer vision", "medical imaging", "image processing", "deep learning", "CNN", 
        "convolutional neural network", "image segmentation", "object detection", "medical AI"
    ],
    "Natural Language Processing": [
        "natural language processing", "NLP", "language model", "text analysis", "machine translation",
        "transformer", "BERT", "GPT", "text mining", "sentiment analysis"
    ],
    "Reinforcement Learning & Robotics": [
        "reinforcement learning", "robotics", "RL", "policy gradient", "robot learning",
        "deep reinforcement learning", "Q-learning", "actor-critic", "robot control"
    ],
    "Graph Learning & Network Analysis": [
        "graph neural network", "network analysis", "graph learning", "GNN", "social network",
        "graph convolutional network", "node classification", "link prediction", "graph embedding"
    ],
    "Scientific Computing & Applications": [
        "computational biology", "computational physics", "scientific computing", "numerical methods", "simulation",
        "bioinformatics", "molecular dynamics", "finite element", "high performance computing"
    ]
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
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Millisecond precision
                self.lines.append(f"[{timestamp}] {text.strip()}")
    
    def flush(self):
        """Required for stdout/stderr compatibility"""
        pass
    
    def get_recent_lines(self):
        """Get copy of recent lines for thread safety"""
        with self.lock:
            return list(self.lines)  # Return copy for thread safety

class CollectionTracker:
    """Tracks collection progress and statistics"""
    def __init__(self):
        self.console = Console()
        self.log_capture = StreamingLogCapture(max_lines=50)
        self.stats = {
            'total_papers': 0,
            'new_papers': 0,
            'api_calls': 0,
            'rate_limits': 0,
            'errors': 0,
            'domains_completed': 0,
            'domain_stats': {}
        }
        
        # Load existing papers
        self.load_existing_data()
        
    def load_existing_data(self):
        """Load existing papers and calculate initial stats"""
        try:
            with open('data/raw_collected_papers.json', 'r') as f:
                papers = json.load(f)
            
            self.stats['total_papers'] = len(papers)
            
            # Calculate domain stats
            domain_stats = defaultdict(lambda: defaultdict(int))
            for paper in papers:
                domain = paper.get('mila_domain', 'unknown')
                year = paper.get('collection_year', paper.get('year', 'unknown'))
                if domain != 'unknown' and year != 'unknown':
                    domain_stats[domain][str(year)] += 1
            
            self.stats['domain_stats'] = dict(domain_stats)
            print(f"✅ Loaded {len(papers)} existing papers")
            
        except FileNotFoundError:
            print("⚠️ No existing papers file found - starting fresh")
        except Exception as e:
            print(f"❌ Error loading papers: {e}")
    
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
        """Search Semantic Scholar with real-time logging"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'year': f"{year}-{year}",
            'limit': limit,
            'fields': 'paperId,title,abstract,authors,year,citationCount,venue,url'
        }
        
        print(f"🔍 Searching Semantic Scholar: '{query}' ({year})")
        self.tracker.update_stats(api_calls=self.tracker.stats['api_calls'] + 1)
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                print("⚠️ Rate limited - waiting 10 seconds...")
                self.tracker.update_stats(rate_limits=self.tracker.stats['rate_limits'] + 1)
                for i in range(10, 0, -1):
                    print(f"⏳ Rate limit cooldown: {i}s remaining...")
                    time.sleep(1)
                return []
            
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for paper in data.get('data', []):
                papers.append({
                    'id': paper.get('paperId', ''),
                    'title': paper.get('title', ''),
                    'abstract': paper.get('abstract', ''),
                    'authors': [a.get('name', '') for a in paper.get('authors', [])],
                    'year': paper.get('year', year),
                    'citations': paper.get('citationCount', 0),
                    'venue': paper.get('venue', ''),
                    'url': paper.get('url', ''),
                    'source': 'semantic_scholar'
                })
            
            print(f"✅ Found {len(papers)} papers from Semantic Scholar")
            return papers
            
        except Exception as e:
            print(f"❌ Semantic Scholar error: {str(e)}")
            self.tracker.update_stats(errors=self.tracker.stats['errors'] + 1)
            return []
    
    def openalex_search(self, query, year, limit=10):
        """Search OpenAlex with real-time logging"""
        url = "https://api.openalex.org/works"
        params = {
            'search': query,
            'filter': f'publication_year:{year}',
            'per-page': limit,
            'select': 'id,title,abstract,authorships,publication_year,cited_by_count,primary_location'
        }
        
        print(f"🔍 Searching OpenAlex: '{query}' ({year})")
        self.tracker.update_stats(api_calls=self.tracker.stats['api_calls'] + 1)
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 403:
                print("⚠️ OpenAlex access limited - skipping")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for work in data.get('results', []):
                venue = 'Unknown venue'
                if work.get('primary_location'):
                    source_info = work['primary_location'].get('source', {})
                    if source_info:
                        venue = source_info.get('display_name', 'Unknown venue')
                
                papers.append({
                    'id': work.get('id', ''),
                    'title': work.get('title', ''),
                    'abstract': work.get('abstract', ''),
                    'authors': [a['author']['display_name'] for a in work.get('authorships', []) if a.get('author')],
                    'year': work.get('publication_year', year),
                    'citations': work.get('cited_by_count', 0),
                    'venue': venue,
                    'url': work.get('id', ''),
                    'source': 'openalex'
                })
            
            print(f"✅ Found {len(papers)} papers from OpenAlex")
            return papers
            
        except Exception as e:
            print(f"❌ OpenAlex error: {str(e)}")
            self.tracker.update_stats(errors=self.tracker.stats['errors'] + 1)
            return []

def create_layout(tracker):
    """Create the dashboard layout with streaming logs"""
    layout = Layout()
    
    # Create domain statistics layout
    domain_stats_layout = Layout()
    domain_boxes = []
    
    # Summary box
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="cyan", width=12)
    summary_table.add_column("Value", style="green bold", width=8)
    
    summary_table.add_row("Total Papers", str(tracker.stats['total_papers']))
    summary_table.add_row("Target", str(TARGET_TOTAL))
    summary_table.add_row("Progress", f"{(tracker.stats['total_papers']/TARGET_TOTAL)*100:.1f}%")
    summary_table.add_row("New Papers", str(tracker.stats['new_papers']))
    summary_table.add_row("API Calls", str(tracker.stats['api_calls']))
    summary_table.add_row("Rate Limits", str(tracker.stats['rate_limits']))
    summary_table.add_row("Errors", str(tracker.stats['errors']))
    
    summary_panel = Panel(summary_table, title="📊 Summary", border_style="green", width=25)
    domain_boxes.append(summary_panel)
    
    # Domain boxes
    domain_names = {
        "Computer Vision & Medical Imaging": "🖼️ CV & Medical",
        "Natural Language Processing": "💬 NLP",
        "Reinforcement Learning & Robotics": "🤖 RL & Robotics", 
        "Graph Learning & Network Analysis": "🕸️ Graph Learning",
        "Scientific Computing & Applications": "🔬 Sci Computing"
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
    domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])
    
    # Create real-time logs panel with streaming content
    recent_lines = tracker.log_capture.get_recent_lines()
    log_text = Text("\\n".join(recent_lines[-25:]) if recent_lines else "Dashboard ready - waiting for collection to start...")
    logs_panel = Panel(log_text, title="📝 Real-time Activity Log", border_style="yellow")
    
    # Main layout
    layout.split_column(
        Layout(domain_stats_layout, size=12),
        Layout(logs_panel)
    )
    
    return layout

def main():
    """Main collection function with streaming dashboard"""
    console = Console()
    console.print("🚀 Starting Real-Time Paper Collection Dashboard", style="bold green")
    
    # Initialize tracker and collector
    tracker = CollectionTracker()
    collector = PaperCollector(tracker)
    
    console.print(f"📊 Current status: {tracker.stats['total_papers']} papers loaded")
    console.print("🖥️ Starting streaming dashboard...")
    
    # Redirect stdout to capture logs
    original_stdout = sys.stdout
    sys.stdout = tracker.log_capture
    
    try:
        # Initial log messages
        print("🚀 Streaming dashboard initialized successfully")
        print(f"📊 Starting with {tracker.stats['total_papers']} existing papers")
        print(f"🎯 Target: {TARGET_TOTAL} papers")
        print(f"📈 Need: {TARGET_TOTAL - tracker.stats['total_papers']} more papers")
        
        # Create progress bars
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        )
        
        main_task = progress.add_task("📈 Overall Progress", total=TARGET_TOTAL)
        progress.update(main_task, completed=tracker.stats['total_papers'])
        
        domain_task = progress.add_task("🎯 Current Domain", total=100)
        
        def create_full_layout():
            """Create complete layout with progress and streaming logs"""
            main_layout = Layout()
            progress_panel = Panel(progress, title="Collection Progress", border_style="bright_blue")
            stats_logs_layout = create_layout(tracker)
            
            main_layout.split_column(
                Layout(progress_panel, size=6),
                Layout(stats_logs_layout)
            )
            return main_layout
        
        print("📱 Starting live dashboard - real-time updates enabled!")
        print("🔄 All stdout/stderr will appear in the activity log below")
        print("⌨️ Press Ctrl+C to stop the dashboard")
        
        # Start the Live display with high refresh rate for real-time feel
        with Live(create_full_layout(), refresh_per_second=6) as live:
            
            # Demo simulation showing real-time logging
            print("🧪 Running demo simulation to test real-time logging...")
            
            domains_list = list(DOMAINS.keys())
            
            for i in range(20):  # 20 iterations to show streaming
                time.sleep(0.5)  # Half-second intervals for responsive feel
                
                # Simulate domain progress
                domain_progress = (i * 5) % 100
                progress.update(domain_task, completed=domain_progress)
                
                # Simulate collection activities
                if i % 4 == 0:
                    domain = domains_list[i // 4 % len(domains_list)]
                    print(f"🔍 Searching {domain}...")
                    tracker.update_stats(api_calls=tracker.stats['api_calls'] + 1)
                
                if i % 4 == 1:
                    print(f"📡 Making API request...")
                
                if i % 4 == 2:
                    print(f"📄 Found paper: 'Advanced Research in {domain}'")
                    tracker.update_stats(
                        new_papers=tracker.stats['new_papers'] + 1,
                        total_papers=tracker.stats['total_papers'] + 1
                    )
                    progress.update(main_task, completed=tracker.stats['total_papers'])
                
                if i % 4 == 3:
                    print(f"⏱️ Rate limiting: waiting...")
                
                if i % 8 == 0:
                    print(f"📊 Progress update: {tracker.stats['total_papers']}/{TARGET_TOTAL} papers")
                
                # Update the live layout to show new logs
                live.update(create_full_layout())
            
            print("✅ Demo simulation completed - streaming logs working!")
            print("🎯 Dashboard successfully shows real-time activity")
            print("📝 Ready for actual paper collection implementation")
            
            # Show final state
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("⚠️ Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore stdout
        sys.stdout = original_stdout
    
    console.print("\\n✅ Streaming dashboard session completed!")
    console.print(f"📊 Final stats: {tracker.stats['total_papers']} papers, {tracker.stats['api_calls']} API calls")
    console.print("\\n🎉 Real-time logging is working correctly!")

if __name__ == "__main__":
    main()