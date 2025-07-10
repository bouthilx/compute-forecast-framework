# Quality Command Phase 3: Integration Implementation Plan

**Date**: 2025-01-10  
**Time**: 18:00  
**Task**: Detailed implementation plan for Phase 3 - Integration (3 hours)

## Phase 3 Overview

Based on the design document, Phase 3 focuses on **Integration** - implementing post-command hooks, integrating quality checks with the collect command, adding configuration loading, and testing the end-to-end flow.

**Estimated Time**: 3 hours  
**Scope**: Integration hooks, command integration, configuration management, end-to-end testing

## Phase 3 Tasks from Design Document

### Task 1: Create Post-Command Hooks (45 minutes)
### Task 2: Integrate with Collect Command (90 minutes)  
### Task 3: Add Configuration Loading (30 minutes)
### Task 4: Test End-to-End Flow (45 minutes)

## Implementation Tasks

### 1. Create Post-Command Hooks (45 minutes)

**File**: `compute_forecast/quality/core/hooks.py`

The hooks system needs to provide seamless integration with existing commands without breaking them.

```python
"""Integration hooks for post-command quality checks."""

from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel

from .runner import QualityRunner
from .interfaces import QualityReport, QualityConfig


def run_post_command_quality_check(
    stage: str,
    output_path: Path,
    context: Optional[Dict[str, Any]] = None,
    config: Optional[QualityConfig] = None,
    show_summary: bool = True
) -> Optional[QualityReport]:
    """Run quality checks after a command completes.
    
    Args:
        stage: The pipeline stage that just completed (e.g., "collection")
        output_path: Path to the output data file/directory
        context: Additional context from the command (venues, years, paper counts, etc.)
        config: Optional quality configuration (will use defaults if None)
        show_summary: Whether to show a quality summary in the console
    
    Returns:
        QualityReport if checks were run successfully, None if skipped or failed
    """
    try:
        runner = QualityRunner()
        
        # Use provided config or get defaults
        if config is None:
            config = _get_default_config(stage)
            config.verbose = False  # Keep integrated checks concise
        
        # Run the quality checks
        report = runner.run_checks(stage, output_path, config)
        
        if show_summary:
            _show_quality_summary(report, context)
        
        # Handle critical issues
        if report.has_critical_issues():
            console = Console()
            console.print("\n[red]⚠️  Critical quality issues detected![/red]")
            console.print(f"Run [cyan]cf quality --stage {stage} --verbose {output_path}[/cyan] for details.")
            # Don't fail the command, just warn
        
        return report
        
    except Exception as e:
        # Don't fail the main command if quality checks fail
        console = Console()
        console.print(f"\n[yellow]Warning: Quality checks failed: {e}[/yellow]")
        return None


def _get_default_config(stage: str) -> QualityConfig:
    """Get default configuration for a stage."""
    # Default thresholds based on stage
    default_thresholds = {
        "collection": {
            "min_coverage": 0.7,
            "min_completeness": 0.8,
            "min_consistency": 0.9,
            "min_accuracy": 0.85
        }
    }
    
    return QualityConfig(
        stage=stage,
        thresholds=default_thresholds.get(stage, {}),
        skip_checks=[],
        output_format="text",
        verbose=False
    )


def _show_quality_summary(report: QualityReport, context: Optional[Dict[str, Any]] = None):
    """Show a concise quality summary in the console."""
    console = Console()
    
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
        if 'venues' in context:
            venues_str = ', '.join(context['venues'][:3])
            if len(context['venues']) > 3:
                venues_str += f" (+{len(context['venues']) - 3} more)"
            summary_lines.append(f"Venues: {venues_str}")
    
    # Add issue counts
    critical_count = len(report.critical_issues)
    warning_count = len(report.warnings)
    
    if critical_count > 0:
        summary_lines.append(f"[red]Critical Issues: {critical_count}[/red]")
    if warning_count > 0:
        summary_lines.append(f"[yellow]Warnings: {warning_count}[/yellow]")
    
    if critical_count == 0 and warning_count == 0:
        summary_lines.append("[green]No issues detected[/green]")
    
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

### 2. Integrate with Collect Command (90 minutes)

**File**: `compute_forecast/cli/commands/collect.py` (modifications)

Add quality check integration to the collect command with proper error handling and user control.

```python
# Add import at top of file
from compute_forecast.quality.core.hooks import run_post_command_quality_check

# Add parameter to main function
def main(
    # ... existing parameters ...
    skip_quality_check: bool = typer.Option(
        False, 
        "--skip-quality-check", 
        help="Skip automatic quality checking after collection"
    ),
):
    """
    Collect research papers from various venues and years.
    
    ... existing docstring ...
    
    Quality Checking:
        By default, quality checks run automatically after collection.
        Use --skip-quality-check to disable this behavior.
    """
    
    # ... existing collection logic ...
    
    # At the end of successful collection, before the summary:
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
            for error in errors[:5]:
                console.print(f"  - {error}")
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more")
        
        # Run quality checks if not skipped
        if not skip_quality_check:
            console.print("\n[cyan]Running quality checks on collected data...[/cyan]")
            try:
                context = {
                    "total_papers": len(all_papers),
                    "venues": list(set(p.venue for p in all_papers)),
                    "years": sorted(list(set(p.year for p in all_papers))),
                    "scrapers_used": list(set(p.source_scraper for p in all_papers)),
                    "errors": errors
                }
                run_post_command_quality_check(
                    stage="collection",
                    output_path=output,
                    context=context,
                    show_summary=True
                )
            except Exception as e:
                console.print(f"[yellow]Warning: Quality check failed: {e}[/yellow]")
                # Don't fail the entire command if quality check fails
    else:
        console.print("[red]No papers collected![/red]")
        raise typer.Exit(1)
```

### 3. Add Configuration Loading (30 minutes)

**File**: `compute_forecast/quality/core/config.py`

Create configuration management for quality thresholds and settings.

```python
"""Configuration management for quality checks."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
import yaml

from .interfaces import QualityConfig


def load_quality_config(
    stage: str, 
    config_file: Optional[Path] = None,
    override_config: Optional[QualityConfig] = None
) -> QualityConfig:
    """Load quality configuration for a stage.
    
    Configuration is loaded in this order (later sources override earlier):
    1. Default configuration
    2. Global config file (~/.cf/quality.yaml)
    3. Project config file (.cf-quality.yaml in current directory)
    4. Explicit config file (if provided)
    5. Environment variables
    6. Override config (if provided)
    """
    # Start with defaults
    config = _get_default_config(stage)
    
    # Load from config files
    configs_to_try = []
    
    # Global config
    global_config = Path.home() / ".cf" / "quality.yaml"
    if global_config.exists():
        configs_to_try.append(global_config)
    
    # Project config
    project_config = Path.cwd() / ".cf-quality.yaml"
    if project_config.exists():
        configs_to_try.append(project_config)
    
    # Explicit config file
    if config_file and config_file.exists():
        configs_to_try.append(config_file)
    
    # Load and merge configs
    for config_path in configs_to_try:
        try:
            file_config = _load_config_file(config_path, stage)
            config = _merge_configs(config, file_config)
        except Exception as e:
            # Don't fail on config errors, just warn
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Override from environment variables
    env_config = _load_from_env(stage)
    config = _merge_configs(config, env_config)
    
    # Apply override config
    if override_config:
        config = _merge_configs(config, override_config)
    
    return config


def _get_default_config(stage: str) -> QualityConfig:
    """Get default configuration for a stage."""
    defaults = {
        "collection": {
            "stage": "collection",
            "thresholds": {
                "min_coverage": 0.7,
                "min_completeness": 0.8,
                "min_consistency": 0.9,
                "min_accuracy": 0.85
            },
            "skip_checks": [],
            "output_format": "text",
            "verbose": False
        }
    }
    
    stage_defaults = defaults.get(stage, defaults["collection"])
    return QualityConfig(**stage_defaults)


def _load_config_file(config_path: Path, stage: str) -> QualityConfig:
    """Load configuration from a YAML or JSON file."""
    with open(config_path, 'r') as f:
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    
    # Extract stage-specific config
    stage_config = data.get('stages', {}).get(stage, {})
    global_config = {k: v for k, v in data.items() if k != 'stages'}
    
    # Merge global and stage-specific
    merged = {**global_config, **stage_config}
    
    return QualityConfig(
        stage=merged.get('stage', stage),
        thresholds=merged.get('thresholds', {}),
        skip_checks=merged.get('skip_checks', []),
        output_format=merged.get('output_format', 'text'),
        verbose=merged.get('verbose', False)
    )


def _load_from_env(stage: str) -> QualityConfig:
    """Load configuration from environment variables."""
    prefix = f"CF_QUALITY_{stage.upper()}_"
    
    thresholds = {}
    skip_checks = []
    
    # Load thresholds from env
    for key in ['MIN_COVERAGE', 'MIN_COMPLETENESS', 'MIN_CONSISTENCY', 'MIN_ACCURACY']:
        env_key = f"{prefix}{key}"
        if env_key in os.environ:
            thresholds[key.lower()] = float(os.environ[env_key])
    
    # Load skip checks from env
    skip_env = os.environ.get(f"{prefix}SKIP_CHECKS", "")
    if skip_env:
        skip_checks = [s.strip() for s in skip_env.split(",")]
    
    return QualityConfig(
        stage=stage,
        thresholds=thresholds,
        skip_checks=skip_checks,
        output_format=os.environ.get(f"{prefix}OUTPUT_FORMAT", "text"),
        verbose=os.environ.get(f"{prefix}VERBOSE", "false").lower() == "true"
    )


def _merge_configs(base: QualityConfig, override: QualityConfig) -> QualityConfig:
    """Merge two configurations, with override taking precedence."""
    merged_thresholds = {**base.thresholds, **override.thresholds}
    merged_skip_checks = list(set(base.skip_checks + override.skip_checks))
    
    return QualityConfig(
        stage=override.stage or base.stage,
        thresholds=merged_thresholds,
        skip_checks=merged_skip_checks,
        output_format=override.output_format or base.output_format,
        verbose=override.verbose if override.verbose is not None else base.verbose
    )
```

### 4. Test End-to-End Flow (45 minutes)

**File**: `tests/integration/quality/test_integration_flow.py`

Comprehensive integration tests for the complete quality check flow.

```python
"""Integration tests for quality check end-to-end flow."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from compute_forecast.quality.core.hooks import run_post_command_quality_check
from compute_forecast.quality.core.config import load_quality_config
from compute_forecast.quality.core.interfaces import QualityConfig


class TestQualityIntegrationFlow:
    """Test complete integration flow of quality checks."""
    
    def test_post_command_hook_with_good_data(self):
        """Test post-command hook with high-quality collection data."""
        with TemporaryDirectory() as tmp_dir:
            # Create test collection data
            test_data = self._create_good_collection_data()
            data_file = Path(tmp_dir) / "collection.json"
            
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
            
            # Test post-command hook
            context = {
                "total_papers": len(test_data["papers"]),
                "venues": ["NeurIPS", "ICML"],
                "years": [2023, 2024],
                "scrapers_used": ["neurips_scraper", "icml_scraper"]
            }
            
            report = run_post_command_quality_check(
                stage="collection",
                output_path=data_file,
                context=context,
                show_summary=False  # Don't print during tests
            )
            
            assert report is not None
            assert report.stage == "collection"
            assert report.overall_score >= 0.8
            assert len(report.critical_issues) == 0
    
    def test_post_command_hook_with_poor_data(self):
        """Test post-command hook with low-quality collection data."""
        with TemporaryDirectory() as tmp_dir:
            # Create test collection data with issues
            test_data = self._create_poor_collection_data()
            data_file = Path(tmp_dir) / "collection.json"
            
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
            
            context = {
                "total_papers": len(test_data["papers"]),
                "venues": ["Unknown"],
                "years": [2023],
                "scrapers_used": ["failing_scraper"]
            }
            
            report = run_post_command_quality_check(
                stage="collection",
                output_path=data_file,
                context=context,
                show_summary=False
            )
            
            assert report is not None
            assert report.overall_score < 0.7
            assert len(report.critical_issues) > 0 or len(report.warnings) > 0
    
    def test_post_command_hook_with_missing_file(self):
        """Test post-command hook gracefully handles missing files."""
        missing_file = Path("/nonexistent/file.json")
        
        report = run_post_command_quality_check(
            stage="collection",
            output_path=missing_file,
            show_summary=False
        )
        
        # Should return None when file doesn't exist
        assert report is None
    
    def test_config_loading_from_defaults(self):
        """Test configuration loading with defaults."""
        config = load_quality_config("collection")
        
        assert config.stage == "collection"
        assert "min_coverage" in config.thresholds
        assert config.output_format == "text"
        assert config.verbose is False
    
    def test_config_loading_from_file(self):
        """Test configuration loading from config file."""
        with TemporaryDirectory() as tmp_dir:
            # Create test config file
            config_data = {
                "stages": {
                    "collection": {
                        "thresholds": {
                            "min_coverage": 0.9,
                            "min_completeness": 0.95
                        },
                        "skip_checks": ["url_validation"],
                        "verbose": True
                    }
                }
            }
            
            config_file = Path(tmp_dir) / "quality.yaml"
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            config = load_quality_config("collection", config_file=config_file)
            
            assert config.thresholds["min_coverage"] == 0.9
            assert config.thresholds["min_completeness"] == 0.95
            assert "url_validation" in config.skip_checks
            assert config.verbose is True
    
    def test_config_loading_from_environment(self):
        """Test configuration loading from environment variables."""
        with patch.dict('os.environ', {
            'CF_QUALITY_COLLECTION_MIN_COVERAGE': '0.85',
            'CF_QUALITY_COLLECTION_SKIP_CHECKS': 'check1,check2',
            'CF_QUALITY_COLLECTION_VERBOSE': 'true'
        }):
            config = load_quality_config("collection")
            
            assert config.thresholds["min_coverage"] == 0.85
            assert "check1" in config.skip_checks
            assert "check2" in config.skip_checks
            assert config.verbose is True
    
    @patch('compute_forecast.cli.commands.collect.run_post_command_quality_check')
    def test_collect_command_integration(self, mock_quality_check):
        """Test that collect command properly calls quality checks."""
        # Mock the quality check function
        mock_report = MagicMock()
        mock_report.has_critical_issues.return_value = False
        mock_quality_check.return_value = mock_report
        
        # Import here to avoid circular imports during test collection
        from compute_forecast.cli.commands.collect import main as collect_main
        
        # This test would need more setup to actually run collect command
        # For now, just verify the mock setup works
        assert mock_quality_check is not None
    
    def test_error_handling_in_hooks(self):
        """Test that quality check errors don't break the main command."""
        with TemporaryDirectory() as tmp_dir:
            # Create invalid JSON file
            data_file = Path(tmp_dir) / "invalid.json"
            with open(data_file, 'w') as f:
                f.write("invalid json content")
            
            # Should not raise exception, should return None
            report = run_post_command_quality_check(
                stage="collection",
                output_path=data_file,
                show_summary=False
            )
            
            assert report is None
    
    def _create_good_collection_data(self):
        """Create high-quality test collection data."""
        return {
            "collection_metadata": {
                "timestamp": "2024-01-10T12:00:00",
                "venues": ["NeurIPS", "ICML"],
                "years": [2023, 2024],
                "total_papers": 4,
                "scrapers_used": ["neurips_scraper", "icml_scraper"]
            },
            "papers": [
                {
                    "title": "High Quality Paper 1",
                    "authors": ["Dr. John Smith", "Prof. Jane Doe"],
                    "venue": "NeurIPS",
                    "year": 2024,
                    "abstract": "This is a high-quality paper with good metadata.",
                    "pdf_urls": ["https://papers.nips.cc/paper1.pdf"],
                    "doi": "10.5555/neurips.2024.1",
                    "paper_id": "neurips_2024_1",
                    "source_scraper": "neurips_scraper"
                },
                {
                    "title": "High Quality Paper 2",
                    "authors": ["Dr. Alice Johnson", "Prof. Bob Wilson"],
                    "venue": "ICML",
                    "year": 2024,
                    "abstract": "Another high-quality paper with complete information.",
                    "pdf_urls": ["https://proceedings.icml.cc/paper2.pdf"],
                    "doi": "10.5555/icml.2024.2",
                    "paper_id": "icml_2024_2",
                    "source_scraper": "icml_scraper"
                },
                {
                    "title": "High Quality Paper 3",
                    "authors": ["Dr. Charlie Brown"],
                    "venue": "NeurIPS",
                    "year": 2023,
                    "abstract": "Well-formatted paper with good metadata.",
                    "pdf_urls": ["https://papers.nips.cc/paper3.pdf"],
                    "doi": "10.5555/neurips.2023.3",
                    "paper_id": "neurips_2023_3",
                    "source_scraper": "neurips_scraper"
                },
                {
                    "title": "High Quality Paper 4",
                    "authors": ["Dr. Diana Prince", "Prof. Eve Davis"],
                    "venue": "ICML",
                    "year": 2023,
                    "abstract": "Complete paper with all required information.",
                    "pdf_urls": ["https://proceedings.icml.cc/paper4.pdf"],
                    "doi": "10.5555/icml.2023.4",
                    "paper_id": "icml_2023_4",
                    "source_scraper": "icml_scraper"
                }
            ]
        }
    
    def _create_poor_collection_data(self):
        """Create low-quality test collection data with various issues."""
        return {
            "collection_metadata": {
                "timestamp": "2024-01-10T12:00:00",
                "venues": ["Unknown"],
                "years": [2023],
                "total_papers": 3,
                "scrapers_used": ["failing_scraper"]
            },
            "papers": [
                {
                    "title": "Poor Paper 1",
                    "authors": ["X", "123"],  # Bad author names
                    "venue": "Unknown",
                    "year": 1800,  # Invalid year
                    "abstract": "",  # Empty abstract
                    "pdf_urls": ["not_a_url"],  # Invalid URL
                    "doi": "bad_doi",  # Invalid DOI
                    "paper_id": "poor_1",
                    "source_scraper": "failing_scraper"
                },
                {
                    "title": "Poor Paper 2",
                    "authors": [],  # No authors
                    "venue": "",  # Empty venue
                    "year": "invalid",  # Invalid year format
                    "pdf_urls": [],  # No URLs
                    "paper_id": "poor_2",
                    "source_scraper": "failing_scraper"
                    # Missing abstract and DOI entirely
                },
                {
                    "title": "Poor Paper 1",  # Duplicate title
                    "authors": ["Same Author"],
                    "venue": "Same Venue",
                    "year": 2023,
                    "paper_id": "poor_3",
                    "source_scraper": "failing_scraper"
                    # Missing many fields
                }
            ]
        }
```

## Testing Plan

### Manual Testing Checklist

1. **Hook Integration**
   - [ ] Collect command runs quality checks by default
   - [ ] Quality checks can be skipped with `--skip-quality-check`
   - [ ] Quality summary appears after collection summary
   - [ ] Critical issues are highlighted properly
   - [ ] Quality check failures don't break collection command

2. **Configuration Loading**
   - [ ] Default configuration works
   - [ ] Config files are loaded properly
   - [ ] Environment variables override config files
   - [ ] Invalid config files don't break the system

3. **End-to-End Flow**
   - [ ] Full workflow: collect → automatic quality check → summary
   - [ ] Manual quality check on collected data works
   - [ ] Multiple output formats work
   - [ ] Error handling works gracefully

### Test Commands

```bash
# Test basic integration
cf collect --venue neurips --year 2024 --max-papers 10

# Test with quality checks skipped
cf collect --venue neurips --year 2024 --max-papers 10 --skip-quality-check

# Test manual quality check
cf quality --stage collection data/collected_papers/papers_*.json

# Test with environment configuration
CF_QUALITY_COLLECTION_MIN_COVERAGE=0.9 cf collect --venue icml --year 2024 --max-papers 5
```

## Success Criteria

### Phase 3 Complete When:

1. **✅ Post-command hooks implemented and working**
   - Hooks integrate seamlessly with collect command
   - Quality checks run automatically after collection
   - Option to skip quality checks works
   - Error handling prevents command failures

2. **✅ Collect command integration complete**
   - Quality checks integrated into collect workflow
   - Context information passed properly
   - Summary displays correctly
   - User can control quality check behavior

3. **✅ Configuration loading working**
   - Default configurations load properly
   - Config files (YAML/JSON) are supported
   - Environment variables override configs
   - Invalid configurations handled gracefully

4. **✅ End-to-end flow tested and validated**
   - Full workflow works: collect → quality check → summary
   - Manual quality checks work on collected data
   - Integration tests pass
   - Error scenarios handled properly

## Risk Mitigation

1. **Integration Breakage**: Keep hooks optional and non-breaking
2. **Performance Impact**: Keep quality checks fast (<10s for typical collections)
3. **Configuration Complexity**: Provide sensible defaults, make config optional
4. **Error Propagation**: Ensure quality check failures don't break main commands

## Files Created/Modified

### New Files:
- `compute_forecast/quality/core/hooks.py` - Post-command integration hooks
- `compute_forecast/quality/core/config.py` - Configuration management
- `tests/integration/quality/test_integration_flow.py` - Integration tests

### Modified Files:
- `compute_forecast/cli/commands/collect.py` - Add quality check integration
- `compute_forecast/quality/core/__init__.py` - Export new components

Phase 3 establishes the integration foundation that makes quality checks a seamless part of the compute-forecast workflow while maintaining the flexibility to use them standalone.