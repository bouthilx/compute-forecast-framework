from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
import threading

from ..consolidation.models import (
    CitationRecord,
    AbstractRecord,
    URLRecord,
    IdentifierRecord,
)


@dataclass
class Author:
    name: str
    affiliations: List[str] = field(default_factory=list)
    email: str = ""


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
    author_details: List[Dict[str, Any]]


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
    citations: List[CitationRecord] = field(default_factory=list)
    abstracts: List[AbstractRecord] = field(default_factory=list)
    doi: str = ""
    urls: List[URLRecord] = field(default_factory=list)
    identifiers: List[IdentifierRecord] = field(default_factory=list)

    # Core identifiers (at least one required)
    paper_id: Optional[str] = None  # Semantic Scholar ID
    openalex_id: Optional[str] = None  # OpenAlex ID
    arxiv_id: Optional[str] = None  # ArXiv ID

    # Enhanced fields for batched collection
    normalized_venue: Optional[str] = None  # Agent Gamma sets this
    keywords: List[str] = field(default_factory=list)
    citation_velocity: Optional[float] = None

    # Processing metadata
    collection_source: str = ""
    collection_timestamp: datetime = field(default_factory=datetime.now)
    processing_flags: Dict[str, bool] = field(default_factory=dict)
    venue_confidence: float = 1.0
    deduplication_confidence: float = 1.0
    breakthrough_score: Optional[float] = None

    # Analysis results (populated by workers)
    computational_analysis: Optional[ComputationalAnalysis] = None
    authorship_analysis: Optional[AuthorshipAnalysis] = None
    venue_analysis: Optional[VenueAnalysis] = None

    # Legacy collection metadata
    source: str = ""
    mila_domain: str = ""
    collection_method: str = ""
    selection_rank: Optional[int] = None
    benchmark_type: str = ""  # 'academic' or 'industry'

    def get_latest_citations_count(self) -> int:
        """Get highest citation count from all sources"""
        if not self.citations:
            return 0
        return max(record.data.count for record in self.citations)

    def get_best_abstract(self) -> str:
        """Get best abstract (original if available, else first found)"""
        # Prioritize original abstracts
        for record in self.abstracts:
            if record.original:
                return record.data.text
        # Fall back to first non-original
        if self.abstracts:
            return self.abstracts[0].data.text
        return ""

    def get_best_urls(self) -> List[str]:
        """Get URLs (original if available, else all)"""
        # Get original URLs first
        original_urls = [record.data.url for record in self.urls if record.original]
        if original_urls:
            return original_urls
        # Fall back to all URLs
        return [record.data.url for record in self.urls]

    def to_dict(self) -> Dict[str, Any]:
        """Convert paper to dictionary for JSON serialization"""
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif key in [
                "citations",
                "abstracts",
                "urls",
                "identifiers",
            ] and isinstance(value, list):
                # Special handling for provenance records
                result[key] = []
                for record in value:
                    record_dict = {
                        "source": record.source,
                        "timestamp": record.timestamp.isoformat(),
                        "original": record.original,
                        "data": record.data.__dict__,
                    }
                    result[key].append(record_dict)
            elif isinstance(value, list) and value and hasattr(value[0], "__dict__"):
                result[key] = [item.__dict__ for item in value]
            elif hasattr(value, "__dict__"):
                result[key] = value.__dict__ if value else None
            else:
                result[key] = value
        return result

    def update_identifiers_from_records(self):
        """Update individual identifier fields from identifier records"""
        for record in self.identifiers:
            id_type = record.data.identifier_type
            id_value = record.data.identifier_value

            if id_type == "doi" and not self.doi:
                self.doi = id_value
            elif id_type == "arxiv" and not self.arxiv_id:
                self.arxiv_id = id_value
            elif id_type == "openalex" and not self.openalex_id:
                self.openalex_id = id_value
            elif id_type == "s2_paper" and not self.paper_id:
                self.paper_id = id_value
            # Store new identifier types in processing_flags
            else:
                if "discovered_identifiers" not in self.processing_flags:
                    self.processing_flags["discovered_identifiers"] = {}
                self.processing_flags["discovered_identifiers"][id_type] = id_value

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paper":
        """Create Paper from dictionary"""
        # Handle authors with backward compatibility
        authors = []
        for author_data in data.get("authors", []):
            if isinstance(author_data, dict):
                # Handle old format (affiliation as string) to new format (affiliations as list)
                if "affiliation" in author_data:
                    author_data = author_data.copy()
                    affiliation_value = author_data.pop("affiliation")
                    if "affiliations" not in author_data:
                        author_data["affiliations"] = (
                            [affiliation_value] if affiliation_value else []
                        )
                # Handle None affiliations
                if author_data.get("affiliations") is None:
                    author_data = author_data.copy()
                    author_data["affiliations"] = []
                # Handle None email
                if author_data.get("email") is None:
                    author_data = author_data.copy()
                    author_data["email"] = ""
                # Remove author_id if present (no longer part of model)
                if "author_id" in author_data:
                    author_data = author_data.copy()
                    author_data.pop("author_id", None)
                authors.append(Author(**author_data))
            elif isinstance(author_data, str):
                # Handle simple string author names from scrapers
                authors.append(Author(name=author_data, affiliations=[]))

        # Handle analysis objects
        comp_analysis = None
        if data.get("computational_analysis"):
            comp_analysis = ComputationalAnalysis(**data["computational_analysis"])

        auth_analysis = None
        if data.get("authorship_analysis"):
            auth_analysis = AuthorshipAnalysis(**data["authorship_analysis"])

        venue_analysis = None
        if data.get("venue_analysis"):
            venue_analysis = VenueAnalysis(**data["venue_analysis"])

        # Handle provenance fields (citations, abstracts, urls)
        citations = []
        if data.get("citations"):
            from ..consolidation.models import CitationRecord, CitationData

            for record in data["citations"]:
                citations.append(
                    CitationRecord(
                        source=record["source"],
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        original=record.get("original", False),
                        data=CitationData(count=record["data"]["count"]),
                    )
                )

        abstracts = []
        if data.get("abstracts"):
            from ..consolidation.models import AbstractRecord, AbstractData

            for record in data["abstracts"]:
                abstracts.append(
                    AbstractRecord(
                        source=record["source"],
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        original=record.get("original", False),
                        data=AbstractData(
                            text=record["data"]["text"],
                            language=record["data"].get("language", "en"),
                        ),
                    )
                )

        urls = []
        if data.get("urls"):
            from ..consolidation.models import URLRecord, URLData

            for record in data["urls"]:
                urls.append(
                    URLRecord(
                        source=record["source"],
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        original=record.get("original", False),
                        data=URLData(url=record["data"]["url"]),
                    )
                )

        identifiers = []
        if data.get("identifiers"):
            from ..consolidation.models import IdentifierRecord, IdentifierData

            for record in data["identifiers"]:
                identifiers.append(
                    IdentifierRecord(
                        source=record["source"],
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        original=record.get("original", False),
                        data=IdentifierData(
                            identifier_type=record["data"]["identifier_type"],
                            identifier_value=record["data"]["identifier_value"],
                        ),
                    )
                )

        # Create paper with processed data
        paper_data = data.copy()

        # Handle None values for string fields
        if paper_data.get("doi") is None:
            paper_data["doi"] = ""

        # Handle None values for list fields
        if paper_data.get("keywords") is None:
            paper_data["keywords"] = []

        # Handle datetime fields
        if "collection_timestamp" in paper_data and isinstance(
            paper_data["collection_timestamp"], str
        ):
            paper_data["collection_timestamp"] = datetime.fromisoformat(
                paper_data["collection_timestamp"]
            )

        # Remove fields we'll set explicitly
        paper_data.pop("authors", None)
        paper_data.pop("citations", None)
        paper_data.pop("abstracts", None)
        paper_data.pop("urls", None)
        paper_data.pop("identifiers", None)
        paper_data.pop("computational_analysis", None)
        paper_data.pop("authorship_analysis", None)
        paper_data.pop("venue_analysis", None)

        # Remove legacy fields that no longer exist in the model
        paper_data.pop("external_ids", None)

        # Remove download-related fields that are added dynamically
        paper_data.pop("pdf_downloaded", None)
        paper_data.pop("pdf_download_timestamp", None)
        paper_data.pop("pdf_download_error", None)

        paper_data["authors"] = authors
        paper_data["citations"] = citations
        paper_data["abstracts"] = abstracts
        paper_data["urls"] = urls
        paper_data["identifiers"] = identifiers
        paper_data["computational_analysis"] = comp_analysis
        paper_data["authorship_analysis"] = auth_analysis
        paper_data["venue_analysis"] = venue_analysis

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


# New data structures for batched API collection


@dataclass
class APIError:
    error_type: str
    message: str
    status_code: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ResponseMetadata:
    total_results: int
    returned_count: int
    query_used: str
    response_time_ms: float
    api_name: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class APIResponse:
    success: bool
    papers: List[Paper]
    metadata: ResponseMetadata
    errors: List[APIError] = field(default_factory=list)


@dataclass
class BatchCollectionResult:
    papers: List[Paper]
    venues_attempted: List[str]
    venues_successful: List[str]
    venues_failed: List[str]
    year: int
    collection_metadata: Dict[str, ResponseMetadata]
    total_duration_seconds: float
    errors: List[APIError] = field(default_factory=list)


@dataclass
class VenueCollectionResult:
    papers: List[Paper]
    venue: str
    year: int
    success: bool
    collection_metadata: ResponseMetadata
    total_duration_seconds: float
    errors: List[APIError] = field(default_factory=list)


@dataclass
class CollectionConfig:
    max_venues_per_batch: int = 6
    batch_timeout_seconds: int = 300  # 5 minutes
    single_venue_timeout_seconds: int = 1800  # 30 minutes
    max_retries: int = 3
    api_priority: List[str] = field(
        default_factory=lambda: ["semantic_scholar", "openalex", "crossref"]
    )


@dataclass
class CollectionEstimate:
    total_batches: int
    estimated_duration_hours: float
    expected_paper_count: int
    api_calls_required: int


@dataclass
class APIConfig:
    requests_per_window: int  # Max requests per 5-minute window
    base_delay_seconds: float  # Minimum delay between requests
    max_delay_seconds: float  # Maximum delay for degraded APIs
    health_degradation_threshold: float  # Success rate threshold for degradation
    burst_allowance: int  # Burst requests allowed


@dataclass
class RateLimitStatus:
    api_name: str
    requests_in_window: int
    window_capacity: int
    next_available_slot: datetime
    current_delay_seconds: float
    health_multiplier: float


@dataclass
class APIHealthStatus:
    api_name: str
    status: Literal["healthy", "degraded", "critical", "offline"]
    success_rate: float  # 0.0 to 1.0
    avg_response_time_ms: float
    consecutive_errors: int
    last_error: Optional[APIError] = None
    last_successful_request: Optional[datetime] = None


# Configuration constants for rate limiting and health monitoring
class HealthMonitoringConfig:
    """Configuration constants for API health monitoring"""

    DEFAULT_HISTORY_SIZE = 100
    RECENT_REQUESTS_WINDOW = 50  # Number of recent requests to analyze
    FAST_RESPONSE_THRESHOLD_MS = 1000  # Responses under this are considered fast
    NORMAL_RESPONSE_THRESHOLD_MS = 3000  # Responses under this are considered normal
    SLOW_RESPONSE_THRESHOLD_MS = 5000  # Responses over this are considered slow
    DEGRADED_CONSECUTIVE_ERRORS = 3  # Errors before marking as degraded
    CRITICAL_CONSECUTIVE_ERRORS = 5  # Errors before marking as critical
    OFFLINE_CONSECUTIVE_ERRORS = 10  # Errors before marking as offline
    DEGRADED_SUCCESS_RATE_THRESHOLD = 0.8  # Success rate below this is degraded
    CRITICAL_SUCCESS_RATE_THRESHOLD = 0.5  # Success rate below this is critical


class RateLimitingConfig:
    """Configuration constants for rate limiting"""

    MAX_WAIT_TIME_SECONDS = 60.0  # Never wait longer than this
    DEFAULT_WINDOW_SECONDS = 300  # 5-minute rolling windows
    BATCH_SIZE_MULTIPLIER_CAP = 3.0  # Maximum multiplier for large batches
    BATCH_SIZE_DIVISOR = 10.0  # Divisor for calculating batch multiplier

    # Health multipliers for different states
    HEALTHY_MULTIPLIER = 1.0
    DEGRADED_MULTIPLIER = 2.0
    CRITICAL_MULTIPLIER = 5.0
    OFFLINE_MULTIPLIER = 10.0

    # Health improvement factors
    FAST_RESPONSE_IMPROVEMENT = 0.95
    NORMAL_RESPONSE_IMPROVEMENT = 0.98
    SLOW_RESPONSE_DEGRADATION = 1.1
    FAILURE_DEGRADATION = 1.5


# Rolling window for request tracking
class RollingWindow:
    """Rolling time window for request tracking"""

    def __init__(self, window_seconds: int, max_requests: int) -> None:
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests: List[datetime] = []
        self._lock = threading.RLock()

    def add_request(self, timestamp: Optional[datetime] = None) -> bool:
        """Add request to window, return if within limits"""
        with self._lock:
            if timestamp is None:
                timestamp = datetime.now()

            # Clean old requests
            self._clean_old_requests(timestamp)

            # Check if we can add this request
            if len(self.requests) < self.max_requests:
                self.requests.append(timestamp)
                return True

            return False

    def get_current_count(self) -> int:
        """Get current request count in window"""
        with self._lock:
            self._clean_old_requests()
            return len(self.requests)

    def time_until_next_slot(self) -> float:
        """Seconds until next request slot available"""
        with self._lock:
            self._clean_old_requests()

            if len(self.requests) < self.max_requests:
                return 0.0

            # Find oldest request
            if self.requests:
                oldest_request = min(self.requests)
                time_until_expired = (
                    self.window_seconds
                    - (datetime.now() - oldest_request).total_seconds()
                )
                return max(0.0, time_until_expired)

            return 0.0

    def _clean_old_requests(self, current_time: Optional[datetime] = None) -> None:
        """Remove requests outside the time window"""
        if current_time is None:
            current_time = datetime.now()

        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        self.requests = [req for req in self.requests if req > cutoff_time]
