"""Enhanced organization classifier with fuzzy matching and confidence scoring."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from dataclasses import dataclass
from rapidfuzz import fuzz
from .organizations import OrganizationDatabase
from ...core.logging import setup_logging


class OrganizationType(Enum):
    """Types of organizations for classification."""
    ACADEMIC = "academic"
    INDUSTRY = "industry"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    UNKNOWN = "unknown"


@dataclass
class OrganizationRecord:
    """Enhanced organization record with aliases and domains."""
    name: str
    type: OrganizationType
    aliases: List[str] = None
    domains: List[str] = None
    keywords: List[str] = None
    confidence: float = 1.0

    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.aliases is None:
            self.aliases = []
        if self.domains is None:
            self.domains = []
        if self.keywords is None:
            self.keywords = []


@dataclass
class ClassificationResult:
    """Result of organization classification with confidence and evidence."""
    organization: Optional[str]
    type: OrganizationType
    confidence: float
    match_method: str  # exact, alias, domain, keyword, fuzzy
    evidence: Dict[str, Any]


class EnhancedOrganizationClassifier(OrganizationDatabase):
    """Enhanced classifier with fuzzy matching and detailed confidence scoring."""
    
    def __init__(self):
        """Initialize enhanced classifier."""
        super().__init__()
        self.fuzzy_threshold = 85  # 85% similarity for fuzzy matching
        self.industry_threshold = 0.25  # 25% industry authors
        self._enhanced_orgs: Dict[str, OrganizationRecord] = {}
        self._domain_map: Dict[str, str] = {}  # domain -> org name
        self._alias_map: Dict[str, str] = {}   # alias -> org name
        
    def load_enhanced_database(self, yaml_path: str) -> None:
        """Load expanded organization database from YAML."""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Load organizations by type
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
            
            self.logger.info(f"Loaded {len(self._enhanced_orgs)} enhanced organizations")
            
        except Exception as e:
            self.logger.error(f"Failed to load enhanced organizations: {e}")
            raise
    
    def add_organization(self, org: OrganizationRecord) -> None:
        """Add new organization to database."""
        # Store in main dict
        self._enhanced_orgs[org.name.lower()] = org
        
        # Build alias map
        for alias in org.aliases:
            self._alias_map[alias.lower()] = org.name
        
        # Build domain map
        for domain in org.domains:
            self._domain_map[domain.lower()] = org.name
    
    def classify_with_confidence(self, affiliation: str) -> ClassificationResult:
        """Classify with detailed confidence scoring."""
        if not affiliation:
            return ClassificationResult(
                organization=None,
                type=OrganizationType.UNKNOWN,
                confidence=0.0,
                match_method="none",
                evidence={"reason": "empty_affiliation"}
            )
        
        affiliation_lower = affiliation.lower().strip()
        
        # 1. Try exact match
        exact_result = self._try_exact_match(affiliation_lower)
        if exact_result:
            return exact_result
        
        # 2. Try alias match
        alias_result = self._try_alias_match(affiliation_lower)
        if alias_result:
            return alias_result
        
        # 3. Try domain match
        domain_result = self._try_domain_match(affiliation_lower)
        if domain_result:
            return domain_result
        
        # 4. Try fuzzy match
        fuzzy_result = self._try_fuzzy_match(affiliation_lower)
        if fuzzy_result:
            return fuzzy_result
        
        # 5. Try keyword match
        keyword_result = self._try_keyword_match(affiliation_lower)
        if keyword_result:
            return keyword_result
        
        # 6. Unknown organization
        return ClassificationResult(
            organization=None,
            type=OrganizationType.UNKNOWN,
            confidence=0.0,
            match_method="none",
            evidence={"reason": "no_match_found"}
        )
    
    def _try_exact_match(self, affiliation_lower: str) -> Optional[ClassificationResult]:
        """Try exact organization name match."""
        for org_name, org in self._enhanced_orgs.items():
            if org_name in affiliation_lower:
                return ClassificationResult(
                    organization=org.name,
                    type=org.type,
                    confidence=0.95,
                    match_method="exact",
                    evidence={"matched_name": org_name}
                )
        return None
    
    def _try_alias_match(self, affiliation_lower: str) -> Optional[ClassificationResult]:
        """Try matching using organization aliases."""
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
        return None
    
    def _try_domain_match(self, affiliation_lower: str) -> Optional[ClassificationResult]:
        """Try matching using email domains."""
        # Look for email addresses or domain patterns
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
        
        # Also check if domain appears without @ symbol
        for domain, org_name in self._domain_map.items():
            if domain in affiliation_lower:
                org = self._enhanced_orgs[org_name.lower()]
                return ClassificationResult(
                    organization=org.name,
                    type=org.type,
                    confidence=0.85,
                    match_method="domain",
                    evidence={"matched_domain": domain}
                )
        
        return None
    
    def _try_fuzzy_match(self, affiliation_lower: str) -> Optional[ClassificationResult]:
        """Try fuzzy string matching for name variations."""
        best_score = 0
        best_match = None
        
        # Check against organization names
        for org_name, org in self._enhanced_orgs.items():
            score = fuzz.ratio(org_name, affiliation_lower)
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = org
        
        # Check against aliases
        for alias, org_name in self._alias_map.items():
            score = fuzz.ratio(alias, affiliation_lower)
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = self._enhanced_orgs[org_name.lower()]
        
        if best_match:
            # Scale confidence based on fuzzy match score
            confidence = 0.7 * (best_score / 100)
            return ClassificationResult(
                organization=best_match.name,
                type=best_match.type,
                confidence=confidence,
                match_method="fuzzy",
                evidence={"fuzzy_score": best_score}
            )
        
        return None
    
    def _try_keyword_match(self, affiliation_lower: str) -> Optional[ClassificationResult]:
        """Try keyword-based classification."""
        # Count keywords by type
        type_scores = {org_type: 0 for org_type in OrganizationType if org_type != OrganizationType.UNKNOWN}
        
        for org in self._enhanced_orgs.values():
            for keyword in org.keywords:
                if keyword.lower() in affiliation_lower:
                    type_scores[org.type] += 1
        
        # Find dominant type
        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]
        
        if best_score > 0:
            # Lower confidence for keyword-only matches
            confidence = min(0.7, best_score * 0.2)
            return ClassificationResult(
                organization=None,
                type=best_type,
                confidence=confidence,
                match_method="keyword",
                evidence={"keyword_matches": best_score}
            )
        
        return None
    
    def classify_paper_authors(self, authors: List['Author']) -> Dict[str, Any]:
        """Classify paper based on author affiliations."""
        academic_count = 0
        industry_count = 0
        government_count = 0
        nonprofit_count = 0
        unknown_count = 0
        
        author_breakdown = []
        total_confidence = 0.0
        
        for author in authors:
            affiliation = author.affiliation if hasattr(author, 'affiliation') else ""
            result = self.classify_with_confidence(affiliation)
            
            author_breakdown.append({
                "name": author.name if hasattr(author, 'name') else "",
                "affiliation": affiliation,
                "classification": result.type.value,
                "confidence": result.confidence,
                "organization": result.organization
            })
            
            total_confidence += result.confidence
            
            if result.type == OrganizationType.ACADEMIC:
                academic_count += 1
            elif result.type == OrganizationType.INDUSTRY:
                industry_count += 1
            elif result.type == OrganizationType.GOVERNMENT:
                government_count += 1
            elif result.type == OrganizationType.NON_PROFIT:
                nonprofit_count += 1
            else:
                unknown_count += 1
        
        total_authors = len(authors)
        classified_authors = total_authors - unknown_count
        
        if classified_authors == 0:
            classification = "unknown"
            confidence = 0.0
        else:
            # Apply 25% threshold rule
            industry_ratio = industry_count / classified_authors
            academic_ratio = academic_count / classified_authors
            
            if industry_ratio >= self.industry_threshold:
                classification = "industry"
            else:
                classification = "academic"
            
            confidence = total_confidence / total_authors if total_authors > 0 else 0.0
        
        return {
            "classification": classification,
            "confidence": confidence,
            "academic_ratio": academic_ratio if classified_authors > 0 else 0.0,
            "industry_ratio": industry_ratio if classified_authors > 0 else 0.0,
            "author_breakdown": author_breakdown,
            "counts": {
                "academic": academic_count,
                "industry": industry_count,
                "government": government_count,
                "non_profit": nonprofit_count,
                "unknown": unknown_count
            }
        }
    
    def get_organization_count(self) -> int:
        """Get total number of organizations in database."""
        return len(self._enhanced_orgs)
    
    def get_organizations_by_type(self, org_type: OrganizationType) -> List[OrganizationRecord]:
        """Get all organizations of a specific type."""
        return [org for org in self._enhanced_orgs.values() if org.type == org_type]