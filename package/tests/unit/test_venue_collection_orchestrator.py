"""Unit tests for VenueCollectionOrchestrator."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import threading
from concurrent.futures import Future

from compute_forecast.orchestration.venue_collection_orchestrator import (
    VenueCollectionOrchestrator,
    OrchestrationConfig,
    WorkflowPhase,
    ComponentStatus,
    ComponentHealth,
    WorkflowState
)
from compute_forecast.data.models import Paper

# Mock classes for testing
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import List, Set

class SessionState(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"

@dataclass
class CollectionSession:
    session_id: str
    start_time: datetime
    state: SessionState
    target_venues: List[str]

@dataclass  
class VenueCollectionState:
    venue: str
    year: int
    status: str


class TestVenueCollectionOrchestrator:
    """Test cases for VenueCollectionOrchestrator."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for orchestrator."""
        return {
            'api_integration': Mock(),
            'rate_limiter': Mock(),
            'health_monitor': Mock(),
            'quality_monitor': Mock(),
            'checkpoint_manager': Mock(),
            'state_manager': Mock()
        }
    
    @pytest.fixture
    def orchestrator_config(self):
        """Create test orchestration config."""
        return OrchestrationConfig(
            max_concurrent_venues=3,
            max_retry_attempts=2,
            retry_delay_seconds=1.0,
            checkpoint_interval_seconds=5.0,
            health_check_interval_seconds=2.0,
            resource_allocation_interval_seconds=10.0,
            failure_recovery_timeout_seconds=30.0,
            enable_adaptive_scaling=True,
            enable_performance_optimization=True
        )
    
    @pytest.fixture
    def orchestrator(self, orchestrator_config, mock_dependencies):
        """Create orchestrator instance with mocks."""
        return VenueCollectionOrchestrator(
            config=orchestrator_config,
            **mock_dependencies
        )
    
    @pytest.fixture
    def test_session(self):
        """Create test collection session."""
        return CollectionSession(
            session_id="test-session-123",
            start_time=datetime.now(),
            state=SessionState.RUNNING,
            target_venues=["NeurIPS_2023", "ICML_2023", "ICLR_2023"]
        )
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.workflow_state.phase == WorkflowPhase.INITIALIZATION
        assert len(orchestrator.workflow_state.active_venues) == 0
        assert len(orchestrator.workflow_state.completed_venues) == 0
        assert len(orchestrator.workflow_state.failed_venues) == 0
        assert orchestrator.executor is not None
    
    def test_coordinate_collection_session_success(self, orchestrator, test_session, mock_dependencies):
        """Test successful collection session coordination."""
        # Mock successful paper collection
        mock_papers = [Mock(spec=Paper) for _ in range(10)]
        mock_dependencies['api_integration'].search_papers.return_value = mock_papers
        
        # Mock quality check passing
        mock_quality_result = Mock(passed=True, issues=[])
        mock_dependencies['quality_monitor'].check_collection_quality.return_value = mock_quality_result
        
        # Run coordination
        with patch.object(orchestrator, '_start_background_tasks'):
            with patch.object(orchestrator, '_cleanup_resources'):
                results = orchestrator.coordinate_collection_session(
                    test_session,
                    ["NeurIPS", "ICML"],
                    [2023]
                )
        
        # Verify initialization
        assert mock_dependencies['checkpoint_manager'].create_checkpoint.called
        
        # Verify API setup
        assert mock_dependencies['health_monitor'].get_health_status.called
    
    def test_initialize_workflow(self, orchestrator, test_session):
        """Test workflow initialization."""
        venues = ["NeurIPS", "ICML"]
        years = [2022, 2023]
        
        orchestrator._initialize_workflow(test_session, venues, years)
        
        # Check phase transition
        assert orchestrator.workflow_state.phase == WorkflowPhase.API_SETUP
        
        # Check component health initialization
        expected_components = [
            "api_integration", "rate_limiter", "health_monitor",
            "quality_monitor", "checkpoint_manager", "state_manager"
        ]
        for component in expected_components:
            assert component in orchestrator.workflow_state.component_health
            health = orchestrator.workflow_state.component_health[component]
            assert health.status == ComponentStatus.INITIALIZING
            assert health.component_name == component
        
        # Check checkpoint creation
        orchestrator.checkpoint_manager.create_checkpoint.assert_called_once()
    
    def test_collect_venue_data_success(self, orchestrator, test_session, mock_dependencies):
        """Test successful venue data collection."""
        venue = "NeurIPS"
        year = 2023
        mock_papers = [Mock(spec=Paper) for _ in range(50)]
        
        # Setup mocks
        mock_dependencies['api_integration'].search_papers.return_value = mock_papers
        mock_quality_result = Mock(passed=True, issues=[])
        mock_dependencies['quality_monitor'].check_collection_quality.return_value = mock_quality_result
        
        # Add venue to active set
        orchestrator.workflow_state.active_venues.add(f"{venue}_{year}")
        
        # Collect data
        result_venue, result_year, papers = orchestrator._collect_venue_data(
            test_session, venue, year
        )
        
        # Verify results
        assert result_venue == venue
        assert result_year == year
        assert papers == mock_papers
        
        # Verify state updates
        assert f"{venue}_{year}" not in orchestrator.workflow_state.active_venues
        assert f"{venue}_{year}" in orchestrator.workflow_state.completed_venues
        
        # Verify quality check
        mock_dependencies['quality_monitor'].check_collection_quality.assert_called_once_with(
            mock_papers, venue, year
        )
        
        # Verify checkpoint
        mock_dependencies['checkpoint_manager'].create_checkpoint.assert_called()
    
    def test_collect_venue_data_failure_with_retry(self, orchestrator, test_session, mock_dependencies):
        """Test venue collection failure with retry."""
        venue = "ICML"
        year = 2023
        venue_key = f"{venue}_{year}"
        
        # Initialize component health
        orchestrator._initialize_component_health()
        
        # Setup mock to fail first, then succeed
        mock_papers = [Mock(spec=Paper) for _ in range(30)]
        mock_dependencies['api_integration'].search_papers.side_effect = [
            Exception("API timeout"),
            mock_papers,
            mock_papers  # In case of additional calls
        ]
        
        # Mock quality result for successful attempt
        mock_quality_result = Mock(passed=True, issues=[])
        mock_dependencies['quality_monitor'].check_collection_quality.return_value = mock_quality_result
        
        # Add venue to active set
        orchestrator.workflow_state.active_venues.add(venue_key)
        
        # Collect data (should retry and succeed)
        result_venue, result_year, papers = orchestrator._collect_venue_data(
            test_session, venue, year
        )
        
        # Verify retry happened
        assert mock_dependencies['api_integration'].search_papers.call_count == 2
        
        # Verify success after retry
        assert result_venue == venue
        assert result_year == year
        assert papers == mock_papers
        assert venue_key in orchestrator.workflow_state.completed_venues
    
    def test_handle_venue_failure(self, orchestrator):
        """Test venue failure handling."""
        venue_key = "ICLR_2023"
        error_msg = "Network connection failed"
        
        # Initialize component health first
        orchestrator._initialize_component_health()
        
        # Add to active venues
        orchestrator.workflow_state.active_venues.add(venue_key)
        
        # Handle failure
        orchestrator._handle_venue_failure(venue_key, error_msg)
        
        # Verify state updates
        assert venue_key not in orchestrator.workflow_state.active_venues
        assert orchestrator.workflow_state.failed_venues[venue_key] == error_msg
        assert orchestrator.workflow_state.component_health["api_integration"].error_count == 1
    
    def test_should_retry(self, orchestrator):
        """Test retry decision logic."""
        venue_key = "NeurIPS_2022"
        
        # First failure - should retry
        assert orchestrator._should_retry(venue_key) is True
        
        # Increment retry count
        orchestrator._retry_counts[venue_key] = 1
        assert orchestrator._should_retry(venue_key) is True
        
        # Max retries reached
        orchestrator._retry_counts[venue_key] = 2
        assert orchestrator._should_retry(venue_key) is False
    
    def test_health_check_loop(self, orchestrator):
        """Test health check background loop."""
        # Mock the perform health checks method
        with patch.object(orchestrator, '_perform_health_checks') as mock_health_check:
            # Set stop event after first iteration
            def stop_after_one():
                orchestrator._stop_event.set()
            
            mock_health_check.side_effect = stop_after_one
            
            # Run health check loop
            orchestrator._health_check_loop()
            
            # Verify health check was called
            mock_health_check.assert_called_once()
    
    def test_resource_optimization(self, orchestrator, mock_dependencies):
        """Test resource optimization based on performance."""
        # Test slow API response - should reduce concurrency
        mock_dependencies['health_monitor'].get_average_response_time = Mock(return_value=6.0)
        
        initial_concurrency = orchestrator.config.max_concurrent_venues
        orchestrator._optimize_resource_allocation()
        
        assert orchestrator.config.max_concurrent_venues == initial_concurrency - 1
        
        # Test fast API response - should increase concurrency
        mock_dependencies['health_monitor'].get_average_response_time = Mock(return_value=0.5)
        
        orchestrator._optimize_resource_allocation()
        assert orchestrator.config.max_concurrent_venues == initial_concurrency
    
    def test_concurrent_venue_processing(self, orchestrator, test_session, mock_dependencies):
        """Test concurrent processing of multiple venues."""
        venues = ["NeurIPS", "ICML", "ICLR"]
        years = [2023]
        
        # Mock paper collection with delays
        def mock_search(query, year, venue):
            import time
            time.sleep(0.1)  # Simulate API delay
            return [Mock(spec=Paper) for _ in range(10)]
        
        mock_dependencies['api_integration'].search_papers.side_effect = mock_search
        
        # Track collection order
        collection_order = []
        original_collect = orchestrator._collect_venue_data
        
        def track_collect(session, venue, year):
            collection_order.append(venue)
            return original_collect(session, venue, year)
        
        with patch.object(orchestrator, '_collect_venue_data', track_collect):
            with patch.object(orchestrator, '_start_background_tasks'):
                with patch.object(orchestrator, '_cleanup_resources'):
                    orchestrator.coordinate_collection_session(
                        test_session, venues, years
                    )
        
        # Verify all venues were processed
        assert len(collection_order) == len(venues)
        assert set(collection_order) == set(venues)
    
    def test_workflow_finalization(self, orchestrator, test_session, mock_dependencies):
        """Test workflow finalization."""
        results = {
            "statistics": {
                "total_papers": 150,
                "successful_venues": 3,
                "failed_venues": 1
            }
        }
        
        # Set some completed venues
        orchestrator.workflow_state.completed_venues = {"NeurIPS_2023", "ICML_2023"}
        orchestrator.workflow_state.failed_venues = {"ICLR_2023": "API error"}
        
        orchestrator._finalize_workflow(test_session, results)
        
        # Verify phase
        assert orchestrator.workflow_state.phase == WorkflowPhase.COMPLETION
        
        # Verify final checkpoint
        mock_dependencies['checkpoint_manager'].create_checkpoint.assert_called()
        call_args = mock_dependencies['checkpoint_manager'].create_checkpoint.call_args
        assert call_args[1]['checkpoint_type'] == 'workflow_completed'
        assert 'results_summary' in call_args[1]['state_data']
    
    def test_orchestration_failure_handling(self, orchestrator, test_session, mock_dependencies):
        """Test handling of complete orchestration failure."""
        error = Exception("Critical system failure")
        
        orchestrator._handle_orchestration_failure(test_session, error)
        
        # Verify error recovery phase
        assert orchestrator.workflow_state.phase == WorkflowPhase.ERROR_RECOVERY
        
        # Verify error checkpoint
        mock_dependencies['checkpoint_manager'].create_checkpoint.assert_called()
        call_args = mock_dependencies['checkpoint_manager'].create_checkpoint.call_args
        assert call_args[1]['checkpoint_type'] == 'orchestration_error'
        assert str(error) in str(call_args[1]['state_data']['error'])
    
    def test_cleanup_resources(self, orchestrator):
        """Test resource cleanup."""
        # Start some background tasks
        orchestrator._health_check_task = Mock(spec=Future)
        orchestrator._checkpoint_task = Mock(spec=Future)
        orchestrator._resource_optimization_task = Mock(spec=Future)
        
        # Mock executor
        orchestrator.executor = Mock()
        
        # Clean up
        orchestrator._cleanup_resources()
        
        # Verify stop event is set
        assert orchestrator._stop_event.is_set()
        
        # Verify executor shutdown
        orchestrator.executor.shutdown.assert_called_once_with(wait=True)
    
    def test_thread_safety(self, orchestrator):
        """Test thread safety of state updates."""
        import threading
        import time
        
        results = []
        errors = []
        
        def add_venue(venue_name):
            try:
                for i in range(10):
                    with orchestrator._lock:
                        orchestrator.workflow_state.active_venues.add(f"{venue_name}_{i}")
                        time.sleep(0.001)
                        orchestrator.workflow_state.completed_venues.add(f"{venue_name}_{i}")
                        orchestrator.workflow_state.active_venues.remove(f"{venue_name}_{i}")
                results.append(f"{venue_name}_done")
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_venue, args=(f"Venue{i}",))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors and all completed
        assert len(errors) == 0
        assert len(results) == 5
        assert len(orchestrator.workflow_state.completed_venues) == 50
        assert len(orchestrator.workflow_state.active_venues) == 0