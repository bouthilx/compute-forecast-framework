# Worker 2: Organization Classification System

## Agent ID: worker2
## Work Stream: Author Affiliation Classification
## Duration: 1.5-2 hours
## Dependencies: Worker 0 (Architecture Setup) - MUST complete first

## Objective
Build comprehensive system for classifying paper authors as academic vs industry to enable benchmark separation.

## Deliverables
1. **Organization Lists**: Curated academic and industry institution databases
2. **Affiliation Parser**: Extract and normalize author affiliation strings
3. **Classification Logic**: Academic vs industry determination with confidence scores
4. **Validation System**: Quality checks and manual review flagging

## Detailed Tasks

### Task 2.1: Organization Database Loader (30 minutes)
```python
# File: src/analysis/classification/organizations.py
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
```

**Progress Documentation**: Create `status/worker2-organizations.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "academic_orgs_count": 150,
  "industry_orgs_count": 75,
  "validation_tests": {
    "known_academic_papers": {"tested": 10, "accuracy": 0.95},
    "known_industry_papers": {"tested": 10, "accuracy": 0.90}
  },
  "issues": []
}
```

### Task 2.2: Affiliation Parser Development (45 minutes)
```python
# File: src/analysis/classification/affiliation_parser.py
import re
from typing import Dict, List
from .organizations import OrganizationDatabase
from ...core.logging import setup_logging

class AffiliationParser:
    def __init__(self):
        self.academic_keywords = [
            'university', 'institut', 'college', 'school',
            'research center', 'laboratory', 'department of', 'faculty of'
        ]

        self.industry_keywords = [
            'corporation', 'inc.', 'ltd.', 'llc', 'labs',
            'research lab', 'ai lab', 'technologies'
        ]

    def normalize_affiliation(self, raw_affiliation):
        """Clean and standardize affiliation strings"""
        # Remove common suffixes, standardize abbreviations
        # Handle international character encoding
        # Extract primary institution name

    def extract_all_affiliations(self, author_list):
        """Process all authors and extract clean affiliations"""
```

**Progress Documentation**: Update `status/worker2-parsing.json`

### Task 2.3: Classification Logic with Confidence Scoring (45 minutes)
```python
# File: src/analysis/classification/paper_classifier.py
from typing import Dict, List
from collections import defaultdict
from ..base import BaseAnalyzer
from ...data.models import Paper, Author, AuthorshipAnalysis
from .organizations import OrganizationDatabase
from .affiliation_parser import AffiliationParser
from ...core.logging import setup_logging

class PaperClassifier(BaseAnalyzer):
    def classify_paper_authorship(self, paper, confidence_threshold=0.7):
        """Classify paper as academic/industry eligible with confidence"""

        authors = paper.get('authors', [])
        academic_count = 0
        industry_count = 0
        unknown_count = 0

        author_details = []

        for author in authors:
            affiliation_classification = self.classify_affiliation(
                author.get('affiliation', '')
            )

            author_details.append({
                'name': author.get('name', ''),
                'affiliation': author.get('affiliation', ''),
                'type': affiliation_classification['type'],
                'confidence': affiliation_classification['confidence']
            })

            if affiliation_classification['type'] == 'academic':
                academic_count += 1
            elif affiliation_classification['type'] == 'industry':
                industry_count += 1
            else:
                unknown_count += 1

        return self._make_final_classification(
            academic_count, industry_count, unknown_count, author_details
        )

    def _make_final_classification(self, academic_count, industry_count, unknown_count, author_details):
        """Apply 25% threshold rule with confidence scoring"""
        total_classified = academic_count + industry_count

        if total_classified == 0:
            return {
                'category': 'needs_manual_review',
                'reason': 'all_unknown_affiliations',
                'confidence': 0.0,
                'author_details': author_details
            }

        industry_percentage = industry_count / total_classified
        academic_percentage = academic_count / total_classified

        # Classification logic: <25% industry = academic eligible
        if industry_percentage < 0.25:
            category = 'academic_eligible'
            confidence = academic_percentage
        elif academic_percentage < 0.25:
            category = 'industry_eligible'
            confidence = industry_percentage
        else:
            category = 'needs_manual_review'
            confidence = 0.5

        return {
            'category': category,
            'academic_count': academic_count,
            'industry_count': industry_count,
            'unknown_count': unknown_count,
            'industry_percentage': industry_percentage,
            'academic_percentage': academic_percentage,
            'confidence': confidence,
            'author_details': author_details
        }
```

**Progress Documentation**: Create `status/worker2-classification.json`

### Task 2.4: Validation and Testing System (30 minutes)
```python
# File: src/analysis/classification/validator.py
from typing import List, Dict, Any
from ...data.models import Paper
from ...quality.validators.base import BaseValidator
from .paper_classifier import PaperClassifier
from ...core.logging import setup_logging

class ClassificationValidator(BaseValidator):
    def validate_known_papers(self):
        """Test classification on papers with known academic/industry status"""

    def flag_edge_cases(self, classification_results):
        """Identify papers needing manual review"""

    def generate_validation_report(self):
        """Summary of classification accuracy and edge cases"""
```

**Progress Documentation**: Create `status/worker2-validation.json`

## Output Files
- `src/analysis/classification/organizations.py` - Organization database manager
- `src/analysis/classification/affiliation_parser.py` - Affiliation parsing and normalization
- `src/analysis/classification/paper_classifier.py` - Paper classification with confidence scoring
- `src/analysis/classification/validator.py` - Classification validation system
- `status/worker2-*.json` - Progress documentation files

## Success Criteria
- [ ] 150+ academic organizations, 75+ industry organizations catalogued
- [ ] Affiliation parser handles 95%+ of common formats
- [ ] Classification achieves >90% accuracy on validation set
- [ ] Clear flagging system for manual review cases
- [ ] Progress documentation complete for orchestration

## Coordination Points
- **Dependencies**: Worker 0 must complete first (architecture setup)
- **Outputs needed by**: Worker 6 (Paper Collection) and Worker 7 (Final Selection)
- **Status updates**: Every 30 minutes to `status/worker2-overall.json`
- **Validation data**: Use current Mila papers for testing

## Risk Mitigation
- **Incomplete affiliations**: Keyword-based backup classification
- **International variations**: Comprehensive institution name variations
- **Edge cases**: Conservative flagging for manual review
- **Accuracy validation**: Test on known academic/industry papers

## Communication Protocol
Update `status/worker2-overall.json` every 30 minutes:
```json
{
  "worker_id": "worker2",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 60,
  "current_task": "Task 2.3: Classification Logic",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "ready_for_handoff": false,
  "validation_accuracy": {
    "academic_papers": 0.92,
    "industry_papers": 0.88
  },
  "outputs_available": ["organizations.py", "affiliation_parser.py"]
}
```
