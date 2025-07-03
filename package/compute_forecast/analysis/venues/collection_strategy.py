"""
Collection Strategy Optimization Module

This module generates optimized venue selection strategies for each research domain
to maximize paper collection efficiency and coverage.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from compute_forecast.analysis.venues.venue_database import VenueDatabase, VenueTier
from compute_forecast.analysis.venues.venue_scoring import VenueScorer, VenueScore

logger = logging.getLogger(__name__)


@dataclass
class VenueTarget:
    """Target venue for paper collection"""
    venue_name: str
    priority: str  # 'primary', 'secondary', 'backup'
    papers_per_year: int
    citation_threshold_by_year: Dict[int, int]
    collection_notes: str


@dataclass
class DomainCollectionStrategy:
    """Collection strategy for a specific research domain"""
    domain: str
    primary_venues: List[VenueTarget]
    secondary_venues: List[VenueTarget]
    general_ml_venues: List[VenueTarget]
    backup_venues: List[VenueTarget]
    total_target_papers: int
    strategy_metadata: Dict[str, Any]


class CollectionStrategyOptimizer:
    """Generates optimized collection strategies for research domains"""
    
    def __init__(self, venue_database: VenueDatabase, venue_scorer: VenueScorer):
        self.venue_db = venue_database
        self.scorer = venue_scorer
        
        # Default collection parameters
        self.default_params = {
            'papers_per_venue_year': 8,
            'primary_venue_count': 3,
            'secondary_venue_count': 3,
            'backup_venue_count': 2,
            'min_citation_thresholds': {
                2024: 5, 2023: 10, 2022: 15, 2021: 25, 2020: 40, 2019: 60, 2018: 80
            },
            'high_impact_citation_thresholds': {
                2024: 10, 2023: 20, 2022: 30, 2021: 50, 2020: 75, 2019: 100, 2018: 150
            }
        }
        
        # General ML venues that should be included for all domains
        self.general_ml_venues = ['NeurIPS', 'ICML', 'ICLR']
    
    def generate_collection_strategy(self, domain: str) -> DomainCollectionStrategy:
        """Create optimized venue selection for a specific domain"""
        logger.info(f"Generating collection strategy for domain: {domain}")
        
        # Get venue scores for domain
        venue_scores = self.scorer.score_all_venues_for_domain(domain)
        
        # Separate scores by recommendation level
        high_priority = [v for v in venue_scores if v.recommendation == 'high']
        medium_priority = [v for v in venue_scores if v.recommendation == 'medium']
        low_priority = [v for v in venue_scores if v.recommendation == 'low']
        
        # Generate venue targets for each category
        primary_venues = self._create_venue_targets(
            high_priority[:self.default_params['primary_venue_count']], 
            'primary',
            self.default_params['papers_per_venue_year'],
            self.default_params['high_impact_citation_thresholds']
        )
        
        secondary_venues = self._create_venue_targets(
            (high_priority[self.default_params['primary_venue_count']:] + medium_priority)[:self.default_params['secondary_venue_count']],
            'secondary', 
            max(self.default_params['papers_per_venue_year'] - 2, 4),
            self.default_params['min_citation_thresholds']
        )
        
        backup_venues = self._create_venue_targets(
            (medium_priority + low_priority)[:self.default_params['backup_venue_count']],
            'backup',
            max(self.default_params['papers_per_venue_year'] - 4, 2),
            self.default_params['min_citation_thresholds']
        )
        
        # Add general ML venues (always include for computational research)
        general_ml_targets = []
        for venue_name in self.general_ml_venues:
            venue_score = next((v for v in venue_scores if v.venue_name == venue_name), None)
            if venue_score:
                target = VenueTarget(
                    venue_name=venue_name,
                    priority='general_ml',
                    papers_per_year=self.default_params['papers_per_venue_year'],
                    citation_threshold_by_year=self.default_params['high_impact_citation_thresholds'],
                    collection_notes=f"High-impact general ML venue, score: {venue_score.final_score}"
                )
                general_ml_targets.append(target)
        
        # Calculate total target papers
        total_papers = (
            sum(v.papers_per_year for v in primary_venues) +
            sum(v.papers_per_year for v in secondary_venues) +
            sum(v.papers_per_year for v in general_ml_targets) +
            sum(v.papers_per_year for v in backup_venues)
        )
        
        # Generate strategy metadata
        strategy_metadata = {
            'generated_at': datetime.now().isoformat(),
            'domain_venue_count': len(venue_scores),
            'scoring_distribution': {
                'high_priority': len(high_priority),
                'medium_priority': len(medium_priority), 
                'low_priority': len(low_priority)
            },
            'collection_parameters': self.default_params,
            'venue_diversity': self._calculate_venue_diversity(venue_scores),
            'estimated_annual_papers': total_papers,
            'collection_coverage': self._assess_collection_coverage(domain, venue_scores)
        }
        
        return DomainCollectionStrategy(
            domain=domain,
            primary_venues=primary_venues,
            secondary_venues=secondary_venues,
            general_ml_venues=general_ml_targets,
            backup_venues=backup_venues,
            total_target_papers=total_papers,
            strategy_metadata=strategy_metadata
        )
    
    def _create_venue_targets(self, venue_scores: List[VenueScore], priority: str, 
                            papers_per_year: int, citation_thresholds: Dict[int, int]) -> List[VenueTarget]:
        """Create venue targets from scored venues"""
        targets = []
        
        for score in venue_scores:
            # Adjust citation thresholds based on venue quality
            adjusted_thresholds = citation_thresholds.copy()
            if score.final_score > 0.8:
                # Lower thresholds for high-quality venues
                adjusted_thresholds = {year: max(int(threshold * 0.8), 1) 
                                     for year, threshold in citation_thresholds.items()}
            elif score.final_score < 0.5:
                # Higher thresholds for lower-quality venues
                adjusted_thresholds = {year: int(threshold * 1.5) 
                                     for year, threshold in citation_thresholds.items()}
            
            # Generate collection notes
            notes = self._generate_collection_notes(score)
            
            target = VenueTarget(
                venue_name=score.venue_name,
                priority=priority,
                papers_per_year=papers_per_year,
                citation_threshold_by_year=adjusted_thresholds,
                collection_notes=notes
            )
            targets.append(target)
        
        return targets
    
    def _generate_collection_notes(self, score: VenueScore) -> str:
        """Generate collection notes for a venue"""
        notes = [f"Score: {score.final_score}"]
        
        # Add insights based on scoring factors
        factors = score.component_scores
        ranking = score.ranking_factors
        
        if factors.get('mila_paper_count', 0) > 0.7:
            notes.append("High Mila presence")
        elif factors.get('mila_paper_count', 0) < 0.2:
            notes.append("Low Mila presence - expansion opportunity")
        
        if factors.get('computational_focus', 0) > 0.8:
            notes.append("High computational focus")
        
        if factors.get('citation_impact', 0) > 0.8:
            notes.append("High-impact venue")
        
        if ranking.get('venue_tier') == 'tier1':
            notes.append("Top-tier venue")
        elif ranking.get('venue_tier') == 'specialized':
            notes.append("Specialized venue")
        
        return "; ".join(notes)
    
    def _calculate_venue_diversity(self, venue_scores: List[VenueScore]) -> Dict[str, Any]:
        """Calculate venue diversity metrics"""
        if not venue_scores:
            return {'error': 'No venues to analyze'}
        
        # Venue types from ranking factors
        venue_tiers = [score.ranking_factors.get('venue_tier', 'unknown') for score in venue_scores]
        tier_distribution = {tier: venue_tiers.count(tier) for tier in set(venue_tiers)}
        
        # Computational focus distribution
        comp_scores = [score.component_scores.get('computational_focus', 0) for score in venue_scores]
        avg_comp_focus = sum(comp_scores) / len(comp_scores)
        
        # Score distribution
        final_scores = [score.final_score for score in venue_scores]
        
        return {
            'tier_distribution': tier_distribution,
            'average_computational_focus': round(avg_comp_focus, 3),
            'score_range': {
                'min': round(min(final_scores), 3),
                'max': round(max(final_scores), 3),
                'avg': round(sum(final_scores) / len(final_scores), 3)
            },
            'high_quality_venues': sum(1 for s in final_scores if s > 0.7),
            'total_venues': len(venue_scores)
        }
    
    def _assess_collection_coverage(self, domain: str, venue_scores: List[VenueScore]) -> Dict[str, Any]:
        """Assess collection coverage for a domain"""
        # Get domain venues from database
        domain_venues = self.venue_db.get_venues_by_domain(domain)
        db_venue_names = {v.name for v in domain_venues}
        
        # Get venues from scoring
        scored_venue_names = {score.venue_name for score in venue_scores}
        
        # Calculate coverage metrics
        venues_in_both = db_venue_names & scored_venue_names
        venues_only_in_db = db_venue_names - scored_venue_names
        venues_only_in_scoring = scored_venue_names - db_venue_names
        
        return {
            'database_venues': len(db_venue_names),
            'scored_venues': len(scored_venue_names),
            'venues_in_both': len(venues_in_both),
            'venues_only_in_database': len(venues_only_in_db),
            'venues_only_in_scoring': len(venues_only_in_scoring),
            'coverage_percentage': round(len(venues_in_both) / len(db_venue_names) * 100, 1) if db_venue_names else 0,
            'missing_from_scoring': list(venues_only_in_db),
            'additional_discovered': list(venues_only_in_scoring)
        }
    
    def generate_all_domain_strategies(self) -> Dict[str, DomainCollectionStrategy]:
        """Generate collection strategies for all domains"""
        logger.info("Generating collection strategies for all domains")
        
        all_domains = list(self.venue_db._domain_mapping.keys())
        strategies = {}
        
        for domain in all_domains:
            try:
                strategy = self.generate_collection_strategy(domain)
                strategies[domain] = strategy
                logger.info(f"Generated strategy for {domain}: {strategy.total_target_papers} target papers")
            except Exception as e:
                logger.error(f"Failed to generate strategy for {domain}: {e}")
                continue
        
        return strategies
    
    def export_collection_strategies(self) -> Dict[str, Any]:
        """Export all collection strategies"""
        strategies = self.generate_all_domain_strategies()
        
        # Convert to exportable format
        export_data = {
            'generation_metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_domains': len(strategies),
                'default_parameters': self.default_params,
                'general_ml_venues': self.general_ml_venues
            },
            'domain_strategies': {},
            'summary_statistics': {}
        }
        
        # Export individual strategies
        total_venues = 0
        total_papers = 0
        
        for domain, strategy in strategies.items():
            export_data['domain_strategies'][domain] = asdict(strategy)
            total_venues += len(strategy.primary_venues) + len(strategy.secondary_venues) + len(strategy.backup_venues)
            total_papers += strategy.total_target_papers
        
        # Calculate summary statistics
        if strategies:
            avg_papers_per_domain = total_papers / len(strategies)
            avg_venues_per_domain = total_venues / len(strategies)
            
            domain_papers = [s.total_target_papers for s in strategies.values()]
            
            export_data['summary_statistics'] = {
                'total_target_papers': total_papers,
                'total_unique_venues': total_venues,
                'average_papers_per_domain': round(avg_papers_per_domain, 1),
                'average_venues_per_domain': round(avg_venues_per_domain, 1),
                'papers_distribution': {
                    'min': min(domain_papers),
                    'max': max(domain_papers),
                    'median': sorted(domain_papers)[len(domain_papers)//2]
                },
                'domains_with_sufficient_venues': sum(1 for s in strategies.values() 
                                                    if len(s.primary_venues) >= 2),
                'collection_feasibility': 'high' if avg_venues_per_domain >= 6 else 'medium'
            }
        
        return export_data
    
    def validate_strategies(self) -> Dict[str, Any]:
        """Validate collection strategies meet requirements"""
        strategies = self.generate_all_domain_strategies()
        validation_results = {
            'overall_status': 'pass',
            'domain_validations': {},
            'issues_found': [],
            'recommendations': []
        }
        
        for domain, strategy in strategies.items():
            domain_validation = {
                'has_sufficient_primary_venues': len(strategy.primary_venues) >= 2,
                'has_backup_venues': len(strategy.backup_venues) > 0,
                'total_venues': len(strategy.primary_venues) + len(strategy.secondary_venues) + len(strategy.backup_venues),
                'target_papers_reasonable': 10 <= strategy.total_target_papers <= 100,
                'includes_general_ml': len(strategy.general_ml_venues) > 0
            }
            
            # Check for issues
            issues = []
            if not domain_validation['has_sufficient_primary_venues']:
                issues.append("Insufficient primary venues (< 2)")
            if not domain_validation['has_backup_venues']:
                issues.append("No backup venues defined")
            if not domain_validation['target_papers_reasonable']:
                issues.append(f"Unreasonable target papers: {strategy.total_target_papers}")
            
            domain_validation['issues'] = issues
            domain_validation['status'] = 'pass' if not issues else 'warning'
            
            validation_results['domain_validations'][domain] = domain_validation
            
            if issues:
                validation_results['overall_status'] = 'warning'
                validation_results['issues_found'].extend([f"{domain}: {issue}" for issue in issues])
        
        # Generate recommendations
        if validation_results['issues_found']:
            validation_results['recommendations'].append("Review domains with insufficient venue coverage")
        
        if len(strategies) < 5:
            validation_results['recommendations'].append("Consider expanding to more research domains")
        
        return validation_results