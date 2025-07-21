"""Download command for fetching PDFs from discovered URLs."""

import typer
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

from compute_forecast.pipeline.metadata_collection.models import Paper


console = Console()

# Load environment variables
load_dotenv()


def load_papers_for_download(papers_path: Path) -> List[Paper]:
    """Load papers from JSON file and filter those with PDF URLs."""
    with open(papers_path, "r") as f:
        data = json.load(f)

    # Handle both direct paper list and wrapped format
    if isinstance(data, dict):
        papers_data = data.get("papers", [])
    else:
        papers_data = data

    # Convert to Paper objects and filter those with PDF URLs
    papers = []
    for paper_data in papers_data:
        paper = Paper.from_dict(paper_data)
        if paper.pdf_url:
            papers.append(paper)

    return papers


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
    issues = []

    # Check Google Drive configuration
    if get_config_value("GOOGLE_DRIVE_FOLDER_ID") is None:
        issues.append("GOOGLE_DRIVE_FOLDER_ID not set in .env file")

    if get_config_value("GOOGLE_CREDENTIALS_PATH") is None:
        issues.append("GOOGLE_CREDENTIALS_PATH not set in .env file")
    else:
        creds_path = Path(get_config_value("GOOGLE_CREDENTIALS_PATH"))
        if not creds_path.exists():
            issues.append(f"Google credentials file not found at: {creds_path}")

    # Check local cache configuration
    cache_dir = get_config_value("LOCAL_CACHE_DIR", ".cache/pdfs")
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        console.print(f"[yellow]Creating cache directory: {cache_path}[/yellow]")
        cache_path.mkdir(parents=True, exist_ok=True)

    if issues:
        console.print("[red]Configuration issues found:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        return False

    return True


def main(
    papers: Path = typer.Option(
        ..., "--papers", help="Path to papers JSON file with PDF URLs"
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
    """

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
    console.print(
        f"  Google Drive folder: {get_config_value('GOOGLE_DRIVE_FOLDER_ID')}"
    )
    console.print()

    # Create placeholder for orchestrator
    # TODO: Import and use actual DownloadOrchestrator once implemented
    console.print(
        "[yellow]Note:[/yellow] Download orchestrator not yet implemented. "
        "This is a placeholder showing the command structure."
    )
    console.print()
    console.print("Would download the following papers:")
    for i, paper in enumerate(papers_to_download[:5]):
        console.print(f"  {i + 1}. {paper.paper_id}: {paper.title[:60]}...")
    if len(papers_to_download) > 5:
        console.print(f"  ... and {len(papers_to_download) - 5} more")

    # Save initial state
    if resume:
        save_download_state(state)

    # TODO: Implement actual download logic with DownloadOrchestrator
    # orchestrator = DownloadOrchestrator(
    #     parallel_workers=parallel,
    #     rate_limit=rate_limit,
    #     timeout=timeout,
    #     max_retries=max_retries,
    #     retry_delay=retry_delay,
    #     exponential_backoff=exponential_backoff,
    #     cache_dir=cache_dir,
    #     progress_manager=progress_manager if not no_progress else None,
    # )
    #
    # updated_papers = orchestrator.download_papers(
    #     papers_to_download,
    #     state=state,
    #     resume=resume,
    # )
    #
    # # Save updated papers with download status
    # save_papers(updated_papers, papers)
