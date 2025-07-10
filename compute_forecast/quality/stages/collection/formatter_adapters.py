"""Adapters to connect collection formatters to the generic formatter registry."""

from compute_forecast.quality.core.interfaces import QualityReport
from compute_forecast.quality.core.formatters import ReportFormatter, FormatterRegistry
from .formatters import TextReportFormatter, JSONReportFormatter, MarkdownReportFormatter
from .models import CollectionQualityMetrics


class CollectionFormatterAdapter(ReportFormatter):
    """Base adapter for collection formatters."""
    
    def __init__(self, formatter_class):
        self.formatter_class = formatter_class
    
    def format_report(self, report: QualityReport, **kwargs) -> str:
        """Format a quality report."""
        # Extract metrics from the report
        metrics = self._extract_metrics(report)
        
        # Create formatter instance
        formatter = self.formatter_class()
        
        # Format the report
        return formatter.format_report(report, metrics)
    
    def _extract_metrics(self, report: QualityReport) -> CollectionQualityMetrics:
        """Extract collection metrics from the report."""
        # Try to find metrics in check results
        for check_result in report.check_results:
            if hasattr(check_result, 'metrics') and 'collection_metrics' in check_result.metrics:
                return check_result.metrics['collection_metrics']
        
        # If no metrics found, create from available data
        return self._create_metrics_from_report(report)
    
    def _create_metrics_from_report(self, report: QualityReport) -> CollectionQualityMetrics:
        """Create metrics from report data."""
        # Extract basic metrics from check results
        metrics_data = {}
        
        for check_result in report.check_results:
            if hasattr(check_result, 'metrics'):
                metrics_data.update(check_result.metrics)
        
        # Create CollectionQualityMetrics with available data
        return CollectionQualityMetrics(
            total_papers_collected=metrics_data.get('total_papers', 0),
            papers_with_all_required_fields=metrics_data.get('papers_with_all_required_fields', 0),
            papers_with_abstracts=metrics_data.get('papers_with_abstracts', 0),
            papers_with_pdfs=metrics_data.get('papers_with_pdfs', 0),
            papers_with_dois=metrics_data.get('papers_with_dois', 0),
            field_completeness_scores=metrics_data.get('field_completeness_scores', {}),
            duplicate_count=metrics_data.get('duplicate_count', 0),
            duplicate_rate=metrics_data.get('duplicate_rate', 0.0),
            venue_consistency_score=metrics_data.get('venue_consistency_score', 1.0),
            year_consistency_score=metrics_data.get('year_consistency_score', 1.0),
            valid_years_count=metrics_data.get('valid_years_count', 0),
            valid_authors_count=metrics_data.get('valid_authors_count', 0),
            valid_urls_count=metrics_data.get('valid_urls_count', 0),
            accuracy_scores=metrics_data.get('accuracy_scores', {}),
            coverage_rate=metrics_data.get('coverage_rate', 0.0),
            papers_by_scraper=metrics_data.get('papers_by_scraper', {}),
            scraper_success_rates=metrics_data.get('scraper_success_rates', {})
        )


class CollectionTextFormatterAdapter(CollectionFormatterAdapter):
    """Adapter for text formatter."""
    
    def __init__(self):
        super().__init__(TextReportFormatter)


class CollectionJSONFormatterAdapter(CollectionFormatterAdapter):
    """Adapter for JSON formatter."""
    
    def __init__(self):
        super().__init__(JSONReportFormatter)


class CollectionMarkdownFormatterAdapter(CollectionFormatterAdapter):
    """Adapter for Markdown formatter."""
    
    def __init__(self):
        super().__init__(MarkdownReportFormatter)