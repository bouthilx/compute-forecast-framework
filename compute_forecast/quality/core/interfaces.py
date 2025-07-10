"""Core interfaces and data structures for quality checking system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class QualityCheckType(Enum):
    """Types of quality checks."""
    
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    COVERAGE = "coverage"


class QualityIssueLevel(Enum):
    """Severity levels for quality issues."""
    
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class QualityIssue:
    """Represents a quality issue found during validation."""
    
    check_type: QualityCheckType
    level: QualityIssueLevel
    field: Optional[str]
    message: str
    suggested_action: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""
    
    check_name: str
    check_type: QualityCheckType
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Comprehensive quality report for a stage."""
    
    stage: str
    timestamp: datetime
    data_path: Path
    overall_score: float
    check_results: List[QualityCheckResult]
    
    @property
    def critical_issues(self) -> List[QualityIssue]:
        """Get all critical issues from all checks."""
        return [issue for result in self.check_results 
                for issue in result.issues 
                if issue.level == QualityIssueLevel.CRITICAL]
    
    @property
    def warnings(self) -> List[QualityIssue]:
        """Get all warnings from all checks."""
        return [issue for result in self.check_results 
                for issue in result.issues 
                if issue.level == QualityIssueLevel.WARNING]
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return len(self.critical_issues) > 0
    
    def get_score_by_type(self, check_type: QualityCheckType) -> float:
        """Get average score for a specific check type."""
        results = [r for r in self.check_results if r.check_type == check_type]
        return sum(r.score for r in results) / len(results) if results else 0.0


@dataclass
class QualityConfig:
    """Configuration for quality checks."""
    
    stage: str
    thresholds: Dict[str, float] = field(default_factory=dict)
    skip_checks: List[str] = field(default_factory=list)
    output_format: str = "text"
    verbose: bool = False
    custom_params: Dict[str, Any] = field(default_factory=dict)