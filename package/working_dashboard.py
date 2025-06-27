#!/usr/bin/env python3
"""
Working dashboard with real-time logs for paper collection
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

class CollectionDashboard:
    def __init__(self):
        self.output_capture = OutputCapture()
        self.stats = {
            'total_papers': 207,
            'new_papers': 0,
            'api_calls': 0,
            'rate_limits': 0,
            'errors': 0,
            'current_domain': 'Computer Vision',
            'current_year': 2024
        }
        
        # Domain paper counts
        self.domain_stats = {
            'Computer Vision & Medical Imaging': {'2019': 6, '2020': 6, '2021': 4, '2022': 8, '2023': 4, '2024': 8},
            'Natural Language Processing': {'2019': 5, '2020': 5, '2021': 4, '2022': 8, '2023': 8, '2024': 3},
            'Reinforcement Learning & Robotics': {'2019': 8, '2020': 8, '2021': 6, '2022': 8, '2023': 8, '2024': 8},
            'Graph Learning & Network Analysis': {'2019': 8, '2020': 3, '2021': 4, '2022': 8, '2023': 8, '2024': 8},
            'Scientific Computing & Applications': {'2019': 6, '2020': 4, '2021': 5, '2022': 8, '2023': 2, '2024': 8}
        }
    
    def update_stats(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

    def create_layout(self):
        """Create the dashboard layout"""
        layout = Layout()
        
        # Create domain statistics boxes
        domain_stats_layout = Layout()
        domain_boxes = []
        
        # Summary box
        summary_table = Table(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Metric", style="cyan", width=12)
        summary_table.add_column("Value", style="green bold", width=8)
        
        summary_table.add_row("Total Papers", str(self.stats['total_papers']))
        summary_table.add_row("Target", "800")
        summary_table.add_row("Progress", f"{(self.stats['total_papers']/800)*100:.1f}%")
        summary_table.add_row("New Papers", str(self.stats['new_papers']))
        summary_table.add_row("API Calls", str(self.stats['api_calls']))
        summary_table.add_row("Rate Limits", str(self.stats['rate_limits']))
        summary_table.add_row("Errors", str(self.stats['errors']))
        
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
        
        years = [2019, 2020, 2021, 2022, 2023, 2024]
        
        for domain_full, domain_short in domain_names.items():
            domain_table = Table(show_header=False, box=None, padding=(0, 1))
            domain_table.add_column("Year", style="cyan", width=6)
            domain_table.add_column("Papers", style="green", width=6)
            
            domain_total = 0
            for year in years:
                count = self.domain_stats.get(domain_full, {}).get(str(year), 0)
                domain_total += count
                domain_table.add_row(str(year), str(count))
            
            domain_table.add_row("─────", "─────")
            domain_table.add_row("Total", f"[bold]{domain_total}[/bold]")
            
            domain_panel = Panel(domain_table, title=domain_short, border_style="blue", width=16)
            domain_boxes.append(domain_panel)
        
        # Arrange domain boxes horizontally
        domain_stats_layout.split_row(*[Layout(box) for box in domain_boxes])
        
        # Create logs panel from captured stdout
        captured_lines = self.output_capture.get_lines()
        log_text = Text("\n".join(captured_lines[-20:]) if captured_lines else "Waiting for activity...")
        logs_panel = Panel(log_text, title="📝 Real-time Activity Log", border_style="yellow")
        
        # Layout arrangement
        layout.split_column(
            Layout(domain_stats_layout, size=12),
            Layout(logs_panel)
        )
        
        return layout

def simulate_paper_collection(dashboard):
    """Simulate paper collection with detailed logging"""
    
    # Redirect stdout to capture logs
    original_stdout = sys.stdout
    sys.stdout = dashboard.output_capture
    
    try:
        print("🚀 Starting Worker 6 paper collection continuation...")
        print("📊 Current status: 207 papers collected")
        print("🎯 Target: 800 papers")
        print("📈 Need to collect: 593 more papers")
        
        domains = ["Computer Vision & Medical Imaging", "Natural Language Processing", "Reinforcement Learning & Robotics"]
        
        for i, domain in enumerate(domains):
            print(f"🏗️ Processing domain {i+1}/3: {domain}")
            print(f"🔑 Keywords: deep learning, neural networks, computer vision")
            
            dashboard.update_stats(current_domain=domain)
            
            for year in [2023, 2024]:
                print(f"📊 {domain} {year}: targeting 5 more papers")
                
                for j, keyword in enumerate(["deep learning", "computer vision"]):
                    print(f"🔍 Keyword {j+1}/2: Searching for '{keyword}' in {year}")
                    
                    # Simulate API call
                    print("📡 Making API request to Semantic Scholar...")
                    time.sleep(1)
                    
                    dashboard.update_stats(api_calls=dashboard.stats['api_calls'] + 1)
                    
                    print("✅ API response received - processing 6 results")
                    time.sleep(0.5)
                    
                    # Simulate processing papers
                    for k in range(3):
                        paper_title = f"Advanced {keyword.title()} Research Paper {k+1}"
                        citations = (k+1) * 50 + (j*100)
                        venue = "ICML" if k % 2 == 0 else "NeurIPS"
                        
                        print(f"📄 Paper {k+1}: \"{paper_title[:40]}...\" ({citations} citations) - {venue}")
                        time.sleep(0.3)
                        
                        print(f"➕ Added paper: \"{paper_title[:40]}...\" ({citations} citations)")
                        dashboard.update_stats(
                            new_papers=dashboard.stats['new_papers'] + 1,
                            total_papers=dashboard.stats['total_papers'] + 1
                        )
                        time.sleep(0.3)
                    
                    print(f"📈 Semantic Scholar: 3 new papers added from 6 results")
                    time.sleep(0.5)
                    
                    # Rate limiting
                    print(f"⏱️ Rate limiting: waiting 3 seconds before next API call...")
                    for countdown in range(3, 0, -1):
                        print(f"⏳ Countdown: {countdown}s...")
                        time.sleep(1)
                    
                    # OpenAlex simulation
                    print(f"🔍 Searching OpenAlex: '{keyword}' ({year}) - limit 10")
                    print("📡 Making API request to OpenAlex...")
                    time.sleep(1)
                    
                    dashboard.update_stats(api_calls=dashboard.stats['api_calls'] + 1)
                    
                    print("✅ API response received - processing 4 results")
                    for k in range(2):
                        paper_title = f"OpenAlex {keyword.title()} Study {k+1}"
                        citations = (k+1) * 30
                        print(f"📄 Paper {k+1}: \"{paper_title[:40]}...\" ({citations} citations)")
                        print(f"➕ Added paper: \"{paper_title[:40]}...\" ({citations} citations)")
                        dashboard.update_stats(
                            new_papers=dashboard.stats['new_papers'] + 1,
                            total_papers=dashboard.stats['total_papers'] + 1
                        )
                        time.sleep(0.3)
                    
                    print(f"📈 OpenAlex: 2 new papers added from 4 results")
                    print(f"⏱️ Rate limiting: waiting 3 seconds before next keyword...")
                    for countdown in range(3, 0, -1):
                        print(f"⏳ Countdown: {countdown}s...")
                        time.sleep(1)
                
                print(f"✅ {domain} {year} completed: 10 papers collected this year")
                print(f"🎯 Session total: 10 new papers | Overall total: {dashboard.stats['total_papers']}/800 ({(dashboard.stats['total_papers']/800)*100:.1f}%)")
                time.sleep(1)
            
            print(f"🏁 Domain {i+1} ({domain}) completed!")
            time.sleep(1)
        
        print(f"🏁 Collection session complete!")
        print(f"📊 Final count: {dashboard.stats['total_papers']} papers")
        print(f"📈 New papers this session: {dashboard.stats['new_papers']}")
        print(f"🎯 Target achievement: {(dashboard.stats['total_papers']/800)*100:.1f}% ({dashboard.stats['total_papers']}/800)")
        print(f"💾 Saving progress to data/raw_collected_papers.json...")
        time.sleep(2)
        print(f"✅ Progress saved successfully!")
        
    finally:
        sys.stdout = original_stdout

def main():
    console = Console()
    console.print("🚀 Starting Paper Collection Dashboard", style="bold green")
    console.print("Watch the dashboard update in real-time!\n")
    
    dashboard = CollectionDashboard()
    
    # Create progress bars
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
        
        # Progress panel
        progress_panel = Panel(progress, title="Collection Progress", border_style="bright_blue")
        
        # Stats and logs layout
        stats_logs_layout = dashboard.create_layout()
        
        # Combine vertically
        main_layout.split_column(
            Layout(progress_panel, size=6),
            Layout(stats_logs_layout)
        )
        
        return main_layout
    
    try:
        with Live(create_full_layout(), refresh_per_second=2) as live:
            
            # Start simulation in background
            import threading
            
            def run_simulation():
                simulate_paper_collection(dashboard)
            
            # Start simulation
            simulation_thread = threading.Thread(target=run_simulation)
            simulation_thread.daemon = True
            simulation_thread.start()
            
            # Update progress bars and stats
            start_papers = dashboard.stats['total_papers']
            for i in range(60):  # Run for 60 seconds
                time.sleep(1)
                
                # Update progress based on current stats
                current_papers = dashboard.stats['total_papers']
                progress.update(main_task, completed=current_papers)
                
                # Update domain progress (simulate)
                domain_progress = (i % 20) * 5  # Cycle through domain progress
                progress.update(domain_task, completed=domain_progress)
                
                # Stop if simulation is done
                if not simulation_thread.is_alive():
                    break
            
            # Final update
            progress.update(main_task, completed=dashboard.stats['total_papers'])
            progress.update(domain_task, completed=100)
            
            # Show final state for a few seconds
            time.sleep(3)
    
    except KeyboardInterrupt:
        console.print("\n⚠️ Dashboard interrupted by user")
    except Exception as e:
        console.print(f"\n❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()
    
    console.print("\n✅ Dashboard demo completed!")
    console.print(f"📊 Final stats: {dashboard.stats['total_papers']} papers, {dashboard.stats['api_calls']} API calls")

if __name__ == "__main__":
    main()