"""Quality assessment framework for paper collections."""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .validators.sanity_checker import SanityChecker
from .validators.citation_validator import CitationValidator


class QualityAssessment:
    """Comprehensive quality assessment framework for paper collections."""

    def __init__(self):
        """Initialize quality assessment with validators and weights."""
        self.quality_weights = {
            "institutional_coverage": 0.25,
            "citation_reliability": 0.20,
            "computational_content": 0.20,
            "domain_balance": 0.15,
            "temporal_balance": 0.10,
            "venue_coverage": 0.10,
        }

        self.sanity_checker = SanityChecker()
        self.citation_validator = CitationValidator()

    def assess_collection_quality(
        self,
        papers: List[Dict[str, Any]],
        classification_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Comprehensive quality assessment of paper collection."""

        # Handle empty collection case
        if not papers:
            return {
                "overall_score": 0,
                "component_scores": {},
                "quality_flags": ["empty_collection"],
                "recommendations": [
                    {
                        "priority": "high",
                        "category": "collection",
                        "recommendation": "No papers collected",
                        "action": "collect_papers",
                    }
                ],
                "metadata": {
                    "total_papers": 0,
                    "assessment_timestamp": datetime.now().isoformat(),
                },
            }

        assessment: Dict[str, Any] = {
            "overall_score": 0,
            "component_scores": {},
            "quality_flags": [],
            "recommendations": [],
            "metadata": {
                "total_papers": len(papers),
                "assessment_timestamp": datetime.now().isoformat(),
            },
        }

        # Institutional coverage assessment
        academic_papers = [p for p in papers if p.get("benchmark_type") == "academic"]
        industry_papers = [p for p in papers if p.get("benchmark_type") == "industry"]

        academic_coverage = self.sanity_checker.check_institutional_coverage(
            academic_papers, "academic"
        )
        industry_coverage = self.sanity_checker.check_institutional_coverage(
            industry_papers, "industry"
        )

        institutional_score = (
            academic_coverage["coverage_percentage"]
            + industry_coverage["coverage_percentage"]
        ) / 2
        assessment["component_scores"]["institutional_coverage"] = institutional_score

        # Citation reliability assessment
        citation_validation = self.citation_validator.validate_citation_counts(papers)
        citation_reliability = (
            1.0 - (len(citation_validation["citation_issues"]) / len(papers))
            if papers
            else 0
        )
        assessment["component_scores"]["citation_reliability"] = citation_reliability

        # Computational content assessment
        if any("computational_analysis" in paper for paper in papers):
            high_comp = len(
                [
                    p
                    for p in papers
                    if p.get("computational_analysis", {}).get(
                        "computational_richness", 0
                    )
                    > 0.6
                ]
            )
            computational_score = high_comp / len(papers) if papers else 0
        else:
            computational_score = 0.5  # Default if not analyzed
        assessment["component_scores"]["computational_content"] = computational_score

        # Domain balance assessment
        domain_balance = self.sanity_checker.check_domain_balance(papers)
        domain_score = 1.0 - (
            len(domain_balance["quality_flags"]) / 10
        )  # Penalty for flags
        assessment["component_scores"]["domain_balance"] = max(domain_score, 0)

        # Temporal balance assessment
        temporal_balance = self.sanity_checker.check_temporal_balance(papers)
        temporal_score = 1.0 - (len(temporal_balance["quality_flags"]) / 6)  # 6 years
        assessment["component_scores"]["temporal_balance"] = max(temporal_score, 0)

        # Venue coverage assessment
        unique_venues = len(set(paper.get("venue", "Unknown") for paper in papers))
        venue_score = min(unique_venues / 30, 1.0)  # Expect 30+ unique venues
        assessment["component_scores"]["venue_coverage"] = venue_score

        # Calculate overall score
        overall_score = sum(
            score * self.quality_weights.get(component, 0)
            for component, score in assessment["component_scores"].items()
        )
        assessment["overall_score"] = overall_score

        # Generate recommendations
        assessment["recommendations"] = self.generate_quality_recommendations(
            assessment
        )

        return assessment

    def generate_quality_recommendations(
        self, assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on quality assessment."""

        recommendations = []
        scores = assessment["component_scores"]

        if scores.get("institutional_coverage", 0) < 0.5:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "institutional_coverage",
                    "recommendation": "Add papers from missing top-tier institutions",
                    "action": "manual_curation",
                }
            )

        if scores.get("citation_reliability", 0) < 0.8:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "citation_reliability",
                    "recommendation": "Re-validate citation counts for flagged papers",
                    "action": "citation_reverification",
                }
            )

        if scores.get("computational_content", 0) < 0.6:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "computational_content",
                    "recommendation": "Prioritize papers with higher computational richness",
                    "action": "content_filtering",
                }
            )

        if scores.get("domain_balance", 0) < 0.7:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "domain_balance",
                    "recommendation": "Address domain imbalances in collection",
                    "action": "domain_rebalancing",
                }
            )

        if scores.get("temporal_balance", 0) < 0.7:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "temporal_balance",
                    "recommendation": "Ensure adequate representation across all years",
                    "action": "temporal_rebalancing",
                }
            )

        if scores.get("venue_coverage", 0) < 0.6:
            recommendations.append(
                {
                    "priority": "low",
                    "category": "venue_coverage",
                    "recommendation": "Expand venue diversity in collection",
                    "action": "venue_expansion",
                }
            )

        return recommendations
