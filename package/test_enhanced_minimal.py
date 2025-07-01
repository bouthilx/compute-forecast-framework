#!/usr/bin/env python3
"""Minimal test for enhanced classification without full package dependencies."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from dataclasses import dataclass


# Mock logging setup
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")

def setup_logging():
    return MockLogger()


# Mock fuzz module
class MockFuzz:
    @staticmethod
    def ratio(s1, s2):
        if not s1 or not s2:
            return 0
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        # Simple substring check
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 90
        # Character overlap
        common = sum(1 for c1, c2 in zip(s1_lower, s2_lower) if c1 == c2)
        return int(100 * common / max(len(s1), len(s2)))


# Minimal implementation of enhanced classifier
class OrganizationType(Enum):
    ACADEMIC = "academic"
    INDUSTRY = "industry"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    UNKNOWN = "unknown"


@dataclass
class OrganizationRecord:
    name: str
    type: OrganizationType
    aliases: List[str] = None
    domains: List[str] = None
    keywords: List[str] = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.domains is None:
            self.domains = []
        if self.keywords is None:
            self.keywords = []


@dataclass
class ClassificationResult:
    organization: Optional[str]
    type: OrganizationType
    confidence: float
    match_method: str
    evidence: Dict[str, Any]


class MinimalEnhancedClassifier:
    def __init__(self):
        self.logger = setup_logging()
        self.fuzzy_threshold = 85
        self._enhanced_orgs: Dict[str, OrganizationRecord] = {}
        self._domain_map: Dict[str, str] = {}
        self._alias_map: Dict[str, str] = {}
        self.fuzz = MockFuzz()
    
    def add_organization(self, org: OrganizationRecord) -> None:
        self._enhanced_orgs[org.name.lower()] = org
        for alias in org.aliases:
            self._alias_map[alias.lower()] = org.name
        for domain in org.domains:
            self._domain_map[domain.lower()] = org.name
    
    def classify_with_confidence(self, affiliation: str) -> ClassificationResult:
        if not affiliation:
            return ClassificationResult(
                organization=None,
                type=OrganizationType.UNKNOWN,
                confidence=0.0,
                match_method="none",
                evidence={"reason": "empty_affiliation"}
            )
        
        affiliation_lower = affiliation.lower().strip()
        
        # Try exact match
        for org_name, org in self._enhanced_orgs.items():
            if org_name in affiliation_lower:
                return ClassificationResult(
                    organization=org.name,
                    type=org.type,
                    confidence=0.95,
                    match_method="exact",
                    evidence={"matched_name": org_name}
                )
        
        # Try alias match
        for alias, org_name in self._alias_map.items():
            if alias in affiliation_lower:
                org = self._enhanced_orgs[org_name.lower()]
                return ClassificationResult(
                    organization=org.name,
                    type=org.type,
                    confidence=0.9,
                    match_method="alias",
                    evidence={"matched_alias": alias}
                )
        
        # Try domain match
        import re
        email_pattern = r'@([\w.-]+\.\w+)'
        domain_matches = re.findall(email_pattern, affiliation_lower)
        
        for domain in domain_matches:
            if domain in self._domain_map:
                org_name = self._domain_map[domain]
                org = self._enhanced_orgs[org_name.lower()]
                return ClassificationResult(
                    organization=org.name,
                    type=org.type,
                    confidence=0.85,
                    match_method="domain",
                    evidence={"matched_domain": domain}
                )
        
        # Try fuzzy match
        best_score = 0
        best_match = None
        
        for org_name, org in self._enhanced_orgs.items():
            score = self.fuzz.ratio(org_name, affiliation_lower)
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = org
        
        if best_match:
            confidence = 0.7 * (best_score / 100)
            return ClassificationResult(
                organization=best_match.name,
                type=best_match.type,
                confidence=confidence,
                match_method="fuzzy",
                evidence={"fuzzy_score": best_score}
            )
        
        return ClassificationResult(
            organization=None,
            type=OrganizationType.UNKNOWN,
            confidence=0.0,
            match_method="none",
            evidence={"reason": "no_match_found"}
        )
    
    def load_enhanced_database(self, yaml_path: str) -> None:
        """Load organization database from YAML."""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            count = 0
            for org_type in OrganizationType:
                if org_type == OrganizationType.UNKNOWN:
                    continue
                    
                type_key = org_type.value
                if type_key in data:
                    for org_data in data[type_key]:
                        org = OrganizationRecord(
                            name=org_data['name'],
                            type=org_type,
                            aliases=org_data.get('aliases', []),
                            domains=org_data.get('domains', []),
                            keywords=org_data.get('keywords', [])
                        )
                        self.add_organization(org)
                        count += 1
            
            self.logger.info(f"Loaded {count} organizations")
            
        except Exception as e:
            self.logger.error(f"Failed to load organizations: {e}")
            raise
    
    def get_organization_count(self) -> int:
        return len(self._enhanced_orgs)
    
    def get_organizations_by_type(self, org_type: OrganizationType) -> List[OrganizationRecord]:
        return [org for org in self._enhanced_orgs.values() if org.type == org_type]


def test_basic_functionality():
    """Test basic classification functionality."""
    print("\n=== Testing Basic Functionality ===")
    
    classifier = MinimalEnhancedClassifier()
    
    # Add test organizations
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
    
    # Test cases
    test_cases = [
        ("MIT", OrganizationType.ACADEMIC, "alias"),
        ("Massachusetts Institute of Technology", OrganizationType.ACADEMIC, "exact"),
        ("john.doe@mit.edu", OrganizationType.ACADEMIC, "domain"),
        ("Google Research", OrganizationType.INDUSTRY, "exact"),
        ("Unknown Company", OrganizationType.UNKNOWN, "none"),
    ]
    
    passed = 0
    for affiliation, expected_type, expected_method in test_cases:
        result = classifier.classify_with_confidence(affiliation)
        if result.type == expected_type:
            print(f"✓ '{affiliation}' -> {result.type.value} (method: {result.match_method}, confidence: {result.confidence:.2f})")
            passed += 1
        else:
            print(f"✗ '{affiliation}' -> Expected {expected_type.value}, got {result.type.value}")
    
    print(f"\nPassed {passed}/{len(test_cases)} tests")
    return passed == len(test_cases)


def test_database_loading():
    """Test loading from YAML database."""
    print("\n=== Testing Database Loading ===")
    
    classifier = MinimalEnhancedClassifier()
    
    yaml_path = Path("config/organizations_enhanced.yaml")
    if not yaml_path.exists():
        print(f"✗ Database file not found: {yaml_path}")
        return False
    
    try:
        classifier.load_enhanced_database(str(yaml_path))
        count = classifier.get_organization_count()
        print(f"✓ Loaded {count} organizations")
        
        # Check organization types
        for org_type in [OrganizationType.ACADEMIC, OrganizationType.INDUSTRY, 
                        OrganizationType.GOVERNMENT, OrganizationType.NON_PROFIT]:
            orgs = classifier.get_organizations_by_type(org_type)
            print(f"  - {org_type.value}: {len(orgs)} organizations")
        
        # Test some known organizations
        test_affiliations = [
            ("MIT Computer Science Department", OrganizationType.ACADEMIC),
            ("Google Research Mountain View", OrganizationType.INDUSTRY),
            ("National Science Foundation Grant", OrganizationType.GOVERNMENT),
            ("Allen Institute for AI", OrganizationType.NON_PROFIT),
        ]
        
        print("\nTesting classification of known organizations:")
        passed = 0
        for affiliation, expected_type in test_affiliations:
            result = classifier.classify_with_confidence(affiliation)
            if result.type == expected_type:
                print(f"✓ '{affiliation}' -> {result.type.value}")
                passed += 1
            else:
                print(f"✗ '{affiliation}' -> Expected {expected_type.value}, got {result.type.value}")
        
        print(f"\nPassed {passed}/{len(test_affiliations)} classification tests")
        return count >= 225 and passed == len(test_affiliations)
        
    except Exception as e:
        print(f"✗ Error loading database: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Enhanced Organization Classification Tests ===")
    
    all_passed = True
    
    # Test basic functionality
    if not test_basic_functionality():
        all_passed = False
    
    # Test database loading
    if not test_database_loading():
        all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())