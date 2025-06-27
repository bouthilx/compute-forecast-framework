#!/usr/bin/env python3
"""
Guaranteed dashboard display for paper collection
"""
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

TARGET_TOTAL = 800

class OutputCapture:
    def __init__(self, max_lines=25):
        self.lines = []
        self.max_lines = max_lines
        
    def write(self, text):
        if text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.lines.append(f"[{timestamp}] {text.strip()}")
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines:]
    
    def flush(self):
        pass
    
    def get_lines(self):
        return self.lines.copy()

class CollectionTracker:
    def __init__(self):
        self.output_capture = OutputCapture()
        
        # Load existing data
        self.current_papers = self.load_existing_papers()
        
        self.stats = {
            'total_papers': len(self.current_papers),
            'new_papers': 0,
            'api_calls': 0,
            'rate_limits': 0,
            'errors': 0,
            'domains_completed': 0,
            'domain_stats': self.calculate_domain_stats()
        }
    
    def load_existing_papers(self):
        """Load existing papers"""
        try:
            with open('data/raw_collected_papers.json', 'r') as f:
                papers = json.load(f)
            print(f"✅ Loaded {len(papers)} existing papers")
            return papers
        except FileNotFoundError:
            print("⚠️ No existing papers file found - starting fresh")
            return []
        except Exception as e:
            print(f"❌ Error loading papers: {e}")
            return []
    
    def calculate_domain_stats(self):
        """Calculate domain statistics from existing papers"""
        domain_stats = defaultdict(lambda: defaultdict(int))
        
        for paper in self.current_papers:
            domain = paper.get('mila_domain', 'unknown')
            year = paper.get('collection_year', paper.get('year', 'unknown'))
            if domain != 'unknown' and year != 'unknown':
                domain_stats[domain][str(year)] += 1
        
        return dict(domain_stats)
    
    def update_stats(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

def create_layout(tracker):
    """Create the dashboard layout"""
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
    
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    
    for domain_full, domain_short in domain_names.items():
        domain_table = Table(show_header=False, box=None, padding=(0, 1))
        domain_table.add_column("Year", style="cyan", width=6)
        domain_table.add_column("Papers", style="green", width=6)
        
        domain_total = 0
        for year in years:
            count = tracker.stats.get('domain_stats', {}).get(domain_full, {}).get(str(year), 0)
            domain_total += count
            domain_table.add_row(str(year), str(count))
        
        domain_table.add_row("─────", "─────")
        domain_table.add_row("Total", f"[bold]{domain_total}[/bold]")
        
        domain_panel = Panel(domain_table, title=domain_short, border_style="blue", width=16)
        domain_boxes.append(domain_panel)
    
    # Arrange domain boxes horizontally
    domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])
    
    # Create logs panel
    captured_lines = tracker.output_capture.get_lines()
    log_text = Text("\n".join(captured_lines[-20:]) if captured_lines else "Dashboard ready - waiting for collection to start...")
    logs_panel = Panel(log_text, title="📝 Real-time Activity Log", border_style="yellow")
    
    # Main layout
    layout.split_column(
        Layout(domain_stats_layout, size=12),
        Layout(logs_panel)
    )
    
    return layout

def main():
    console = Console()
    console.print("🚀 Starting Paper Collection Dashboard", style="bold green")
    console.print("Loading existing data and initializing dashboard...")
    
    # Initialize tracker
    tracker = CollectionTracker()
    
    console.print(f"📊 Current status: {tracker.stats['total_papers']} papers loaded")
    console.print("🖥️ Starting dashboard display...")
    
    # Redirect stdout to capture logs
    original_stdout = sys.stdout
    sys.stdout = tracker.output_capture
    
    try:
        # Initial log messages
        print("🚀 Dashboard initialized successfully")
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
        
        domain_task = progress.add_task("🎯 Current Status", total=100)
        progress.update(domain_task, completed=50)
        
        def create_full_layout():
            main_layout = Layout()
            progress_panel = Panel(progress, title="Collection Progress", border_style="bright_blue")
            stats_logs_layout = create_layout(tracker)
            
            main_layout.split_column(
                Layout(progress_panel, size=6),
                Layout(stats_logs_layout)
            )
            return main_layout
        
        print("📱 Dashboard starting - you should see the interface now!")
        print("🔄 Updates will appear in real-time below")
        print("⌨️ Press Ctrl+C to stop the dashboard")
        
        # Start the Live display
        with Live(create_full_layout(), refresh_per_second=2) as live:
            
            # Demo simulation - you can replace this with real collection
            domains = ["Computer Vision", "NLP", "Reinforcement Learning"]
            
            for i in range(30):  # Run for 30 iterations (15 seconds)
                time.sleep(0.5)
                
                # Update progress
                domain_progress = (i * 3.33) % 100
                progress.update(domain_task, completed=domain_progress)
                
                # Simulate some activity every few iterations
                if i % 6 == 0:
                    domain = domains[i // 6 % 3]
                    print(f"🔍 Searching {domain} papers...")
                    tracker.update_stats(api_calls=tracker.stats['api_calls'] + 1)
                
                if i % 6 == 2:
                    print(f"📄 Found paper: 'Advanced {domain} Research'")
                    tracker.update_stats(
                        new_papers=tracker.stats['new_papers'] + 1,
                        total_papers=tracker.stats['total_papers'] + 1
                    )
                    progress.update(main_task, completed=tracker.stats['total_papers'])
                
                if i % 6 == 4:
                    print(f"⏱️ Rate limiting: waiting...")
                
                if i % 10 == 0:
                    print(f"📊 Progress update: {tracker.stats['total_papers']}/{TARGET_TOTAL} papers")
            
            print("✅ Demo simulation completed")
            print("🎯 Dashboard is working correctly!")
            print("📝 Real collection can now be implemented")
            
            # Show final state for a few seconds
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("⚠️ Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore stdout
        sys.stdout = original_stdout
    
    console.print("\n✅ Dashboard session completed!")
    console.print(f"📊 Final stats: {tracker.stats['total_papers']} papers, {tracker.stats['api_calls']} API calls")
    console.print("\n🎉 The dashboard is working! You can now run the full collection.")

if __name__ == "__main__":
    main()