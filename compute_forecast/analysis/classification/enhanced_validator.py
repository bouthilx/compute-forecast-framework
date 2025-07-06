"""Enhanced validation framework for classification accuracy testing."""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from ...data.models import Paper
from .validator import ClassificationValidator
from .enhanced_organizations import EnhancedOrganizationClassifier


@dataclass
class ValidationCase:
    """Test case for validation."""

    affiliation: str
    expected_type: str  # academic, industry, government, non_profit
    expected_org: str


class EnhancedClassificationValidator(ClassificationValidator):
    """Enhanced validator with comprehensive accuracy testing."""

    def __init__(self):
        """Initialize enhanced validator."""
        super().__init__()
        self.enhanced_classifier = EnhancedOrganizationClassifier()
        self.test_cases: List[ValidationCase] = []
        self._load_default_test_cases()

        # Try to load enhanced database if available
        try:
            import os

            config_path = os.path.join(
                os.path.dirname(__file__), "../../../config/organizations_enhanced.yaml"
            )
            if os.path.exists(config_path):
                self.enhanced_classifier.load_enhanced_database(config_path)
        except Exception:
            # If loading fails, continue with test organizations
            pass

    def _load_default_test_cases(self):
        """Load default validation test cases."""
        # Academic test cases
        self.test_cases.extend(
            [
                ValidationCase(
                    "MIT", "academic", "Massachusetts Institute of Technology"
                ),
                ValidationCase(
                    "Stanford University", "academic", "Stanford University"
                ),
                ValidationCase(
                    "University of Toronto", "academic", "University of Toronto"
                ),
                ValidationCase("ETH Zurich", "academic", "ETH Zurich"),
                ValidationCase(
                    "Cambridge University", "academic", "University of Cambridge"
                ),
            ]
        )

        # Industry test cases
        self.test_cases.extend(
            [
                ValidationCase("Google Research", "industry", "Google Research"),
                ValidationCase("Microsoft Research", "industry", "Microsoft Research"),
                ValidationCase("OpenAI", "industry", "OpenAI"),
                ValidationCase("DeepMind", "industry", "DeepMind"),
                ValidationCase("Meta AI", "industry", "Meta AI"),
            ]
        )

        # Government test cases
        self.test_cases.extend(
            [
                ValidationCase(
                    "National Science Foundation",
                    "government",
                    "National Science Foundation",
                ),
                ValidationCase("DARPA", "government", "DARPA"),
                ValidationCase(
                    "National Institutes of Health",
                    "government",
                    "National Institutes of Health",
                ),
            ]
        )

        # Non-profit test cases
        self.test_cases.extend(
            [
                ValidationCase(
                    "Allen Institute for AI", "non_profit", "Allen Institute for AI"
                ),
                ValidationCase(
                    "Chan Zuckerberg Initiative",
                    "non_profit",
                    "Chan Zuckerberg Initiative",
                ),
            ]
        )

    def load_test_cases(self, path: str) -> None:
        """Load validation test cases from file."""
        # Implementation would load test cases from a YAML or JSON file
        pass

    def validate(self, papers: List[Paper]) -> Dict[str, Any]:
        """Override parent validate method to include accuracy metrics."""
        # Get base validation results
        base_results = super().validate(papers)

        # Add enhanced accuracy metrics
        accuracy_metrics = self.validate_accuracy()

        # Merge results
        base_results.update(accuracy_metrics)

        # Add confidence distribution for real papers
        if papers:
            confidence_dist = self.validate_confidence_distribution(papers)
            base_results["confidence_distribution"] = confidence_dist

        return base_results

    def validate_accuracy(self) -> Dict[str, float]:
        """Run validation and return accuracy metrics."""
        results = {
            "overall_accuracy": 0.0,
            "academic_precision": 0.0,
            "industry_precision": 0.0,
            "government_precision": 0.0,
            "non_profit_precision": 0.0,
            "unknown_rate": 0.0,
            "type_accuracy": {},
            "confidence_metrics": {},
        }

        if not self.test_cases:
            return results

        # Track results by type
        type_correct = {"academic": 0, "industry": 0, "government": 0, "non_profit": 0}
        type_total = {"academic": 0, "industry": 0, "government": 0, "non_profit": 0}
        unknown_count = 0
        total_confidence = 0.0

        for test_case in self.test_cases:
            classification = self.enhanced_classifier.classify_with_confidence(
                test_case.affiliation
            )

            type_total[test_case.expected_type] += 1
            total_confidence += classification.confidence

            if classification.type.value == "unknown":
                unknown_count += 1
            elif classification.type.value == test_case.expected_type:
                type_correct[test_case.expected_type] += 1

        # Calculate metrics
        total_cases = len(self.test_cases)
        overall_correct = sum(type_correct.values())

        results["overall_accuracy"] = (
            overall_correct / total_cases if total_cases > 0 else 0.0
        )
        results["unknown_rate"] = (
            unknown_count / total_cases if total_cases > 0 else 0.0
        )
        results["average_confidence"] = (
            total_confidence / total_cases if total_cases > 0 else 0.0
        )

        # Calculate precision by type
        for org_type in ["academic", "industry", "government", "non_profit"]:
            if type_total[org_type] > 0:
                precision = type_correct[org_type] / type_total[org_type]
                results[f"{org_type}_precision"] = precision
                results["type_accuracy"][org_type] = {
                    "correct": type_correct[org_type],
                    "total": type_total[org_type],
                    "accuracy": precision,
                }

        return results

    def identify_failures(self) -> List[Tuple[ValidationCase, Any]]:
        """Identify cases where classification failed."""
        failures = []

        for test_case in self.test_cases:
            classification = self.enhanced_classifier.classify_with_confidence(
                test_case.affiliation
            )

            # Check for misclassification
            if classification.type.value != test_case.expected_type:
                failures.append((test_case, classification))

            # Check for low confidence on known organizations
            elif classification.confidence < 0.7:
                failures.append((test_case, classification))

        return failures

    def validate_confidence_distribution(self, papers: List[Paper]) -> Dict[str, Any]:
        """Analyze confidence score distribution across papers."""
        confidence_bins = {
            "high_confidence": 0,  # > 0.8
            "medium_confidence": 0,  # 0.5 - 0.8
            "low_confidence": 0,  # < 0.5
        }

        confidence_by_type = {
            "academic": [],
            "industry": [],
            "government": [],
            "non_profit": [],
            "unknown": [],
        }

        for paper in papers:
            for author in paper.authors:
                if hasattr(author, "affiliation"):
                    result = self.enhanced_classifier.classify_with_confidence(
                        author.affiliation
                    )

                    # Bin by confidence level
                    if result.confidence > 0.8:
                        confidence_bins["high_confidence"] += 1
                    elif result.confidence >= 0.5:
                        confidence_bins["medium_confidence"] += 1
                    else:
                        confidence_bins["low_confidence"] += 1

                    # Track by type
                    confidence_by_type[result.type.value].append(result.confidence)

        # Calculate average confidence by type
        avg_confidence_by_type = {}
        for org_type, confidences in confidence_by_type.items():
            if confidences:
                avg_confidence_by_type[org_type] = sum(confidences) / len(confidences)
            else:
                avg_confidence_by_type[org_type] = 0.0

        total_authors = sum(confidence_bins.values())

        return {
            "distribution": confidence_bins,
            "percentages": {
                k: v / total_authors if total_authors > 0 else 0.0
                for k, v in confidence_bins.items()
            },
            "average_by_type": avg_confidence_by_type,
            "total_authors": total_authors,
        }

    def generate_detailed_report(self, papers: List[Paper]) -> str:
        """Generate comprehensive validation report."""
        # Run accuracy validation on test cases
        accuracy_results = self.validate_accuracy()

        # Analyze confidence distribution on actual papers
        confidence_dist = self.validate_confidence_distribution(papers)

        # Identify failures
        failures = self.identify_failures()

        report = "=== Enhanced Classification Validation Report ===\n\n"

        # Accuracy section
        report += "## Accuracy on Test Cases\n"
        report += f"Overall Accuracy: {accuracy_results['overall_accuracy']:.1%}\n"
        report += f"Unknown Rate: {accuracy_results['unknown_rate']:.1%}\n"
        report += (
            f"Average Confidence: {accuracy_results['average_confidence']:.3f}\n\n"
        )

        # Type-specific accuracy
        report += "### Accuracy by Organization Type\n"
        for org_type, metrics in accuracy_results.get("type_accuracy", {}).items():
            report += f"- {org_type.title()}: {metrics['accuracy']:.1%} ({metrics['correct']}/{metrics['total']})\n"

        # Confidence distribution
        report += "\n## Confidence Distribution (Real Papers)\n"
        report += f"Total Authors Analyzed: {confidence_dist['total_authors']}\n"
        for level, percentage in confidence_dist["percentages"].items():
            report += f"- {level.replace('_', ' ').title()}: {percentage:.1%}\n"

        # Failures
        report += "\n## Classification Failures\n"
        report += f"Total Failures: {len(failures)}\n"
        if failures:
            report += "\nSample Failures:\n"
            for i, (test_case, result) in enumerate(failures[:5]):
                report += f"{i+1}. '{test_case.affiliation}'\n"
                report += f"   Expected: {test_case.expected_type}, Got: {result.type.value}\n"
                report += f"   Confidence: {result.confidence:.3f}\n"

        return report
