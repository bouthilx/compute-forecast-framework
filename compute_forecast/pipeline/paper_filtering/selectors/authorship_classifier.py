"""
Authorship Classifier for Issue #8.
Classifies authors by affiliation type (academic vs industry) and analyzes collaboration patterns.
"""

import re
import logging
from typing import List, Dict, Any
from collections import Counter

from ...metadata_collection.models import Author, AuthorshipAnalysis

logger = logging.getLogger(__name__)


class AuthorshipClassifier:
    """
    Classifies paper authorship based on affiliations to determine
    academic vs industry collaboration patterns.
    """

    def __init__(self):
        # Academic institution patterns and keywords
        self.academic_patterns = [
            r"\buniversit",
            r"\bcolleg",
            r"\binstitut",
            r"\bacadem",
            r"\bschool\s+of",
            r"\bdepartment\s+of",
            r"\bfacult",
            r"\bcentre\s+for",
            r"\bcenter\s+for",
            r"\bresearch\s+(?:center|centre|institute)",
            r"\bgraduate\s+school",
            r"\bpostdoc",
            r"\bph\.?d",
            r"\bdoctoral",
            r"\bpost-doc",
        ]

        self.academic_keywords = {
            "university",
            "college",
            "institute",
            "academia",
            "school",
            "department",
            "faculty",
            "laboratory",
            "lab",
            "research",
            "professor",
            "student",
            "postdoc",
            "doctoral",
            "graduate",
        }

        # Specific academic institution names (top CS departments)
        self.known_academic = {
            "mit",
            "stanford",
            "berkeley",
            "cmu",
            "caltech",
            "harvard",
            "princeton",
            "yale",
            "columbia",
            "cornell",
            "upenn",
            "nyu",
            "ucla",
            "usc",
            "umich",
            "uiuc",
            "georgia tech",
            "ut austin",
            "uw",
            "ucsd",
            "umd",
            "wisc",
            "purdue",
            "brown",
            "rice",
            "duke",
            "unc",
            "virginia",
            "washington",
            "oxford",
            "cambridge",
            "eth",
            "epfl",
            "imperial",
            "ucl",
            "edinburgh",
            "toronto",
            "waterloo",
            "mcgill",
            "ubc",
            "melbourne",
            "sydney",
            "anu",
            "tsinghua",
            "peking",
            "tokyo",
            "kyoto",
            "seoul national",
            "kaist",
            "iit",
            "iisc",
            "technion",
            "tel aviv",
            "max planck",
            "inria",
            "cnrs",
            "ens",
            "polytechnique",
            "sorbonne",
        }

        # Industry patterns and keywords
        self.industry_patterns = [
            r"\b(?:inc|corp|ltd|llc|gmbh|ag|sa|plc)\b",
            r"\blabs?\b",
            r"\bresearch\s+(?:division|group|team)",
            r"\btechnolog",
            r"\bsoftware",
            r"\bengineering",
            r"\bsolutions",
            r"\bsystems",
            r"\bproducts",
            r"\bservices",
        ]

        self.industry_keywords = {
            "corporation",
            "company",
            "incorporated",
            "limited",
            "labs",
            "laboratory",
            "technologies",
            "software",
            "hardware",
            "solutions",
            "products",
            "services",
            "engineering",
            "development",
            "r&d",
        }

        # Known tech companies and research labs
        self.known_industry = {
            "google",
            "microsoft",
            "facebook",
            "meta",
            "apple",
            "amazon",
            "ibm",
            "intel",
            "nvidia",
            "amd",
            "qualcomm",
            "broadcom",
            "cisco",
            "oracle",
            "sap",
            "salesforce",
            "adobe",
            "vmware",
            "twitter",
            "netflix",
            "uber",
            "airbnb",
            "lyft",
            "spotify",
            "deepmind",
            "openai",
            "anthropic",
            "cohere",
            "hugging face",
            "tesla",
            "spacex",
            "boston dynamics",
            "waymo",
            "cruise",
            "baidu",
            "alibaba",
            "tencent",
            "bytedance",
            "huawei",
            "samsung",
            "lg",
            "sony",
            "panasonic",
            "toshiba",
            "fujitsu",
            "siemens",
            "bosch",
            "philips",
            "ericsson",
            "nokia",
            "accenture",
            "deloitte",
            "pwc",
            "ey",
            "kpmg",
            "mckinsey",
        }

        logger.info(
            "AuthorshipClassifier initialized with comprehensive affiliation patterns"
        )

    def classify_authors(self, authors: List[Author]) -> AuthorshipAnalysis:
        """
        Classify authorship based on author affiliations.

        Args:
            authors: List of Author objects

        Returns:
            AuthorshipAnalysis with classification results
        """
        academic_count = 0
        industry_count = 0
        unknown_count = 0
        author_details = []

        for author in authors:
            classification = self._classify_single_author(author)
            author_details.append(
                {
                    "name": author.name,
                    "affiliation": author.affiliation,
                    "classification": classification,
                    "confidence": self._get_classification_confidence(
                        author.affiliation, classification
                    ),
                }
            )

            if classification == "academic":
                academic_count += 1
            elif classification == "industry":
                industry_count += 1
            else:
                unknown_count += 1

        # Determine overall category
        category = self._determine_category(
            academic_count, industry_count, unknown_count
        )

        # Calculate confidence
        confidence = self._calculate_overall_confidence(
            academic_count, industry_count, unknown_count, author_details
        )

        return AuthorshipAnalysis(
            category=category,
            academic_count=academic_count,
            industry_count=industry_count,
            unknown_count=unknown_count,
            confidence=confidence,
            author_details=author_details,
        )

    def _classify_single_author(self, author: Author) -> str:
        """Classify a single author's affiliation."""
        if not author.affiliation:
            return "unknown"

        affiliation_lower = author.affiliation.lower()

        # Check known institutions first
        for academic_inst in self.known_academic:
            if academic_inst in affiliation_lower:
                return "academic"

        for industry_comp in self.known_industry:
            if industry_comp in affiliation_lower:
                return "industry"

        # Check patterns
        academic_score = 0
        industry_score = 0

        # Pattern matching
        for pattern in self.academic_patterns:
            if re.search(pattern, affiliation_lower):
                academic_score += 2

        for pattern in self.industry_patterns:
            if re.search(pattern, affiliation_lower):
                industry_score += 2

        # Keyword matching
        words = set(affiliation_lower.split())
        academic_score += len(words.intersection(self.academic_keywords))
        industry_score += len(words.intersection(self.industry_keywords))

        # Special cases
        if "research" in affiliation_lower:
            # "Research" can be both academic and industry
            if any(
                term in affiliation_lower
                for term in ["university", "institute", "college"]
            ):
                academic_score += 3
            elif any(
                term in affiliation_lower for term in ["labs", "corporation", "company"]
            ):
                industry_score += 3

        # Make decision
        if academic_score > industry_score and academic_score >= 3:
            return "academic"
        elif industry_score > academic_score and industry_score >= 3:
            return "industry"
        elif academic_score == industry_score and academic_score > 0:
            # Tie-breaker: check for explicit company indicators
            if re.search(r"\b(?:inc|corp|ltd|llc)\b", affiliation_lower):
                return "industry"
            else:
                return "academic"
        else:
            return "unknown"

    def _get_classification_confidence(
        self, affiliation: str, classification: str
    ) -> float:
        """Get confidence score for a single classification."""
        if not affiliation or classification == "unknown":
            return 0.0

        affiliation_lower = affiliation.lower()

        # High confidence for known institutions
        if classification == "academic":
            for inst in self.known_academic:
                if inst in affiliation_lower:
                    return 0.95
        elif classification == "industry":
            for comp in self.known_industry:
                if comp in affiliation_lower:
                    return 0.95

        # Medium confidence for pattern matches
        strong_patterns = {
            "academic": [r"\buniversit", r"\bcolleg", r"\binstitut"],
            "industry": [r"\b(?:inc|corp|ltd|llc)\b", r"\blabs\b"],
        }

        for pattern in strong_patterns.get(classification, []):
            if re.search(pattern, affiliation_lower):
                return 0.8

        # Lower confidence otherwise
        return 0.6

    def _determine_category(
        self, academic_count: int, industry_count: int, unknown_count: int
    ) -> str:
        """
        Determine overall authorship category.

        Categories:
        - 'academic_eligible': Majority academic authors
        - 'industry_eligible': Has industry collaboration
        - 'needs_manual_review': Too many unknowns or unclear
        """
        total_authors = academic_count + industry_count + unknown_count

        if total_authors == 0:
            return "needs_manual_review"

        # If too many unknowns, needs review
        if unknown_count >= total_authors * 0.5:
            return "needs_manual_review"

        # If any industry authors, mark as industry eligible
        if industry_count > 0:
            return "industry_eligible"

        # If majority academic
        if academic_count >= total_authors * 0.6:
            return "academic_eligible"

        return "needs_manual_review"

    def _calculate_overall_confidence(
        self,
        academic_count: int,
        industry_count: int,
        unknown_count: int,
        author_details: List[Dict],
    ) -> float:
        """Calculate overall confidence in the classification."""
        total_authors = academic_count + industry_count + unknown_count

        if total_authors == 0:
            return 0.0

        # Base confidence on known vs unknown ratio
        known_ratio = (academic_count + industry_count) / total_authors
        base_confidence = known_ratio

        # Adjust based on individual author confidences
        if author_details:
            avg_individual_confidence = sum(
                d["confidence"] for d in author_details
            ) / len(author_details)
            base_confidence = base_confidence * 0.5 + avg_individual_confidence * 0.5

        # Penalty for mixed affiliations (harder to classify)
        if academic_count > 0 and industry_count > 0:
            base_confidence *= 0.9

        return float(base_confidence)

    def analyze_collaboration_patterns(self, authors: List[Author]) -> Dict[str, Any]:
        """
        Analyze collaboration patterns between academic and industry.

        Returns additional insights about the collaboration.
        """
        classification = self.classify_authors(authors)

        patterns = {
            "total_authors": len(authors),
            "collaboration_type": "none",
            "academic_percentage": 0.0,
            "industry_percentage": 0.0,
            "unknown_percentage": 0.0,
            "is_pure_academic": False,
            "is_pure_industry": False,
            "is_mixed_collaboration": False,
            "primary_affiliations": [],
        }

        if len(authors) == 0:
            return patterns

        # Calculate percentages
        patterns["academic_percentage"] = classification.academic_count / len(authors)
        patterns["industry_percentage"] = classification.industry_count / len(authors)
        patterns["unknown_percentage"] = classification.unknown_count / len(authors)

        # Determine collaboration type
        if classification.academic_count > 0 and classification.industry_count > 0:
            patterns["collaboration_type"] = "academic_industry"
            patterns["is_mixed_collaboration"] = True
        elif classification.academic_count > 0:
            patterns["collaboration_type"] = "academic_only"
            patterns["is_pure_academic"] = classification.industry_count == 0
        elif classification.industry_count > 0:
            patterns["collaboration_type"] = "industry_only"
            patterns["is_pure_industry"] = classification.academic_count == 0
        else:
            patterns["collaboration_type"] = "unknown"

        # Extract primary affiliations
        affiliation_counts: Counter[str] = Counter()
        for author in authors:
            if author.affiliation:
                # Extract institution name (simplified)
                inst_name = self._extract_institution_name(author.affiliation)
                if inst_name:
                    affiliation_counts[inst_name] += 1

        patterns["primary_affiliations"] = [
            {"name": name, "count": count}
            for name, count in affiliation_counts.most_common(5)
        ]

        return patterns

    def _extract_institution_name(self, affiliation: str) -> str:
        """Extract simplified institution name from affiliation string."""
        # Remove common suffixes
        cleaned = re.sub(
            r"\b(?:inc|corp|ltd|llc|gmbh|ag|sa|plc)\b\.?",
            "",
            affiliation,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(?:university|college|institute|labs?|research)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"[,;].*", "", cleaned
        )  # Take first part before comma/semicolon
        cleaned = cleaned.strip()

        # Try to match known institutions
        lower = cleaned.lower()
        for known in self.known_academic.union(self.known_industry):
            if known in lower:
                return str(known.title())

        # Return cleaned version
        return cleaned[:50] if cleaned else ""
