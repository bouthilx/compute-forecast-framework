#!/usr/bin/env python3
"""
Test the UI layout without running collection
"""
import time
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
import queue

class MockTracker:
    def __init__(self):
        self.console = Console()
        self.log_queue = queue.Queue()
        self.stats = {
            'total_papers': 207,
            'new_papers': 20,
            'api_calls': 145,
            'rate_limits': 3,
            'errors': 2,
            'domains_completed': 2,
            'domain_stats': {
                'Computer Vision & Medical Imaging': {'2019': 6, '2020': 6, '2021': 4, '2022': 8, '2023': 4, '2024': 8},
                'Natural Language Processing': {'2019': 5, '2020': 5, '2021': 4, '2022': 8, '2023': 8, '2024': 3},
                'Reinforcement Learning & Robotics': {'2019': 8, '2020': 8, '2021': 6, '2022': 8, '2023': 8, '2024': 8},
                'Graph Learning & Network Analysis': {'2019': 8, '2020': 3, '2021': 4, '2022': 8, '2023': 8, '2024': 8},
                'Scientific Computing & Applications': {'2019': 6, '2020': 4, '2021': 5, '2022': 8, '2023': 2, '2024': 8}
            }
        }
        
        # Add some detailed mock logs
        mock_logs = [
            "🚀 Starting Worker 6 paper collection continuation...",
            "📊 Current status: 207 papers collected",
            "🎯 Target: 800 papers",
            "🏗️ Processing domain 1/5: Computer Vision & Medical Imaging",
            "🔑 Keywords: computer vision, medical imaging, image processing",
            "🔍 Keyword 1/6: Searching for 'computer vision' in CV 2024",
            "📡 Making API request to Semantic Scholar...",
            "✅ API response received - processing 8 results",
            "📄 Paper 1: \"Deep Learning for Medical Image Analysis...\" (156 citations)",
            "➕ Added paper: \"Deep Learning for Medical Image Analysis...\" (156 citations)",
            "📈 Semantic Scholar: 3 new papers added from 8 results",
            "⏱️ Rate limiting: waiting 3 seconds before next API call...",
            "⏳ Countdown: 2s...",
            "🔍 Searching OpenAlex: 'computer vision' (2024) - limit 10",
            "✅ {domain_name} 2024 completed: 5 papers collected this year"
        ]
        
        for i, log_msg in enumerate(mock_logs):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_queue.put(f"[{timestamp}] [INFO] {log_msg}")
    
    def update_stats(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

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
        "Reinforcement Learning & Robotics": "🤖 RL & Robotics", 
        "Graph Learning & Network Analysis": "🕸️ Graph Learning",
        "Scientific Computing & Applications": "🔬 Sci Computing"
    }
    
    YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
    
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
    
    # Create logs panel
    logs = []
    temp_queue = []
    
    # Get recent logs (up to 12)
    while not tracker.log_queue.empty() and len(logs) < 12:
        log_entry = tracker.log_queue.get()
        logs.append(log_entry)
        temp_queue.append(log_entry)
    
    # Put logs back in queue
    for log_entry in temp_queue:
        tracker.log_queue.put(log_entry)
    
    log_text = Text("\n".join(logs[-15:]))  # Show last 15 logs
    logs_panel = Panel(log_text, title="📝 Detailed Activity Log", border_style="yellow")
    
    # Layout arrangement - no progress bars here to avoid overlap
    layout.split_column(
        Layout(domain_stats_layout, size=12),
        Layout(logs_panel)
    )
    
    return layout

def main():
    tracker = MockTracker()
    
    # Create separate progress display
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )
    
    # Main progress task
    main_task = progress.add_task("📈 Overall Progress", total=800)
    progress.update(main_task, completed=207)
    
    # Domain progress task  
    domain_task = progress.add_task("🎯 Current Domain", total=100)
    progress.update(domain_task, completed=40)
    
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
    
    print("🧪 Testing UI Layout...")
    print("This will show the collection interface for 10 seconds")
    print("Press Ctrl+C to exit early\n")
    
    with Live(create_full_layout(), refresh_per_second=2) as live:
        try:
            for i in range(20):  # Run for 10 seconds (20 * 0.5s)
                time.sleep(0.5)
                
                # Simulate progress updates
                if i % 4 == 0:  # Every 2 seconds
                    tracker.stats['total_papers'] += 2
                    tracker.stats['new_papers'] += 2
                    tracker.stats['api_calls'] += 3
                    
                    progress.update(main_task, completed=tracker.stats['total_papers'])
                    progress.update(domain_task, completed=min(100, (i*5) % 100))
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    tracker.log_queue.put(f"[{timestamp}] [INFO] Simulated collection update {i//4 + 1}")
                    
        except KeyboardInterrupt:
            pass
    
    print("\n✅ UI test completed!")
    print("Layout features:")
    print("  📈 Progress bars at top")
    print("  📊 Summary statistics box")
    print("  🖼️💬🤖🕸️🔬 Domain-specific boxes (horizontal)")
    print("  📝 Scrolling activity logs")

if __name__ == "__main__":
    main()