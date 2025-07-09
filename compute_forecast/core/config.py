import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class CitationSourceConfig:
    rate_limit: float
    retry_attempts: int
    api_key: Optional[str] = None
    timeout: int = 30
    use_browser_automation: bool = False
    manual_captcha_intervention: bool = False


@dataclass
class CollectionConfig:
    papers_per_domain_year: int
    total_target_min: int
    total_target_max: int
    citation_threshold_base: int


@dataclass
class QualityConfig:
    computational_richness_min: float
    citation_reliability_min: float
    institution_coverage_min: float
    overall_quality_min: float


class ConfigManager:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if self._config is None:
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        return self._config

    def get_citation_config(self, source: str) -> CitationSourceConfig:
        """Get configuration for specific citation source"""
        config = self.load_config()
        source_config = config["citation_sources"][source]
        return CitationSourceConfig(**source_config)

    def get_collection_config(self) -> CollectionConfig:
        """Get paper collection configuration"""
        config = self.load_config()
        return CollectionConfig(**config["collection_targets"])

    def get_quality_config(self) -> QualityConfig:
        """Get quality control configuration"""
        config = self.load_config()
        return QualityConfig(**config["quality_thresholds"])

    def get_venues_config(self) -> Dict[str, Any]:
        """Get venue configuration"""
        venue_config_path = self.config_path.parent / "venues.yaml"
        with open(venue_config_path, "r") as f:
            return yaml.safe_load(f) or {}
