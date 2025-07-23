# Quality Command Design and Implementation Plan (Revised)

**Date**: 2025-01-10
**Time**: 15:30
**Task**: Revised design and plan for `cf quality` command based on feedback

## Executive Summary

Design a modular quality checking system for the compute-forecast pipeline, starting with collection stage quality checks. The system will provide automated quality assessment at the end of each pipeline stage, with a standalone CLI command for manual quality checks. Initial implementation focuses on collection stage with extensible architecture for future stages.

## Analysis of Existing Quality Infrastructure

### Current State

The codebase contains extensive quality infrastructure spread across multiple modules:

1. **Core Quality Modules** (`compute_forecast/quality/`)
   - `quality_analyzer.py` - Weighted scoring for papers/venues
   - `quality_filter.py` - Threshold-based filtering
   - `quality_structures.py` - Data structures
   - Complex adaptive threshold and monitoring systems

2. **Pipeline Quality** (`compute_forecast/pipeline/`)
   - Extraction quality validators with confidence scoring
   - Computational analysis quality control with comprehensive checkers
   - Cross-validation and consistency checking

3. **Key Findings**
   - No standalone CLI command for quality checks
   - Quality checks embedded in pipeline components
   - Overly complex for initial needs (adaptive thresholds, monitoring)
   - Good patterns for reuse (data structures, scoring, check types)

### Reuse Strategy

**Keep:**
- Core data structures (`QualityIssue`, `QualityReport`, scoring system)
- Multi-level check pattern (completeness, consistency, accuracy, plausibility)
- Issue severity levels (critical, warning, info)
- 0.0-1.0 scoring paradigm

**Simplify:**
- Remove adaptive thresholds (overkill for current needs)
- Skip monitoring integration (can add later)
- Flatten complex validation hierarchies

**Extend:**
- Add stage-specific quality checkers
- Create unified CLI interface
- Build integration hooks for commands

## Proposed Architecture

### Module Structure

```
compute_forecast/
├── cli/
│   └── commands/
│       └── quality.py             # Quality CLI command
└── quality/                       # Quality check helpers
    ├── stages/                    # Stage-specific quality checks
    │   ├── base.py                # Base stage checker interface
    │   ├── collection/            # Collection stage checks
    │   │   ├── checker.py         # Main collection quality checker
    │   │   ├── validators.py      # Collection-specific validators
    │   │   └── metrics.py         # Collection quality metrics
    │   ├── consolidation/         # Future: Consolidation stage
    │   ├── extraction/            # Future: Extraction stage
    │   ├── preanalysis/           # Future: Pre-analysis stage
    │   └── analysis/              # Future: Analysis stage
    ├── core/                      # Core quality infrastructure
    │   ├── interfaces.py          # Main interfaces
    │   ├── registry.py            # Stage checker registry
    │   ├── runner.py              # Quality check orchestrator
    │   └── hooks.py               # Integration hooks
    └── reports/                   # Reporting utilities
        ├── formatters.py          # Output formatters (text, json, markdown)
        ├── generator.py           # Report generation
        └── templates/             # Report templates
```

### Core Interfaces

```python
# Base interface for all stage checkers
class StageQualityChecker(ABC):
    @abstractmethod
    def check(self, data: Any, config: QualityConfig) -> QualityReport:
        """Run quality checks for this stage."""

    @abstractmethod
    def get_stage_name(self) -> str:
        """Return the stage name."""

# Configuration for quality checks
@dataclass
class QualityConfig:
    stage: str
    thresholds: Dict[str, float]
    skip_checks: List[str] = field(default_factory=list)
    output_format: str = "text"
    verbose: bool = False

# Main orchestrator
class QualityRunner:
    def run_checks(self, stage: str, data_path: Path, config: QualityConfig) -> QualityReport:
        """Run quality checks for specified stage."""

    def register_stage_checker(self, checker: StageQualityChecker):
        """Register a stage-specific checker."""
```

## Collection Stage Quality Checks

### Check Categories

1. **Completeness Checks**
   - Paper-level: Required fields (title, authors, venue, year)
   - Paper-level: Important fields (abstract, pdf_urls, paper_id)
   - Collection-level: Coverage vs expected counts
   - Collection-level: Venue/year completeness

2. **Consistency Checks**
   - Venue consistency (labeled venue matches actual)
   - Year consistency (labeled year matches actual)
   - Format standardization (author names, venues)

3. **Accuracy Checks**
   - Temporal validation (reasonable year bounds)
   - Author name pattern validation
   - URL format validation
   - Known venue name validation

4. **Quality Metrics**
   ```python
   @dataclass
   class CollectionQualityMetrics:
       # Coverage
       total_papers_collected: int
       expected_papers: Optional[int]
       coverage_rate: float

       # Completeness
       papers_with_abstracts: int
       papers_with_pdfs: int
       papers_with_all_required_fields: int
       field_completeness_scores: Dict[str, float]

       # Consistency
       venue_consistency_score: float
       year_consistency_score: float
       duplicate_rate: float

       # Sources
       papers_by_scraper: Dict[str, int]
       scraper_success_rates: Dict[str, float]
   ```

### Author Name Pattern Validation Implementation

The author name pattern validation will check that author names follow reasonable patterns and catch common extraction errors:

```python
def validate_author_names(papers: List[SimplePaper], config: QualityConfig) -> QualityCheckResult:
    """Validate that author names follow reasonable patterns."""
    import re

    issues = []
    papers_with_issues = set()
    total_authors_checked = 0
    problematic_authors = 0

    # Common patterns that indicate extraction errors
    suspicious_patterns = [
        r'^\d+$',  # Just numbers
        r'^[A-Z]{2,}$',  # All caps abbreviations (except valid like "AI")
        r'^\W+$',  # Only special characters
        r'^.{1}$',  # Single character (except valid initials)
        r'\d{3,}',  # Contains 3+ consecutive digits
        r'[^\w\s\-\'\.]',  # Contains unusual characters
        r'^(and|et|al|der|van|von|de|la|le)$',  # Common particles as full names
    ]

    # Compile patterns
    suspicious_regexes = [re.compile(p, re.IGNORECASE) for p in suspicious_patterns]

    # Valid name pattern (basic check)
    valid_name_pattern = re.compile(r'^[A-Za-z\-\'\s\.]+$')

    for paper in papers:
        paper_has_issues = False

        for author in paper.authors:
            total_authors_checked += 1

            # Check for empty or whitespace-only
            if not author or not author.strip():
                problematic_authors += 1
                paper_has_issues = True
                issues.append(QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.WARNING,
                    field="authors",
                    message=f"Empty author name in paper '{paper.title}'",
                    suggested_action="Check paper extraction for author parsing errors",
                    details={"paper_id": paper.paper_id}
                ))
                continue

            # Check for suspicious patterns
            for regex in suspicious_regexes:
                if regex.match(author.strip()):
                    problematic_authors += 1
                    paper_has_issues = True
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.WARNING,
                        field="authors",
                        message=f"Suspicious author name '{author}' in paper '{paper.title}'",
                        suggested_action="Verify author name extraction",
                        details={"paper_id": paper.paper_id, "author": author}
                    ))
                    break

            # Check if doesn't match valid pattern
            if not valid_name_pattern.match(author.strip()):
                problematic_authors += 1
                paper_has_issues = True
                issues.append(QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.INFO,
                    field="authors",
                    message=f"Unusual characters in author name '{author}'",
                    suggested_action="Verify if special characters are correct",
                    details={"paper_id": paper.paper_id, "author": author}
                ))

        if paper_has_issues:
            papers_with_issues.add(paper.paper_id)

    # Calculate score
    author_score = 1.0 - (problematic_authors / total_authors_checked) if total_authors_checked > 0 else 1.0
    paper_score = 1.0 - (len(papers_with_issues) / len(papers)) if papers else 1.0
    score = (author_score + paper_score) / 2  # Average of both metrics

    return QualityCheckResult(
        check_name="author_name_validation",
        check_type=QualityCheckType.ACCURACY,
        passed=len(issues) == 0,
        score=score,
        issues=issues,
        metrics={
            "papers_checked": len(papers),
            "total_authors_checked": total_authors_checked,
            "problematic_authors": problematic_authors,
            "papers_with_author_issues": len(papers_with_issues),
            "author_accuracy_rate": author_score,
            "paper_accuracy_rate": paper_score
        }
    )
```

## Integration Pattern

### Command Integration

```python
# In collect.py
from compute_forecast.quality.core.hooks import run_post_command_quality_check

def collect_command(..., run_quality_check: bool = True):
    # ... existing collection logic ...

    # Post-collection quality check
    if run_quality_check:
        quality_report = run_post_command_quality_check(
            stage="collection",
            output_path=output_path,
            context={
                "venues": venues_collected,
                "years": years_collected,
                "total_papers": len(papers),
            }
        )

        if quality_report.has_critical_issues():
            console.print("[red]Critical quality issues detected![/red]")
            # Show summary and optionally abort
```

### Hook Implementation

```python
# quality/core/hooks.py
def run_post_command_quality_check(
    stage: str,
    output_path: Path,
    context: Dict[str, Any]
) -> QualityReport:
    """Run quality checks after command completion."""
    runner = QualityRunner()
    config = QualityConfig(
        stage=stage,
        thresholds=load_default_thresholds(stage),
        verbose=False  # Summary only for integrated checks
    )
    return runner.run_checks(stage, output_path, config)
```

## CLI Interface

### Command Structure

```bash
# Check specific file/directory
cf quality --stage collection data/collected_papers/neurips_2024.json

# Check all files in directory
cf quality --stage collection data/collected_papers/

# Run all applicable checks
cf quality --all data/

# Output formats
cf quality --stage collection --format json --output report.json
cf quality --stage collection --format markdown --output report.md

# Verbose output
cf quality --stage collection --verbose data/papers.json

# Custom thresholds
cf quality --stage collection --min-coverage 0.8 --min-completeness 0.9

# Skip specific checks
cf quality --stage collection --skip-checks url_validation,abstract_validation
```

### Output Examples

**Text Format (Default):**
```
Quality Report: Collection Stage
================================
File: data/collected_papers/neurips_2024.json
Papers: 1,532
Overall Score: 0.87 (B+)

Completeness: 0.92 (A-)
✓ All papers have required fields
⚠ 156 papers (10.2%) missing abstracts
⚠ 89 papers (5.8%) missing PDF URLs

Consistency: 0.85 (B)
✓ Venue consistency: 100%
✓ Year consistency: 100%
⚠ 23 duplicate papers detected (1.5%)

Accuracy: 0.84 (B)
✓ All years within valid range
✓ Author names validated
⚠ 45 papers (2.9%) with invalid URLs

Coverage: 0.88 (B+)
✓ Collected 1,532 of ~1,740 expected papers (88.0%)
```

## Implementation Timeline

### Phase 1: Core Infrastructure (4 hours)
- [ ] Create base interfaces and data structures
- [ ] Implement stage registry pattern
- [ ] Build quality runner orchestrator
- [ ] Set up basic CLI command structure

### Phase 2: Collection Stage (6 hours)
- [ ] Implement collection-specific validators
- [ ] Create completeness checker
- [ ] Create consistency checker
- [ ] Create accuracy checker (including temporal validation)
- [ ] Build metrics calculation
- [ ] Implement report generation

### Phase 3: Integration (3 hours)
- [ ] Create post-command hooks
- [ ] Integrate with collect command
- [ ] Add configuration loading
- [ ] Test end-to-end flow

### Phase 4: CLI & Reporting (3 hours)
- [ ] Complete CLI command with all options
- [ ] Implement formatters (text, json, markdown)
- [ ] Create report templates
- [ ] Add progress tracking

### Phase 5: Testing & Documentation (2 hours)
- [ ] Unit tests for quality checkers
- [ ] Integration tests for CLI
- [ ] Update documentation
- [ ] Add usage examples

## Success Criteria

1. **Functionality**: Collection stage quality checks working end-to-end
2. **Integration**: Seamless integration with collect command
3. **Extensibility**: Easy to add new stages (consolidation, extraction, analysis)
4. **Usability**: Clear, actionable quality reports
5. **Performance**: Quality checks complete in <30s for 10K papers

## Risk Mitigation

1. **Scope Creep**: Focus only on collection stage initially
2. **Over-engineering**: Keep it simple, avoid premature optimization
3. **Integration Issues**: Design hooks to be optional/non-breaking
4. **Performance**: Use sampling for very large collections

## Next Steps

1. Implement core infrastructure
2. Build collection stage quality checks
3. Integrate with collect command
4. Add CLI command
5. Test with real collection data

This design provides a clean, focused implementation that can grow with the project's needs while delivering immediate value for collection quality assessment.
