"""Integration example showing how to use error handling components with existing scrapers"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .base import BaseScraper, ScrapingConfig, ScrapingResult
from .error_handling import (
    ScrapingMonitor,
    retry_on_error,
    RateLimiter,
    ErrorType,
    ScrapingError,
)
from ..models import Paper


class EnhancedScraper(BaseScraper):
    """Enhanced scraper with integrated error handling and monitoring"""

    def __init__(self, source_name: str, config: Optional[ScrapingConfig] = None):
        super().__init__(source_name, config)

        # Initialize error handling components
        self.monitor = ScrapingMonitor()
        self.rate_limiter = RateLimiter(
            requests_per_second=1.0 / self.config.rate_limit_delay
        )

        # Set up logging
        self.logger = logging.getLogger(f"scraper.{source_name}")

    def start_collection(self):
        """Start monitoring and prepare for collection"""
        self.monitor.start_monitoring()
        self.logger.info(f"Started collection with {self.source_name}")

    def finish_collection(self):
        """Finish monitoring and generate report"""
        self.monitor.end_monitoring()
        report = self.monitor.get_performance_report()

        self.logger.info(f"Collection completed. Performance report: {report}")
        return report

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def _make_monitored_request(self, url: str, **kwargs) -> str:
        """Make HTTP request with monitoring and error handling"""
        try:
            # Apply rate limiting
            self.rate_limiter.wait()

            # Make the request
            response = self._make_request(url, **kwargs)

            # Record success
            self.rate_limiter.record_success()

            return response.text

        except Exception as e:
            # Record error for rate limiting
            self.rate_limiter.record_error()

            # Create detailed error for monitoring
            error = ScrapingError(
                error_type=ErrorType.NETWORK_ERROR,
                message=str(e),
                url=url,
                traceback=str(e),
            )
            self.monitor.record_error(error)

            # Re-raise to trigger retry logic
            raise

    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Enhanced scrape with monitoring"""
        try:
            # Simulate scraping logic
            papers = self._scrape_papers(venue, year)

            # Record success
            self.monitor.record_success(len(papers), venue, year)

            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={"venue": venue, "year": year, "papers": papers},
            )

        except Exception as e:
            # Record error
            error = ScrapingError(
                error_type=ErrorType.PARSING_ERROR,
                message=f"Failed to scrape {venue} {year}: {str(e)}",
                venue=venue,
                year=year,
            )
            self.monitor.record_error(error)

            return ScrapingResult.failure_result(
                errors=[str(error)], metadata={"venue": venue, "year": year}
            )

    def _scrape_papers(self, venue: str, year: int) -> List[Paper]:
        """Mock scraping implementation"""
        # This would contain actual scraping logic
        # For demo purposes, we'll simulate some papers
        papers = []

        # Simulate fetching multiple pages
        for page in range(3):
            url = f"https://example.com/{venue}/{year}/page/{page}"

            try:
                html = self._make_monitored_request(url)

                # Simulate parsing (would be real parsing logic)
                page_papers = self._parse_page(html, venue, year)
                papers.extend(page_papers)

            except ScrapingError:
                # Error already recorded by _make_monitored_request
                self.logger.warning(f"Failed to fetch page {page} for {venue} {year}")
                continue

        return papers

    def _parse_page(self, html: str, venue: str, year: int) -> List[Paper]:
        """Mock parsing implementation"""
        # This would contain actual HTML parsing logic
        # For demo, return some mock papers
        return [
            Paper(
                title=f"Sample Paper {i} from {venue} {year}",
                authors=[],
                venue=venue,
                year=year,
                abstract="Sample abstract",
                doi="",
                urls=[],
                collection_source=self.source_name,
                collection_timestamp=datetime.now(),
                citations=0,
            )
            for i in range(5)  # 5 papers per page
        ]

    def get_supported_venues(self) -> List[str]:
        """Return supported venues for demo"""
        return ["CVPR", "ICCV", "ECCV", "NeurIPS", "ICML"]

    def get_available_years(self, venue: str) -> List[int]:
        """Return available years for demo"""
        return list(range(2019, 2025))

    def get_monitoring_report(self) -> Dict[str, Any]:
        """Get current monitoring state"""
        return {
            "performance_report": self.monitor.get_performance_report(),
            "recent_errors": [
                str(error) for error in self.monitor.get_recent_errors(5)
            ],
            "error_summary": self.monitor.get_error_summary(),
            "rate_limiter_state": {
                "consecutive_errors": self.rate_limiter.consecutive_errors,
                "current_delay": self.rate_limiter.get_current_delay(),
            },
        }


def demonstration_workflow():
    """Demonstrate the enhanced error handling workflow"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create enhanced scraper
    config = ScrapingConfig(
        rate_limit_delay=0.1,  # Fast for demo
        max_retries=2,
        timeout=30,
    )

    scraper = EnhancedScraper("demo_scraper", config)

    # Start collection
    scraper.start_collection()

    # Scrape multiple venues
    venues_to_scrape = {"CVPR": [2023, 2024], "NeurIPS": [2023], "ICML": [2023, 2024]}

    results = {}
    for venue, years in venues_to_scrape.items():
        for year in years:
            print(f"\nScraping {venue} {year}...")

            result = scraper.scrape_venue_year(venue, year)
            results[f"{venue}_{year}"] = result

            if result.success:
                print(f"✓ Successfully scraped {result.papers_collected} papers")
            else:
                print(f"✗ Failed: {result.errors}")

    # Finish collection and get report
    performance_report = scraper.finish_collection()
    monitoring_report = scraper.get_monitoring_report()

    print("\n" + "=" * 50)
    print("FINAL REPORT")
    print("=" * 50)

    print(f"Papers collected: {performance_report['papers_collected']}")
    print(f"Venues processed: {performance_report['venues_processed']}")
    print(f"Total errors: {performance_report['total_errors']}")
    print(f"Error rate: {performance_report['error_rate']:.2%}")
    print(f"Duration: {performance_report['duration_seconds']:.2f}s")
    print(f"Papers per second: {performance_report['papers_per_second']:.2f}")

    if monitoring_report["error_summary"]:
        print("\nError breakdown:")
        for error_type, count in monitoring_report["error_summary"].items():
            print(f"  {error_type}: {count}")

    if monitoring_report["recent_errors"]:
        print("\nRecent errors:")
        for error in monitoring_report["recent_errors"]:
            print(f"  {error}")

    print("\nRate limiter state:")
    print(
        f"  Consecutive errors: {monitoring_report['rate_limiter_state']['consecutive_errors']}"
    )
    print(
        f"  Current delay: {monitoring_report['rate_limiter_state']['current_delay']:.2f}s"
    )

    return results, performance_report, monitoring_report


if __name__ == "__main__":
    # Run the demonstration
    results, perf_report, mon_report = demonstration_workflow()

    print("\n" + "=" * 50)
    print("DEMONSTRATION COMPLETE")
    print("=" * 50)
    print("This example shows how to integrate the new error handling")
    print("components with existing scrapers for robust, monitored collection.")
