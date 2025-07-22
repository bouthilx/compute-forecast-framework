# Quality Command Phase 1: Core Infrastructure Implementation

**Date**: 2025-01-10
**Time**: 15:00
**Task**: Detailed implementation plan for Phase 1 of quality command (Core Infrastructure)

## Phase 1 Overview

Build the foundational infrastructure for the quality checking system, including base interfaces, data structures, stage registry, and basic CLI command setup. This phase establishes the architectural patterns that all future quality checks will follow.

## Implementation Tasks

### 1. Core Data Structures (45 minutes)

**File**: `compute_forecast/quality/core/interfaces.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path

# Reuse from existing quality_control.py
class QualityCheckType(Enum):
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    COVERAGE = "coverage"  # New for collection

class QualityIssueLevel(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class QualityIssue:
    check_type: QualityCheckType
    level: QualityIssueLevel
    field: Optional[str]
    message: str
    suggested_action: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityCheckResult:
    check_name: str
    check_type: QualityCheckType
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityReport:
    stage: str
    timestamp: datetime
    data_path: Path
    overall_score: float
    check_results: List[QualityCheckResult]

    @property
    def critical_issues(self) -> List[QualityIssue]:
        return [issue for result in self.check_results
                for issue in result.issues
                if issue.level == QualityIssueLevel.CRITICAL]

    @property
    def warnings(self) -> List[QualityIssue]:
        return [issue for result in self.check_results
                for issue in result.issues
                if issue.level == QualityIssueLevel.WARNING]

    def has_critical_issues(self) -> bool:
        return len(self.critical_issues) > 0

    def get_score_by_type(self, check_type: QualityCheckType) -> float:
        results = [r for r in self.check_results if r.check_type == check_type]
        return sum(r.score for r in results) / len(results) if results else 0.0

@dataclass
class QualityConfig:
    stage: str
    thresholds: Dict[str, float] = field(default_factory=dict)
    skip_checks: List[str] = field(default_factory=list)
    output_format: str = "text"
    verbose: bool = False
    custom_params: Dict[str, Any] = field(default_factory=dict)
```

### 2. Stage Checker Interface (30 minutes)

**File**: `compute_forecast/quality/stages/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any, List, Dict
from pathlib import Path
from ..core.interfaces import QualityReport, QualityConfig, QualityCheckResult

class StageQualityChecker(ABC):
    """Base class for stage-specific quality checkers."""

    def __init__(self):
        self._checks = self._register_checks()

    @abstractmethod
    def get_stage_name(self) -> str:
        """Return the stage name this checker handles."""
        pass

    @abstractmethod
    def load_data(self, data_path: Path) -> Any:
        """Load and parse data for this stage."""
        pass

    @abstractmethod
    def _register_checks(self) -> Dict[str, callable]:
        """Register all quality checks for this stage.

        Returns:
            Dict mapping check names to check methods
        """
        pass

    def check(self, data_path: Path, config: QualityConfig) -> QualityReport:
        """Run all quality checks for this stage."""
        # Load data
        data = self.load_data(data_path)

        # Run checks
        results = []
        for check_name, check_func in self._checks.items():
            if check_name not in config.skip_checks:
                result = check_func(data, config)
                results.append(result)

        # Calculate overall score
        overall_score = sum(r.score for r in results) / len(results) if results else 0.0

        return QualityReport(
            stage=self.get_stage_name(),
            timestamp=datetime.now(),
            data_path=data_path,
            overall_score=overall_score,
            check_results=results
        )

    def get_available_checks(self) -> List[str]:
        """Get list of available check names."""
        return list(self._checks.keys())
```

### 3. Stage Registry (45 minutes)

**File**: `compute_forecast/quality/core/registry.py`

```python
from typing import Dict, Optional, Type
from ..stages.base import StageQualityChecker

class StageCheckerRegistry:
    """Registry for stage-specific quality checkers."""

    def __init__(self):
        self._checkers: Dict[str, Type[StageQualityChecker]] = {}
        self._instances: Dict[str, StageQualityChecker] = {}

    def register(self, stage: str, checker_class: Type[StageQualityChecker]):
        """Register a stage checker class."""
        self._checkers[stage.lower()] = checker_class

    def get_checker(self, stage: str) -> Optional[StageQualityChecker]:
        """Get or create a checker instance for a stage."""
        stage = stage.lower()

        if stage not in self._checkers:
            return None

        if stage not in self._instances:
            self._instances[stage] = self._checkers[stage]()

        return self._instances[stage]

    def list_stages(self) -> List[str]:
        """List all registered stages."""
        return list(self._checkers.keys())

    def list_checks_for_stage(self, stage: str) -> Optional[List[str]]:
        """List available checks for a stage."""
        checker = self.get_checker(stage)
        return checker.get_available_checks() if checker else None

# Global registry instance
_registry = StageCheckerRegistry()

def get_registry() -> StageCheckerRegistry:
    """Get the global stage checker registry."""
    return _registry

def register_stage_checker(stage: str, checker_class: Type[StageQualityChecker]):
    """Convenience function to register a stage checker."""
    _registry.register(stage, checker_class)
```

### 4. Quality Runner (60 minutes)

**File**: `compute_forecast/quality/core/runner.py`

```python
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from .interfaces import QualityReport, QualityConfig
from .registry import get_registry

class QualityRunner:
    """Orchestrates quality checks across stages."""

    def __init__(self):
        self.registry = get_registry()

    def run_checks(
        self,
        stage: str,
        data_path: Path,
        config: Optional[QualityConfig] = None
    ) -> QualityReport:
        """Run quality checks for a specific stage."""
        if config is None:
            config = self._get_default_config(stage)

        checker = self.registry.get_checker(stage)
        if not checker:
            raise ValueError(f"No quality checker registered for stage: {stage}")

        return checker.check(data_path, config)

    def run_all_applicable_checks(
        self,
        data_path: Path,
        config: Optional[QualityConfig] = None
    ) -> List[QualityReport]:
        """Run quality checks for all applicable stages based on data."""
        reports = []

        # Detect applicable stages based on file/directory structure
        applicable_stages = self._detect_applicable_stages(data_path)

        for stage in applicable_stages:
            try:
                stage_config = config or self._get_default_config(stage)
                report = self.run_checks(stage, data_path, stage_config)
                reports.append(report)
            except Exception as e:
                # Log but continue with other stages
                print(f"Warning: Quality check failed for stage {stage}: {e}")

        return reports

    def _detect_applicable_stages(self, data_path: Path) -> List[str]:
        """Detect which stages are applicable based on data structure."""
        applicable = []

        if data_path.is_file() and data_path.suffix == '.json':
            # Try to detect stage from file content
            with open(data_path, 'r') as f:
                data = json.load(f)

            # Collection stage detection
            if 'collection_metadata' in data or 'papers' in data:
                applicable.append('collection')

            # Future: Add detection for other stages
            # if 'consolidated_data' in data:
            #     applicable.append('consolidation')

        elif data_path.is_dir():
            # Check directory structure for hints
            if (data_path / 'collected_papers').exists():
                applicable.append('collection')

        return applicable

    def _get_default_config(self, stage: str) -> QualityConfig:
        """Get default configuration for a stage."""
        # Default thresholds by stage
        default_thresholds = {
            'collection': {
                'min_completeness': 0.8,
                'min_coverage': 0.7,
                'min_consistency': 0.9,
                'min_accuracy': 0.85,
            },
            # Future stages...
        }

        return QualityConfig(
            stage=stage,
            thresholds=default_thresholds.get(stage, {}),
            skip_checks=[],
            output_format='text',
            verbose=False
        )
```

### 5. Integration Hooks (45 minutes)

**File**: `compute_forecast/quality/core/hooks.py`

```python
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
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

def _grade_to_color(grade: str) -> str:
    """Get color for grade display."""
    if grade.startswith("A"): return "green"
    elif grade.startswith("B"): return "cyan"
    elif grade.startswith("C"): return "yellow"
    elif grade.startswith("D"): return "magenta"
    else: return "red"
```

### 6. Basic CLI Command Setup (45 minutes)

**File**: `compute_forecast/cli/commands/quality.py`

```python
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from compute_forecast.quality.core.runner import QualityRunner
from compute_forecast.quality.core.interfaces import QualityConfig
from compute_forecast.quality.core.registry import get_registry

console = Console()

def main(
    data_path: Path = typer.Argument(
        ...,
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
    skip_checks: Optional[List[str]] = typer.Option(
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
    if not all_stages and not stage:
        console.print("[red]Error: Must specify either --stage or --all[/red]")
        raise typer.Exit(1)

    if not data_path.exists():
        console.print(f"[red]Error: Data path does not exist: {data_path}[/red]")
        raise typer.Exit(1)

    # Prepare configuration
    config = QualityConfig(
        stage=stage or "all",
        thresholds={},  # Will use defaults
        skip_checks=skip_checks or [],
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
```

### 7. Module Initialization (15 minutes)

**File**: `compute_forecast/quality/__init__.py`

```python
"""Quality checking system for compute-forecast pipeline."""

from .core.interfaces import (
    QualityCheckType,
    QualityIssueLevel,
    QualityIssue,
    QualityCheckResult,
    QualityReport,
    QualityConfig,
)
from .core.runner import QualityRunner
from .core.registry import get_registry, register_stage_checker
from .core.hooks import run_post_command_quality_check
from .stages.base import StageQualityChecker

__all__ = [
    # Core types
    "QualityCheckType",
    "QualityIssueLevel",
    "QualityIssue",
    "QualityCheckResult",
    "QualityReport",
    "QualityConfig",
    # Main components
    "QualityRunner",
    "StageQualityChecker",
    # Functions
    "get_registry",
    "register_stage_checker",
    "run_post_command_quality_check",
]
```

**File**: `compute_forecast/quality/core/__init__.py`

```python
"""Core quality checking infrastructure."""

from .interfaces import *
from .runner import QualityRunner
from .registry import get_registry, register_stage_checker
from .hooks import run_post_command_quality_check

__all__ = [
    "QualityRunner",
    "get_registry",
    "register_stage_checker",
    "run_post_command_quality_check",
]
```

**File**: `compute_forecast/quality/stages/__init__.py`

```python
"""Stage-specific quality checkers."""

from .base import StageQualityChecker

__all__ = ["StageQualityChecker"]
```

### 8. CLI Integration (15 minutes)

Update `compute_forecast/cli/main.py` to register the quality command:

```python
# Add to imports
from .commands.quality import main as quality_command

# Register the quality command
app.command(name="quality")(quality_command)
```

## Implementation Order

1. **Start with interfaces.py** - Define all data structures
2. **Create base.py** - Stage checker base class
3. **Implement registry.py** - Registration system
4. **Build runner.py** - Main orchestrator
5. **Add hooks.py** - Integration utilities
6. **Create basic quality.py CLI** - Minimal command
7. **Update __init__.py files** - Module exports
8. **Update main.py** - Register command

## Testing Strategy

For Phase 1, create a simple test to verify the infrastructure works:

```python
# test_infrastructure.py
from compute_forecast.quality import (
    QualityRunner,
    StageQualityChecker,
    register_stage_checker,
    QualityCheckResult,
    QualityCheckType
)

class DummyChecker(StageQualityChecker):
    def get_stage_name(self):
        return "dummy"

    def load_data(self, data_path):
        return {"test": "data"}

    def _register_checks(self):
        return {"dummy_check": self._dummy_check}

    def _dummy_check(self, data, config):
        return QualityCheckResult(
            check_name="dummy_check",
            check_type=QualityCheckType.COMPLETENESS,
            passed=True,
            score=1.0,
            issues=[]
        )

# Register and test
register_stage_checker("dummy", DummyChecker)
runner = QualityRunner()
report = runner.run_checks("dummy", Path("test.json"))
assert report.overall_score == 1.0
```

## Success Criteria

Phase 1 is complete when:
1. All core interfaces are defined
2. Stage registration system works
3. Quality runner can orchestrate checks
4. Basic CLI command runs without errors
5. Integration hooks are ready for use
6. Simple test passes

## Notes

- Keep implementation minimal - just the framework
- Don't implement actual quality checks yet (Phase 2)
- Focus on clean interfaces and extensibility
- Ensure all components are loosely coupled
- Document interfaces thoroughly

This infrastructure will serve as the foundation for all quality checking functionality in the compute-forecast pipeline.
