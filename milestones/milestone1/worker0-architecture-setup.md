# Worker 0: Architecture & Codebase Setup

## Agent ID: worker0
## Work Stream: Foundation Architecture Setup
## Duration: 1 hour
## Dependencies: None (must complete before all other workers)

## Objective
Establish the foundational codebase architecture, interfaces, and configuration management that all other workers will build upon.

## Deliverables
1. **Directory Structure**: Complete organized codebase layout
2. **Base Classes & Interfaces**: Abstract base classes for all components
3. **Configuration Management**: YAML-based settings and data files
4. **Data Models**: Core data structures (Paper, Author, etc.)
5. **Logging & Error Handling**: Centralized logging and exception framework

## Detailed Tasks

### Task 0.1: Directory Structure Creation (10 minutes)
```bash
# Create complete directory structure
mkdir -p src/{core,data/{sources,collectors},analysis/{computational,classification,venues},quality/validators,selection/selectors,orchestration}
mkdir -p config data/{raw,processed,benchmarks,cache} status reports tests/{unit,integration,fixtures} scripts
```

**Progress Documentation**: Create `status/worker0-structure.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "directories_created": 25,
  "structure_validated": true,
  "issues": []
}
```

### Task 0.2: Core Infrastructure Setup (15 minutes)
```python
# File: src/core/__init__.py
"""Core infrastructure for paper collection and analysis system."""

# File: src/core/config.py
import yaml
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass

@dataclass
class CitationSourceConfig:
    rate_limit: float
    retry_attempts: int
    api_key: str = None
    timeout: int = 30

@dataclass
class CollectionConfig:
    papers_per_domain_year: int
    total_target_min: int
    total_target_max: int
    citation_threshold_base: int

@dataclass
class QualityConfig:
    computational_richness_min: float
    citation_reliability_min: float
    institution_coverage_min: float
    overall_quality_min: float

class ConfigManager:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self._config = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if self._config is None:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        return self._config
    
    def get_citation_config(self, source: str) -> CitationSourceConfig:
        """Get configuration for specific citation source"""
        config = self.load_config()
        source_config = config['citation_sources'][source]
        return CitationSourceConfig(**source_config)
    
    def get_collection_config(self) -> CollectionConfig:
        """Get paper collection configuration"""
        config = self.load_config()
        return CollectionConfig(**config['collection_targets'])
    
    def get_quality_config(self) -> QualityConfig:
        """Get quality control configuration"""
        config = self.load_config()
        return QualityConfig(**config['quality_thresholds'])

# File: src/core/logging.py
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup centralized logging configuration"""
    
    # Create logs directory if it doesn't exist
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

# File: src/core/exceptions.py
class PaperCollectionError(Exception):
    """Base exception for paper collection system"""
    pass

class APIError(PaperCollectionError):
    """Error accessing external APIs"""
    pass

class ValidationError(PaperCollectionError):
    """Error in data validation"""
    pass

class ConfigurationError(PaperCollectionError):
    """Error in configuration"""
    pass

class WorkerError(PaperCollectionError):
    """Error in worker execution"""
    pass
```

### Task 0.3: Data Models Definition (15 minutes)
```python
# File: src/data/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class Author:
    name: str
    affiliation: str = ""
    author_id: str = ""
    email: str = ""
    
    def normalize_affiliation(self) -> str:
        """Get normalized affiliation string"""
        return self.affiliation.lower().strip()

@dataclass
class ComputationalAnalysis:
    computational_richness: float
    keyword_matches: Dict[str, int]
    resource_metrics: Dict[str, Any]
    experimental_indicators: Dict[str, Any]
    confidence_score: float

@dataclass 
class AuthorshipAnalysis:
    category: str  # 'academic_eligible', 'industry_eligible', 'needs_manual_review'
    academic_count: int
    industry_count: int
    unknown_count: int
    confidence: float
    author_details: List[Dict[str, str]]

@dataclass
class VenueAnalysis:
    venue_score: float
    domain_relevance: float
    computational_focus: float
    importance_ranking: int

@dataclass
class Paper:
    title: str
    authors: List[Author]
    venue: str
    year: int
    citations: int
    abstract: str = ""
    doi: str = ""
    urls: List[str] = field(default_factory=list)
    
    # Analysis results (populated by workers)
    computational_analysis: Optional[ComputationalAnalysis] = None
    authorship_analysis: Optional[AuthorshipAnalysis] = None
    venue_analysis: Optional[VenueAnalysis] = None
    
    # Collection metadata
    source: str = ""
    collection_timestamp: str = ""
    mila_domain: str = ""
    collection_method: str = ""
    selection_rank: Optional[int] = None
    benchmark_type: str = ""  # 'academic' or 'industry'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paper to dictionary for JSON serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, list) and value and hasattr(value[0], '__dict__'):
                result[key] = [item.__dict__ for item in value]
            elif hasattr(value, '__dict__'):
                result[key] = value.__dict__ if value else None
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """Create Paper from dictionary"""
        # Handle authors
        authors = [Author(**author_data) for author_data in data.get('authors', [])]
        
        # Handle analysis objects
        comp_analysis = None
        if data.get('computational_analysis'):
            comp_analysis = ComputationalAnalysis(**data['computational_analysis'])
        
        auth_analysis = None
        if data.get('authorship_analysis'):
            auth_analysis = AuthorshipAnalysis(**data['authorship_analysis'])
        
        venue_analysis = None
        if data.get('venue_analysis'):
            venue_analysis = VenueAnalysis(**data['venue_analysis'])
        
        # Create paper with processed data
        paper_data = data.copy()
        paper_data['authors'] = authors
        paper_data['computational_analysis'] = comp_analysis
        paper_data['authorship_analysis'] = auth_analysis
        paper_data['venue_analysis'] = venue_analysis
        
        return cls(**paper_data)

@dataclass
class CollectionQuery:
    domain: str
    year: int
    venue: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    min_citations: int = 0
    max_results: int = 50

@dataclass
class CollectionResult:
    papers: List[Paper]
    query: CollectionQuery
    source: str
    collection_timestamp: str
    success_count: int
    failed_count: int
    errors: List[str] = field(default_factory=list)
```

### Task 0.4: Base Interface Classes (15 minutes)
```python
# File: src/data/sources/base.py
from abc import ABC, abstractmethod
from typing import List
from ..models import Paper, CollectionQuery, CollectionResult

class BaseCitationSource(ABC):
    """Abstract base class for citation data sources"""
    
    def __init__(self, config: dict):
        self.config = config
        self.rate_limit = config.get('rate_limit', 1.0)
        self.retry_attempts = config.get('retry_attempts', 3)
    
    @abstractmethod
    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search for papers using this citation source"""
        pass
    
    @abstractmethod
    def get_paper_details(self, paper_id: str) -> Paper:
        """Get detailed information for a specific paper"""
        pass
    
    @abstractmethod
    def test_connectivity(self) -> bool:
        """Test if the citation source is accessible"""
        pass
    
    def get_rate_limit(self) -> float:
        """Get rate limit for this source"""
        return self.rate_limit

# File: src/data/collectors/base.py
from abc import ABC, abstractmethod
from typing import List
from ..models import Paper, CollectionQuery

class BaseCollector(ABC):
    """Abstract base class for paper collectors"""
    
    @abstractmethod
    def collect(self, query: CollectionQuery) -> List[Paper]:
        """Collect papers based on query"""
        pass
    
    @abstractmethod
    def validate_collection(self, papers: List[Paper]) -> bool:
        """Validate collected papers"""
        pass

# File: src/analysis/base.py
from abc import ABC, abstractmethod
from typing import Any
from ..data.models import Paper

class BaseAnalyzer(ABC):
    """Abstract base class for paper analyzers"""
    
    @abstractmethod
    def analyze(self, paper: Paper) -> Any:
        """Analyze a paper and return results"""
        pass
    
    @abstractmethod
    def get_confidence_score(self, analysis_result: Any) -> float:
        """Get confidence score for analysis result"""
        pass

# File: src/quality/validators/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ...data.models import Paper

class BaseValidator(ABC):
    """Abstract base class for quality validators"""
    
    @abstractmethod
    def validate(self, papers: List[Paper]) -> Dict[str, Any]:
        """Validate papers and return validation results"""
        pass
    
    @abstractmethod
    def get_validation_score(self, validation_result: Dict[str, Any]) -> float:
        """Get overall validation score"""
        pass
```

### Task 0.5: Configuration Files Setup (15 minutes)
```yaml
# File: config/settings.yaml
citation_sources:
  google_scholar:
    rate_limit: 1.0
    retry_attempts: 3
    timeout: 30
  
  semantic_scholar:
    rate_limit: 0.1
    retry_attempts: 3
    timeout: 30
    api_key: null
  
  openalex:
    rate_limit: 0.05
    retry_attempts: 3
    timeout: 30

collection_targets:
  papers_per_domain_year: 8
  total_target_min: 360
  total_target_max: 720
  citation_threshold_base: 50

quality_thresholds:
  computational_richness_min: 0.4
  citation_reliability_min: 0.8
  institution_coverage_min: 0.3
  overall_quality_min: 0.7

logging:
  level: "INFO"
  file: "logs/milestone1.log"

# File: config/organizations.yaml
academic_organizations:
  tier1:
    - "MIT"
    - "Stanford University"
    - "Carnegie Mellon University"
    - "UC Berkeley"
    - "Harvard University"
    - "Princeton University"
  
  tier2:
    - "University of Washington"
    - "NYU"
    - "Columbia University"
    - "University of Chicago"
  
  international:
    - "University of Oxford"
    - "University of Cambridge"
    - "ETH Zurich"
    - "University of Toronto"
    - "McGill University"
  
  research_institutes:
    - "Max Planck Institute"
    - "Allen Institute"
    - "Mila"
    - "Vector Institute"

industry_organizations:
  big_tech:
    - "Google"
    - "Google Research"
    - "Google DeepMind"
    - "DeepMind"
    - "OpenAI"
    - "Microsoft Research"
    - "Meta AI"
    - "Apple"
    - "Amazon"
    - "NVIDIA"
  
  ai_companies:
    - "Anthropic"
    - "Cohere"
    - "Hugging Face"
    - "Stability AI"
    - "Character.AI"
  
  traditional_research:
    - "IBM Research"
    - "Adobe Research"
    - "Salesforce Research"

# File: config/venues.yaml
venues_by_domain:
  computer_vision:
    tier1: ["CVPR", "ICCV", "ECCV"]
    tier2: ["BMVC", "WACV", "ACCV"]
    medical: ["MICCAI", "IPMI", "ISBI"]
  
  nlp:
    tier1: ["ACL", "EMNLP", "NAACL"]
    tier2: ["COLING", "EACL", "CoNLL"]
    specialized: ["WMT", "SemEval"]
  
  ml_general:
    tier1: ["NeurIPS", "ICML", "ICLR"]
    tier2: ["AISTATS", "UAI", "COLT"]
  
  reinforcement_learning:
    specialized: ["AAMAS", "AAAI", "IJCAI"]
    robotics: ["ICRA", "IROS", "RSS"]

computational_focus_scores:
  "CVPR": 0.9
  "ICCV": 0.9
  "NeurIPS": 0.95
  "ICML": 0.95
  "ICLR": 0.9
  # ... more venues with scores

# File: config/keywords.yaml
computational_indicators:
  gpu_hardware:
    - "GPU"
    - "V100"
    - "A100"
    - "H100"
    - "TPU"
    - "CUDA"
  
  training_resources:
    - "training time"
    - "compute hours"
    - "GPU hours"
    - "wall-clock time"
  
  model_scale:
    - "parameters"
    - "billion parameters"
    - "model size"
    - "transformer"
  
  dataset_scale:
    - "dataset size"
    - "training data"
    - "million samples"
    - "billion tokens"
```

## Output Files
- Complete `src/` directory structure with base classes
- `config/` directory with YAML configuration files
- `src/core/` infrastructure (config, logging, exceptions)
- `src/data/models.py` with all data structures
- Base interface classes for all component types

## Success Criteria
- [ ] All directories created and organized
- [ ] Base classes and interfaces defined
- [ ] Configuration management functional
- [ ] Data models support serialization/deserialization
- [ ] Logging and error handling setup
- [ ] All imports and dependencies work

## Progress Documentation
Update `status/worker0-overall.json` every 15 minutes:
```json
{
  "worker_id": "worker0",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|failed",
  "completion_percentage": 80,
  "current_task": "Configuration Files Setup",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "architecture_ready": true,
  "outputs_available": [
    "src/ directory structure",
    "config/ files",
    "base classes and interfaces"
  ]
}
```

## Critical Dependencies for Other Workers
**ALL OTHER WORKERS DEPEND ON WORKER 0 COMPLETION**

- **Worker 1**: Uses `BaseCitationSource` and configuration management
- **Worker 2**: Uses `BaseAnalyzer` and `Paper`/`Author` models  
- **Worker 3**: Uses venue configuration and `BaseAnalyzer`
- **Worker 4**: Uses computational keywords config and `BaseAnalyzer`
- **Worker 5**: Uses `BaseValidator` and quality configuration
- **Worker 6**: Uses all collector interfaces and data models
- **Worker 7**: Uses selection interfaces and all analysis results

**Worker 0 MUST complete before any other worker can begin.**