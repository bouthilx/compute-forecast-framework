"""Quality check runner orchestrator."""

from pathlib import Path
from typing import Optional, List
import json

from .interfaces import QualityReport, QualityConfig
from .registry import get_registry


class QualityRunner:
    """Orchestrates quality checks across stages."""
    
    def __init__(self):
        self.registry = get_registry()
    
    def run_checks(
        self, 
        stage: str, 
        data_path: Path, 
        config: Optional[QualityConfig] = None
    ) -> QualityReport:
        """Run quality checks for a specific stage."""
        if config is None:
            config = self._get_default_config(stage)
        
        checker = self.registry.get_checker(stage)
        if not checker:
            raise ValueError(f"No quality checker registered for stage: {stage}")
        
        return checker.check(data_path, config)
    
    def run_all_applicable_checks(
        self, 
        data_path: Path,
        config: Optional[QualityConfig] = None
    ) -> List[QualityReport]:
        """Run quality checks for all applicable stages based on data."""
        reports = []
        
        # Detect applicable stages based on file/directory structure
        applicable_stages = self._detect_applicable_stages(data_path)
        
        for stage in applicable_stages:
            try:
                stage_config = config or self._get_default_config(stage)
                report = self.run_checks(stage, data_path, stage_config)
                reports.append(report)
            except Exception as e:
                # Log but continue with other stages
                print(f"Warning: Quality check failed for stage {stage}: {e}")
        
        return reports
    
    def _detect_applicable_stages(self, data_path: Path) -> List[str]:
        """Detect which stages are applicable based on data structure."""
        applicable = []
        
        if data_path.is_file() and data_path.suffix == '.json':
            # Try to detect stage from file content
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                    
                # Collection stage detection
                if 'collection_metadata' in data or 'papers' in data:
                    applicable.append('collection')
                
                # Future: Add detection for other stages
                # if 'consolidated_data' in data:
                #     applicable.append('consolidation')
            except Exception:
                # If we can't read the file, skip detection
                pass
        
        elif data_path.is_dir():
            # Check directory structure for hints
            if (data_path / 'collected_papers').exists():
                applicable.append('collection')
        
        return applicable
    
    def _get_default_config(self, stage: str) -> QualityConfig:
        """Get default configuration for a stage."""
        # Default thresholds by stage
        default_thresholds = {
            'collection': {
                'min_completeness': 0.8,
                'min_coverage': 0.7,
                'min_consistency': 0.9,
                'min_accuracy': 0.85,
            },
            # Future stages...
        }
        
        return QualityConfig(
            stage=stage,
            thresholds=default_thresholds.get(stage, {}),
            skip_checks=[],
            output_format='text',
            verbose=False
        )