"""
Integration utilities for connecting dashboard with existing agent components.

Provides adapters and interfaces for integrating the monitoring dashboard
with venue collection engines, state managers, and data processors.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .dashboard_metrics import VenueProgressMetrics
from ..data.models import APIHealthStatus


logger = logging.getLogger(__name__)


class VenueEngineAdapter:
    """Adapter for venue collection engine integration"""
    
    def __init__(self, venue_engine):
        self.venue_engine = venue_engine
        
    def get_collection_progress(self) -> Dict[str, Any]:
        """Extract collection progress from venue engine"""
        try:
            # Try to get progress from venue engine
            if hasattr(self.venue_engine, 'get_collection_progress'):
                return self.venue_engine.get_collection_progress()
            
            # Fallback: construct progress from available methods
            progress = {
                'total_venues': 0,
                'completed_venues': 0, 
                'in_progress_venues': 0,
                'failed_venues': 0,
                'papers_collected': 0,
                'estimated_total_papers': 1000
            }
            
            # Try to get basic stats
            if hasattr(self.venue_engine, 'get_venue_statistics'):
                stats = self.venue_engine.get_venue_statistics()
                progress.update(stats)
            
            return progress
            
        except Exception as e:
            logger.warning(f"Failed to get collection progress: {e}")
            return {
                'total_venues': 0,
                'completed_venues': 0,
                'in_progress_venues': 0, 
                'failed_venues': 0,
                'papers_collected': 0,
                'estimated_total_papers': 1000
            }
    
    def get_api_health_status(self) -> Dict[str, APIHealthStatus]:
        """Extract API health status from venue engine"""
        try:
            # Try to get API health from venue engine
            if hasattr(self.venue_engine, 'get_api_health_status'):
                return self.venue_engine.get_api_health_status()
            
            # Try to get from API health monitor
            if hasattr(self.venue_engine, 'api_health_monitor'):
                monitor = self.venue_engine.api_health_monitor
                api_names = ['semantic_scholar', 'openalex', 'crossref', 'google_scholar']
                
                health_statuses = {}
                for api_name in api_names:
                    try:
                        health_status = monitor.get_health_status(api_name)
                        health_statuses[api_name] = health_status
                    except Exception as e:
                        logger.debug(f"Could not get health for {api_name}: {e}")
                
                return health_statuses
            
            return {}
            
        except Exception as e:
            logger.warning(f"Failed to get API health status: {e}")
            return {}
    
    def get_venue_progress(self) -> Dict[str, Dict[str, Any]]:
        """Extract individual venue progress from venue engine"""
        try:
            # Try to get venue-specific progress
            if hasattr(self.venue_engine, 'get_venue_progress'):
                return self.venue_engine.get_venue_progress()
            
            # Fallback: construct mock venue progress
            venues = ['NeurIPS', 'ICML', 'AAAI', 'IJCAI', 'KDD']
            years = [2019, 2020, 2021, 2022, 2023, 2024]
            
            venue_progress = {}
            for venue in venues:
                for year in years:
                    venue_key = f"{venue}_{year}"
                    venue_progress[venue_key] = {
                        'status': 'not_started',
                        'papers_collected': 0,
                        'target_papers': 100,
                        'completion_percentage': 0.0,
                        'last_update_time': datetime.now(),
                        'duration_minutes': 0.0,
                        'estimated_remaining_minutes': 0.0
                    }
            
            return venue_progress
            
        except Exception as e:
            logger.warning(f"Failed to get venue progress: {e}")
            return {}


class StateManagerAdapter:
    """Adapter for state manager integration"""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        
    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """Extract checkpoint statistics from state manager"""
        try:
            if hasattr(self.state_manager, 'get_checkpoint_statistics'):
                return self.state_manager.get_checkpoint_statistics()
            
            # Fallback: construct basic checkpoint stats
            return {
                'checkpoints_created': 0,
                'last_checkpoint_time': None,
                'rate_per_hour': 0.0,
                'recovery_possible': True,
                'last_recovery_time': None,
                'recovery_success_rate': 1.0,
                'state_size_mb': 0.0,
                'checkpoint_size_mb': 0.0,
                'creation_time_ms': 0.0,
                'save_time_ms': 0.0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get checkpoint statistics: {e}")
            return {
                'checkpoints_created': 0,
                'last_checkpoint_time': None,
                'rate_per_hour': 0.0,
                'recovery_possible': True,
                'last_recovery_time': None,
                'recovery_success_rate': 1.0,
                'state_size_mb': 0.0,
                'checkpoint_size_mb': 0.0,
                'creation_time_ms': 0.0,
                'save_time_ms': 0.0
            }


class DataProcessorAdapter:
    """Adapter for data processor integration"""
    
    def __init__(self, processors: Dict[str, Any]):
        self.processors = processors or {}
        
    def get_venue_normalizer_stats(self) -> Dict[str, Any]:
        """Get venue normalization statistics"""
        try:
            normalizer = self.processors.get('venue_normalizer')
            if normalizer and hasattr(normalizer, 'get_mapping_statistics'):
                return normalizer.get_mapping_statistics()
            
            return {
                'venues_normalized': 0,
                'accuracy': 1.0,
                'rate_per_second': 0.0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get venue normalizer stats: {e}")
            return {
                'venues_normalized': 0,
                'accuracy': 1.0,
                'rate_per_second': 0.0
            }
    
    def get_deduplicator_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        try:
            deduplicator = self.processors.get('deduplicator')
            if deduplicator and hasattr(deduplicator, 'get_statistics'):
                return deduplicator.get_statistics()
            
            return {
                'papers_processed': 0,
                'duplicates_removed': 0,
                'deduplication_rate': 0.0,
                'confidence': 1.0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get deduplicator stats: {e}")
            return {
                'papers_processed': 0,
                'duplicates_removed': 0,
                'deduplication_rate': 0.0,
                'confidence': 1.0
            }
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get computational filter statistics"""
        try:
            comp_filter = self.processors.get('computational_filter')
            if comp_filter and hasattr(comp_filter, 'get_statistics'):
                return comp_filter.get_statistics()
            
            return {
                'papers_analyzed': 0,
                'papers_above_threshold': 0,
                'breakthrough_papers': 0,
                'rate_per_second': 0.0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get filter stats: {e}")
            return {
                'papers_analyzed': 0,
                'papers_above_threshold': 0,
                'breakthrough_papers': 0,
                'rate_per_second': 0.0
            }


class DashboardIntegration:
    """Main integration class for dashboard with all components"""
    
    def __init__(self, venue_engine=None, state_manager=None, data_processors=None):
        self.venue_adapter = VenueEngineAdapter(venue_engine) if venue_engine else None
        self.state_adapter = StateManagerAdapter(state_manager) if state_manager else None
        self.processor_adapter = DataProcessorAdapter(data_processors)
        
    def create_mock_components(self):
        """Create mock components for testing"""
        self.venue_adapter = MockVenueEngine()
        self.state_adapter = MockStateManager()
        self.processor_adapter = MockDataProcessors()
        
    def get_venue_engine_adapter(self) -> Optional[VenueEngineAdapter]:
        return self.venue_adapter
    
    def get_state_manager_adapter(self) -> Optional[StateManagerAdapter]:
        return self.state_adapter
    
    def get_processor_adapter(self) -> DataProcessorAdapter:
        return self.processor_adapter


class MockVenueEngine:
    """Mock venue engine for testing"""
    
    def __init__(self):
        self.mock_data = {
            'papers_collected': 0,
            'venues_completed': 0,
            'session_start': datetime.now()
        }
    
    def get_collection_progress(self) -> Dict[str, Any]:
        # Simulate growing collection
        import time
        elapsed_minutes = (datetime.now() - self.mock_data['session_start']).total_seconds() / 60
        papers_collected = int(elapsed_minutes * 5)  # 5 papers per minute
        
        return {
            'total_venues': 30,
            'completed_venues': min(papers_collected // 100, 30),
            'in_progress_venues': 1 if papers_collected < 3000 else 0,
            'failed_venues': 0,
            'papers_collected': papers_collected,
            'estimated_total_papers': 3000
        }
    
    def get_api_health_status(self) -> Dict[str, APIHealthStatus]:
        return {
            'semantic_scholar': APIHealthStatus(
                api_name='semantic_scholar',
                status='healthy',
                success_rate=0.95,
                avg_response_time_ms=450.0,
                consecutive_errors=0
            ),
            'openalex': APIHealthStatus(
                api_name='openalex',
                status='degraded',
                success_rate=0.85,
                avg_response_time_ms=1200.0,
                consecutive_errors=2
            )
        }
    
    def get_venue_progress(self) -> Dict[str, Dict[str, Any]]:
        venues = ['NeurIPS', 'ICML', 'AAAI', 'IJCAI', 'KDD']
        years = [2019, 2020, 2021, 2022, 2023, 2024]
        
        progress = {}
        for i, venue in enumerate(venues):
            for j, year in enumerate(years):
                venue_key = f"{venue}_{year}"
                # Simulate different completion states
                total_items = len(venues) * len(years)
                completed_items = min(i * len(years) + j, total_items - 5)
                
                if completed_items <= i * len(years) + j:
                    status = 'completed'
                    papers = 100
                elif completed_items == i * len(years) + j:
                    status = 'in_progress'
                    papers = 50
                else:
                    status = 'not_started'
                    papers = 0
                
                progress[venue_key] = {
                    'status': status,
                    'papers_collected': papers,
                    'target_papers': 100,
                    'completion_percentage': papers,
                    'last_update_time': datetime.now(),
                    'duration_minutes': papers * 0.5,
                    'estimated_remaining_minutes': (100 - papers) * 0.5
                }
        
        return progress


class MockStateManager:
    """Mock state manager for testing"""
    
    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        return {
            'checkpoints_created': 15,
            'last_checkpoint_time': datetime.now(),
            'rate_per_hour': 4.0,
            'recovery_possible': True,
            'last_recovery_time': None,
            'recovery_success_rate': 1.0,
            'state_size_mb': 25.5,
            'checkpoint_size_mb': 12.3,
            'creation_time_ms': 150.0,
            'save_time_ms': 75.0
        }


class MockDataProcessors:
    """Mock data processors for testing"""
    
    def get_venue_normalizer_stats(self) -> Dict[str, Any]:
        return {
            'venues_normalized': 150,
            'accuracy': 0.96,
            'rate_per_second': 25.0
        }
    
    def get_deduplicator_stats(self) -> Dict[str, Any]:
        return {
            'papers_processed': 1250,
            'duplicates_removed': 85,
            'deduplication_rate': 0.068,
            'confidence': 0.92
        }
    
    def get_filter_stats(self) -> Dict[str, Any]:
        return {
            'papers_analyzed': 1165,
            'papers_above_threshold': 892,
            'breakthrough_papers': 45,
            'rate_per_second': 15.5
        }