"""Register collection quality checker."""

from .checker import CollectionQualityChecker
from .formatter_adapters import CollectionTextFormatterAdapter, CollectionJSONFormatterAdapter, CollectionMarkdownFormatterAdapter


def register_collection_checker():
    """Register the collection quality checker."""
    # Import here to avoid circular import
    from compute_forecast.quality.core.registry import register_stage_checker
    register_stage_checker("collection", CollectionQualityChecker)


def register_collection_formatters():
    """Register the collection formatters."""
    # Import here to avoid circular import
    from compute_forecast.quality.core.formatters import FormatterRegistry
    
    FormatterRegistry.register("text", CollectionTextFormatterAdapter, stage="collection")
    FormatterRegistry.register("json", CollectionJSONFormatterAdapter, stage="collection")
    FormatterRegistry.register("markdown", CollectionMarkdownFormatterAdapter, stage="collection")