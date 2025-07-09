"""
Data Analysis System for Issue #9.
Provides comprehensive statistical analysis, trend analysis, and research insights
for collected academic papers.
"""

from compute_forecast.pipeline.metadata_collection.analysis.statistical_analyzer import (
    StatisticalAnalyzer,
    PaperStatistics,
    VenueStatistics,
    AnalysisSummary,
)

__all__ = [
    # Statistical Analysis
    "StatisticalAnalyzer",
    "PaperStatistics",
    "VenueStatistics",
    "AnalysisSummary",
]
