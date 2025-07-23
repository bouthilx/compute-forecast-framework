"""Progress tracking for PDF downloads with two-level progress bars."""

import logging
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime
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
    DownloadColumn,
    TransferSpeedColumn,
    TaskID,
)
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

logger = logging.getLogger(__name__)


class DownloadProgressManager:
    """Manages progress display for PDF downloads."""

    def __init__(self, console: Optional[Console] = None, max_parallel: int = 5):
        """Initialize progress manager.

        Args:
            console: Rich console instance
            max_parallel: Maximum parallel progress bars to show
        """
        self.console = console or Console()
        self.max_parallel = max_parallel

        # Progress tracking
        self.total_papers = 0
        self.completed = 0
        self.failed = 0
        self.active_downloads: Dict[str, Dict[str, Any]] = {}

        # Threading
        self._lock = threading.Lock()
        self._running = False

        # Progress bars
        self.progress: Optional[Progress] = None
        self.live: Optional[Live] = None
        self.overall_task: Optional[TaskID] = None

        # Log messages
        self.log_messages: List[str] = []
        self.max_log_messages = 20

    def start(self, total_papers: int):
        """Start progress tracking.

        Args:
            total_papers: Total number of papers to download
        """
        self.total_papers = total_papers
        self.completed = 0
        self.failed = 0
        self._running = True

        # Create progress bars
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=False,
        )

        # Create overall progress task
        self.overall_task = self.progress.add_task(
            f"Overall: 0/{total_papers} papers", total=total_papers, visible=True
        )

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="logs", ratio=1),
            Layout(
                name="progress", size=self.max_parallel + 3
            ),  # +3 for overall bar and padding
        )

        # Start live display
        self.live = Live(
            layout, console=self.console, refresh_per_second=4, screen=False
        )
        self.live.start()

        # Start update thread
        self._update_thread = threading.Thread(target=self._update_display)
        self._update_thread.daemon = True
        self._update_thread.start()

    def stop(self):
        """Stop progress tracking."""
        self._running = False

        if self._update_thread:
            self._update_thread.join(timeout=1)

        if self.live:
            self.live.stop()

    def log(self, message: str, level: str = "INFO"):
        """Add a log message.

        Args:
            message: Log message
            level: Log level (INFO, SUCCESS, ERROR, WARNING)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Color coding
        color_map = {
            "INFO": "white",
            "SUCCESS": "green",
            "ERROR": "red",
            "WARNING": "yellow",
        }
        color = color_map.get(level, "white")

        log_entry = f"[{timestamp}] [{color}]{level}[/{color}]: {message}"

        with self._lock:
            self.log_messages.append(log_entry)
            # Keep only recent messages
            if len(self.log_messages) > self.max_log_messages:
                self.log_messages = self.log_messages[-self.max_log_messages :]

    def start_download(self, paper_id: str, total_size: int = 0):
        """Register a new download with its own progress bar.

        Args:
            paper_id: Paper identifier
            total_size: Total file size in bytes
        """
        with self._lock:
            if not self.progress:
                return
                
            # Limit number of active progress bars
            if len(self.active_downloads) >= self.max_parallel:
                # Find and remove oldest completed task
                for pid, task_info in list(self.active_downloads.items()):
                    if task_info.get("completed", False):
                        self.progress.remove_task(task_info["task"])
                        del self.active_downloads[pid]
                        break

            # Create new task
            task = self.progress.add_task(
                f"Paper: {paper_id[:20]}",
                total=total_size or 100,  # Use 100 for unknown size
                visible=True,
            )

            self.active_downloads[paper_id] = {
                "task": task,
                "start_time": time.time(),
                "completed": False,
                "operation": "Downloading",
            }

    def update_download(
        self, paper_id: str, transferred: int, operation: str, speed: float
    ):
        """Update progress for a specific download.

        Args:
            paper_id: Paper identifier
            transferred: Bytes transferred
            operation: Current operation (Downloading, Uploading to Drive, etc.)
            speed: Transfer speed in bytes per second
        """
        with self._lock:
            if paper_id in self.active_downloads and self.progress:
                task_info = self.active_downloads[paper_id]
                task = task_info["task"]
                task_info["operation"] = operation

                # Update task description with operation
                speed_mb = speed / (1024 * 1024)
                self.progress.update(
                    task,
                    completed=transferred,
                    description=f"Paper: {paper_id[:20]} • {speed_mb:.1f} MB/s • {operation}",
                )

    def complete_download(self, paper_id: str, success: bool):
        """Mark download as complete and remove progress bar.

        Args:
            paper_id: Paper identifier
            success: Whether download was successful
        """
        with self._lock:
            if paper_id in self.active_downloads:
                task_info = self.active_downloads[paper_id]
                task_info["completed"] = True

                # Complete the task
                task = task_info["task"]
                if self.progress:
                    self.progress.update(task, visible=False)

                # Schedule for removal (don't remove immediately to avoid flickering)
                # Will be removed when space is needed

            # Update counters
            if success:
                self.completed += 1
                self.log(f"Downloaded {paper_id}", "SUCCESS")
            else:
                self.failed += 1
                self.log(f"Failed to download {paper_id}", "ERROR")

            # Update overall progress
            if self.progress and self.overall_task is not None:
                self.progress.advance(self.overall_task, 1)
            self._update_overall_description()

    def _update_overall_description(self):
        """Update overall progress bar description."""
        description = (
            f"Overall: {self.completed + self.failed}/{self.total_papers} papers "
            f"[green]Success: {self.completed}[/green] "
            f"[red]Failed: {self.failed}[/red]"
        )
        if self.progress and self.overall_task is not None:
            self.progress.update(self.overall_task, description=description)

    def _update_display(self):
        """Update the display in a separate thread."""
        while self._running:
            try:
                with self._lock:
                    # Create logs panel
                    logs_content = (
                        "\n".join(self.log_messages)
                        if self.log_messages
                        else "No logs yet..."
                    )
                    logs_panel = Panel(
                        logs_content, title="Download Logs", border_style="blue"
                    )

                    # Create progress panel
                    progress_panel = Panel(
                        self.progress, title="Download Progress", border_style="green"
                    )

                    # Update layout
                    if self.live and self.live.is_started:
                        layout = self.live.renderable
                        layout["logs"].update(logs_panel)
                        layout["progress"].update(progress_panel)
                        self.live.refresh()

                time.sleep(0.25)  # Update 4 times per second

            except Exception as e:
                logger.error(f"Error updating display: {e}")

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

    def get_stats(self) -> Dict[str, float]:
        """Get current download statistics.

        Returns:
            Dictionary with download stats
        """
        return {
            "total": self.total_papers,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": len(
                [d for d in self.active_downloads.values() if not d["completed"]]
            ),
            "success_rate": self.completed / max(self.completed + self.failed, 1) * 100,
        }
