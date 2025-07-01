"""Template coverage reporting for extraction analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict
import statistics

from .template_engine import ExtractionField, ExtractionTemplate


@dataclass
class FieldCoverageStats:
    """Statistics for a single field across extractions."""
    field: ExtractionField
    total_papers: int = 0
    papers_with_field: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    validation_failures: int = 0
    unique_values: set = field(default_factory=set)
    
    @property
    def coverage_percentage(self) -> float:
        """Percentage of papers that have this field."""
        if self.total_papers == 0:
            return 0.0
        return (self.papers_with_field / self.total_papers) * 100
    
    @property
    def average_confidence(self) -> float:
        """Average confidence score for this field."""
        if not self.confidence_scores:
            return 0.0
        return statistics.mean(self.confidence_scores)
    
    @property
    def confidence_std_dev(self) -> float:
        """Standard deviation of confidence scores."""
        if len(self.confidence_scores) < 2:
            return 0.0
        return statistics.stdev(self.confidence_scores)


@dataclass
class TemplateCoverageReport:
    """Coverage report for a specific template."""
    template_id: str
    template_name: str
    total_papers: int = 0
    successful_extractions: int = 0
    validation_failures: int = 0
    field_coverage: Dict[ExtractionField, FieldCoverageStats] = field(default_factory=dict)
    common_validation_issues: List[str] = field(default_factory=list)
    average_completeness: float = 0.0
    completeness_scores: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful extractions."""
        if self.total_papers == 0:
            return 0.0
        return (self.successful_extractions / self.total_papers) * 100
    
    def get_required_field_coverage(self, template: ExtractionTemplate) -> Dict[ExtractionField, float]:
        """Get coverage percentages for required fields."""
        coverage = {}
        for field in template.required_fields:
            if field in self.field_coverage:
                coverage[field] = self.field_coverage[field].coverage_percentage
            else:
                coverage[field] = 0.0
        return coverage
    
    def get_low_coverage_fields(self, threshold: float = 50.0) -> List[ExtractionField]:
        """Get fields with coverage below threshold."""
        low_coverage = []
        for field, stats in self.field_coverage.items():
            if stats.coverage_percentage < threshold:
                low_coverage.append(field)
        return low_coverage


class CoverageReporter:
    """Generate coverage reports for extraction templates."""
    
    def __init__(self):
        self.template_reports: Dict[str, TemplateCoverageReport] = {}
        self.extraction_results: List[Dict[str, Any]] = []
    
    def add_extraction_result(self, result: Dict[str, Any], template: ExtractionTemplate):
        """Add an extraction result to the reporter."""
        self.extraction_results.append(result)
        
        template_id = result['template_id']
        
        # Initialize report if needed
        if template_id not in self.template_reports:
            self.template_reports[template_id] = TemplateCoverageReport(
                template_id=template_id,
                template_name=template.template_name
            )
        
        report = self.template_reports[template_id]
        report.total_papers += 1
        
        # Update success/failure counts
        if result['validation_results']['passed']:
            report.successful_extractions += 1
        else:
            report.validation_failures += 1
            # Track common validation issues
            for error in result['validation_results']['errors']:
                if isinstance(error, dict) and 'message' in error:
                    report.common_validation_issues.append(error['message'])
        
        # Update completeness
        completeness = result.get('completeness', 0.0)
        report.completeness_scores.append(completeness)
        report.average_completeness = statistics.mean(report.completeness_scores)
        
        # Update field coverage
        extracted_fields = result.get('extracted_fields', {})
        confidence_scores = result.get('confidence_scores', {})
        
        # Initialize field stats for all template fields
        all_fields = set(template.required_fields + template.optional_fields)
        for field in all_fields:
            if field not in report.field_coverage:
                report.field_coverage[field] = FieldCoverageStats(field=field)
            
            stats = report.field_coverage[field]
            stats.total_papers += 1
            
            if field in extracted_fields:
                stats.papers_with_field += 1
                
                # Track confidence
                if field in confidence_scores:
                    stats.confidence_scores.append(confidence_scores[field])
                
                # Track unique values (limit to reasonable size)
                value = extracted_fields[field]
                if len(stats.unique_values) < 1000:  # Prevent memory issues
                    stats.unique_values.add(str(value))
            
            # Track validation failures for this field
            validation_errors = result['validation_results'].get('errors', [])
            for error in validation_errors:
                if isinstance(error, dict) and error.get('field') == field.value:
                    stats.validation_failures += 1
    
    def generate_report(self, template_id: str) -> Optional[TemplateCoverageReport]:
        """Generate coverage report for a specific template."""
        return self.template_reports.get(template_id)
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report across all templates."""
        summary = {
            "total_extractions": len(self.extraction_results),
            "templates_used": len(self.template_reports),
            "template_summaries": {}
        }
        
        for template_id, report in self.template_reports.items():
            summary["template_summaries"][template_id] = {
                "name": report.template_name,
                "total_papers": report.total_papers,
                "success_rate": f"{report.success_rate:.1f}%",
                "average_completeness": f"{report.average_completeness:.2f}",
                "validation_failures": report.validation_failures,
                "low_coverage_fields": [
                    f.value for f in report.get_low_coverage_fields()
                ]
            }
        
        return summary
    
    def get_field_insights(self, field: ExtractionField) -> Dict[str, Any]:
        """Get insights for a specific field across all templates."""
        insights = {
            "field": field.value,
            "usage_by_template": {},
            "overall_coverage": 0.0,
            "overall_confidence": 0.0,
            "common_values": []
        }
        
        total_papers = 0
        papers_with_field = 0
        all_confidence_scores = []
        value_frequency = defaultdict(int)
        
        for template_id, report in self.template_reports.items():
            if field in report.field_coverage:
                stats = report.field_coverage[field]
                
                total_papers += stats.total_papers
                papers_with_field += stats.papers_with_field
                all_confidence_scores.extend(stats.confidence_scores)
                
                insights["usage_by_template"][template_id] = {
                    "coverage": f"{stats.coverage_percentage:.1f}%",
                    "avg_confidence": f"{stats.average_confidence:.2f}",
                    "validation_failures": stats.validation_failures
                }
                
                # Track value frequency
                for value in stats.unique_values:
                    value_frequency[value] += 1
        
        # Calculate overall metrics
        if total_papers > 0:
            insights["overall_coverage"] = f"{(papers_with_field / total_papers * 100):.1f}%"
        
        if all_confidence_scores:
            insights["overall_confidence"] = f"{statistics.mean(all_confidence_scores):.2f}"
        
        # Get most common values
        if value_frequency:
            sorted_values = sorted(value_frequency.items(), key=lambda x: x[1], reverse=True)
            insights["common_values"] = [
                {"value": v, "count": c} for v, c in sorted_values[:10]
            ]
        
        return insights
    
    def export_detailed_report(self, template_id: str) -> str:
        """Export detailed coverage report as formatted text."""
        report = self.template_reports.get(template_id)
        if not report:
            return f"No report found for template {template_id}"
        
        lines = [
            f"# Template Coverage Report: {report.template_name}",
            f"Template ID: {report.template_id}",
            f"Total Papers Analyzed: {report.total_papers}",
            f"Success Rate: {report.success_rate:.1f}%",
            f"Average Completeness: {report.average_completeness:.2f}",
            "",
            "## Field Coverage Statistics",
            "-" * 80,
            f"{'Field':<30} {'Coverage':<10} {'Avg Conf':<10} {'Failures':<10}",
            "-" * 80
        ]
        
        # Sort fields by coverage
        sorted_fields = sorted(
            report.field_coverage.items(),
            key=lambda x: x[1].coverage_percentage,
            reverse=True
        )
        
        for field, stats in sorted_fields:
            lines.append(
                f"{field.value:<30} "
                f"{stats.coverage_percentage:>6.1f}% "
                f"{stats.average_confidence:>9.2f} "
                f"{stats.validation_failures:>9d}"
            )
        
        if report.common_validation_issues:
            lines.extend([
                "",
                "## Common Validation Issues",
                "-" * 80
            ])
            
            # Count issue frequency
            issue_counts = defaultdict(int)
            for issue in report.common_validation_issues:
                issue_counts[issue] += 1
            
            # Sort by frequency
            sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            
            for issue, count in sorted_issues[:10]:  # Top 10 issues
                lines.append(f"- {issue} (occurred {count} times)")
        
        return "\n".join(lines)