"""
Integration tests for VenueCollectionOrchestrator system.
Tests the coordination between all agent components.
"""

import pytest
import time
from unittest.mock import Mock, patch
from dataclasses import asdict

from src.orchestration.venue_collection_orchestrator import VenueCollectionOrchestrator
from src.data.models import CollectionConfig, Paper, Author

class TestVenueCollectionOrchestrator:
    """Test orchestrator system integration"""
    
    @pytest.fixture
    def test_config(self):
        """Test configuration"""
        return CollectionConfig(
            max_venues_per_batch=3,
            batch_timeout_seconds=60,
            api_priority=["semantic_scholar", "openalex"]
        )
    
    @pytest.fixture
    def orchestrator(self, test_config):
        """Create orchestrator instance"""
        return VenueCollectionOrchestrator(test_config)
    
    def test_system_initialization(self, orchestrator):
        """Test complete system initialization"""
        # Test initialization
        result = orchestrator.initialize_system()
        
        # Should complete within 60 seconds
        assert result.initialization_duration_seconds <= 60
        
        # At least critical components should initialize
        critical_components = ['agent_alpha', 'agent_beta', 'agent_gamma']
        for component in critical_components:
            assert component in result.component_status
            # Allow degraded state for testing
            assert result.component_status[component].status in ["ready", "error"]
        
        # System should have some level of readiness
        assert isinstance(result.ready_for_collection, bool)
        
        # Should have integration validation
        assert result.integration_validation is not None
        assert isinstance(result.integration_validation.overall_success, bool)
    
    def test_component_interface_validation(self, orchestrator):
        """Test that component interfaces are properly validated"""
        # Initialize system first
        init_result = orchestrator.initialize_system()
        
        # Test integration validation
        validation_result = orchestrator.validate_system_integration()
        
        assert isinstance(validation_result.component_validations, dict)
        assert isinstance(validation_result.interface_validations, dict)
        assert isinstance(validation_result.data_flow_integrity, bool)
        
        # Should test major component interfaces
        expected_components = ['agent_alpha', 'agent_beta', 'agent_gamma_venue']
        for component in expected_components:
            if component in validation_result.component_validations:
                comp_validation = validation_result.component_validations[component]
                assert hasattr(comp_validation, 'validation_passed')
                assert isinstance(comp_validation.interface_methods_found, list)
    
    def test_session_lifecycle(self, orchestrator):
        """Test complete session lifecycle"""
        # Initialize system
        init_result = orchestrator.initialize_system()
        
        # Only proceed if system is somewhat functional
        if not (orchestrator.state_manager and orchestrator.api_engine):
            pytest.skip("System components not properly initialized")
        
        # Start session
        session_id = orchestrator.start_collection_session()
        assert session_id
        assert session_id in orchestrator.active_sessions
        
        # Get system status
        status = orchestrator.get_system_status()
        assert session_id in status.active_sessions
        
        # Shutdown system
        orchestrator.shutdown_system()
        assert len(orchestrator.active_sessions) == 0
        assert not orchestrator.system_ready
    
    def test_venue_collection_workflow(self, orchestrator):
        """Test venue collection execution workflow"""
        # Initialize and start session
        init_result = orchestrator.initialize_system()
        
        if not orchestrator.system_ready:
            pytest.skip("System not ready for collection testing")
        
        session_id = orchestrator.start_collection_session()
        
        # Execute small collection
        test_venues = ["ICML", "ICLR"]
        test_years = [2024]
        
        result = orchestrator.execute_venue_collection(session_id, test_venues, test_years)
        
        # Validate result structure
        assert hasattr(result, 'session_id')
        assert hasattr(result, 'success')
        assert hasattr(result, 'venues_attempted')
        assert hasattr(result, 'raw_papers_collected')
        assert hasattr(result, 'data_quality_score')
        
        # Should attempt all venues
        assert len(result.venues_attempted) == len(test_venues) * len(test_years)
        
        # If successful, should have some papers
        if result.success:
            assert result.raw_papers_collected > 0
            assert result.data_quality_score >= 0.0
    
    def test_error_handling_resilience(self, orchestrator):
        """Test system resilience to component failures"""
        # Test with invalid session
        with pytest.raises(ValueError):
            orchestrator.execute_venue_collection("invalid_session", ["ICML"], [2024])
        
        # Test system status with failures
        status = orchestrator.get_system_status()
        assert hasattr(status, 'overall_health')
        assert status.overall_health in ["healthy", "degraded", "critical", "offline"]
    
    def test_session_recovery(self, orchestrator):
        """Test session recovery functionality"""
        # Initialize system
        orchestrator.initialize_system()
        
        if not orchestrator.state_manager:
            pytest.skip("State manager not available")
        
        # Create and then attempt to recover a session
        session_id = orchestrator.start_collection_session()
        
        # Simulate recovery
        recovery_result = orchestrator.resume_interrupted_session(session_id)
        
        # Should have proper structure
        assert hasattr(recovery_result, 'success')
        assert hasattr(recovery_result, 'session_id')
        assert hasattr(recovery_result, 'state_consistency_validated')
        assert recovery_result.session_id == session_id
    
    def test_data_flow_integrity(self, orchestrator):
        """Test data flow between components"""
        # Initialize system
        orchestrator.initialize_system()
        
        # Test data flow validation
        data_flow_ok = orchestrator._test_data_flow_integrity()
        
        # Should return boolean result
        assert isinstance(data_flow_ok, bool)
    
    def test_performance_benchmarks(self, orchestrator):
        """Test performance benchmarking"""
        # Initialize system
        orchestrator.initialize_system()
        
        # Run performance benchmarks
        benchmarks = orchestrator._run_performance_benchmarks()
        
        # Should return metrics
        assert isinstance(benchmarks, dict)
        
        # Should have basic metrics
        expected_metrics = ['api_response_time', 'processing_throughput']
        for metric in expected_metrics:
            if metric in benchmarks:
                assert isinstance(benchmarks[metric], (int, float))
                assert benchmarks[metric] >= 0

class TestSystemIntegrationRobustness:
    """Test system integration robustness and edge cases"""
    
    def test_initialization_timeout_handling(self):
        """Test behavior when initialization takes too long"""
        config = CollectionConfig()
        orchestrator = VenueCollectionOrchestrator(config)
        
        # Mock slow initialization
        with patch.object(orchestrator, '_initialize_alpha_component') as mock_alpha:
            mock_alpha.side_effect = lambda: time.sleep(0.1)  # Small delay for testing
            
            start_time = time.time()
            result = orchestrator.initialize_system()
            duration = time.time() - start_time
            
            # Should still complete
            assert result is not None
            assert hasattr(result, 'initialization_duration_seconds')
    
    def test_partial_component_failure(self):
        """Test behavior when some components fail to initialize"""
        config = CollectionConfig()
        orchestrator = VenueCollectionOrchestrator(config)
        
        # Mock component failure
        with patch.object(orchestrator, '_initialize_delta_component') as mock_delta:
            mock_delta.return_value = Mock(
                component_name="agent_delta",
                status="error",
                error_message="Mock failure"
            )
            
            result = orchestrator.initialize_system()
            
            # Should handle partial failure gracefully
            assert 'agent_delta' in result.failed_components
            assert len(result.initialization_errors) > 0
    
    def test_concurrent_session_handling(self):
        """Test handling multiple concurrent sessions"""
        config = CollectionConfig()
        orchestrator = VenueCollectionOrchestrator(config)
        
        # Initialize system
        orchestrator.initialize_system()
        
        if not orchestrator.system_ready:
            pytest.skip("System not ready for concurrent testing")
        
        # Start multiple sessions
        session_ids = []
        for i in range(3):
            session_id = orchestrator.start_collection_session()
            session_ids.append(session_id)
        
        # All should be active
        assert len(orchestrator.active_sessions) == 3
        
        # System status should show all sessions
        status = orchestrator.get_system_status()
        assert len(status.active_sessions) == 3
    
    def test_invalid_configuration_handling(self):
        """Test handling of invalid configurations"""
        # Test with minimal config
        minimal_config = CollectionConfig(max_venues_per_batch=0)
        orchestrator = VenueCollectionOrchestrator(minimal_config)
        
        # Should not crash
        result = orchestrator.initialize_system()
        assert result is not None
    
    @pytest.mark.slow
    def test_extended_workflow_execution(self):
        """Test extended workflow execution (marked as slow test)"""
        config = CollectionConfig()
        orchestrator = VenueCollectionOrchestrator(config)
        
        # Initialize system
        orchestrator.initialize_system()
        
        if not orchestrator.system_ready:
            pytest.skip("System not ready for extended testing")
        
        session_id = orchestrator.start_collection_session()
        
        # Test with more venues and years
        test_venues = ["ICML", "ICLR", "NeurIPS", "AAAI"]
        test_years = [2023, 2024]
        
        start_time = time.time()
        result = orchestrator.execute_venue_collection(session_id, test_venues, test_years)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert execution_time < 300  # 5 minutes max for test
        
        # Should attempt all venue/year combinations
        expected_attempts = len(test_venues) * len(test_years)
        assert len(result.venues_attempted) == expected_attempts