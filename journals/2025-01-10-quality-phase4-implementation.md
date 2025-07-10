# Quality Command Phase 4: CLI & Reporting Implementation Plan

**Date**: 2025-01-10  
**Time**: 20:00  
**Task**: Detailed implementation plan for Phase 4 - CLI & Reporting (3 hours)

## Phase 4 Overview

Based on the design document, Phase 4 focuses on **CLI & Reporting** - completing the CLI command with all options, implementing formatters, creating report templates, and adding progress tracking.

**Estimated Time**: 3 hours  
**Scope**: Complete CLI functionality, multi-format reporting, progress indicators

## Current State Analysis

### Already Implemented ✅

1. **Basic CLI Command Structure** (`compute_forecast/cli/commands/quality.py`)
   - Command with basic arguments (data_path, stage, all_stages)
   - --list-stages and --list-checks functionality
   - --skip-checks parsing
   - Basic error handling and validation
   - Placeholder text report output

2. **Collection Stage Formatters** (`compute_forecast/quality/stages/collection/formatters.py`)
   - TextReportFormatter - Human-readable text format
   - JSONReportFormatter - Machine-readable JSON format
   - MarkdownReportFormatter - Documentation-friendly markdown
   - All formatters use CollectionQualityMetrics

### What's Missing ⚠️

1. **CLI Command Enhancements**
   - Custom threshold options (--min-coverage, --min-completeness, etc.)
   - Output file handling (--output flag)
   - **CRITICAL: Formatters exist but are NOT being used!**
   - The CLI shows placeholder text instead of rich formatted output
   - Multi-stage report handling for --all

2. **Hook Output Enhancement**
   - Post-collect hook shows minimal panel instead of detailed report
   - Should show the rich output format from the design

3. **Progress Tracking**
   - No progress indicators during quality checks
   - No feedback for long-running operations

4. **Report Integration**
   - Generic report formatter for all stages (not just collection)
   - Unified report generation across stages

## Phase 4 Implementation Tasks

### Task 1: Connect Existing Formatters and Complete CLI Options (60 minutes)

**File**: `compute_forecast/cli/commands/quality.py` (modifications)

The most critical issue is that the formatters exist but aren't being used! We need to connect them and add missing CLI options:

```python
# Add imports
from compute_forecast.quality.core.config import create_quality_config
from compute_forecast.quality.reports.formatter import ReportFormatterFactory

# Add threshold options to main()
def main(
    # ... existing parameters ...
    min_completeness: Optional[float] = typer.Option(
        None,
        "--min-completeness",
        help="Minimum completeness threshold (0.0-1.0)"
    ),
    min_coverage: Optional[float] = typer.Option(
        None,
        "--min-coverage", 
        help="Minimum coverage threshold (0.0-1.0)"
    ),
    min_consistency: Optional[float] = typer.Option(
        None,
        "--min-consistency",
        help="Minimum consistency threshold (0.0-1.0)"
    ),
    min_accuracy: Optional[float] = typer.Option(
        None,
        "--min-accuracy",
        help="Minimum accuracy threshold (0.0-1.0)"
    ),
):
    """Run quality checks on compute-forecast data."""
    
    # ... existing validation logic ...
    
    # Build custom thresholds
    custom_thresholds = {}
    if min_completeness is not None:
        custom_thresholds["min_completeness"] = min_completeness
    if min_coverage is not None:
        custom_thresholds["min_coverage"] = min_coverage
    if min_consistency is not None:
        custom_thresholds["min_consistency"] = min_consistency
    if min_accuracy is not None:
        custom_thresholds["min_accuracy"] = min_accuracy
    
    # Use create_quality_config instead of manual construction
    config = create_quality_config(
        stage=stage or "all",
        thresholds=custom_thresholds,
        skip_checks=skip_checks_list,
        output_format=output_format,
        verbose=verbose
    )
    
    # ... run quality checks ...
    
    # Format and output results using EXISTING formatters!
    if all_stages:
        # Handle multiple reports
        _print_multi_stage_reports(reports, output_format, output_file, verbose)
    else:
        # Single stage - use the stage-specific formatter
        _print_single_report(report, output_format, output_file, verbose)


def _print_single_report(report: QualityReport, output_format: str, output_file: Optional[Path], verbose: bool):
    """Print a single quality report using the appropriate formatter."""
    # For collection stage, we have rich formatters already!
    if report.stage == "collection":
        # Get the metrics from the report
        from compute_forecast.quality.stages.collection import (
            TextReportFormatter, 
            JSONReportFormatter, 
            MarkdownReportFormatter,
            CollectionQualityMetrics
        )
        
        # Extract metrics from check results
        metrics = _extract_collection_metrics(report)
        
        # Select formatter
        if output_format == "json":
            formatter = JSONReportFormatter()
        elif output_format == "markdown":
            formatter = MarkdownReportFormatter()
        else:
            formatter = TextReportFormatter()
        
        # Format the report
        formatted_output = formatter.format_report(report, metrics)
        
    else:
        # For other stages, use generic formatter (to be implemented)
        formatted_output = _format_generic_report(report, output_format, verbose)
    
    # Output
    if output_file:
        output_file.write_text(formatted_output)
        console.print(f"[green]✓[/green] Report saved to {output_file}")
    else:
        console.print(formatted_output)


def _extract_collection_metrics(report: QualityReport) -> CollectionQualityMetrics:
    """Extract collection metrics from the report's check results."""
    # The metrics should be available in the check results
    # This bridges the gap between the report structure and formatter expectations
    for check_result in report.check_results:
        if hasattr(check_result, 'metrics') and 'collection_metrics' in check_result.metrics:
            return check_result.metrics['collection_metrics']
    
    # Fallback: create basic metrics from report data
    return CollectionQualityMetrics(
        total_papers_collected=report.check_results[0].metrics.get('total_papers', 0),
        # ... extract other metrics from check results
    )
```

### Task 2: Create Unified Report Formatter System (60 minutes)

**File**: `compute_forecast/quality/reports/formatter.py`

Create a factory system that can handle reports from any stage:

```python
"""Unified report formatting system for all quality stages."""

from typing import List, Dict, Any, Protocol
from pathlib import Path

from compute_forecast.quality.core.interfaces import QualityReport
from compute_forecast.quality.stages.collection.formatters import (
    TextReportFormatter as CollectionTextFormatter,
    JSONReportFormatter as CollectionJSONFormatter,
    MarkdownReportFormatter as CollectionMarkdownFormatter,
)


class StageFormatter(Protocol):
    """Protocol for stage-specific formatters."""
    
    def format_report(self, report: QualityReport, context: Dict[str, Any]) -> str:
        """Format a quality report for output."""
        ...


class GenericTextFormatter:
    """Generic text formatter for stages without specific formatters."""
    
    def format_report(self, report: QualityReport, context: Dict[str, Any]) -> str:
        """Format report as generic text."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append(f"{report.stage.upper()} QUALITY REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Data Path: {report.data_path}")
        lines.append("")
        
        # Overall Score
        grade = self._score_to_grade(report.overall_score)
        lines.append(f"OVERALL QUALITY SCORE: {report.overall_score:.2f} ({grade})")
        lines.append("")
        
        # Check Results
        lines.append("QUALITY CHECKS:")
        lines.append("-" * 30)
        
        for result in report.check_results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            lines.append(f"{result.check_name:<25} {result.score:.2f} {status}")
        
        # Issues Summary
        if report.critical_issues:
            lines.append(f"\n[!] {len(report.critical_issues)} CRITICAL ISSUES")
        if report.warnings:
            lines.append(f"[!] {len(report.warnings)} WARNINGS")
        
        return "\n".join(lines)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.97: return "A+"
        elif score >= 0.93: return "A"
        elif score >= 0.90: return "A-"
        elif score >= 0.87: return "B+"
        elif score >= 0.83: return "B"
        elif score >= 0.80: return "B-"
        elif score >= 0.77: return "C+"
        elif score >= 0.73: return "C"
        elif score >= 0.70: return "C-"
        elif score >= 0.67: return "D+"
        elif score >= 0.63: return "D"
        elif score >= 0.60: return "D-"
        else: return "F"


class ReportFormatterFactory:
    """Factory for creating appropriate formatters."""
    
    def __init__(self):
        # Registry of stage-specific formatters
        self._formatters = {
            "collection": {
                "text": CollectionTextFormatter,
                "json": CollectionJSONFormatter,
                "markdown": CollectionMarkdownFormatter,
            }
            # Future stages will be added here
        }
        
        # Generic formatters for unknown stages
        self._generic_formatters = {
            "text": GenericTextFormatter,
            "json": GenericJSONFormatter,
            "markdown": GenericMarkdownFormatter,
        }
    
    def format_reports(
        self, 
        reports: List[QualityReport], 
        output_format: str = "text",
        verbose: bool = False
    ) -> str:
        """Format multiple quality reports."""
        if not reports:
            return "No quality reports to display."
        
        if len(reports) == 1:
            return self._format_single_report(reports[0], output_format, verbose)
        
        # Multi-report formatting
        if output_format == "json":
            return self._format_multi_json(reports)
        elif output_format == "markdown":
            return self._format_multi_markdown(reports, verbose)
        else:
            return self._format_multi_text(reports, verbose)
    
    def _format_single_report(
        self, 
        report: QualityReport, 
        output_format: str,
        verbose: bool
    ) -> str:
        """Format a single quality report."""
        # Get appropriate formatter
        formatter_class = self._get_formatter(report.stage, output_format)
        formatter = formatter_class()
        
        # Get stage-specific context if available
        context = self._get_stage_context(report)
        
        # Format report
        return formatter.format_report(report, context)
```

### Task 3: Enhance Hook Output (30 minutes)

**File**: `compute_forecast/quality/core/hooks.py` (modifications)

Update the post-command hook to show detailed output like in the design:

```python
def _show_quality_summary(report: QualityReport, context: Optional[Dict[str, Any]] = None):
    """Show a detailed quality summary in the console."""
    # Instead of just a minimal panel, show the rich formatted output
    
    if report.stage == "collection":
        from compute_forecast.quality.stages.collection import TextReportFormatter
        from ..stages.collection.checker import CollectionQualityChecker
        
        # Get metrics from the checker or report
        metrics = _extract_metrics_from_report(report)
        
        # Use the text formatter to create rich output
        formatter = TextReportFormatter()
        formatted_report = formatter.format_report(report, metrics)
        
        # Print the detailed report
        console.print("\n" + formatted_report)
        
        # Optionally add a summary panel for critical issues
        if report.has_critical_issues():
            console.print("\n[red]⚠️  Critical quality issues detected![/red]")
            console.print(f"Run [cyan]cf quality --stage {report.stage} --verbose {report.data_path}[/cyan] for full details.")
    else:
        # Fallback to current minimal summary for other stages
        _show_minimal_summary(report, context)
```

This ensures that when quality checks run after `collect`, users see the rich, detailed output shown in the design document, not just a minimal score panel.

### Task 4: Add Progress Tracking (30 minutes)

**File**: `compute_forecast/quality/core/progress.py`

Create progress tracking utilities:

```python
"""Progress tracking for quality checks."""

from typing import Optional
from contextlib import contextmanager
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console


class QualityCheckProgress:
    """Progress tracker for quality checks."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._progress = None
        self._task_id = None
    
    @contextmanager
    def track_checks(self, total_checks: int, description: str = "Running quality checks"):
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
                self._task_id, 
                description=f"Running {check_name}...",
                advance=advance
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
                progress.update(task, description=f"✓ {stage_name} quality check complete")
```

**Integration in Runner**:

```python
# In quality/core/runner.py, add progress tracking

from .progress import QualityCheckProgress

class QualityRunner:
    def run_checks(self, stage: str, data_path: Path, config: QualityConfig) -> QualityReport:
        """Run quality checks for a specific stage with progress tracking."""
        # ... existing validation ...
        
        # Get checker
        checker = self.registry.get_checker(stage)
        
        # Run with progress tracking if not verbose
        if not config.verbose:
            progress = QualityCheckProgress()
            with progress.track_stage(stage):
                return checker.check(data_path, config)
        else:
            return checker.check(data_path, config)
```

### Task 5: Integration and Testing (30 minutes)

**File**: `tests/integration/quality/test_cli_reporting.py`

Create integration tests for CLI and reporting:

```python
"""Integration tests for CLI command and reporting functionality."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from typer.testing import CliRunner
import json

from compute_forecast.cli.main import app


class TestCLIReporting:
    """Test CLI command with reporting features."""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_cli_with_custom_thresholds(self, sample_collection_data):
        """Test CLI with custom threshold options."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--min-completeness", "0.95",
                "--min-coverage", "0.85",
                "--verbose"
            ])
            
            assert result.exit_code == 0
            assert "COLLECTION QUALITY REPORT" in result.output
            assert "min_completeness: 0.95" in result.output  # Should show custom threshold
    
    def test_cli_output_formats(self, sample_collection_data):
        """Test different output formats."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            # Test JSON format
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "json"
            ])
            
            assert result.exit_code == 0
            # Should be valid JSON
            output_data = json.loads(result.output)
            assert "overall_score" in output_data
            
            # Test Markdown format
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "markdown"
            ])
            
            assert result.exit_code == 0
            assert "# Collection Quality Report" in result.output
            assert "## Overall Score" in result.output
    
    def test_cli_output_to_file(self, sample_collection_data):
        """Test output to file functionality."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            output_file = Path(tmp_dir) / "report.md"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "markdown",
                "--output", str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Report saved to" in result.output
            
            # Verify file content
            content = output_file.read_text()
            assert "# Collection Quality Report" in content
    
    def test_cli_progress_tracking(self, sample_collection_data):
        """Test progress tracking displays correctly."""
        # Progress tracking is harder to test in CLI
        # We mainly verify it doesn't break the command
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection"
            ])
            
            assert result.exit_code == 0
            # Progress indicators should not appear in non-TTY output
```

## Testing Plan

### Manual Testing Commands

```bash
# Test custom thresholds
cf quality --stage collection --min-completeness 0.95 --min-coverage 0.85 data/papers.json

# Test output formats
cf quality --stage collection --format json data/papers.json
cf quality --stage collection --format markdown data/papers.json

# Test output to file
cf quality --stage collection --format markdown --output report.md data/papers.json

# Test progress tracking (should show spinner/progress bar)
cf quality --stage collection data/large_collection.json

# Test multi-stage with --all
cf quality --all --verbose data/

# Test combined options
cf quality --stage collection --min-completeness 0.9 --skip-checks url_validation --format json --output results.json data/papers.json
```

## Success Criteria

### Phase 4 Complete When:

1. **✅ CLI Command Fully Functional**
   - All threshold options working (--min-completeness, etc.)
   - Output file handling implemented
   - All output formats functional (text, json, markdown)
   - Multi-stage reporting with --all

2. **✅ Report Formatting System**
   - Unified formatter factory
   - Stage-specific formatters integrated
   - Generic formatters for future stages
   - Consistent formatting across all outputs

3. **✅ Progress Tracking**
   - Progress indicators during quality checks
   - Stage-level progress tracking
   - Graceful handling in non-TTY environments

4. **✅ Integration Tests**
   - CLI command tests with all options
   - Output format validation
   - File output testing
   - Progress tracking verification

## Risk Mitigation

1. **Output Format Complexity**: Keep formatters simple and focused
2. **Progress Display Issues**: Use Rich library's built-in TTY detection
3. **Multi-stage Complexity**: Start with single-stage, extend to multi-stage
4. **Performance with Large Data**: Progress tracking helps user experience

## Files Created/Modified

### New Files:
- `compute_forecast/quality/reports/formatter.py` - Unified formatting system
- `compute_forecast/quality/core/progress.py` - Progress tracking utilities
- `tests/integration/quality/test_cli_reporting.py` - CLI integration tests

### Modified Files:
- `compute_forecast/cli/commands/quality.py` - Add threshold options and formatter integration
- `compute_forecast/quality/core/runner.py` - Add progress tracking integration

## Time Estimate: 3 hours

**CRITICAL NOTE**: The main issue is that the formatters were already implemented in Phase 2 but are not being used! Phase 4's primary goal is to connect these existing formatters to both the CLI command and the post-collect hook to produce the rich, detailed output shown in the design document's examples.

Without this phase:
- Users see "Detailed reporting will be implemented in Phase 4" placeholder text
- The post-collect hook shows only a minimal panel with score and issue counts
- The rich formatters (TextReportFormatter, JSONReportFormatter, MarkdownReportFormatter) remain unused

This plan ensures the quality command produces the detailed, actionable output described in the design document.