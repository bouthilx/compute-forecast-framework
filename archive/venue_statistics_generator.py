#!/usr/bin/env python3
"""
Venue Statistics Generator for Mila Papers
Worker 2: Generate comprehensive venue publication statistics from Mila papers dataset
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict, Counter
from datetime import datetime
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MilaVenueStatisticsGenerator:
    """Generate comprehensive venue statistics from Mila papers data"""
    
    def __init__(self, input_file: str = "all_domains_full.json"):
        self.input_file = Path(input_file)
        self.output_file = Path("data/mila_venue_statistics.json")
        self.papers_data = []
        
        # Venue normalization mapping
        self.venue_aliases = {
            'Conference on Computer Vision and Pattern Recognition': 'CVPR',
            'International Conference on Computer Vision': 'ICCV', 
            'European Conference on Computer Vision': 'ECCV',
            'Conference on Neural Information Processing Systems': 'NeurIPS',
            'International Conference on Machine Learning': 'ICML',
            'International Conference on Learning Representations': 'ICLR',
            'Association for Computational Linguistics': 'ACL',
            'Empirical Methods in Natural Language Processing': 'EMNLP',
            'North American Chapter of the Association for Computational Linguistics': 'NAACL',
            'AAAI Conference on Artificial Intelligence': 'AAAI',
            'International Joint Conference on Artificial Intelligence': 'IJCAI',
            'IEEE Transactions on Pattern Analysis and Machine Intelligence': 'TPAMI',
            'Journal of Machine Learning Research': 'JMLR',
            'Nature Machine Intelligence': 'Nature MI',
            'Science Robotics': 'Science Robotics',
            'Int. J. Robotics Res.': 'IJRR',
            'Empirical Software Engineering': 'Empirical Software Engineering',
            'IEEE Transactions on Image Processing': 'TIP',
            'Neural Networks': 'Neural Networks'
        }
        
        # Advanced venue normalization patterns
        self.venue_patterns = [
            # NeurIPS variations
            (r'NeurIPS\.cc/\d+/Conference', 'NeurIPS'),
            (r'NeurIPS\.cc/\d+/.*', 'NeurIPS'),
            # ICLR variations  
            (r'ICLR\.cc/\d+/Conference', 'ICLR'),
            (r'ICLR\.cc/\d+/.*', 'ICLR'),
            # ICML variations
            (r'Proceedings of the \d+th International Conference on Machine Learning', 'ICML'),
            (r'Proceedings of the \d+st International Conference on Machine Learning', 'ICML'),
            (r'Proceedings of the \d+nd International Conference on Machine Learning', 'ICML'),
            (r'Proceedings of the \d+rd International Conference on Machine Learning', 'ICML'),
            # CVPR variations
            (r'Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition', 'CVPR'),
            (r'IEEE/CVF Conference on Computer Vision and Pattern Recognition', 'CVPR'),
            # ICCV variations
            (r'Proceedings of the IEEE/CVF International Conference on Computer Vision', 'ICCV'),
            (r'IEEE/CVF International Conference on Computer Vision', 'ICCV'),
            # AAAI variations
            (r'Proceedings of the \d+th AAAI Conference on Artificial Intelligence', 'AAAI'),
            (r'AAAI-\d+', 'AAAI'),
        ]
        
        # Venue computational focus scores (0.0 to 1.0)
        self.computational_scores = {
            'NeurIPS': 0.95, 'ICML': 0.95, 'ICLR': 0.90,
            'CVPR': 0.90, 'ICCV': 0.90, 'ECCV': 0.85,
            'ACL': 0.75, 'EMNLP': 0.75, 'NAACL': 0.70,
            'AAAI': 0.80, 'IJCAI': 0.80, 'AISTATS': 0.85,
            'ICRA': 0.85, 'IROS': 0.80, 'RSS': 0.90,
            'MICCAI': 0.80, 'IPMI': 0.75, 'ISBI': 0.70,
            'TPAMI': 0.85, 'TIP': 0.80, 'JMLR': 0.90,
            'Nature MI': 0.95, 'Science Robotics': 0.90,
            'IJRR': 0.85, 'Neural Networks': 0.85,
            'Empirical Software Engineering': 0.60
        }
        
        # Citation averages (estimated from venue rankings)
        self.citation_averages = {
            'NeurIPS': 31.2, 'ICML': 29.8, 'ICLR': 28.5,
            'CVPR': 28.5, 'ICCV': 27.3, 'ECCV': 25.8,
            'ACL': 22.4, 'EMNLP': 21.6, 'NAACL': 19.8,
            'AAAI': 18.5, 'IJCAI': 17.9, 'AISTATS': 16.2,
            'TPAMI': 35.6, 'TIP': 24.3, 'JMLR': 32.1,
            'Nature MI': 42.5, 'Science Robotics': 38.7,
            'IJRR': 26.8, 'Neural Networks': 22.1,
            'Empirical Software Engineering': 15.3
        }
        
    def load_papers_data(self) -> None:
        """Load and validate papers data"""
        logger.info(f"Loading papers data from {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
            
        with open(self.input_file, 'r') as f:
            self.papers_data = json.load(f)
            
        logger.info(f"Loaded {len(self.papers_data)} paper records")
        
        # Validate data structure
        if not self.papers_data:
            raise ValueError("No papers data loaded")
            
        sample = self.papers_data[0]
        required_fields = ['venue', 'year', 'domain_name']
        missing_fields = [field for field in required_fields if field not in sample]
        if missing_fields:
            logger.warning(f"Sample record missing fields: {missing_fields}")
            
    def normalize_venue_name(self, venue: str) -> str:
        """Normalize venue name to standard format"""
        import re
        
        if not venue or venue.lower() in ['unknown', 'n/a', '']:
            return None
            
        venue = venue.strip()
        
        # First try exact matches from aliases
        normalized = self.venue_aliases.get(venue, venue)
        if normalized != venue:
            return normalized
            
        # Then try regex patterns
        for pattern, replacement in self.venue_patterns:
            if re.search(pattern, venue):
                return replacement
                
        return venue
        
    def extract_venue_counts(self) -> Dict[str, Dict]:
        """Extract venue publication counts by year"""
        logger.info("Extracting venue publication counts")
        
        venue_data = defaultdict(lambda: {
            'total': 0,
            'by_year': defaultdict(int),
            'papers': [],
            'domains': set(),
            'unique_papers': set()  # Track unique papers by paper_id
        })
        
        for paper in self.papers_data:
            venue = self.normalize_venue_name(paper.get('venue'))
            if not venue:
                continue
                
            year = str(paper.get('year', ''))
            if not year or year == '0':
                continue
                
            paper_id = paper.get('paper_id', '')
            domain = paper.get('domain_name', 'Unknown')
            
            # Only count unique papers per venue
            venue_data[venue]['unique_papers'].add(paper_id)
            venue_data[venue]['by_year'][year] += 1
            venue_data[venue]['papers'].append(paper)
            venue_data[venue]['domains'].add(domain)
            
        # Calculate totals and convert sets to counts/lists
        final_venue_data = {}
        for venue, data in venue_data.items():
            final_venue_data[venue] = {
                'total': len(data['unique_papers']),
                'by_year': dict(data['by_year']),
                'domains': list(data['domains']),
                'paper_count': len(data['papers']),  # Total records (may have duplicates)
                'unique_paper_count': len(data['unique_papers'])
            }
            
        logger.info(f"Processed {len(final_venue_data)} venues")
        return final_venue_data
        
    def create_domain_venue_mapping(self) -> Dict[str, Dict[str, int]]:
        """Create mapping of domains to venues with paper counts"""
        logger.info("Creating domain-venue mapping")
        
        domain_venues = defaultdict(lambda: defaultdict(set))  # Track unique papers
        
        for paper in self.papers_data:
            venue = self.normalize_venue_name(paper.get('venue'))
            if not venue:
                continue
                
            domain = paper.get('domain_name', 'Unknown')
            paper_id = paper.get('paper_id', '')
            
            domain_venues[domain][venue].add(paper_id)
            
        # Convert to counts
        final_mapping = {}
        for domain, venues in domain_venues.items():
            final_mapping[domain] = {
                venue: len(paper_ids) 
                for venue, paper_ids in venues.items()
            }
            
        logger.info(f"Mapped {len(final_mapping)} domains to venues")
        return final_mapping
        
    def calculate_venue_metadata(self, venue_counts: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate venue quality metrics and metadata"""
        logger.info("Calculating venue metadata")
        
        venue_metadata = {
            'computational_scores': {},
            'citation_averages': {},
            'venue_types': {},
            'year_coverage': {},
            'domain_diversity': {}
        }
        
        for venue, data in venue_counts.items():
            # Computational focus score
            venue_metadata['computational_scores'][venue] = self.computational_scores.get(venue, 0.5)
            
            # Citation averages
            venue_metadata['citation_averages'][venue] = self.citation_averages.get(venue, 15.0)
            
            # Venue type classification
            venue_type = self._classify_venue_type(venue)
            venue_metadata['venue_types'][venue] = venue_type
            
            # Year coverage analysis
            years = list(data['by_year'].keys())
            if years:
                venue_metadata['year_coverage'][venue] = {
                    'first_year': min(years),
                    'last_year': max(years), 
                    'year_span': len(years),
                    'years_active': sorted(years)
                }
            
            # Domain diversity
            domain_count = len(data['domains'])
            venue_metadata['domain_diversity'][venue] = {
                'domain_count': domain_count,
                'domains': data['domains'],
                'diversity_score': min(domain_count / 5.0, 1.0)  # Normalize to max 5 domains
            }
            
        return venue_metadata
        
    def _classify_venue_type(self, venue: str) -> str:
        """Classify venue as conference, journal, or workshop"""
        venue_lower = venue.lower()
        
        # Journal indicators
        journal_keywords = ['journal', 'transactions', 'proceedings', 'nature', 'science', 'acm', 'ieee']
        if any(keyword in venue_lower for keyword in journal_keywords):
            return 'journal'
            
        # Conference indicators  
        conference_keywords = ['conference', 'cvpr', 'iclr', 'icml', 'neurips', 'aaai', 'ijcai']
        if any(keyword in venue_lower for keyword in conference_keywords):
            return 'conference'
            
        # Workshop indicators
        workshop_keywords = ['workshop', 'symposium', 'forum']
        if any(keyword in venue_lower for keyword in workshop_keywords):
            return 'workshop'
            
        return 'conference'  # Default assumption
        
    def generate_analysis_summary(self, venue_counts: Dict, domain_mapping: Dict) -> Dict[str, Any]:
        """Generate overall analysis summary statistics"""
        total_venues = len(venue_counts)
        total_papers = sum(data['unique_paper_count'] for data in venue_counts.values())
        
        # Year coverage analysis
        all_years = set()
        for data in venue_counts.values():
            all_years.update(data['by_year'].keys())
            
        years_covered = sorted([year for year in all_years if year.isdigit()])
        
        # Calculate venue coverage rate (venues with > 1 paper)
        active_venues = sum(1 for data in venue_counts.values() if data['total'] > 1)
        venue_coverage_rate = active_venues / total_venues if total_venues > 0 else 0
        
        # Domain coverage
        total_domains = len(domain_mapping)
        
        return {
            'total_venues': total_venues,
            'total_papers': total_papers,
            'years_covered': years_covered,
            'venue_coverage_rate': round(venue_coverage_rate, 3),
            'total_domains': total_domains,
            'active_venues': active_venues,
            'analysis_date': datetime.now().isoformat(),
            'data_source': str(self.input_file.name)
        }
        
    def generate_statistics(self) -> Dict[str, Any]:
        """Generate complete venue statistics"""
        logger.info("Starting venue statistics generation")
        
        # Load data
        self.load_papers_data()
        
        # Extract venue counts
        venue_counts = self.extract_venue_counts()
        
        # Create domain mapping
        domain_mapping = self.create_domain_venue_mapping()
        
        # Calculate metadata
        venue_metadata = self.calculate_venue_metadata(venue_counts)
        
        # Generate summary
        analysis_summary = self.generate_analysis_summary(venue_counts, domain_mapping)
        
        # Combine all results
        results = {
            'venue_counts': venue_counts,
            'venue_by_domain': domain_mapping,
            'venue_metadata': venue_metadata,
            'analysis_summary': analysis_summary
        }
        
        logger.info("Venue statistics generation completed")
        return results
        
    def save_results(self, results: Dict[str, Any]) -> None:
        """Save results to output file"""
        # Ensure data directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving results to {self.output_file}")
        
        with open(self.output_file, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Results saved successfully ({self.output_file.stat().st_size} bytes)")
        
    def run(self) -> Dict[str, Any]:
        """Execute complete venue statistics generation"""
        try:
            results = self.generate_statistics()
            self.save_results(results)
            
            # Print summary
            summary = results['analysis_summary']
            print(f"\n{'='*60}")
            print("MILA VENUE STATISTICS GENERATION COMPLETE")  
            print(f"{'='*60}")
            print(f"Total venues analyzed: {summary['total_venues']}")
            print(f"Total papers processed: {summary['total_papers']}")
            print(f"Years covered: {summary['years_covered'][0]} - {summary['years_covered'][-1]}")
            print(f"Active venues (>1 paper): {summary['active_venues']}")
            print(f"Domain coverage: {summary['total_domains']} domains")
            print(f"Output saved to: {self.output_file}")
            print(f"{'='*60}\n")
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating venue statistics: {e}")
            raise


def main():
    """Main execution function"""
    generator = MilaVenueStatisticsGenerator()
    results = generator.run()
    return results


if __name__ == "__main__":
    main()