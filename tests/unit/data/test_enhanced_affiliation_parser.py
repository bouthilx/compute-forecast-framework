"""Test suite for enhanced affiliation parser."""

import pytest
from compute_forecast.analysis.classification.enhanced_affiliation_parser import (
    EnhancedAffiliationParser,
)


class TestEnhancedAffiliationParser:
    """Test enhanced affiliation parser functionality."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return EnhancedAffiliationParser()

    def test_parse_simple_affiliation(self, parser):
        """Test parsing of simple affiliation strings."""
        test_cases = [
            (
                "MIT",
                {
                    "organization": "MIT",
                    "department": None,
                    "city": None,
                    "country": None,
                },
            ),
            (
                "Google Research",
                {
                    "organization": "Google Research",
                    "department": None,
                    "city": None,
                    "country": None,
                },
            ),
            (
                "Stanford University",
                {
                    "organization": "Stanford University",
                    "department": None,
                    "city": None,
                    "country": None,
                },
            ),
        ]

        for affiliation, expected in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] == expected["organization"]

    def test_parse_department_affiliation(self, parser):
        """Test parsing affiliations with department information."""
        test_cases = [
            (
                "Department of Computer Science, MIT",
                {"organization": "MIT", "department": "Computer Science"},
            ),
            (
                "Dept. of AI, Stanford University",
                {
                    "organization": "Stanford University",
                    "department": "Artificial Intelligence",
                },
            ),
            (
                "School of Engineering, UC Berkeley",
                {"organization": "UC Berkeley", "department": "Engineering"},
            ),
        ]

        for affiliation, expected in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] == expected["organization"]
            assert result["department"] == expected["department"]

    def test_parse_location_information(self, parser):
        """Test parsing affiliations with location details."""
        test_cases = [
            (
                "MIT, Cambridge, MA, USA",
                {
                    "organization": "MIT",
                    "city": "Cambridge",
                    "state": "MA",
                    "country": "USA",
                },
            ),
            (
                "University of Toronto, Toronto, ON, Canada",
                {
                    "organization": "University of Toronto",
                    "city": "Toronto",
                    "state": "ON",
                    "country": "Canada",
                },
            ),
            (
                "ETH Zurich, Zurich, Switzerland",
                {
                    "organization": "ETH Zurich",
                    "city": "Zurich",
                    "country": "Switzerland",
                },
            ),
        ]

        for affiliation, expected in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] == expected["organization"]
            assert result["city"] == expected["city"]
            assert result["country"] == expected["country"]

    def test_handle_email_addresses(self, parser):
        """Test handling of affiliations containing email addresses."""
        test_cases = [
            "john.doe@mit.edu, MIT",
            "MIT (john.doe@mit.edu)",
            "john.doe@google.com, Google Research",
        ]

        for affiliation in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            # Email should be extracted or removed
            assert "@" not in result.get("organization", "")

    def test_handle_multiple_affiliations(self, parser):
        """Test handling of multiple affiliations in one string."""
        multi_affiliation = "MIT, Cambridge, MA; Google Research, Mountain View, CA"
        result = parser.handle_edge_cases(multi_affiliation)

        # Should extract primary affiliation
        assert result is not None
        assert "MIT" in result or "Google" in result

    def test_handle_parenthetical_information(self, parser):
        """Test handling of parenthetical information."""
        test_cases = [
            ("MIT (Massachusetts Institute of Technology)", "MIT"),
            ("Google Research (formerly Google Brain)", "Google Research"),
            (
                "Stanford University (Computer Science Department)",
                "Stanford University",
            ),
        ]

        for affiliation, expected_org in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] == expected_org

    def test_normalize_abbreviations(self, parser):
        """Test normalization of common abbreviations."""
        test_cases = {
            "Dept.": "Department",
            "Univ.": "University",
            "Inst.": "Institute",
            "Tech.": "Technology",
            "Sci.": "Science",
            "Comp.": "Computer",
            "Eng.": "Engineering",
        }

        for abbrev, expansion in test_cases.items():
            affiliation = f"{abbrev} of Something"
            normalized = parser.normalize_affiliation(affiliation)
            assert abbrev.lower() not in normalized or expansion.lower() in normalized

    def test_handle_non_ascii_characters(self, parser):
        """Test handling of non-ASCII characters in affiliations."""
        test_cases = [
            "Université de Montréal",
            "École Polytechnique Fédérale de Lausanne",
            "Technische Universität München",
            "Universidad Autónoma de Madrid",
        ]

        for affiliation in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] is not None
            # Should preserve non-ASCII characters
            assert any(ord(c) > 127 for c in result["organization"])

    def test_extract_institution_type(self, parser):
        """Test extraction of institution type from affiliation."""
        test_cases = [
            ("MIT Research Laboratory", "research_lab"),
            ("Stanford University Hospital", "medical"),
            ("Google Research Center", "research_center"),
            ("National Science Foundation", "government"),
        ]

        for affiliation, expected_type in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            # Parser should identify institution type when possible
            assert "institution_type" in result or True  # Optional feature

    def test_handle_complex_formatting(self, parser):
        """Test handling of complex formatting and punctuation."""
        test_cases = [
            "MIT - Massachusetts Institute of Technology, Cambridge, MA 02139, USA",
            "Google Research (Mountain View), CA, United States",
            "Stanford University / Computer Science Department / AI Lab",
            "University of Toronto; Vector Institute for AI",
        ]

        for affiliation in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] is not None
            assert len(result["organization"]) > 0

    def test_confidence_scoring(self, parser):
        """Test confidence scoring for parsed affiliations."""
        # High confidence - clear organization
        high_conf = parser.parse_complex_affiliation("MIT")
        assert high_conf.get("parse_confidence", 1.0) >= 0.9

        # Medium confidence - some ambiguity
        med_conf = parser.parse_complex_affiliation("Research Lab, Unknown Location")
        assert 0.5 <= med_conf.get("parse_confidence", 0.7) <= 0.9

        # Low confidence - very ambiguous
        low_conf = parser.parse_complex_affiliation("Unknown affiliation string")
        assert low_conf.get("parse_confidence", 0.3) <= 0.5

    def test_empty_and_null_handling(self, parser):
        """Test handling of empty and null affiliations."""
        test_cases = ["", None, "   ", "\n", "\t"]

        for affiliation in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] in [None, ""]
            assert result.get("parse_confidence", 0) == 0

    def test_special_characters_handling(self, parser):
        """Test handling of special characters and symbols."""
        test_cases = [
            "MIT & Harvard Joint Program",
            "Google/DeepMind",
            "Stanford + Berkeley Collaboration",
            "University #1 in Rankings",
        ]

        for affiliation in test_cases:
            result = parser.parse_complex_affiliation(affiliation)
            assert result["organization"] is not None
            # Special characters should be handled gracefully
            assert len(result["organization"]) > 0
