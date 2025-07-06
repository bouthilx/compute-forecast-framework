"""
Venue Analysis Module

This module analyzes current Mila publication venues and maps them to research domains.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict, Counter

from compute_forecast.core.config import ConfigManager
from compute_forecast.data.models import VenueAnalysis

logger = logging.getLogger(__name__)


class MilaVenueAnalyzer:
    """Analyzes venues from current Mila publication data"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.venue_config = self.config.get_venues_config()
        self.venues_by_domain = self.venue_config.get('venues_by_domain', {})
        self.computational_scores = self.venue_config.get('computational_focus_scores', {})
        
    def load_current_domain_results(self, file_path: str = None) -> Dict[str, Any]:
        """Load current domain analysis results"""
        if file_path is None:
            # Try to find the most recent domain analysis file  
            package_dir = Path(__file__).parent.parent.parent.parent
            domain_files = [
                'all_domains_full.json',          # Move this FIRST (has venues)
                'all_domains_final_fix.json',     # Move incomplete files later
                'all_domains_actual_fix.json',
                'all_domains_completely_fixed.json', 
                'all_domains_fixed.json'
            ]
            
            for filename in domain_files:
                filepath = package_dir / filename
                if filepath.exists():
                    file_path = str(filepath)
                    break
            
            if file_path is None:
                raise FileNotFoundError(f"No domain analysis file found in {package_dir}. Tried: {domain_files}")
        
        logger.info(f"Loading domain results from: {file_path}")
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load domain data from {file_path}: {e}")
        
        # Validate data structure
        if not isinstance(data, list):
            raise ValueError(f"Expected list of papers, got {type(data)}")
        
        if len(data) == 0:
            logger.warning("Loaded domain data is empty")
        else:
            logger.info(f"Successfully loaded {len(data)} domain analysis records")
            
            # Validate a sample record has expected structure
            sample = data[0]
            required_fields = ['domain_name']
            missing_fields = [field for field in required_fields if field not in sample]
            if missing_fields:
                logger.warning(f"Sample record missing expected fields: {missing_fields}")
        
        return data
    
    def extract_venues_from_papers(self, papers_data: List[Dict]) -> Dict[str, Dict]:
        """Extract venue information from papers data"""
        venue_stats = defaultdict(lambda: {
            'papers': [],
            'domains': set(),
            'years': set(),
            'total_count': 0
        })
        
        for paper in papers_data:
            # Try to extract venue from various possible fields
            venue = self._extract_venue_from_paper(paper)
            if venue:
                venue_stats[venue]['papers'].append(paper)
                venue_stats[venue]['domains'].add(paper.get('domain_name', 'Unknown'))
                venue_stats[venue]['years'].add(paper.get('year', 0))
                venue_stats[venue]['total_count'] += 1
        
        # Convert sets to lists for JSON serialization
        for venue in venue_stats:
            venue_stats[venue]['domains'] = list(venue_stats[venue]['domains'])
            venue_stats[venue]['years'] = sorted(list(venue_stats[venue]['years']))
        
        return dict(venue_stats)
    
    def _extract_venue_from_paper(self, paper: Dict) -> str:
        """Extract venue name from paper data"""
        # Check common venue field names
        venue_fields = ['venue', 'journal', 'conference', 'publication_venue', 'source']
        
        for field in venue_fields:
            if field in paper and paper[field]:
                venue = paper[field].strip()
                if venue and venue.lower() not in ['unknown', 'n/a', '']:
                    return self._normalize_venue_name(venue)
        
        # Try to extract from title or other fields if needed
        return None
    
    def _normalize_venue_name(self, venue: str) -> str:
        """Normalize venue name to standard format"""
        venue = venue.strip()
        
        # Common venue name mappings
        venue_aliases = {
            'Conference on Computer Vision and Pattern Recognition': 'CVPR',
            'International Conference on Computer Vision': 'ICCV',
            'European Conference on Computer Vision': 'ECCV',
            'Conference on Neural Information Processing Systems': 'NeurIPS',
            'International Conference on Machine Learning': 'ICML',
            'International Conference on Learning Representations': 'ICLR',
            'Association for Computational Linguistics': 'ACL',
            'Empirical Methods in Natural Language Processing': 'EMNLP',
            'North American Chapter of the Association for Computational Linguistics': 'NAACL'
        }
        
        return venue_aliases.get(venue, venue)
    
    def analyze_mila_venues(self) -> Dict[str, Any]:
        """Extract and categorize venues from current Mila publication data"""
        # Load domain analysis results
        domain_data = self.load_current_domain_results()
        
        # Extract venues from papers
        venue_stats = self.extract_venues_from_papers(domain_data)
        
        # Organize venues by domain
        venues_by_domain = defaultdict(lambda: {
            'primary_venues': [],
            'all_venues': {},
            'paper_count': 0,
            'venue_count': 0
        })
        
        # Count papers and venues per domain
        domain_paper_counts = Counter()
        domain_venue_sets = defaultdict(set)
        
        for paper in domain_data:
            domain = paper.get('domain_name', 'Unknown')
            domain_paper_counts[domain] += 1
            
            venue = self._extract_venue_from_paper(paper)
            if venue:
                domain_venue_sets[domain].add(venue)
        
        # Build domain summaries
        for domain, count in domain_paper_counts.items():
            venues_in_domain = domain_venue_sets[domain]
            
            # Get venue stats for this domain
            domain_venue_stats = {}
            for venue in venues_in_domain:
                if venue in venue_stats:
                    domain_papers = [p for p in venue_stats[venue]['papers'] 
                                   if p.get('domain_name') == domain]
                    domain_venue_stats[venue] = len(domain_papers)
            
            # Sort venues by paper count
            sorted_venues = sorted(domain_venue_stats.items(), 
                                 key=lambda x: x[1], reverse=True)
            
            venues_by_domain[domain] = {
                'primary_venues': [v[0] for v in sorted_venues[:3]],
                'all_venues': dict(sorted_venues),
                'paper_count': count,
                'venue_count': len(venues_in_domain)
            }
        
        return {
            'venues_by_domain': dict(venues_by_domain),
            'venue_statistics': venue_stats,
            'total_venues': len(venue_stats),
            'total_domains': len(venues_by_domain),
            'analysis_metadata': {
                'source_file': 'domain_analysis_results',
                'total_papers_analyzed': len(domain_data)
            }
        }
    
    def get_venue_domain_mapping(self) -> Dict[str, List[str]]:
        """Get mapping of venues to their primary domains"""
        venue_analysis = self.analyze_mila_venues()
        venue_to_domains = defaultdict(list)
        
        for domain, domain_info in venue_analysis['venues_by_domain'].items():
            for venue in domain_info['all_venues'].keys():
                venue_to_domains[venue].append(domain)
        
        return dict(venue_to_domains)
    
    def validate_venue_coverage(self) -> Dict[str, Any]:
        """Validate that all domains have sufficient venue coverage"""
        venue_analysis = self.analyze_mila_venues()
        coverage_report = {}
        
        for domain, domain_info in venue_analysis['venues_by_domain'].items():
            venue_count = domain_info['venue_count']
            paper_count = domain_info['paper_count']
            
            coverage_report[domain] = {
                'venue_count': venue_count,
                'paper_count': paper_count,
                'venues_per_paper_ratio': venue_count / max(paper_count, 1),
                'has_sufficient_venues': venue_count >= 3,
                'primary_venues': domain_info['primary_venues'],
                'coverage_status': 'good' if venue_count >= 3 else 'needs_expansion'
            }
        
        return coverage_report