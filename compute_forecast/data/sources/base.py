from abc import ABC, abstractmethod
from ..models import Paper, CollectionQuery, CollectionResult


class BaseCitationSource(ABC):
    """Abstract base class for citation data sources"""

    def __init__(self, config: dict):
        self.config = config
        self.rate_limit = config.get("rate_limit", 1.0)
        self.retry_attempts = config.get("retry_attempts", 3)

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
        return float(self.rate_limit)
