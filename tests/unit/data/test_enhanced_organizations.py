"""Test suite for enhanced organization classification system."""

import pytest
from datetime import datetime

from compute_forecast.pipeline.analysis.classification.enhanced_organizations import (
    EnhancedOrganizationClassifier,
    OrganizationType,
    OrganizationRecord,
)
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.metadata_collection.models import (
    Paper,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestEnhancedOrganizationClassifier:
    """Test enhanced organization classifier with fuzzy matching and confidence scoring."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance for testing."""
        classifier = EnhancedOrganizationClassifier()
        # Add test organizations
        test_orgs = [
            OrganizationRecord(
                name="Massachusetts Institute of Technology",
                type=OrganizationType.ACADEMIC,
                aliases=["MIT", "M.I.T.", "Mass. Inst. of Tech."],
                domains=["mit.edu", "csail.mit.edu"],
                keywords=["Laboratory", "Department"],
            ),
            OrganizationRecord(
                name="Google Research",
                type=OrganizationType.INDUSTRY,
                aliases=["Google", "Google AI", "Google Brain"],
                domains=["google.com", "research.google.com"],
                keywords=["Research", "Labs"],
            ),
            OrganizationRecord(
                name="National Science Foundation",
                type=OrganizationType.GOVERNMENT,
                aliases=["NSF"],
                domains=["nsf.gov"],
                keywords=["Foundation", "National"],
            ),
        ]
        for org in test_orgs:
            classifier.add_organization(org)
        return classifier

    def test_exact_match_classification(self, classifier):
        """Test classification with exact organization name match."""
        result = classifier.classify_with_confidence(
            "Massachusetts Institute of Technology"
        )
        assert result.organization == "Massachusetts Institute of Technology"
        assert result.type == OrganizationType.ACADEMIC
        assert result.confidence >= 0.95
        assert result.match_method == "exact"

    def test_alias_match_classification(self, classifier):
        """Test classification using organization aliases."""
        result = classifier.classify_with_confidence("MIT Computer Science Department")
        assert result.organization == "Massachusetts Institute of Technology"
        assert result.type == OrganizationType.ACADEMIC
        assert result.confidence >= 0.9
        assert result.match_method == "alias"

    def test_domain_match_classification(self, classifier):
        """Test classification using email domains."""
        result = classifier.classify_with_confidence("john.doe@csail.mit.edu")
        assert result.organization == "Massachusetts Institute of Technology"
        assert result.type == OrganizationType.ACADEMIC
        assert result.confidence >= 0.85
        assert result.match_method == "domain"

    def test_fuzzy_match_classification(self, classifier):
        """Test fuzzy matching for name variations."""
        # Test variations with typos or different formatting that don't contain exact match
        fuzzy_variations = [
            ("Massachusets Institute of Technology", "fuzzy"),  # Typo
            ("Massachusetts Inst. of Tech.", "alias"),  # This is an alias match
            ("Mass Inst Tech", "fuzzy"),  # Abbreviated, should be fuzzy
        ]

        for variation, expected_method in fuzzy_variations:
            result = classifier.classify_with_confidence(variation)
            assert result.organization == "Massachusetts Institute of Technology"
            assert result.type == OrganizationType.ACADEMIC
            assert result.confidence >= 0.7
            if expected_method == "fuzzy":
                assert result.match_method == "fuzzy"

    def test_keyword_match_classification(self, classifier):
        """Test keyword-based classification."""
        result = classifier.classify_with_confidence(
            "Unknown University Research Laboratory"
        )
        assert result.type == OrganizationType.ACADEMIC  # Keywords suggest academic
        assert result.confidence < 0.8  # Lower confidence for keyword-only match
        assert result.match_method == "keyword"

    def test_government_organization_classification(self, classifier):
        """Test government organization classification."""
        result = classifier.classify_with_confidence(
            "National Science Foundation Grant Office"
        )
        assert result.organization == "National Science Foundation"
        assert result.type == OrganizationType.GOVERNMENT
        assert result.confidence >= 0.85

    def test_unknown_organization_classification(self, classifier):
        """Test handling of completely unknown organizations."""
        result = classifier.classify_with_confidence("Random Company LLC")
        assert result.type == OrganizationType.UNKNOWN
        assert result.confidence < 0.5
        assert result.organization is None

    def test_confidence_score_ordering(self, classifier):
        """Test that confidence scores follow expected ordering."""
        exact_result = classifier.classify_with_confidence(
            "Massachusetts Institute of Technology"
        )
        alias_result = classifier.classify_with_confidence("MIT")
        fuzzy_result = classifier.classify_with_confidence(
            "Massachusets Inst of Tech"
        )  # Typo
        keyword_result = classifier.classify_with_confidence(
            "Some University Laboratory"
        )

        # Exact match should have highest confidence
        assert exact_result.confidence > alias_result.confidence
        assert alias_result.confidence > fuzzy_result.confidence
        assert fuzzy_result.confidence > keyword_result.confidence

    def test_case_insensitive_matching(self, classifier):
        """Test case-insensitive organization matching."""
        variations = ["MIT", "mit", "Mit", "mIt"]
        results = [classifier.classify_with_confidence(var) for var in variations]

        # All should match to the same organization
        assert all(
            r.organization == "Massachusetts Institute of Technology" for r in results
        )
        assert all(r.type == OrganizationType.ACADEMIC for r in results)

    def test_multiple_affiliation_handling(self, classifier):
        """Test handling of multiple affiliations in one string."""
        affiliation = "MIT; Google Research; Stanford University"
        # This should be handled by the parser, but classifier should handle gracefully
        result = classifier.classify_with_confidence(affiliation)
        assert result is not None
        assert (
            result.confidence < 1.0
        )  # Should have lower confidence for complex strings


class TestEnhancedAffiliationParser:
    """Test enhanced affiliation parser with edge case handling."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        from compute_forecast.pipeline.analysis.classification.enhanced_affiliation_parser import (
            EnhancedAffiliationParser,
        )

        return EnhancedAffiliationParser()

    def test_parse_complex_affiliation(self, parser):
        """Test parsing of complex multi-part affiliations."""
        affiliation = "Dept. of Computer Science, MIT, Cambridge, MA, USA"
        result = parser.parse_complex_affiliation(affiliation)

        assert result["organization"] == "MIT"
        assert result["department"] == "Computer Science"
        assert result["city"] == "Cambridge"
        assert result["country"] == "USA"

    def test_extract_primary_organization(self, parser):
        """Test extraction of primary organization from parsed data."""
        parsed_data = {
            "organization": "Stanford University",
            "department": "Computer Science",
            "city": "Stanford",
            "country": "USA",
        }
        primary = parser.extract_primary_organization(parsed_data)
        assert primary == "Stanford University"

    def test_handle_multiple_affiliations(self, parser):
        """Test handling of semicolon-separated multiple affiliations."""
        affiliation = "MIT, Cambridge; Google Research, Mountain View"
        result = parser.handle_edge_cases(affiliation)
        assert result is not None
        # Should return the first/primary affiliation
        assert "MIT" in result or "Google" in result

    def test_handle_non_english_affiliations(self, parser):
        """Test handling of non-English organization names."""
        affiliations = [
            "Université de Montréal",
            "École Polytechnique Fédérale de Lausanne",
            "中国科学院",  # Chinese Academy of Sciences
        ]

        for affiliation in affiliations:
            result = parser.handle_edge_cases(affiliation)
            assert result is not None

    def test_handle_abbreviated_names(self, parser):
        """Test expansion of common abbreviations."""
        test_cases = {
            "Dept. of CS, MIT": "Department of Computer Science, MIT",
            "Univ. of Toronto": "University of Toronto",
            "Inst. of Tech.": "Institute of Technology",
        }

        for abbreviated, expected_substring in test_cases.items():
            normalized = parser.normalize_affiliation(abbreviated)
            # Check that abbreviations are expanded
            assert "dept" not in normalized or "department" in normalized
            assert "univ" not in normalized or "university" in normalized
            assert "inst" not in normalized or "institute" in normalized


class TestClassificationValidator:
    """Test validation framework for classification accuracy."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        from compute_forecast.pipeline.analysis.classification.enhanced_validator import (
            EnhancedClassificationValidator,
        )

        return EnhancedClassificationValidator()

    def test_validation_accuracy_calculation(self, validator):
        """Test accuracy calculation on known test cases."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        # Create test papers with known classifications
        test_papers = [
            create_test_paper(
                paper_id="test1",
                title="Test Paper 1",
                authors=[Author(name="John Doe", affiliations=["MIT"])],
                venue="NeurIPS",
                year=2023,
                citation_count=10,
            ),
            create_test_paper(
                paper_id="test2",
                title="Test Paper 2",
                authors=[Author(name="Jane Smith", affiliations=["Google Research"])],
                venue="ICML",
                year=2023,
                citation_count=5,
            ),
        ]

        results = validator.validate(test_papers)
        assert "overall_accuracy" in results
        assert 0 <= results["overall_accuracy"] <= 1
        assert "academic_precision" in results
        assert "industry_precision" in results

    def test_edge_case_identification(self, validator):
        """Test identification of classification edge cases."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        # Create paper with mixed affiliations (edge case)
        create_test_paper(
            paper_id="edge1",
            title="Edge Case Paper",
            authors=[
                Author(name="Author 1", affiliations=["MIT"]),
                Author(name="Author 2", affiliations=["Google"]),
                Author(name="Author 3", affiliations=["Unknown Org"]),
            ],
            venue="Conference",
            year=2023,
            citation_count=0,
        )

        failures = validator.identify_failures()
        # Should identify papers near the 25% threshold as potential failures
        assert isinstance(failures, list)

    def test_confidence_distribution_analysis(self, validator):
        """Test analysis of confidence score distribution."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        papers = [
            create_test_paper(
                paper_id=f"test{i}",
                title=f"Paper {i}",
                authors=[Author(name=f"Author {i}", affiliations=[aff])],
                venue="Venue",
                year=2023,
                citation_count=i,
            )
            for i, aff in enumerate(
                ["MIT", "Google", "Unknown University", "Random Corp"]
            )
        ]

        results = validator.validate(papers)
        confidence_dist = results.get("confidence_distribution", {})

        # Check distribution structure
        assert "distribution" in confidence_dist
        distribution = confidence_dist["distribution"]
        assert "high_confidence" in distribution
        assert "medium_confidence" in distribution
        assert "low_confidence" in distribution

        # Verify some papers have high confidence
        assert distribution["high_confidence"] > 0


class TestOrganizationDatabaseExpansion:
    """Test expanded organization database functionality."""

    def test_load_enhanced_database(self):
        """Test loading of enhanced organization database from YAML."""
        from compute_forecast.pipeline.analysis.classification.enhanced_organizations import (
            EnhancedOrganizationClassifier,
        )

        classifier = EnhancedOrganizationClassifier()
        classifier.load_enhanced_database("config/organizations_enhanced.yaml")

        # Should have loaded 225+ organizations
        assert classifier.get_organization_count() >= 225

        # Should have all organization types
        assert classifier.get_organizations_by_type(OrganizationType.ACADEMIC)
        assert classifier.get_organizations_by_type(OrganizationType.INDUSTRY)
        assert classifier.get_organizations_by_type(OrganizationType.GOVERNMENT)
        assert classifier.get_organizations_by_type(OrganizationType.NON_PROFIT)

    def test_organization_database_coverage(self):
        """Test that database covers major institutions."""
        from compute_forecast.pipeline.analysis.classification.enhanced_organizations import (
            EnhancedOrganizationClassifier,
        )

        classifier = EnhancedOrganizationClassifier()
        classifier.load_enhanced_database("config/organizations_enhanced.yaml")

        # Test coverage of major institutions
        major_universities = [
            "MIT",
            "Stanford",
            "Harvard",
            "Berkeley",
            "CMU",
            "Oxford",
            "Cambridge",
            "ETH Zurich",
            "Toronto",
            "McGill",
        ]

        major_companies = [
            "Google",
            "Microsoft",
            "Meta",
            "OpenAI",
            "DeepMind",
            "Amazon",
            "Apple",
            "NVIDIA",
            "IBM",
            "Intel",
        ]

        for uni in major_universities:
            result = classifier.classify_with_confidence(uni)
            assert result.type == OrganizationType.ACADEMIC
            assert result.confidence > 0.8

        for company in major_companies:
            result = classifier.classify_with_confidence(company)
            assert result.type == OrganizationType.INDUSTRY
            assert result.confidence > 0.8


class TestPaperAuthorClassification:
    """Test paper-level classification based on author affiliations."""

    @pytest.fixture
    def classifier(self):
        """Create enhanced classifier for testing."""
        from compute_forecast.pipeline.analysis.classification.enhanced_organizations import (
            EnhancedOrganizationClassifier,
        )

        classifier = EnhancedOrganizationClassifier()
        classifier.load_enhanced_database("config/organizations_enhanced.yaml")
        return classifier

    def test_academic_paper_classification(self, classifier):
        """Test classification of purely academic papers."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        paper = create_test_paper(
            paper_id="acad1",
            title="Academic Paper",
            authors=[
                Author(name="Prof A", affiliations=["MIT"]),
                Author(name="Prof B", affiliations=["Stanford University"]),
                Author(name="Prof C", affiliations=["University of Toronto"]),
            ],
            venue="NeurIPS",
            year=2023,
            citation_count=50,
        )

        result = classifier.classify_paper_authors(paper.authors)
        assert result["classification"] == "academic"
        assert result["confidence"] >= 0.9
        assert result["academic_ratio"] == 1.0
        assert result["industry_ratio"] == 0.0

    def test_industry_paper_classification(self, classifier):
        """Test classification of industry-dominated papers."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        paper = create_test_paper(
            paper_id="ind1",
            title="Industry Paper",
            authors=[
                Author(name="Researcher A", affiliations=["Google Research"]),
                Author(name="Researcher B", affiliations=["Microsoft Research"]),
                Author(name="Researcher C", affiliations=["Meta AI"]),
                Author(name="Prof D", affiliations=["MIT"]),  # One academic
            ],
            venue="ICML",
            year=2023,
            citation_count=100,
        )

        result = classifier.classify_paper_authors(paper.authors)
        assert result["classification"] == "industry"
        assert result["confidence"] >= 0.8
        assert result["academic_ratio"] == 0.25
        assert result["industry_ratio"] == 0.75

    def test_borderline_paper_classification(self, classifier):
        """Test classification of papers near 25% threshold."""
        from compute_forecast.pipeline.metadata_collection.models import Author

        # Exactly 25% industry (should be academic)
        paper = create_test_paper(
            paper_id="border1",
            title="Borderline Paper",
            authors=[
                Author(name="A", affiliations=["MIT"]),
                Author(name="B", affiliations=["Stanford"]),
                Author(name="C", affiliations=["Harvard"]),
                Author(name="D", affiliations=["Google"]),  # 25% industry
            ],
            venue="Conference",
            year=2023,
            citation_count=20,
        )

        result = classifier.classify_paper_authors(paper.authors)
        # At exactly 25%, should be classified as needing review or academic
        assert result["classification"] in ["academic", "needs_manual_review"]
        assert result["industry_ratio"] == 0.25
