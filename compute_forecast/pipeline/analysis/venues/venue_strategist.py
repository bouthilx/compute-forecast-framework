"""
Strategic Venue List Generator

This module generates prioritized venue lists for external institution paper collection
based on Mila publication patterns and venue computational focus.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from compute_forecast.core.config import ConfigManager
from compute_forecast.pipeline.analysis.venues.venue_analyzer import MilaVenueAnalyzer
from compute_forecast.pipeline.analysis.venues.venue_database import VenueDatabase
from compute_forecast.pipeline.analysis.venues.venue_scoring import VenueScorer

logger = logging.getLogger(__name__)


@dataclass
class VenueCollectionParams:
    """Collection parameters for a venue"""

    papers_per_year: int
    citation_threshold: int
    domains: List[str]


@dataclass
class VenueMetadata:
    """Metadata for venue quality assessment"""

    computational_score: float
    mila_papers: int
    avg_citations: float
    venue_type: str
    domain_breadth: int
    priority_score: float


@dataclass
class StrategicVenue:
    """Strategic venue for collection"""

    venue: str
    priority: int
    collection_params: VenueCollectionParams
    metadata: VenueMetadata


@dataclass
class CollectionStrategy:
    """Overall collection strategy parameters"""

    total_target_papers: int
    venue_coverage_target: int
    papers_per_venue_year: int
    citation_thresholds: Dict[str, int]
    backup_venues: List[str]


class VenueStrategist:
    """Generates strategic venue lists for external institution paper collection"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.venue_db = VenueDatabase(config_manager)
        self.mila_analyzer = MilaVenueAnalyzer(config_manager)
        self.scorer = VenueScorer(self.venue_db, self.mila_analyzer)

        # Strategic weights for venue selection
        self.selection_weights = {
            "mila_usage_weight": 0.25,  # How much Mila uses this venue
            "computational_weight": 0.30,  # Computational research focus
            "citation_weight": 0.20,  # Average citation impact
            "coverage_weight": 0.15,  # Domain breadth coverage
            "venue_tier_weight": 0.10,  # Venue prestige/tier
        }

        # Target parameters
        self.target_total_papers = 800
        self.target_venue_count = 25
        self.papers_per_venue_base = 8

    def load_mila_venue_data(self) -> Optional[Dict[str, Any]]:
        """Load Mila venue statistics from Worker 2 or fallback"""

        # Check for Worker 2 output first
        worker2_file = Path("data/mila_venue_statistics.json")
        if worker2_file.exists():
            logger.info("Loading Mila venue statistics from Worker 2")
            with open(worker2_file, "r") as f:
                data = json.load(f)
                return dict(data) if isinstance(data, dict) else None

        # Fallback: Use existing venue analysis infrastructure
        logger.info("Worker 2 data not available, using venue analysis fallback")
        try:
            mila_venues = self.mila_analyzer.analyze_mila_venues()
            logger.info(f"Fallback analysis found {mila_venues['total_venues']} venues")
            return mila_venues
        except Exception as e:
            logger.error(f"Failed to load venue data: {e}")
            return None

    def calculate_venue_priority(
        self, venue: str, venue_stats: Dict[str, Any], mila_data: Dict[str, Any]
    ) -> Tuple[float, VenueMetadata]:
        """Calculate priority score for a venue"""

        # Get venue info from database
        venue_info = self.venue_db.get_venue_info(venue)

        # Extract Mila usage data
        mila_venue_stats = mila_data.get("venue_statistics", {}).get(venue, {})
        mila_papers = mila_venue_stats.get("total_count", 0)

        # Get domain coverage
        domains = mila_venue_stats.get("domains", [])
        domain_breadth = len(domains) if domains else 1

        # Calculate component scores
        scores = {}

        # 1. Mila usage score (normalized)
        max_mila_papers = 200  # Reasonable upper bound
        scores["mila_usage"] = min(mila_papers / max_mila_papers, 1.0)

        # 2. Computational focus score
        if venue_info:
            scores["computational"] = venue_info.computational_focus
            venue_type = venue_info.venue_type
            tier_score = self._get_tier_score(venue_info.tier.value)
        else:
            scores["computational"] = 0.5
            venue_type = "unknown"
            tier_score = 0.5

        # 3. Citation impact (estimated)
        avg_citations = self._estimate_venue_citations(venue, mila_venue_stats)
        max_citations = 100  # Reasonable upper bound
        scores["citation"] = min(avg_citations / max_citations, 1.0)

        # 4. Domain coverage score
        max_domains = 10  # Reasonable upper bound
        scores["coverage"] = min(domain_breadth / max_domains, 1.0)

        # 5. Venue tier score
        scores["tier"] = tier_score

        # Calculate weighted priority score
        priority_score = (
            scores["mila_usage"] * self.selection_weights["mila_usage_weight"]
            + scores["computational"] * self.selection_weights["computational_weight"]
            + scores["citation"] * self.selection_weights["citation_weight"]
            + scores["coverage"] * self.selection_weights["coverage_weight"]
            + scores["tier"] * self.selection_weights["venue_tier_weight"]
        )

        # Create metadata
        metadata = VenueMetadata(
            computational_score=scores["computational"],
            mila_papers=mila_papers,
            avg_citations=avg_citations,
            venue_type=venue_type,
            domain_breadth=domain_breadth,
            priority_score=priority_score,
        )

        return priority_score, metadata

    def _get_tier_score(self, tier: str) -> float:
        """Get numerical score for venue tier"""
        tier_scores = {
            "tier1": 1.0,
            "tier2": 0.8,
            "specialized": 0.9,
            "medical": 0.85,
            "robotics": 0.85,
            "theory": 0.7,
        }
        return tier_scores.get(tier, 0.5)

    def _estimate_venue_citations(
        self, venue: str, venue_stats: Dict[str, Any]
    ) -> float:
        """Estimate average citations for venue papers"""
        # This is a simplified estimation - in real implementation would use historical data

        # Base citation estimates by venue type/tier
        citation_estimates = {
            "NeurIPS": 45.0,
            "ICML": 42.0,
            "ICLR": 38.0,
            "CVPR": 35.0,
            "ICCV": 32.0,
            "ECCV": 30.0,
            "ACL": 25.0,
            "EMNLP": 22.0,
            "NAACL": 20.0,
            "AAAI": 28.0,
            "IJCAI": 26.0,
            "AAMAS": 18.0,
            "ICRA": 24.0,
            "IROS": 20.0,
            "RSS": 22.0,
        }

        return citation_estimates.get(venue, 15.0)  # Default estimate

    def generate_primary_venues(
        self, mila_data: Dict[str, Any]
    ) -> List[StrategicVenue]:
        """Generate primary venue list for broad collection"""
        logger.info("Generating primary venue list")

        # Get all venues from Mila data and venue database
        mila_venues = set(mila_data.get("venue_statistics", {}).keys())
        db_venues = set(v.name for v in self.venue_db._venue_db.values())
        all_venues = mila_venues | db_venues

        # Calculate priority scores for all venues
        venue_priorities = []
        for venue in all_venues:
            try:
                priority_score, metadata = self.calculate_venue_priority(
                    venue, {}, mila_data
                )
                venue_priorities.append((venue, priority_score, metadata))
            except Exception as e:
                logger.warning(f"Failed to score venue {venue}: {e}")
                continue

        # Sort by priority score
        venue_priorities.sort(key=lambda x: x[1], reverse=True)

        # Generate strategic venues
        strategic_venues = []
        for i, (venue, score, metadata) in enumerate(
            venue_priorities[: self.target_venue_count]
        ):
            # Calculate collection parameters based on priority
            papers_per_year = self._calculate_papers_per_year(score, i)
            citation_threshold = self._calculate_citation_threshold(venue, metadata)
            domains = self._get_venue_domains(venue, mila_data)

            collection_params = VenueCollectionParams(
                papers_per_year=papers_per_year,
                citation_threshold=citation_threshold,
                domains=domains,
            )

            strategic_venue = StrategicVenue(
                venue=venue,
                priority=i + 1,
                collection_params=collection_params,
                metadata=metadata,
            )

            strategic_venues.append(strategic_venue)

        logger.info(f"Generated {len(strategic_venues)} primary venues")
        return strategic_venues

    def _calculate_papers_per_year(self, priority_score: float, rank: int) -> int:
        """Calculate papers per year based on venue priority"""
        base_papers = self.papers_per_venue_base

        # Higher priority venues get more papers
        if rank < 5:  # Top 5 venues
            return base_papers + 7  # 15 papers
        elif rank < 10:  # Top 10 venues
            return base_papers + 4  # 12 papers
        elif rank < 15:  # Top 15 venues
            return base_papers + 2  # 10 papers
        else:
            return base_papers  # 8 papers

    def _calculate_citation_threshold(self, venue: str, metadata: VenueMetadata) -> int:
        """Calculate citation threshold for venue"""
        # Base threshold adjusted by venue quality
        base_threshold = 10

        if metadata.computational_score > 0.9:
            return base_threshold + 5  # High computational venues: 15
        elif metadata.computational_score > 0.7:
            return base_threshold  # Medium computational venues: 10
        else:
            return base_threshold - 3  # Lower computational venues: 7

    def _get_venue_domains(self, venue: str, mila_data: Dict[str, Any]) -> List[str]:
        """Get research domains for a venue"""
        venue_stats = mila_data.get("venue_statistics", {}).get(venue, {})
        domains = venue_stats.get("domains", [])

        # Fallback to venue database mapping
        if not domains:
            venue_info = self.venue_db.get_venue_info(venue)
            if venue_info:
                # Map venue database domain to research domains
                domain_mapping = {
                    "computer_vision": ["Computer Vision"],
                    "nlp": ["Natural Language Processing"],
                    "ml_general": ["Machine Learning"],
                    "reinforcement_learning": ["Reinforcement Learning"],
                    "data_science": ["Data Science"],
                    "cybersecurity": ["Cybersecurity"],
                    "hci": ["Human-Computer Interaction"],
                    "bioinformatics": ["Bioinformatics"],
                }
                domains = domain_mapping.get(venue_info.domain, ["General"])

        return list(domains[:4])  # Limit to 4 domains

    def generate_domain_specific_venues(
        self, mila_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate domain-specific venue lists"""
        logger.info("Generating domain-specific venue lists")

        # Define major research domains
        research_domains = [
            "Computer Vision",
            "Natural Language Processing",
            "Machine Learning",
            "Reinforcement Learning",
            "Data Science",
        ]

        domain_venues = {}

        for domain in research_domains:
            # Get venues that publish in this domain
            domain_venue_list: List[Dict[str, Any]] = []

            # Get venues from venue database for this domain
            db_domain_map = {
                "Computer Vision": "computer_vision",
                "Natural Language Processing": "nlp",
                "Machine Learning": "ml_general",
                "Reinforcement Learning": "reinforcement_learning",
                "Data Science": "data_science",
            }

            db_domain = db_domain_map.get(domain)
            if db_domain:
                domain_db_venues = self.venue_db.get_venues_by_domain(db_domain)

                for venue_info in domain_db_venues:
                    priority_score, metadata = self.calculate_venue_priority(
                        venue_info.name, {}, mila_data
                    )

                    papers_per_year = min(
                        self.papers_per_venue_base + 2, 12
                    )  # 10-12 papers

                    domain_venue_list.append(
                        {
                            "venue": venue_info.name,
                            "priority": len(domain_venue_list) + 1,
                            "papers_per_year": papers_per_year,
                            "computational_score": metadata.computational_score,
                            "priority_score": priority_score,
                        }
                    )

            # Sort by priority score and take top venues
            domain_venue_list.sort(
                key=lambda x: float(x["priority_score"]), reverse=True
            )
            domain_venues[domain] = domain_venue_list[:8]  # Top 8 per domain

        logger.info(
            f"Generated domain-specific venues for {len(domain_venues)} domains"
        )
        return domain_venues

    def generate_collection_strategy(
        self, primary_venues: List[StrategicVenue]
    ) -> CollectionStrategy:
        """Generate overall collection strategy"""
        logger.info("Generating collection strategy")

        # Calculate total target papers
        total_papers = sum(
            venue.collection_params.papers_per_year for venue in primary_venues
        )

        # Adjust if needed to meet target
        if total_papers < self.target_total_papers:
            # Increase papers per venue proportionally
            adjustment_factor = self.target_total_papers / total_papers
            for venue in primary_venues:
                venue.collection_params.papers_per_year = int(
                    venue.collection_params.papers_per_year * adjustment_factor
                )
            total_papers = self.target_total_papers

        # Define citation thresholds by year
        citation_thresholds = {
            "2024": 5,  # Recent papers, lower threshold
            "2023": 8,  # 1 year old
            "2022": 12,  # 2 years old
            "2021": 15,  # 3 years old
            "2020": 20,  # Older papers, higher threshold
        }

        # Select backup venues (high-quality general venues)
        backup_venues = ["ICLR", "ICML", "AAAI", "IJCAI", "AISTATS"]

        strategy = CollectionStrategy(
            total_target_papers=total_papers,
            venue_coverage_target=len(primary_venues),
            papers_per_venue_year=self.papers_per_venue_base,
            citation_thresholds=citation_thresholds,
            backup_venues=backup_venues,
        )

        logger.info(
            f"Collection strategy: {total_papers} papers across {len(primary_venues)} venues"
        )
        return strategy

    def generate_strategic_venue_collection(self) -> Dict[str, Any]:
        """Generate complete strategic venue collection output"""
        logger.info("Starting strategic venue collection generation")

        # Load Mila venue data
        mila_data = self.load_mila_venue_data()
        if not mila_data:
            raise ValueError("Failed to load Mila venue data")

        # Generate primary venues
        primary_venues = self.generate_primary_venues(mila_data)

        # Generate domain-specific venues
        domain_specific = self.generate_domain_specific_venues(mila_data)

        # Generate collection strategy
        collection_strategy = self.generate_collection_strategy(primary_venues)

        # Build output structure
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "worker": "worker3",
                "data_source": "venue_analysis_fallback"
                if not Path("data/mila_venue_statistics.json").exists()
                else "worker2_data",
                "total_venues_analyzed": len(mila_data.get("venue_statistics", {})),
                "selection_weights": self.selection_weights,
            },
            "primary_venues": [
                {
                    "venue": venue.venue,
                    "priority": venue.priority,
                    "collection_params": asdict(venue.collection_params),
                    "metadata": asdict(venue.metadata),
                }
                for venue in primary_venues
            ],
            "domain_specific": domain_specific,
            "collection_strategy": asdict(collection_strategy),
        }

        logger.info("Strategic venue collection generation complete")
        return output
