"""Generic formatters for quality reports."""

import json

from .interfaces import QualityReport
from .formatters import ReportFormatter


class GenericTextFormatter(ReportFormatter):
    """Generic text formatter for quality reports."""

    def format_report(self, report: QualityReport, **kwargs) -> str:
        """Format report as human-readable text."""
        verbose = kwargs.get("verbose", False)
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"QUALITY REPORT: {report.stage.upper()} STAGE")
        lines.append("=" * 70)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Data Path: {report.data_path}")
        lines.append("")

        # Overall Score
        grade = self._score_to_grade(report.overall_score)
        lines.append(f"OVERALL QUALITY SCORE: {report.overall_score:.2f} ({grade})")
        lines.append("")

        # Summary by check type
        lines.append("QUALITY CHECKS SUMMARY:")
        lines.append("-" * 30)

        for result in report.check_results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            lines.append(f"{result.check_name.title():<20} {result.score:.2f} {status}")

        lines.append("")

        # Issues
        if report.critical_issues or report.warnings:
            lines.append("ISSUES FOUND:")
            lines.append("-" * 30)

            if report.critical_issues:
                lines.append("CRITICAL ISSUES:")
                for issue in report.critical_issues:
                    lines.append(f"  • {issue.message}")
                    if issue.suggested_action:
                        lines.append(f"    → {issue.suggested_action}")
                    if verbose and issue.details:
                        for key, value in issue.details.items():
                            lines.append(f"      {key}: {value}")
                lines.append("")

            if report.warnings:
                lines.append("WARNINGS:")
                for issue in report.warnings:
                    lines.append(f"  • {issue.message}")
                    if issue.suggested_action:
                        lines.append(f"    → {issue.suggested_action}")
                    if verbose and issue.details:
                        for key, value in issue.details.items():
                            lines.append(f"      {key}: {value}")
                lines.append("")

        # Detailed Metrics (if verbose)
        if verbose and any(result.metrics for result in report.check_results):
            lines.append("DETAILED METRICS:")
            lines.append("-" * 30)
            for result in report.check_results:
                if result.metrics:
                    lines.append(f"\n{result.check_name.title()}:")
                    for key, value in result.metrics.items():
                        if isinstance(value, dict):
                            lines.append(f"  {key}:")
                            for k, v in value.items():
                                lines.append(f"    {k}: {v}")
                        else:
                            lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.80:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.70:
            return "B-"
        elif score >= 0.65:
            return "C+"
        elif score >= 0.60:
            return "C"
        elif score >= 0.50:
            return "D"
        else:
            return "F"


class GenericJSONFormatter(ReportFormatter):
    """Generic JSON formatter for quality reports."""

    def format_report(self, report: QualityReport, **kwargs) -> str:
        """Format report as JSON."""
        data = {
            "report_info": {
                "stage": report.stage,
                "timestamp": report.timestamp.isoformat(),
                "data_path": str(report.data_path),
                "overall_score": report.overall_score,
                "grade": self._score_to_grade(report.overall_score),
            },
            "check_results": [
                {
                    "check_name": result.check_name,
                    "check_type": result.check_type.value,
                    "passed": result.passed,
                    "score": result.score,
                    "issues_count": len(result.issues),
                    "metrics": result.metrics,
                }
                for result in report.check_results
            ],
            "issues": {
                "critical": [
                    {
                        "check_type": issue.check_type.value,
                        "field": issue.field,
                        "message": issue.message,
                        "suggested_action": issue.suggested_action,
                        "details": issue.details,
                    }
                    for issue in report.critical_issues
                ],
                "warnings": [
                    {
                        "check_type": issue.check_type.value,
                        "field": issue.field,
                        "message": issue.message,
                        "suggested_action": issue.suggested_action,
                        "details": issue.details,
                    }
                    for issue in report.warnings
                ],
            },
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.80:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.70:
            return "B-"
        elif score >= 0.65:
            return "C+"
        elif score >= 0.60:
            return "C"
        elif score >= 0.50:
            return "D"
        else:
            return "F"


class GenericMarkdownFormatter(ReportFormatter):
    """Generic Markdown formatter for quality reports."""

    def format_report(self, report: QualityReport, **kwargs) -> str:
        """Format report as Markdown."""
        lines = []

        # Header
        lines.append(f"# {report.stage.title()} Quality Report")
        lines.append("")
        lines.append(f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Data Path:** `{report.data_path}`")
        lines.append("")

        # Overall Score
        grade = self._score_to_grade(report.overall_score)
        lines.append(f"## Overall Quality Score: {report.overall_score:.2f} ({grade})")
        lines.append("")

        # Summary table
        lines.append("## Quality Checks Summary")
        lines.append("")
        lines.append("| Check | Score | Status |")
        lines.append("|-------|-------|--------|")

        for result in report.check_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            lines.append(
                f"| {result.check_name.title()} | {result.score:.2f} | {status} |"
            )

        lines.append("")

        # Issues
        if report.critical_issues or report.warnings:
            lines.append("## Issues Found")
            lines.append("")

            if report.critical_issues:
                lines.append("### 🚨 Critical Issues")
                lines.append("")
                for issue in report.critical_issues:
                    lines.append(f"- **{issue.message}**")
                    if issue.suggested_action:
                        lines.append(f"  - *Action:* {issue.suggested_action}")
                lines.append("")

            if report.warnings:
                lines.append("### ⚠️ Warnings")
                lines.append("")
                for issue in report.warnings:
                    lines.append(f"- **{issue.message}**")
                    if issue.suggested_action:
                        lines.append(f"  - *Action:* {issue.suggested_action}")
                lines.append("")

        # Metrics Summary
        if any(result.metrics for result in report.check_results):
            lines.append("## Metrics Summary")
            lines.append("")

            for result in report.check_results:
                if result.metrics:
                    lines.append(f"### {result.check_name.title()}")
                    lines.append("")

                    # Try to format metrics nicely
                    for key, value in result.metrics.items():
                        if isinstance(value, (int, float)):
                            lines.append(
                                f"- **{key.replace('_', ' ').title()}:** {value}"
                            )
                        elif isinstance(value, dict) and len(value) <= 5:
                            lines.append(f"- **{key.replace('_', ' ').title()}:**")
                            for k, v in value.items():
                                lines.append(f"  - {k}: {v}")
                        else:
                            lines.append(
                                f"- **{key.replace('_', ' ').title()}:** *See detailed report*"
                            )
                    lines.append("")

        return "\n".join(lines)

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.80:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.70:
            return "B-"
        elif score >= 0.65:
            return "C+"
        elif score >= 0.60:
            return "C"
        elif score >= 0.50:
            return "D"
        else:
            return "F"
