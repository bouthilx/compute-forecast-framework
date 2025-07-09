"""
Comprehensive Venue Database Module

This module builds and manages a comprehensive database of academic venues
categorized by research domains and importance tiers.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from compute_forecast.core.config import ConfigManager

logger = logging.getLogger(__name__)


class VenueTier(Enum):
    """Venue importance tiers"""

    TIER1 = "tier1"
    TIER2 = "tier2"
    SPECIALIZED = "specialized"
    MEDICAL = "medical"
    ROBOTICS = "robotics"
    THEORY = "theory"


@dataclass
class VenueInfo:
    """Comprehensive venue information"""

    name: str
    domain: str
    tier: VenueTier
    computational_focus: float
    aliases: List[str]
    full_name: str
    venue_type: str  # 'conference' or 'journal'
    frequency: str  # 'annual', 'biannual', etc.
    impact_score: Optional[float] = None
    h5_index: Optional[int] = None
    acceptance_rate: Optional[float] = None


class VenueDatabase:
    """Comprehensive venue database with categorization and metadata"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.venue_config = self.config.get_venues_config()
        self.venues_by_domain = self.venue_config.get("venues_by_domain", {})
        self.computational_scores = self.venue_config.get(
            "computational_focus_scores", {}
        )

        # Initialize venue database
        self._venue_db: Dict[str, VenueInfo] = {}
        self._domain_mapping: Dict[str, List[str]] = {}
        self._tier_mapping: Dict[str, List[str]] = {}

        self._build_database()

    def _build_database(self):
        """Build comprehensive venue database from configuration"""
        logger.info("Building comprehensive venue database")

        # Expanded venue database with additional metadata
        extended_venues = {
            # Computer Vision
            "computer_vision": {
                "tier1": [
                    (
                        "CVPR",
                        "Conference on Computer Vision and Pattern Recognition",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICCV",
                        "International Conference on Computer Vision",
                        "conference",
                        "biannual",
                    ),
                    (
                        "ECCV",
                        "European Conference on Computer Vision",
                        "conference",
                        "biannual",
                    ),
                ],
                "tier2": [
                    (
                        "BMVC",
                        "British Machine Vision Conference",
                        "conference",
                        "annual",
                    ),
                    (
                        "WACV",
                        "Winter Conference on Applications of Computer Vision",
                        "conference",
                        "annual",
                    ),
                    (
                        "ACCV",
                        "Asian Conference on Computer Vision",
                        "conference",
                        "biannual",
                    ),
                ],
                "medical": [
                    (
                        "MICCAI",
                        "Medical Image Computing and Computer Assisted Intervention",
                        "conference",
                        "annual",
                    ),
                    (
                        "IPMI",
                        "Information Processing in Medical Imaging",
                        "conference",
                        "biannual",
                    ),
                    (
                        "ISBI",
                        "International Symposium on Biomedical Imaging",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "3DV",
                        "International Conference on 3D Vision",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICCV Workshops",
                        "ICCV Workshop Proceedings",
                        "workshop",
                        "biannual",
                    ),
                ],
            },
            # Natural Language Processing
            "nlp": {
                "tier1": [
                    (
                        "ACL",
                        "Association for Computational Linguistics",
                        "conference",
                        "annual",
                    ),
                    (
                        "EMNLP",
                        "Empirical Methods in Natural Language Processing",
                        "conference",
                        "annual",
                    ),
                    (
                        "NAACL",
                        "North American Chapter of the Association for Computational Linguistics",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "COLING",
                        "International Conference on Computational Linguistics",
                        "conference",
                        "biannual",
                    ),
                    (
                        "EACL",
                        "European Chapter of the Association for Computational Linguistics",
                        "conference",
                        "triennial",
                    ),
                    (
                        "CoNLL",
                        "Conference on Computational Natural Language Learning",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    ("WMT", "Workshop on Machine Translation", "workshop", "annual"),
                    ("SemEval", "Semantic Evaluation Workshop", "workshop", "annual"),
                ],
            },
            # Machine Learning General
            "ml_general": {
                "tier1": [
                    (
                        "NeurIPS",
                        "Conference on Neural Information Processing Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICML",
                        "International Conference on Machine Learning",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICLR",
                        "International Conference on Learning Representations",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "AISTATS",
                        "International Conference on Artificial Intelligence and Statistics",
                        "conference",
                        "annual",
                    ),
                    (
                        "UAI",
                        "Conference on Uncertainty in Artificial Intelligence",
                        "conference",
                        "annual",
                    ),
                    ("COLT", "Conference on Learning Theory", "conference", "annual"),
                ],
            },
            # Reinforcement Learning
            "reinforcement_learning": {
                "specialized": [
                    (
                        "AAMAS",
                        "International Conference on Autonomous Agents and Multiagent Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "AAAI",
                        "AAAI Conference on Artificial Intelligence",
                        "conference",
                        "annual",
                    ),
                    (
                        "IJCAI",
                        "International Joint Conference on Artificial Intelligence",
                        "conference",
                        "annual",
                    ),
                ],
                "robotics": [
                    (
                        "ICRA",
                        "International Conference on Robotics and Automation",
                        "conference",
                        "annual",
                    ),
                    (
                        "IROS",
                        "International Conference on Intelligent Robots and Systems",
                        "conference",
                        "annual",
                    ),
                    ("RSS", "Robotics: Science and Systems", "conference", "annual"),
                ],
            },
            # Graph Learning
            "graph_learning": {
                "specialized": [
                    (
                        "WWW",
                        "International World Wide Web Conference",
                        "conference",
                        "annual",
                    ),
                    (
                        "KDD",
                        "ACM SIGKDD Conference on Knowledge Discovery and Data Mining",
                        "conference",
                        "annual",
                    ),
                    (
                        "WSDM",
                        "ACM International Conference on Web Search and Data Mining",
                        "conference",
                        "annual",
                    ),
                ],
                "theory": [
                    (
                        "SODA",
                        "ACM-SIAM Symposium on Discrete Algorithms",
                        "conference",
                        "annual",
                    ),
                    (
                        "FOCS",
                        "IEEE Symposium on Foundations of Computer Science",
                        "conference",
                        "annual",
                    ),
                    (
                        "STOC",
                        "ACM Symposium on Theory of Computing",
                        "conference",
                        "annual",
                    ),
                ],
            },
            # Additional domains
            "data_science": {
                "tier1": [
                    (
                        "SIGMOD",
                        "ACM SIGMOD International Conference on Management of Data",
                        "conference",
                        "annual",
                    ),
                    (
                        "VLDB",
                        "International Conference on Very Large Data Bases",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICDE",
                        "IEEE International Conference on Data Engineering",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "PODS",
                        "ACM Symposium on Principles of Database Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "EDBT",
                        "International Conference on Extending Database Technology",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "ICDM",
                        "IEEE International Conference on Data Mining",
                        "conference",
                        "annual",
                    ),
                    (
                        "SDM",
                        "SIAM International Conference on Data Mining",
                        "conference",
                        "annual",
                    ),
                    (
                        "PKDD",
                        "European Conference on Principles and Practice of Knowledge Discovery in Databases",
                        "conference",
                        "annual",
                    ),
                    (
                        "CIKM",
                        "ACM International Conference on Information and Knowledge Management",
                        "conference",
                        "annual",
                    ),
                    (
                        "RecSys",
                        "ACM Conference on Recommender Systems",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "cybersecurity": {
                "tier1": [
                    (
                        "CCS",
                        "ACM Conference on Computer and Communications Security",
                        "conference",
                        "annual",
                    ),
                    (
                        "S&P",
                        "IEEE Symposium on Security and Privacy",
                        "conference",
                        "annual",
                    ),
                    (
                        "USENIX Security",
                        "USENIX Security Symposium",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "NDSS",
                        "Network and Distributed System Security Symposium",
                        "conference",
                        "annual",
                    ),
                    (
                        "ESORICS",
                        "European Symposium on Research in Computer Security",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "CRYPTO",
                        "International Cryptology Conference",
                        "conference",
                        "annual",
                    ),
                    (
                        "EUROCRYPT",
                        "International Conference on the Theory and Applications of Cryptographic Techniques",
                        "conference",
                        "annual",
                    ),
                    (
                        "ASIACRYPT",
                        "International Conference on the Theory and Application of Cryptology and Information Security",
                        "conference",
                        "annual",
                    ),
                    (
                        "TCC",
                        "Theory of Cryptography Conference",
                        "conference",
                        "annual",
                    ),
                    (
                        "FC",
                        "International Conference on Financial Cryptography and Data Security",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "hci": {
                "tier1": [
                    (
                        "CHI",
                        "ACM Conference on Human Factors in Computing Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "UIST",
                        "ACM Symposium on User Interface Software and Technology",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "IUI",
                        "International Conference on Intelligent User Interfaces",
                        "conference",
                        "annual",
                    ),
                    (
                        "CSCW",
                        "ACM Conference on Computer-Supported Cooperative Work",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "UbiComp",
                        "ACM International Joint Conference on Pervasive and Ubiquitous Computing",
                        "conference",
                        "annual",
                    ),
                    (
                        "ASSETS",
                        "ACM SIGACCESS Conference on Computers and Accessibility",
                        "conference",
                        "annual",
                    ),
                    (
                        "DIS",
                        "ACM Conference on Designing Interactive Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "TEI",
                        "ACM International Conference on Tangible, Embedded, and Embodied Interaction",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "bioinformatics": {
                "tier1": [
                    (
                        "RECOMB",
                        "International Conference on Research in Computational Molecular Biology",
                        "conference",
                        "annual",
                    ),
                    (
                        "ISMB",
                        "Intelligent Systems for Molecular Biology",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "PSB",
                        "Pacific Symposium on Biocomputing",
                        "conference",
                        "annual",
                    ),
                    (
                        "WABI",
                        "Workshop on Algorithms in Bioinformatics",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "BIBM",
                        "IEEE International Conference on Bioinformatics and Biomedicine",
                        "conference",
                        "annual",
                    ),
                    (
                        "BCB",
                        "ACM Conference on Bioinformatics, Computational Biology, and Health Informatics",
                        "conference",
                        "annual",
                    ),
                    (
                        "CSB",
                        "IEEE International Conference on Computational Systems Biology",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "quantum_computing": {
                "tier1": [
                    (
                        "QCE",
                        "IEEE International Conference on Quantum Computing and Engineering",
                        "conference",
                        "annual",
                    ),
                    (
                        "TQC",
                        "Conference on the Theory of Quantum Computation, Communication and Cryptography",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "QCMC",
                        "International Conference on Quantum Communication, Measurement and Computing",
                        "conference",
                        "biannual",
                    ),
                    (
                        "QPL",
                        "International Conference on Quantum Physics and Logic",
                        "conference",
                        "annual",
                    ),
                    (
                        "QIP",
                        "Conference on Quantum Information Processing",
                        "conference",
                        "annual",
                    ),
                    (
                        "QCTIP",
                        "International Conference on Quantum Communication, Theory, and Information Processing",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "distributed_systems": {
                "tier1": [
                    (
                        "SOSP",
                        "ACM Symposium on Operating Systems Principles",
                        "conference",
                        "biannual",
                    ),
                    (
                        "OSDI",
                        "USENIX Symposium on Operating Systems Design and Implementation",
                        "conference",
                        "biannual",
                    ),
                    (
                        "NSDI",
                        "USENIX Symposium on Networked Systems Design and Implementation",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "EuroSys",
                        "European Conference on Computer Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "DISC",
                        "International Symposium on Distributed Computing",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "PODC",
                        "ACM Symposium on Principles of Distributed Computing",
                        "conference",
                        "annual",
                    ),
                    (
                        "SPAA",
                        "ACM Symposium on Parallelism in Algorithms and Architectures",
                        "conference",
                        "annual",
                    ),
                    (
                        "PPoPP",
                        "ACM Symposium on Principles and Practice of Parallel Programming",
                        "conference",
                        "annual",
                    ),
                ],
            },
            "software_engineering": {
                "tier1": [
                    (
                        "ICSE",
                        "International Conference on Software Engineering",
                        "conference",
                        "annual",
                    ),
                    (
                        "FSE",
                        "ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering",
                        "conference",
                        "annual",
                    ),
                ],
                "tier2": [
                    (
                        "ASE",
                        "IEEE/ACM International Conference on Automated Software Engineering",
                        "conference",
                        "annual",
                    ),
                    (
                        "OOPSLA",
                        "ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications",
                        "conference",
                        "annual",
                    ),
                ],
                "specialized": [
                    (
                        "PLDI",
                        "ACM SIGPLAN Conference on Programming Language Design and Implementation",
                        "conference",
                        "annual",
                    ),
                    (
                        "POPL",
                        "ACM SIGPLAN Symposium on Principles of Programming Languages",
                        "conference",
                        "annual",
                    ),
                    (
                        "ISSTA",
                        "International Symposium on Software Testing and Analysis",
                        "conference",
                        "annual",
                    ),
                    (
                        "ESEM",
                        "International Symposium on Empirical Software Engineering and Measurement",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICPC",
                        "IEEE International Conference on Program Comprehension",
                        "conference",
                        "annual",
                    ),
                    (
                        "MSR",
                        "International Conference on Mining Software Repositories",
                        "conference",
                        "annual",
                    ),
                    (
                        "ICSME",
                        "IEEE International Conference on Software Maintenance and Evolution",
                        "conference",
                        "annual",
                    ),
                    (
                        "RE",
                        "IEEE International Requirements Engineering Conference",
                        "conference",
                        "annual",
                    ),
                    (
                        "MODELS",
                        "ACM/IEEE International Conference on Model Driven Engineering Languages and Systems",
                        "conference",
                        "annual",
                    ),
                    (
                        "ECOOP",
                        "European Conference on Object-Oriented Programming",
                        "conference",
                        "annual",
                    ),
                ],
            },
        }

        # Build venue database
        for domain, tiers in extended_venues.items():
            self._domain_mapping[domain] = []

            for tier_name, venues in tiers.items():
                tier = VenueTier(tier_name)
                self._tier_mapping.setdefault(tier_name, [])

                for venue_info in venues:
                    venue_short, venue_full, venue_type, frequency = venue_info

                    # Get computational focus score
                    comp_score = self.computational_scores.get(venue_short, 0.5)

                    # Create venue info object
                    venue_obj = VenueInfo(
                        name=venue_short,
                        domain=domain,
                        tier=tier,
                        computational_focus=comp_score,
                        aliases=[venue_short, venue_full],
                        full_name=venue_full,
                        venue_type=venue_type,
                        frequency=frequency,
                    )

                    self._venue_db[venue_short] = venue_obj
                    self._domain_mapping[domain].append(venue_short)
                    self._tier_mapping[tier_name].append(venue_short)

        logger.info(
            f"Built database with {len(self._venue_db)} venues across {len(self._domain_mapping)} domains"
        )

    def get_venue_info(self, venue_name: str) -> Optional[VenueInfo]:
        """Get comprehensive information for a venue"""
        return self._venue_db.get(venue_name)

    def get_venues_by_domain(self, domain: str) -> List[VenueInfo]:
        """Get all venues for a specific domain"""
        venue_names = self._domain_mapping.get(domain, [])
        return [self._venue_db[name] for name in venue_names]

    def get_venues_by_tier(self, tier: VenueTier) -> List[VenueInfo]:
        """Get all venues in a specific tier"""
        venue_names = self._tier_mapping.get(tier.value, [])
        return [self._venue_db[name] for name in venue_names]

    def get_computational_venues(self, threshold: float = 0.7) -> List[VenueInfo]:
        """Get venues with high computational focus"""
        return [
            venue
            for venue in self._venue_db.values()
            if venue.computational_focus >= threshold
        ]

    def search_venues(self, query: str) -> List[VenueInfo]:
        """Search venues by name or alias"""
        query_lower = query.lower()
        matches = []

        for venue in self._venue_db.values():
            if (
                query_lower in venue.name.lower()
                or query_lower in venue.full_name.lower()
                or any(query_lower in alias.lower() for alias in venue.aliases)
            ):
                matches.append(venue)

        return matches

    def get_domain_coverage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get coverage statistics for each domain"""
        stats = {}

        for domain, venues in self._domain_mapping.items():
            domain_venues = [self._venue_db[name] for name in venues]

            tier_counts = {}
            for tier in VenueTier:
                tier_counts[tier.value] = sum(
                    1 for v in domain_venues if v.tier == tier
                )

            avg_comp_score = (
                sum(v.computational_focus for v in domain_venues) / len(domain_venues)
                if domain_venues
                else 0
            )

            stats[domain] = {
                "total_venues": len(venues),
                "tier_distribution": tier_counts,
                "avg_computational_focus": round(avg_comp_score, 2),
                "venue_types": {
                    vtype: sum(1 for v in domain_venues if v.venue_type == vtype)
                    for vtype in set(v.venue_type for v in domain_venues)
                },
            }

        return stats

    def export_database(self) -> Dict[str, Any]:
        """Export complete venue database"""
        return {
            "venues": {name: asdict(venue) for name, venue in self._venue_db.items()},
            "domain_mapping": self._domain_mapping,
            "tier_mapping": self._tier_mapping,
            "statistics": self.get_domain_coverage_stats(),
        }


class VenueClassifier:
    """Classifies and scores venues for research domains"""

    def __init__(self, venue_database: VenueDatabase):
        self.venue_db = venue_database

    def classify_venue_domain(self, venue_name: str) -> Optional[str]:
        """Determine primary research domain for a venue"""
        venue_info = self.venue_db.get_venue_info(venue_name)
        if venue_info:
            return venue_info.domain

        # Try fuzzy matching if exact match fails
        matches = self.venue_db.search_venues(venue_name)
        if matches:
            return matches[0].domain

        return None

    def get_venue_computational_score(self, venue_name: str) -> float:
        """Score venue by computational research focus (0-1)"""
        venue_info = self.venue_db.get_venue_info(venue_name)
        if venue_info:
            return venue_info.computational_focus

        # Default score for unknown venues
        return 0.5

    def rank_venues_by_importance(self, domain: str) -> List[tuple]:
        """Rank venues by paper collection priority for a domain"""
        domain_venues = self.venue_db.get_venues_by_domain(domain)

        # Score venues by multiple factors
        scored_venues = []
        for venue in domain_venues:
            # Tier scoring
            tier_scores = {
                VenueTier.TIER1: 1.0,
                VenueTier.TIER2: 0.8,
                VenueTier.SPECIALIZED: 0.9,
                VenueTier.MEDICAL: 0.85,
                VenueTier.ROBOTICS: 0.85,
                VenueTier.THEORY: 0.7,
            }

            tier_score = tier_scores.get(venue.tier, 0.5)
            comp_score = venue.computational_focus

            # Combined importance score
            importance = (tier_score * 0.6) + (comp_score * 0.4)

            scored_venues.append((venue.name, importance, venue.tier.value))

        # Sort by importance score descending
        return sorted(scored_venues, key=lambda x: x[1], reverse=True)
