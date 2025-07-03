"""
Domain-based paper collection module.
Handles collection of papers for specific domains and years.
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

import logging

logger = logging.getLogger(__name__)


class DomainCollector:
    """Handles paper collection for specific domains and years"""
    
    def __init__(self, collection_executor):
        self.executor = collection_executor
        self.collection_results = {
            'raw_papers': [],
            'collection_stats': defaultdict(lambda: defaultdict(int)),
            'failed_searches': [],
            'source_distribution': defaultdict(int)
        }
    
    def execute_domain_collection(self, target_per_domain_year: int = 8) -> Dict[str, Any]:
        """Execute collection for each domain and year combination"""
        logger.info(f"Starting domain collection with target {target_per_domain_year} papers per domain/year")
        
        domains = self.executor.get_domains_from_analysis()
        logger.info(f"Collecting papers for {len(domains)} domains: {domains}")
        
        for domain_name in domains:
            logger.info(f"\n=== Collecting papers for {domain_name} ===")
            
            for year in range(2019, 2025):
                logger.info(f"Processing {domain_name} - {year}")
                
                try:
                    year_papers = self.collect_domain_year_papers(
                        domain_name, year, target_per_domain_year
                    )
                    
                    # Enrich papers with computational analysis
                    enriched_papers = self.enrich_papers_with_analysis(
                        year_papers, domain_name, year
                    )
                    
                    self.collection_results['raw_papers'].extend(enriched_papers)
                    self.collection_results['collection_stats'][domain_name][year] = len(enriched_papers)
                    
                    # Track source distribution
                    for paper in enriched_papers:
                        source = paper.get('source', 'unknown')
                        self.collection_results['source_distribution'][source] += 1
                    
                    logger.info(f"  ✓ Collected {len(enriched_papers)} papers for {domain_name} {year}")
                    
                except Exception as e:
                    logger.error(f"  ✗ Failed to collect papers for {domain_name} {year}: {e}")
                    self.collection_results['failed_searches'].append({
                        'domain': domain_name,
                        'year': year,
                        'error': str(e),
                        'method': 'domain_year_collection'
                    })
                
                # Rate limiting between domain/year combinations
                self.executor.rate_limiter.wait('general_search')
        
        logger.info(f"\nCollection complete! Total papers: {len(self.collection_results['raw_papers'])}")
        return self.collection_results
    
    def collect_domain_year_papers(self, domain_name: str, year: int, target_count: int) -> List[Dict[str, Any]]:
        """Collect papers for specific domain and year"""
        collected_papers = []
        
        # Method 1: Domain-specific venues (if available in collection strategy)
        if hasattr(self.executor, 'collection_strategy_optimizer') and self.executor.collection_strategy_optimizer:
            try:
                venue_papers = self.collect_from_domain_venues(domain_name, year, target_count)
                collected_papers.extend(venue_papers)
                logger.debug(f"    Domain venues: {len(venue_papers)} papers")
            except Exception as e:
                logger.warning(f"    Domain venue collection failed: {e}")
        
        # Method 2: Major ML venues with domain keywords
        try:
            keyword_papers = self.collect_from_major_venues_with_keywords(domain_name, year, target_count)
            collected_papers.extend(keyword_papers)
            logger.debug(f"    Major venues with keywords: {len(keyword_papers)} papers")
        except Exception as e:
            logger.warning(f"    Major venue keyword search failed: {e}")
        
        # Method 3: Direct keyword search (backup)
        if len(collected_papers) < target_count:
            try:
                direct_papers = self.collect_from_direct_keyword_search(domain_name, year, target_count)
                collected_papers.extend(direct_papers)
                logger.debug(f"    Direct keyword search: {len(direct_papers)} papers")
            except Exception as e:
                logger.warning(f"    Direct keyword search failed: {e}")
        
        # Remove duplicates and sort by citations
        unique_papers = self.deduplicate_papers(collected_papers)
        sorted_papers = sorted(unique_papers, key=lambda x: x.get('citations', 0), reverse=True)
        
        # Select top papers for this domain/year
        selected_papers = sorted_papers[:target_count]
        
        return selected_papers
    
    def collect_from_domain_venues(self, domain_name: str, year: int, target_count: int) -> List[Dict[str, Any]]:
        """Collect papers from domain-specific venues"""
        papers = []
        
        # Get domain-specific venues from collection strategy
        try:
            strategy = self.executor.collection_strategy_optimizer.generate_collection_strategy(domain_name)
            primary_venues = [venue.venue_name for venue in strategy.primary_venues[:3]]  # Top 3 venues per domain
            
            for venue in primary_venues:
                try:
                    citation_threshold = self.executor.get_citation_threshold(year)
                    venue_papers = self.executor.paper_collector.collect_from_venue_year(
                        venue, year, citation_threshold, working_apis=getattr(self.executor, 'working_apis', None)
                    )
                    papers.extend(venue_papers)
                    self.executor.rate_limiter.wait('venue_search')
                    
                except Exception as e:
                    self.collection_results['failed_searches'].append({
                        'venue': venue,
                        'year': year,
                        'domain': domain_name,
                        'method': 'venue_search',
                        'error': str(e)
                    })
        except Exception as e:
            logger.warning(f"Failed to generate collection strategy for {domain_name}: {e}")
        
        return papers
    
    def collect_from_major_venues_with_keywords(self, domain_name: str, year: int, target_count: int) -> List[Dict[str, Any]]:
        """Collect papers from major ML venues using domain keywords"""
        papers = []
        
        major_venues = ['NeurIPS', 'ICML', 'ICLR', 'AAAI', 'IJCAI']
        domain_keywords = self.get_domain_keywords(domain_name)
        
        for venue in major_venues:
            try:
                keyword_papers = self.executor.paper_collector.collect_from_venue_year_with_keywords(
                    venue, year, domain_keywords[:5], domain_name, working_apis=getattr(self.executor, 'working_apis', None)
                )
                papers.extend(keyword_papers)
                self.executor.rate_limiter.wait('keyword_search')
                
            except Exception as e:
                self.collection_results['failed_searches'].append({
                    'venue': venue,
                    'year': year,
                    'domain': domain_name,
                    'method': 'keyword_search',
                    'error': str(e)
                })
        
        return papers
    
    def collect_from_direct_keyword_search(self, domain_name: str, year: int, target_count: int) -> List[Dict[str, Any]]:
        """Collect papers using direct keyword search as backup"""
        papers = []
        
        domain_keywords = self.get_domain_keywords(domain_name)
        
        try:
            keyword_papers = self.executor.paper_collector.collect_from_keywords(
                domain_keywords, year, domain_name, working_apis=getattr(self.executor, 'working_apis', None)
            )
            papers.extend(keyword_papers)
            
        except Exception as e:
            logger.error(f"    Direct keyword search failed for {domain_name} {year}: {e}")
        
        return papers
    
    def get_domain_keywords(self, domain_name: str) -> List[str]:
        """Get keywords for a specific research domain"""
        domain_keyword_map = {
            'Computer Vision': [
                'computer vision', 'image recognition', 'object detection',
                'image segmentation', 'visual recognition', 'CNN', 'convolutional neural network'
            ],
            'Natural Language Processing': [
                'natural language processing', 'NLP', 'language model', 'text classification',
                'machine translation', 'sentiment analysis', 'transformer', 'BERT'
            ],
            'Reinforcement Learning': [
                'reinforcement learning', 'RL', 'policy gradient', 'Q-learning',
                'deep reinforcement learning', 'actor-critic', 'multi-agent'
            ],
            'Machine Learning Theory': [
                'machine learning theory', 'statistical learning', 'generalization bounds',
                'optimization theory', 'learning theory', 'PAC learning'
            ],
            'Deep Learning': [
                'deep learning', 'neural network', 'deep neural network',
                'backpropagation', 'gradient descent', 'representation learning'
            ],
            'Robotics': [
                'robotics', 'robot learning', 'robot control', 'manipulation',
                'robot navigation', 'autonomous systems', 'embodied AI'
            ],
            'Speech and Audio Processing': [
                'speech recognition', 'audio processing', 'speech synthesis',
                'automatic speech recognition', 'ASR', 'text-to-speech', 'voice'
            ]
        }
        
        return domain_keyword_map.get(domain_name, [domain_name.lower()])
    
    def deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity"""
        if not papers:
            return []
        
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            title = paper.get('title', '').lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)
        
        return unique_papers
    
    def enrich_papers_with_analysis(self, papers: List[Dict[str, Any]], domain_name: str, year: int) -> List[Dict[str, Any]]:
        """Add computational analysis and metadata to papers"""
        enriched_papers = []
        
        for paper in papers:
            # Convert Author objects to dictionaries if needed
            if 'authors' in paper and paper['authors']:
                serializable_authors = []
                for author in paper['authors']:
                    if hasattr(author, '__dict__'):  # It's an Author object
                        author_dict = {
                            'name': getattr(author, 'name', ''),
                            'affiliation': getattr(author, 'affiliation', ''),
                            'author_id': getattr(author, 'author_id', ''),
                            'email': getattr(author, 'email', '')
                        }
                        serializable_authors.append(author_dict)
                    else:  # It's already a dict or string
                        serializable_authors.append(author)
                paper['authors'] = serializable_authors
            
            # Add collection metadata
            paper['mila_domain'] = domain_name
            paper['collection_year'] = year
            paper['collection_timestamp'] = datetime.now().isoformat()
            
            # Add computational analysis
            try:
                computational_analysis = self.executor.computational_analyzer.analyze_paper_content(paper)
                paper['computational_analysis'] = computational_analysis
            except Exception as e:
                logger.warning(f"Computational analysis failed for paper '{paper.get('title', 'Unknown')}': {e}")
                paper['computational_analysis'] = {
                    'error': str(e),
                    'computational_richness': 0.0
                }
            
            # Add venue scoring
            try:
                venue = paper.get('venue', '')
                venue_score = self.executor.venue_classifier.get_venue_computational_score(venue)
                paper['venue_score'] = venue_score
            except Exception as e:
                logger.debug(f"Venue scoring failed: {e}")
                paper['venue_score'] = 0.5  # Default score
            
            enriched_papers.append(paper)
        
        return enriched_papers