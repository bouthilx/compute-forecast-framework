#!/usr/bin/env python3
"""
Demo of real-time logging capture in UI
"""
import time
import sys
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table

class OutputCapture:
    def __init__(self, max_lines=20):
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

class MockTracker:
    def __init__(self):
        self.output_capture = OutputCapture()
        self.stats = {
            'total_papers': 207,
            'new_papers': 0,
            'api_calls': 0,
            'rate_limits': 0,
            'errors': 0,
            'domain_stats': {
                'Computer Vision & Medical Imaging': {'2019': 6, '2020': 6, '2021': 4, '2022': 8, '2023': 4, '2024': 8},
                'Natural Language Processing': {'2019': 5, '2020': 5, '2021': 4, '2022': 8, '2023': 8, '2024': 3},
            }
        }
    
    def update_stats(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

def create_layout(tracker):
    """Create layout with real-time stdout logs"""
    layout = Layout()
    
    # Summary stats
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Metric", style="cyan", width=12)
    summary_table.add_column("Value", style="green bold", width=8)
    
    summary_table.add_row("Total Papers", str(tracker.stats['total_papers']))
    summary_table.add_row("Target", "800")
    summary_table.add_row("Progress", f"{(tracker.stats['total_papers']/800)*100:.1f}%")
    summary_table.add_row("API Calls", str(tracker.stats['api_calls']))
    summary_table.add_row("Rate Limits", str(tracker.stats['rate_limits']))
    summary_table.add_row("Errors", str(tracker.stats['errors']))
    
    summary_panel = Panel(summary_table, title="📊 Summary", border_style="green", width=25)
    
    # Real-time logs from captured stdout
    captured_lines = tracker.output_capture.get_lines()
    log_text = Text("\n".join(captured_lines[-15:]) if captured_lines else "Waiting for activity...")
    logs_panel = Panel(log_text, title="📝 Real-time stdout/stderr Log", border_style="yellow")
    
    # Layout
    layout.split_row(
        Layout(summary_panel, size=30),
        Layout(logs_panel)
    )
    
    return layout

def simulate_collection():
    """Simulate paper collection with real print statements"""
    
    domains = ["Computer Vision", "NLP", "Reinforcement Learning"]
    
    for i, domain in enumerate(domains):
        print(f"🏗️ Processing domain {i+1}/3: {domain}")
        print(f"🔑 Keywords: deep learning, neural networks, AI")
        
        for year in [2023, 2024]:
            print(f"📊 {domain} {year}: targeting 5 more papers")
            
            for keyword in ["deep learning", "neural networks"]:
                print(f"🔍 Searching for '{keyword}' in {year}")
                
                print("📡 Making API request to Semantic Scholar...")
                time.sleep(1)
                
                print("✅ API response received - processing 8 results")
                time.sleep(0.5)
                
                for j in range(3):
                    paper_title = f"Deep Learning Paper {j+1}"
                    citations = (j+1) * 50
                    print(f"📄 Paper {j+1}: \"{paper_title}\" ({citations} citations)")
                    time.sleep(0.3)
                    
                    print(f"➕ Added paper: \"{paper_title}\" ({citations} citations)")
                    time.sleep(0.3)
                
                print(f"📈 Semantic Scholar: 3 new papers added from 8 results")
                time.sleep(0.5)
                
                print(f"⏱️ Rate limiting: waiting 3 seconds...")
                for countdown in range(3, 0, -1):
                    print(f"⏳ Countdown: {countdown}s...")
                    time.sleep(1)
            
            print(f"✅ {domain} {year} completed: 6 papers collected this year")
            time.sleep(0.5)
        
        print(f"🏁 Domain {i+1} ({domain}) completed!")
        time.sleep(1)
    
    print(f"🏁 Collection session complete!")
    print(f"📊 Final count: 225 papers")
    print(f"🎯 Target achievement: 28.1% (225/800)")
    print(f"💾 Saving final results...")
    time.sleep(1)
    print(f"✅ All files saved successfully!")

def main():
    tracker = MockTracker()
    
    # Redirect stdout to capture print statements
    original_stdout = sys.stdout
    sys.stdout = tracker.output_capture
    
    try:
        # Create progress
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        )
        
        main_task = progress.add_task("📈 Overall Progress", total=800)
        progress.update(main_task, completed=207)
        
        domain_task = progress.add_task("🎯 Current Domain", total=100)
        
        def create_full_layout():
            main_layout = Layout()
            progress_panel = Panel(progress, title="Collection Progress", border_style="bright_blue")
            stats_logs_layout = create_layout(tracker)
            
            main_layout.split_column(
                Layout(progress_panel, size=6),
                Layout(stats_logs_layout)
            )
            return main_layout
        
        print("🚀 Starting enhanced paper collection with real-time logs...")
        print("📊 Current status: 207 papers collected")
        print("🎯 Target: 800 papers")
        print("📈 Starting collection simulation...")
        
        with Live(create_full_layout(), refresh_per_second=2) as live:
            # Simulate collection while updating progress
            papers_collected = 207
            
            # Run simulation in chunks to update progress
            for i in range(10):  # Simulate 10 steps
                if i < 5:
                    progress.update(domain_task, completed=i * 20)
                    tracker.stats['api_calls'] += 2
                    tracker.stats['total_papers'] = papers_collected + i * 3
                
                time.sleep(2)  # Pause between simulation steps
            
            # Final simulation
            simulate_collection()
            
            # Update final progress
            tracker.stats['total_papers'] = 225
            tracker.stats['api_calls'] = 45
            progress.update(main_task, completed=225)
            progress.update(domain_task, completed=100)
            
            time.sleep(3)  # Show final state
    
    finally:
        # Restore stdout
        sys.stdout = original_stdout

if __name__ == "__main__":
    print("🧪 Demo: Real-time stdout/stderr capture in collection UI")
    print("This will show live logs being captured and displayed")
    print("Watch the bottom panel for real-time activity!\n")
    
    main()
    
    print("\n✅ Demo completed!")
    print("Features demonstrated:")
    print("  📈 Progress bars")
    print("  📊 Statistics updates")
    print("  📝 Real-time stdout capture")
    print("  🔄 Live UI updates")