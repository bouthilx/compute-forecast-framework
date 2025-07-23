"""Collect command for gathering research papers from various venues."""

import typer
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

from compute_forecast.pipeline.metadata_collection.sources.scrapers.registry import (
    get_registry,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.base import (
    ScrapingConfig,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.models import (
    SimplePaper,
)


console = Console()


def parse_years(years_str: str) -> List[int]:
    """Parse year specification into list of years.

    Examples:
        "2024" -> [2024]
        "2020-2024" -> [2020, 2021, 2022, 2023, 2024]
        "2020,2022,2024" -> [2020, 2022, 2024]
    """
    years = []

    if "-" in years_str:
        # Range format
        parts = years_str.split("-")
        if len(parts) == 2:
            start, end = int(parts[0]), int(parts[1])
            years = list(range(start, end + 1))
    elif "," in years_str:
        # List format
        years = [int(y.strip()) for y in years_str.split(",")]
    else:
        # Single year
        years = [int(years_str)]

    return years


def load_venue_file(venue_file: Path) -> Dict[str, List[int]]:
    """Load venue specifications from file.

    Expected format (YAML):
    venues:
      - name: neurips
        years: [2020, 2021, 2022, 2023, 2024]
      - name: icml
        years: 2020-2024
    """
    import yaml

    with open(venue_file, "r") as f:
        data = yaml.safe_load(f)

    venue_specs = {}
    for venue_spec in data.get("venues", []):
        name = venue_spec["name"]
        years = venue_spec.get("years", [])

        if isinstance(years, str):
            years = parse_years(years)
        elif isinstance(years, int):
            years = [years]

        venue_specs[name] = years

    return venue_specs


def save_papers(papers: List[SimplePaper], output_path: Path, metadata: Dict[str, Any]):
    """Save collected papers to JSON file."""
    # Convert SimplePaper objects to Paper format
    converted_papers = [p.to_package_paper() for p in papers]

    output_data = {
        "collection_metadata": {
            "timestamp": datetime.now().isoformat(),
            "venues": list(set(p.venue for p in converted_papers)),
            "years": sorted(list(set(p.year for p in converted_papers))),
            "total_papers": len(converted_papers),
            "scrapers_used": list(set(p.source_scraper for p in papers)),
            **metadata,
        },
        "papers": [p.to_dict() for p in converted_papers],
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    console.print(f"[green]✓[/green] Saved {len(papers)} papers to {output_path}")


def get_checkpoint_path(venue: str, year: int) -> Path:
    """Get checkpoint file path for a venue/year combination."""
    checkpoint_dir = Path(".cf_state/collect")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir / f"{venue}_{year}_checkpoint.json"


def save_checkpoint(
    venue: str, year: int, papers: List[SimplePaper], completed: bool = False
):
    """Save collection checkpoint."""
    checkpoint_path = get_checkpoint_path(venue, year)
    checkpoint_data = {
        "venue": venue,
        "year": year,
        "papers_collected": len(papers),
        "completed": completed,
        "last_updated": datetime.now().isoformat(),
        "papers": [
            {"title": p.title, "paper_id": p.paper_id, "source_url": p.source_url}
            for p in papers
        ],
    }

    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint_data, f, indent=2)


def load_checkpoint(venue: str, year: int) -> Optional[Dict[str, Any]]:
    """Load checkpoint if it exists."""
    checkpoint_path = get_checkpoint_path(venue, year)
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            data: Dict[str, Any] = json.load(f)
            return data
    return None


def main(
    venue: Optional[str] = typer.Option(
        None, "--venue", help="Conference venue (e.g., neurips, icml)"
    ),
    year: Optional[int] = typer.Option(None, "--year", help="Publication year"),
    years: Optional[str] = typer.Option(
        None, "--years", help="Year range (e.g., 2020-2024) or list (2020,2022,2024)"
    ),
    venues: Optional[str] = typer.Option(
        None, "--venues", help="Multiple venues (comma-separated)"
    ),
    venue_file: Optional[Path] = typer.Option(
        None, "--venue-file", help="YAML file with venue specifications"
    ),
    max_papers: int = typer.Option(
        0, "--max-papers", help="Maximum papers per venue/year (0 = unlimited)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    resume: bool = typer.Option(False, "--resume", help="Resume from last checkpoint"),
    no_progress: bool = typer.Option(
        False, "--no-progress", help="Disable progress bars"
    ),
    parallel: int = typer.Option(
        1, "--parallel", help="Number of parallel workers (currently not implemented)"
    ),
    rate_limit: float = typer.Option(
        1.0, "--rate-limit", help="API rate limit (requests/second)"
    ),
    scraper: Optional[str] = typer.Option(
        None, "--scraper", help="Override default scraper (e.g., OpenReviewScraperV2)"
    ),
    list_venues: bool = typer.Option(
        False, "--list-venues", help="List available venues and their scrapers"
    ),
):
    """
    Collect research papers from various venues and years.

    Examples:

        # List available venues
        cf collect --list-venues

        # Collect single venue/year
        cf collect --venue neurips --year 2024

        # Collect with paper limit
        cf collect --venue icml --year 2023 --max-papers 100

        # Collect year range
        cf collect --venue iclr --years 2020-2024

        # Collect multiple venues
        cf collect --venues neurips,icml --year 2024

        # Resume interrupted collection
        cf collect --venue neurips --year 2024 --resume

        # Use new OpenReview scraper (with better decision extraction)
        cf collect --venue iclr --year 2024 --scraper OpenReviewScraperV2
    """

    # Handle --list-venues option
    if list_venues:
        registry = get_registry()

        # Get all venue mappings from registry
        venue_mappings = registry._venue_mapping

        # Group venues by scraper for better display
        scraper_venues: Dict[str, List[str]] = {}
        for venue, scraper_name in venue_mappings.items():
            if venue == "*":  # Skip the fallback entry
                continue
            if scraper_name not in scraper_venues:
                scraper_venues[scraper_name] = []
            scraper_venues[scraper_name].append(venue)

        # Sort venues within each scraper
        for scraper_name in scraper_venues:
            scraper_venues[scraper_name].sort()

        # Create table
        table = Table(title="Available Venues and Scrapers")
        table.add_column("Scraper", style="cyan", width=25)
        table.add_column("Supported Venues", style="green")
        table.add_column("Description", style="yellow")

        # Add scraper descriptions
        scraper_descriptions = {
            "NeurIPSScraper": "Neural Information Processing Systems",
            "IJCAIScraper": "International Joint Conference on AI",
            "ACLAnthologyScraper": "ACL Anthology (NLP conferences)",
            "MLRScraper": "PMLR venues (ICML, AISTATS, UAI)",
            "OpenReviewScraper": "OpenReview-hosted conferences (original)",
            "OpenReviewScraperV2": "OpenReview with improved decision extraction",
            "NaturePortfolioScraper": "Nature Portfolio journals via Crossref",
            "AAAIScraper": "AAAI proceedings via OAI-PMH protocol",
            "CVFScraper": "Computer Vision Foundation conferences",
            "PMLRScraper": "Proceedings of Machine Learning Research",
            "SemanticScholarScraper": "API-based fallback for other venues",
        }

        # Add rows to table
        for scraper_name in sorted(scraper_venues.keys()):
            venues_str = ", ".join(scraper_venues[scraper_name])
            description = scraper_descriptions.get(scraper_name, "")
            table.add_row(scraper_name, venues_str, description)

        console.print(table)
        console.print()
        console.print(
            "[cyan]Usage:[/cyan] cf collect --venue <venue_name> --year <year>"
        )
        console.print("[cyan]Example:[/cyan] cf collect --venue neurips --year 2023")
        console.print(
            "[cyan]Override scraper:[/cyan] cf collect --venue iclr --year 2024 --scraper OpenReviewScraperV2"
        )
        console.print()
        console.print(
            "[yellow]Note:[/yellow] OpenReviewScraperV2 provides improved decision extraction and filtering."
        )

        return

    # Parse venue/year specifications
    venue_years = {}

    if venue_file:
        venue_years = load_venue_file(venue_file)
    else:
        # Parse venues
        venue_list = []
        if venue:
            venue_list = [venue]
        elif venues:
            venue_list = [v.strip() for v in venues.split(",")]
        else:
            console.print(
                "[red]Error:[/red] Must specify --venue, --venues, or --venue-file"
            )
            raise typer.Exit(1)

        # Parse years
        year_list = []
        if year:
            year_list = [year]
        elif years:
            year_list = parse_years(years)
        else:
            # Default to current year
            year_list = [datetime.now().year]
            console.print(
                f"[yellow]No year specified, using current year: {year_list[0]}[/yellow]"
            )

        # Build venue_years dict
        for v in venue_list:
            venue_years[v] = year_list

    # Set default output path if not specified
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"data/collected_papers/papers_{timestamp}.json")

    # Configure scraping
    config = ScrapingConfig(
        rate_limit_delay=1.0 / rate_limit,
        batch_size=max_papers
        if max_papers > 0
        else 10000,  # Use large batch size for unlimited
        max_retries=3,
        timeout=30,
    )

    # Get registry
    registry = get_registry()

    # Collect papers
    all_papers = []
    errors = []

    # Show summary table
    table = Table(title="Collection Plan")
    table.add_column("Venue", style="cyan")
    table.add_column("Years", style="magenta")
    table.add_column("Scraper", style="green")

    for venue_name, venue_year_list in venue_years.items():
        if scraper:
            # Show overridden scraper
            scraper_name = scraper
            is_override = True
        else:
            # Show default scraper
            scraper_info = registry.get_scraper_for_venue_info(venue_name)
            scraper_name = scraper_info["scraper"]
            is_override = False

        display_name = scraper_name
        if is_override:
            display_name += " (override)"

        table.add_row(
            venue_name,
            ", ".join(str(y) for y in venue_year_list),
            display_name,
        )

    console.print(table)
    console.print()

    # Estimate total papers to collect
    console.print("[cyan]Estimating collection size...[/cyan]")
    total_papers_estimate = 0
    venue_estimates = {}

    for venue_name, venue_year_list in venue_years.items():
        # Get scraper for estimation - use override if provided
        if scraper:
            scraper_class = registry._scrapers.get(scraper)
            if scraper_class:
                estimate_scraper = scraper_class(config)  # type: ignore
                # estimate_scraper._original_venue = venue_name  # Not needed
            else:
                estimate_scraper = None
        else:
            estimate_scraper = registry.get_scraper_for_venue(venue_name, config)

        if estimate_scraper:
            for year in venue_year_list:
                estimate = estimate_scraper.estimate_paper_count(venue_name, year)
                if estimate:
                    # Apply max_papers limit to estimate (if limited)
                    if max_papers > 0:
                        estimate = min(estimate, max_papers)
                    venue_estimates[(venue_name, year)] = estimate
                    total_papers_estimate += estimate
                else:
                    # Default estimate if scraper doesn't provide one
                    default_estimate = (
                        max_papers if max_papers > 0 else 1000
                    )  # Default for unlimited
                    venue_estimates[(venue_name, year)] = default_estimate
                    total_papers_estimate += default_estimate

    # Collection progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn(
            "• {task.fields[papers_collected]}/{task.fields[papers_total]} papers"
        ),
        console=console,
        disable=no_progress,
    ) as progress:
        main_task = progress.add_task(
            "Collecting papers...",
            total=total_papers_estimate,
            papers_collected=0,
            papers_total=total_papers_estimate,
        )

        for venue_name, venue_year_list in venue_years.items():
            # Get scraper - use override if provided
            if scraper:
                # User provided specific scraper
                scraper_class = registry._scrapers.get(scraper)
                if scraper_class:
                    scraper_instance = scraper_class(config)  # type: ignore
                    # scraper_instance._original_venue = venue_name  # Not needed
                else:
                    console.print(
                        f"[red]Error:[/red] Unknown scraper {scraper}. "
                        f"Available scrapers: {', '.join(registry.get_available_scrapers())}"
                    )
                    errors.append(f"Unknown scraper {scraper}")
                    continue
            else:
                # Use default scraper for venue
                scraper_instance = registry.get_scraper_for_venue(venue_name, config)  # type: ignore

            if not scraper_instance:
                console.print(
                    f"[red]Error:[/red] No scraper available for venue {venue_name}"
                )
                errors.append(f"No scraper for {venue_name}")
                # Advance by estimated papers for this venue
                venue_estimate = sum(
                    venue_estimates.get((venue_name, y), 0) for y in venue_year_list
                )
                progress.advance(main_task, venue_estimate)
                continue

            for year in venue_year_list:
                task_desc = f"Collecting {venue_name} {year}"
                expected_papers = venue_estimates.get((venue_name, year), max_papers)
                progress.update(main_task, description=task_desc)

                # Check for checkpoint if resuming
                if resume:
                    checkpoint = load_checkpoint(venue_name, year)
                    if checkpoint and checkpoint.get("completed"):
                        console.print(
                            f"[yellow]Skipping {venue_name} {year} (already completed)[/yellow]"
                        )
                        progress.advance(main_task, expected_papers)
                        papers_collected = (
                            progress.tasks[main_task].fields["papers_collected"]
                            + expected_papers
                        )
                        progress.update(main_task, papers_collected=papers_collected)
                        continue

                try:
                    # Scrape papers
                    result = scraper_instance.scrape_venue_year(venue_name, year)

                    if result.success:
                        papers = result.metadata.get("papers", [])
                        collected = papers if max_papers == 0 else papers[:max_papers]
                        all_papers.extend(collected)

                        # Save checkpoint
                        save_checkpoint(venue_name, year, collected, completed=True)

                        console.print(
                            f"[green]✓[/green] Collected {len(collected)} papers "
                            f"from {venue_name} {year}"
                        )

                        # Update progress
                        if max_papers == 0:
                            # For unlimited collection, update total estimate as we discover actual counts
                            actual_diff = len(collected) - expected_papers
                            if actual_diff != 0:
                                # Adjust total and advance appropriately
                                current_total = progress.tasks[main_task].total or 0
                                new_total = max(
                                    current_total + actual_diff,
                                    len(collected),
                                )
                                progress.update(main_task, total=new_total)
                            progress.advance(main_task, len(collected))
                        else:
                            # For limited collection, stick to estimates
                            progress.advance(main_task, len(collected))
                            if len(collected) < expected_papers:
                                progress.advance(
                                    main_task, expected_papers - len(collected)
                                )

                        papers_collected = progress.tasks[main_task].fields[
                            "papers_collected"
                        ] + len(collected)
                        progress.update(main_task, papers_collected=papers_collected)
                    else:
                        errors.extend(result.errors)
                        console.print(
                            f"[red]✗[/red] Failed to collect {venue_name} {year}: "
                            f"{', '.join(result.errors)}"
                        )
                        # Still advance progress by expected amount on failure
                        progress.advance(main_task, expected_papers)

                except Exception as e:
                    error_msg = f"Exception collecting {venue_name} {year}: {str(e)}"
                    errors.append(error_msg)
                    console.print(f"[red]✗[/red] {error_msg}")
                    # Still advance progress by expected amount on exception
                    progress.advance(main_task, expected_papers)

    # Save results
    if all_papers:
        save_papers(all_papers, output, {"errors": errors})

        # Show summary
        console.print("\n[bold]Collection Summary:[/bold]")
        console.print(f"Total papers collected: {len(all_papers)}")
        console.print(f"Venues: {', '.join(sorted(set(p.venue for p in all_papers)))}")
        console.print(
            f"Years: {', '.join(str(y) for y in sorted(set(p.year for p in all_papers)))}"
        )

        if errors:
            console.print(f"\n[yellow]Warnings/Errors ({len(errors)}):[/yellow]")
            for error in errors[:5]:  # Show first 5 errors
                console.print(f"  - {error}")
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more")
    else:
        console.print("[red]No papers collected![/red]")
        raise typer.Exit(1)
