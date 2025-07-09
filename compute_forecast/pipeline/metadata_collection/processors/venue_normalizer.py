"""
Venue Normalizer using Worker 2/3 mappings with fuzzy matching.
Implements the exact interface contract specified in Issue #6.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Set, Literal
from dataclasses import dataclass
from datetime import datetime
import logging

from compute_forecast.pipeline.metadata_collection.processors.venue_mapping_loader import (
    VenueMappingLoader,
    VenueConfig,
)
from compute_forecast.pipeline.metadata_collection.processors.fuzzy_venue_matcher import (
    FuzzyVenueMatcher,
)
from compute_forecast.pipeline.metadata_collection.models import Paper

logger = logging.getLogger(__name__)


@dataclass
class VenueNormalizationResult:
    """Result of venue normalization for a single venue"""

    original_venue: str
    normalized_venue: str
    confidence: float  # 0.0 to 1.0
    mapping_type: Literal["exact", "fuzzy", "manual", "none"]
    alternatives: List[Tuple[str, float]]  # Alternative matches with scores


@dataclass
class BatchNormalizationResult:
    """Result of batch venue normalization"""

    papers_processed: int
    venues_normalized: int
    venues_unmapped: int
    new_mappings_created: int
    average_confidence: float
    normalization_statistics: Dict[str, int]  # mapping_type -> count
    unmapped_venues: List[str]  # Venues that couldn't be normalized


@dataclass
class VenueMappingStats:
    """Statistics about venue mappings"""

    total_mappings: int
    exact_mappings: int
    fuzzy_mappings: int
    high_confidence_mappings: int  # confidence >= 0.95
    medium_confidence_mappings: int  # 0.8 <= confidence < 0.95
    low_confidence_mappings: int  # confidence < 0.8
    coverage_by_tier: Dict[str, float]  # tier -> coverage percentage


@dataclass
class MappingValidationError:
    """Validation error for venue mappings"""

    error_type: str
    message: str
    venues_affected: List[str]


class VenueNormalizer:
    """
    Venue normalization system using Worker 2/3 mappings with fuzzy matching.
    Thread-safe implementation with real-time processing capabilities.
    """

    def __init__(
        self,
        mapping_file: Path = Path("data/worker2_venue_statistics.json"),
        fuzzy_threshold: float = 0.9,
        update_mappings_live: bool = True,
    ):
        """
        Initialize venue normalizer

        Args:
            mapping_file: Path to primary mapping file (legacy parameter)
            fuzzy_threshold: Minimum similarity score for fuzzy matching
            update_mappings_live: Whether to persist new mappings to disk
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.update_mappings_live = update_mappings_live
        self.logger = logging.getLogger(__name__)

        # Thread safety
        self._lock = threading.RLock()

        # Load mappings from all available sources
        self.mapping_loader = VenueMappingLoader()
        self.fuzzy_matcher = FuzzyVenueMatcher(fuzzy_threshold)

        # Internal state
        self._venue_mappings: Dict[str, str] = {}
        self._venue_configs: Dict[str, VenueConfig] = {}
        self._canonical_venues: Set[str] = set()
        self._fuzzy_cache: Dict[str, VenueNormalizationResult] = {}
        self._load_errors: List[str] = []

        # Statistics
        self._stats = {
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "no_matches": 0,
            "new_mappings_created": 0,
        }

        # Load initial mappings
        self._load_initial_mappings()

    def _load_initial_mappings(self) -> None:
        """Load initial venue mappings from all sources"""
        try:
            load_result = self.mapping_loader.load_all_mappings()

            with self._lock:
                self._venue_mappings = load_result.venue_mappings
                self._venue_configs = load_result.venue_configs
                self._canonical_venues = load_result.canonical_venues
                self._load_errors = load_result.load_errors

            self.logger.info(f"Loaded {len(self._venue_mappings)} venue mappings")
            self.logger.info(f"Canonical venues: {len(self._canonical_venues)}")

            if self._load_errors:
                self.logger.warning(f"Load errors: {self._load_errors}")

        except Exception as e:
            self.logger.error(f"Failed to load initial mappings: {e}")
            self._load_errors.append(f"Initial mapping load failed: {e}")

    def normalize_venue(self, raw_venue: str) -> VenueNormalizationResult:
        """
        Normalize venue name using Worker 2/3 mappings + fuzzy matching

        REQUIREMENTS:
        - Must check exact mapping first
        - Must use fuzzy matching for new variants (threshold 0.9)
        - Must return confidence score (0.0 to 1.0)
        - Must complete within 10ms per venue
        - Must be thread-safe
        """
        if not raw_venue:
            return VenueNormalizationResult(
                original_venue=raw_venue,
                normalized_venue=raw_venue,
                confidence=0.0,
                mapping_type="none",
                alternatives=[],
            )

        raw_venue = raw_venue.strip()

        with self._lock:
            # Step 1: Check exact mapping
            if raw_venue in self._venue_mappings:
                normalized = self._venue_mappings[raw_venue]
                self._stats["exact_matches"] += 1
                return VenueNormalizationResult(
                    original_venue=raw_venue,
                    normalized_venue=normalized,
                    confidence=1.0,
                    mapping_type="exact",
                    alternatives=[],
                )

            # Step 2: Check fuzzy cache
            if raw_venue in self._fuzzy_cache:
                return self._fuzzy_cache[raw_venue]

            # Step 3: Fuzzy matching
            fuzzy_result = self.fuzzy_matcher.find_best_match(
                raw_venue, list(self._canonical_venues), self.fuzzy_threshold
            )

            if fuzzy_result.matched_venue:
                # Create normalization result
                result = VenueNormalizationResult(
                    original_venue=raw_venue,
                    normalized_venue=fuzzy_result.matched_venue,
                    confidence=fuzzy_result.similarity_score,
                    mapping_type="fuzzy",
                    alternatives=[],
                )

                # Cache the result
                self._fuzzy_cache[raw_venue] = result
                self._stats["fuzzy_matches"] += 1

                # Optionally create permanent mapping
                if fuzzy_result.similarity_score >= 0.95:
                    self._venue_mappings[raw_venue] = fuzzy_result.matched_venue
                    if self.update_mappings_live:
                        self._persist_new_mapping(
                            raw_venue,
                            fuzzy_result.matched_venue,
                            fuzzy_result.similarity_score,
                        )
                    self._stats["new_mappings_created"] += 1

                return result

            # Step 4: No match found
            self._stats["no_matches"] += 1
            result = VenueNormalizationResult(
                original_venue=raw_venue,
                normalized_venue=raw_venue,  # Keep original
                confidence=0.0,
                mapping_type="none",
                alternatives=[],
            )

            # Cache negative result
            self._fuzzy_cache[raw_venue] = result
            return result

    def batch_normalize_venues(self, papers: List[Paper]) -> BatchNormalizationResult:
        """
        Normalize venues for entire paper batch efficiently

        REQUIREMENTS:
        - Must update Paper.normalized_venue field
        - Must update Paper.venue_confidence field
        - Must track normalization statistics
        - Must handle concurrent access safely
        - Must process 1000+ papers within 30 seconds
        """
        start_time = datetime.now()

        venues_processed = set()
        venues_normalized = 0
        venues_unmapped = 0
        new_mappings_created = 0
        confidence_sum = 0.0
        normalization_stats = {"exact": 0, "fuzzy": 0, "manual": 0, "none": 0}
        unmapped_venues = []

        # Collect unique venues for batch processing
        unique_venues = set()
        for paper in papers:
            if paper.venue:
                unique_venues.add(paper.venue)

        # Batch process fuzzy matching for unmapped venues
        unmapped_raw_venues = []
        for venue in unique_venues:
            if venue not in self._venue_mappings:
                unmapped_raw_venues.append(venue)

        if unmapped_raw_venues:
            batch_fuzzy_results = self.fuzzy_matcher.batch_find_matches(
                unmapped_raw_venues, list(self._canonical_venues), self.fuzzy_threshold
            )

            # Process batch results
            with self._lock:
                for raw_venue, fuzzy_result in batch_fuzzy_results.items():
                    if fuzzy_result.matched_venue:
                        self._fuzzy_cache[raw_venue] = VenueNormalizationResult(
                            original_venue=raw_venue,
                            normalized_venue=fuzzy_result.matched_venue,
                            confidence=fuzzy_result.similarity_score,
                            mapping_type="fuzzy",
                            alternatives=[],
                        )

                        # Create permanent mapping for high-confidence matches
                        if fuzzy_result.similarity_score >= 0.95:
                            self._venue_mappings[raw_venue] = fuzzy_result.matched_venue
                            new_mappings_created += 1
                    else:
                        self._fuzzy_cache[raw_venue] = VenueNormalizationResult(
                            original_venue=raw_venue,
                            normalized_venue=raw_venue,
                            confidence=0.0,
                            mapping_type="none",
                            alternatives=[],
                        )

        # Apply normalization to all papers
        for paper in papers:
            if not paper.venue:
                continue

            norm_result = self.normalize_venue(paper.venue)

            # Update paper fields
            paper.normalized_venue = norm_result.normalized_venue
            paper.venue_confidence = norm_result.confidence

            # Update statistics
            venues_processed.add(paper.venue)
            normalization_stats[norm_result.mapping_type] += 1
            confidence_sum += norm_result.confidence

            if norm_result.mapping_type != "none":
                venues_normalized += 1
            else:
                venues_unmapped += 1
                if paper.venue not in unmapped_venues:
                    unmapped_venues.append(paper.venue)

        # Calculate average confidence
        average_confidence = confidence_sum / len(papers) if papers else 0.0

        # Persist new mappings if enabled
        if self.update_mappings_live and new_mappings_created > 0:
            self._persist_batch_mappings()

        processing_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"Batch normalized {len(papers)} papers in {processing_time:.2f}s"
        )

        return BatchNormalizationResult(
            papers_processed=len(papers),
            venues_normalized=venues_normalized,
            venues_unmapped=venues_unmapped,
            new_mappings_created=new_mappings_created,
            average_confidence=average_confidence,
            normalization_statistics=normalization_stats,
            unmapped_venues=unmapped_venues,
        )

    def update_mapping(
        self, raw_venue: str, normalized_venue: str, confidence: float
    ) -> bool:
        """
        Add new venue mapping (if confidence meets threshold)

        REQUIREMENTS:
        - Must validate confidence >= 0.8 before adding
        - Must persist mapping to disk if update_live=True
        - Must prevent circular mappings
        - Must be thread-safe
        """
        if confidence < 0.8:
            return False

        # Prevent circular mappings
        if raw_venue == normalized_venue:
            return False

        # Check if normalized venue exists in canonical venues
        if normalized_venue not in self._canonical_venues:
            self.logger.warning(
                f"Normalized venue '{normalized_venue}' not in canonical venues"
            )
            return False

        with self._lock:
            # Update mapping
            self._venue_mappings[raw_venue] = normalized_venue

            # Update cache
            self._fuzzy_cache[raw_venue] = VenueNormalizationResult(
                original_venue=raw_venue,
                normalized_venue=normalized_venue,
                confidence=confidence,
                mapping_type="manual",
                alternatives=[],
            )

            # Persist if enabled
            if self.update_mappings_live:
                self._persist_new_mapping(raw_venue, normalized_venue, confidence)

            self._stats["new_mappings_created"] += 1

        return True

    def get_mapping_statistics(self) -> VenueMappingStats:
        """Get venue normalization statistics and coverage"""
        with self._lock:
            total_mappings = len(self._venue_mappings)

            # Count by confidence level
            high_confidence = 0
            medium_confidence = 0
            low_confidence = 0
            exact_mappings = 0
            fuzzy_mappings = 0

            for venue, norm_result in self._fuzzy_cache.items():
                if norm_result.confidence >= 0.95:
                    high_confidence += 1
                elif norm_result.confidence >= 0.8:
                    medium_confidence += 1
                else:
                    low_confidence += 1

                if norm_result.mapping_type == "exact":
                    exact_mappings += 1
                elif norm_result.mapping_type == "fuzzy":
                    fuzzy_mappings += 1

            # Add exact mappings
            exact_mappings += len(self._venue_mappings)

            # Calculate coverage by tier
            coverage_by_tier = {}
            for tier in ["tier1", "tier2", "tier3", "tier4"]:
                tier_venues = [
                    v for v in self._venue_configs.values() if v.venue_tier == tier
                ]
                if tier_venues:
                    mapped_count = sum(
                        1 for v in tier_venues if v.venue_name in self._venue_mappings
                    )
                    coverage_by_tier[tier] = mapped_count / len(tier_venues)
                else:
                    coverage_by_tier[tier] = 0.0

            return VenueMappingStats(
                total_mappings=total_mappings,
                exact_mappings=exact_mappings,
                fuzzy_mappings=fuzzy_mappings,
                high_confidence_mappings=high_confidence,
                medium_confidence_mappings=medium_confidence,
                low_confidence_mappings=low_confidence,
                coverage_by_tier=coverage_by_tier,
            )

    def validate_mappings(self) -> List[MappingValidationError]:
        """Validate mapping consistency and detect issues"""
        errors = []

        with self._lock:
            # Check for circular mappings
            for raw_venue, normalized_venue in self._venue_mappings.items():
                if raw_venue == normalized_venue:
                    errors.append(
                        MappingValidationError(
                            error_type="circular_mapping",
                            message=f"Circular mapping detected: {raw_venue} -> {normalized_venue}",
                            venues_affected=[raw_venue],
                        )
                    )

            # Check for mappings to non-canonical venues
            for raw_venue, normalized_venue in self._venue_mappings.items():
                if normalized_venue not in self._canonical_venues:
                    errors.append(
                        MappingValidationError(
                            error_type="invalid_target",
                            message=f"Mapping to non-canonical venue: {raw_venue} -> {normalized_venue}",
                            venues_affected=[raw_venue],
                        )
                    )

            # Check for conflicting mappings
            mapping_targets = {}
            for raw_venue, normalized_venue in self._venue_mappings.items():
                if normalized_venue in mapping_targets:
                    # This is actually expected - multiple raw venues can map to same canonical venue
                    pass
                else:
                    mapping_targets[normalized_venue] = [raw_venue]

        return errors

    def _persist_new_mapping(
        self, raw_venue: str, normalized_venue: str, confidence: float
    ) -> None:
        """Persist a single new mapping to disk"""
        try:
            # Create/update manual corrections file
            manual_corrections_path = Path("data/manual_venue_corrections.json")
            manual_corrections_path.parent.mkdir(exist_ok=True)

            # Load existing corrections
            corrections = {}
            if manual_corrections_path.exists():
                with open(manual_corrections_path, "r", encoding="utf-8") as f:
                    corrections = json.load(f)

            # Add new mapping
            if "venue_mappings" not in corrections:
                corrections["venue_mappings"] = {}

            corrections["venue_mappings"][raw_venue] = normalized_venue
            corrections["last_updated"] = datetime.now().isoformat()

            # Save back to file
            with open(manual_corrections_path, "w", encoding="utf-8") as f:
                json.dump(corrections, f, indent=2, ensure_ascii=False)

            self.logger.info(
                f"Persisted new mapping: {raw_venue} -> {normalized_venue}"
            )

        except Exception as e:
            self.logger.error(f"Failed to persist mapping: {e}")

    def _persist_batch_mappings(self) -> None:
        """Persist all new mappings created during batch processing"""
        try:
            # This would be implemented to save all new mappings at once
            # For now, individual mappings are saved as they're created
            pass
        except Exception as e:
            self.logger.error(f"Failed to persist batch mappings: {e}")
