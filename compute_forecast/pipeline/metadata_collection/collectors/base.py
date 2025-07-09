from abc import ABC, abstractmethod
from typing import List
from compute_forecast.pipeline.metadata_collection.models import Paper, CollectionQuery


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
