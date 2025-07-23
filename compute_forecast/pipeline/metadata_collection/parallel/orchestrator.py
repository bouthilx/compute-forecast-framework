"""Orchestrator for parallel paper collection."""

import multiprocessing
import queue
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    ProgressColumn,
    Task,
)
from rich.text import Text
from rich.live import Live

from ..sources.scrapers.base import ScrapingConfig
from ..sources.scrapers.models import SimplePaper
from .worker import VenueWorker
from .models import CollectionResult
from compute_forecast.cli.utils.logging_handler import RichConsoleHandler


logger = logging.getLogger(__name__)


class CollectionProgressColumn(ProgressColumn):
    """Custom progress column showing: percentage%, (done/total) elapsed (ETA)."""

    def render(self, task: Task) -> Text:
        """Render the progress details."""
        if task.total is None:
            return Text("")

        # Calculate percentage
        percentage = (task.completed / task.total) * 100 if task.total > 0 else 0

        # Format elapsed time
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
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            eta_str = eta_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            eta_str = "Unknown"

        # Format the complete string
        text = f"{percentage:5.1f}%, ({task.completed}/{task.total}) {elapsed_str} ({eta_str} ETA)"

        return Text(text, style="cyan")


class ParallelCollectionOrchestrator:
    """Orchestrates parallel collection of papers from multiple venues."""
    
    def __init__(
        self,
        config: ScrapingConfig,
        scraper_override: Optional[str] = None,
        console: Optional[Console] = None,
        no_progress: bool = False,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            config: Scraping configuration
            scraper_override: Optional scraper name to use for all venues
            console: Rich console for output
            no_progress: Disable progress bars
        """
        self.config = config
        self.scraper_override = scraper_override
        self.console = console or Console()
        self.no_progress = no_progress
        self.logger = logging.getLogger("orchestrator")
        
    def collect_parallel(
        self,
        venues: Dict[str, List[int]],
        output_path: Optional[Path] = None,
        checkpoint_callback: Optional[Any] = None,
    ) -> List[SimplePaper]:
        """
        Collect papers from multiple venues in parallel.
        
        Args:
            venues: Dictionary mapping venue names to lists of years
            output_path: Optional path to save intermediate results
            checkpoint_callback: Optional callback for checkpointing
            
        Returns:
            List of all collected papers
        """
        # Create shared queue for results
        result_queue = multiprocessing.Queue()
        
        # Create and start worker processes
        workers = []
        for venue, years in venues.items():
            worker = VenueWorker(
                venue=venue,
                years=years,
                config=self.config,
                result_queue=result_queue,
                scraper_override=self.scraper_override,
                log_level=logging.getLogger().level,  # Use main process log level
            )
            worker.start()
            workers.append(worker)
            self.logger.info(f"Started worker for {venue} with years {years}")
        
        # Setup progress tracking
        progress_tasks = {}  # (venue, year) -> task_id
        venue_year_pairs = []  # Ordered list of (venue, year) for progress display
        
        # Create ordered list of venue/year pairs
        for venue, years in venues.items():
            for year in sorted(years):
                venue_year_pairs.append((venue, year))
        
        # Create progress display
        progress_column = CollectionProgressColumn()
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            progress_column,
            console=self.console,
            disable=self.no_progress,
        )
        
        # Create progress bars for all venue/year combinations
        for venue, year in venue_year_pairs:
            task = progress.add_task(
                f"{venue} {year}",
                total=None,  # Will be set when we get estimate
            )
            progress_tasks[(venue, year)] = task
        
        # Process results from queue
        all_papers = []
        active_workers = len(workers)
        venue_year_status = {}  # Track completion status
        errors = []
        
        with Live(
            progress,
            console=self.console,
            refresh_per_second=4,
            vertical_overflow="visible",
            transient=True,
        ) as live:
            # Add custom logging handler if progress bars are enabled
            if not self.no_progress:
                rich_handler = RichConsoleHandler(self.console, live)
                rich_handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
                logging.getLogger().addHandler(rich_handler)
            
            # Main collection loop
            papers_by_venue_year = {}  # (venue, year) -> list of papers
            
            while active_workers > 0:
                try:
                    # Get result from queue with timeout
                    result = result_queue.get(timeout=0.1)
                    
                    # Handle worker completion
                    if result.is_worker_done:
                        active_workers -= 1
                        self.logger.info(f"Worker completed, {active_workers} workers remaining")
                        continue
                    
                    # Handle venue/year completion
                    if result.is_complete:
                        venue_year_status[(result.venue, result.year)] = "completed"
                        self.logger.info(f"Completed {result.venue} {result.year}")
                        
                        # Checkpoint if callback provided
                        if checkpoint_callback and (result.venue, result.year) in papers_by_venue_year:
                            checkpoint_callback(
                                result.venue, 
                                result.year, 
                                papers_by_venue_year[(result.venue, result.year)]
                            )
                        continue
                    
                    # Get task for progress update
                    task_id = progress_tasks.get((result.venue, result.year))
                    if task_id is None:
                        self.logger.warning(
                            f"No progress task for {result.venue} {result.year}"
                        )
                        continue
                    
                    # Handle progress initialization
                    if result.total_expected and progress.tasks[task_id].total is None:
                        progress.update(task_id, total=result.total_expected)
                        self.logger.debug(
                            f"Set total for {result.venue} {result.year}: {result.total_expected}"
                        )
                    
                    # Handle paper result
                    if result.paper:
                        all_papers.append(result.paper)
                        progress.advance(task_id, 1)
                        
                        # Track papers by venue/year for checkpointing
                        key = (result.venue, result.year)
                        if key not in papers_by_venue_year:
                            papers_by_venue_year[key] = []
                        papers_by_venue_year[key].append(result.paper)
                        
                    # Handle error result
                    elif result.error:
                        errors.append(result.error)
                        self.logger.error(result.error)
                        
                except queue.Empty:
                    # No results available, continue
                    continue
                except KeyboardInterrupt:
                    self.logger.warning("Keyboard interrupt received, stopping collection")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing result: {e}")
                    continue
            
            self.logger.info(f"All workers completed. Collected {len(all_papers)} papers total")
        
        # Wait for all workers to finish
        for worker in workers:
            worker.join(timeout=5)
            if worker.is_alive():
                self.logger.warning(f"Worker {worker.name} did not terminate cleanly")
                worker.terminate()
                worker.join()
        
        # Report errors if any
        if errors:
            self.console.print(f"\n[yellow]Encountered {len(errors)} errors during collection:[/yellow]")
            for error in errors[:5]:  # Show first 5 errors
                self.console.print(f"  - {error}")
            if len(errors) > 5:
                self.console.print(f"  ... and {len(errors) - 5} more")
        
        return all_papers