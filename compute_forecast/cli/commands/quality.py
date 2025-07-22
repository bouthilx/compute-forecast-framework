"""Quality check command for compute-forecast."""

import typer
import json
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console

from compute_forecast.quality.core.runner import QualityRunner
from compute_forecast.quality.core.interfaces import QualityConfig, QualityReport
from compute_forecast.quality.core.registry import get_registry
from compute_forecast.quality.core.formatters import format_report, save_report


console = Console()


def main(
    data_path: Optional[Path] = typer.Argument(
        None, help="Path to data file or directory to check"
    ),
    stage: Optional[str] = typer.Option(
        None,
        "--stage",
        "-s",
        help="Specific stage to check (e.g., collection, consolidation)",
    ),
    all_stages: bool = typer.Option(
        False, "--all", "-a", help="Run quality checks for all applicable stages"
    ),
    output_format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json, markdown"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path (defaults to stdout)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed quality issues"
    ),
    skip_checks: Optional[str] = typer.Option(
        None, "--skip-checks", help="Comma-separated list of checks to skip"
    ),
    list_stages: bool = typer.Option(
        False, "--list-stages", help="List available stages and exit"
    ),
    list_checks: Optional[str] = typer.Option(
        None, "--list-checks", help="List available checks for a stage and exit"
    ),
    # Custom threshold options
    min_completeness: Optional[float] = typer.Option(
        None, "--min-completeness", help="Minimum completeness score (0.0-1.0)"
    ),
    min_coverage: Optional[float] = typer.Option(
        None, "--min-coverage", help="Minimum coverage score (0.0-1.0)"
    ),
    min_accuracy: Optional[float] = typer.Option(
        None, "--min-accuracy", help="Minimum accuracy score (0.0-1.0)"
    ),
    min_consistency: Optional[float] = typer.Option(
        None, "--min-consistency", help="Minimum consistency score (0.0-1.0)"
    ),
    min_overall: Optional[float] = typer.Option(
        None, "--min-overall", help="Minimum overall quality score (0.0-1.0)"
    ),
    fail_on_critical: bool = typer.Option(
        True,
        "--fail-on-critical/--no-fail-on-critical",
        help="Exit with error code if critical issues found",
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
            console.print(
                f"[red]No quality checker found for stage: {list_checks}[/red]"
            )
        raise typer.Exit()

    # Validate arguments
    if not data_path:
        console.print(
            "[red]Error: DATA_PATH is required unless using --list-stages or --list-checks[/red]"
        )
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

    # Build custom thresholds
    thresholds = {}
    if min_completeness is not None:
        thresholds["completeness"] = min_completeness
    if min_coverage is not None:
        thresholds["coverage"] = min_coverage
    if min_accuracy is not None:
        thresholds["accuracy"] = min_accuracy
    if min_consistency is not None:
        thresholds["consistency"] = min_consistency
    if min_overall is not None:
        thresholds["overall"] = min_overall

    # Prepare configuration
    config = QualityConfig(
        stage=stage or "all",
        thresholds=thresholds,
        skip_checks=skip_checks_list,
        output_format=output_format,
        verbose=verbose,
    )

    # Run quality checks
    runner = QualityRunner()

    try:
        if all_stages:
            reports = runner.run_all_applicable_checks(data_path, config)
            if not reports:
                console.print(
                    "[yellow]No applicable quality checks found for the data.[/yellow]"
                )
                raise typer.Exit()
            # For now, just show first report (will enhance in later phases)
            report = reports[0]
        else:
            if stage is None:
                console.print("[red]Error: Stage must be specified[/red]")
                raise typer.Exit(1)
            report = runner.run_checks(stage, data_path, config)

        # Handle output formatting and saving
        if all_stages:
            _handle_multi_stage_output(reports, output_format, output_file, verbose)
        else:
            _handle_single_stage_output(report, output_format, output_file, verbose)

        # Check for critical issues and exit code
        has_critical = (
            any(r.has_critical_issues() for r in reports)
            if all_stages
            else report.has_critical_issues()
        )
        if has_critical and fail_on_critical:
            console.print("\n[red]Quality check failed due to critical issues[/red]")
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def _handle_single_stage_output(
    report: QualityReport,
    output_format: str,
    output_file: Optional[Path],
    verbose: bool,
):
    """Handle output for a single stage report."""
    try:
        formatted = format_report(report, output_format, verbose=verbose)

        if output_file:
            save_report(report, output_file, output_format, verbose=verbose)
            console.print(f"[green]Report saved to: {output_file}[/green]")
        else:
            # For JSON format, print without adding extra newline
            if output_format == "json":
                print(formatted, end="")
            else:
                console.print(formatted)
    except ValueError as e:
        console.print(f"[red]Formatting error: {e}[/red]")
        # Fall back to basic text output
        console.print("\n[yellow]Falling back to basic text format[/yellow]")
        _print_basic_report(report, verbose)


def _handle_multi_stage_output(
    reports: list, output_format: str, output_file: Optional[Path], verbose: bool
):
    """Handle output for multiple stage reports."""
    if output_format == "json":
        # Combine all reports into a single JSON
        combined_data: Dict[str, Any] = {"reports": []}
        for report in reports:
            try:
                formatted = format_report(report, "json", verbose=verbose)
                report_data = json.loads(formatted)
                combined_data["reports"].append(report_data)
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to format {report.stage} report: {e}[/yellow]"
                )

        output = json.dumps(combined_data, indent=2)
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Combined report saved to: {output_file}[/green]")
        else:
            console.print(output)

    elif output_format == "markdown":
        # Combine all reports into a single Markdown document
        lines = ["# Quality Check Report - All Stages", ""]

        for report in reports:
            try:
                formatted = format_report(report, "markdown", verbose=verbose)
                lines.append(formatted)
                lines.append("")
                lines.append("---")
                lines.append("")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to format {report.stage} report: {e}[/yellow]"
                )

        output = "\n".join(lines)
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Combined report saved to: {output_file}[/green]")
        else:
            console.print(output)

    else:  # text format
        # Output each report separately
        outputs = []
        for report in reports:
            try:
                formatted = format_report(report, output_format, verbose=verbose)
                outputs.append(formatted)
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to format {report.stage} report: {e}[/yellow]"
                )
                # Fall back to basic format
                basic = _get_basic_report_text(report, verbose)
                outputs.append(basic)

        output = "\n\n".join(outputs)
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Combined report saved to: {output_file}[/green]")
        else:
            console.print(output)


def _print_basic_report(report: QualityReport, verbose: bool):
    """Print basic text report as fallback."""
    console.print(_get_basic_report_text(report, verbose))


def _get_basic_report_text(report: QualityReport, verbose: bool) -> str:
    """Get basic text report as fallback."""
    lines = []
    lines.append(f"\nQuality Report: {report.stage.title()} Stage")
    lines.append("=" * 50)
    lines.append(f"Data: {report.data_path}")
    lines.append(f"Overall Score: {report.overall_score:.2f}")
    lines.append(f"Critical Issues: {len(report.critical_issues)}")
    lines.append(f"Warnings: {len(report.warnings)}")

    if verbose:
        lines.append("\nCheck Results:")
        for result in report.check_results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"  {result.check_name}: {result.score:.2f} [{status}]")

    return "\n".join(lines)
