# Quality Command Phase 2: Collection Stage Implementation

**Date**: 2025-01-10  
**Time**: 16:00  
**Task**: Detailed implementation plan for Phase 2 of quality command (Collection Stage Quality Checks)

## Phase 2 Overview

Build collection-specific quality checks on top of the Phase 1 infrastructure. This phase implements comprehensive quality validation for collected papers, including completeness, consistency, accuracy, and coverage checks. The implementation will integrate seamlessly with the `cf collect` command to provide automatic quality assessment.

## Implementation Tasks

### 1. Collection Data Models (30 minutes)

**File**: `compute_forecast/quality/stages/collection/models.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class CollectionQualityMetrics:
    """Metrics for collection quality assessment."""
    
    # Coverage metrics
    total_papers_collected: int
    expected_papers: Optional[int] = None
    coverage_rate: float = 0.0
    
    # Completeness metrics
    papers_with_all_required_fields: int = 0
    papers_with_abstracts: int = 0
    papers_with_pdfs: int = 0
    papers_with_dois: int = 0
    field_completeness_scores: Dict[str, float] = field(default_factory=dict)
    
    # Consistency metrics
    venue_consistency_score: float = 1.0
    year_consistency_score: float = 1.0
    duplicate_count: int = 0
    duplicate_rate: float = 0.0
    
    # Accuracy metrics
    valid_years_count: int = 0
    valid_authors_count: int = 0
    valid_urls_count: int = 0
    accuracy_scores: Dict[str, float] = field(default_factory=dict)
    
    # Source metrics
    papers_by_scraper: Dict[str, int] = field(default_factory=dict)
    scraper_success_rates: Dict[str, float] = field(default_factory=dict)
    
    # Timing
    collection_timestamp: Optional[datetime] = None
    quality_check_timestamp: Optional[datetime] = None

@dataclass
class CollectionContext:
    """Context information from collection process."""
    
    venues_requested: List[str]
    years_requested: List[int]
    scrapers_used: List[str]
    collection_duration: Optional[float] = None
    errors_encountered: List[str] = field(default_factory=list)
```

### 2. Collection Checker Implementation (90 minutes)

**File**: `compute_forecast/quality/stages/collection/checker.py`

```python
import json
from pathlib import Path
from typing import Dict, List, Any, Callable
from datetime import datetime

from compute_forecast.quality.stages.base import StageQualityChecker
from compute_forecast.quality.core.interfaces import (
    QualityCheckResult, QualityCheckType, QualityConfig
)
from .validators import (
    CompletenessValidator,
    ConsistencyValidator,
    AccuracyValidator,
    CoverageValidator
)
from .models import CollectionQualityMetrics, CollectionContext

class CollectionQualityChecker(StageQualityChecker):
    """Quality checker for collection stage."""
    
    def __init__(self):
        self.completeness_validator = CompletenessValidator()
        self.consistency_validator = ConsistencyValidator()
        self.accuracy_validator = AccuracyValidator()
        self.coverage_validator = CoverageValidator()
        super().__init__()
    
    def get_stage_name(self) -> str:
        return "collection"
    
    def load_data(self, data_path: Path) -> Dict[str, Any]:
        """Load collection data from JSON file."""
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Extract papers and metadata
        papers = data.get('papers', [])
        metadata = data.get('collection_metadata', {})
        
        # Build context from metadata
        context = CollectionContext(
            venues_requested=metadata.get('venues', []),
            years_requested=metadata.get('years', []),
            scrapers_used=metadata.get('scrapers_used', []),
            collection_duration=metadata.get('duration_seconds'),
            errors_encountered=metadata.get('errors', [])
        )
        
        return {
            'papers': papers,
            'metadata': metadata,
            'context': context,
            'metrics': self._calculate_metrics(papers, metadata, context)
        }
    
    def _register_checks(self) -> Dict[str, Callable]:
        """Register all collection quality checks."""
        return {
            'completeness_check': self._completeness_check,
            'consistency_check': self._consistency_check,
            'accuracy_check': self._accuracy_check,
            'coverage_check': self._coverage_check,
        }
    
    def _completeness_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Check completeness of collected papers."""
        papers = data['papers']
        metrics = data['metrics']
        
        return self.completeness_validator.validate(
            papers, 
            metrics,
            config.thresholds.get('min_completeness', 0.8)
        )
    
    def _consistency_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Check consistency of collected data."""
        papers = data['papers']
        context = data['context']
        metrics = data['metrics']
        
        return self.consistency_validator.validate(
            papers,
            context,
            metrics,
            config.thresholds.get('min_consistency', 0.9)
        )
    
    def _accuracy_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Check accuracy of collected data."""
        papers = data['papers']
        metrics = data['metrics']
        
        return self.accuracy_validator.validate(
            papers,
            metrics,
            config.thresholds.get('min_accuracy', 0.85),
            config.custom_params
        )
    
    def _coverage_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Check coverage of collection."""
        papers = data['papers']
        context = data['context']
        metrics = data['metrics']
        
        return self.coverage_validator.validate(
            papers,
            context,
            metrics,
            config.thresholds.get('min_coverage', 0.7)
        )
    
    def _calculate_metrics(
        self, 
        papers: List[Dict[str, Any]], 
        metadata: Dict[str, Any],
        context: CollectionContext
    ) -> CollectionQualityMetrics:
        """Calculate comprehensive metrics for the collection."""
        metrics = CollectionQualityMetrics(
            total_papers_collected=len(papers),
            collection_timestamp=datetime.fromisoformat(metadata['timestamp'])
            if 'timestamp' in metadata else None,
            quality_check_timestamp=datetime.now()
        )
        
        # Field completeness
        required_fields = ['title', 'authors', 'venue', 'year']
        optional_fields = ['abstract', 'pdf_urls', 'doi', 'paper_id']
        
        for paper in papers:
            # Check required fields
            if all(paper.get(f) for f in required_fields):
                metrics.papers_with_all_required_fields += 1
            
            # Check optional fields
            if paper.get('abstract'):
                metrics.papers_with_abstracts += 1
            if paper.get('pdf_urls') and len(paper['pdf_urls']) > 0:
                metrics.papers_with_pdfs += 1
            if paper.get('doi'):
                metrics.papers_with_dois += 1
        
        # Calculate field completeness scores
        if papers:
            for field in required_fields + optional_fields:
                count = sum(1 for p in papers if p.get(field))
                metrics.field_completeness_scores[field] = count / len(papers)
        
        # Source metrics
        for paper in papers:
            scraper = paper.get('source_scraper', 'unknown')
            metrics.papers_by_scraper[scraper] = metrics.papers_by_scraper.get(scraper, 0) + 1
        
        return metrics
```

### 3. Validator Implementations (2 hours)

**File**: `compute_forecast/quality/stages/collection/validators.py`

```python
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse

from compute_forecast.quality.core.interfaces import (
    QualityCheckResult, QualityCheckType, QualityIssue, QualityIssueLevel
)
from .models import CollectionQualityMetrics, CollectionContext

class CompletenessValidator:
    """Validates completeness of collected papers."""
    
    REQUIRED_FIELDS = ['title', 'authors', 'venue', 'year']
    IMPORTANT_FIELDS = ['abstract', 'pdf_urls', 'paper_id']
    
    def validate(
        self, 
        papers: List[Dict[str, Any]], 
        metrics: CollectionQualityMetrics,
        threshold: float
    ) -> QualityCheckResult:
        """Validate completeness of the collection."""
        issues = []
        
        # Check overall required field completeness
        required_completeness = metrics.papers_with_all_required_fields / len(papers) if papers else 0
        
        if required_completeness < threshold:
            issues.append(QualityIssue(
                check_type=QualityCheckType.COMPLETENESS,
                level=QualityIssueLevel.WARNING,
                field=None,
                message=f"Only {required_completeness:.1%} of papers have all required fields",
                suggested_action=f"Review scraper implementation to ensure all required fields are extracted",
                details={'required_fields': self.REQUIRED_FIELDS}
            ))
        
        # Check specific field issues
        for field, score in metrics.field_completeness_scores.items():
            if field in self.REQUIRED_FIELDS and score < 0.95:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.COMPLETENESS,
                    level=QualityIssueLevel.CRITICAL if score < 0.8 else QualityIssueLevel.WARNING,
                    field=field,
                    message=f"Field '{field}' missing in {(1-score):.1%} of papers",
                    suggested_action=f"Check scraper extraction for '{field}' field",
                    details={'completeness_score': score}
                ))
        
        # Check important optional fields
        abstract_rate = metrics.papers_with_abstracts / len(papers) if papers else 0
        pdf_rate = metrics.papers_with_pdfs / len(papers) if papers else 0
        
        if abstract_rate < 0.5:
            issues.append(QualityIssue(
                check_type=QualityCheckType.COMPLETENESS,
                level=QualityIssueLevel.WARNING,
                field='abstract',
                message=f"Only {abstract_rate:.1%} of papers have abstracts",
                suggested_action="Consider enhancing scrapers to extract abstracts",
                details={'papers_with_abstracts': metrics.papers_with_abstracts}
            ))
        
        # Calculate overall score
        weights = {
            'required': 0.6,
            'abstract': 0.2,
            'pdf': 0.2
        }
        
        score = (
            weights['required'] * required_completeness +
            weights['abstract'] * abstract_rate +
            weights['pdf'] * pdf_rate
        )
        
        return QualityCheckResult(
            check_name="completeness_check",
            check_type=QualityCheckType.COMPLETENESS,
            passed=len([i for i in issues if i.level == QualityIssueLevel.CRITICAL]) == 0,
            score=score,
            issues=issues,
            metrics={
                'required_completeness': required_completeness,
                'abstract_completeness': abstract_rate,
                'pdf_completeness': pdf_rate,
                'field_scores': metrics.field_completeness_scores
            }
        )


class ConsistencyValidator:
    """Validates consistency of collected data."""
    
    def validate(
        self,
        papers: List[Dict[str, Any]],
        context: CollectionContext,
        metrics: CollectionQualityMetrics,
        threshold: float
    ) -> QualityCheckResult:
        """Validate data consistency."""
        issues = []
        
        # Check for duplicates
        seen_ids = set()
        seen_titles = set()
        duplicate_ids = []
        duplicate_titles = []
        
        for paper in papers:
            # Check paper_id duplicates
            paper_id = paper.get('paper_id')
            if paper_id:
                if paper_id in seen_ids:
                    duplicate_ids.append(paper_id)
                seen_ids.add(paper_id)
            
            # Check title duplicates (normalized)
            title = paper.get('title', '').lower().strip()
            if title:
                if title in seen_titles:
                    duplicate_titles.append(paper.get('title'))
                seen_titles.add(title)
        
        duplicate_rate = (len(duplicate_ids) + len(duplicate_titles)) / (2 * len(papers)) if papers else 0
        
        if duplicate_rate > 0.05:  # More than 5% duplicates
            issues.append(QualityIssue(
                check_type=QualityCheckType.CONSISTENCY,
                level=QualityIssueLevel.WARNING,
                field=None,
                message=f"Found {duplicate_rate:.1%} duplicate papers",
                suggested_action="Review deduplication logic in scrapers",
                details={
                    'duplicate_ids': duplicate_ids[:10],  # First 10
                    'duplicate_titles': duplicate_titles[:10]
                }
            ))
        
        # Check venue consistency
        venue_issues = self._check_venue_consistency(papers, context)
        issues.extend(venue_issues)
        
        # Check year consistency
        year_issues = self._check_year_consistency(papers, context)
        issues.extend(year_issues)
        
        # Calculate score
        consistency_score = 1.0 - (
            0.4 * duplicate_rate +
            0.3 * (len(venue_issues) / len(papers) if papers else 0) +
            0.3 * (len(year_issues) / len(papers) if papers else 0)
        )
        
        return QualityCheckResult(
            check_name="consistency_check",
            check_type=QualityCheckType.CONSISTENCY,
            passed=consistency_score >= threshold,
            score=max(0, consistency_score),
            issues=issues,
            metrics={
                'duplicate_rate': duplicate_rate,
                'venue_consistency_issues': len(venue_issues),
                'year_consistency_issues': len(year_issues)
            }
        )
    
    def _check_venue_consistency(
        self, 
        papers: List[Dict[str, Any]], 
        context: CollectionContext
    ) -> List[QualityIssue]:
        """Check if paper venues match requested venues."""
        issues = []
        requested_venues = set(v.lower() for v in context.venues_requested)
        
        if not requested_venues:
            return issues
        
        mismatched_papers = []
        for paper in papers[:100]:  # Check first 100 for performance
            paper_venue = paper.get('venue', '').lower()
            if paper_venue and not any(req in paper_venue for req in requested_venues):
                mismatched_papers.append({
                    'title': paper.get('title', 'Unknown'),
                    'venue': paper.get('venue'),
                    'expected': context.venues_requested
                })
        
        if mismatched_papers:
            issues.append(QualityIssue(
                check_type=QualityCheckType.CONSISTENCY,
                level=QualityIssueLevel.WARNING,
                field='venue',
                message=f"Found {len(mismatched_papers)} papers with unexpected venues",
                suggested_action="Verify venue extraction and filtering logic",
                details={'examples': mismatched_papers[:5]}
            ))
        
        return issues
    
    def _check_year_consistency(
        self,
        papers: List[Dict[str, Any]],
        context: CollectionContext
    ) -> List[QualityIssue]:
        """Check if paper years match requested years."""
        issues = []
        requested_years = set(context.years_requested)
        
        if not requested_years:
            return issues
        
        mismatched_papers = []
        for paper in papers:
            paper_year = paper.get('year')
            if paper_year and paper_year not in requested_years:
                mismatched_papers.append({
                    'title': paper.get('title', 'Unknown'),
                    'year': paper_year,
                    'expected': sorted(requested_years)
                })
        
        if mismatched_papers:
            issues.append(QualityIssue(
                check_type=QualityCheckType.CONSISTENCY,
                level=QualityIssueLevel.WARNING,
                field='year',
                message=f"Found {len(mismatched_papers)} papers with unexpected years",
                suggested_action="Verify year extraction and filtering logic",
                details={'examples': mismatched_papers[:5]}
            ))
        
        return issues


class AccuracyValidator:
    """Validates accuracy of collected data."""
    
    def validate(
        self,
        papers: List[Dict[str, Any]],
        metrics: CollectionQualityMetrics,
        threshold: float,
        custom_params: Dict[str, Any]
    ) -> QualityCheckResult:
        """Validate data accuracy."""
        issues = []
        
        # Validate temporal bounds
        temporal_issues = self._validate_temporal_bounds(papers, custom_params)
        issues.extend(temporal_issues)
        
        # Validate author names
        author_issues = self._validate_author_names(papers)
        issues.extend(author_issues)
        
        # Validate URLs
        url_issues = self._validate_urls(papers)
        issues.extend(url_issues)
        
        # Calculate accuracy score
        total_validations = len(papers) * 3  # 3 validation types
        total_issues = len(temporal_issues) + len(author_issues) + len(url_issues)
        accuracy_score = 1.0 - (total_issues / total_validations) if total_validations > 0 else 1.0
        
        return QualityCheckResult(
            check_name="accuracy_check",
            check_type=QualityCheckType.ACCURACY,
            passed=accuracy_score >= threshold,
            score=accuracy_score,
            issues=issues,
            metrics={
                'temporal_issues': len(temporal_issues),
                'author_issues': len(author_issues),
                'url_issues': len(url_issues),
                'accuracy_rate': accuracy_score
            }
        )
    
    def _validate_temporal_bounds(
        self,
        papers: List[Dict[str, Any]],
        custom_params: Dict[str, Any]
    ) -> List[QualityIssue]:
        """Validate paper years are within reasonable bounds."""
        issues = []
        current_year = datetime.now().year
        
        # Get bounds from config or use defaults
        min_year = custom_params.get('min_valid_year', 1950)
        max_year = custom_params.get('max_valid_year', current_year + 1)
        
        for paper in papers:
            year = paper.get('year')
            if not year:
                continue
                
            if year < min_year:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.WARNING,
                    field='year',
                    message=f"Paper '{paper.get('title', 'Unknown')[:50]}...' has year {year} before {min_year}",
                    suggested_action="Verify year extraction or check for data errors",
                    details={'paper_id': paper.get('paper_id'), 'year': year}
                ))
            elif year > max_year:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.ACCURACY,
                    level=QualityIssueLevel.WARNING,
                    field='year',
                    message=f"Paper '{paper.get('title', 'Unknown')[:50]}...' has future year {year}",
                    suggested_action="Verify if this is an early access paper",
                    details={'paper_id': paper.get('paper_id'), 'year': year}
                ))
        
        return issues
    
    def _validate_author_names(self, papers: List[Dict[str, Any]]) -> List[QualityIssue]:
        """Validate author name patterns as designed in revised journal."""
        issues = []
        
        # Patterns that indicate extraction errors
        suspicious_patterns = [
            re.compile(r'^\d+$'),  # Just numbers
            re.compile(r'^[A-Z]{2,}$'),  # All caps (except valid like "AI")
            re.compile(r'^\W+$'),  # Only special characters
            re.compile(r'^.{1}$'),  # Single character
            re.compile(r'\d{3,}'),  # Contains 3+ consecutive digits
            re.compile(r'^(and|et|al|der|van|von|de|la|le)$', re.IGNORECASE),  # Particles as names
        ]
        
        papers_checked = 0
        for paper in papers[:1000]:  # Limit to first 1000 for performance
            if not paper.get('authors'):
                continue
                
            papers_checked += 1
            paper_has_issues = False
            
            for author in paper['authors']:
                if not author or not author.strip():
                    if not paper_has_issues:
                        issues.append(QualityIssue(
                            check_type=QualityCheckType.ACCURACY,
                            level=QualityIssueLevel.WARNING,
                            field='authors',
                            message=f"Empty author in '{paper.get('title', 'Unknown')[:50]}...'",
                            suggested_action="Check author extraction logic",
                            details={'paper_id': paper.get('paper_id')}
                        ))
                        paper_has_issues = True
                    continue
                
                # Check suspicious patterns
                for pattern in suspicious_patterns:
                    if pattern.match(author.strip()):
                        if not paper_has_issues:
                            issues.append(QualityIssue(
                                check_type=QualityCheckType.ACCURACY,
                                level=QualityIssueLevel.WARNING,
                                field='authors',
                                message=f"Suspicious author '{author}' in '{paper.get('title', 'Unknown')[:30]}...'",
                                suggested_action="Verify author name extraction",
                                details={'paper_id': paper.get('paper_id'), 'author': author}
                            ))
                            paper_has_issues = True
                        break
        
        return issues
    
    def _validate_urls(self, papers: List[Dict[str, Any]]) -> List[QualityIssue]:
        """Validate URL formats."""
        issues = []
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        papers_with_urls = 0
        for paper in papers[:500]:  # Limit for performance
            pdf_urls = paper.get('pdf_urls', [])
            if not pdf_urls:
                continue
                
            papers_with_urls += 1
            for url in pdf_urls[:3]:  # Check first 3 URLs per paper
                if not url_pattern.match(url):
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.ACCURACY,
                        level=QualityIssueLevel.INFO,
                        field='pdf_urls',
                        message=f"Invalid URL format in '{paper.get('title', 'Unknown')[:30]}...'",
                        suggested_action="Verify URL extraction and formatting",
                        details={'paper_id': paper.get('paper_id'), 'url': url[:100]}
                    ))
                    break
        
        return issues


class CoverageValidator:
    """Validates collection coverage."""
    
    # Expected paper counts by venue (rough estimates)
    EXPECTED_PAPERS_PER_VENUE = {
        'neurips': 1500,
        'icml': 1000,
        'iclr': 800,
        'cvpr': 1600,
        'aaai': 1200,
        'ijcai': 700,
        'acl': 600,
        'emnlp': 400,
    }
    
    def validate(
        self,
        papers: List[Dict[str, Any]],
        context: CollectionContext,
        metrics: CollectionQualityMetrics,
        threshold: float
    ) -> QualityCheckResult:
        """Validate collection coverage."""
        issues = []
        
        # Estimate expected papers
        expected_total = 0
        for venue in context.venues_requested:
            venue_lower = venue.lower()
            expected = self.EXPECTED_PAPERS_PER_VENUE.get(venue_lower, 500)  # Default 500
            expected_per_year = expected
            expected_total += expected_per_year * len(context.years_requested)
        
        if expected_total > 0:
            coverage_rate = len(papers) / expected_total
            metrics.expected_papers = expected_total
            metrics.coverage_rate = coverage_rate
            
            if coverage_rate < threshold:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.COVERAGE,
                    level=QualityIssueLevel.WARNING,
                    field=None,
                    message=f"Collected {len(papers)} papers, expected ~{expected_total} ({coverage_rate:.1%} coverage)",
                    suggested_action="Check if scrapers are missing papers or if estimates need adjustment",
                    details={
                        'collected': len(papers),
                        'expected': expected_total,
                        'venues': context.venues_requested,
                        'years': context.years_requested
                    }
                ))
            
            # Check per-scraper performance
            for scraper, count in metrics.papers_by_scraper.items():
                if count == 0 and scraper in context.scrapers_used:
                    issues.append(QualityIssue(
                        check_type=QualityCheckType.COVERAGE,
                        level=QualityIssueLevel.CRITICAL,
                        field=None,
                        message=f"Scraper '{scraper}' returned no papers",
                        suggested_action=f"Check if {scraper} scraper is working correctly",
                        details={'scraper': scraper}
                    ))
        
        # Calculate score
        score = min(1.0, coverage_rate) if expected_total > 0 else 1.0
        
        return QualityCheckResult(
            check_name="coverage_check",
            check_type=QualityCheckType.COVERAGE,
            passed=len([i for i in issues if i.level == QualityIssueLevel.CRITICAL]) == 0,
            score=score,
            issues=issues,
            metrics={
                'collected': len(papers),
                'expected': expected_total,
                'coverage_rate': coverage_rate if expected_total > 0 else 1.0,
                'papers_by_scraper': metrics.papers_by_scraper
            }
        )
```

### 4. Collection Stage Registration (15 minutes)

**File**: `compute_forecast/quality/stages/collection/__init__.py`

```python
"""Collection stage quality checks."""

from compute_forecast.quality.core.registry import register_stage_checker
from .checker import CollectionQualityChecker
from .models import CollectionQualityMetrics, CollectionContext
from .validators import (
    CompletenessValidator,
    ConsistencyValidator,
    AccuracyValidator,
    CoverageValidator,
)

# Automatically register the collection checker when module is imported
register_stage_checker("collection", CollectionQualityChecker)

__all__ = [
    "CollectionQualityChecker",
    "CollectionQualityMetrics",
    "CollectionContext",
    "CompletenessValidator",
    "ConsistencyValidator", 
    "AccuracyValidator",
    "CoverageValidator",
]
```

### 5. Report Formatters (45 minutes)

**File**: `compute_forecast/quality/reports/formatters.py`

```python
import json
from typing import Dict, Any
from pathlib import Path

from compute_forecast.quality.core.interfaces import QualityReport, QualityIssueLevel
from compute_forecast.quality.core.hooks import _score_to_grade, _grade_to_color


class TextFormatter:
    """Format quality reports as human-readable text."""
    
    def format(self, report: QualityReport, verbose: bool = False) -> str:
        """Format report as text."""
        lines = []
        
        # Header
        lines.append(f"\nQuality Report: {report.stage.title()} Stage")
        lines.append("=" * 60)
        lines.append(f"File: {report.data_path}")
        lines.append(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Overall score
        grade = _score_to_grade(report.overall_score)
        lines.append(f"\nOverall Score: {report.overall_score:.2f} ({grade})")
        
        # Summary by check type
        lines.append("\nCheck Summary:")
        lines.append("-" * 40)
        
        for result in report.check_results:
            status = "✓" if result.passed else "✗"
            score_str = f"{result.score:.2f}"
            lines.append(f"{status} {result.check_name}: {score_str}")
            
            if verbose and result.issues:
                for issue in result.issues[:5]:  # First 5 issues
                    level_symbol = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}[issue.level.value]
                    lines.append(f"    {level_symbol} {issue.message}")
        
        # Issue summary
        critical_count = len(report.critical_issues)
        warning_count = len(report.warnings)
        
        lines.append(f"\nIssues Found:")
        lines.append(f"  Critical: {critical_count}")
        lines.append(f"  Warnings: {warning_count}")
        
        if verbose and (critical_count > 0 or warning_count > 0):
            lines.append("\nDetailed Issues:")
            lines.append("-" * 40)
            
            # Show critical issues first
            if critical_count > 0:
                lines.append("\nCRITICAL ISSUES:")
                for issue in report.critical_issues[:10]:
                    lines.append(f"\n  • {issue.message}")
                    lines.append(f"    Field: {issue.field or 'N/A'}")
                    lines.append(f"    Action: {issue.suggested_action}")
            
            # Show warnings
            if warning_count > 0 and verbose:
                lines.append("\nWARNINGS:")
                for issue in report.warnings[:10]:
                    lines.append(f"\n  • {issue.message}")
                    lines.append(f"    Action: {issue.suggested_action}")
        
        return "\n".join(lines)


class JSONFormatter:
    """Format quality reports as JSON."""
    
    def format(self, report: QualityReport, verbose: bool = False) -> str:
        """Format report as JSON."""
        data = {
            "stage": report.stage,
            "timestamp": report.timestamp.isoformat(),
            "data_path": str(report.data_path),
            "overall_score": report.overall_score,
            "grade": _score_to_grade(report.overall_score),
            "summary": {
                "critical_issues": len(report.critical_issues),
                "warnings": len(report.warnings),
                "checks_passed": sum(1 for r in report.check_results if r.passed),
                "checks_failed": sum(1 for r in report.check_results if not r.passed),
            },
            "check_results": []
        }
        
        for result in report.check_results:
            check_data = {
                "name": result.check_name,
                "type": result.check_type.value,
                "passed": result.passed,
                "score": result.score,
                "metrics": result.metrics
            }
            
            if verbose:
                check_data["issues"] = [
                    {
                        "level": issue.level.value,
                        "field": issue.field,
                        "message": issue.message,
                        "suggested_action": issue.suggested_action,
                        "details": issue.details
                    }
                    for issue in result.issues
                ]
            
            data["check_results"].append(check_data)
        
        return json.dumps(data, indent=2)


class MarkdownFormatter:
    """Format quality reports as Markdown."""
    
    def format(self, report: QualityReport, verbose: bool = False) -> str:
        """Format report as Markdown."""
        lines = []
        
        # Header
        lines.append(f"# Quality Report: {report.stage.title()} Stage")
        lines.append("")
        lines.append(f"**File:** `{report.data_path}`")
        lines.append(f"**Timestamp:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall score
        grade = _score_to_grade(report.overall_score)
        lines.append(f"## Overall Score: {report.overall_score:.2f} ({grade})")
        lines.append("")
        
        # Summary table
        lines.append("## Check Summary")
        lines.append("")
        lines.append("| Check | Type | Score | Status |")
        lines.append("|-------|------|-------|--------|")
        
        for result in report.check_results:
            status = "✅ Passed" if result.passed else "❌ Failed"
            lines.append(f"| {result.check_name} | {result.check_type.value} | {result.score:.2f} | {status} |")
        
        lines.append("")
        
        # Issues
        critical_count = len(report.critical_issues)
        warning_count = len(report.warnings)
        
        lines.append("## Issues Summary")
        lines.append("")
        lines.append(f"- **Critical Issues:** {critical_count}")
        lines.append(f"- **Warnings:** {warning_count}")
        lines.append("")
        
        if verbose and (critical_count > 0 or warning_count > 0):
            lines.append("## Detailed Issues")
            lines.append("")
            
            if critical_count > 0:
                lines.append("### Critical Issues")
                lines.append("")
                for i, issue in enumerate(report.critical_issues[:10], 1):
                    lines.append(f"{i}. **{issue.message}**")
                    lines.append(f"   - Field: `{issue.field or 'N/A'}`")
                    lines.append(f"   - Action: {issue.suggested_action}")
                    lines.append("")
            
            if warning_count > 0:
                lines.append("### Warnings")
                lines.append("")
                for i, issue in enumerate(report.warnings[:10], 1):
                    lines.append(f"{i}. {issue.message}")
                    lines.append(f"   - Action: {issue.suggested_action}")
                    lines.append("")
        
        return "\n".join(lines)


# Registry of formatters
FORMATTERS = {
    "text": TextFormatter(),
    "json": JSONFormatter(),
    "markdown": MarkdownFormatter(),
}


def format_report(report: QualityReport, format: str, verbose: bool = False) -> str:
    """Format a quality report in the specified format."""
    formatter = FORMATTERS.get(format)
    if not formatter:
        raise ValueError(f"Unknown format: {format}. Available: {list(FORMATTERS.keys())}")
    
    return formatter.format(report, verbose)
```

### 6. Integration with Collect Command (30 minutes)

**File**: Update `compute_forecast/cli/commands/collect.py`

Add quality check integration at the end of the collect command:

```python
# Add to imports
from compute_forecast.quality.core.hooks import run_post_command_quality_check

# Add parameter to main function
def main(
    # ... existing parameters ...
    skip_quality_check: bool = typer.Option(
        False,
        "--skip-quality-check",
        help="Skip automatic quality check after collection"
    ),
):
    # ... existing collection logic ...
    
    # After saving papers (around line 150)
    save_papers(all_papers, output_path, additional_metadata)
    
    # Run quality check
    if not skip_quality_check:
        console.print("\n[cyan]Running quality checks...[/cyan]")
        quality_report = run_post_command_quality_check(
            stage="collection",
            output_path=output_path,
            context={
                "venues": list(all_venues),
                "years": sorted(all_years),
                "total_papers": len(all_papers),
                "scrapers_used": list(set(p.source_scraper for p in all_papers)),
            }
        )
    
    # Final summary remains the same
```

### 7. Enhanced CLI Output (30 minutes)

**File**: Update `compute_forecast/cli/commands/quality.py`

Replace the basic `_print_text_report` with proper formatting:

```python
# Add to imports
from compute_forecast.quality.reports.formatters import format_report

# Replace _print_text_report function
def _print_text_report(report, verbose: bool):
    """Print formatted text report."""
    from compute_forecast.quality.reports.formatters import format_report
    
    formatted = format_report(report, "text", verbose)
    console.print(formatted)

# Update main function to handle all formats
def main(
    # ... existing parameters ...
):
    # ... existing logic ...
    
    # Output results section
    if output_format == "text":
        _print_text_report(report, verbose)
    else:
        formatted = format_report(report, output_format, verbose)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(formatted)
            console.print(f"[green]Report saved to {output_file}[/green]")
        else:
            console.print(formatted)
```

### 8. Testing (1 hour)

**File**: `tests/unit/quality/test_collection_checker.py`

```python
"""Test collection stage quality checks."""

import pytest
from pathlib import Path
import json
import tempfile
from datetime import datetime

from compute_forecast.quality import QualityRunner, QualityConfig
from compute_forecast.quality.stages.collection import CollectionQualityChecker


class TestCollectionQualityChecker:
    """Test collection quality checker."""
    
    @pytest.fixture
    def sample_collection_data(self):
        """Create sample collection data."""
        return {
            "collection_metadata": {
                "timestamp": datetime.now().isoformat(),
                "venues": ["neurips"],
                "years": [2024],
                "total_papers": 3,
                "scrapers_used": ["NeurIPSScraper"],
            },
            "papers": [
                {
                    "title": "Deep Learning Paper 1",
                    "authors": ["John Doe", "Jane Smith"],
                    "venue": "NeurIPS",
                    "year": 2024,
                    "abstract": "This paper presents...",
                    "pdf_urls": ["https://papers.nips.cc/paper/1.pdf"],
                    "paper_id": "neurips_2024_001",
                    "doi": "10.1234/neurips.2024.001",
                    "source_scraper": "NeurIPSScraper"
                },
                {
                    "title": "Machine Learning Paper 2",
                    "authors": ["Alice Johnson"],
                    "venue": "NeurIPS",
                    "year": 2024,
                    "abstract": "We propose a new method...",
                    "pdf_urls": [],
                    "paper_id": "neurips_2024_002",
                    "source_scraper": "NeurIPSScraper"
                },
                {
                    "title": "AI Research Paper 3",
                    "authors": ["Bob Wilson", "123"],  # Bad author
                    "venue": "NeurIPS",
                    "year": 2025,  # Future year
                    "paper_id": "neurips_2024_003",
                    "source_scraper": "NeurIPSScraper"
                }
            ]
        }
    
    @pytest.fixture
    def temp_data_file(self, sample_collection_data):
        """Create temporary data file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_collection_data, f)
            return Path(f.name)
    
    def test_collection_checker_registration(self):
        """Test that collection checker is registered."""
        # Import triggers registration
        import compute_forecast.quality.stages.collection
        
        runner = QualityRunner()
        stages = runner.registry.list_stages()
        assert "collection" in stages
    
    def test_completeness_check(self, temp_data_file):
        """Test completeness validation."""
        runner = QualityRunner()
        config = QualityConfig(stage="collection", verbose=True)
        
        report = runner.run_checks("collection", temp_data_file, config)
        
        # Find completeness check result
        completeness_result = next(
            r for r in report.check_results 
            if r.check_name == "completeness_check"
        )
        
        # Check that we detected missing abstracts and PDFs
        assert completeness_result.score < 1.0
        assert len(completeness_result.issues) > 0
        
        # Check metrics
        assert "field_scores" in completeness_result.metrics
        assert completeness_result.metrics["field_scores"]["abstract"] < 1.0
    
    def test_accuracy_check(self, temp_data_file):
        """Test accuracy validation."""
        runner = QualityRunner()
        config = QualityConfig(
            stage="collection",
            custom_params={"min_valid_year": 2020, "max_valid_year": 2024}
        )
        
        report = runner.run_checks("collection", temp_data_file, config)
        
        # Find accuracy check result
        accuracy_result = next(
            r for r in report.check_results 
            if r.check_name == "accuracy_check"
        )
        
        # Should detect future year and bad author name
        assert accuracy_result.score < 1.0
        assert len(accuracy_result.issues) >= 2
        
        # Check for specific issues
        issue_messages = [issue.message for issue in accuracy_result.issues]
        assert any("future year" in msg for msg in issue_messages)
        assert any("123" in msg for msg in issue_messages)  # Bad author
    
    def test_consistency_check(self, temp_data_file):
        """Test consistency validation."""
        runner = QualityRunner()
        config = QualityConfig(stage="collection")
        
        report = runner.run_checks("collection", temp_data_file, config)
        
        # Find consistency check result
        consistency_result = next(
            r for r in report.check_results 
            if r.check_name == "consistency_check"
        )
        
        # Should pass for this sample data
        assert consistency_result.passed
        assert consistency_result.score > 0.9
    
    def test_coverage_check(self, temp_data_file):
        """Test coverage validation."""
        runner = QualityRunner()
        config = QualityConfig(stage="collection")
        
        report = runner.run_checks("collection", temp_data_file, config)
        
        # Find coverage check result
        coverage_result = next(
            r for r in report.check_results 
            if r.check_name == "coverage_check"
        )
        
        # Should detect low coverage (3 papers vs expected ~1500)
        assert coverage_result.score < 0.1
        assert len(coverage_result.issues) > 0
        assert "expected" in coverage_result.metrics
    
    def test_report_formatting(self, temp_data_file):
        """Test report formatting."""
        from compute_forecast.quality.reports.formatters import format_report
        
        runner = QualityRunner()
        report = runner.run_checks("collection", temp_data_file)
        
        # Test text format
        text_output = format_report(report, "text", verbose=True)
        assert "Quality Report: Collection Stage" in text_output
        assert "Overall Score:" in text_output
        
        # Test JSON format
        json_output = format_report(report, "json", verbose=False)
        data = json.loads(json_output)
        assert data["stage"] == "collection"
        assert "overall_score" in data
        
        # Test Markdown format
        md_output = format_report(report, "markdown", verbose=True)
        assert "# Quality Report: Collection Stage" in md_output
        assert "| Check | Type | Score | Status |" in md_output
```

## Implementation Timeline

### Day 1 (4 hours)
1. **Collection Data Models** (30 min)
2. **Collection Checker Core** (90 min)
3. **Completeness & Consistency Validators** (90 min)
4. **Accuracy & Coverage Validators** (60 min)

### Day 2 (3 hours)
5. **Collection Stage Registration** (15 min)
6. **Report Formatters** (45 min)
7. **Collect Command Integration** (30 min)
8. **Enhanced CLI Output** (30 min)
9. **Testing & Debugging** (60 min)

### Day 3 (1 hour)
10. **Integration Testing** (30 min)
11. **Documentation Updates** (30 min)

## Success Criteria

1. **Functional Checks**: All four check types working correctly
2. **Accurate Scoring**: Scores reflect actual data quality
3. **Actionable Feedback**: Clear issues with suggested actions
4. **Performance**: Checks complete in <5s for 10K papers
5. **Integration**: Seamless with collect command
6. **Output Formats**: Text, JSON, and Markdown working

## Testing Strategy

1. **Unit Tests**: Each validator tested independently
2. **Integration Tests**: Full collection checker flow
3. **CLI Tests**: Command-line interface functionality
4. **Format Tests**: All output formats validated
5. **Performance Tests**: Large collection handling

## Risk Mitigation

1. **Performance**: Use sampling for expensive checks
2. **Memory**: Process papers in batches if needed
3. **Accuracy**: Conservative thresholds to avoid false positives
4. **Extensibility**: Clear patterns for adding new checks

## Future Enhancements

1. **Machine Learning**: Use ML to detect quality issues
2. **Historical Comparison**: Compare quality over time
3. **Custom Rules**: User-defined quality checks
4. **Batch Processing**: Quality checks for multiple files
5. **Detailed Reports**: PDF report generation

This plan provides a comprehensive implementation of collection-specific quality checks that will help ensure data quality throughout the pipeline.