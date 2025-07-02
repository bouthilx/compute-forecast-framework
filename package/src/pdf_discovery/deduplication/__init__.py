"""PDF deduplication module for handling duplicate papers across sources."""

from .engine import PaperDeduplicator
from .matchers import (
    IdentifierNormalizer,
    PaperFuzzyMatcher,
    ExactMatch,
    FuzzyMatch,
)
from .version_manager import VersionManager, SourcePriority

__all__ = [
    "PaperDeduplicator",
    "IdentifierNormalizer",
    "PaperFuzzyMatcher",
    "ExactMatch",
    "FuzzyMatch",
    "VersionManager",
    "SourcePriority",
]