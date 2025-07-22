"""Progress tracking for quality checks."""

from typing import Optional
from contextlib import contextmanager
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.console import Console


class QualityCheckProgress:
    """Progress tracker for quality checks."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._progress = None
        self._task_id = None

    @contextmanager
    def track_checks(
        self, total_checks: int, description: str = "Running quality checks"
    ):
        """Context manager for tracking quality check progress."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            self._progress = progress
            self._task_id = progress.add_task(description, total=total_checks)

            try:
                yield self
            finally:
                self._progress = None
                self._task_id = None

    def update(self, check_name: str, advance: int = 1):
        """Update progress for a completed check."""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id, description=f"Running {check_name}...", advance=advance
            )

    @contextmanager
    def track_stage(self, stage_name: str):
        """Track progress for a specific stage."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Checking {stage_name} quality...", total=None)
            try:
                yield
            finally:
                progress.update(
                    task, description=f"✓ {stage_name} quality check complete"
                )
