#!/usr/bin/env python3
"""
Paper Collection Dashboard with Progress Tracking and Statistics

A comprehensive dashboard for monitoring paper collection progress across research domains
with real-time statistics, progress bars, and structured logging using Rich.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from rich.logging import RichHandler
from rich.align import Align
from rich.columns import Columns
import logging

# Configure logging with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("collection")

@dataclass
class DomainStats:
    """Statistics for a research domain."""
    name: str
    total_papers: int = 0
    papers_by_year: Dict[int, int] = field(default_factory=dict)
    target_papers: int = 48  # 8 papers per domain per year * 6 years
    computational_rich: int = 0
    high_citation: int = 0
    completion_percentage: float = 0.0
    
    def update_completion(self):
        """Update completion percentage."""
        self.completion_percentage = (self.total_papers / self.target_papers) * 100 if self.target_papers > 0 else 0

@dataclass
class CollectionProgress:
    """Overall collection progress tracking."""
    total_domains: int = 6
    completed_domains: int = 0
    total_papers_target: int = 288  # 48 papers * 6 domains
    total_papers_collected: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def overall_percentage(self) -> float:
        return (self.total_papers_collected / self.total_papers_target) * 100 if self.total_papers_target > 0 else 0

class CollectionDashboard:
    """Rich-based dashboard for paper collection monitoring."""
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
        
        # Research domains based on mila taxonomy
        self.domains = [
            "Computer Vision & Medical Imaging",
            "Natural Language Processing", 
            "Reinforcement Learning & Robotics",
            "Deep Learning & Neural Architectures",
            "Graph Learning & Network Analysis",
            "Scientific Computing & Applications"
        ]
        
        # Initialize domain statistics
        self.domain_stats: Dict[str, DomainStats] = {
            domain: DomainStats(name=domain) for domain in self.domains
        }
        
        self.collection_progress = CollectionProgress()
        self.log_messages: List[str] = []
        
        # Progress task IDs
        self.main_task_id: Optional[TaskID] = None
        self.domain_task_ids: Dict[str, TaskID] = {}
        
        self._setup_layout()
        self._load_existing_data()
    
    def _setup_layout(self):
        """Setup the Rich layout structure."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=5),
            Layout(name="stats", size=12),
            Layout(name="logs", minimum_size=10)
        )
        
        # Split stats into domain boxes and summary
        self.layout["stats"].split_row(
            Layout(name="domain_stats", ratio=4),
            Layout(name="summary_stats", ratio=1)
        )
    
    def _load_existing_data(self):
        """Load existing data files to initialize statistics."""
        try:
            # Load domain statistics from existing files
            data_files = [
                "all_domains_actual_fix.json",
                "final_corrected_domain_stats.json",
                "temporal_analysis_data_FIXED.json"
            ]
            
            for file_path in data_files:
                path = Path(file_path)
                if path.exists():
                    self._process_data_file(path)
                    logger.info(f"Loaded data from {file_path}")
            
            # Update completion percentages
            for stats in self.domain_stats.values():
                stats.update_completion()
            
            # Update overall progress
            self.collection_progress.total_papers_collected = sum(
                stats.total_papers for stats in self.domain_stats.values()
            )
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def _process_data_file(self, file_path: Path):
        """Process a data file to extract statistics."""
        try:
            with open(file_path) as f:
                data = json.load(f)
            
            if file_path.name == "final_corrected_domain_stats.json":
                # Process corrected domain statistics
                for domain_key, stats in data.items():
                    # Map domain keys to full names
                    domain_mapping = {
                        "cv": "Computer Vision & Medical Imaging",
                        "nlp": "Natural Language Processing",
                        "rl": "Reinforcement Learning & Robotics", 
                        "dl": "Deep Learning & Neural Architectures",
                        "graph": "Graph Learning & Network Analysis",
                        "sci": "Scientific Computing & Applications"
                    }
                    
                    full_name = domain_mapping.get(domain_key, domain_key)
                    if full_name in self.domain_stats:
                        if isinstance(stats, dict):
                            self.domain_stats[full_name].total_papers = stats.get("total_papers", 0)
                        else:
                            self.domain_stats[full_name].total_papers = stats
            
            elif file_path.name == "temporal_analysis_data_FIXED.json":
                # Process temporal analysis data for year-by-year breakdown
                for domain_data in data:
                    domain_name = domain_data.get("domain")
                    if domain_name in self.domain_stats:
                        year_data = domain_data.get("year_data", {})
                        for year_str, count in year_data.items():
                            if year_str.isdigit():
                                year = int(year_str)
                                self.domain_stats[domain_name].papers_by_year[year] = count
                        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def create_header(self) -> Panel:
        """Create the header panel."""
        title = "[bold cyan]Paper Collection Dashboard[/bold cyan]"
        subtitle = f"Monitoring collection across {self.collection_progress.total_domains} research domains"
        elapsed = datetime.now() - self.collection_progress.start_time
        
        header_text = f"{title}\n{subtitle}\nRuntime: {elapsed}"
        return Panel(Align.center(header_text), style="bold blue")
    
    def create_progress_panel(self) -> Panel:
        """Create the progress panel."""
        if self.main_task_id is None:
            self.main_task_id = self.progress.add_task(
                "Overall Collection Progress", 
                total=self.collection_progress.total_papers_target
            )
        
        # Update main progress
        self.progress.update(
            self.main_task_id, 
            completed=self.collection_progress.total_papers_collected
        )
        
        return Panel(self.progress, title="[bold green]Collection Progress", border_style="green")
    
    def create_domain_stats_panel(self) -> Panel:
        """Create domain statistics panels."""
        domain_panels = []
        
        for domain_name, stats in self.domain_stats.items():
            # Create table for this domain
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")
            
            # Add statistics rows
            table.add_row("Papers", f"{stats.total_papers:,}")
            table.add_row("Target", f"{stats.target_papers:,}")
            table.add_row("Progress", f"{stats.completion_percentage:.1f}%")
            
            # Add recent years data
            recent_years = sorted(stats.papers_by_year.keys())[-3:] if stats.papers_by_year else []
            for year in recent_years:
                table.add_row(f"{year}", f"{stats.papers_by_year[year]:,}")
            
            # Determine panel color based on completion
            if stats.completion_percentage >= 100:
                style = "bold green"
            elif stats.completion_percentage >= 75:
                style = "bold yellow"
            else:
                style = "bold red"
            
            # Create panel for this domain (shortened name for space)
            short_name = domain_name.split()[0] + (" " + domain_name.split()[1] if len(domain_name.split()) > 1 else "")
            panel = Panel(
                table,
                title=f"[{style}]{short_name}[/{style}]",
                border_style=style.split()[1] if " " in style else style
            )
            domain_panels.append(panel)
        
        # Arrange panels in columns
        return Panel(
            Columns(domain_panels, equal=True, expand=True),
            title="[bold blue]Domain Statistics",
            border_style="blue"
        )
    
    def create_summary_panel(self) -> Panel:
        """Create overall summary statistics panel."""
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="bold white")
        
        # Calculate summary statistics
        total_papers = sum(stats.total_papers for stats in self.domain_stats.values())
        total_target = sum(stats.target_papers for stats in self.domain_stats.values())
        avg_completion = sum(stats.completion_percentage for stats in self.domain_stats.values()) / len(self.domain_stats)
        
        # Active domains (>50% complete)
        active_domains = sum(1 for stats in self.domain_stats.values() if stats.completion_percentage > 50)
        
        # Top performing domain
        top_domain = max(self.domain_stats.values(), key=lambda x: x.completion_percentage)
        
        table.add_row("Total Papers", f"{total_papers:,}")
        table.add_row("Total Target", f"{total_target:,}")
        table.add_row("Overall Progress", f"{avg_completion:.1f}%")
        table.add_row("Active Domains", f"{active_domains}/{len(self.domains)}")
        table.add_row("Top Domain", f"{top_domain.name.split()[0]}")
        table.add_row("Top Progress", f"{top_domain.completion_percentage:.1f}%")
        
        # Add estimated completion time
        elapsed = datetime.now() - self.collection_progress.start_time
        if avg_completion > 0:
            estimated_total = elapsed * (100 / avg_completion)
            remaining = estimated_total - elapsed
            table.add_row("Est. Remaining", f"{remaining}")
        
        return Panel(
            table,
            title="[bold magenta]Summary Statistics",
            border_style="magenta"
        )
    
    def create_logs_panel(self) -> Panel:
        """Create the logs panel."""
        # Get recent log messages (last 15)
        recent_logs = self.log_messages[-15:] if self.log_messages else ["[dim]No logs yet...[/dim]"]
        
        log_text = "\n".join(recent_logs)
        return Panel(
            log_text,
            title="[bold yellow]Collection Logs",
            border_style="yellow",
            height=10
        )
    
    def add_log(self, message: str, level: str = "info"):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        level_colors = {
            "info": "blue",
            "warning": "yellow", 
            "error": "red",
            "success": "green"
        }
        
        color = level_colors.get(level, "white")
        formatted_message = f"[dim]{timestamp}[/dim] [{color}]{level.upper()}[/{color}] {message}"
        
        self.log_messages.append(formatted_message)
        logger.info(message)
    
    def update_domain_stats(self, domain: str, papers_added: int = 0, **kwargs):
        """Update statistics for a specific domain."""
        if domain in self.domain_stats:
            stats = self.domain_stats[domain]
            stats.total_papers += papers_added
            
            # Update other metrics if provided
            for key, value in kwargs.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            
            stats.update_completion()
            
            # Update overall progress
            self.collection_progress.total_papers_collected = sum(
                s.total_papers for s in self.domain_stats.values()
            )
    
    def update_display(self):
        """Update all dashboard components."""
        self.layout["header"].update(self.create_header())
        self.layout["progress"].update(self.create_progress_panel())
        self.layout["domain_stats"].update(self.create_domain_stats_panel())
        self.layout["summary_stats"].update(self.create_summary_panel())
        self.layout["logs"].update(self.create_logs_panel())
    
    def run_collection_simulation(self):
        """Simulate paper collection process with dashboard updates."""
        self.add_log("Starting paper collection process...", "info")
        
        with Live(self.layout, refresh_per_second=2, screen=True):
            try:
                # Simulate collection for each domain
                for i, domain in enumerate(self.domains):
                    self.add_log(f"Processing domain: {domain}", "info")
                    
                    # Simulate collecting papers with progress updates
                    papers_to_collect = 10  # Simulate collecting 10 papers
                    
                    for j in range(papers_to_collect):
                        time.sleep(0.5)  # Simulate processing time
                        
                        self.update_domain_stats(domain, papers_added=1)
                        self.add_log(f"Collected paper {j+1} for {domain.split()[0]}", "success")
                        self.update_display()
                    
                    self.add_log(f"Completed collection for {domain}", "success")
                    time.sleep(1)
                
                self.add_log("Paper collection process completed!", "success")
                
                # Show final summary
                time.sleep(3)
                
            except KeyboardInterrupt:
                self.add_log("Collection process interrupted by user", "warning")
            except Exception as e:
                self.add_log(f"Error during collection: {e}", "error")

def main():
    """Main execution function."""
    dashboard = CollectionDashboard()
    
    # Run the collection simulation
    dashboard.run_collection_simulation()
    
    print("\nCollection dashboard completed. Check logs above for details.")

if __name__ == "__main__":
    main()