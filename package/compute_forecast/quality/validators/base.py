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