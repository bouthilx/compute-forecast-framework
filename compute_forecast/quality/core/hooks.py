"""Integration hooks for post-command quality checks."""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel

from .runner import QualityRunner
from .interfaces import QualityReport, QualityConfig


console = Console()


def run_post_command_quality_check(
    stage: str,
    output_path: Path,
    context: Optional[Dict[str, Any]] = None,
    config: Optional[QualityConfig] = None,
    show_summary: bool = True
) -> Optional[QualityReport]:
    """Run quality checks after a command completes.
    
    Args:
        stage: The pipeline stage that just completed
        output_path: Path to the output data
        context: Additional context from the command
        config: Optional quality configuration
        show_summary: Whether to show a summary in console
    
    Returns:
        QualityReport if checks were run, None if skipped
    """
    try:
        runner = QualityRunner()
        
        # Use provided config or get defaults
        if config is None:
            config = runner._get_default_config(stage)
            config.verbose = False  # Keep integrated checks concise
        
        # Run the quality checks
        report = runner.run_checks(stage, output_path, config)
        
        if show_summary:
            _show_quality_summary(report, context)
        
        # Handle critical issues
        if report.has_critical_issues():
            console.print("\n[red]⚠️  Critical quality issues detected![/red]")
            console.print("Run [cyan]cf quality --stage collection --verbose[/cyan] for details.")
            # Don't fail the command, just warn
        
        return report
        
    except Exception as e:
        # Don't fail the main command if quality checks fail
        console.print(f"\n[yellow]Warning: Quality checks failed: {e}[/yellow]")
        return None


def _show_quality_summary(report: QualityReport, context: Optional[Dict[str, Any]] = None):
    """Show a concise quality summary in the console."""
    # Determine overall quality grade
    grade = _score_to_grade(report.overall_score)
    grade_color = _grade_to_color(grade)
    
    # Build summary text
    summary_lines = [
        f"Quality Score: [bold {grade_color}]{report.overall_score:.2f} ({grade})[/bold {grade_color}]"
    ]
    
    # Add key metrics from context
    if context:
        if 'total_papers' in context:
            summary_lines.append(f"Papers Collected: {context['total_papers']}")
    
    # Add issue counts
    critical_count = len(report.critical_issues)
    warning_count = len(report.warnings)
    
    if critical_count > 0:
        summary_lines.append(f"[red]Critical Issues: {critical_count}[/red]")
    if warning_count > 0:
        summary_lines.append(f"[yellow]Warnings: {warning_count}[/yellow]")
    
    # Show summary panel
    panel = Panel(
        "\n".join(summary_lines),
        title="✓ Quality Check Summary",
        border_style="green" if critical_count == 0 else "red"
    )
    console.print(panel)


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 0.97:
        return "A+"
    elif score >= 0.93:
        return "A"
    elif score >= 0.90:
        return "A-"
    elif score >= 0.87:
        return "B+"
    elif score >= 0.83:
        return "B"
    elif score >= 0.80:
        return "B-"
    elif score >= 0.77:
        return "C+"
    elif score >= 0.73:
        return "C"
    elif score >= 0.70:
        return "C-"
    elif score >= 0.67:
        return "D+"
    elif score >= 0.63:
        return "D"
    elif score >= 0.60:
        return "D-"
    else:
        return "F"


def _grade_to_color(grade: str) -> str:
    """Get color for grade display."""
    if grade.startswith("A"):
        return "green"
    elif grade.startswith("B"):
        return "cyan"
    elif grade.startswith("C"):
        return "yellow"
    elif grade.startswith("D"):
        return "magenta"
    else:
        return "red"