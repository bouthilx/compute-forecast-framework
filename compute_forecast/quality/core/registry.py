"""Registry for stage-specific quality checkers."""

from typing import Dict, Optional, Type, List

from ..stages.base import StageQualityChecker


class StageCheckerRegistry:
    """Registry for stage-specific quality checkers."""

    def __init__(self):
        self._checkers: Dict[str, Type[StageQualityChecker]] = {}
        self._instances: Dict[str, StageQualityChecker] = {}

    def register(self, stage: str, checker_class: Type[StageQualityChecker]):
        """Register a stage checker class."""
        self._checkers[stage.lower()] = checker_class

    def get_checker(self, stage: str) -> Optional[StageQualityChecker]:
        """Get or create a checker instance for a stage."""
        stage = stage.lower()

        if stage not in self._checkers:
            return None

        if stage not in self._instances:
            self._instances[stage] = self._checkers[stage]()

        return self._instances[stage]

    def list_stages(self) -> List[str]:
        """List all registered stages."""
        return list(self._checkers.keys())

    def list_checks_for_stage(self, stage: str) -> Optional[List[str]]:
        """List available checks for a stage."""
        checker = self.get_checker(stage)
        return checker.get_available_checks() if checker else None


# Global registry instance
_registry = StageCheckerRegistry()


def get_registry() -> StageCheckerRegistry:
    """Get the global stage checker registry."""
    return _registry


def register_stage_checker(stage: str, checker_class: Type[StageQualityChecker]):
    """Convenience function to register a stage checker."""
    _registry.register(stage, checker_class)
