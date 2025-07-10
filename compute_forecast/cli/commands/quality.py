"""Quality check command for compute-forecast."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console

from compute_forecast.quality.core.runner import QualityRunner
from compute_forecast.quality.core.interfaces import QualityConfig
from compute_forecast.quality.core.registry import get_registry


console = Console()


def main(
    data_path: Optional[Path] = typer.Argument(
        None,
        help="Path to data file or directory to check"
    ),
    stage: Optional[str] = typer.Option(
        None,
        "--stage", "-s",
        help="Specific stage to check (e.g., collection, consolidation)"
    ),
    all_stages: bool = typer.Option(
        False,
        "--all", "-a",
        help="Run quality checks for all applicable stages"
    ),
    output_format: str = typer.Option(
        "text",
        "--format", "-f",
        help="Output format: text, json, markdown"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (defaults to stdout)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed quality issues"
    ),
    skip_checks: Optional[str] = typer.Option(
        None,
        "--skip-checks",
        help="Comma-separated list of checks to skip"
    ),
    list_stages: bool = typer.Option(
        False,
        "--list-stages",
        help="List available stages and exit"
    ),
    list_checks: Optional[str] = typer.Option(
        None,
        "--list-checks",
        help="List available checks for a stage and exit"
    ),
):
    """Run quality checks on compute-forecast data."""
    
    registry = get_registry()
    
    # Handle listing options
    if list_stages:
        console.print("\nAvailable quality check stages:")
        for stage in registry.list_stages():
            console.print(f"  - {stage}")
        raise typer.Exit()
    
    if list_checks:
        checks = registry.list_checks_for_stage(list_checks)
        if checks:
            console.print(f"\nAvailable checks for stage '{list_checks}':")
            for check in checks:
                console.print(f"  - {check}")
        else:
            console.print(f"[red]No quality checker found for stage: {list_checks}[/red]")
        raise typer.Exit()
    
    # Validate arguments
    if not data_path:
        console.print("[red]Error: DATA_PATH is required unless using --list-stages or --list-checks[/red]")
        raise typer.Exit(1)
        
    if not all_stages and not stage:
        console.print("[red]Error: Must specify either --stage or --all[/red]")
        raise typer.Exit(1)
    
    if not data_path.exists():
        console.print(f"[red]Error: Data path does not exist: {data_path}[/red]")
        raise typer.Exit(1)
    
    # Parse skip checks
    skip_checks_list = []
    if skip_checks:
        skip_checks_list = [s.strip() for s in skip_checks.split(",")]
    
    # Prepare configuration
    config = QualityConfig(
        stage=stage or "all",
        thresholds={},  # Will use defaults
        skip_checks=skip_checks_list,
        output_format=output_format,
        verbose=verbose
    )
    
    # Run quality checks
    runner = QualityRunner()
    
    try:
        if all_stages:
            reports = runner.run_all_applicable_checks(data_path, config)
            if not reports:
                console.print("[yellow]No applicable quality checks found for the data.[/yellow]")
                raise typer.Exit()
            # For now, just show first report (will enhance in later phases)
            report = reports[0]
        else:
            report = runner.run_checks(stage, data_path, config)
        
        # Output results (basic text format for now)
        if output_format == "text":
            _print_text_report(report, verbose)
        else:
            console.print(f"[yellow]Format '{output_format}' not yet implemented[/yellow]")
            
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def _print_text_report(report, verbose: bool):
    """Print basic text report (placeholder for Phase 1)."""
    console.print(f"\nQuality Report: {report.stage.title()} Stage")
    console.print("=" * 50)
    console.print(f"Data: {report.data_path}")
    console.print(f"Overall Score: {report.overall_score:.2f}")
    console.print(f"Critical Issues: {len(report.critical_issues)}")
    console.print(f"Warnings: {len(report.warnings)}")
    console.print("\n[yellow]Detailed reporting will be implemented in Phase 4[/yellow]")