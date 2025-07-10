"""Base class for stage-specific quality checkers."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Callable
from pathlib import Path
from datetime import datetime

from ..core.interfaces import QualityReport, QualityConfig


class StageQualityChecker(ABC):
    """Base class for stage-specific quality checkers."""
    
    def __init__(self):
        self._checks = self._register_checks()
    
    @abstractmethod
    def get_stage_name(self) -> str:
        """Return the stage name this checker handles."""
        pass
    
    @abstractmethod
    def load_data(self, data_path: Path) -> Any:
        """Load and parse data for this stage."""
        pass
    
    @abstractmethod
    def _register_checks(self) -> Dict[str, Callable]:
        """Register all quality checks for this stage.
        
        Returns:
            Dict mapping check names to check methods
        """
        pass
    
    def check(self, data_path: Path, config: QualityConfig) -> QualityReport:
        """Run all quality checks for this stage."""
        # Load data
        data = self.load_data(data_path)
        
        # Run checks
        results = []
        for check_name, check_func in self._checks.items():
            if check_name not in config.skip_checks:
                result = check_func(data, config)
                results.append(result)
        
        # Calculate overall score
        overall_score = sum(r.score for r in results) / len(results) if results else 0.0
        
        return QualityReport(
            stage=self.get_stage_name(),
            timestamp=datetime.now(),
            data_path=data_path,
            overall_score=overall_score,
            check_results=results
        )
    
    def get_available_checks(self) -> List[str]:
        """Get list of available check names."""
        return list(self._checks.keys())