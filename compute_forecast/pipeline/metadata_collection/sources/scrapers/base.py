"""Base classes for web scraping conference proceedings and journal papers"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...models import Paper


@dataclass
class ScrapingConfig:
    """Configuration for scraper behavior"""

    rate_limit_delay: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    batch_size: int = 100
    cache_enabled: bool = True
    user_agent: str = "ComputeForecast/1.0 (Academic Research)"


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""

    success: bool
    papers_collected: int
    errors: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime

    @classmethod
    def success_result(
        cls, papers_count: int, metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a successful result"""
        return cls(
            success=True,
            papers_collected=papers_count,
            errors=[],
            metadata=metadata or {},
            timestamp=datetime.now(),
        )

    @classmethod
    def failure_result(
        cls, errors: List[str], metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a failure result"""
        return cls(
            success=False,
            papers_collected=0,
            errors=errors,
            metadata=metadata or {},
            timestamp=datetime.now(),
        )


class BaseScraper(ABC):
    """Abstract base class for all paper scrapers"""

    def __init__(self, source_name: str, config: Optional[ScrapingConfig] = None):
        self.source_name = source_name
        self.config = config or ScrapingConfig()
        self.logger = logging.getLogger(f"scraper.{source_name}")
        self._session = None
        self._cache = {}

    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session with retry configuration"""
        if self._session is None:
            self._session = requests.Session()

            # Configure retries
            retry_strategy = Retry(
                total=self.config.max_retries,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

            # Set user agent
            self._session.headers.update({"User-Agent": self.config.user_agent})

        return self._session

    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with rate limiting"""
        time.sleep(self.config.rate_limit_delay)

        kwargs.setdefault("timeout", self.config.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()

        return response

    @abstractmethod
    def get_supported_venues(self) -> List[str]:
        """Return list of venue names this scraper supports"""
        pass

    @abstractmethod
    def get_available_years(self, venue: str) -> List[int]:
        """Return available years for a specific venue"""
        pass

    @abstractmethod
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape all papers from a venue for a specific year"""
        pass

    def estimate_paper_count(self, venue: str, year: int) -> Optional[int]:
        """Estimate the number of papers available for a venue/year.
        
        Returns None if estimation is not possible.
        Override in subclasses to provide better estimates.
        """
        return None

    def scrape_multiple_venues(
        self, venue_years: Dict[str, List[int]]
    ) -> Dict[str, ScrapingResult]:
        """Scrape papers from multiple venues/years"""
        results = {}

        for venue, years in venue_years.items():
            if venue not in self.get_supported_venues():
                self.logger.warning(
                    f"Venue {venue} not supported by {self.source_name}"
                )
                results[venue] = ScrapingResult.failure_result(
                    [f"Venue {venue} not supported by {self.source_name}"]
                )
                continue

            for year in years:
                key = f"{venue}_{year}"
                self.logger.info(f"Scraping {venue} {year}")

                try:
                    results[key] = self.scrape_venue_year(venue, year)
                except Exception as e:
                    self.logger.error(f"Error scraping {venue} {year}: {str(e)}")
                    results[key] = ScrapingResult.failure_result(
                        [f"Error scraping {venue} {year}: {str(e)}"]
                    )

                # Rate limiting between venue/year combinations
                time.sleep(self.config.rate_limit_delay)

        return results

    def validate_venue_year(self, venue: str, year: int) -> List[str]:
        """Validate venue and year parameters"""
        errors = []

        # Check venue support with case-insensitive matching
        supported = self.get_supported_venues()
        venue_supported = any(venue.lower() == v.lower() for v in supported)
        if not venue_supported:
            errors.append(f"Venue '{venue}' not supported")

        available_years = self.get_available_years(venue)
        if available_years and year not in available_years:
            errors.append(f"Year {year} not available for venue '{venue}'")

        return errors


class ConferenceProceedingsScraper(BaseScraper):
    """Base class for conference proceedings scrapers"""

    @abstractmethod
    def get_proceedings_url(self, venue: str, year: int) -> str:
        """Construct proceedings URL for venue/year"""
        pass

    @abstractmethod
    def parse_proceedings_page(self, html: str, venue: str, year: int) -> List[Paper]:
        """Parse proceedings page HTML to extract papers"""
        pass

    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Default implementation for scraping conference proceedings"""
        # Validate parameters
        validation_errors = self.validate_venue_year(venue, year)
        if validation_errors:
            return ScrapingResult.failure_result(validation_errors)

        try:
            # Get proceedings URL
            url = self.get_proceedings_url(venue, year)
            self.logger.info(f"Fetching proceedings from: {url}")

            # Fetch page
            response = self._make_request(url)

            # Parse papers
            papers = self.parse_proceedings_page(response.text, venue, year)

            self.logger.info(
                f"Successfully scraped {len(papers)} papers from {venue} {year}"
            )
            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={"venue": venue, "year": year, "url": url, "papers": papers},
            )

        except Exception as e:
            self.logger.error(f"Error scraping {venue} {year}: {str(e)}")
            return ScrapingResult.failure_result(
                errors=[str(e)], metadata={"venue": venue, "year": year}
            )


class JournalPublisherScraper(BaseScraper):
    """Base class for journal publisher scrapers"""

    @abstractmethod
    def search_papers(
        self, journal: str, keywords: List[str], year_range: Tuple[int, int]
    ) -> List[Paper]:
        """Search for papers in journal by keywords and year range"""
        pass

    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape journal papers for a specific year"""
        try:
            # For journals, we might need to search rather than enumerate
            papers = self.search_papers(
                journal=venue,
                keywords=[],  # Get all papers
                year_range=(year, year),
            )

            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={"journal": venue, "year": year, "papers": papers},
            )

        except Exception as e:
            self.logger.error(f"Error scraping journal {venue} year {year}: {str(e)}")
            return ScrapingResult.failure_result(
                errors=[str(e)], metadata={"journal": venue, "year": year}
            )


class APIEnhancedScraper(BaseScraper):
    """Base class for API-based scrapers"""

    def __init__(self, source_name: str, config: Optional[ScrapingConfig] = None):
        super().__init__(source_name, config)
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with API if required"""
        pass

    @abstractmethod
    def make_api_request(self, endpoint: str, params: Dict) -> Dict:
        """Make authenticated API request"""
        pass

    def _ensure_authenticated(self):
        """Ensure we're authenticated before making API requests"""
        if not self._authenticated:
            self.logger.info(f"Authenticating with {self.source_name} API")
            if not self.authenticate():
                raise RuntimeError(
                    f"Failed to authenticate with {self.source_name} API"
                )
            self._authenticated = True

    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Default implementation using API"""
        # Validate parameters
        validation_errors = self.validate_venue_year(venue, year)
        if validation_errors:
            return ScrapingResult.failure_result(validation_errors)

        try:
            # Ensure authenticated
            self._ensure_authenticated()

            # Make API request
            params = {"venue": venue, "year": year, "limit": self.config.batch_size}

            papers = []
            offset = 0

            while True:
                params["offset"] = offset
                response = self.make_api_request("/papers", params.copy())

                batch_papers = response.get("papers", [])
                papers.extend(batch_papers)

                # Check if more results available
                if len(batch_papers) < self.config.batch_size:
                    break

                offset += self.config.batch_size
                time.sleep(self.config.rate_limit_delay)

            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={"venue": venue, "year": year, "papers": papers},
            )

        except Exception as e:
            self.logger.error(f"API error for {venue} {year}: {str(e)}")
            return ScrapingResult.failure_result(
                errors=[str(e)], metadata={"venue": venue, "year": year}
            )
