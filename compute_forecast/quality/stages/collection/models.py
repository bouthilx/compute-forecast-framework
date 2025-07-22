"""Data models for collection quality assessment."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class CollectionQualityMetrics:
    """Metrics for collection quality assessment."""

    # Coverage metrics
    total_papers_collected: int
    expected_papers: Optional[int] = None
    coverage_rate: float = 0.0

    # Completeness metrics
    papers_with_all_required_fields: int = 0
    papers_with_abstracts: int = 0
    papers_with_pdfs: int = 0
    papers_with_dois: int = 0
    field_completeness_scores: Dict[str, float] = field(default_factory=dict)

    # Consistency metrics
    venue_consistency_score: float = 1.0
    year_consistency_score: float = 1.0
    duplicate_count: int = 0
    duplicate_rate: float = 0.0

    # Accuracy metrics
    valid_years_count: int = 0
    valid_authors_count: int = 0
    valid_urls_count: int = 0
    accuracy_scores: Dict[str, float] = field(default_factory=dict)

    # Source metrics
    papers_by_scraper: Dict[str, int] = field(default_factory=dict)
    scraper_success_rates: Dict[str, float] = field(default_factory=dict)
    papers_by_venue: Dict[str, int] = field(default_factory=dict)

    # Timing
    collection_timestamp: Optional[datetime] = None
    quality_check_timestamp: Optional[datetime] = None


@dataclass
class CollectionContext:
    """Context information from collection process."""

    venues_requested: List[str]
    years_requested: List[int]
    scrapers_used: List[str]
    collection_duration: Optional[float] = None
    errors_encountered: List[str] = field(default_factory=list)
