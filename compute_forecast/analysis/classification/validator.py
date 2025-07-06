from typing import List, Dict, Any
from ...data.models import Paper
from ...quality.validators.base import BaseValidator
from .paper_classifier import PaperClassifier
from ...core.logging import setup_logging


class ClassificationValidator(BaseValidator):
    """Validates organization classification accuracy and identifies edge cases"""

    def __init__(self):
        self.logger = setup_logging()
        self.classifier = PaperClassifier()

        # Known test cases for validation
        self.known_academic_affiliations = [
            "MIT Computer Science",
            "Stanford University AI Lab",
            "Carnegie Mellon University",
            "University of Toronto Vector Institute",
            "Mila - Quebec AI Institute",
        ]

        self.known_industry_affiliations = [
            "Google Research",
            "OpenAI",
            "Microsoft Research",
            "Meta AI Research",
            "DeepMind",
        ]

    def validate(self, papers: List[Paper]) -> Dict[str, Any]:
        """Validate classification on papers and return validation results"""

        validation_results = {
            "total_papers": len(papers),
            "classification_distribution": {},
            "confidence_analysis": {},
            "edge_cases": [],
            "validation_accuracy": {},
            "known_org_accuracy": {},
        }

        # Test classification distribution
        summary = self.classifier.get_classification_summary(papers)
        validation_results["classification_distribution"] = summary

        # Analyze confidence scores
        validation_results["confidence_analysis"] = self._analyze_confidence_scores(
            papers
        )

        # Identify edge cases
        validation_results["edge_cases"] = self.flag_edge_cases(papers)

        # Test on known organizations
        validation_results["known_org_accuracy"] = self.validate_known_papers()

        # Overall validation score
        validation_results["overall_score"] = self.get_validation_score(
            validation_results
        )

        return validation_results

    def get_validation_score(self, validation_result: Dict[str, Any]) -> float:
        """Get overall validation score"""

        # Weight different aspects of validation
        weights = {
            "known_org_accuracy": 0.4,
            "confidence_distribution": 0.3,
            "edge_case_handling": 0.3,
        }

        # Known organization accuracy
        known_acc = validation_result.get("known_org_accuracy", {})
        academic_acc = known_acc.get("academic_accuracy", 0.0)
        industry_acc = known_acc.get("industry_accuracy", 0.0)
        avg_known_acc = (academic_acc + industry_acc) / 2

        # Confidence distribution score (prefer higher average confidence)
        conf_analysis = validation_result.get("confidence_analysis", {})
        avg_confidence = conf_analysis.get("average_confidence", 0.0)

        # Edge case handling (prefer fewer edge cases needing manual review)
        dist = validation_result.get("classification_distribution", {})
        total_papers = dist.get("total_papers", 1)
        review_percentage = dist.get("review_percentage", 1.0)
        edge_case_score = max(0.0, 1.0 - review_percentage)

        # Calculate weighted score
        overall_score = (
            weights["known_org_accuracy"] * avg_known_acc
            + weights["confidence_distribution"] * avg_confidence
            + weights["edge_case_handling"] * edge_case_score
        )

        return min(1.0, overall_score)

    def validate_known_papers(self) -> Dict[str, float]:
        """Test classification on papers with known academic/industry status"""

        academic_correct = 0
        academic_total = len(self.known_academic_affiliations)

        industry_correct = 0
        industry_total = len(self.known_industry_affiliations)

        # Test academic affiliations
        for affiliation in self.known_academic_affiliations:
            classification = self.classifier.classify_affiliation(affiliation)
            if classification["type"] == "academic":
                academic_correct += 1

        # Test industry affiliations
        for affiliation in self.known_industry_affiliations:
            classification = self.classifier.classify_affiliation(affiliation)
            if classification["type"] == "industry":
                industry_correct += 1

        academic_accuracy = (
            academic_correct / academic_total if academic_total > 0 else 0.0
        )
        industry_accuracy = (
            industry_correct / industry_total if industry_total > 0 else 0.0
        )

        return {
            "academic_accuracy": academic_accuracy,
            "industry_accuracy": industry_accuracy,
            "academic_tested": academic_total,
            "academic_correct": academic_correct,
            "industry_tested": industry_total,
            "industry_correct": industry_correct,
        }

    def flag_edge_cases(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """Identify papers needing manual review"""

        edge_cases = []

        for i, paper in enumerate(papers):
            analysis = self.classifier.classify_paper_authorship(paper)

            # Flag low confidence classifications
            if analysis.confidence < 0.5:
                edge_cases.append(
                    {
                        "paper_index": i,
                        "paper_title": paper.title
                        if hasattr(paper, "title")
                        else f"Paper {i}",
                        "reason": "low_confidence",
                        "confidence": analysis.confidence,
                        "category": analysis.category,
                    }
                )

            # Flag papers with high unknown author percentage
            total_authors = (
                analysis.academic_count
                + analysis.industry_count
                + analysis.unknown_count
            )
            if total_authors > 0:
                unknown_percentage = analysis.unknown_count / total_authors
                if unknown_percentage > 0.5:
                    edge_cases.append(
                        {
                            "paper_index": i,
                            "paper_title": paper.title
                            if hasattr(paper, "title")
                            else f"Paper {i}",
                            "reason": "high_unknown_percentage",
                            "unknown_percentage": unknown_percentage,
                            "category": analysis.category,
                        }
                    )

            # Flag borderline cases (close to 25% threshold)
            if analysis.academic_count + analysis.industry_count > 0:
                industry_percentage = analysis.industry_count / (
                    analysis.academic_count + analysis.industry_count
                )
                if 0.2 <= industry_percentage <= 0.3:  # Within 5% of 25% threshold
                    edge_cases.append(
                        {
                            "paper_index": i,
                            "paper_title": paper.title
                            if hasattr(paper, "title")
                            else f"Paper {i}",
                            "reason": "borderline_threshold",
                            "industry_percentage": industry_percentage,
                            "category": analysis.category,
                        }
                    )

        return edge_cases

    def _analyze_confidence_scores(self, papers: List[Paper]) -> Dict[str, float]:
        """Analyze distribution of confidence scores"""

        confidences = []
        category_confidences = {
            "academic_eligible": [],
            "industry_eligible": [],
            "needs_manual_review": [],
        }

        for paper in papers:
            analysis = self.classifier.classify_paper_authorship(paper)
            confidences.append(analysis.confidence)
            category_confidences[analysis.category].append(analysis.confidence)

        if not confidences:
            return {"average_confidence": 0.0}

        result = {
            "average_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "low_confidence_count": sum(1 for c in confidences if c < 0.5),
            "high_confidence_count": sum(1 for c in confidences if c > 0.8),
        }

        # Add category-specific confidence averages
        for category, conf_list in category_confidences.items():
            if conf_list:
                result[f"{category}_avg_confidence"] = sum(conf_list) / len(conf_list)
            else:
                result[f"{category}_avg_confidence"] = 0.0

        return result

    def generate_validation_report(self, papers: List[Paper]) -> str:
        """Generate human-readable validation report"""

        validation_results = self.validate(papers)

        report = "=== Classification Validation Report ===\n\n"

        # Overall summary
        dist = validation_results["classification_distribution"]
        report += f"Total Papers Analyzed: {dist['total_papers']}\n"
        report += f"Academic Eligible: {dist['academic_eligible']} ({dist['academic_percentage']:.1%})\n"
        report += f"Industry Eligible: {dist['industry_eligible']} ({dist['industry_percentage']:.1%})\n"
        report += f"Needs Manual Review: {dist['needs_manual_review']} ({dist['review_percentage']:.1%})\n\n"

        # Confidence analysis
        conf = validation_results["confidence_analysis"]
        report += f"Average Confidence Score: {conf['average_confidence']:.3f}\n"
        report += f"Low Confidence Papers (<0.5): {conf['low_confidence_count']}\n"
        report += f"High Confidence Papers (>0.8): {conf['high_confidence_count']}\n\n"

        # Known organization accuracy
        known_acc = validation_results["known_org_accuracy"]
        report += f"Known Academic Organizations Accuracy: {known_acc['academic_accuracy']:.1%}\n"
        report += f"Known Industry Organizations Accuracy: {known_acc['industry_accuracy']:.1%}\n\n"

        # Edge cases
        edge_cases = validation_results["edge_cases"]
        report += f"Edge Cases Requiring Review: {len(edge_cases)}\n"
        if edge_cases:
            for case in edge_cases[:5]:  # Show first 5
                report += f"  - {case['paper_title'][:50]}... ({case['reason']})\n"

        report += (
            f"\nOverall Validation Score: {validation_results['overall_score']:.3f}\n"
        )

        return report
