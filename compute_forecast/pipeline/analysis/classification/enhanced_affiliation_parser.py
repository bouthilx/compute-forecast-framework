"""Enhanced affiliation parser with improved edge case handling."""

import re
from typing import Dict, Optional, Any
from .affiliation_parser import AffiliationParser


class EnhancedAffiliationParser(AffiliationParser):
    """Extends existing parser with better edge case handling."""

    def __init__(self):
        """Initialize enhanced parser."""
        super().__init__()

        # Additional patterns for complex parsing
        self.department_patterns = [
            r"(?:department|dept\.?|school|faculty|institute|center|centre|laboratory|lab)\s+(?:of|for)\s+(\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*)\s+(?:department|dept\.?|school|faculty|institute|center|centre|laboratory|lab)",
        ]

        self.location_patterns = {
            "city": r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "state": r"([A-Z]{2})",
            "country": r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "postal": r"(\d{5}(?:-\d{4})?|\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b)",
        }

        # Extended abbreviation map
        self.extended_abbreviations = {
            "cs": "computer science",
            "ai": "artificial intelligence",
            "ml": "machine learning",
            "ee": "electrical engineering",
            "ece": "electrical and computer engineering",
            "math": "mathematics",
            "phys": "physics",
            "bio": "biology",
            "chem": "chemistry",
            "med": "medicine",
        }

        # Add to parent abbreviations
        self.abbreviations.update(self.extended_abbreviations)

    def parse_complex_affiliation(self, affiliation: str) -> Dict[str, Any]:
        """Handle complex multi-part affiliations."""
        if not affiliation or not affiliation.strip():
            return {
                "organization": None,
                "department": None,
                "city": None,
                "state": None,
                "country": None,
                "parse_confidence": 0.0,
            }

        # Remove email addresses but keep track of domain
        email_domain = None
        email_pattern = r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
        email_match = re.search(email_pattern, affiliation)
        if email_match:
            email_domain = email_match.group(1)
            affiliation = re.sub(email_pattern, "", affiliation)

        # Handle parenthetical information
        paren_content = []
        paren_pattern = r"\([^)]+\)"
        for match in re.finditer(paren_pattern, affiliation):
            paren_content.append(match.group(0)[1:-1])  # Remove parentheses
        affiliation = re.sub(paren_pattern, "", affiliation)

        # Split by common separators
        parts = re.split(r"[,;/]", affiliation)
        parts = [p.strip() for p in parts if p.strip()]

        result = {
            "organization": None,
            "department": None,
            "city": None,
            "state": None,
            "country": None,
            "email_domain": email_domain,
            "parse_confidence": 1.0,
        }

        # Process each part
        for i, part in enumerate(parts):
            part_lower = part.lower()

            # Check for department
            if not result["department"]:
                for pattern in self.department_patterns:
                    dept_match = re.search(pattern, part, re.IGNORECASE)
                    if dept_match is not None:
                        dept = dept_match.group(1)
                        # Expand abbreviations in department name
                        for abbrev, expansion in self.abbreviations.items():
                            dept = re.sub(
                                rf"\b{abbrev}\b", expansion, dept, flags=re.IGNORECASE
                            )
                        result["department"] = dept.title()
                        # Don't remove department from part - it might contain org info
                        # Just mark that we found a department
                        break

            # Check for state abbreviation (US states)
            if len(part) == 2 and part.isupper() and not result["state"]:
                result["state"] = part
                continue

            # Check for location information
            if i >= 1:  # Location info usually comes after organization
                if len(part) <= 30 and not any(
                    keyword in part_lower
                    for keyword in [
                        "university",
                        "institute",
                        "college",
                        "department",
                        "dept",
                        "school",
                    ]
                ):
                    # Check if it's a country
                    country_map = {
                        "USA": "USA",
                        "UK": "UK",
                        "CA": "CA",
                        "CANADA": "Canada",
                        "FRANCE": "France",
                        "GERMANY": "Germany",
                        "CHINA": "China",
                        "JAPAN": "Japan",
                        "SWITZERLAND": "Switzerland",
                    }
                    if part.upper() in country_map:
                        result["country"] = country_map.get(part.upper(), part)
                    # Check if it's already identified as state
                    elif part != result.get("state") and not result["organization"]:
                        # Skip this - it might be the organization
                        pass
                    elif part != result.get("state"):
                        # If we don't have a city yet, this could be the city
                        if not result["city"]:
                            result["city"] = part

            # Extract organization name (usually first substantial part)
            if not result["organization"] and len(part) > 2:
                # Check if it's a known organization pattern
                org_keywords = [
                    "university",
                    "institute",
                    "college",
                    "corporation",
                    "company",
                    "research",
                    "laboratory",
                    "foundation",
                    "academy",
                ]
                # Common university abbreviations including UC variants
                common_abbreviations = [
                    "MIT",
                    "UCLA",
                    "UCB",
                    "NYU",
                    "CMU",
                    "UIUC",
                    "USC",
                    "UCSD",
                ]

                # Special handling for UC Berkeley and similar patterns
                uc_pattern = r"UC\s+(\w+)"
                uc_match = re.search(uc_pattern, part)
                if uc_match:
                    result["organization"] = f"UC {uc_match.group(1)}"
                elif any(keyword in part_lower for keyword in org_keywords):
                    result["organization"] = self._clean_organization_name(part)
                elif part.upper() in common_abbreviations:
                    result["organization"] = part.upper()
                elif (
                    i == 0 and not result["department"]
                ):  # First part is often the organization if no dept found
                    result["organization"] = self._clean_organization_name(part)

        # If no organization found, check parenthetical content
        if not result["organization"] and paren_content:
            for content in paren_content:
                if any(
                    keyword in content.lower()
                    for keyword in ["university", "institute", "research"]
                ):
                    result["organization"] = self._clean_organization_name(content)
                    break

        # Calculate parse confidence
        confidence = 1.0
        if not result["organization"]:
            confidence *= 0.3
        elif (
            isinstance(result["organization"], str)
            and "unknown" in result["organization"].lower()
            and "affiliation" in result["organization"].lower()
        ):
            # Very vague/unknown affiliation
            confidence *= 0.3
        elif isinstance(result["organization"], str) and any(
            vague in result["organization"].lower()
            for vague in ["unknown", "research lab", "laboratory"]
        ):
            # Generic or vague organization names
            confidence *= 0.7

        if not result["department"] and any(
            word in affiliation.lower() for word in ["dept", "department"]
        ):
            confidence *= 0.8

        if email_domain and not result["organization"]:
            confidence *= 0.7

        # Check for location quality
        if (
            result.get("city")
            and isinstance(result["city"], str)
            and "unknown" in result["city"].lower()
        ):
            confidence *= 0.8

        # Very short affiliations are less reliable
        if affiliation and len(affiliation.strip()) < 10:
            confidence *= 0.9

        result["parse_confidence"] = confidence
        return result

    def _clean_organization_name(self, name: str) -> str:
        """Clean and normalize organization name."""
        # Remove common prefixes
        prefixes = ["the", "at", "from"]
        words = name.split()
        if words and words[0].lower() in prefixes:
            name = " ".join(words[1:])

        # Expand abbreviations
        for abbrev, expansion in self.abbreviations.items():
            name = re.sub(rf"\b{abbrev}\b", expansion, name, flags=re.IGNORECASE)

        # Clean up whitespace and punctuation
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"^[,\-\s]+|[,\-\s]+$", "", name)

        return name

    def extract_primary_organization(self, parsed: Dict[str, Any]) -> str:
        """Extract main organization from parsed data."""
        if parsed.get("organization"):
            return str(parsed["organization"])

        # Try to construct from other fields
        if parsed.get("department") and parsed.get("email_domain"):
            # Try to infer organization from domain
            domain_parts = parsed["email_domain"].split(".")
            if len(domain_parts) >= 2:
                org_part = domain_parts[0]
                # Common academic domain patterns
                if org_part in ["mit", "stanford", "harvard", "berkeley"]:
                    return (
                        str(org_part.upper())
                        if org_part == "mit"
                        else str(org_part.title())
                    )

        return ""

    def handle_edge_cases(self, affiliation: str) -> Optional[str]:
        """Handle known edge cases."""
        if not affiliation:
            return None

        # Handle multiple affiliations separated by semicolons
        if ";" in affiliation:
            # Return the first affiliation as primary
            parts = affiliation.split(";")
            if parts:
                primary = parts[0].strip()
                parsed = self.parse_complex_affiliation(primary)
                return str(parsed.get("organization", primary))

        # Handle affiliations with both academic and industry
        if " and " in affiliation.lower() or " & " in affiliation:
            # Parse both and return the first one
            parts = re.split(r"\s+(?:and|&)\s+", affiliation, flags=re.IGNORECASE)
            if parts:
                primary = parts[0].strip()
                parsed = self.parse_complex_affiliation(primary)
                return str(parsed.get("organization", primary))

        # Handle non-English affiliations (preserve them)
        if self._contains_non_ascii(affiliation):
            # Try basic parsing but preserve original if it fails
            parsed = self.parse_complex_affiliation(affiliation)
            if parsed.get("organization"):
                return str(parsed["organization"])
            else:
                # Return cleaned version of original
                return self._clean_organization_name(affiliation)

        # Default parsing
        parsed = self.parse_complex_affiliation(affiliation)
        return parsed.get("organization")

    def _contains_non_ascii(self, text: str) -> bool:
        """Check if text contains non-ASCII characters."""
        return any(ord(char) > 127 for char in text)

    def normalize_affiliation(self, raw_affiliation: str) -> str:
        """Enhanced normalization with better abbreviation handling."""
        # Call parent normalization first
        normalized = super().normalize_affiliation(raw_affiliation)

        # Additional normalization for enhanced parser
        # Expand department-specific abbreviations
        dept_abbreviations = {
            r"\bcs\b": "computer science",
            r"\bece\b": "electrical and computer engineering",
            r"\bee\b": "electrical engineering",
            r"\bmath\b": "mathematics",
            r"\bphys\b": "physics",
            r"\bchem\b": "chemistry",
            r"\bbio\b": "biology",
        }

        for pattern, replacement in dept_abbreviations.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized
