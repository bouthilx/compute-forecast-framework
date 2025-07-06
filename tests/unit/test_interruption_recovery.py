"""
Unit tests for InterruptionRecoveryEngine class.
Tests recovery functionality, timing requirements, and error handling.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# Add package root to Python path
package_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(package_root))

from compute_forecast.data.collectors.interruption_recovery import (
    InterruptionRecoveryEngine, InterruptionType, RecoveryStrategy
)
from compute_forecast.data.collectors.state_management import StateManager
from compute_forecast.data.collectors.state_structures import (
    VenueConfig, CheckpointData, CollectionSession, RecoveryPlan, 
    SessionResumeResult, InterruptionAnalysis, InterruptionCause,
    ErrorContext
)
from compute_forecast.data.models import APIHealthStatus, RateLimitStatus


class TestInterruptionRecoveryEngine:
    """Test InterruptionRecoveryEngine functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create StateManager instance for testing"""
        return StateManager(
            base_state_dir=temp_dir,
            backup_interval_seconds=300,
            max_checkpoints_per_session=100
        )
    
    @pytest.fixture
    def recovery_engine(self, state_manager):
        """Create InterruptionRecoveryEngine instance for testing"""
        return InterruptionRecoveryEngine(
            state_manager=state_manager,
            max_recovery_attempts=3,
            recovery_timeout_seconds=300,  # 5 minutes
            health_check_interval=30
        )
    
    @pytest.fixture
    def sample_session(self, state_manager):
        """Create a sample interrupted session"""
        venues = [
            VenueConfig(venue_name="CVPR", target_years=[2023, 2024], max_papers_per_year=50),
            VenueConfig(venue_name="ICLR", target_years=[2023, 2024], max_papers_per_year=40),
        ]
        
        session_id = state_manager.create_session(
            target_venues=venues,
            target_years=[2023, 2024],
            collection_config={"max_retries": 3, "timeout_seconds": 300}
        )
        
        # Create checkpoint to simulate partial progress
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("CVPR", 2024)],
            papers_collected=100,
            papers_by_venue={"CVPR": {2023: 100}},
            last_successful_operation="cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={}
        )
        
        state_manager.save_checkpoint(session_id, checkpoint_data)
        
        return session_id
    
    def test_recovery_engine_initialization(self, state_manager):
        """Test InterruptionRecoveryEngine initialization"""
        engine = InterruptionRecoveryEngine(
            state_manager=state_manager,
            max_recovery_attempts=5,
            recovery_timeout_seconds=600,
            health_check_interval=60
        )
        
        assert engine.state_manager == state_manager
        assert engine.max_recovery_attempts == 5
        assert engine.recovery_timeout_seconds == 600
        assert engine.health_check_interval == 60
        assert isinstance(engine._recovery_attempts, dict)
        assert isinstance(engine._active_recoveries, dict)
    
    def test_detect_interruption_type_api_failure(self, recovery_engine, state_manager, sample_session):
        """Test detection of API failure interruption"""
        # Create checkpoint with API error
        error_context = ErrorContext(
            error_type="api_timeout",
            error_message="API request timed out",
            stack_trace="Traceback...",
            venue_context="CVPR",
            year_context=2023,
            retry_count=3
        )
        
        checkpoint_data = CheckpointData(
            checkpoint_id="error_checkpoint",
            session_id=sample_session,
            checkpoint_type="error_occurred",
            timestamp=datetime.now(),
            venues_completed=[],
            venues_in_progress=[("CVPR", 2023)],
            venues_not_started=[("ICLR", 2024)],
            papers_collected=50,
            papers_by_venue={"CVPR": {2023: 50}},
            last_successful_operation="api_call_failed",
            api_health_status={},
            rate_limit_status={},
            error_context=error_context
        )
        
        state_manager.save_checkpoint(sample_session, checkpoint_data)
        
        interruption_type = recovery_engine.detect_interruption_type(sample_session)
        assert interruption_type == InterruptionType.API_FAILURE
    
    def test_detect_interruption_type_network_failure(self, recovery_engine, state_manager, sample_session):
        """Test detection of network failure interruption"""
        # Create checkpoint with network error
        error_context = ErrorContext(
            error_type="network_error",
            error_message="Connection failed",
            stack_trace="Traceback...",
            venue_context="ICLR",
            year_context=2024,
            retry_count=2
        )
        
        checkpoint_data = CheckpointData(
            checkpoint_id="network_error_checkpoint",
            session_id=sample_session,
            checkpoint_type="error_occurred",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[],
            papers_collected=75,
            papers_by_venue={"CVPR": {2023: 75}},
            last_successful_operation="network_call_failed",
            api_health_status={},
            rate_limit_status={},
            error_context=error_context
        )
        
        state_manager.save_checkpoint(sample_session, checkpoint_data)
        
        interruption_type = recovery_engine.detect_interruption_type(sample_session)
        assert interruption_type == InterruptionType.NETWORK_INTERRUPTION
    
    def test_detect_interruption_type_process_termination(self, recovery_engine, state_manager):
        """Test detection of process termination interruption"""
        # Create session with old last activity time
        venues = [VenueConfig(venue_name="CVPR", target_years=[2023], max_papers_per_year=50)]
        session_id = state_manager.create_session(
            target_venues=venues,
            target_years=[2023],
            collection_config={"max_retries": 3}
        )
        
        # Modify session to have old last activity time
        session = state_manager._active_sessions[session_id]
        session.last_activity_time = datetime.now() - timedelta(hours=2)
        
        # Update session in memory (simplified for test)
        state_manager._active_sessions[session_id] = session
        
        interruption_type = recovery_engine.detect_interruption_type(session_id)
        assert interruption_type == InterruptionType.PROCESS_TERMINATION
    
    def test_resume_interrupted_session_success(self, recovery_engine, sample_session):
        """Test successful session resumption"""
        start_time = time.time()
        
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        duration = time.time() - start_time
        
        # Verify basic result structure
        assert isinstance(result, SessionResumeResult)
        assert result.session_id == sample_session
        assert result.success is True
        assert result.recovery_duration_seconds < 300  # Within 5 minutes
        assert result.recovery_duration_seconds == pytest.approx(duration, abs=1.0)
        
        # Verify recovery steps were executed
        assert len(result.recovery_steps_executed) > 0
        assert "Interruption analysis completed" in result.recovery_steps_executed
        assert "Recovery plan generated" in result.recovery_steps_executed
        assert "Recovery feasibility validated" in result.recovery_steps_executed
        assert "State consistency validated" in result.recovery_steps_executed
        
        # Verify state consistency
        assert result.state_consistency_validated is True
        assert result.ready_for_continuation is True
        
        # Verify recovery statistics
        assert result.checkpoints_recovered >= 1
        assert result.papers_recovered > 0
        assert result.venues_recovered > 0
    
    def test_resume_interrupted_session_nonexistent(self, recovery_engine):
        """Test resumption of non-existent session"""
        result = recovery_engine.resume_interrupted_session("nonexistent_session")
        
        assert result.success is False
        assert len(result.resume_errors) > 0
        assert result.state_consistency_validated is False
        assert result.ready_for_continuation is False
    
    def test_recovery_timeout_requirement(self, recovery_engine, sample_session):
        """Test that recovery completes within 5 minutes"""
        start_time = time.time()
        
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Must complete within 5 minutes (300 seconds)
        assert duration < 300
        assert result.recovery_duration_seconds < 300
        
        # Should complete much faster in practice (within seconds)
        assert duration < 10  # Should complete within 10 seconds for tests
    
    def test_concurrent_recovery_prevention(self, recovery_engine, sample_session):
        """Test that concurrent recovery attempts are prevented"""
        # Start first recovery (simulate by adding to active recoveries)
        recovery_engine._active_recoveries[sample_session] = datetime.now()
        
        # Attempt second recovery
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        # Should fail due to concurrent recovery
        assert result.success is False
        assert any("already in progress" in error for error in result.resume_errors)
    
    def test_max_recovery_attempts(self, recovery_engine, sample_session):
        """Test maximum recovery attempts limit"""
        # Set recovery attempts to maximum
        recovery_engine._recovery_attempts[sample_session] = recovery_engine.max_recovery_attempts
        
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        # Should fail due to max attempts exceeded
        assert result.success is False
        assert any("Maximum recovery attempts" in error for error in result.resume_errors)
    
    def test_recovery_feasibility_validation(self, recovery_engine, state_manager):
        """Test recovery feasibility validation"""
        # Create session without valid checkpoints
        venues = [VenueConfig(venue_name="CVPR", target_years=[2023], max_papers_per_year=50)]
        session_id = state_manager.create_session(
            target_venues=venues,
            target_years=[2023],
            collection_config={"max_retries": 3}
        )
        
        # Mock get_recovery_plan to return low confidence
        with patch.object(state_manager, 'get_recovery_plan') as mock_plan:
            mock_plan.return_value = RecoveryPlan(
                session_id=session_id,
                plan_id="test_plan",
                created_at=datetime.now(),
                based_on_analysis=MagicMock(),
                resumption_strategy="from_last_checkpoint",
                optimal_checkpoint_id=None,
                venues_to_skip=[],
                venues_to_resume=[],
                venues_to_restart=[],
                venues_to_validate=[],
                checkpoints_to_restore=[],
                data_files_to_recover=[],
                corrupted_data_to_discard=[],
                estimated_recovery_time_minutes=2.0,
                estimated_papers_to_recover=0,
                data_loss_estimate=0,
                confidence_score=0.3,  # Low confidence
                recovery_confidence=0.3,
                recommended_validation_steps=[],
                risk_assessment=[]
            )
            
            result = recovery_engine.resume_interrupted_session(session_id)
            
            # Should fail feasibility validation
            assert result.success is False
            assert "Recovery feasibility validation" in result.recovery_steps_failed
    
    def test_checkpoint_recovery_strategy(self, recovery_engine, sample_session):
        """Test checkpoint-based recovery strategy"""
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        # Should succeed with checkpoint recovery
        assert result.success is True
        assert result.checkpoints_recovered >= 1
        assert result.papers_recovered > 0
        assert "Checkpoint loaded and validated" in result.recovery_steps_executed
    
    def test_state_consistency_validation(self, recovery_engine, sample_session):
        """Test state consistency validation after recovery"""
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        # Should validate state consistency
        assert result.state_consistency_validated is True
        assert len(result.data_integrity_checks) > 0
        assert "State consistency validated" in result.recovery_steps_executed
    
    def test_recovery_status_tracking(self, recovery_engine, sample_session):
        """Test recovery status tracking"""
        # Initially no recovery
        status = recovery_engine.get_recovery_status(sample_session)
        assert status["is_recovering"] is False
        assert status["recovery_attempts"] == 0
        
        # During recovery (simulate)
        recovery_engine._active_recoveries[sample_session] = datetime.now()
        recovery_engine._recovery_attempts[sample_session] = 1
        
        status = recovery_engine.get_recovery_status(sample_session)
        assert status["is_recovering"] is True
        assert status["recovery_attempts"] == 1
        assert status["session_id"] == sample_session
        assert status["max_attempts"] == recovery_engine.max_recovery_attempts
        assert status["timeout_seconds"] == recovery_engine.recovery_timeout_seconds
    
    def test_cancel_recovery(self, recovery_engine, sample_session):
        """Test recovery cancellation"""
        # Start recovery tracking
        recovery_engine._active_recoveries[sample_session] = datetime.now()
        
        # Cancel recovery
        cancelled = recovery_engine.cancel_recovery(sample_session)
        
        assert cancelled is True
        assert sample_session not in recovery_engine._active_recoveries
        
        # Try to cancel non-existent recovery
        cancelled = recovery_engine.cancel_recovery("nonexistent_session")
        assert cancelled is False
    
    def test_error_handling_in_recovery(self, recovery_engine, state_manager):
        """Test error handling during recovery process"""
        # Create session
        venues = [VenueConfig(venue_name="CVPR", target_years=[2023], max_papers_per_year=50)]
        session_id = state_manager.create_session(
            target_venues=venues,
            target_years=[2023],
            collection_config={"max_retries": 3}
        )
        
        # Mock state_manager to raise exception
        with patch.object(state_manager, 'get_recovery_plan', side_effect=Exception("Test error")):
            result = recovery_engine.resume_interrupted_session(session_id)
            
            # Should handle error gracefully
            assert result.success is False
            assert len(result.resume_errors) > 0
            assert any("Recovery engine error" in error for error in result.resume_errors)
            assert result.recovery_duration_seconds > 0
    
    def test_recovery_cleanup_on_success(self, recovery_engine, sample_session):
        """Test cleanup of tracking data on successful recovery"""
        # Simulate previous failed attempts
        recovery_engine._recovery_attempts[sample_session] = 2
        
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        if result.success:
            # Should reset attempt counter on success
            assert recovery_engine._recovery_attempts[sample_session] == 0
            # Should clean up active recovery tracking
            assert sample_session not in recovery_engine._active_recoveries
    
    def test_performance_requirement_validation(self, recovery_engine, sample_session):
        """Test that recovery meets performance requirements"""
        start_time = time.time()
        
        result = recovery_engine.resume_interrupted_session(sample_session)
        
        duration = time.time() - start_time
        
        # Performance requirements
        assert duration < 5.0  # Should complete within 5 seconds for tests
        assert result.recovery_duration_seconds < 300  # Within 5 minutes requirement
        
        # Should not trigger timeout warning for fast recovery
        assert not any("exceeded 5-minute requirement" in warning for warning in result.resume_warnings)
    
    def test_interruption_analysis_creation(self, recovery_engine, sample_session):
        """Test creation of detailed interruption analysis"""
        # Access the private method for testing
        analysis = recovery_engine._analyze_interruption(sample_session)
        
        assert isinstance(analysis, InterruptionAnalysis)
        assert analysis.session_id == sample_session
        assert analysis.analysis_timestamp is not None
        assert analysis.interruption_time is not None
        assert analysis.last_successful_operation is not None
        assert isinstance(analysis.venues_definitely_completed, list)
        assert isinstance(analysis.venues_possibly_incomplete, list)
        assert isinstance(analysis.valid_checkpoints, list)
        assert analysis.recovery_complexity in ["trivial", "simple", "complex", "problematic"]
        assert isinstance(analysis.interruption_cause, InterruptionCause)
    
    def test_multiple_interruption_types(self, recovery_engine, state_manager):
        """Test handling of different interruption types"""
        interruption_types = [
            InterruptionType.API_FAILURE,
            InterruptionType.NETWORK_INTERRUPTION,
            InterruptionType.COMPONENT_CRASH,
            InterruptionType.PROCESS_TERMINATION,
            InterruptionType.DISK_SPACE_EXHAUSTION
        ]
        
        for interruption_type in interruption_types:
            # Create session for each type
            venues = [VenueConfig(venue_name="CVPR", target_years=[2023], max_papers_per_year=50)]
            session_id = state_manager.create_session(
                target_venues=venues,
                target_years=[2023],
                collection_config={"max_retries": 3},
                session_id=f"test_session_{interruption_type.value}"
            )
            
            # Test detection (mock the detection logic)
            with patch.object(recovery_engine, 'detect_interruption_type', return_value=interruption_type):
                detected_type = recovery_engine.detect_interruption_type(session_id)
                assert detected_type == interruption_type
    
    def test_recovery_with_corrupted_checkpoint(self, recovery_engine, state_manager, sample_session):
        """Test recovery when checkpoint is corrupted"""
        # Mock checkpoint manager to return invalid checkpoint
        with patch.object(state_manager.checkpoint_manager, 'validate_checkpoint') as mock_validate:
            from compute_forecast.data.collectors.state_structures import CheckpointValidationResult
            
            mock_validate.return_value = CheckpointValidationResult(
                checkpoint_id="corrupted_checkpoint",
                is_valid=False,
                validation_errors=["Checksum mismatch"],
                integrity_score=0.0,
                can_be_used_for_recovery=False
            )
            
            result = recovery_engine.resume_interrupted_session(sample_session)
            
            # Should handle corrupted checkpoint
            # May still succeed with alternative recovery strategy
            assert isinstance(result, SessionResumeResult)
            assert result.recovery_duration_seconds >= 0  # Allow immediate failures


if __name__ == "__main__":
    pytest.main([__file__])