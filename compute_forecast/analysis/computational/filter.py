"""
Paper filtering and prioritization based on computational content.
"""

from typing import Dict, List, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from compute_forecast.data.models import Paper
from .analyzer import ComputationalAnalyzer
from .experimental_detector import ExperimentalDetector


class ComputationalFilter:
    """Filters and prioritizes papers based on computational content"""

    def __init__(self):
        self.analyzer = ComputationalAnalyzer()
        self.experimental_detector = ExperimentalDetector()

        self.thresholds = {
            "high_computational": 0.7,
            "medium_computational": 0.4,
            "low_computational": 0.2,
            "experimental_required": 0.3,
            "confidence_threshold": 0.6,
        }

        self.priority_weights = {
            "computational_richness": 0.4,
            "experimental_content": 0.3,
            "resource_specificity": 0.2,
            "implementation_details": 0.1,
        }

    def filter_papers_by_computational_content(
        self, papers: List[Paper]
    ) -> Dict[str, List[Paper]]:
        """Filter and prioritize papers based on computational content"""

        filtered_papers = {
            "high_priority": [],  # Rich computational content
            "medium_priority": [],  # Some computational content
            "low_priority": [],  # Minimal computational content
            "theoretical_only": [],  # No computational indicators
        }

        analysis_results = []

        for paper in papers:
            # Perform comprehensive analysis
            computational_analysis = self.analyzer.analyze(paper)
            experimental_analysis = (
                self.experimental_detector.detect_experimental_content(
                    self.analyzer.extract_paper_text(paper)
                )
            )

            # Calculate combined priority score
            priority_score = self._calculate_priority_score(
                computational_analysis, experimental_analysis
            )

            # Store analysis results
            analysis_result = {
                "computational_analysis": computational_analysis,
                "experimental_analysis": experimental_analysis,
                "priority_score": priority_score,
                "paper": paper,
            }
            analysis_results.append(analysis_result)

            # Add analysis to paper metadata
            paper.computational_analysis = computational_analysis

            # Categorize paper based on priority logic
            category = self._categorize_paper(
                computational_analysis, experimental_analysis
            )
            filtered_papers[category].append(paper)

        # Sort each category by priority score
        for category in filtered_papers:
            filtered_papers[category] = self._sort_papers_by_priority(
                filtered_papers[category], analysis_results
            )

        return filtered_papers

    def _calculate_priority_score(
        self,
        computational_analysis: Dict[str, Any],
        experimental_analysis: Dict[str, Any],
    ) -> float:
        """Calculate weighted priority score for resource analysis suitability"""

        # Computational richness component
        richness_score = computational_analysis["computational_richness"]

        # Experimental content component
        experimental_score = experimental_analysis["overall_experimental_score"]

        # Resource specificity component (based on extracted metrics)
        resource_specificity = self._calculate_resource_specificity(
            computational_analysis["resource_metrics"]
        )

        # Implementation details component
        implementation_score = experimental_analysis["implementation_score"]

        # Calculate weighted priority score
        priority_score = (
            self.priority_weights["computational_richness"] * richness_score
            + self.priority_weights["experimental_content"] * experimental_score
            + self.priority_weights["resource_specificity"] * resource_specificity
            + self.priority_weights["implementation_details"] * implementation_score
        )

        return min(priority_score, 1.0)

    def _calculate_resource_specificity(
        self, resource_metrics: Dict[str, Any]
    ) -> float:
        """Calculate how specific and detailed the resource information is"""

        if not resource_metrics:
            return 0.0

        specificity_scores = {
            "gpu_count": 0.2,
            "training_time": 0.2,
            "parameter_count": 0.2,
            "dataset_size": 0.15,
            "memory_usage": 0.15,
            "batch_size": 0.05,
            "learning_rate": 0.03,
            "epochs": 0.02,
        }

        total_specificity = 0.0
        for metric_type, weight in specificity_scores.items():
            if metric_type in resource_metrics:
                # More detailed metrics get higher scores
                metric_detail = len(resource_metrics[metric_type]["raw_matches"])
                normalized_detail = min(metric_detail / 3.0, 1.0)  # Cap at 3 mentions
                total_specificity += weight * normalized_detail

        return total_specificity

    def _categorize_paper(
        self,
        computational_analysis: Dict[str, Any],
        experimental_analysis: Dict[str, Any],
    ) -> str:
        """Categorize paper based on computational and experimental content"""

        richness = computational_analysis["computational_richness"]
        is_experimental = experimental_analysis["is_experimental_paper"]
        experimental_confidence = experimental_analysis["experimental_confidence"]

        # High priority: Rich computational content + experimental
        if (
            richness >= self.thresholds["high_computational"]
            and is_experimental
            and experimental_confidence >= self.thresholds["confidence_threshold"]
        ):
            return "high_priority"

        # Medium priority: Decent computational content + experimental
        elif richness >= self.thresholds["medium_computational"] and is_experimental:
            return "medium_priority"

        # Low priority: Some computational content OR experimental
        elif richness >= self.thresholds["low_computational"] or is_experimental:
            return "low_priority"

        # Theoretical only: Minimal computational indicators
        else:
            return "theoretical_only"

    def _sort_papers_by_priority(
        self, papers: List[Paper], analysis_results: List[Dict[str, Any]]
    ) -> List[Paper]:
        """Sort papers within category by priority score"""

        # Create mapping from paper ID to priority score
        paper_scores = {}
        for result in analysis_results:
            if result["paper"] in papers:
                # Use paper ID as key instead of Paper object (which is unhashable)
                paper_key = id(result["paper"])
                paper_scores[paper_key] = result["priority_score"]

        # Helper function to get priority score for a paper
        def get_priority_score(paper):
            return paper_scores.get(id(paper), 0.0)

        # Sort papers by priority score (descending)
        return sorted(papers, key=get_priority_score, reverse=True)

    def generate_computational_report(
        self, filtered_papers: Dict[str, List[Paper]]
    ) -> Dict[str, Any]:
        """Generate comprehensive report of computational content analysis"""

        total_papers = sum(len(papers) for papers in filtered_papers.values())

        if total_papers == 0:
            return {
                "total_papers_analyzed": 0,
                "error": "No papers provided for analysis",
            }

        # Calculate distribution statistics
        distribution = {}
        for category, papers in filtered_papers.items():
            distribution[category] = {
                "count": len(papers),
                "percentage": (len(papers) / total_papers * 100)
                if total_papers > 0
                else 0,
            }

        # Calculate resource projection quality
        projection_quality = {
            "high_confidence": len(filtered_papers["high_priority"]),
            "medium_confidence": len(filtered_papers["medium_priority"]),
            "low_confidence": len(filtered_papers["low_priority"]),
            "insufficient_data": len(filtered_papers["theoretical_only"]),
        }

        # Calculate quality metrics
        quality_score = self._calculate_dataset_quality_score(filtered_papers)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            filtered_papers, projection_quality
        )

        report = {
            "total_papers_analyzed": total_papers,
            "computational_distribution": distribution,
            "resource_projection_quality": projection_quality,
            "dataset_quality_score": quality_score,
            "recommendations": recommendations,
            "analysis_summary": {
                "suitable_for_projection": len(filtered_papers["high_priority"])
                + len(filtered_papers["medium_priority"]),
                "projection_confidence": self._calculate_projection_confidence(
                    filtered_papers
                ),
                "resource_data_richness": self._calculate_resource_richness(
                    filtered_papers
                ),
            },
        }

        return report

    def _calculate_dataset_quality_score(
        self, filtered_papers: Dict[str, List[Paper]]
    ) -> float:
        """Calculate overall quality score for resource projection dataset"""

        total_papers = sum(len(papers) for papers in filtered_papers.values())
        if total_papers == 0:
            return 0.0

        # Weight categories by their usefulness for projection
        category_weights = {
            "high_priority": 1.0,
            "medium_priority": 0.7,
            "low_priority": 0.3,
            "theoretical_only": 0.0,
        }

        weighted_score = 0.0
        for category, papers in filtered_papers.items():
            weight = category_weights[category]
            contribution = (len(papers) / total_papers) * weight
            weighted_score += contribution

        return weighted_score

    def _calculate_projection_confidence(
        self, filtered_papers: Dict[str, List[Paper]]
    ) -> float:
        """Calculate confidence in resource projections based on data quality"""

        high_quality_papers = len(filtered_papers["high_priority"])
        medium_quality_papers = len(filtered_papers["medium_priority"])
        total_useful_papers = high_quality_papers + medium_quality_papers
        total_papers = sum(len(papers) for papers in filtered_papers.values())

        if total_papers == 0:
            return 0.0

        # Confidence based on proportion of useful papers
        base_confidence = total_useful_papers / total_papers

        # Boost for having high-quality papers
        if high_quality_papers > 0:
            high_quality_boost = min(high_quality_papers / 10.0, 0.2)  # Up to 20% boost
            base_confidence += high_quality_boost

        return min(base_confidence, 1.0)

    def _calculate_resource_richness(
        self, filtered_papers: Dict[str, List[Paper]]
    ) -> float:
        """Calculate richness of resource information in dataset"""

        # Count papers with computational analysis data
        papers_with_analysis = 0
        total_papers = 0

        for papers in filtered_papers.values():
            for paper in papers:
                total_papers += 1
                if (
                    hasattr(paper, "computational_analysis")
                    and paper.computational_analysis
                    and paper.computational_analysis.get("resource_metrics")
                ):
                    papers_with_analysis += 1

        if total_papers == 0:
            return 0.0

        return papers_with_analysis / total_papers

    def _generate_recommendations(
        self,
        filtered_papers: Dict[str, List[Paper]],
        projection_quality: Dict[str, int],
    ) -> List[str]:
        """Generate actionable recommendations based on analysis results"""

        recommendations = []

        total_papers = sum(len(papers) for papers in filtered_papers.values())
        high_priority_count = len(filtered_papers["high_priority"])

        # Recommendations based on data quality
        if high_priority_count / total_papers > 0.3:
            recommendations.append(
                "Excellent computational content - proceed with resource projections"
            )
        elif high_priority_count / total_papers > 0.15:
            recommendations.append(
                "Good computational content - consider supplementing with additional high-quality papers"
            )
        else:
            recommendations.append(
                "Limited computational content - focus collection on implementation-heavy papers"
            )

        # Recommendations based on theoretical vs practical balance
        theoretical_ratio = len(filtered_papers["theoretical_only"]) / total_papers
        if theoretical_ratio > 0.5:
            recommendations.append(
                "High proportion of theoretical papers - target more experimental studies"
            )

        # Recommendations for improving projection accuracy
        if (
            projection_quality["insufficient_data"]
            > projection_quality["high_confidence"]
        ):
            recommendations.append(
                "Consider adding computational resource requirements to paper collection criteria"
            )

        return recommendations

    def export_filtered_results(
        self, filtered_papers: Dict[str, List[Paper]], output_path: str
    ) -> None:
        """Export filtered results to JSON file"""
        import json
        from datetime import datetime

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_papers": sum(len(papers) for papers in filtered_papers.values()),
            "categories": {},
        }

        for category, papers in filtered_papers.items():
            export_data["categories"][category] = {
                "count": len(papers),
                "papers": [paper.to_dict() for paper in papers],
            }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

    def get_top_papers_for_projection(
        self, filtered_papers: Dict[str, List[Paper]], max_papers: int = 50
    ) -> List[Paper]:
        """Get top papers most suitable for resource projection analysis"""

        # Combine high and medium priority papers
        candidate_papers = (
            filtered_papers["high_priority"] + filtered_papers["medium_priority"]
        )

        # Already sorted by priority, so just take the top N
        return candidate_papers[:max_papers]
