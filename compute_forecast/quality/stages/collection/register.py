"""Register collection quality checker."""

from .checker import CollectionQualityChecker


def register_collection_checker():
    """Register the collection quality checker."""
    # Import here to avoid circular import
    from compute_forecast.quality.core.registry import register_stage_checker
    register_stage_checker("collection", CollectionQualityChecker)