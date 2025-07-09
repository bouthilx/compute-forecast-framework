import re
from typing import Dict, List, Any
from .organizations import OrganizationDatabase
from ....core.logging import setup_logging


class AffiliationParser:
    """Parses and normalizes author affiliation strings"""

    def __init__(self):
        self.logger = setup_logging()
        self.org_db = OrganizationDatabase()

        self.academic_keywords = [
            "university",
            "institut",
            "college",
            "school",
            "research center",
            "laboratory",
            "department of",
            "faculty of",
            "dept",
            "lab",
            "center for",
            "centre for",
        ]

        self.industry_keywords = [
            "corporation",
            "inc.",
            "ltd.",
            "llc",
            "labs",
            "research lab",
            "ai lab",
            "technologies",
            "corp",
            "company",
            "limited",
            "incorporated",
        ]

        # Common abbreviations and their expansions
        self.abbreviations = {
            "univ": "university",
            "inst": "institute",
            "tech": "technology",
            "sci": "science",
            "comp": "computer",
            "eng": "engineering",
            "dept": "department",
        }

    def normalize_affiliation(self, raw_affiliation: str) -> str:
        """Clean and standardize affiliation strings"""
        if not raw_affiliation:
            return ""

        # Convert to lowercase for processing
        normalized = raw_affiliation.lower().strip()

        # Remove common punctuation and extra whitespace
        normalized = re.sub(r"[,;]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        # Handle common abbreviations
        for abbrev, expansion in self.abbreviations.items():
            normalized = re.sub(rf"\b{abbrev}\b", expansion, normalized)

        # Remove email addresses
        normalized = re.sub(r"\S+@\S+", "", normalized)

        # Remove common address components (numbers, zip codes)
        normalized = re.sub(r"\b\d{4,5}\b", "", normalized)  # zip codes
        normalized = re.sub(
            r"\b\d+\s+(st|nd|rd|th)\b", "", normalized
        )  # street numbers

        # Clean up multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def extract_primary_institution(self, affiliation: str) -> str:
        """Extract the main institution name from affiliation string"""
        normalized = self.normalize_affiliation(affiliation)

        # Try to find known organizations first
        match = self.org_db.get_organization_match(normalized)
        if match["organization"]:
            return str(match["organization"])

        # Split by common separators and take the first meaningful part
        parts = re.split(r"[,;]", normalized)
        if parts:
            primary = parts[0].strip()

            # Remove department/faculty prefixes
            primary = re.sub(
                r"^(department of|faculty of|school of|center for|centre for)\s+",
                "",
                primary,
            )

            return primary

        return normalized

    def classify_affiliation(self, affiliation: str) -> Dict[str, Any]:
        """Classify affiliation as academic, industry, or unknown with confidence"""
        if not affiliation:
            return {
                "type": "unknown",
                "confidence": 0.0,
                "normalized": "",
                "primary_institution": "",
                "matched_organization": None,
            }

        normalized = self.normalize_affiliation(affiliation)
        primary_institution = self.extract_primary_institution(affiliation)

        # Check against known organizations first
        org_match = self.org_db.get_organization_match(normalized)
        if org_match["type"] != "unknown":
            confidence = 0.95  # High confidence for known organizations
            return {
                "type": org_match["type"],
                "confidence": confidence,
                "normalized": normalized,
                "primary_institution": primary_institution,
                "matched_organization": org_match["organization"],
            }

        # Keyword-based classification for unknown organizations
        academic_score = self._calculate_keyword_score(
            normalized, self.academic_keywords
        )
        industry_score = self._calculate_keyword_score(
            normalized, self.industry_keywords
        )

        if academic_score > industry_score and academic_score > 0:
            classification_type = "academic"
            confidence = min(0.8, academic_score)  # Cap at 0.8 for keyword-based
        elif industry_score > academic_score and industry_score > 0:
            classification_type = "industry"
            confidence = min(0.8, industry_score)
        else:
            classification_type = "unknown"
            confidence = 0.0

        return {
            "type": classification_type,
            "confidence": confidence,
            "normalized": normalized,
            "primary_institution": primary_institution,
            "matched_organization": None,
        }

    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword presence"""
        if not text:
            return 0.0

        matches = sum(1 for keyword in keywords if keyword in text)
        return min(1.0, matches / 3.0)  # Normalize to 0-1 scale

    def extract_all_affiliations(self, author_list: List[Dict]) -> List[Dict]:
        """Process all authors and extract clean affiliations"""
        results = []

        for author in author_list:
            affiliation = author.get("affiliation", "")
            classification = self.classify_affiliation(affiliation)

            results.append(
                {
                    "name": author.get("name", ""),
                    "original_affiliation": affiliation,
                    "classification": classification,
                }
            )

        return results
