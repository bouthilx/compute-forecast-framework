#!/usr/bin/env python3
"""Test script for enhanced organization classification."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from analysis.classification.enhanced_organizations import (
    EnhancedOrganizationClassifier,
    OrganizationType,
    OrganizationRecord,
)
from analysis.classification.enhanced_affiliation_parser import EnhancedAffiliationParser
from data.models import Paper, Author


def test_basic_classification():
    """Test basic classification functionality."""
    print("Testing basic classification...")
    
    classifier = EnhancedOrganizationClassifier()
    
    # Add some test organizations
    test_orgs = [
        OrganizationRecord(
            name="Massachusetts Institute of Technology",
            type=OrganizationType.ACADEMIC,
            aliases=["MIT", "M.I.T."],
            domains=["mit.edu"],
            keywords=["Laboratory", "Department"],
        ),
        OrganizationRecord(
            name="Google Research",
            type=OrganizationType.INDUSTRY,
            aliases=["Google", "Google AI"],
            domains=["google.com"],
            keywords=["Research", "Labs"],
        ),
    ]
    
    for org in test_orgs:
        classifier.add_organization(org)
    
    # Test exact match
    result = classifier.classify_with_confidence("MIT")
    print(f"  MIT -> {result.type.value}, confidence: {result.confidence:.2f}")
    assert result.type == OrganizationType.ACADEMIC
    assert result.confidence >= 0.9
    
    # Test fuzzy match
    result = classifier.classify_with_confidence("Massachusets Institute of Technology")  # Typo
    print(f"  Massachusets (typo) -> {result.type.value}, confidence: {result.confidence:.2f}")
    assert result.type == OrganizationType.ACADEMIC
    
    # Test domain match
    result = classifier.classify_with_confidence("john.doe@mit.edu")
    print(f"  @mit.edu -> {result.type.value}, confidence: {result.confidence:.2f}")
    assert result.type == OrganizationType.ACADEMIC
    
    print("✓ Basic classification tests passed\n")


def test_enhanced_parser():
    """Test enhanced affiliation parser."""
    print("Testing enhanced affiliation parser...")
    
    parser = EnhancedAffiliationParser()
    
    # Test complex affiliation
    affiliation = "Dept. of Computer Science, MIT, Cambridge, MA, USA"
    result = parser.parse_complex_affiliation(affiliation)
    print(f"  Parsed: {affiliation}")
    print(f"    -> Organization: {result['organization']}")
    print(f"    -> Department: {result['department']}")
    print(f"    -> City: {result['city']}")
    
    assert result["organization"] == "MIT"
    assert result["department"] == "Computer Science"
    assert result["city"] == "Cambridge"
    
    # Test edge cases
    multi_affil = "MIT; Google Research"
    result = parser.handle_edge_cases(multi_affil)
    print(f"  Multi-affiliation: {multi_affil} -> {result}")
    assert result is not None
    
    print("✓ Parser tests passed\n")


def test_paper_classification():
    """Test paper-level classification."""
    print("Testing paper classification...")
    
    classifier = EnhancedOrganizationClassifier()
    classifier.load_enhanced_database("config/organizations_enhanced.yaml")
    
    # Academic paper
    paper1 = Paper(
        title="Academic Paper",
        authors=[
            Author(name="Prof A", affiliation="MIT"),
            Author(name="Prof B", affiliation="Stanford University"),
            Author(name="Prof C", affiliation="Harvard"),
        ],
        venue="NeurIPS",
        year=2023,
        citations=10,
    )
    
    result = classifier.classify_paper_authors(paper1.authors)
    print(f"  Academic paper -> {result['classification']}, confidence: {result['confidence']:.2f}")
    assert result["classification"] == "academic"
    
    # Industry paper
    paper2 = Paper(
        title="Industry Paper",
        authors=[
            Author(name="Researcher A", affiliation="Google Research"),
            Author(name="Researcher B", affiliation="OpenAI"),
            Author(name="Researcher C", affiliation="Microsoft Research"),
        ],
        venue="ICML",
        year=2023,
        citations=20,
    )
    
    result = classifier.classify_paper_authors(paper2.authors)
    print(f"  Industry paper -> {result['classification']}, confidence: {result['confidence']:.2f}")
    assert result["classification"] == "industry"
    
    # Mixed paper (25% threshold test)
    paper3 = Paper(
        title="Mixed Paper",
        authors=[
            Author(name="A", affiliation="MIT"),
            Author(name="B", affiliation="Stanford"),
            Author(name="C", affiliation="Berkeley"),
            Author(name="D", affiliation="Google"),  # 25% industry
        ],
        venue="Conference",
        year=2023,
        citations=5,
    )
    
    result = classifier.classify_paper_authors(paper3.authors)
    print(f"  Mixed paper (25% industry) -> {result['classification']}")
    print(f"    Industry ratio: {result['industry_ratio']:.2%}")
    
    print("✓ Paper classification tests passed\n")


def test_database_coverage():
    """Test database coverage of major institutions."""
    print("Testing database coverage...")
    
    classifier = EnhancedOrganizationClassifier()
    classifier.load_enhanced_database("config/organizations_enhanced.yaml")
    
    # Count organizations
    org_count = classifier.get_organization_count()
    print(f"  Total organizations: {org_count}")
    assert org_count >= 225
    
    # Check coverage by type
    for org_type in [OrganizationType.ACADEMIC, OrganizationType.INDUSTRY, 
                     OrganizationType.GOVERNMENT, OrganizationType.NON_PROFIT]:
        orgs = classifier.get_organizations_by_type(org_type)
        print(f"  {org_type.value.title()}: {len(orgs)} organizations")
    
    # Test major institutions
    test_affiliations = [
        ("MIT Computer Science", OrganizationType.ACADEMIC),
        ("Google Research Mountain View", OrganizationType.INDUSTRY),
        ("National Science Foundation", OrganizationType.GOVERNMENT),
        ("Allen Institute for AI", OrganizationType.NON_PROFIT),
    ]
    
    print("\n  Testing major institutions:")
    for affiliation, expected_type in test_affiliations:
        result = classifier.classify_with_confidence(affiliation)
        print(f"    {affiliation} -> {result.type.value} (confidence: {result.confidence:.2f})")
        assert result.type == expected_type
        assert result.confidence > 0.7
    
    print("✓ Database coverage tests passed\n")


def main():
    """Run all tests."""
    print("=== Enhanced Organization Classification Tests ===\n")
    
    try:
        test_basic_classification()
        test_enhanced_parser()
        test_paper_classification()
        test_database_coverage()
        
        print("✅ All tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())