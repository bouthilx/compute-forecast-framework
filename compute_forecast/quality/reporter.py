"""Quality reporting system for generating assessment reports."""

from typing import Dict, List, Any
from datetime import datetime


class QualityReporter:
    """Automated reporting and issue flagging system."""

    def generate_milestone1_report(
        self,
        papers: List[Dict[str, Any]],
        quality_assessment: Dict[str, Any],
        collection_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive Milestone 1 completion report."""

        report = {
            "milestone": "Milestone 1: Paper Collection",
            "completion_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_papers_collected": len(papers),
                "academic_papers": len(
                    [p for p in papers if p.get("benchmark_type") == "academic"]
                ),
                "industry_papers": len(
                    [p for p in papers if p.get("benchmark_type") == "industry"]
                ),
                "overall_quality_score": quality_assessment["overall_score"],
                "collection_success": quality_assessment["overall_score"] > 0.7,
            },
            "detailed_metrics": quality_assessment,
            "collection_statistics": collection_stats,
            "next_steps": self.generate_next_steps(quality_assessment),
            "files_generated": [
                "academic_benchmark_papers.json",
                "industry_benchmark_papers.json",
                "quality_assessment_report.json",
                "collection_metadata.json",
            ],
        }

        return report

    def generate_next_steps(self, quality_assessment: Dict[str, Any]) -> List[str]:
        """Generate recommended next steps based on quality assessment."""

        next_steps = []
        overall_score = quality_assessment["overall_score"]

        if overall_score > 0.8:
            next_steps.append("Proceed to Milestone 2: Extraction Pipeline Development")
        elif overall_score > 0.6:
            next_steps.extend(
                [
                    "Address quality recommendations before proceeding",
                    "Consider targeted manual curation for critical gaps",
                ]
            )
        else:
            next_steps.extend(
                [
                    "Significant quality issues identified - recommend collection review",
                    "Focus on institutional coverage and computational content improvements",
                ]
            )

        return next_steps

    def generate_quality_summary(
        self, quality_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate concise quality summary for quick review."""

        scores = quality_assessment["component_scores"]

        summary = {
            "overall_grade": self._get_grade(quality_assessment["overall_score"]),
            "component_grades": {
                component: self._get_grade(score) for component, score in scores.items()
            },
            "critical_issues": [
                rec
                for rec in quality_assessment["recommendations"]
                if rec["priority"] == "high"
            ],
            "total_recommendations": len(quality_assessment["recommendations"]),
        }

        return summary

    def _get_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def generate_issue_report(
        self, quality_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed issue report for remediation."""

        issues: Dict[str, List[Dict[str, Any]]] = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
        }

        for recommendation in quality_assessment["recommendations"]:
            priority = recommendation["priority"]
            issues[f"{priority}_priority"].append(recommendation)

        return {
            "issue_summary": {
                "total_issues": len(quality_assessment["recommendations"]),
                "high_priority_count": len(issues["high_priority"]),
                "medium_priority_count": len(issues["medium_priority"]),
                "low_priority_count": len(issues["low_priority"]),
            },
            "issues_by_priority": issues,
            "remediation_timeline": self._estimate_remediation_time(issues),
        }

    def _estimate_remediation_time(
        self, issues: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Estimate time required for issue remediation."""

        high_count = len(issues["high_priority"])
        medium_count = len(issues["medium_priority"])
        low_count = len(issues["low_priority"])

        # Rough estimates in hours
        estimated_hours = (high_count * 4) + (medium_count * 2) + (low_count * 1)

        if estimated_hours <= 4:
            timeline = "Same day"
        elif estimated_hours <= 16:
            timeline = "1-2 days"
        elif estimated_hours <= 40:
            timeline = "1 week"
        else:
            timeline = "Multiple weeks"

        return {
            "estimated_hours": estimated_hours,
            "timeline": timeline,
            "recommendation": "High priority issues should be addressed first",
        }
