"""
Venue mapping loader for Worker 2/3 data integration.
Loads venue mappings and configurations from various sources.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class VenueConfig:
    """Configuration for a specific venue"""

    venue_name: str
    venue_tier: str = "tier4"  # tier1, tier2, tier3, tier4
    computational_focus: float = 0.5
    domain: str = "general"
    aliases: List[str] = field(default_factory=list)


@dataclass
class VenueMappingLoadResult:
    """Result of loading venue mappings"""

    venue_mappings: Dict[str, str]  # raw_venue -> normalized_venue
    venue_configs: Dict[str, VenueConfig]  # normalized_venue -> config
    canonical_venues: Set[str]
    load_errors: List[str] = field(default_factory=list)
    sources_loaded: List[str] = field(default_factory=list)


class VenueMappingLoader:
    """Loads venue mappings from Worker 2/3 data files"""

    def __init__(self, base_path: Path = Path(".")):
        self.base_path = base_path
        self.logger = logging.getLogger(__name__)

    def load_all_mappings(self) -> VenueMappingLoadResult:
        """
        Load venue mappings from all available sources

        Priority order:
        1. Worker 6 venue mapping (most comprehensive)
        2. Manual venue corrections
        3. Venues.yaml configuration
        4. Worker 3 venue database
        """
        result = VenueMappingLoadResult(
            venue_mappings={}, venue_configs={}, canonical_venues=set()
        )

        # Source 1: Worker 6 venue mapping (highest priority)
        worker6_path = self.base_path / "worker6_venue_mapping.json"
        if worker6_path.exists():
            try:
                self._load_worker6_mappings(worker6_path, result)
                result.sources_loaded.append("worker6_venue_mapping.json")
                self.logger.info(
                    f"Loaded {len(result.venue_mappings)} mappings from Worker 6"
                )
            except Exception as e:
                error_msg = f"Failed to load Worker 6 mappings: {e}"
                result.load_errors.append(error_msg)
                self.logger.error(error_msg)

        # Source 2: Manual corrections (override existing mappings)
        manual_path = self.base_path / "data/manual_venue_corrections.json"
        if manual_path.exists():
            try:
                self._load_manual_corrections(manual_path, result)
                result.sources_loaded.append("manual_venue_corrections.json")
                self.logger.info("Loaded manual venue corrections")
            except Exception as e:
                error_msg = f"Failed to load manual corrections: {e}"
                result.load_errors.append(error_msg)
                self.logger.error(error_msg)

        # Source 3: venues.yaml configuration (for tiers and computational focus)
        venues_yaml_path = self.base_path / "config/venues.yaml"
        if venues_yaml_path.exists():
            try:
                self._load_venues_yaml(venues_yaml_path, result)
                result.sources_loaded.append("config/venues.yaml")
                self.logger.info("Loaded venue configuration from venues.yaml")
            except Exception as e:
                error_msg = f"Failed to load venues.yaml: {e}"
                result.load_errors.append(error_msg)
                self.logger.error(error_msg)

        # Source 4: Worker 3 venue database (backup mappings)
        worker3_path = self.base_path / "status/worker3-venue-database.json"
        if worker3_path.exists():
            try:
                self._load_worker3_venues(worker3_path, result)
                result.sources_loaded.append("worker3-venue-database.json")
                self.logger.info("Loaded Worker 3 venue database")
            except Exception as e:
                error_msg = f"Failed to load Worker 3 venues: {e}"
                result.load_errors.append(error_msg)
                self.logger.error(error_msg)

        # Finalize canonical venues set
        result.canonical_venues = set(result.venue_mappings.values())

        self.logger.info(f"Total mappings loaded: {len(result.venue_mappings)}")
        self.logger.info(f"Canonical venues: {len(result.canonical_venues)}")

        return result

    def _load_worker6_mappings(
        self, file_path: Path, result: VenueMappingLoadResult
    ) -> None:
        """Load mappings from Worker 6 venue mapping file"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load venue normalization map
        if "venue_normalization_map" in data:
            for raw_venue, normalized_venue in data["venue_normalization_map"].items():
                result.venue_mappings[raw_venue] = normalized_venue

        # Load canonical venues and create basic configs
        if "canonical_venues" in data:
            for venue in data["canonical_venues"]:
                if venue not in result.venue_configs:
                    result.venue_configs[venue] = VenueConfig(
                        venue_name=venue,
                        venue_tier=self._infer_venue_tier(venue),
                        computational_focus=self._infer_computational_focus(venue),
                    )

    def _load_manual_corrections(
        self, file_path: Path, result: VenueMappingLoadResult
    ) -> None:
        """Load manual venue corrections (overrides other mappings)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Manual corrections override existing mappings
            if "venue_mappings" in data:
                for raw_venue, normalized_venue in data["venue_mappings"].items():
                    result.venue_mappings[raw_venue] = normalized_venue

        except FileNotFoundError:
            # Manual corrections file is optional
            pass

    def _load_venues_yaml(
        self, file_path: Path, result: VenueMappingLoadResult
    ) -> None:
        """Load venue tiers and computational focus from venues.yaml"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Load venues by domain and tier
        if "venues_by_domain" in data:
            for domain, tiers in data["venues_by_domain"].items():
                for tier, venues in tiers.items():
                    if isinstance(venues, list):
                        for venue in venues:
                            if venue in result.venue_configs:
                                result.venue_configs[venue].venue_tier = tier
                                result.venue_configs[venue].domain = domain
                            else:
                                result.venue_configs[venue] = VenueConfig(
                                    venue_name=venue,
                                    venue_tier=tier,
                                    domain=domain,
                                    computational_focus=self._infer_computational_focus(
                                        venue
                                    ),
                                )

        # Load computational focus scores
        if "computational_focus_scores" in data:
            for venue, score in data["computational_focus_scores"].items():
                if venue in result.venue_configs:
                    result.venue_configs[venue].computational_focus = score
                else:
                    result.venue_configs[venue] = VenueConfig(
                        venue_name=venue, computational_focus=score
                    )

    def _load_worker3_venues(
        self, file_path: Path, result: VenueMappingLoadResult
    ) -> None:
        """Load additional venue data from Worker 3 status"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)

            # Worker 3 data might contain additional venue information
            # This is a backup source, so we don't override existing mappings

        except (FileNotFoundError, json.JSONDecodeError):
            # Worker 3 data is optional
            pass

    def _infer_venue_tier(self, venue: str) -> str:
        """Infer venue tier based on venue name"""
        venue_upper = venue.upper()

        # Tier 1: Top-tier conferences
        if venue_upper in ["NEURIPS", "ICML", "ICLR", "CVPR", "ICCV", "ECCV"]:
            return "tier1"

        # Tier 2: Strong conferences
        if venue_upper in [
            "AAAI",
            "EMNLP",
            "ACL",
            "NAACL",
            "AISTATS",
            "UAI",
            "ICRA",
            "IROS",
        ]:
            return "tier2"

        # Tier 3: Good conferences
        if venue_upper in [
            "BMVC",
            "WACV",
            "COLING",
            "EACL",
            "CHI",
            "SIGIR",
            "KDD",
            "WWW",
        ]:
            return "tier3"

        # Default: Tier 4
        return "tier4"

    def _infer_computational_focus(self, venue: str) -> float:
        """Infer computational focus score based on venue name"""
        venue_upper = venue.upper()

        # High computational focus
        if venue_upper in [
            "NEURIPS",
            "ICML",
            "ICLR",
            "CVPR",
            "ICCV",
            "ECCV",
            "ICRA",
            "IROS",
        ]:
            return 0.9

        # Medium computational focus
        if venue_upper in ["AAAI", "AISTATS", "UAI", "KDD", "WWW"]:
            return 0.8

        # Lower computational focus (more theoretical or domain-specific)
        if venue_upper in ["ACL", "EMNLP", "NAACL", "CHI", "SIGIR"]:
            return 0.7

        # Default
        return 0.5


def create_manual_corrections_template(output_path: Path) -> None:
    """Create template file for manual venue corrections"""
    template = {
        "venue_mappings": {
            "Example Raw Venue Name": "Canonical Venue Name",
            "ICML 2024": "ICML",
            "Neural Information Processing Systems": "NeurIPS",
        },
        "instructions": {
            "purpose": "Manual overrides for venue normalization",
            "priority": "These mappings override all other sources",
            "format": "raw_venue_name -> canonical_venue_name",
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
