"""Report formatters for collection quality reports."""

import json
from typing import List

from compute_forecast.quality.core.interfaces import QualityReport
from .models import CollectionQualityMetrics


class CollectionReportFormatter:
    """Base formatter for collection quality reports."""

    def format_report(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> str:
        """Format a quality report with metrics."""
        raise NotImplementedError


class TextReportFormatter(CollectionReportFormatter):
    """Text format reporter for collection quality reports."""

    def format_report(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> str:
        """Format report as human-readable text."""
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("COLLECTION QUALITY REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Data Path: {report.data_path}")
        lines.append(f"Total Papers: {metrics.total_papers_collected}")
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
            lines.append(f"{result.check_name.title():<15} {result.score:.2f} {status}")

        lines.append("")

        # Detailed Metrics
        lines.append("DETAILED METRICS:")
        lines.append("-" * 30)

        # Completeness
        lines.append("Completeness:")
        lines.append(
            f"  Papers with all required fields: {metrics.papers_with_all_required_fields}/{metrics.total_papers_collected}"
        )
        lines.append(
            f"  Papers with abstracts: {metrics.papers_with_abstracts}/{metrics.total_papers_collected}"
        )
        lines.append(
            f"  Papers with PDFs: {metrics.papers_with_pdfs}/{metrics.total_papers_collected}"
        )
        lines.append(
            f"  Papers with DOIs: {metrics.papers_with_dois}/{metrics.total_papers_collected}"
        )
        lines.append("")

        # Consistency
        lines.append("Consistency:")
        lines.append(
            f"  Duplicate rate: {metrics.duplicate_rate:.1%} ({metrics.duplicate_count} papers)"
        )
        lines.append(f"  Venue consistency: {metrics.venue_consistency_score:.2f}")
        lines.append(f"  Year consistency: {metrics.year_consistency_score:.2f}")
        lines.append("")

        # Accuracy
        lines.append("Accuracy:")
        lines.append(
            f"  Valid years: {metrics.valid_years_count}/{metrics.total_papers_collected}"
        )
        lines.append(
            f"  Valid authors: {metrics.valid_authors_count}/{metrics.total_papers_collected}"
        )
        lines.append(
            f"  Valid URLs: {metrics.valid_urls_count}/{metrics.total_papers_collected}"
        )
        lines.append("")

        # Coverage
        lines.append("Coverage:")
        lines.append(f"  Coverage rate: {metrics.coverage_rate:.1%}")
        if metrics.papers_by_venue:
            lines.append("  Papers by venue:")
            for venue, count in sorted(metrics.papers_by_venue.items()):
                lines.append(f"    {venue}: {count}")
        if metrics.papers_by_scraper:
            lines.append("  Papers by scraper:")
            for scraper, count in metrics.papers_by_scraper.items():
                lines.append(f"    {scraper}: {count}")
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
                lines.append("")

            if report.warnings:
                lines.append("WARNINGS:")
                for issue in report.warnings:
                    lines.append(f"  • {issue.message}")
                    if issue.suggested_action:
                        lines.append(f"    → {issue.suggested_action}")

                    # Show duplicate summary statistics
                    if (
                        issue.field == "duplicate_summary"
                        and "cross_venue_statistics" in issue.details
                    ):
                        lines.append(
                            f"    Total duplicates: {issue.details['total_duplicates']}"
                        )
                        lines.append(
                            f"    Cross-venue: {issue.details['cross_venue_duplicates']}"
                        )
                        lines.append(
                            f"    Same-venue: {issue.details['same_venue_duplicates']}"
                        )
                        if issue.details["cross_venue_statistics"]:
                            lines.append("    Cross-venue duplicate rates:")
                            for stat in issue.details["cross_venue_statistics"]:
                                lines.append(f"      - {stat}")

                    # Show author issues with details
                    elif (
                        issue.field == "author_missing_name"
                        and "author_data" in issue.details
                    ):
                        lines.append(
                            f'    Paper: "{issue.details.get("paper_title", "Unknown")}"'
                        )
                        lines.append(f"    Author data: {issue.details['author_data']}")
                        if len(issue.details.get("all_authors", [])) <= 5:
                            lines.append(
                                f"    All authors: {issue.details.get('all_authors', [])}"
                            )

                    # Show duplicate details if available
                    elif (
                        issue.field == "duplicates"
                        and "paper_1" in issue.details
                        and "paper_2" in issue.details
                    ):
                        p1 = issue.details["paper_1"]
                        p2 = issue.details["paper_2"]
                        lines.append(f'    Paper 1: "{p1["title"]}"')
                        lines.append(f"             {p1['venue']} ({p1['year']})")
                        lines.append(f'    Paper 2: "{p2["title"]}"')
                        lines.append(f"             {p2['venue']} ({p2['year']})")
                        lines.append(
                            f"    Detection: {issue.details.get('detection_method', 'Unknown')}"
                        )
                lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 30)
        recommendations = self._generate_recommendations(report, metrics)
        for rec in recommendations:
            lines.append(f"  • {rec}")

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

    def _generate_recommendations(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> List[str]:
        """Generate recommendations based on quality results."""
        recommendations = []

        # Completeness recommendations
        if (
            metrics.papers_with_all_required_fields
            < metrics.total_papers_collected * 0.9
        ):
            recommendations.append(
                "Improve extraction of required fields (title, authors, venue, year)"
            )

        if metrics.papers_with_abstracts < metrics.total_papers_collected * 0.7:
            recommendations.append("Enhance abstract extraction across scrapers")

        if metrics.papers_with_pdfs < metrics.total_papers_collected * 0.5:
            recommendations.append("Improve PDF URL extraction and validation")

        # Consistency recommendations
        if metrics.duplicate_rate > 0.05:
            recommendations.append("Implement duplicate detection and removal")

        if metrics.venue_consistency_score < 0.8:
            recommendations.append("Standardize venue name formats across scrapers")

        # Accuracy recommendations
        if metrics.valid_years_count < metrics.total_papers_collected * 0.9:
            recommendations.append("Improve year extraction and validation")

        if metrics.valid_authors_count < metrics.total_papers_collected * 0.8:
            recommendations.append("Enhance author name extraction and formatting")

        # Coverage recommendations
        if metrics.coverage_rate < 0.8:
            recommendations.append("Review collection strategy to improve coverage")

        if len(metrics.papers_by_scraper) == 1:
            recommendations.append(
                "Consider using multiple scrapers for better coverage"
            )

        # Critical issues
        critical_count = len(report.critical_issues)
        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical issues immediately"
            )

        if not recommendations:
            recommendations.append(
                "Quality looks good! Consider minor optimizations based on warnings."
            )

        return recommendations


class JSONReportFormatter(CollectionReportFormatter):
    """JSON format reporter for collection quality reports."""

    def format_report(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> str:
        """Format report as JSON."""
        data = {
            "report_info": {
                "stage": report.stage,
                "timestamp": report.timestamp.isoformat(),
                "data_path": str(report.data_path),
                "overall_score": report.overall_score,
                "grade": self._score_to_grade(report.overall_score),
            },
            "metrics": {
                "total_papers": metrics.total_papers_collected,
                "completeness": {
                    "papers_with_all_required_fields": metrics.papers_with_all_required_fields,
                    "papers_with_abstracts": metrics.papers_with_abstracts,
                    "papers_with_pdfs": metrics.papers_with_pdfs,
                    "papers_with_dois": metrics.papers_with_dois,
                    "field_completeness_scores": metrics.field_completeness_scores,
                },
                "consistency": {
                    "duplicate_count": metrics.duplicate_count,
                    "duplicate_rate": metrics.duplicate_rate,
                    "venue_consistency_score": metrics.venue_consistency_score,
                    "year_consistency_score": metrics.year_consistency_score,
                },
                "accuracy": {
                    "valid_years_count": metrics.valid_years_count,
                    "valid_authors_count": metrics.valid_authors_count,
                    "valid_urls_count": metrics.valid_urls_count,
                    "accuracy_scores": metrics.accuracy_scores,
                },
                "coverage": {
                    "coverage_rate": metrics.coverage_rate,
                    "papers_by_venue": metrics.papers_by_venue,
                    "papers_by_scraper": metrics.papers_by_scraper,
                    "scraper_success_rates": metrics.scraper_success_rates,
                },
            },
            "check_results": [
                {
                    "check_name": result.check_name,
                    "check_type": result.check_type.value,
                    "passed": result.passed,
                    "score": result.score,
                    "issues_count": len(result.issues),
                }
                for result in report.check_results
            ],
            "issues": {
                "critical": [
                    {
                        "field": issue.field,
                        "message": issue.message,
                        "suggested_action": issue.suggested_action,
                        "details": issue.details,
                    }
                    for issue in report.critical_issues
                ],
                "warnings": [
                    {
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


class MarkdownReportFormatter(CollectionReportFormatter):
    """Markdown format reporter for collection quality reports."""

    def format_report(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> str:
        """Format report as Markdown."""
        lines = []

        # Header
        lines.append("# Collection Quality Report")
        lines.append("")
        lines.append(f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Data Path:** `{report.data_path}`")
        lines.append(f"**Total Papers:** {metrics.total_papers_collected}")
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

        # Detailed Metrics
        lines.append("## Detailed Metrics")
        lines.append("")

        # Completeness
        lines.append("### Completeness")
        lines.append("")
        lines.append("| Metric | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        total = metrics.total_papers_collected
        if total > 0:
            lines.append(
                f"| Papers with all required fields | {metrics.papers_with_all_required_fields} | {metrics.papers_with_all_required_fields / total * 100:.1f}% |"
            )
            lines.append(
                f"| Papers with abstracts | {metrics.papers_with_abstracts} | {metrics.papers_with_abstracts / total * 100:.1f}% |"
            )
            lines.append(
                f"| Papers with PDFs | {metrics.papers_with_pdfs} | {metrics.papers_with_pdfs / total * 100:.1f}% |"
            )
            lines.append(
                f"| Papers with DOIs | {metrics.papers_with_dois} | {metrics.papers_with_dois / total * 100:.1f}% |"
            )
        else:
            lines.append("| No papers to analyze | - | - |")
        lines.append("")

        # Consistency
        lines.append("### Consistency")
        lines.append("")
        lines.append(
            f"- **Duplicate Rate:** {metrics.duplicate_rate:.1%} ({metrics.duplicate_count} papers)"
        )
        lines.append(f"- **Venue Consistency:** {metrics.venue_consistency_score:.2f}")
        lines.append(f"- **Year Consistency:** {metrics.year_consistency_score:.2f}")
        lines.append("")

        # Accuracy
        lines.append("### Accuracy")
        lines.append("")
        lines.append("| Metric | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        if total > 0:
            lines.append(
                f"| Valid years | {metrics.valid_years_count} | {metrics.valid_years_count / total * 100:.1f}% |"
            )
            lines.append(
                f"| Valid authors | {metrics.valid_authors_count} | {metrics.valid_authors_count / total * 100:.1f}% |"
            )
            lines.append(
                f"| Valid URLs | {metrics.valid_urls_count} | {metrics.valid_urls_count / total * 100:.1f}% |"
            )
        else:
            lines.append("| No papers to analyze | - | - |")
        lines.append("")

        # Coverage
        lines.append("### Coverage")
        lines.append("")
        lines.append(f"- **Coverage Rate:** {metrics.coverage_rate:.1%}")
        if metrics.papers_by_venue:
            lines.append("")
            lines.append("**Papers by Venue:**")
            lines.append("")
            for venue, count in sorted(metrics.papers_by_venue.items()):
                lines.append(f"- {venue}: {count}")
        if metrics.papers_by_scraper:
            lines.append("")
            lines.append("**Papers by Scraper:**")
            lines.append("")
            for scraper, count in metrics.papers_by_scraper.items():
                lines.append(f"- {scraper}: {count}")
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

                    # Show duplicate summary statistics
                    if (
                        issue.field == "duplicate_summary"
                        and "cross_venue_statistics" in issue.details
                    ):
                        lines.append(
                            f"  - **Total duplicates:** {issue.details['total_duplicates']}"
                        )
                        lines.append(
                            f"  - **Cross-venue:** {issue.details['cross_venue_duplicates']}"
                        )
                        lines.append(
                            f"  - **Same-venue:** {issue.details['same_venue_duplicates']}"
                        )
                        if issue.details["cross_venue_statistics"]:
                            lines.append("  - **Cross-venue duplicate rates:**")
                            for stat in issue.details["cross_venue_statistics"]:
                                lines.append(f"    - {stat}")

                    # Show duplicate details if available
                    elif (
                        issue.field == "duplicates"
                        and "paper_1" in issue.details
                        and "paper_2" in issue.details
                    ):
                        p1 = issue.details["paper_1"]
                        p2 = issue.details["paper_2"]
                        lines.append(f'  - **Paper 1:** "{p1["title"]}"')
                        lines.append(f"    - {p1['venue']} ({p1['year']})")
                        lines.append(f'  - **Paper 2:** "{p2["title"]}"')
                        lines.append(f"    - {p2['venue']} ({p2['year']})")
                        lines.append(
                            f"  - **Detection method:** {issue.details.get('detection_method', 'Unknown')}"
                        )
                lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        recommendations = self._generate_recommendations(report, metrics)
        for rec in recommendations:
            lines.append(f"- {rec}")

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

    def _generate_recommendations(
        self, report: QualityReport, metrics: CollectionQualityMetrics
    ) -> List[str]:
        """Generate recommendations based on quality results."""
        recommendations = []

        # Completeness recommendations
        if (
            metrics.papers_with_all_required_fields
            < metrics.total_papers_collected * 0.9
        ):
            recommendations.append(
                "Improve extraction of required fields (title, authors, venue, year)"
            )

        if metrics.papers_with_abstracts < metrics.total_papers_collected * 0.7:
            recommendations.append("Enhance abstract extraction across scrapers")

        if metrics.papers_with_pdfs < metrics.total_papers_collected * 0.5:
            recommendations.append("Improve PDF URL extraction and validation")

        # Consistency recommendations
        if metrics.duplicate_rate > 0.05:
            recommendations.append("Implement duplicate detection and removal")

        if metrics.venue_consistency_score < 0.8:
            recommendations.append("Standardize venue name formats across scrapers")

        # Accuracy recommendations
        if metrics.valid_years_count < metrics.total_papers_collected * 0.9:
            recommendations.append("Improve year extraction and validation")

        if metrics.valid_authors_count < metrics.total_papers_collected * 0.8:
            recommendations.append("Enhance author name extraction and formatting")

        # Coverage recommendations
        if metrics.coverage_rate < 0.8:
            recommendations.append("Review collection strategy to improve coverage")

        if len(metrics.papers_by_scraper) == 1:
            recommendations.append(
                "Consider using multiple scrapers for better coverage"
            )

        # Critical issues
        critical_count = len(report.critical_issues)
        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical issues immediately"
            )

        if not recommendations:
            recommendations.append(
                "Quality looks good! Consider minor optimizations based on warnings."
            )

        return recommendations
