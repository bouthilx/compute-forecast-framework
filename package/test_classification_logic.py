#!/usr/bin/env python3
"""Test script to verify classification logic with various scenarios"""

import sys
sys.path.append('/home/bouthilx/projects/preliminary_report/package')

from src.data.models import Paper, Author
from src.analysis.classification import PaperClassifier


def create_test_paper(authors_affiliations):
    """Create a test paper with given author affiliations"""
    authors = []
    for i, (name, affiliation) in enumerate(authors_affiliations):
        authors.append(Author(name=name, affiliation=affiliation))
    
    return Paper(
        title=f"Test Paper",
        authors=authors,
        venue="Test Venue",
        year=2024,
        citations=0
    )


def test_classification_scenarios():
    """Test various classification scenarios"""
    classifier = PaperClassifier()
    
    test_cases = [
        # Format: (description, [(name, affiliation)], expected_category)
        (
            "100% Academic (MIT only)",
            [("Author1", "MIT"), ("Author2", "Stanford University")],
            "academic_eligible"
        ),
        (
            "100% Industry (Google only)", 
            [("Author1", "Google Research"), ("Author2", "OpenAI")],
            "industry_eligible"
        ),
        (
            "20% Industry (1 out of 5)",
            [("A1", "MIT"), ("A2", "Stanford University"), ("A3", "Harvard University"), 
             ("A4", "Princeton University"), ("A5", "Google Research")],
            "academic_eligible"
        ),
        (
            "25% Industry (1 out of 4) - Boundary case",
            [("A1", "MIT"), ("A2", "Stanford University"), ("A3", "Harvard University"), ("A4", "Google Research")],
            "needs_manual_review"
        ),
        (
            "30% Industry (3 out of 10)",
            [("A1", "MIT"), ("A2", "Stanford University"), ("A3", "Harvard University"), 
             ("A4", "Princeton University"), ("A5", "Yale University"), ("A6", "Caltech"),
             ("A7", "University of Toronto"), ("A8", "Google Research"), ("A9", "OpenAI"), ("A10", "Meta AI")],
            "needs_manual_review"
        ),
        (
            "50% Industry (1 out of 2) - The reported case",
            [("Author1", "MIT"), ("Author2", "Google Research")],
            "needs_manual_review"
        ),
        (
            "75% Industry (3 out of 4)",
            [("A1", "MIT"), ("A2", "Google Research"), ("A3", "OpenAI"), ("A4", "Meta AI")],
            "needs_manual_review" 
        ),
        (
            "80% Industry (4 out of 5)",
            [("A1", "MIT"), ("A2", "Google Research"), ("A3", "OpenAI"), ("A4", "Meta AI"), ("A5", "Anthropic")],
            "industry_eligible"
        ),
        (
            "Unknown affiliations only",
            [("A1", "Unknown Organization"), ("A2", "Mystery Foundation")],
            "needs_manual_review"
        ),
        (
            "Mixed with unknowns",
            [("A1", "MIT"), ("A2", "Google Research"), ("A3", "Unknown Foundation")],
            "needs_manual_review"
        )
    ]
    
    print("=== Classification Logic Test Results ===\n")
    
    all_passed = True
    for description, authors_affiliations, expected in test_cases:
        paper = create_test_paper(authors_affiliations)
        analysis = classifier.classify_paper_authorship(paper)
        
        # Calculate percentages for reporting
        total_classified = analysis.academic_count + analysis.industry_count
        if total_classified > 0:
            industry_pct = analysis.industry_count / total_classified
            academic_pct = analysis.academic_count / total_classified
        else:
            industry_pct = 0.0
            academic_pct = 0.0
        
        passed = analysis.category == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status} {description}")
        print(f"   Authors: {len(authors_affiliations)}")
        print(f"   Academic: {analysis.academic_count}, Industry: {analysis.industry_count}, Unknown: {analysis.unknown_count}")
        print(f"   Industry %: {industry_pct:.1%}, Academic %: {academic_pct:.1%}")
        print(f"   Expected: {expected}")
        print(f"   Actual: {analysis.category}")
        print(f"   Confidence: {analysis.confidence:.3f}")
        print()
        
        if not passed:
            all_passed = False
    
    print(f"=== Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'} ===")
    return all_passed


if __name__ == "__main__":
    test_classification_scenarios()