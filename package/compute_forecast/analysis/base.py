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