"""
Venue Relevance Scorer for Issue #8.
Scores venues based on domain relevance and computational focus.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from ..data.models import VenueAnalysis

logger = logging.getLogger(__name__)


class VenueRelevanceScorer:
    """
    Scores venues based on their relevance to computational research domains.
    """
    
    def __init__(self):
        # Venue classifications by computational focus
        self.venue_classifications = {
            'algorithms_theory': {
                'STOC', 'FOCS', 'SODA', 'ESA', 'ICALP', 'ISAAC', 'SWAT', 'WADS',
                'LATIN', 'APPROX', 'RANDOM', 'FSTTCS', 'MFCS', 'STACS', 'FCT',
                'WG', 'IPEC', 'CIAC', 'COCOON', 'COCOA', 'FAW', 'WALCOM'
            },
            'machine_learning': {
                'NEURIPS', 'NIPS', 'ICML', 'ICLR', 'AAAI', 'IJCAI', 'UAI', 'AISTATS',
                'COLT', 'ALT', 'ECML', 'PKDD', 'ACML', 'ICONIP', 'NIPS WORKSHOP',
                'ICML WORKSHOP', 'ICLR WORKSHOP', 'MLSYS', 'ML4H', 'FACCT'
            },
            'computer_vision': {
                'CVPR', 'ICCV', 'ECCV', 'BMVC', 'ACCV', 'WACV', '3DV', 'ICIP',
                'ICPR', 'FG', 'AVSS', 'CVPR Workshop', 'ICCV Workshop', 'ECCV Workshop'
            },
            'nlp': {
                'ACL', 'EMNLP', 'NAACL', 'EACL', 'COLING', 'CoNLL', 'LREC',
                'TACL', 'CL', 'ACL Workshop', 'EMNLP Workshop', 'NAACL Workshop',
                'SemEval', 'WMT', 'BEA', 'INLG', 'SIGDIAL'
            },
            'systems': {
                'OSDI', 'SOSP', 'NSDI', 'EuroSys', 'USENIX ATC', 'ASPLOS', 'ISCA',
                'MICRO', 'HPCA', 'SC', 'PPoPP', 'PLDI', 'POPL', 'OOPSLA', 'ICSE',
                'FSE', 'ASE', 'ISSTA', 'ICST', 'MSR', 'ICSME', 'SANER'
            },
            'databases': {
                'SIGMOD', 'VLDB', 'ICDE', 'PODS', 'EDBT', 'ICDT', 'DASFAA',
                'CIKM', 'SSDBM', 'DEXA', 'APWeb', 'WAIM', 'WISE', 'ER'
            },
            'security': {
                'IEEE S&P', 'CCS', 'USENIX Security', 'NDSS', 'RAID', 'ACSAC',
                'ASIACCS', 'ESORICS', 'DSN', 'CSF', 'CHES', 'FC', 'TCC', 'PKC'
            },
            'networking': {
                'SIGCOMM', 'NSDI', 'CoNEXT', 'IMC', 'INFOCOM', 'MobiCom', 'MobiSys',
                'SenSys', 'IPSN', 'EWSN', 'PerCom', 'UbiComp', 'WWW', 'WSDM'
            },
            'hci': {
                'CHI', 'UIST', 'IUI', 'CSCW', 'DIS', 'TEI', 'ISS', 'MobileHCI',
                'INTERACT', 'IDC', 'TVX', 'EICS', 'ITS', 'SUI', 'VR', 'ISMAR'
            },
            'graphics': {
                'SIGGRAPH', 'SIGGRAPH Asia', 'Eurographics', 'Pacific Graphics',
                'I3D', 'SCA', 'SGP', 'HPG', 'EGSR', 'VMV', 'CGI', 'GMP', 'SMI'
            },
            'robotics': {
                'ICRA', 'IROS', 'RSS', 'WAFR', 'ISRR', 'FSR', 'ISER', 'RUR',
                'HRI', 'RO-MAN', 'CASE', 'ICORR', 'TAROS', 'FIRA'
            },
            'bioinformatics': {
                'ISMB', 'RECOMB', 'PSB', 'WABI', 'ICCABS', 'BCB', 'BIBM',
                'BIBE', 'CSB', 'GIW', 'APBC', 'InCoB'
            }
        }
        
        # Domain keywords for venue name analysis
        self.domain_keywords = {
            'algorithms': ['algorithm', 'theory', 'computation', 'complexity', 'combinatorial'],
            'machine_learning': ['learning', 'neural', 'intelligence', 'ml', 'ai'],
            'systems': ['system', 'operating', 'distributed', 'parallel', 'architecture'],
            'databases': ['database', 'data', 'information', 'retrieval', 'mining'],
            'security': ['security', 'crypto', 'privacy', 'forensic', 'cyber'],
            'networking': ['network', 'communication', 'wireless', 'mobile', 'internet'],
            'vision': ['vision', 'visual', 'image', 'video', 'graphics'],
            'nlp': ['language', 'linguistic', 'speech', 'text', 'translation'],
            'hci': ['human', 'computer', 'interaction', 'interface', 'user'],
            'robotics': ['robot', 'autonomous', 'mechatronic', 'control']
        }
        
        # Computational focus weights by domain
        self.computational_weights = {
            'algorithms_theory': 1.0,
            'machine_learning': 0.95,
            'computer_vision': 0.9,
            'nlp': 0.85,
            'systems': 0.85,
            'databases': 0.8,
            'security': 0.75,
            'networking': 0.7,
            'robotics': 0.7,
            'bioinformatics': 0.7,
            'graphics': 0.65,
            'hci': 0.5
        }
        
        # Venue importance rankings (simplified - in practice would be more comprehensive)
        self.venue_rankings = {
            # Top-tier venues (rank 1)
            'STOC': 1, 'FOCS': 1, 'SODA': 1, 'NEURIPS': 1, 'ICML': 1, 'CVPR': 1,
            'ACL': 1, 'SIGMOD': 1, 'VLDB': 1, 'OSDI': 1, 'SOSP': 1, 'SIGCOMM': 1,
            'IEEE S&P': 1, 'CCS': 1, 'CHI': 1, 'SIGGRAPH': 1, 'ICRA': 1,
            
            # Second-tier venues (rank 2)
            'ICLR': 2, 'AAAI': 2, 'IJCAI': 2, 'ICCV': 2, 'ECCV': 2, 'EMNLP': 2,
            'ICDE': 2, 'NSDI': 2, 'EuroSys': 2, 'USENIX Security': 2, 'UIST': 2,
            'IROS': 2, 'ISMB': 2, 'ICALP': 2, 'ESA': 2, 'ASPLOS': 2,
            
            # Third-tier venues (rank 3)
            'UAI': 3, 'AISTATS': 3, 'NAACL': 3, 'COLING': 3, 'PODS': 3,
            'USENIX ATC': 3, 'NDSS': 3, 'MobiCom': 3, 'WWW': 3, 'CSCW': 3,
            'Eurographics': 3, 'RSS': 3, 'RECOMB': 3, 'APPROX': 3
        }
        
        logger.info("VenueRelevanceScorer initialized with comprehensive venue database")
    
    def score_venue(self, venue_name: str, paper_count: Optional[int] = None) -> VenueAnalysis:
        """
        Score a venue based on computational relevance and importance.
        
        Args:
            venue_name: Name of the venue
            paper_count: Optional number of papers from this venue (for context)
            
        Returns:
            VenueAnalysis with scores and rankings
        """
        # Normalize venue name
        normalized_venue = self._normalize_venue_name(venue_name)
        
        # Calculate domain relevance
        domain_relevance = self._calculate_domain_relevance(normalized_venue)
        
        # Calculate computational focus
        computational_focus = self._calculate_computational_focus(normalized_venue)
        
        # Get importance ranking
        importance_ranking = self._get_importance_ranking(normalized_venue)
        
        # Calculate overall venue score
        venue_score = self._calculate_venue_score(
            domain_relevance, computational_focus, importance_ranking
        )
        
        return VenueAnalysis(
            venue_score=venue_score,
            domain_relevance=domain_relevance,
            computational_focus=computational_focus,
            importance_ranking=importance_ranking
        )
    
    def _normalize_venue_name(self, venue_name: str) -> str:
        """Normalize venue name for matching."""
        # Remove year information
        normalized = re.sub(r'\b\d{4}\b', '', venue_name)
        
        # Remove common suffixes
        normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)
        normalized = re.sub(r'\s+Workshop.*', ' Workshop', normalized)
        normalized = re.sub(r'\s+Conference.*', '', normalized)
        normalized = re.sub(r'\s+Symposium.*', '', normalized)
        normalized = re.sub(r'\s+Proceedings.*', '', normalized)
        
        # Clean up whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def _calculate_domain_relevance(self, venue_name: str) -> float:
        """Calculate how relevant the venue is to computational domains."""
        relevance_score = 0.0
        venue_upper = venue_name.upper()
        
        # Check if venue is in known classifications
        for domain, venues in self.venue_classifications.items():
            if any(known_venue in venue_upper for known_venue in venues):
                # Use computational weight for the domain
                relevance_score = self.computational_weights.get(domain, 0.5)
                return relevance_score
        
        # If not in known venues, analyze venue name
        venue_lower = venue_name.lower()
        keyword_matches = {}
        
        for domain, keywords in self.domain_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in venue_lower)
            if matches > 0:
                keyword_matches[domain] = matches
        
        if keyword_matches:
            # Take the domain with most matches
            best_domain = max(keyword_matches.items(), key=lambda x: x[1])[0]
            # Map to computational domain
            domain_mapping = {
                'algorithms': 'algorithms_theory',
                'machine_learning': 'machine_learning',
                'vision': 'computer_vision',
                'nlp': 'nlp',
                'systems': 'systems',
                'databases': 'databases',
                'security': 'security',
                'networking': 'networking',
                'hci': 'hci',
                'robotics': 'robotics'
            }
            
            computational_domain = domain_mapping.get(best_domain, 'other')
            relevance_score = self.computational_weights.get(computational_domain, 0.5)
        else:
            # Default relevance for unknown venues
            relevance_score = 0.3
        
        return float(relevance_score)
    
    def _calculate_computational_focus(self, venue_name: str) -> float:
        """Calculate how focused the venue is on computational research."""
        focus_score = 0.0
        venue_upper = venue_name.upper()
        
        # Strong computational indicators
        strong_indicators = {
            'ALGORITHM', 'COMPUTATION', 'LEARNING', 'NEURAL', 'SYSTEM',
            'ARCHITECTURE', 'PARALLEL', 'DISTRIBUTED', 'DATA', 'MINING',
            'SECURITY', 'CRYPTO', 'NETWORK', 'OPTIMIZATION', 'COMPLEXITY'
        }
        
        # Medium computational indicators
        medium_indicators = {
            'CONFERENCE', 'SYMPOSIUM', 'WORKSHOP', 'INTERNATIONAL', 'JOURNAL',
            'TRANSACTIONS', 'COMPUTER', 'SCIENCE', 'ENGINEERING', 'TECHNOLOGY'
        }
        
        # Weak or non-computational indicators
        weak_indicators = {
            'SOCIAL', 'HUMANITIES', 'ARTS', 'BUSINESS', 'MANAGEMENT',
            'EDUCATION', 'HEALTH', 'MEDICAL', 'BIOLOGICAL', 'CHEMICAL'
        }
        
        # Calculate scores
        strong_matches = sum(1 for ind in strong_indicators if ind in venue_upper)
        medium_matches = sum(1 for ind in medium_indicators if ind in venue_upper)
        weak_matches = sum(1 for ind in weak_indicators if ind in venue_upper)
        
        # Strong indicators boost score significantly
        focus_score += min(1.0, strong_matches * 0.3)
        
        # Medium indicators provide moderate boost
        focus_score += min(0.3, medium_matches * 0.1)
        
        # Weak indicators reduce score
        focus_score -= min(0.3, weak_matches * 0.15)
        
        # Ensure score is in valid range
        focus_score = max(0.0, min(1.0, focus_score))
        
        # Special case: if venue is in our known computational venues
        for domain, venues in self.venue_classifications.items():
            if any(known_venue in venue_upper for known_venue in venues):
                # Known computational venue gets high focus score
                focus_score = max(focus_score, 0.8)
                break
        
        return float(focus_score)
    
    def _get_importance_ranking(self, venue_name: str) -> int:
        """Get importance ranking for the venue (1=top tier, higher=lower tier)."""
        venue_upper = venue_name.upper()
        
        # Check direct matches in rankings
        for ranked_venue, rank in self.venue_rankings.items():
            if ranked_venue in venue_upper:
                return rank
        
        # Check if it's a workshop of a known venue
        if 'WORKSHOP' in venue_upper:
            # Check if it contains a known venue name
            for ranked_venue, rank in self.venue_rankings.items():
                if ranked_venue in venue_upper:
                    # Workshops are typically one tier lower
                    return min(rank + 1, 5)
            # If workshop but not of a known venue
            return 4
        
        # Unknown venue - assign based on indicators
        if any(term in venue_upper for term in ['INTERNATIONAL', 'CONFERENCE', 'SYMPOSIUM']):
            return 4  # Established but not top-tier
        else:
            return 5  # Unknown or new venue
    
    def _calculate_venue_score(self, domain_relevance: float, 
                             computational_focus: float, 
                             importance_ranking: int) -> float:
        """Calculate overall venue score combining all factors."""
        # Convert importance ranking to score (1 = 1.0, 5 = 0.2)
        importance_score = 1.0 - (importance_ranking - 1) * 0.2
        
        # Weighted combination
        venue_score = (
            domain_relevance * 0.4 +
            computational_focus * 0.3 +
            importance_score * 0.3
        )
        
        return float(venue_score)
    
    def batch_score_venues(self, venue_names: List[str]) -> Dict[str, VenueAnalysis]:
        """Score multiple venues efficiently."""
        results = {}
        
        for venue_name in venue_names:
            try:
                analysis = self.score_venue(venue_name)
                results[venue_name] = analysis
            except Exception as e:
                logger.error(f"Error scoring venue '{venue_name}': {e}")
                # Return minimal analysis on error
                results[venue_name] = VenueAnalysis(
                    venue_score=0.3,
                    domain_relevance=0.3,
                    computational_focus=0.3,
                    importance_ranking=5
                )
        
        return results
    
    def get_venue_classification(self, venue_name: str) -> Optional[str]:
        """Get the computational domain classification for a venue."""
        normalized = self._normalize_venue_name(venue_name)
        venue_upper = normalized.upper()
        
        for domain, venues in self.venue_classifications.items():
            if any(known_venue in venue_upper for known_venue in venues):
                return domain
        
        return None