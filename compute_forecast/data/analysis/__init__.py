"""
Data Analysis System for Issue #9.
Provides comprehensive statistical analysis, trend analysis, and research insights
for collected academic papers.
"""

from .statistical_analyzer import (
    StatisticalAnalyzer,
    PaperStatistics,
    VenueStatistics,
    AnalysisSummary,
)

from .trend_analyzer import (
    TrendAnalyzer,
    CitationTrend,
    VenueTrend,
    ResearchTrend,
    TrendAnalysisResult,
)

from .research_insights import (
    ResearchInsightsEngine,
    CitationNetworkAnalyzer,
    AuthorCollaborationAnalyzer,
    VenueAnalyzer,
    ResearchInsight,
)

from .analysis_pipeline import AnalysisPipeline, AnalysisJob, AnalysisScheduler

from .report_generator import AnalysisReportGenerator, ReportTemplate, ReportExporter

__all__ = [
    # Statistical Analysis
    "StatisticalAnalyzer",
    "PaperStatistics",
    "VenueStatistics",
    "AnalysisSummary",
    # Trend Analysis
    "TrendAnalyzer",
    "CitationTrend",
    "VenueTrend",
    "ResearchTrend",
    "TrendAnalysisResult",
    # Research Insights
    "ResearchInsightsEngine",
    "CitationNetworkAnalyzer",
    "AuthorCollaborationAnalyzer",
    "VenueAnalyzer",
    "ResearchInsight",
    # Analysis Pipeline
    "AnalysisPipeline",
    "AnalysisJob",
    "AnalysisScheduler",
    # Report Generation
    "AnalysisReportGenerator",
    "ReportTemplate",
    "ReportExporter",
]
