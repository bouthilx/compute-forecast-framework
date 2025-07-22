"""Download command for fetching PDFs from discovered URLs."""

import typer
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.orchestration import DownloadOrchestrator
from compute_forecast.monitoring.simple_download_progress import (
    SimpleDownloadProgressManager,
)


console = Console()

# Load environment variables
load_dotenv()


def load_papers_for_download(papers_path: Path) -> List[Paper]:
    """Load papers from JSON file and filter those with PDF URLs."""
    logger = logging.getLogger(__name__)

    with open(papers_path, "r") as f:
        data = json.load(f)

    # Handle both direct paper list and wrapped format
    if isinstance(data, dict):
        papers_data = data.get("papers", [])
    else:
        papers_data = data

    logger.info(f"Loaded {len(papers_data)} papers from {papers_path}")

    # Convert to Paper objects and filter those with PDF URLs
    papers = []
    papers_without_urls = 0

    for i, paper_data in enumerate(papers_data):
        paper = Paper.from_dict(paper_data)

        # Generate paper_id if not present
        if not paper.paper_id:
            # Use existing identifiers or generate from title/venue/year
            if paper.arxiv_id:
                paper.paper_id = f"arxiv_{paper.arxiv_id}"
            elif paper.openalex_id:
                paper.paper_id = f"openalex_{paper.openalex_id}"
            elif paper.doi:
                paper.paper_id = f"doi_{paper.doi.replace('/', '_').replace('.', '_')}"
            else:
                # Generate from title, venue, year
                title_slug = paper.title[:50].lower()
                title_slug = "".join(c if c.isalnum() else "_" for c in title_slug)
                paper.paper_id = f"{paper.venue}_{paper.year}_{title_slug}_{i}"

        # Extract best PDF URL from urls field
        pdf_url = get_best_pdf_url(paper)
        if pdf_url:
            # Store the selected PDF URL in processing_flags for easy access
            paper.processing_flags["selected_pdf_url"] = pdf_url
            papers.append(paper)
            logger.debug(f"Paper {paper.paper_id} has PDF URL: {pdf_url}")
        else:
            papers_without_urls += 1
            logger.debug(f"Paper {paper.paper_id} has no usable PDF URL")

    logger.info(
        f"Found {len(papers)} papers with PDF URLs, {papers_without_urls} without URLs"
    )
    return papers


def get_best_pdf_url(paper: Paper) -> Optional[str]:
    """Get the best PDF URL from a paper's URL records.

    Prioritizes original=True records, otherwise selects the most recent one.
    Only considers URLs that appear to be PDFs.
    """
    if not paper.urls:
        return None

    # Filter for likely PDF URLs
    pdf_urls = []
    for url_record in paper.urls:
        url = url_record.data.url
        # Check if URL likely points to a PDF
        if url and (".pdf" in url.lower() or "pdf" in url.lower()):
            pdf_urls.append(url_record)

    if not pdf_urls:
        return None

    # First, look for original URLs
    original_urls = [record for record in pdf_urls if record.original]
    if original_urls:
        # If multiple originals, take the most recent
        original_urls.sort(key=lambda r: r.timestamp, reverse=True)
        return original_urls[0].data.url

    # No originals, take the most recent URL
    pdf_urls.sort(key=lambda r: r.timestamp, reverse=True)
    return pdf_urls[0].data.url


def get_download_state_path() -> Path:
    """Get path for download state file."""
    state_dir = Path(".cf_state/download")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "download_progress.json"


def load_download_state() -> Dict[str, Any]:
    """Load download state from checkpoint file."""
    state_path = get_download_state_path()
    if state_path.exists():
        with open(state_path, "r") as f:
            return json.load(f)
    return {
        "completed": [],
        "failed": [],
        "in_progress": [],
        "last_updated": None,
    }


def save_download_state(state: Dict[str, Any]):
    """Save download state to checkpoint file."""
    state["last_updated"] = datetime.now().isoformat()
    state_path = get_download_state_path()
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value from environment or default."""
    return os.getenv(key, default)


def validate_configuration() -> bool:
    """Validate required configuration is present."""
    warnings = []

    # Check Google Drive configuration (optional)
    has_google_drive = False
    if get_config_value("GOOGLE_DRIVE_FOLDER_ID") is not None:
        has_google_drive = True
        if get_config_value("GOOGLE_CREDENTIALS_PATH") is None:
            warnings.append(
                "GOOGLE_DRIVE_FOLDER_ID set but GOOGLE_CREDENTIALS_PATH not set"
            )
        else:
            creds_path = Path(get_config_value("GOOGLE_CREDENTIALS_PATH"))
            if not creds_path.exists():
                warnings.append(f"Google credentials file not found at: {creds_path}")

    # Check local cache configuration
    cache_dir = get_config_value("LOCAL_CACHE_DIR", ".cache/pdfs")
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        console.print(f"[yellow]Creating cache directory: {cache_path}[/yellow]")
        cache_path.mkdir(parents=True, exist_ok=True)

    if warnings:
        console.print("[yellow]Configuration warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")
        if has_google_drive:
            console.print(
                "[yellow]Google Drive upload will be disabled, using local cache only[/yellow]"
            )
    elif not has_google_drive:
        console.print(
            "[blue]Google Drive not configured, using local cache only[/blue]"
        )

    return True  # Always return True since Google Drive is optional


def main(
    papers: Path = typer.Option(
        ..., "--papers", help="Path to papers JSON file with PDF URLs"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Path for output JSON file with download status (optional)"
    ),
    parallel: int = typer.Option(
        None, "--parallel", help="Number of parallel downloads (default from .env or 5)"
    ),
    rate_limit: Optional[float] = typer.Option(
        None, "--rate-limit", help="Download rate limit (requests/second)"
    ),
    timeout: int = typer.Option(
        30, "--timeout", help="Download timeout per file (seconds)"
    ),
    retry_failed: bool = typer.Option(
        False, "--retry-failed", help="Retry previously failed downloads"
    ),
    max_retries: int = typer.Option(
        3, "--max-retries", help="Maximum retry attempts per paper"
    ),
    retry_delay: int = typer.Option(
        5, "--retry-delay", help="Delay between retries (seconds)"
    ),
    exponential_backoff: bool = typer.Option(
        False, "--exponential-backoff", help="Use exponential backoff for retries"
    ),
    resume: bool = typer.Option(False, "--resume", help="Resume interrupted downloads"),
    no_progress: bool = typer.Option(
        False, "--no-progress", help="Disable progress bars"
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity level (-v for INFO, -vv for DEBUG)",
    ),
):
    """
    Download PDFs using URLs discovered by consolidate command.

    This command downloads PDFs from URLs found during the consolidation phase,
    stores them in a local cache, and uploads them to Google Drive for permanent
    storage.

    Examples:

        # Basic download
        cf download --papers papers.json

        # Download with custom parallelism
        cf download --papers papers.json --parallel 10

        # Retry failed downloads
        cf download --papers papers.json --retry-failed

        # Resume interrupted download session
        cf download --papers papers.json --resume

        # Enable verbose logging
        cf download --papers papers.json -v      # INFO level logging
        cf download --papers papers.json -vv     # DEBUG level logging
    """

    # Configure logging based on verbosity
    log_level = logging.WARNING
    if verbose >= 2:
        log_level = logging.DEBUG
    elif verbose >= 1:
        log_level = logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Add console handler for verbose output
    )

    # Add a separate handler for verbose logging that works with Rich console
    if verbose > 0:
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

        # Create a new handler that outputs to stderr (won't interfere with Rich progress bar)
        import sys

        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(log_level)

    # Validate configuration
    if not validate_configuration():
        raise typer.Exit(1)

    # Load configuration
    if parallel is None:
        parallel = int(get_config_value("DEFAULT_PARALLEL_WORKERS", "5"))

    cache_dir = Path(get_config_value("LOCAL_CACHE_DIR", ".cache/pdfs"))

    # Validate input file
    if not papers.exists():
        console.print(f"[red]Error:[/red] Papers file not found: {papers}")
        raise typer.Exit(1)

    # Load papers
    console.print(f"Loading papers from {papers}...")
    try:
        all_papers = load_papers_for_download(papers)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load papers: {e}")
        raise typer.Exit(1)

    if not all_papers:
        console.print("[yellow]No papers with PDF URLs found in input file.[/yellow]")
        raise typer.Exit(0)

    # Load state if resuming
    state = (
        load_download_state()
        if resume
        else {
            "completed": [],
            "failed": [],
            "in_progress": [],
            "last_updated": None,
        }
    )

    # Filter papers based on state and flags
    papers_to_download = []

    for paper in all_papers:
        paper_id = paper.paper_id

        # Skip if already completed (unless retry_failed is set)
        if paper_id in state["completed"]:
            continue

        # Include failed papers only if retry_failed is set
        if paper_id in state["failed"] and not retry_failed:
            continue

        papers_to_download.append(paper)

    if not papers_to_download:
        if resume and state["completed"]:
            console.print(
                f"[green]All papers already downloaded![/green] "
                f"({len(state['completed'])} completed)"
            )
        else:
            console.print("[yellow]No papers to download.[/yellow]")
        raise typer.Exit(0)

    # Show download plan
    table = Table(title="Download Plan")
    table.add_column("Total Papers", style="cyan", justify="right")
    table.add_column("To Download", style="green", justify="right")
    table.add_column("Already Completed", style="blue", justify="right")
    table.add_column("Failed (to retry)", style="red", justify="right")

    failed_to_retry = len(
        [p for p in papers_to_download if p.paper_id in state["failed"]]
    )

    table.add_row(
        str(len(all_papers)),
        str(len(papers_to_download)),
        str(len(state["completed"])),
        str(failed_to_retry) if retry_failed else "0",
    )

    console.print(table)
    console.print()

    # Configuration summary
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Parallel downloads: {parallel}")
    console.print(f"  Timeout per file: {timeout}s")
    console.print(f"  Max retries: {max_retries}")
    console.print(f"  Cache directory: {cache_dir}")
    google_drive_folder = get_config_value("GOOGLE_DRIVE_FOLDER_ID")
    if google_drive_folder:
        console.print(f"  Google Drive folder: {google_drive_folder}")
    else:
        console.print("  Google Drive: [yellow]Not configured[/yellow]")
    console.print()

    # Create progress manager if not disabled
    progress_manager = (
        None
        if no_progress
        else SimpleDownloadProgressManager(console=console, max_parallel=parallel)
    )

    # Create download orchestrator
    orchestrator = DownloadOrchestrator(
        parallel_workers=parallel,
        rate_limit=rate_limit,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        exponential_backoff=exponential_backoff,
        cache_dir=str(cache_dir),
        google_drive_credentials=get_config_value("GOOGLE_CREDENTIALS_PATH"),
        google_drive_folder_id=get_config_value("GOOGLE_DRIVE_FOLDER_ID"),
        progress_manager=progress_manager,
        state_path=get_download_state_path(),
    )

    # Filter papers based on state
    papers_to_process = orchestrator.filter_papers_for_download(
        all_papers, retry_failed=retry_failed, resume=resume
    )

    console.print(f"Starting download of {len(papers_to_process)} papers...")

    # Determine output file path
    output_path = output
    if output_path and output is not None:
        console.print(f"  [blue]Output file:[/blue] {output_path}")
    
    # Callback to save papers periodically
    def save_papers_callback(updated_papers: List[Paper]):
        # Only save if output path is specified
        if output_path is not None:
            # Update papers in original data structure
            paper_dict = {p.paper_id: p for p in updated_papers}
            for i, p in enumerate(all_papers):
                if p.paper_id in paper_dict:
                    all_papers[i] = paper_dict[p.paper_id]

            # Save to output file (not input file)
            save_papers_to_file(all_papers, output_path, papers)

    # Download papers
    try:
        successful, failed = orchestrator.download_papers(
            papers_to_process, save_papers_callback=save_papers_callback
        )

        # Final summary
        console.print()
        console.print("[bold]Download Summary:[/bold]")
        console.print(f"  [green]Successful:[/green] {successful}")
        console.print(f"  [red]Failed:[/red] {failed}")

        # Show storage stats
        stats = orchestrator.get_download_stats()
        storage_stats = stats.get("storage_stats", {})
        if storage_stats:
            cache_stats = storage_stats.get("local_cache", {})
            console.print(
                f"  [blue]Cache size:[/blue] {cache_stats.get('total_size_mb', 0):.1f} MB"
            )
            console.print(
                f"  [blue]Cached files:[/blue] {cache_stats.get('total_files', 0)}"
            )

        # Export failed papers if any
        if failed > 0:
            console.print()
            console.print("[bold]Exporting Failed Papers:[/bold]")
            failed_papers_file = orchestrator.export_failed_papers()
            if failed_papers_file:
                console.print(
                    f"  [yellow]Failed papers exported to:[/yellow] {failed_papers_file}"
                )

                # Show summary of failure types
                if orchestrator.state.failed_papers:
                    permanent_failures = len(
                        [
                            fp
                            for fp in orchestrator.state.failed_papers
                            if fp.permanent_failure
                        ]
                    )
                    temporary_failures = len(
                        [
                            fp
                            for fp in orchestrator.state.failed_papers
                            if not fp.permanent_failure
                        ]
                    )

                    console.print(
                        f"  [red]Permanent failures:[/red] {permanent_failures} (will not retry)"
                    )
                    console.print(
                        f"  [yellow]Temporary failures:[/yellow] {temporary_failures} (can retry)"
                    )

                    # Show breakdown by error type
                    error_summary = orchestrator._get_error_type_summary()
                    if error_summary:
                        console.print("  [dim]Error breakdown:[/dim]")
                        for error_type, stats in error_summary.items():
                            console.print(f"    {error_type}: {stats['count']} papers")
        else:
            console.print("  [green]All downloads successful![/green]")

        # Save final output if specified
        if output_path is not None:
            console.print()
            console.print(f"[green]Output saved to:[/green] {output_path}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        if progress_manager:
            progress_manager.stop()
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error during download:[/red] {e}")
        if progress_manager:
            progress_manager.stop()
        raise typer.Exit(1)


def save_papers_to_file(papers: List[Paper], output_path: Path, input_path: Path):
    """Save papers to output JSON file, preserving the original structure."""
    try:
        # Load original file structure from input file
        with open(input_path, "r") as f:
            data = json.load(f)

        # Update papers in original structure
        if isinstance(data, dict):
            data["papers"] = [p.to_dict() for p in papers]
        else:
            data = [p.to_dict() for p in papers]

        # Save to output file
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    except Exception as e:
        console.print(f"[red]Error saving papers to {output_path}:[/red] {e}")
