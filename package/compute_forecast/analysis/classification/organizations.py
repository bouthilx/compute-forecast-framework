import yaml
from pathlib import Path
from typing import List, Dict, Set
from ...core.config import ConfigManager
from ...core.logging import setup_logging


class OrganizationDatabase:
    """Manages academic and industry organization databases"""
    
    def __init__(self):
        self.logger = setup_logging()
        self._academic_orgs = None
        self._industry_orgs = None
        self._load_organizations()
    
    def _load_organizations(self):
        """Load organization data from configuration"""
        try:
            with open('config/organizations.yaml', 'r') as f:
                org_data = yaml.safe_load(f)
            
            # Flatten academic organizations
            academic_data = org_data['academic_organizations']
            self._academic_orgs = []
            for tier, orgs in academic_data.items():
                self._academic_orgs.extend(orgs)
            
            # Flatten industry organizations  
            industry_data = org_data['industry_organizations']
            self._industry_orgs = []
            for category, orgs in industry_data.items():
                self._industry_orgs.extend(orgs)
            
            self.logger.info(f"Loaded {len(self._academic_orgs)} academic and {len(self._industry_orgs)} industry organizations")
            
        except Exception as e:
            self.logger.error(f"Failed to load organizations: {e}")
            raise
    
    def get_academic_organizations(self) -> List[str]:
        """Get list of academic organizations"""
        return self._academic_orgs.copy()
    
    def get_industry_organizations(self) -> List[str]:
        """Get list of industry organizations"""
        return self._industry_orgs.copy()
    
    def is_academic_organization(self, affiliation: str) -> bool:
        """Check if affiliation matches academic organization"""
        affiliation_lower = affiliation.lower()
        return any(org.lower() in affiliation_lower for org in self._academic_orgs)
    
    def is_industry_organization(self, affiliation: str) -> bool:
        """Check if affiliation matches industry organization"""
        affiliation_lower = affiliation.lower()
        return any(org.lower() in affiliation_lower for org in self._industry_orgs)
    
    def get_organization_match(self, affiliation: str) -> Dict[str, str]:
        """Get the specific organization that matches affiliation"""
        affiliation_lower = affiliation.lower()
        
        # Check academic first
        for org in self._academic_orgs:
            if org.lower() in affiliation_lower:
                return {'type': 'academic', 'organization': org}
        
        # Check industry
        for org in self._industry_orgs:
            if org.lower() in affiliation_lower:
                return {'type': 'industry', 'organization': org}
        
        return {'type': 'unknown', 'organization': None}