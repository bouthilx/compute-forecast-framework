"""
Collection Executor for comprehensive paper collection across all research domains.
Coordinates citation APIs, venue analysis, and computational analysis systems.
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

from ..sources.google_scholar import GoogleScholarSource
from ..sources.semantic_scholar import SemanticScholarSource
from ..sources.openalex import OpenAlexSource
from .citation_collector import CitationCollector
from ...analysis.venues.venue_analyzer import MilaVenueAnalyzer
from ...analysis.venues.venue_database import VenueDatabase, VenueClassifier
from ...analysis.venues.collection_strategy import CollectionStrategyOptimizer
from ...analysis.venues.venue_scoring import VenueScorer
from ...analysis.computational.analyzer import ComputationalAnalyzer
from ...analysis.computational.filter import ComputationalFilter
from ...core.config import ConfigManager

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API calls"""

    def __init__(self):
        self.last_calls = {"venue_search": 0, "keyword_search": 0, "general_search": 0}
        self.delays = {"venue_search": 3, "keyword_search": 2, "general_search": 1}

    def wait(self, operation_type: str):
        """Wait appropriate time before making next API call"""
        current_time = time.time()
        last_call = self.last_calls.get(operation_type, 0)
        delay = self.delays.get(operation_type, 1)

        time_since_last = current_time - last_call
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.info(
                f"Rate limiting: waiting {sleep_time:.2f}s for {operation_type}"
            )
            time.sleep(sleep_time)

        self.last_calls[operation_type] = time.time()


class CollectionExecutor:
    """Main collection executor that coordinates all paper collection activities"""

    def __init__(self):
        self.citation_apis = None
        self.venue_analyzer = None
        self.venue_database = None
        self.venue_classifier = None
        self.collection_strategy_optimizer = None
        self.computational_analyzer = None
        self.computational_filter = None
        self.rate_limiter = RateLimiter()
        self.domain_analysis = None
        self.paper_collector = None
        self.config_manager = None
        self.working_apis = []

    def setup_collection_environment(self) -> bool:
        """Initialize all required systems from other workers"""
        logger.info("Setting up collection environment...")

        try:
            # Load citation infrastructure (Worker 1)
            logger.info("Loading citation APIs...")
            self.citation_apis = {
                "google_scholar": GoogleScholarSource(),
                "semantic_scholar": SemanticScholarSource(),
                "openalex": OpenAlexSource(),
            }

            self.paper_collector = CitationCollector()

            # Test API connectivity
            api_status = self.test_api_connectivity()
            working_apis = [api for api, status in api_status.items() if status]
            if len(working_apis) < 2:  # Require at least 2 working APIs
                logger.error(f"Insufficient working APIs: {api_status}")
                return False
            else:
                logger.info(
                    f"Proceeding with {len(working_apis)} working APIs: {working_apis}"
                )
                # Store working APIs for domain collector to use
                self.working_apis = working_apis

            logger.info("✓ Citation APIs loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Worker 1 outputs: {e}")
            return False

        try:
            # Load venue analysis (Worker 3)
            logger.info("Loading venue analysis...")
            self.config_manager = ConfigManager()
            self.venue_analyzer = MilaVenueAnalyzer(self.config_manager)
            self.venue_database = VenueDatabase(self.config_manager)
            self.venue_classifier = VenueClassifier(self.venue_database)

            # Initialize venue scorer and collection strategy optimizer
            venue_scorer = VenueScorer(self.venue_database, self.venue_analyzer)
            self.collection_strategy_optimizer = CollectionStrategyOptimizer(
                self.venue_database, venue_scorer
            )

            logger.info("✓ Venue analysis loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Worker 3 outputs: {e}")
            return False

        try:
            # Load computational analyzer (Worker 4)
            logger.info("Loading computational analyzer...")
            self.computational_analyzer = ComputationalAnalyzer()
            self.computational_filter = ComputationalFilter()

            logger.info("✓ Computational analyzer loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Worker 4 outputs: {e}")
            return False

        # Load domain analysis results
        try:
            self.domain_analysis = self.load_domain_results()
            logger.info("✓ Domain analysis loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load domain analysis: {e}")
            return False

        logger.info("Collection environment setup complete!")
        return True

    def test_api_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all citation APIs"""
        logger.info("Testing API connectivity...")

        api_status = {}

        for api_name, api_instance in self.citation_apis.items():
            try:
                status = api_instance.test_connectivity()
                api_status[api_name] = status
                logger.info(f"  {api_name}: {'✓' if status else '✗'}")
            except Exception as e:
                logger.error(f"  {api_name}: ✗ - {e}")
                api_status[api_name] = False

        return api_status

    def load_domain_results(self) -> Dict[str, Any]:
        """Load finalized domain analysis from existing results"""
        logger.info("Loading domain analysis results...")

        # Try to load the most recent/complete domain analysis
        domain_files = [
            "final_corrected_domain_stats.json",
            "all_domains_final_fix.json",
            "all_domains_completely_fixed.json",
            "domain_clusters.json",
        ]

        for filename in domain_files:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    logger.info(f"✓ Loaded domain analysis from {filename}")
                    return dict(data) if isinstance(data, dict) else {}
            except FileNotFoundError:
                logger.debug(f"Domain file {filename} not found, trying next...")
                continue

        raise FileNotFoundError("No domain analysis files found")

    def get_domains_from_analysis(self) -> List[str]:
        """Extract domain names from domain analysis"""
        if isinstance(self.domain_analysis, dict):
            if "final_corrected_stats" in self.domain_analysis:
                return list(self.domain_analysis["final_corrected_stats"].keys())
            elif "domains" in self.domain_analysis:
                return list(self.domain_analysis["domains"].keys())
            elif "domain_clusters" in self.domain_analysis:
                return list(self.domain_analysis["domain_clusters"].keys())
            else:
                # Filter out metadata keys and get actual domain keys
                excluded_keys = {
                    "methodology",
                    "inflation_factor",
                    "total_papers",
                    "corrections_applied",
                }
                domain_keys = [
                    k for k in self.domain_analysis.keys() if k not in excluded_keys
                ]
                if domain_keys:
                    return domain_keys

        # Fallback to common ML domains
        return [
            "Computer Vision",
            "Natural Language Processing",
            "Reinforcement Learning",
            "Machine Learning Theory",
            "Deep Learning",
            "Robotics",
            "Speech and Audio Processing",
        ]

    def get_citation_threshold(self, year: int) -> int:
        """Get minimum citation threshold based on year"""
        current_year = datetime.now().year
        years_since = current_year - year

        # More recent papers need fewer citations
        if years_since <= 1:
            return 0  # Very recent papers
        elif years_since <= 2:
            return 5
        elif years_since <= 3:
            return 10
        else:
            return 15

    def create_setup_status(
        self, setup_success: bool, api_status: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Create setup status documentation"""
        domains = self.get_domains_from_analysis()

        status = {
            "timestamp": datetime.now().isoformat(),
            "status": "completed" if setup_success else "failed",
            "dependencies_loaded": {
                "worker1_citation_apis": all(api_status.values()),
                "worker3_venue_analysis": self.venue_analyzer is not None,
                "worker4_computational_analyzer": self.computational_analyzer
                is not None,
                "domain_analysis": self.domain_analysis is not None,
            },
            "api_status": {
                api_name: "ok" if status else "failed"
                for api_name, status in api_status.items()
            },
            "collection_targets": {
                "total_papers_target": len(domains)
                * 6
                * 8,  # domains * years * papers_per_domain_year
                "papers_per_domain_year": 8,
                "domains_count": len(domains),
                "years_span": 6,
                "domains": domains,
            },
            "issues": []
            if setup_success
            else ["Setup failed - check logs for details"],
        }

        return status
