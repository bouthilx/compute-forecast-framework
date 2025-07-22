"""Simple progress tracking for PDF downloads using the same approach as consolidate command."""

import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
import threading
import time

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    ProgressColumn,
    Task,
)
from rich.live import Live

logger = logging.getLogger(__name__)


class StatusColumn(ProgressColumn):
    """Custom column to show download status counts."""
    
    def __init__(self):
        super().__init__()
    
    def render(self, task: Task) -> str:
        """Render the status counts."""
        # Extract counts from task fields
        success = task.fields.get('success', 0)
        failed = task.fields.get('failed', 0)
        broken = task.fields.get('broken', 0)
        
        return f"[green]success:{success}[/green] [yellow]failed:{failed}[/yellow] [red]broken:{broken}[/red]"


class DetailedProgressColumn(ProgressColumn):
    """Custom column showing percentage, count, elapsed time and ETA."""
    
    def render(self, task: Task) -> str:
        """Render detailed progress information."""
        if task.total is None:
            return ""
        
        # Calculate percentage
        percentage = (task.completed / task.total * 100) if task.total > 0 else 0
        
        # Get elapsed time
        elapsed = task.elapsed
        if elapsed is None:
            elapsed_str = "00:00:00"
        else:
            days = int(elapsed // 86400)
            hours = int((elapsed % 86400) // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            if days > 0:
                elapsed_str = f"{days:02d} {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Calculate ETA
        if task.speed and task.remaining:
            eta_seconds = task.remaining / task.speed
            eta_datetime = datetime.now() + timedelta(seconds=eta_seconds)
            eta_str = eta_datetime.strftime("%Y-%m-%d %H:%M:%S ETA")
        else:
            eta_str = "--:--:-- ETA"
        
        return f"{percentage:3.0f}% ({task.completed}/{task.total}) {elapsed_str} ({eta_str})"


class SimpleDownloadProgressManager:
    """Simplified progress display for PDF downloads."""

    def __init__(self, console: Optional[Console] = None, max_parallel: int = 5):
        """Initialize progress manager.

        Args:
            console: Rich console instance
            max_parallel: Maximum parallel downloads (unused in simple version)
        """
        self.console = console or Console()

        # Progress tracking
        self.total_papers = 0
        self.completed = 0
        self.failed = 0  # Temporary failures (can be retried)
        self.broken = 0  # Permanent failures (should not be retried)
        self.active_downloads: Dict[str, Dict[str, Any]] = {}

        # Threading
        self._lock = threading.Lock()

        # Progress bars
        self.progress = None
        self.live = None
        self.overall_task = None

    def start(self, total_papers: int):
        """Start progress tracking.

        Args:
            total_papers: Total number of papers to download
        """
        self.total_papers = total_papers
        self.completed = 0
        self.failed = 0
        self.broken = 0

        # Create progress bar with custom columns
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DetailedProgressColumn(),
            "[",
            StatusColumn(),
            "]",
            console=self.console,
            disable=False,
        )

        # Create overall progress task with custom fields
        self.overall_task = self.progress.add_task(
            "[cyan]Downloading papers[/cyan]", 
            total=total_papers,
            success=0,
            failed=0,
            broken=0
        )

        # Start live display with transient mode
        self.live = Live(
            self.progress,
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self.live.start()

    def stop(self):
        """Stop progress tracking."""
        if self.live:
            self.live.stop()

        # Print final summary
        self.console.print(
            f"\n[green]✓[/green] Downloaded {self.completed} papers successfully"
        )
        if self.failed > 0:
            self.console.print(f"[yellow]⚠[/yellow] Failed to download {self.failed} papers (can retry)")
        if self.broken > 0:
            self.console.print(f"[red]✗[/red] Failed to download {self.broken} papers (permanent failures)")

    def log(self, message: str, level: str = "INFO"):
        """Log a message to console.

        Args:
            message: Log message
            level: Log level (INFO, SUCCESS, ERROR, WARNING)
        """
        # Color coding
        color_map = {
            "INFO": "white",
            "SUCCESS": "green",
            "ERROR": "red",
            "WARNING": "yellow",
        }
        color = color_map.get(level, "white")

        # Log directly to console (will appear above progress bar)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.print(f"[dim]{timestamp}[/dim] [{color}]{message}[/{color}]")

        # Also log to the standard logger for verbosity support
        logger_level_map = {
            "INFO": logging.INFO,
            "SUCCESS": logging.INFO,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
        }
        logger.log(logger_level_map.get(level, logging.INFO), message)

    def start_download(self, paper_id: str, total_size: int = 0):
        """Register a new download.

        Args:
            paper_id: Paper identifier
            total_size: Total file size in bytes (unused in simple version)
        """
        with self._lock:
            self.active_downloads[paper_id] = {
                "start_time": time.time(),
            }

    def update_download(
        self, paper_id: str, transferred: int, operation: str, speed: float
    ):
        """Update progress for a specific download.

        Args:
            paper_id: Paper identifier
            transferred: Bytes transferred (unused in simple version)
            operation: Current operation
            speed: Transfer speed in bytes per second
        """
        # In simple mode, we just update the description to show current activity
        with self._lock:
            active_count = len(self.active_downloads)
            desc = f"[cyan]Downloading papers[/cyan] ({active_count} active)"
            if active_count > 0 and paper_id in self.active_downloads:
                speed_mb = speed / (1024 * 1024) if speed > 0 else 0
                desc += f" - {paper_id[:30]}: {speed_mb:.1f} MB/s"

            self.progress.update(self.overall_task, description=desc)

    def complete_download(self, paper_id: str, success: bool, permanent_failure: bool = False):
        """Mark download as complete.

        Args:
            paper_id: Paper identifier
            success: Whether download was successful
            permanent_failure: Whether this is a permanent failure (broken)
        """
        with self._lock:
            # Remove from active downloads
            if paper_id in self.active_downloads:
                del self.active_downloads[paper_id]

            # Update counters
            if success:
                self.completed += 1
                self.log(f"Downloaded {paper_id}", "SUCCESS")
            else:
                if permanent_failure:
                    self.broken += 1
                    self.log(f"Failed to download {paper_id} (permanent)", "ERROR")
                else:
                    self.failed += 1
                    self.log(f"Failed to download {paper_id}", "ERROR")

            # Update overall progress
            self.progress.advance(self.overall_task, 1)
            
            # Update task fields for custom columns
            self.progress.update(
                self.overall_task, 
                success=self.completed,
                failed=self.failed,
                broken=self.broken
            )

    def get_progress_callback(self) -> Callable[[str, int, str, float], None]:
        """Get a progress callback function for downloads.

        Returns:
            Callback function that can be passed to downloaders
        """

        def callback(
            paper_id: str, bytes_transferred: int, operation: str, speed: float
        ):
            # Check if this is a new download
            if paper_id not in self.active_downloads:
                self.start_download(paper_id, bytes_transferred)
            else:
                self.update_download(paper_id, bytes_transferred, operation, speed)

        return callback

    def get_stats(self) -> Dict[str, int]:
        """Get current download statistics.

        Returns:
            Dictionary with download stats
        """
        total_attempted = self.completed + self.failed + self.broken
        return {
            "total": self.total_papers,
            "completed": self.completed,
            "failed": self.failed,
            "broken": self.broken,
            "in_progress": len(self.active_downloads),
            "success_rate": self.completed / max(total_attempted, 1) * 100,
        }
