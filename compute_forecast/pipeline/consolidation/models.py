from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum


class EnrichmentSource(Enum):
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    ORIGINAL = "original"


@dataclass
class ProvenanceRecord:
    """Base class for tracking source and timing of enrichment data"""

    source: str
    timestamp: datetime
    original: bool  # True if from original scraper, False if from enrichment API


@dataclass
class CitationData:
    """Citation count data"""

    count: int


@dataclass
class CitationRecord(ProvenanceRecord):
    """Citation count with provenance"""

    data: CitationData


@dataclass
class AbstractData:
    """Abstract text data"""

    text: str
    language: str = "en"


@dataclass
class AbstractRecord(ProvenanceRecord):
    """Abstract text with provenance"""

    data: AbstractData


@dataclass
class URLData:
    """URL data"""

    url: str


@dataclass
class URLRecord(ProvenanceRecord):
    """URL with provenance"""

    data: URLData


@dataclass
class IdentifierData:
    """Paper identifier data"""

    identifier_type: (
        str  # 'doi', 'arxiv', 's2_paper', 's2_corpus', 'pmid', 'acl', 'mag', 'openalex'
    )
    identifier_value: str


@dataclass
class IdentifierRecord(ProvenanceRecord):
    """Identifier with provenance tracking"""

    data: IdentifierData


@dataclass
class EnrichmentResult:
    """Result of enriching a single paper"""

    paper_id: str
    citations: List[CitationRecord] = field(default_factory=list)
    abstracts: List[AbstractRecord] = field(default_factory=list)
    urls: List[URLRecord] = field(default_factory=list)
    identifiers: List[IdentifierRecord] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ConsolidationResult:
    """Overall consolidation operation result"""

    total_papers: int
    enriched_papers: int
    citations_added: int
    abstracts_added: int
    errors: List[Dict[str, Any]]
    duration_seconds: float
    api_calls: Dict[str, int]  # Track API usage per source
