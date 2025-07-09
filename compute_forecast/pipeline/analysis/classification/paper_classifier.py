from typing import Dict, List, Any
from collections import defaultdict
from ..base import BaseAnalyzer
from ...metadata_collection.models import Paper, AuthorshipAnalysis
from .organizations import OrganizationDatabase
from .affiliation_parser import AffiliationParser
from ....core.logging import setup_logging


class PaperClassifier(BaseAnalyzer):
    """Classifies papers as academic/industry eligible based on author affiliations"""

    def __init__(self):
        self.logger = setup_logging()
        self.org_db = OrganizationDatabase()
        self.affiliation_parser = AffiliationParser()

    def analyze(self, paper: Paper) -> AuthorshipAnalysis:
        """Main analysis method required by BaseAnalyzer"""
        return self.classify_paper_authorship(paper)

    def get_confidence_score(self, analysis_result: AuthorshipAnalysis) -> float:
        """Get confidence score for analysis result"""
        return analysis_result.confidence

    def classify_paper_authorship(
        self, paper: Paper, confidence_threshold: float = 0.7
    ) -> AuthorshipAnalysis:
        """Classify paper as academic/industry eligible with confidence"""

        authors = paper.authors if hasattr(paper, "authors") and paper.authors else []
        academic_count = 0
        industry_count = 0
        unknown_count = 0

        author_details = []

        for author in authors:
            affiliation = author.affiliation if hasattr(author, "affiliation") else ""
            name = author.name if hasattr(author, "name") else ""

            affiliation_classification = self.affiliation_parser.classify_affiliation(
                affiliation
            )

            author_details.append(
                {
                    "name": name,
                    "affiliation": affiliation,
                    "type": affiliation_classification["type"],
                    "confidence": affiliation_classification["confidence"],
                    "matched_organization": affiliation_classification.get(
                        "matched_organization"
                    ),
                }
            )

            if affiliation_classification["type"] == "academic":
                academic_count += 1
            elif affiliation_classification["type"] == "industry":
                industry_count += 1
            else:
                unknown_count += 1

        classification_result = self._make_final_classification(
            academic_count, industry_count, unknown_count, author_details
        )

        # Create AuthorshipAnalysis object
        return AuthorshipAnalysis(
            category=classification_result["category"],
            academic_count=classification_result["academic_count"],
            industry_count=classification_result["industry_count"],
            unknown_count=classification_result["unknown_count"],
            confidence=classification_result["confidence"],
            author_details=classification_result["author_details"],
        )

    def _make_final_classification(
        self,
        academic_count: int,
        industry_count: int,
        unknown_count: int,
        author_details: List[Dict],
    ) -> Dict:
        """Apply 25% threshold rule with confidence scoring"""
        total_classified = academic_count + industry_count

        if total_classified == 0:
            return {
                "category": "needs_manual_review",
                "reason": "all_unknown_affiliations",
                "confidence": 0.0,
                "academic_count": academic_count,
                "industry_count": industry_count,
                "unknown_count": unknown_count,
                "author_details": author_details,
            }

        industry_percentage = industry_count / total_classified
        academic_percentage = academic_count / total_classified

        # Classification logic: <25% industry = academic eligible
        if industry_percentage < 0.25:
            category = "academic_eligible"
            confidence = self._calculate_confidence(
                academic_percentage, author_details, "academic"
            )
        elif academic_percentage < 0.25:
            category = "industry_eligible"
            confidence = self._calculate_confidence(
                industry_percentage, author_details, "industry"
            )
        else:
            category = "needs_manual_review"
            confidence = 0.5

        return {
            "category": category,
            "academic_count": academic_count,
            "industry_count": industry_count,
            "unknown_count": unknown_count,
            "industry_percentage": industry_percentage,
            "academic_percentage": academic_percentage,
            "confidence": confidence,
            "author_details": author_details,
        }

    def _calculate_confidence(
        self, dominant_percentage: float, author_details: List[Dict], category_type: str
    ) -> float:
        """Calculate confidence based on percentage dominance and individual confidences"""

        # Base confidence from percentage dominance
        base_confidence = min(0.9, dominant_percentage)

        # Average individual confidence scores for the dominant category
        relevant_confidences = [
            author["confidence"]
            for author in author_details
            if author["type"] == category_type
        ]

        if relevant_confidences:
            avg_individual_confidence = sum(relevant_confidences) / len(
                relevant_confidences
            )
            # Weighted combination of base and individual confidences
            final_confidence = 0.6 * base_confidence + 0.4 * avg_individual_confidence
        else:
            final_confidence = base_confidence

        return float(min(0.95, final_confidence))

    def classify_affiliation(self, affiliation: str) -> Dict[Any, Any]:
        """Wrapper method for affiliation classification"""
        result = self.affiliation_parser.classify_affiliation(affiliation)
        return dict(result) if result else {}

    def get_classification_summary(self, papers: List[Paper]) -> Dict:
        """Generate summary statistics for a batch of papers"""

        academic_eligible = 0
        industry_eligible = 0
        needs_review = 0
        total_confidence = 0.0

        category_breakdown: Dict[str, int] = defaultdict(int)

        for paper in papers:
            analysis = self.classify_paper_authorship(paper)

            category_breakdown[analysis.category] += 1
            total_confidence += analysis.confidence

            if analysis.category == "academic_eligible":
                academic_eligible += 1
            elif analysis.category == "industry_eligible":
                industry_eligible += 1
            else:
                needs_review += 1

        total_papers = len(papers)
        avg_confidence = total_confidence / total_papers if total_papers > 0 else 0.0

        return {
            "total_papers": total_papers,
            "academic_eligible": academic_eligible,
            "industry_eligible": industry_eligible,
            "needs_manual_review": needs_review,
            "academic_percentage": academic_eligible / total_papers
            if total_papers > 0
            else 0.0,
            "industry_percentage": industry_eligible / total_papers
            if total_papers > 0
            else 0.0,
            "review_percentage": needs_review / total_papers
            if total_papers > 0
            else 0.0,
            "average_confidence": avg_confidence,
            "category_breakdown": dict(category_breakdown),
        }
